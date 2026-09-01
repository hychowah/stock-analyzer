# Eng session 2026-09-01-harness-pin-and-viz

- Created: 2026-08-31T23:34:53Z
- Work type: W1
- Goal: In-repo pins plus Analyze version select and /harness visualization

## Log

- 2026-08-31T23:34:53Z scaffolded
- filled issue.json + feature_list (pin-runtime, jobs-bind-pin, analyze-and-harness-ui)
- recent git: cde6a6e ticker check 2.26.0; d2ae7a4 ANALYZE_MAX=3; 0770228 packages+harness 2.25.0
- **pin-runtime:** `packages/harness_pin` (`resolve` / `list_versions` / `Pin.run` / `spawn_env` / `workflow_spec` / `agent_prompt`). `workflow_spec` dumps phases/edges from existing SINCE constants. Uniform `### Agent <id>` headings. Write-once identity: finalize copies scaffold stamp. `publish_harness_release.py` → `pins/2.27.0/`. VERSION 2.27.0. `eng_verify` requires matching pin folder on W1 bump; published pin trees immutable.
- **jobs-bind-pin:** `start_analyze(harness_version=)` uses Pin only (no live `scaffold()` import). Map prompt is coordinates. Spawn PYTHONPATH replace; Grok cwd = workspace.
- **analyze-and-harness-ui:** Analyze `<select>`, list/detail version column, `/harness` swimlanes + artifact graph + prompt inspector.
- **verify:** `python scripts/eng_verify.py` PASS (577 tests). Implementer does not flip `passes`.

## Git

Not committed. Proposed subject: **Add in-repo harness pins, versioned Analyze, and /harness workflow view (2.27.0)**
