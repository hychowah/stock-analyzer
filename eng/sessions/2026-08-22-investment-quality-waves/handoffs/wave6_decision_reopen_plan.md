# Wave 6 plan — decision after 2.5 + Agent 12 join (harness 2.14.0)

Persona pack item 3. Extends Wave 2 decision packet. Agent 5 stays **single-writer**.

## Goal

The duration verb is not final until stress (`risk_bridge`) and the TSR screen (`tsr_validation`) exist. Same Agent 5 reopens `decision.json`. No second valuer. Stress still does not rewrite DCF numbers.

## Why

Today Agent 5 writes `decision.json` in Phase 2 while Agent 12 runs in parallel and Phase 2.5 is later. Merge is “not a co-author of new haircuts.” So `initiate` can lock before destock stress or buyback flags exist.

## Alignment constraints

- W1; VERSION 2.14.0 same change set; synthetic tests; no archive mutation.
- Keep Wave 2 `check_decision_packet` for <2.14.0 (initiate still blocked on useless cone).
- Extend `scripts/kd_research/decision.py` — no `decision_reopen.py`.
- Do **not** block `initiate` because `cheap_claim ≠ franchise_mos`.
- Do **not** add book_state / invalidation / CIO cover (Wave 8).
- Do **not** make Agent 12 write valuation.
- Machine-gate booleans, not NLP on rationale.
- 5b is a **re-invocation of Agent 5**, not a new specialist id in the phase graph (optional `handoffs/5b_decision_reopen.md`).

## Prompt / law

1. **Agent 5 Phase 2:** still writes `decision.json`. On ≥2.14.0 set `reopened_after_stress: false` and `tsr_seen: false` until 5b. Label duration **provisional**.
2. **Orchestrator after Phase 2.5 complete** (risk_bridge on disk; Agent 12 already finished in 2_parallel): re-invoke Agent 5 with a short 5b prompt: read `risk_bridge` + `tsr_validation`; do not rewrite FV; may change `duration.action`; set `reopened_after_stress: true` and `tsr_seen: true` (or explicit `tsr_missing` if TSR file absent).
3. **2.5 merge:** still not a co-author of haircuts. Decision reopen is Agent 5’s job after the merge.
4. **Agent 13:** `decision.json` with initiate/add and `reopened_after_stress` false/missing after 2.5 is major.
5. **`RESEARCH_AGENTS.md` §8 / §13, `HARNESS_MAP.md`, `orchestrator_runbook.md`:** 5b after 2.5; Agent 5 single-writer.
6. **`templates/decision.schema.json`:** document the two booleans; not schema required[] (Python gate).

## Gates (≥ 2.14.0)

- If `risk_bridge.json` exists and `decision.reopened_after_stress` is not true → FAIL.
- If `tsr_validation.json` exists and `decision.tsr_seen` is not true → FAIL.
- `initiate`/`add` with `reopened_after_stress` not true → FAIL.
- No risk_bridge yet → SKIPPED (provisional Phase 2 session).
- <2.14.0 → SKIPPED.
- Do not require specific TSR flag ids this wave (buyback VWAP stays prompt / later).

## Files

`decision.py`, `check_session.py` / `gates.py` if they only call `check_wave2_decision` (extend that function or add `check_wave6_reopen` in the same module), prompts, runbook, HARNESS_MAP, RESEARCH_AGENTS, VERSION, decision.schema.json, `test_wave6_decision_reopen.py` + keep `test_wave2_decision.py` green.

## Non-goals

Wave 8 README CIO. Wave 7 gather. Forcing Agent 12 before Agent 5’s DCF. Second valuer. Archive rewrites.
