# Handoff quality exemplars

Purpose: teach the four-section handoff as soft-state (where it is soft), not a second essay.  
Used by: every agent.  
**ILLUSTRATIVE.**

---

## Pair 1 — Data agent handoff (2b-style)

### Context (shared)

SEC/local filings agent got 3 annuals + 2 interims; one prior-year annual download failed; supplement stored uncapped.

### BAD

```markdown
# 2b_sec_filings

## What I did
- Fetched filings

## Data issues & gaps
- none

## Assumptions & deviations
- none

## For downstream agents & the auditor
- Look at sec_filings.json
```

**Why bad:** Claims “none” on gaps while a year is missing. No paths, no fallback, no warning for 2e strategy_arc coverage. Downstream will under-widen uncertainty.

### GOOD

```markdown
# 2b_sec_filings

## What I did
- Wrote `registry/sec_filings.json` (index capped ~20k/filing) and hermetic copies under `data/raw_sec/` for FY2023–FY2025 annuals + last two interims.
- Stored latest earnings supplement uncapped at `data/latest_supplement.txt`.
- Primary source: sec-edgar MCP; logged tool timeouts in `registry/data_fetch_log.json`.

## Data issues & gaps
- FY2022 annual primary text **failed** (MCP timeout ×2). Fallback: none usable. Strategy arc for 2e will be 3 years (2023–2025) only — mark coverage partial if 2e expects ≥3 *prior* arcs including 2022.
- Item 1A risk-factor full text truncated in index by design; full text remains in raw_sec HTML.

## Assumptions & deviations
- Treated HK/20-F-style annual as primary where `market_context.listing.primary_filing_source` said so (did not force EDGAR-only).
- Did not invent EX-99.1 outlook text for years without exhibits.

## For downstream agents & the auditor
- **2e:** start from `data/raw_sec/*FY2023*`…; do not assume FY2022 on disk.
- **2d:** prefer `data/latest_supplement.txt` over capped MD&A for KPI tables.
- **Auditor:** re-check ≥3 footnote figures against raw_sec paths listed in sec_filings sources.
```

**Why good:** Concrete paths, honest gaps, named downstream impacts. Softness is visible without re-dumping the filing.
