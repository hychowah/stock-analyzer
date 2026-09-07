# Eng session 2026-09-07-ui-job

- Work type: W4
- Goal: Wave 9 ui-job — analyze wait page is resume_hint; complete Open catalog run / Read CIO cover as .btn

## Log

- Scaffolded then implemented Wave 9. Plan: `PLAN_POST_COMPOSE.md`. Predecessors Waves 1–8 on `ui-ux-compose`.
- `analyze_detail.html`: `#job-phase-wrap` hidden when `resume_hint` is non-empty (hides the word “phase” plus the token). Complete: `.btn` Open catalog run; `.btn` Read CIO cover when allowlisted README exists (catalog `/artifact` when `catalog_run_ready`). Artifact `<ul>` unchanged. Reconcile copy stays `.muted` unless failed/cancelled/abandoned.
- `analyze_detail.js`: `hidePhaseWhenHint`; error class muted vs err; still no `innerHTML`; meta refresh stays server-side.
- Did not edit: `app.css`, `run_detail.html`, `runs.html`, `routes/pages.py`, `analyze.html`.
- Docs: `ARCHITECTURE.md` and `apps/analysis_web/README.md` `/analyze/{id}` cells match the wait page.
- pytest `apps/analysis_web/tests` 225 passed. `eng_verify.py` PASS (816).
- Playwright MCP (separate reviewer agent) on live `:8765`: PASS. Report: `handoffs/playwright-wave9.md`. 4516.T complete: phase wrap hidden, `.btn` Open catalog run + Read CIO cover; COHR/WHR reconcile `.muted`; running jobs refresh=15; Wave 8 football+CIO still above the chart. No product adjust.
- Compose remainder after this wave: `PLAN_POST_COMPOSE.md` Out of scope.
