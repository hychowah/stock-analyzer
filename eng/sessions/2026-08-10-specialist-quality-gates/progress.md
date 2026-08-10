# Progress — specialist-quality-gates

## Orientation

- Mode B / W1 research runtime.
- Plan: selective specialist outcomes (hooks, Agent 4 isolation, handoffs, phase_status↔disk).

## Done

- Scaffolded session; issue W1; feature list.
- **F-A:** RESEARCH_AGENTS §13, HARNESS_MAP, orchestrator_runbook, Agent 13 process band, failure catalog F17–F20.
- **F-B:** `filing_deep_dive_hooks` machine gate + preflight `2_5` entry / `2_parallel` complete; intensity all-noted_only FAIL for medium/high.
- **F-C:** Agent 4 isolation heuristic; swarm handoffs (`phase0_*` / `phase25_*`); header WARN.
- **F-D:** phase_status complete vs disk FAIL; lag WARN; expanded complete_checks for 1_parallel / 1c / 2_parallel / 4_parallel.
- Fixed stale test pointing at root AGENTS.md for §5b → RESEARCH_AGENTS.md.
- `harness/VERSION` → **2.3.0**.
- `eng_verify` PASS; gate unit tests PASS.

## Verify

```bash
python3 scripts/eng_verify.py
python3 -m pytest scripts/tests/test_fdd_hooks_check.py scripts/tests/test_agent4_isolation_check.py scripts/tests/test_handoff_structure.py scripts/tests/test_market_context_check.py scripts/tests/test_gates_preflight.py -q
```

## Note

- Implementer left `feature_list.passes` for verifier; ship_note written.
- Commit only when user asks.
