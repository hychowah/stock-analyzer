# Wave 5 plan — mid-cycle construction (harness 2.13.0)

Persona pack item 2. Extends §10d; does not replace ROIC identity.

## Goal

Stop feeding §10d a peak or last-year print and calling it a franchise. `franchise_mos` / `quality_bucket=above_wacc` requires a **shown mid-cycle window**, not a slogan.

## Why

Agent 5 today: “Do not treat one peak year or one trough quarter as mid-cycle.” One sentence. §10d then capitalizes whatever NOPAT the agent called mid-cycle. TTC ROIC < WACC is printed, not FAIL (trough cyclicals). A peak year labeled mid-cycle still clears `above_wacc`.

## Alignment constraints

- W1; VERSION 2.13.0 same change set; synthetic tests; no archive mutation; Agent 5 single-writer.
- Keep `check_roic_identity` behavior for <2.13.0. Do not FAIL TTC < WACC (would nuke trough cyclicals).
- Do **not** block `initiate` solely because `cheap_claim ≠ franchise_mos`.
- Machine-gate structured fields, not NLP on “this print was a peak.”
- One home: `roic_identity.mid_cycle_construction` in `scripts/kd_research/roic_identity.py` (extend, no parallel module).
- Prompt altitude: a short block after Agent 5 2b, not a second destock essay.

## Prompt / law

1. **Agent 5 after 2b:** require `roic_identity.mid_cycle_construction` when `applies:true`: `window_kind`, `years_used` (≥1), `print_vs_midcycle` (≥20 chars). Forbidden: last-year SOI as mid-cycle without a window. If window is too short, cannot `franchise_mos` / cannot `above_wacc` on that print alone.
2. **`window_kind` enum:** `ttc_cycle` | `multi_year_avg` | `last_year` | `peak_year` | `insufficient_window`.
3. **Agent 13 Band 3 `4-midcycle`:** last-year/peak SOI as mid-cycle with `franchise_mos` is major. Missing construction on `applies:true` is major on ≥2.13.0.
4. **`valuation_decision_quality.md` Pair 8:** BAD = mid-cycle ROIC 18% from a peak/last year, no window, `franchise_mos`. GOOD = same print, `window_kind=insufficient_window` or `last_year`, `equity_near_book` / `not_cheap`.
5. **`RESEARCH_AGENTS.md` §10d / §13:** construction required; `franchise_mos` illegal on last_year/peak_year/insufficient_window. TTC < WACC remains non-FAIL for commodity cyclicals.
6. **`HARNESS_MAP.md` / `VERSION`:** 2.13.0.

## Gates (≥ 2.13.0; legacy SKIPPED)

When `roic_identity.applies` is true:

- Missing `mid_cycle_construction` with `window_kind` + `years_used` + `print_vs_midcycle` (≥20 chars) → FAIL.
- `cheap_claim.class=franchise_mos` **or** `quality_bucket=above_wacc` with `window_kind` in `{last_year, peak_year, insufficient_window}` → FAIL.
- `franchise_mos` with `years_used` length < 2 (and not a `{start,end}` span of ≥2 years) → FAIL.

`applies:false` (banks/REITs/pre-profit) SKIPPED. Do not invent a formula for mid-cycle NOPAT.

## Files

`harness/agent_prompts.md`, `RESEARCH_AGENTS.md`, `HARNESS_MAP.md`, `VERSION`, `exemplars/valuation_decision_quality.md`, `templates/valuation_model.schema.json` (document the object), `scripts/kd_research/roic_identity.py`, `scripts/check_session.py` if needed (already calls check_roic_identity), `scripts/tests/test_wave5_midcycle.py`, this plan + alignment.

## Non-goals

Incremental ROIC path (quality-owner Pair 9) — prompt sentence at most, not a gate. Decision reopen (Wave 6). Archive rewrites. Mandate pack.
