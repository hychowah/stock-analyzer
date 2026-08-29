"""Readonly change fingerprints for SSE / poll (no DB writes)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from apps.analysis_web.config import archive_root, local_dir


def _stat_tuple(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
    except OSError:
        return None
    # mtime_ns + size is enough for local catalog rebuild / finalize patches
    return (int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))), int(st.st_size))


def catalog_paths(root: Path | None = None) -> dict[str, Path]:
    ar = root or archive_root()
    catalog = ar / "catalog"
    return {
        "sqlite": catalog / "research_compare.sqlite",
        "sqlite_wal": catalog / "research_compare.sqlite-wal",
        "runs_index": catalog / "runs_index.json",
        "tickers_index": catalog / "tickers_index.json",
        "schema_version": catalog / "schema_version",
    }


def portfolio_path() -> Path:
    return local_dir() / "portfolio.json"


def fingerprint(*, root: Path | None = None) -> dict[str, Any]:
    """Return a JSON-serializable fingerprint of catalog (+ optional portfolio book)."""
    ar = root or archive_root()
    parts: list[str] = [f"archive_root={ar}"]
    for name, path in catalog_paths(ar).items():
        st = _stat_tuple(path)
        if st is None:
            parts.append(f"{name}=missing")
        else:
            parts.append(f"{name}={st[0]}:{st[1]}")

    book = portfolio_path()
    book_st = _stat_tuple(book)
    if book_st is None:
        parts.append("portfolio=missing")
    else:
        parts.append(f"portfolio={book_st[0]}:{book_st[1]}")

    comparisons = ar / "comparisons"
    if not comparisons.is_dir():
        parts.append("comparisons=missing")
    else:
        n = 0
        for ticker_dir in comparisons.iterdir():
            if not ticker_dir.is_dir():
                continue
            for packet in ticker_dir.iterdir():
                job = packet / "job.json"
                st = _stat_tuple(job)
                if st is None:
                    continue
                parts.append(f"compare:{ticker_dir.name}:{packet.name}={st[0]}:{st[1]}")
                n += 1
                if n >= 200:
                    break
            if n >= 200:
                break
        if n == 0:
            parts.append("comparisons=empty")

    jobs_root = ar / "research_jobs"
    if not jobs_root.is_dir():
        parts.append("research_jobs=missing")
    else:
        n = 0
        for ticker_dir in jobs_root.iterdir():
            if not ticker_dir.is_dir() or ticker_dir.name.startswith("."):
                continue
            for packet in ticker_dir.iterdir():
                if not packet.is_dir():
                    continue
                job = packet / "job.json"
                st = _stat_tuple(job)
                if st is not None:
                    parts.append(f"analyze:{ticker_dir.name}:{packet.name}={st[0]}:{st[1]}")
                    n += 1
                phase = (
                    ar / "research" / ticker_dir.name / packet.name / "registry" / "phase_status.json"
                )
                pst = _stat_tuple(phase)
                if pst is not None:
                    parts.append(f"phase:{ticker_dir.name}:{packet.name}={pst[0]}:{pst[1]}")
                if n >= 200:
                    break
            if n >= 200:
                break
        if n == 0:
            parts.append("research_jobs=empty")

    blob = "|".join(parts)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
    return {
        "token": digest,
        "archive_root": str(ar),
        "catalog_db_exists": (ar / "catalog" / "research_compare.sqlite").is_file(),
        "portfolio_exists": book.is_file(),
        "parts": parts,
    }


def fingerprint_token(*, root: Path | None = None) -> str:
    return str(fingerprint(root=root)["token"])


def classify_change(prev: dict[str, Any] | None, cur: dict[str, Any]) -> list[str]:
    """Which high-level sources changed between two fingerprints."""
    if prev is None:
        return []
    prev_parts = {p.split("=", 1)[0]: p for p in prev.get("parts") or []}
    cur_parts = {p.split("=", 1)[0]: p for p in cur.get("parts") or []}
    events: list[str] = []
    catalog_keys = {
        "sqlite",
        "sqlite_wal",
        "runs_index",
        "tickers_index",
        "schema_version",
    }
    if any(prev_parts.get(k) != cur_parts.get(k) for k in catalog_keys):
        events.append("catalog_changed")
    if prev_parts.get("portfolio") != cur_parts.get("portfolio"):
        events.append("portfolio_changed")
    compare_keys = set()
    for k in list(prev_parts.keys()) + list(cur_parts.keys()):
        if k == "comparisons" or k.startswith("compare:"):
            compare_keys.add(k)
    if any(prev_parts.get(k) != cur_parts.get(k) for k in compare_keys):
        events.append("compare_changed")
    analyze_keys = set()
    for k in list(prev_parts.keys()) + list(cur_parts.keys()):
        if k == "research_jobs" or k.startswith("analyze:") or k.startswith("phase:"):
            analyze_keys.add(k)
    if any(prev_parts.get(k) != cur_parts.get(k) for k in analyze_keys):
        events.append("analyze_changed")
    if not events and prev.get("token") != cur.get("token"):
        events.append("catalog_changed")
    return events


def dump_fingerprint(fp: dict[str, Any]) -> str:
    """Compact SSE data payload (omit verbose parts)."""
    return json.dumps(
        {
            "token": fp.get("token"),
            "catalog_db_exists": fp.get("catalog_db_exists"),
            "portfolio_exists": fp.get("portfolio_exists"),
        },
        separators=(",", ":"),
    )
