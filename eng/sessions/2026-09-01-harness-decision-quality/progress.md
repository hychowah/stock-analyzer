# Eng session 2026-09-01-harness-decision-quality

- Created: 2026-09-01
- Work type: W1
- Goal: five Mode A decision-quality increments (2.28–2.32)
- Status: complete

## Log

- scaffolded W1 (`--work-type W1`); allowlist `harness/` + `pins/`; denylist archive research/outcomes and `pins/2.27.0/**`
- 2.27.0 already on `main` (`d4b7404`); did not extend pin-and-viz or 2.18 Street sessions
- 2.28.0 committed (`0995b47`): Street default Y1 + evidence-gated `independent_y1`
- 2.29.0 committed (`ef3fce6`): material stress binds duration
- 2.30.0 committed (`7bed05d`): bind-then-classify, slim Phase 0, `1_parallel` ∥ Phase 0
- 2.31.0 committed (`6e3df4b`): consume FDD/Street/1d_ind/legal $
- 2.32.0 committed (`e1441e8`): TSR ROC join on `decision.json` at 5b (FAIL); Phase 2 stays parallel
- Session notes closed after confirming all five plan items are on `main`. Catalog indexes left uncommitted.

## Refactor

- Street Y1 policy split: 2.18 statute stays version-banded; 2.28 is a consistency layer (`street_baseline` vs `independent_y1` + resolved gate) rather than a longer if-else of valuation recipes. `ttc_midcycle` is not a Y1 license.
- Stress bind is duration-and-usefulness, not a second DCF.
- TSR cheap-claim join lives on `decision.json` so Agent 5 stays parallel with Agent 12.
