"""Targeted extraction of financial-statement notes from SEC filing text.

Pure helpers for Agent 2e / offline tests. Full filing text should live under
session ``data/raw_sec/``; this module never fetches the network.
"""

from __future__ import annotations

import re
from typing import Any

# Default standard/growth footnote checklist ids → keyword patterns for note titles.
NOTE_CHECKLIST: dict[str, list[str]] = {
    "revenue_disaggregation": [
        r"revenue",
        r"disaggregation",
        r"revenue\s+from\s+contracts",
    ],
    "segment": [
        r"segment",
        r"segment\s+information",
    ],
    "sbc_unrecognized": [
        r"stock[- ]based\s+compensation",
        r"share[- ]based\s+payment",
        r"equity\s+incentive",
    ],
    "debt_leases": [
        r"\bdebt\b",
        r"long[- ]term\s+debt",
        r"\bleases?\b",
        r"borrowings",
    ],
    "contingencies_legal": [
        r"contingen",
        r"commitments\s+and\s+contingen",
        r"legal\s+proceed",
        r"litigation",
    ],
    "income_taxes": [
        r"income\s+taxes?",
        r"\btaxes?\b",
    ],
    "capex_commitments": [
        r"commitments",
        r"purchase\s+obligations?",
        r"capital\s+commitments?",
    ],
    "related_party_dual_class": [
        r"related[- ]party",
        r"stockholders[’']?\s+equity",
        r"common\s+stock",
        r"dual[- ]class",
    ],
}

# Match "Note 2." / "NOTE 13 —" style headings at line starts.
_NOTE_HEADING = re.compile(
    r"(?m)^[ \t]*(?:Note|NOTE)\s+(\d+[A-Za-z]?)[ \t]*[.:\-—–][ \t]*(.+?)\s*$"
)

# Item 3 legal proceedings (10-K) — often denser than contingency note alone.
_ITEM3 = re.compile(
    r"(?is)(?:^|\n)\s*ITEM\s*3[.:\s]+LEGAL\s+PROCEEDINGS\b(.*?)(?=(?:\n\s*ITEM\s*\d)|\Z)"
)


def split_notes(text: str) -> list[dict[str, Any]]:
    """Split notes section (or full filing) into ordered note bodies.

    Returns a list of ``{number, title, body, start, end}`` where body excludes
    the heading line. If no note headings are found, returns an empty list.
    """
    if not text:
        return []

    matches = list(_NOTE_HEADING.finditer(text))
    if not matches:
        return []

    notes: list[dict[str, Any]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end() : end].strip()
        notes.append(
            {
                "number": m.group(1),
                "title": m.group(2).strip(),
                "body": body,
                "start": start,
                "end": end,
                "full_text": text[start:end].strip(),
            }
        )
    return notes


def _title_matches(title: str, patterns: list[str]) -> bool:
    t = title.lower()
    return any(re.search(p, t, re.IGNORECASE) for p in patterns)


