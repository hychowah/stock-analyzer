# Filing deep dive — methodology (advisory)

Agent **2e** produces `registry/filing_deep_dive.json`. This note is advisory methodology (like sector modules): follow the schema and AGENTS.md §10b; adapt checklist items when a sector needs extra notes.

## Goals

1. Mine **footnotes / notes** that statement CSVs omit (SBC unrecognized, geo mix, debt maturities, contingencies).
2. Track **strategy alignment over multiple years** (typically ≥3 annual reports).
3. Score **whether management kept their word** using **SEC filings first** and **earnings-call transcripts second**.

## What not to do

- Do not raise `sec_filings.json` caps to dump full 10-Ks into every agent.
- Do not invent transcript quotes when IR/transcript hosts fail — mark `missing` and degrade scorecard quality.
- Do not auto-map hit-rate → WACC or probabilities. Valuation **reads** the deep dive and judges.

## Footnotes

Prefer `scripts/kd_research/note_extract.py`:

- `split_notes` / `find_notes_for_checklist` / `build_footnote_items` on annual report text in `data/raw_sec/`.
- Default checklist (standard/growth): revenue disaggregation, segment, SBC, debt/leases, contingencies/legal (Item 3 fallback), income taxes, commitments, related-party/dual-class.
- Each item must be `extracted`, `missing`, `partial`, or `not_applicable`.
- When `registry/market_context.json` has `ownership.complexity` medium/high or `intensity` high (family, SOE, VIE, pyramid, dual-class), enrich related-party/dual-class with stakes and structures from the filings; note accounting-regime peer traps when non-US GAAP. Market context does **not** auto-set WACC — valuation still judges via `market_context_hooks`.

## Strategy arc

From Item 1 + MD&A priority/outlook language across stored annuals:

- Priorities by year with filing path basis and short excerpts.
- Continuity score in \([0,1]\) with rationale/basis.
- Pivot flags and capital-allocation story.
- `implied_model_hooks` for Agent 5 (horizon, reinvestment, segment treatment).

## Management scorecard

1. Collect promises from prior EX-99.1 outlooks, MD&A, and (secondary) transcripts.
2. Join to actuals via `scripts/kd_research/promise_vs_actual.py` when numeric.
3. Label every row `source_type`: `filing` | `transcript` | `filing+transcript`.
4. Soft vision milestones → `too_early` / narrative shift — no false precision.
5. `credibility_summary` states pattern + `valuation_implication` for Agent 5/2.5 (widen range, raise bear weight, trust guides more, etc.).

## Transcripts

- Store under `data/transcripts/`.
- Secondary to filings on conflicts.
- Missing transcripts → explicit gap + wider uncertainty, not fabricated color.

## Downstream

| Consumer | Duty |
|---|---|
| Agent 5 | `filing_deep_dive_hooks` use or reject |
| Phase 2.5 | Legal/contingency from footnotes before web $ |
| Agent 7 | Non-stub footnotes / strategy / track-record sections |
| Agent 13 | ≥3 footnote figures vs `raw_sec`; hooks + report sections present |
