# Eng session 2026-09-01-harness-viz-ux

- Created: 2026-09-01T06:12:01Z
- Work type: W4 then W1 (spec dump for the visualizer)
- Goal: Make /harness a workflow visualizer instead of a raw JSON/markdown dump

## Log

- 2026-09-01T06:12:01Z scaffolded
- filled issue.json + feature_list; git log: 0f33dba close 2.28-2.32; d4b7404 first /harness dump
- strategic design review of the plan (candidates 1–5 applied; 6 in this follow-up)
- **view-model / workspace-ui:** display-only page model, one pipeline, overview from the model, prompt on demand. Committed `fb325a0`.
- **debt removal (2.33.0):** `workflow_spec` emits phase/agent labels, orchestrator+2a street writes, and `conventions` body. Spawn gates unchanged (`SPECIALIST_ARTIFACTS` untouched). `GET /harness` no longer calls `Pin.agent_prompt` for conventions. UI `PHASE_META` remains fallback for older pins. `pins/2.33.0` published.
- Implementer does not flip `passes`. Leave `archive/catalog/*` uncommitted.

## Git

Follow-up subject: **Emit harness display labels, extra writes, and conventions in workflow_spec (2.33.0)**