def find_notes_for_checklist(
    text: str,
    checklist: dict[str, list[str]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Map checklist ids to matching notes (may be multiple per id)."""
    cl = checklist or NOTE_CHECKLIST
    notes = split_notes(text)
    out: dict[str, list[dict[str, Any]]] = {k: [] for k in cl}
    for note in notes:
        for cid, patterns in cl.items():
            if _title_matches(note["title"], patterns):
                out[cid].append(note)
    return out


def excerpt(text: str, max_chars: int = 800) -> str:
    """Trim to max_chars on a word/paragraph boundary when possible."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    br = max(cut.rfind("\n\n"), cut.rfind(". "), cut.rfind(" "))
    if br > max_chars // 2:
        cut = cut[: br + 1]
    return cut.rstrip() + " […]"


def extract_item3_legal(text: str, max_chars: int = 800) -> dict[str, Any] | None:
    """Extract Item 3 Legal Proceedings body if present."""
    if not text:
        return None
    m = _ITEM3.search(text)
    if not m:
        return None
    body = m.group(1).strip()
    return {
        "id": "item3_legal_proceedings",
        "title": "Item 3. Legal Proceedings",
        "body": body,
        "excerpt": excerpt(body, max_chars),
    }


def build_footnote_items(
    text: str,
    *,
    form: str = "10-K",
    fiscal_year: int | str | None = None,
    path: str = "",
    url: str | None = None,
    checklist: dict[str, list[str]] | None = None,
    max_excerpt: int = 800,
) -> list[dict[str, Any]]:
    """Build structured footnote checklist items for ``filing_deep_dive.json``.

    Status is ``extracted`` when at least one note matches, else ``missing``.
    Contingencies also try Item 3 when the contingency note is absent.
    """
    cl = checklist or NOTE_CHECKLIST
    matched = find_notes_for_checklist(text, cl)
    items: list[dict[str, Any]] = []

    for cid, patterns in cl.items():
        hits = matched.get(cid) or []
        if hits:
            primary = hits[0]
            note_label = f"Note {primary['number']}"
            body = primary["full_text"]
            # Prefer body after title for excerpt density
            ex = excerpt(primary["body"] or body, max_excerpt)
            items.append(
                {
                    "id": cid,
                    "status": "extracted",
                    "title": primary["title"],
                    "value": {
                        "note_number": primary["number"],
                        "note_title": primary["title"],
                        "match_count": len(hits),
                    },
                    "excerpt": ex,
                    "source": {
                        "form": form,
                        "fiscal_year": fiscal_year,
                        "note": note_label,
                        "path": path,
                        "url": url,
                    },
                    "downstream_use": _default_downstream(cid),
                }
            )
            continue

        # Fallback: legal from Item 3
        if cid == "contingencies_legal":
            item3 = extract_item3_legal(text, max_excerpt)
            if item3:
                items.append(
                    {
                        "id": cid,
                        "status": "extracted",
                        "title": item3["title"],
                        "value": {"from": "item_3"},
                        "excerpt": item3["excerpt"],
                        "source": {
                            "form": form,
                            "fiscal_year": fiscal_year,
                            "note": "Item 3",
                            "path": path,
                            "url": url,
                        },
                        "downstream_use": _default_downstream(cid),
                    }
                )
                continue

        items.append(
            {
                "id": cid,
                "status": "missing",
                "title": cid,
                "value": None,
                "excerpt": None,
                "source": {
                    "form": form,
                    "fiscal_year": fiscal_year,
                    "note": None,
                    "path": path,
                    "url": url,
                },
                "downstream_use": _default_downstream(cid),
            }
        )

    return items


def _default_downstream(cid: str) -> str:
    return {
        "revenue_disaggregation": "growth|context",
        "segment": "sotp|context",
        "sbc_unrecognized": "dilution",
        "debt_leases": "capital_structure",
        "contingencies_legal": "risk",
        "income_taxes": "tax",
        "capex_commitments": "capital_structure",
        "related_party_dual_class": "context",
    }.get(cid, "context")


def parse_guidance_outlook_block(text: str) -> list[dict[str, str]]:
    """Heuristic pull of outlook/guidance lines from an earnings release or MD&A.

    Returns list of ``{line, kind}`` where kind is a best-effort class tag.
    Not a substitute for agent judgment — a starting slice for scorecards.
    """
    if not text:
        return []

    # Focus on Outlook / guidance windows when present.
    window = text
    m = re.search(
        r"(?is)(CFO\s+Outlook|Outlook\s+Commentary|Full\s+Year\s+\d{4}\s+Outlook|"
        r"we\s+(?:now\s+)?expect|guidance)(.{0,8000})",
        text,
    )
    if m:
        window = m.group(0)

    lines_out: list[dict[str, str]] = []
    for raw in window.splitlines():
        line = " ".join(raw.split()).strip()
        if len(line) < 20:
            continue
        low = line.lower()
        if not any(
            k in low
            for k in (
                "expect",
                "outlook",
                "guidance",
                "between",
                "range",
                "approximately",
                "will be",
                "capex",
                "capital expenditure",
                "revenue",
                "expense",
            )
        ):
            continue
        kind = "other"
        if "capex" in low or "capital expenditure" in low:
            kind = "capex"
        elif "revenue" in low:
            kind = "revenue"
        elif "expense" in low or "opex" in low or "operating expense" in low:
            kind = "opex"
        elif "margin" in low:
            kind = "margin"
        elif "repurchase" in low or "buyback" in low or "dividend" in low:
            kind = "capital_returns"
        lines_out.append({"line": line[:500], "kind": kind})
    return lines_out
