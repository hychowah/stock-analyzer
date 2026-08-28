# Eng session 2026-08-28-spawn-required-abandon

- Created: 2026-08-28T07:41:12Z
- Work type: W1
- Goal: Fail-closed specialist spawn; spawn failure abandons the session.

## Log

- 2026-08-28T07:41:12Z scaffolded
- Baseline: `eng_verify` was green on 2.19.0 before the increment (session started from a passing tree; this follow-up re-verified after 2.20.0).
- Implemented spawn-or-abandon (harness 2.20.0):
  - Law: specialists must `spawn_subagent`; inline specialist work is forbidden; spawn fail → abandon (not “do it as the lead”).
  - Machine: `registry/spawns.json` ledger + `registry/abandon.json`; wired into preflight, `check_session`, `finalize_session`.
  - CLIs: `scripts/record_spawn.py`, `scripts/abandon_session.py`.
  - Honesty: ledger is process telemetry, not Task-API cryptographic proof. Missing ledger FAILs; faking a ledger is a harness violation.
- Dual-reviewer follow-up (before commit):
  - Agent 13 no longer says spawn is optional.
  - `orchestrator_lead` is orch-row only; 5b must not retag Agent 5; `orchestrator_inline` is schema-legal and a specialist FAIL.
  - Return without prior launch is rejected; spawn must belong to the home phase.
  - Year-reader home phase is `1c` in `check_phase_status_graph`.
  - Phase 0 / 2.5 require one returned spawn per raw file, not one swarm row.
  - `spawns.json` / `abandon.json` schema-checked in `check_session` when present.
  - `--event fail` still abandons (user rule); retry spawn without recording fail if the tool glitched.
- Verify: `pytest scripts/tests/test_spawn_gate.py` + related 50 passed; `eng_verify.py` re-run after follow-up.

## Refactor

- Year-reader ids (`2e_fyYYYY`) are valid `--subagent` values on phase `1c`; `home_phase_for_subagent` is shared by preflight, spawn CLI, and graph integrity.
- Phase 0 round ids stay `phase0_rN` (no longer collapsed to `phase0_swarm`) so per-raw spawn rows can be required.
