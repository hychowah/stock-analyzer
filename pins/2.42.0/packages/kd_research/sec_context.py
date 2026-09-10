"""Helpers to extract and chunk structured sections from SEC filing text.

The web-fetch MCP returns clean text, so we use heading-based regex splitting.
This module is intentionally dependency-light so it can be imported anywhere.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# Common headings in 10-K filings (case-insensitive, tolerant of unicode apostrophes and colons)
HEADING_PATTERNS: dict[str, list[str]] = {
    "business": [
        r"ITEM\s*1[.:\s]+BUSINESS",
        r"ITEM\s*1[.:\s]+Business",
        r"^BUSINESS$",
    ],
    "risk_factors": [
        r"ITEM\s*1A[.:\s]+RISK\s*FACTORS",
        r"ITEM\s*1A[.:\s]+Risk Factors",
        r"^RISK FACTORS$",
    ],
    "md_and_a": [
        r"ITEM\s*7[.:\s]+MANAGEMENT[’']S\s*DISCUSSION\s*AND\s*ANALYSIS",
        r"ITEM\s*7[.:\s]+Management[’']s Discussion and Analysis",
        r"MANAGEMENT[’']S\s*DISCUSSION\s*AND\s*ANALYSIS",
        r"^MD&A$",
    ],
    "financial_statements": [
        # Some filings insert the company name between the item number and the
        # "Financial Statements" phrase (e.g., "Item 8: Comcast Corporation
        # Financial Statements and Supplementary Data").
        r"ITEM\s*8[.:\s]+.*?FINANCIAL\s*STATEMENTS",
        r"ITEM\s*8[.:\s]+.*?Financial Statements",
    ],
    "notes": [
        r"NOTES\s*TO\s*CONSOLIDATED\s*FINANCIAL\s*STATEMENTS",
        r"NOTES\s*TO\s*FINANCIAL\nSTATEMENTS",
    ],
}

# Quarterly filing headings
QUARTERLY_HEADINGS: dict[str, list[str]] = {
    "md_and_a": [
        r"ITEM\s*2[.:\s]+MANAGEMENT[’']S\s*DISCUSSION\s*AND\s*ANALYSIS",
        r"ITEM\s*2[.:\s]+Management[’']s Discussion and Analysis",
        r"MANAGEMENT[’']S\s*DISCUSSION\s*AND\s*ANALYSIS",
    ],
    "risk_factors": [
        r"ITEM\s*1A[.:\s]+RISK\s*FACTORS",
        r"ITEM\s*1A[.:\s]+Risk Factors",
    ],
    "financial_statements": [
        r"ITEM\s*1[.:\s]+FINANCIAL\s*STATEMENTS",
        r"ITEM\s*1[.:\s]+Financial Statements",
    ],
}

# For each section, the set of ITEM numbers that may legitimately follow it in
# a well-ordered filing. This lets us skip table-of-contents entries and stray
# cross-references that happen to contain the heading text.
EXPECTED_NEXT: dict[str, dict[str, set[str]]] = {
    "10-K": {
        "business": {"1A", "1B", "2"},
        "risk_factors": {"1B", "2"},
        "md_and_a": {"7A", "8"},
        "financial_statements": {"9", "9A", "9B", "9C", "10", "11", "12", "13", "14", "15", "16"},
        "notes": set(),  # notes usually run to the end of the document
    },
    "10-Q": {
        "risk_factors": {"2", "3", "4", "6"},
        "md_and_a": {"3", "4"},
        "financial_statements": {"2", "3"},
    },
}


def _section_end_pattern() -> re.Pattern:
    """Pattern that marks the end of a section: next ITEM, PART, signature page, or exhibit index.

    The match ends right after the item number/label so it works for headings
    that continue with descriptive text on the same line (e.g.,
    "Item 1A: Risk Factors ...").
    """
    # PART must be a real form-part heading (PART I / PART II), not words like
    # "Parties", "Participation", or "Partial" that appear mid-section.
    return re.compile(
        r"(?:^|\n)\s*(ITEM\s*\d+[A-Z]?[.:\s]|PART\s+[IVXLC\d]+\b|SIGNATURES|EXHIBIT\s*INDEX)",
        re.IGNORECASE,
    )


def _extract_item_number(end_match_text: str) -> str | None:
    """Pull the ITEM number (e.g. '1A', '7') from a section-end match."""
    m = re.search(r"ITEM\s*(\d+[A-Z]?)[.:\s]", end_match_text, re.IGNORECASE)
    return m.group(1).upper() if m else None


def _find_section_start(text: str, patterns: list[str], section: str, form_type: str) -> int | None:
    """Return the best character index where a section starts, or None.

    Filings often repeat headings inside a table of contents and later as
    cross-references. We evaluate every heading match and prefer the one whose
    following boundary is a plausible next ITEM for that section and whose body
    is substantial. Falls back to the longest body if no match has a plausible
    next ITEM.
    """
    end_pat = _section_end_pattern()
    expected = EXPECTED_NEXT.get(form_type, {}).get(section, set())

    best_plausible_start: int | None = None
    best_plausible_len = 0
    best_any_start: int | None = None
    best_any_len = 0

    for pat in patterns:
        for match in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
            start = match.start()
            remaining = text[match.end() :]
            end_match = end_pat.search(remaining)
            length = end_match.start() if end_match else len(remaining)

            if length <= 200:
                continue  # TOC entry

            if length > best_any_len:
                best_any_len = length
                best_any_start = start

            if expected and end_match:
                next_item = _extract_item_number(end_match.group(1))
                if next_item in expected and length > best_plausible_len:
                    best_plausible_len = length
                    best_plausible_start = start

    return best_plausible_start if best_plausible_start is not None else best_any_start


def extract_section(text: str, section: str, form_type: str = "10-K") -> str | None:
    """Extract a named section from filing text.

    Args:
        text: Clean filing text from web-fetch.
        section: One of the keys in HEADING_PATTERNS or QUARTERLY_HEADINGS.
        form_type: "10-K" or "10-Q" (selects heading set).

    Returns:
        The extracted section text, trimmed, or None if not found.
    """
    if not text:
        return None

    headings = HEADING_PATTERNS if form_type == "10-K" else QUARTERLY_HEADINGS
    if section not in headings:
        return None

    start = _find_section_start(text, headings[section], section, form_type)
    if start is None:
        return None

    # Search for the next major heading after the matched section start.
    remaining = text[start + 1 :]
    end_match = _section_end_pattern().search(remaining)
    if end_match:
        end = start + 1 + end_match.start()
    else:
        end = len(text)

    return text[start:end].strip()


def chunk_text(text: str, max_chars: int = 12000, overlap: int = 500) -> list[str]:
    """Split text into overlapping chunks for subagent context windows."""
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Try to break at a paragraph boundary.
        if end < len(text):
            paragraph_break = text.rfind("\n\n", start, end)
            if paragraph_break > start + max_chars // 2:
                end = paragraph_break
        chunks.append(text[start:end].strip())
        start = end - overlap
        if start <= chunks[-1].__len__() and len(chunks) > 1:
            # Avoid infinite loop on tiny overlap.
            start = end
    return chunks


@dataclass
class FilingContext:
    """Structured context extracted from a single filing."""

    ticker: str
    form: str
    fiscal_year: int | None
    fiscal_period: str | None
    filing_date: str | None
    url: str | None
    business: str | None
    risk_factors: str | None
    md_and_a: str | None
    financial_statements: str | None
    notes: str | None
    raw_headings: list[str] | None = None


def extract_all_sections(text: str, ticker: str, form: str, metadata: dict[str, Any] | None = None) -> FilingContext:
    """Extract all known sections from a filing and return a FilingContext."""
    meta = metadata or {}
    form_type = "10-K" if "10-K" in form else ("10-Q" if "10-Q" in form else "other")

    # Grab a list of detected headings for debugging.
    raw_headings = re.findall(r"^\s*(ITEM\s*\d+[A-Z]?[.\s]+[A-Z][A-Z\s&,’'\-]+)\s*$", text, re.IGNORECASE | re.MULTILINE)

    return FilingContext(
        ticker=ticker,
        form=form,
        fiscal_year=meta.get("fiscal_year"),
        fiscal_period=meta.get("fiscal_period"),
        filing_date=meta.get("filing_date"),
        url=meta.get("url"),
        business=extract_section(text, "business", form_type),
        risk_factors=extract_section(text, "risk_factors", form_type),
        md_and_a=extract_section(text, "md_and_a", form_type),
        financial_statements=extract_section(text, "financial_statements", form_type),
        notes=extract_section(text, "notes", form_type),
        raw_headings=raw_headings,
    )


def context_to_dict(ctx: FilingContext) -> dict[str, Any]:
    """Serialize a FilingContext to a plain dict for JSON storage."""
    return {
        "ticker": ctx.ticker,
        "form": ctx.form,
        "fiscal_year": ctx.fiscal_year,
        "fiscal_period": ctx.fiscal_period,
        "filing_date": ctx.filing_date,
        "url": ctx.url,
        "sections": {
            "business": ctx.business,
            "risk_factors": ctx.risk_factors,
            "md_and_a": ctx.md_and_a,
            "financial_statements": ctx.financial_statements,
            "notes": ctx.notes,
        },
        "raw_headings": ctx.raw_headings,
    }


def cap_context(ctx: FilingContext, per_section_chars: int = 6000, total_chars: int = 20000) -> FilingContext:
    """Truncate extracted sections in place so a filing context stays context-safe.

    sec_filings.json is read in full by downstream subagents; without a cap a
    single 10-K can exceed 100k chars per section. Truncated sections get a
    marker so readers know there is more on disk.
    """
    sections = ["business", "risk_factors", "md_and_a", "financial_statements", "notes"]
    remaining = total_chars
    for name in sections:
        text = getattr(ctx, name)
        if not text:
            continue
        budget = min(per_section_chars, max(remaining, 1000))
        if len(text) > budget:
            setattr(ctx, name, text[:budget] + f"\n[... truncated at {budget} chars; full text not stored ...]")
        remaining -= min(len(text), budget)
    return ctx
