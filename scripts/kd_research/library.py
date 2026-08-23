"""Ticker document library: manifest, ingest, bind, freshness, harvest.

Primary documents live under archive/library/<TICKER>/. Sessions get a
required-set copy (hermetic). See harness/library.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.kd_research.annuals import (
    is_annual_form,
    load_run_manifest_version,
    normalize_fiscal_year,
    parse_semver,
)
from scripts.kd_research.doc_text import convert_path
from scripts.kd_research.paths import (
    ensure_archive_tree,
    iter_research_sessions,
    library_root,
    ticker_library,
)

LIBRARY_SINCE = (2, 19, 0)
BIND_REL = "registry/library_bind.json"
FETCH_LOG_REL = "registry/data_fetch_log.json"
FILING_INDEX_REL = "registry/raw/filing_index.json"
IR_LISTING_REL = "registry/raw/ir_listing.json"

ALLOWED_SUFFIXES = frozenset({".pdf", ".htm", ".html", ".txt"})
REFUSED_SUFFIXES = frozenset({".json", ".csv", ".md", ".py"})
TYPED_DIRS = ("filings", "transcripts", "supplements", "ir", "_inbox", "_unlabeled")
KINDS = (
    "annual",
    "interim",
    "earnings_release",
    "supplement",
    "transcript",
    "presentation",
    "other",
)
KIND_DIR = {
    "annual": "filings",
    "interim": "filings",
    "earnings_release": "filings",
    "supplement": "supplements",
    "transcript": "transcripts",
    "presentation": "ir",
    "other": "_unlabeled",
}
COMPLETED_STATUSES = frozenset(
    {"complete", "completed", "finalized", "done", "immutable"}
)
_PERIOD_RE = re.compile(r"(FY\s*)?((?:19|20)\d{2})(?:\s*Q([1-4]))?", re.IGNORECASE)
_DATE_RE = re.compile(r"(19|20)\d{2}-\d{2}-\d{2}")
_TICKER_SAFE = re.compile(r"[^A-Za-z0-9._-]+")

_KIND_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("transcript", re.compile(r"transcript|earnings[_\s-]*call|\bcall\b", re.I)),
    ("supplement", re.compile(r"ex-?99\.?2|supplement|ex992", re.I)),
    ("earnings_release", re.compile(r"ex-?99\.?1|ex991|8-?k|earnings[_\s-]*release|results", re.I)),
    ("interim", re.compile(r"10-?q|interim|half[_\s-]?year|6-?k|tanshin", re.I)),
    ("annual", re.compile(r"10-?k|20-?f|40-?f|annual|(?:^|_|-)ar(?:_|-|$)|yuho|integrated", re.I)),
    ("presentation", re.compile(r"presentation|deck|slides|\bir\b", re.I)),
]


class LibraryError(RuntimeError):
    """User-facing ingest/bind error."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_ticker(ticker: str) -> str:
    return str(ticker).strip().upper()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def session_enforces_library(session: Path) -> bool:
    if (session / BIND_REL).is_file():
        return True
    parsed = parse_semver(load_run_manifest_version(session))
    if parsed is None:
        return False
    return parsed >= LIBRARY_SINCE


