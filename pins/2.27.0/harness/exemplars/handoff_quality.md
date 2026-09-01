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
- Wrote `registry/sec_filings.json` (index capped ~20k/filing). Bind already had unique-FY FY2023–FY2025 annuals + two interims as `.txt` under `data/raw_sec/`; did not re-download those.
- `session_missing` was the latest 8-K exhibit; fetched that only via sec-edgar MCP; write-through ingest from the session path. Left `library_gaps` (older years) in the corpus.
- Stored latest earnings supplement uncapped at `data/latest_supplement.txt`.
- Freshness in `registry/data_fetch_log.json` (`checked_at`, `index_source`, `session_missing`, `fetched_new`).

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

---

## Pair 2 — Downstream actions vs hollow “looks fine”

### Context (shared)

Valuation agent finished; scorecard lacked transcripts; intensity medium; one peer KPI missing.

### BAD

```markdown
# 5_valuation

## What I did
- Built DCF, wrote valuation_model.json

## Data issues & gaps
- none

## Assumptions & deviations
- Used standard WACC

## For downstream agents & the auditor
- Reports can use the model
```

**Why bad:** Schema-valid session may still be investment-toxic: hides missing transcripts (should widen range), empty downstream actions, no paths, “standard WACC” without basis. Next agents and auditor cannot see softness.

### GOOD

```markdown
# 5_valuation

## What I did
- Wrote `data/valuation_model.json` + `data/compute/valuation.py` (rerun reproduces base FV).
- Logged `filing_deep_dive_hooks` (12) and `market_context_hooks` (intensity medium → local Rf + FX policy used).
- Applied two latest_quarter overrides (guidance_change; capital buyback).

## Data issues & gaps
- Scorecard `data_quality=degraded_no_transcripts` — **widened** bear/base FV range in model; do not treat guide credibility as high-precision.
- Peer NIM for PEER_X missing from peer_comparison.csv; used filing excerpt path in hooks basis instead.

## Assumptions & deviations
- Rejected region-module family-control discount (ownership is widely held) — see market_context_hooks rejected row.

## For downstream agents & the auditor
- **Agent 7:** restate hooks that moved WACC and terminal margin; cite `data/compute/valuation_result.json` for FV grid — do not re-type chat numbers.
- **Phase 2.5:** open risk from deep-dive contingencies note (status=partial) — add or explicitly drop.
- **Auditor:** rerun `data/compute/valuation.py`; check MOS sign vs price in model; verify ≥3 footnote figures against raw_sec paths in hooks.
```

**Why good:** Top miss-nots, range-widen triggers, authoritative paths — next phase can act without re-researching.
