# Wave 6 alignment — decision reopen

Verdict: **ALIGN WITH EDITS**.

5b is a re-invocation of Agent 5 on `decision.json` only (orchestrator lead after 2.5; do **not** spawn subagent `5` in `2_5`; do not add a PHASE_AGENTS node). Gate `check_wave6_reopen` SKIPPED without `risk_bridge.json` so Phase 2 complete stays green. Wire at `4_parallel` entry + `--full`. `tsr_missing` illegal when `tsr_validation.json` exists. Wave 2 cone unchanged.
