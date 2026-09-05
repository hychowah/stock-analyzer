"""List stored annual reports and decide whether year-dive gates apply.

Pure helpers for Phase 1c. No network. Never reads live archive except via
the session Path the caller passes (tests use tmpdirs).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# New-runtime floor: sessions stamped ≥ this must produce fdd_year_*.json.
YEAR_DIVE_SINCE = (2, 5, 0)

REQUIRED_YEAR_SECTIONS: tuple[str, ...] = (
    "business",
    "risk_factors",
    "legal",
    "md_and_a",
    "notes",
    "related_party",
)

_ANNUAL_FORM = re.compile(
    r"(10-?K|20-?F|40-?F|annual|integrated\s*report|yuho|(?:^|_|-)AR(?:_|-|$))",
    re.IGNORECASE,
)
_NOT_ANNUAL = re.compile(r"(10-?Q|8-?K|6-?K|tanshin|interim|quarter)", re.IGNORECASE)
_YEAR = re.compile(r"(?:FY)?((?:19|20)\d{2})", re.IGNORECASE)
_YEAR_DIVE_NAME = re.compile(r"fdd_year_(?:FY)?((?:19|20)\d{2})", re.IGNORECASE)


def parse_semver(raw: str | None) -> tuple[int, int, int] | None:
    if not raw:
        return None
    m = re.match(r"^\s*(\d+)\.(\d+)\.(\d+)", str(raw))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def normalize_fiscal_year(val: Any) -> int | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val if 1900 <= val <= 2100 else None
    if isinstance(val, float) and val.is_integer():
        iv = int(val)
        return iv if 1900 <= iv <= 2100 else None
    m = _YEAR.search(str(val))
    if not m:
        return None
    year = int(m.group(1))
    return year if 1900 <= year <= 2100 else None


def is_annual_form(form: str | None) -> bool:
    if not form:
        return False
    if _NOT_ANNUAL.search(form) and not _ANNUAL_FORM.search(form):
        return False
    if re.search(r"10-?Q", form, re.IGNORECASE):
        return False
    if re.search(r"8-?K", form, re.IGNORECASE):
        return False
    return bool(_ANNUAL_FORM.search(form))


def prefer_txt_rel(session: Path, rel: str) -> str:
    """Prefer a .txt sidecar next to HTML/PDF when it exists."""
    rel = rel.replace("\\", "/").lstrip("/")
    p = session / rel
    if p.suffix.lower() == ".txt" and p.is_file():
        return rel
    txt = p.with_suffix(".txt")
    if txt.is_file():
        try:
            return str(txt.relative_to(session)).replace("\\", "/")
        except ValueError:
            return rel
    # Sometimes both 10-K_2025.htm and 10-K_2025.txt exist with different stems
    if p.is_file() or True:
        alt = p.parent / (p.stem + ".txt")
        if alt.is_file():
            try:
                return str(alt.relative_to(session)).replace("\\", "/")
            except ValueError:
                return rel
    return rel


def _entry(
    *,
    fiscal_year: int | None,
    form: str,
    path: str,
    url: str | None = None,
    source: str,
) -> dict[str, Any]:
    return {
        "fiscal_year": fiscal_year,
        "form": form,
        "path": path,
        "url": url,
        "source": source,
    }


def list_annuals_from_index(sec_filings: dict[str, Any], session: Path | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    filings = sec_filings.get("filings") if isinstance(sec_filings, dict) else None
    if not isinstance(filings, list):
        return out
    for f in filings:
        if not isinstance(f, dict):
            continue
        form = str(f.get("form") or "")
        if not is_annual_form(form):
            continue
        path = str(f.get("path") or f.get("local_path") or "")
        if not path:
            continue
        year = normalize_fiscal_year(
            f.get("fiscal_year") or f.get("fiscal_period") or path
        )
        rel = prefer_txt_rel(session, path) if session is not None else path.replace("\\", "/")
        out.append(
            _entry(
                fiscal_year=year,
                form=form,
                path=rel,
                url=f.get("url"),
                source="sec_filings",
            )
        )
    return out


def list_annuals_from_filenames(raw_sec: Path) -> list[dict[str, Any]]:
    if not raw_sec.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(raw_sec.iterdir()):
        if not p.is_file():
            continue
        name = p.name
        if not is_annual_form(name):
            continue
        if p.suffix.lower() not in {".txt", ".htm", ".html", ".pdf"}:
            continue
        # Prefer .txt; skip html/pdf if txt sibling exists
        if p.suffix.lower() != ".txt" and (p.with_suffix(".txt")).is_file():
            continue
        year = normalize_fiscal_year(name)
        try:
            session = raw_sec.parent.parent  # data/raw_sec → session
            rel = str(p.relative_to(session)).replace("\\", "/")
        except ValueError:
            rel = f"data/raw_sec/{name}"
        out.append(_entry(fiscal_year=year, form=name, path=rel, source="raw_sec"))
    return out


def list_annuals(session: Path) -> list[dict[str, Any]]:
    """Deduped annuals: index first, then filename gaps."""
    by_year: dict[int | str, dict[str, Any]] = {}
    idx_path = session / "registry" / "sec_filings.json"
    if idx_path.is_file():
        try:
            data = json.loads(idx_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            for item in list_annuals_from_index(data, session):
                key: int | str = item["fiscal_year"] if item["fiscal_year"] is not None else item["path"]
                by_year[key] = item
    for item in list_annuals_from_filenames(session / "data" / "raw_sec"):
        key = item["fiscal_year"] if item["fiscal_year"] is not None else item["path"]
        if key not in by_year:
            by_year[key] = item
    items = list(by_year.values())
    items.sort(key=lambda x: (x["fiscal_year"] is None, x["fiscal_year"] or 0, x["path"]))
    return items


def year_dive_files(session: Path) -> list[Path]:
    raw = session / "registry" / "raw"
    if not raw.is_dir():
        return []
    return sorted(raw.glob("fdd_year_*.json"))


def fiscal_year_from_year_dive_path(path: Path) -> int | None:
    m = _YEAR_DIVE_NAME.search(path.name)
    return int(m.group(1)) if m else None


def load_run_manifest_version(session: Path) -> str | None:
    p = session / "meta" / "run_manifest.json"
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    ver = data.get("harness_version")
    if not ver:
        prov = data.get("provenance")
        if isinstance(prov, dict):
            ver = prov.get("harness_version")
    return str(ver) if ver else None


def session_enforces_year_dives(session: Path) -> bool:
    """True when year-dive completeness/excerpt gates apply.

    Enforce if any year-file already exists (must be valid) OR the session
    was stamped with harness_version ≥ 2.5.0. Legacy / slim fixtures skip.
    """
    if year_dive_files(session):
        return True
    from packages.kd_research.check_core import session_since

    return session_since(session, YEAR_DIVE_SINCE)


def check_1c_year_dive_complete(session: Path) -> list[tuple[str, str, str]]:
    """1c complete: FDD always; year-dives + excerpts only on new runtime."""
    from packages.kd_research.check_core import load_json
    from packages.kd_research.excerpt_check import check_year_dive_document, load_year_dive
    from packages.kd_research.gates import check_path

    out: list[tuple[str, str, str]] = []
    status, detail = check_path(session, "registry/filing_deep_dive.json")
    out.append((status, "registry/filing_deep_dive.json", detail))

    files = year_dive_files(session)
    enforce = session_enforces_year_dives(session)
    if not enforce and not files:
        out.append(
            (
                "SKIPPED",
                "1c_year_dives",
                "legacy/slim session (no fdd_year_*.json; harness_version < 2.5.0)",
            )
        )
        return out

    annuals = list_annuals(session)
    if not annuals:
        out.append(("FAIL", "1c_year_dives", "no annuals listed in sec_filings/raw_sec"))
        return out

    if not files:
        out.append(
            (
                "FAIL",
                "1c_year_dives",
                f"need registry/raw/fdd_year_*.json for {len(annuals)} annual(s)",
            )
        )
        return out

    years_have: set[int] = set()
    for yp in files:
        doc, err = load_year_dive(yp)
        rel = f"registry/raw/{yp.name}"
        if err or doc is None:
            out.append(("FAIL", rel, err or "unparseable"))
            continue
        out.extend(check_year_dive_document(session, doc, rel=rel))
        y = normalize_fiscal_year(doc.get("fiscal_year")) or fiscal_year_from_year_dive_path(yp)
        if y is not None:
            years_have.add(y)

    years_need = {a["fiscal_year"] for a in annuals if a.get("fiscal_year") is not None}
    missing_years = sorted(years_need - years_have)
    if missing_years:
        out.append(("FAIL", "1c_year_dives", f"missing year-dives for FY {missing_years}"))
    elif years_need:
        out.append(("PASS", "1c_year_dives", f"{len(files)} year-dive(s) cover {sorted(years_need)}"))

    fdd, fdd_err = load_json(session / "registry" / "filing_deep_dive.json")
    if fdd_err or not isinstance(fdd, dict):
        return out

    rechecks = fdd.get("verify_rechecks")
    if not isinstance(rechecks, list) or len(rechecks) < 3:
        out.append(
            (
                "FAIL",
                "1c_verify_rechecks",
                "need ≥3 verify_rechecks[] {path,value} on filing_deep_dive.json",
            )
        )
    else:
        bad = [
            i
            for i, r in enumerate(rechecks)
            if not (isinstance(r, dict) and r.get("path") and r.get("value") is not None)
        ]
        if bad:
            out.append(("FAIL", "1c_verify_rechecks", f"entries missing path/value: {bad}"))
        else:
            out.append(("PASS", "1c_verify_rechecks", f"{len(rechecks)} re-read(s)"))

    arc = fdd.get("strategy_arc") if isinstance(fdd.get("strategy_arc"), dict) else {}
    covered = {normalize_fiscal_year(y) for y in (arc.get("years_covered") or [])}
    covered.discard(None)
    if years_have and covered and covered != years_have:
        out.append(
            (
                "FAIL",
                "1c_years_covered",
                f"strategy_arc.years_covered={sorted(covered)} != year-dives {sorted(years_have)}",
            )
        )
    elif years_have and covered:
        out.append(("PASS", "1c_years_covered", f"{sorted(covered)}"))

    return out
