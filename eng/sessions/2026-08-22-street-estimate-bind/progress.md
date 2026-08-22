# street-estimate-bind (2026-08-22)

## Goal
Independent FY+1 revenue path from company evidence; Street consensus is a calibration bar, not a copy-paste input.

## Done
- `templates/street_estimates.schema.json`
- `scripts/kd_research/street_bind.py` + gates/check_session wiring
- `harness/RESEARCH_AGENTS.md` §10c
- Agent prompts 2a/2c/2d/1d/4/5/13
- Exemplar Pair 6
- `harness/VERSION` 2.7.0
- Tests: `scripts/tests/test_street_bind.py`

## Validation follow-up (2026-08-22)
Closed gaps from `handoffs/validation_review.md`:
- `bind.street` identity vs `street_estimates.json` FY+1
- `conservatism_dials` four keys required on harness ≥ 2.7.0 (omit = FAIL)
- SOTP+DCF both present without `multi_method_reconciliation` = FAIL
- Schema allows empty `years[]` only when `unavailable=true`; `--full` schema-checks the Street file when present
- Street removed from `PHASE_ENTRY_OPTIONAL`; extra-required like 1d via `check_street_fetch`
- `HARNESS_MAP.md` 1_parallel evidence cell includes `street_estimates.json`

Catalog indexes stay **dirty and unstaged** (Mode B read-only data plane; not this commit).

## Verify
- `python scripts/eng_verify.py` PASS
- pytest list 81 passed
- AVGO 2026-08-21 `check_session --full` 115 passed, 1 skipped (street_bind legacy)
