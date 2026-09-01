# Eng session 2026-09-01-harness-viz-ux

- Created: 2026-09-01T06:12:01Z
- Work type: W4
- Goal: Make /harness a workflow visualizer instead of a raw JSON/markdown dump

## Log

- 2026-09-01T06:12:01Z scaffolded
- filled issue.json + feature_list; git log: 0f33dba close 2.28-2.32; d4b7404 first /harness dump
- strategic design review of the plan (candidates 1–5 applied; 6 later)
- **view-model:** `harness_page_model` is display-only (stages/phases/agents). No decorated spec, no `edges`/`agent_index`. Annotations: `phase` / `before` phase / `before` agent / page. Glob chips keep the glob. `convention_items` start after "Conventions for all agents". Prompt payload additive (`sections`, `spawn_role`, `role_line`).
- **workspace-ui:** one staged pipeline + sticky inspector. Overview from the page model (no fetch). Prompt tab on demand. Conventions in the toolbar. No Handoffs/DAG view, no `pin_root` chrome.
- tests: `pytest apps/analysis_web/tests` 78 passed; `python scripts/eng_verify.py` PASS (630). Implementer does not flip `passes`.
- follow-up sweep before commit: Prompt-tab cache flicker and `CSS.escape` fallback fixed. Remaining debt listed below (not this W4).

## Follow-ups (not this commit)

- **W1 / review candidate 6:** `workflow_spec` should emit phase/agent display labels and orchestrator (and 2a street) writes. Then UI `PHASE_META` is a fallback for old pins, and need-chips can name producers that are not in `SPECIALIST_ARTIFACTS`. Needs `harness/VERSION`.
- **Page-load subprocess:** `GET /harness` calls `Pin.agent_prompt("orchestrator")` only for the conventions preamble (second process after `workflow_spec`). Same W1 dump can carry that body and drop the extra call.
- **Verifier:** `feature_list.json` still `passes: false` (implementer does not flip).
- **Do not commit** live `archive/catalog/*` (unrelated dirty tree).

## Git

Proposed subject: **Turn /harness into a pipeline map with a briefing inspector**
