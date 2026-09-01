# Eng session 2026-09-01-harness-decision-quality

- Created: 2026-09-01
- Work type: W1
- Goal: gated-independent Y1 (2.28.0)

## Log

- scaffolded W1 (`--work-type W1`); allowlist `harness/` + `pins/`; denylist archive research/outcomes and `pins/2.27.0/**`
- 2.27.0 already on `main` (`d4b7404`); did not extend pin-and-viz or 2.18 Street sessions
- Implemented item 1 only (plan items 2–5 not in this increment)
- Machines: `street_bind.py` 2.28 gated Y1; `epistemology.py` destock-in-base licensed by `destock_this_print`
- Law: RESEARCH_AGENTS §10c current; §13 2.18 bounded `< 2.28`; new 2.28 row; `harness/law_history.md` JIT for Agent 13 on old stamps
- Prompts: Agent 5 Y1 LAW at top; 4d/4e/self-check; Agent 13 4-street; 1d_merge
- Tests: `test_wave11_gated_y1.py`; law-surface freeze retargeted
- VERSION 2.28.0 + `publish_harness_release.py` → `pins/2.28.0/`
- `python scripts/eng_verify.py` PASS (594 tests; pin matches VERSION)
- Implementer did not flip `feature_list` `passes`
- 2.29.0 committed: material stress binds duration
- 2.30.0 committed: bind-then-classify, slim Phase 0, 1_parallel ∥ Phase 0
- 2.31.0 committed: consume FDD/Street/1d_ind/legal $
- 2.32.0: TSR ROC join on decision.json at 5b (FAIL); Phase 2 stays parallel

## Refactor

- Street Y1 policy split: 2.18 statute stays version-banded; 2.28 is a consistency layer (`street_baseline` vs `independent_y1` + resolved gate) rather than a longer if-else of valuation recipes. `ttc_midcycle` is not a Y1 license.
