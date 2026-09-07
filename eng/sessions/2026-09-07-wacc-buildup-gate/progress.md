# 2026-09-07-wacc-buildup-gate

- Scaffolded W1. Goal: harness 2.40.0 `wacc_buildup` so new runs cannot repeat CMCSA coupon-as-Kd / trough-weight WACC. Did not rewrite completed research.
- Spawned six investing-persona reviewers (conservative value, quality compounder, forensic accountant, valuation process, risk PM, reverse engineer). Memos in `handoffs/01`–`06`. Synthesis in `handoffs/99_synthesis.md`.
- Absorbed load-bearing comments: coupon illegal; Kd ≥ Rf except `negative_rate_market`; 0 bp spread hatch; distressed tripwire without book prong; anti-copy of trough `wd`; skip net-cash; no pasted rate; Agent 13 `4-wacc`. Dropped mandated Blume, FAIL-the-tape, and auto-kill `franchise_mos` from implied WACC.
- Implemented checker `packages/kd_research/wacc_buildup.py`, catalog rows, §10e, Agent 5 2c / Agent 13 4-wacc, schema, exemplar BAD twin, F35, pin `pins/2.40.0/`.
- Verify: `test_wacc_buildup.py` 17 passed; `eng_verify.py` PASS (833 tests). CMCSA `2026-09-07` harness 2.39 → SKIPPED.
