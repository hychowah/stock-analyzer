# Wave 3 plan — epistemology (harness 2.11.0)

IDs: **E1–E4, E6, F3, D5–D7**.

## Goal

Stop the promoter-path DCF: unresolved destock cannot be duration-in-base without honesty; Street 20% is calibration not a skill miss; high TV + still-high Y8 growth must extend or switch; related-party concentration cannot hide at intensity=low; updates changelog **facts** without copying prior FV (F14/F16).

## Alignment

- Version-gate new FAILs at ≥ 2.11.0; Street 20% change is a **softening** (WARN not FAIL) and applies whenever street_bind already runs (≥2.7.0) so we do not keep teaching FY+1 consensus as skill.
- Isolation: changelog required only when `research_brief.mode=update` or `prior_session_key` is **declared**. Do **not** list `archive/research/<T>/` to discover priors.
- Changelog must not contain prior `fair_value` / `margin_of_safety` / `wacc` / scenario masses as inputs.
- Synthetic tests; no live snapshot/outcomes rewrite.

## Gates

### E1 destock-as-base
If `operating_path_brief.conflicts[]` has unresolved flatten/destock (id or claims), then valuation must either:
- encode destock in **base** (`operating_path_hooks` used_as destock/quality-reset in base), or
- `decision_usefulness=low`, or
- `duration.action` in pass/too_hard
Else FAIL.

### E2 beat ≠ trust_guides_more
Prompt: scorecard `beat` is not a hit for trusting guides. Machine WARN if valuation/hooks contain `trust_guides_more` without a `met_only` or cash-quality split on the scorecard.

### E3 two-quarter raise + WC
Prompt + WARN if `overrides_applied` two_quarter_rule raises volume/growth while LQ cash_flow FCF is negative and AR/inventory up. Too heuristic for FAIL.

### E4 Street |delta|>20%
`street_bind`: missing response/divergence on |delta|>20% is **WARN** (calibration note), not FAIL. Copying Street into the path remains FAIL.

### E6 TV share
If `terminal_consistency.tv_share_of_ev_base > 0.60` **and** Y8/Y10 growth ≥ 8%, require `terminal_consistency.response` in `{extend_years, switch_primary, residual_income}` (or explicit years≥10 already). Else FAIL on ≥2.11.0.

### F3 related-party intensity
If `market_context.intensity=low` and FDD related-party footnote/blob shows related-party revenue ≥20% or preferred/board rights → FAIL (cannot stay low).

### D5–D7 changelog / update
- `research_brief.mode` optional: `initiate` (default) | `update`
- If `update` or `prior_session_key` set: require `registry/earning_power_changelog.json` with fact fields (nopat/ic/shares/scorecard) and **forbidden** prior FV/MoS/WACC keys.
- Isolation `prior_valuation_as_input` remains false.
- Orchestrator runbook: after audit, default `compare_after` when prior_session_key declared (script: `compare_runs.py` docs; do not auto-open valuation).

## Files
`scripts/kd_research/epistemology.py`, street_bind WARN, templates changelog + research_brief.mode, prompts 2e/5/13, VERSION 2.11.0, `test_wave3_epistemology.py`, isolation tests that changelog with prior FV FAILs.

## Non-goals
Wave 4 mandate pack. Scanning live archive for priors. Rewriting completed sessions.
