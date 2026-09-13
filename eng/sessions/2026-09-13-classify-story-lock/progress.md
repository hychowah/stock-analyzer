# 2026-09-13-classify-story-lock

## Done

- Orchestrator writes `registry/classification.json` (job, life-cycle, one iv_playbook, overlays, buyer, market-contest) after KPI sector + region and before Phase 0.
- New phase `1e`: specialist `story` writes `narrative_bind` (draft, story carriers, evidence_hooks map|reject); specialist `3p` grades 3P and locks on PASS.
- Agent 5 waits on 1e. Machine FAIL if bind stamps disagree with classification. `story_input_bind` maps carriers onto model inputs.
- Legacy `< 3.4.0` omits 1e; Agent 5 still lock-then-compute.
- SDR reshape (3.4.1): identity lives only on classification.json; 3P PASS is the lock; Agent 5 does not write the bind or re-consume FDD/oppath.
- Harness 3.4.1 pin published. `eng_verify` PASS (1176 tests).

## Not in this increment

Street-as-default-Y1, job-based skips, dropping Agent 4/12, stress-quota rewrite.