def session_is_completed(session: Path) -> bool:
    if (session / "meta" / "prediction_snapshot.json").is_file():
        return True
    man = session / "meta" / "run_manifest.json"
    if not man.is_file():
        return False
    try:
        data = json.loads(man.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    if data.get("immutable") is True:
        return True
    status = str(data.get("status") or "").strip().lower()
    return status in COMPLETED_STATUSES


def empty_manifest(ticker: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ticker": _norm_ticker(ticker),
        "documents": [],
    }


def _lock_path(lib: Path) -> Path:
    return lib / "_manifest.lock"


def _acquire_lock(lib: Path, *, timeout: float = 30.0) -> None:
    lock = _lock_path(lib)
    deadline = time.time() + timeout
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            return
        except FileExistsError:
            if time.time() >= deadline:
                raise LibraryError(f"timeout waiting for library lock: {lock}")
            time.sleep(0.05)


def _release_lock(lib: Path) -> None:
    lock = _lock_path(lib)
    try:
        lock.unlink()
    except OSError:
        pass


def load_manifest(lib: Path) -> dict[str, Any]:
    path = lib / "manifest.json"
    if not path.is_file():
        return empty_manifest(lib.name)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_manifest(lib.name)
    if not isinstance(data, dict):
        return empty_manifest(lib.name)
    docs = data.get("documents")
    if not isinstance(docs, list):
        data["documents"] = []
    return data


def save_manifest(lib: Path, data: dict[str, Any]) -> None:
    lib.mkdir(parents=True, exist_ok=True)
    path = lib / "manifest.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_ticker_library(ticker: str, output_dir: Path | str | None = None) -> Path:
    ensure_archive_tree(output_dir)
    lib = ticker_library(ticker, output_dir)
    lib.mkdir(parents=True, exist_ok=True)
    for name in TYPED_DIRS:
        (lib / name).mkdir(exist_ok=True)
    readme = lib / "README.md"
    if not readme.is_file():
        t = _norm_ticker(ticker)
        readme.write_text(
            f"# Library for {t}\n\n"
            "Drop files in `_inbox/` then run "
            f"`python3 scripts/ingest_library.py --ticker {t}`.\n"
            "Mode A agents except 2b unlabeled must not mine this folder; "
            "bind copies the required set into the session.\n",
            encoding="utf-8",
        )
    if not (lib / "manifest.json").is_file():
        save_manifest(lib, empty_manifest(ticker))
    return lib


def parse_period(text: str | None) -> str | None:
    if not text:
        return None
    m = _PERIOD_RE.search(str(text).replace(" ", ""))
    if not m:
        return None
    year = m.group(2)
    q = m.group(3)
    if q:
        return f"FY{year}Q{q}"
    return f"FY{year}"


def period_sort_key(period: str | None) -> tuple[int, int]:
    p = parse_period(period) or ""
    m = re.match(r"FY(\d{4})(?:Q([1-4]))?$", p)
    if not m:
        return (0, 0)
    q = int(m.group(2) or 4)
    return (int(m.group(1)), q)


def classify_kind(name: str) -> str | None:
    for kind, pat in _KIND_PATTERNS:
        if pat.search(name):
            return kind
    if is_annual_form(name):
        return "annual"
    return None


def _stable_stem(ticker: str, kind: str, period: str | None, filing_date: str | None, digest: str) -> str:
    t = _TICKER_SAFE.sub("_", _norm_ticker(ticker))
    form = {
        "annual": "AR" if kind == "annual" else kind,
        "interim": "10-Q",
        "earnings_release": "8-K_EX991",
        "supplement": "SUPP",
        "transcript": "transcript",
        "presentation": "IR",
        "other": "other",
    }.get(kind, kind)
    if kind == "annual":
        form = "AR"
    parts = [t, form]
    if period:
        parts.append(period)
    if filing_date:
        parts.append(filing_date)
    else:
        parts.append(digest[:8])
    return "_".join(parts)


def find_by_sha(manifest: dict[str, Any], digest: str) -> dict[str, Any] | None:
    for doc in manifest.get("documents") or []:
        if isinstance(doc, dict) and doc.get("sha256") == digest:
            return doc
    return None


def text_ok(doc: dict[str, Any]) -> bool:
    if doc.get("conversion_status") and doc.get("conversion_status") != "ok":
        return False
    files = doc.get("files") if isinstance(doc.get("files"), dict) else {}
    text = files.get("text")
    return bool(text)


def ingest_file(
    ticker: str,
    src: Path,
    *,
    output_dir: Path | str | None = None,
    kind: str | None = None,
    fiscal_period: str | None = None,
    filing_date: str | None = None,
    ingested_from: str = "inbox",
    source_url: str | None = None,
    accession: str | None = None,
) -> dict[str, Any]:
    src = Path(src)
    suffix = src.suffix.lower()
    if suffix in REFUSED_SUFFIXES:
        raise LibraryError(f"refused extension {suffix} (not a primary document): {src.name}")
    if suffix not in ALLOWED_SUFFIXES:
        raise LibraryError(f"unsupported extension {suffix}: {src.name}")
    if not src.is_file():
        raise LibraryError(f"not a file: {src}")

    lib = ensure_ticker_library(ticker, output_dir)
    digest = sha256_file(src)
    _acquire_lock(lib)
    try:
        manifest = load_manifest(lib)
        existing = find_by_sha(manifest, digest)
        if existing:
            return {"status": "duplicate", "document": existing}

        guessed_kind = kind or classify_kind(src.name)
        period = fiscal_period or parse_period(src.name)
        date = filing_date
        if not date:
            dm = _DATE_RE.search(src.name)
            date = dm.group(0) if dm else None
        needs_label = guessed_kind is None or period is None
        if guessed_kind is None:
            guessed_kind = "other"
        dest_dir_name = "_unlabeled" if needs_label else KIND_DIR.get(guessed_kind, "_unlabeled")
        dest_dir = lib / dest_dir_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        stem = (
            src.stem
            if needs_label
            else _stable_stem(_norm_ticker(ticker), guessed_kind, period, date, digest)
        )
        original_dest = dest_dir / f"{stem}{suffix}"
        n = 2
        while original_dest.exists():
            original_dest = dest_dir / f"{stem}_v{n}{suffix}"
            n += 1
        shutil.copy2(src, original_dest)
        conv = convert_path(original_dest, original_dest.with_suffix(".txt"))
        text_rel = None
        conv_status = conv.get("status") or "failed"
        if conv_status == "ok" and conv.get("text_path"):
            text_path = Path(str(conv["text_path"]))
            try:
                text_rel = str(text_path.relative_to(lib)).replace("\\", "/")
            except ValueError:
                text_rel = text_path.name
        orig_rel = str(original_dest.relative_to(lib)).replace("\\", "/")
        doc_id = f"{guessed_kind}_{period}" if period else f"{guessed_kind}_{digest[:12]}"
        # Same id different hash → suffix
        ids = {
            str(d.get("id"))
            for d in manifest["documents"]
            if isinstance(d, dict)
        }
        if doc_id in ids:
            doc_id = f"{doc_id}_{digest[:8]}"

        doc = {
            "id": doc_id,
            "sha256": digest,
            "kind": guessed_kind,
            "form": guessed_kind if guessed_kind != "annual" else "AR",
            "fiscal_period": period,
            "filing_date": date,
            "accession": accession,
            "source_url": source_url,
            "files": {"original": orig_rel, "text": text_rel},
            "needs_label": needs_label,
            "conversion_status": conv_status,
            "conversion_detail": conv.get("detail"),
            "ingested_at": _utc_now(),
            "ingested_from": ingested_from,
        }
        if guessed_kind == "annual":
            doc["form"] = "AR"
        manifest["documents"].append(doc)
        save_manifest(lib, manifest)
        return {"status": "ingested", "document": doc}
    finally:
        _release_lock(lib)


def ingest_inbox(ticker: str, output_dir: Path | str | None = None) -> list[dict[str, Any]]:
    lib = ensure_ticker_library(ticker, output_dir)
    results: list[dict[str, Any]] = []
    inbox = lib / "_inbox"
    if not inbox.is_dir():
        return results
    for p in sorted(inbox.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() in REFUSED_SUFFIXES:
            results.append({"status": "refused", "path": p.name, "detail": p.suffix})
            continue
        if p.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        try:
            results.append(ingest_file(ticker, p, output_dir=output_dir, ingested_from="inbox"))
            p.unlink()
        except LibraryError as exc:
            results.append({"status": "error", "path": p.name, "detail": str(exc)})
    return results


def apply_label(
    ticker: str,
    filename: str,
    kind: str,
    fiscal_period: str,
    filing_date: str | None = None,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    if kind not in KINDS:
        raise LibraryError(f"unknown kind {kind!r}")
    lib = ensure_ticker_library(ticker, output_dir)
    _acquire_lock(lib)
    try:
        manifest = load_manifest(lib)
        target: dict[str, Any] | None = None
        for doc in manifest["documents"]:
            if not isinstance(doc, dict):
                continue
            files = doc.get("files") if isinstance(doc.get("files"), dict) else {}
            orig = str(files.get("original") or "")
            if Path(orig).name == filename or orig.endswith("/" + filename):
                target = doc
                break
        if target is None:
            raise LibraryError(f"no library document named {filename}")
        target["kind"] = kind
        target["form"] = "AR" if kind == "annual" else kind
        target["fiscal_period"] = parse_period(fiscal_period) or fiscal_period
        if filing_date:
            target["filing_date"] = filing_date
        target["needs_label"] = False
        files = target.get("files") if isinstance(target.get("files"), dict) else {}
        orig = files.get("original")
        text = files.get("text")
        dest_dir = lib / KIND_DIR.get(kind, "_unlabeled")
        dest_dir.mkdir(parents=True, exist_ok=True)
        for key, rel in (("original", orig), ("text", text)):
            if not rel:
                continue
            src = lib / rel
            if not src.is_file():
                continue
            dest = dest_dir / src.name
            if src.resolve() != dest.resolve():
                shutil.move(str(src), str(dest))
                files[key] = str(dest.relative_to(lib)).replace("\\", "/")
        target["files"] = files
        save_manifest(lib, manifest)
        return target
    finally:
        _release_lock(lib)


def required_annual_count(session: Path | None) -> int:
    if session is None:
        return 3
    n = 3
    brief = session / "registry" / "research_brief.json"
    ctx = session / "registry" / "market_context.json"
    for path in (brief, ctx):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if str(data.get("research_depth") or "").lower() == "deep":
            n = 5
        if str(data.get("intensity") or "").lower() == "high":
            n = 5
    return n


def _docs_of_kind(manifest: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for doc in manifest.get("documents") or []:
        if not isinstance(doc, dict):
            continue
        if doc.get("needs_label"):
            continue
        if not text_ok(doc):
            continue
        if doc.get("kind") != kind:
            continue
        out.append(doc)
    return out


def _unique_periods(docs: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """Most recent unique fiscal_period; prefer EN / year_reader_preferred / shorter name."""

    def rank(doc: dict[str, Any]) -> tuple:
        files = doc.get("files") if isinstance(doc.get("files"), dict) else {}
        name = str(files.get("text") or files.get("original") or "")
        preferred = 0 if doc.get("year_reader_preferred") else 1
        en = 0 if re.search(r"(?:^|_|-)EN(?:_|-|$)", name, re.I) else 1
        cn = 1 if re.search(r"(?:^|_|-)C(?:N)?(?:_|-|$)", name, re.I) else 0
        return (preferred, en, cn, len(name), name)

    by: dict[str, list[dict[str, Any]]] = {}
    for doc in docs:
        period = parse_period(str(doc.get("fiscal_period") or "")) or str(
            doc.get("fiscal_period") or doc.get("id")
        )
        by.setdefault(period, []).append(doc)
    ordered_periods = sorted(by.keys(), key=period_sort_key, reverse=True)
    selected: list[dict[str, Any]] = []
    for period in ordered_periods[:n]:
        candidates = sorted(by[period], key=rank)
        selected.append(candidates[0])
    return selected


def select_required_docs(
    manifest: dict[str, Any],
    *,
    n_annual: int = 3,
    n_interim: int = 2,
    n_transcript: int = 8,
) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    chosen.extend(_unique_periods(_docs_of_kind(manifest, "annual"), n_annual))
    chosen.extend(_unique_periods(_docs_of_kind(manifest, "interim"), n_interim))
    releases = _unique_periods(_docs_of_kind(manifest, "earnings_release"), 1)
    chosen.extend(releases)
    chosen.extend(_unique_periods(_docs_of_kind(manifest, "supplement"), 1))
    chosen.extend(_unique_periods(_docs_of_kind(manifest, "transcript"), n_transcript))
    # de-dupe by sha256
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for doc in chosen:
        sha = str(doc.get("sha256") or "")
        if sha and sha in seen:
            continue
        if sha:
            seen.add(sha)
        out.append(doc)
    return out


def _session_dest(kind: str) -> str:
    if kind == "transcript":
        return "data/transcripts"
    return "data/raw_sec"


def bind_to_session(
    ticker: str,
    session: Path,
    *,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    session = Path(session)
    if session_is_completed(session):
        raise LibraryError(
            f"refusing to bind into completed session {session} "
            "(prediction_snapshot or finalized run_manifest)"
        )
    lib = ensure_ticker_library(ticker, output_dir)
    manifest = load_manifest(lib)
    n_annual = required_annual_count(session)
    required = select_required_docs(manifest, n_annual=n_annual)
    unlabeled = [
        d
        for d in manifest.get("documents") or []
        if isinstance(d, dict) and d.get("needs_label")
    ]
    bound: list[dict[str, Any]] = []
    skipped_older: list[str] = []
    required_ids = {str(d.get("id")) for d in required}
    for doc in manifest.get("documents") or []:
        if not isinstance(doc, dict):
            continue
        if str(doc.get("id")) not in required_ids and doc.get("kind") in {
            "annual",
            "interim",
            "transcript",
        }:
            skipped_older.append(str(doc.get("id")))

    for doc in required:
        if not text_ok(doc):
            continue
        files = doc.get("files") if isinstance(doc.get("files"), dict) else {}
        text_rel = files.get("text")
        orig_rel = files.get("original")
        dest_rel = _session_dest(str(doc.get("kind")))
        dest_dir = session / dest_rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        copied_text = None
        if text_rel:
            src = lib / text_rel
            if src.is_file():
                dest = dest_dir / src.name
                shutil.copy2(src, dest)
                copied_text = f"{dest_rel}/{dest.name}".replace("\\", "/")
        if orig_rel:
            osrc = lib / orig_rel
            if osrc.is_file() and osrc.suffix.lower() != ".txt":
                shutil.copy2(osrc, dest_dir / osrc.name)
        if copied_text and doc.get("kind") == "supplement":
            shutil.copy2(session / copied_text, session / "data" / "latest_supplement.txt")
        bound.append(
            {
                "id": doc.get("id"),
                "kind": doc.get("kind"),
                "fiscal_period": doc.get("fiscal_period"),
                "sha256": doc.get("sha256"),
                "session_path": copied_text,
                "library_text": text_rel,
            }
        )

    payload = {
        "schema_version": 1,
        "ticker": _norm_ticker(ticker),
        "session_key": session.name,
        "library_empty": len(manifest.get("documents") or []) == 0,
        "required_set": {
            "annuals": n_annual,
            "interims": 2,
            "transcripts": 8,
        },
        "bound": bound,
        "skipped_older": skipped_older,
        "unlabeled_count": len(unlabeled),
        "bound_at": _utc_now(),
    }
    dest = session / BIND_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def load_index_items(session: Path) -> tuple[list[dict[str, Any]], str | None]:
    for rel, source in (
        (FILING_INDEX_REL, "filing_index"),
        (IR_LISTING_REL, "ir_listing"),
    ):
        path = session / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        items = data.get("items")
        if not isinstance(items, list):
            continue
        out = [i for i in items if isinstance(i, dict)]
        return out, source
    return [], None


def _match_doc(item: dict[str, Any], docs: list[dict[str, Any]]) -> dict[str, Any] | None:
    acc = str(item.get("accession") or "").strip()
    kind = str(item.get("kind") or "")
    period = parse_period(str(item.get("fiscal_period") or item.get("period") or ""))
    for doc in docs:
        if acc and str(doc.get("accession") or "") == acc:
            return doc
        if kind and doc.get("kind") == kind:
            dp = parse_period(str(doc.get("fiscal_period") or ""))
            if period and dp == period:
                return doc
    return None


def compare_freshness(
    index_items: list[dict[str, Any]],
    bound_docs: list[dict[str, Any]],
    *,
    n_annual: int = 3,
    n_interim: int = 2,
    n_transcript: int = 8,
) -> dict[str, list[dict[str, Any]]]:
    """Split index into session_missing (fetch into S) vs library_gaps (corpus only)."""
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for item in index_items:
        kind = str(item.get("kind") or "")
        if not kind:
            form = str(item.get("form") or "")
            if is_annual_form(form) or classify_kind(form) == "annual":
                kind = "annual"
            elif classify_kind(form):
                kind = classify_kind(form) or "other"
            else:
                kind = "other"
            item = {**item, "kind": kind}
        by_kind.setdefault(kind, []).append(item)

    limits = {
        "annual": n_annual,
        "interim": n_interim,
        "earnings_release": 1,
        "supplement": 1,
        "transcript": n_transcript,
    }
    session_missing: list[dict[str, Any]] = []
    library_gaps: list[dict[str, Any]] = []
    for kind, items in by_kind.items():
        n = limits.get(kind)
        if not n:
            continue

        def _item_key(it: dict[str, Any]) -> tuple[int, int]:
            return period_sort_key(
                parse_period(str(it.get("fiscal_period") or it.get("period") or it.get("filing_date") or ""))
            )

        ordered = sorted(items, key=_item_key, reverse=True)
        # unique periods
        seen_p: set[str] = set()
        uniq: list[dict[str, Any]] = []
        rest: list[dict[str, Any]] = []
        for it in ordered:
            p = parse_period(str(it.get("fiscal_period") or it.get("period") or "")) or str(
                it.get("accession") or it.get("id") or id(it)
            )
            if p in seen_p:
                rest.append(it)
                continue
            seen_p.add(p)
            uniq.append(it)
        required_items = uniq[:n]
        older = uniq[n:] + rest
        for it in required_items:
            if _match_doc(it, bound_docs) is None:
                session_missing.append(it)
        library_gaps.extend(older)
    return {"session_missing": session_missing, "library_gaps": library_gaps}


def unlabeled_matching_missing(
    unlabeled: list[dict[str, Any]],
    session_missing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for u in unlabeled:
        name = ""
        files = u.get("files") if isinstance(u.get("files"), dict) else {}
        name = str(files.get("original") or files.get("text") or u.get("id") or "")
        up = parse_period(name) or parse_period(str(u.get("fiscal_period") or ""))
        for m in session_missing:
            mp = parse_period(str(m.get("fiscal_period") or m.get("period") or ""))
            if up and mp and up == mp:
                hits.append(u)
                break
            acc = str(m.get("accession") or "")
            if acc and acc in name:
                hits.append(u)
                break
    return hits


def check_library_gates(session: Path, *, phase: str | None = None) -> list[tuple[str, str, str]]:
    """Version-banded library bind / freshness gates."""
    out: list[tuple[str, str, str]] = []
    bind_path = session / BIND_REL
    enforces = session_enforces_library(session)
    if not enforces and not bind_path.is_file():
        out.append(
            (
                "SKIPPED",
                "library_bind",
                "legacy/slim (no library_bind.json; harness_version < 2.19.0)",
            )
        )
        return out

    if not bind_path.is_file():
        out.append(("FAIL", BIND_REL, "missing on harness >= 2.19.0 — run bind_library.py before 2b"))
        return out
    try:
        bind = json.loads(bind_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        out.append(("FAIL", BIND_REL, str(exc)))
        return out
    if not isinstance(bind, dict):
        out.append(("FAIL", BIND_REL, "not an object"))
        return out
    out.append(("PASS", BIND_REL, f"bound={len(bind.get('bound') or [])}"))

    for row in bind.get("bound") or []:
        if not isinstance(row, dict):
            continue
        rel = row.get("session_path")
        if rel and not (session / str(rel)).is_file():
            out.append(("FAIL", "library_bind_path", f"bound path missing: {rel}"))

    if phase == "1_parallel_entry":
        return out

    # Completeness: on-disk index + freshness log
    items, source = load_index_items(session)
    if not source:
        out.append(
            (
                "FAIL",
                "library_index",
                f"missing {FILING_INDEX_REL} or {IR_LISTING_REL} after 2b",
            )
        )
    else:
        out.append(("PASS", "library_index", source))

    log_path = session / FETCH_LOG_REL
    freshness = None
    if log_path.is_file():
        try:
            log = json.loads(log_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log = {}
        if isinstance(log, dict):
            freshness = log.get("freshness")
    if not isinstance(freshness, dict):
        out.append(
            (
                "FAIL",
                "library_freshness",
                "data_fetch_log.freshness required (checked_at, index_source, session_missing, fetched_new)",
            )
        )
    else:
        missing_keys = [
            k
            for k in ("checked_at", "index_source", "session_missing", "fetched_new")
            if k not in freshness
        ]
        if missing_keys:
            out.append(("FAIL", "library_freshness", f"missing keys {missing_keys}"))
        else:
            out.append(("PASS", "library_freshness", str(freshness.get("index_source"))))

    unlabeled_n = int(bind.get("unlabeled_count") or 0)
    if unlabeled_n and isinstance(freshness, dict):
        missing = freshness.get("session_missing") or []
        if missing:
            out.append(
                (
                    "FAIL",
                    "library_unlabeled",
                    f"{unlabeled_n} unlabeled and session_missing still set — label or fetch",
                )
            )
        else:
            out.append(("WARN", "library_unlabeled", f"{unlabeled_n} unlabeled (not required-set)"))

    return out


def check_transcript_freshness(session: Path) -> list[tuple[str, str, str]]:
    if not session_enforces_library(session):
        return [
            (
                "SKIPPED",
                "transcript_freshness",
                "legacy/slim (harness_version < 2.19.0)",
            )
        ]
    log_path = session / FETCH_LOG_REL
    blob: dict[str, Any] | None = None
    if log_path.is_file():
        try:
            data = json.loads(log_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            raw = data.get("transcript_freshness")
            if isinstance(raw, dict):
                blob = raw
    if not blob:
        return [
            (
                "FAIL",
                "transcript_freshness",
                "data_fetch_log.transcript_freshness missing — 2e must record a check",
            )
        ]
    if "checked_at" not in blob or "latest_period" not in blob:
        return [("FAIL", "transcript_freshness", "need checked_at and latest_period")]
    return [("PASS", "transcript_freshness", str(blob.get("latest_period")))]


def check_library_path_citations(session: Path, *, full: bool = False) -> list[tuple[str, str, str]]:
    """FAIL --full if FDD / year-dives / valuation cite archive/library."""
    rels = [
        "data/valuation_model.json",
        "registry/filing_deep_dive.json",
        "registry/technical.json",
        "registry/risk_bridge.json",
        "registry/background.json",
        "registry/audit.json",
    ]
    raw = session / "registry" / "raw"
    if raw.is_dir():
        for p in raw.glob("fdd_year_*.json"):
            rels.append(str(p.relative_to(session)).replace("\\", "/"))
    reports = session / "reports"
    if reports.is_dir():
        for p in reports.glob("*.md"):
            rels.append(str(p.relative_to(session)).replace("\\", "/"))
    hits: list[str] = []
    needle = re.compile(r"archive[/\\]library[/\\]", re.I)
    for rel in rels:
        path = session / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if needle.search(text):
            hits.append(rel)
    if not hits:
        return [("PASS", "library_direct_read", "no archive/library citations in FDD/valuation")]
    detail = "; ".join(hits[:8])
    status = "FAIL" if full else "WARN"
    return [(status, "library_direct_read", detail)]


def harvest_session_documents(
    ticker: str,
    session: Path,
    *,
    output_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Copy allowed document suffixes from a session into the library. Never mutate session."""
    results: list[dict[str, Any]] = []
    roots = [
        session / "data" / "raw_sec",
        session / "data" / "transcripts",
    ]
    for root in roots:
        if not root.exists():
            continue
        files: list[Path] = []
        if root.is_file():
            files = [root]
        else:
            files = [p for p in root.rglob("*") if p.is_file()]
        for p in files:
            suf = p.suffix.lower()
            if suf in REFUSED_SUFFIXES:
                continue
            if suf not in ALLOWED_SUFFIXES:
                continue
            try:
                results.append(
                    ingest_file(
                        ticker,
                        p,
                        output_dir=output_dir,
                        ingested_from="harvest",
                    )
                )
            except LibraryError as exc:
                results.append({"status": "error", "path": str(p), "detail": str(exc)})
    return results


def harvest_ticker(ticker: str, output_dir: Path | str | None = None) -> list[dict[str, Any]]:
    t = _norm_ticker(ticker)
    results: list[dict[str, Any]] = []
    for tick, _key, path in iter_research_sessions(output_dir, include_legacy=True):
        if tick != t:
            continue
        results.extend(harvest_session_documents(t, path, output_dir=output_dir))
    informal = library_root(output_dir).parent / "research" / t / "source_materials"
    if informal.is_dir():
        for p in informal.rglob("*"):
            if not p.is_file():
                continue
            suf = p.suffix.lower()
            if suf in REFUSED_SUFFIXES or suf not in ALLOWED_SUFFIXES:
                continue
            try:
                results.append(
                    ingest_file(t, p, output_dir=output_dir, ingested_from="harvest")
                )
            except LibraryError as exc:
                results.append({"status": "error", "path": str(p), "detail": str(exc)})
    return results
