"""Forbidden-citation scans: Agent 4 vs fundamentals, and cross-session paths.

Library path citations stay in library.py.
"""

from __future__ import annotations

from pathlib import Path

# Path-anchored tokens: avoid bare English false positives (e.g. "background").
AGENT4_FORBIDDEN_TOKENS = (
    "filing_deep_dive",
    "fdd_year",
    "valuation_model",
    "registry/background",
    "background.json",
    "latest_quarter",
    "market_context.json",
    "sec_filings",
    "sp_financials",
    "operating_path_brief",
    "oppath_",
    "revenue_growth.json",
    "industry_trend.json",
    "operating_leverage.json",
    "street_estimates",
    "street_bind",
    "archive/library",
    "library_bind",
    "tsr_validation",
)


def check_agent4_isolation(session: Path, *, full: bool = False) -> list[tuple[str, str, str]]:
    """Post-hoc: technical artifact/handoff must not cite fundamental session paths."""
    texts: list[tuple[str, str]] = []
    tech = session / "registry" / "technical.json"
    if tech.exists():
        try:
            texts.append(
                (str(tech.relative_to(session)), tech.read_text(encoding="utf-8", errors="replace"))
            )
        except OSError as e:
            return [("FAIL", "agent4_isolation", f"cannot read technical.json: {e}")]
    handoff_dir = session / "registry" / "handoffs"
    if handoff_dir.is_dir():
        for p in sorted(handoff_dir.glob("4*.md")):
            try:
                texts.append(
                    (str(p.relative_to(session)), p.read_text(encoding="utf-8", errors="replace"))
                )
            except OSError:
                continue
    if not texts:
        return [("SKIPPED", "agent4_isolation", "no technical.json or handoffs/4*.md")]

    hits: list[str] = []
    for rel, text in texts:
        lower = text.lower()
        for tok in AGENT4_FORBIDDEN_TOKENS:
            if tok.lower() in lower:
                hits.append(f"{rel}:{tok}")
    if not hits:
        return [("PASS", "agent4_isolation", f"scanned {len(texts)} file(s)")]
    detail = "; ".join(hits[:12])
    status = "FAIL" if full else "WARN"
    return [(status, "agent4_isolation", detail)]
