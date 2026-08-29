# Eng session 2026-08-29-analyze-concurrency-3

- Created: 2026-08-29
- Work type: W2 (capacity defaults) + light W4 (Analyze page copy)
- Goal: Allow three concurrent Mode A Analyze jobs (ANALYZE_MAX=3, GROK_JOBS_MAX=4)

## Git log (orient)

- 0770228 Move research runtime into packages and Mode A law under harness (2.25.0).
- de88d9c Add Mode A Analyze to the web UI (harness 2.22.0).
- 42df40a Abort Mode A and analysis when the ticker is not real

Dirty tree at start: `archive/catalog/*.json` (unrelated; leave alone).

## Log

- Scaffolded. Capacity today: ANALYZE_MAX=1, COMPARE_MAX=1, GROK_JOBS_MAX=2. Raising Analyze to 3 also requires GROK_JOBS_MAX>=3; set 4 so one Compare can still overlap three Analyze jobs (same kind-slot+global design as v1).
- Implemented: defaults ANALYZE_MAX=3, GROK_JOBS_MAX=4 (COMPARE_MAX stays 1). `limits()` now reads those constants so defaults cannot drift. Busy copy is slot-count based. `/analyze` and `/analyze/new` show the live cap. Tests: 3 running Analyze allowed; 4th raises AnalyzeBusy. `eng_verify` PASS (547). Did not restart the live UI on :8765 — operator must restart to pick up the new process defaults.
- Refactor: capacity module constants are the single default source for `limits()` (env still overrides).
- Strategic review follow-through (all four candidates):
  1. `GROK_JOBS_MAX` is no longer a third default literal — unset means `ANALYZE_MAX + COMPARE_MAX` (env still tightens).
  2. `limits()` returns frozen `Limits` (`analyze`/`compare`/`grok`, plus `analyze_slots = min(analyze, grok)`). Analyze pages take that object; `_capacity_ctx` deleted.
  3. Compare raises `CompareBusy(str(e))` from `JobsBusy` — no more max=1 “already running ({rid})” rewrite.
  4. Shared `claim_start(archive_root, kind)` = exclusive lock + census + slot check. Both Analyze and Compare use it. Census lives in `agent_jobs` via `count_running_analyze` / `count_running_compare`. Lock file `archive/.grok_jobs.lock`.
- Why: one policy number (Analyze parallelism) plus optional tighter global; one error sentence; one start gate. Compare and Analyze no longer each count the other kind.
