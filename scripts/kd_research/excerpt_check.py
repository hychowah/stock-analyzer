"""Whitespace-tolerant excerpt-in-source checks for year-dive JSON.

Used before Agent 2e merge and by check_session / 1c complete-mode.
Does not fetch the network. Session paths only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.kd_research.annuals import REQUIRED_YEAR_SECTIONS

_WS = re.compile(r"\s+")


def fold_ws(text: str) -> str:
    return _WS.sub(" ", (text or "")).strip().lower()


def excerpt_in_text(excerpt: str | None, source: str) -> bool:
    """True when excerpt is a whitespace-tolerant substring of source."""
    if excerpt is None:
        return True
    needle = fold_ws(str(excerpt))
    if len(needle) < 8:
        return False
    hay = fold_ws(source)
    if needle in hay:
        return True
    # Allow a slightly shortened needle (ellipsis / cap at 800)
    clipped = needle[:120].rstrip(".[…")
    return len(clipped) >= 8 and clipped in hay


def _read_source(session: Path, rel: str) -> tuple[str | None, str | None]:
    rel = (rel or "").replace("\\", "/").lstrip("/")
    if not rel:
        return None, "empty path"
    p = session / rel
    if not p.is_file():
        txt = p.with_suffix(".txt")
        if txt.is_file():
            p = txt
        else:
            return None, f"missing source {rel}"
    try:
        return p.read_text(encoding="utf-8", errors="replace"), None
    except OSError as exc:
        return None, f"unreadable {rel}: {exc}"


def _iter_excerpts(doc: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return (label, excerpt, source_rel) for every citable snippet."""
    out: list[tuple[str, str, str]] = []
    default_path = str(doc.get("path") or "")
    footnotes = doc.get("footnotes") if isinstance(doc.get("footnotes"), dict) else {}
    items = footnotes.get("items") if isinstance(footnotes, dict) else None
    if isinstance(items, list):
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            ex = item.get("excerpt")
            if not ex:
                continue
            src = default_path
            source = item.get("source")
            if isinstance(source, dict) and source.get("path"):
                src = str(source["path"])
            out.append((f"footnotes.items[{i}].excerpt", str(ex), src))
    for i, fig in enumerate(doc.get("key_figures") or []):
        if not isinstance(fig, dict):
            continue
        ex = fig.get("excerpt")
        if not ex:
            continue
        src = str(fig.get("source_path") or default_path)
        out.append((f"key_figures[{i}].excerpt", str(ex), src))
    for i, p in enumerate(doc.get("outlook_promises") or []):
        if not isinstance(p, dict):
            continue
        ex = p.get("excerpt")
        if not ex:
            continue
        out.append((f"outlook_promises[{i}].excerpt", str(ex), default_path))
    return out


def check_year_dive_document(
    session: Path,
    doc: dict[str, Any],
    *,
    rel: str = "",
) -> list[tuple[str, str, str]]:
    """Structural + excerpt-in-source rows for one year-dive dict."""
    rows: list[tuple[str, str, str]] = []
    label = rel or "year_dive"

    walked = doc.get("sections_walked")
    if not isinstance(walked, list):
        rows.append(("FAIL", f"{label}:sections_walked", "missing list"))
    else:
        walked_l = {str(x).lower() for x in walked}
        missing = [s for s in REQUIRED_YEAR_SECTIONS if s not in walked_l]
        if missing:
            rows.append(("FAIL", f"{label}:sections_walked", f"missing {missing}"))
        else:
            rows.append(("PASS", f"{label}:sections_walked", f"{len(walked)} section(s)"))

    figs = doc.get("key_figures")
    if not isinstance(figs, list) or len(figs) < 1:
        rows.append(("FAIL", f"{label}:key_figures", "need ≥1 key_figure"))
    else:
        rows.append(("PASS", f"{label}:key_figures", f"{len(figs)} figure(s)"))

    footnotes = doc.get("footnotes") if isinstance(doc.get("footnotes"), dict) else {}
    items = footnotes.get("items") if isinstance(footnotes, dict) else None
    if not isinstance(items, list) or len(items) < 1:
        rows.append(("FAIL", f"{label}:footnotes.items", "need non-empty items[]"))
    else:
        rows.append(("PASS", f"{label}:footnotes.items", f"{len(items)} item(s)"))

    cache: dict[str, tuple[str | None, str | None]] = {}
    excerpt_fail = 0
    excerpt_ok = 0
    for loc, excerpt, src_rel in _iter_excerpts(doc):
        if src_rel not in cache:
            cache[src_rel] = _read_source(session, src_rel)
        text, err = cache[src_rel]
        if err:
            rows.append(("FAIL", f"{label}:{loc}", err))
            excerpt_fail += 1
            continue
        if excerpt_in_text(excerpt, text or ""):
            excerpt_ok += 1
        else:
            rows.append(("FAIL", f"{label}:{loc}", f"excerpt not found in {src_rel}"))
            excerpt_fail += 1
    if excerpt_fail == 0 and excerpt_ok:
        rows.append(("PASS", f"{label}:excerpts", f"{excerpt_ok} matched"))
    elif excerpt_ok == 0 and excerpt_fail == 0:
        rows.append(("FAIL", f"{label}:excerpts", "no excerpts to verify"))
    return rows


def load_year_dive(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "not an object"
    return data, None
