# Eng session 2026-09-07-ui-sheet

- Work type: W4
- Goal: Wave 8 ui-sheet — cover-first run page, two sibling lists, table-scroll

## Log

- Scaffolded then implemented Wave 8. Plan: `PLAN_POST_COMPOSE.md`. Predecessors Waves 1–7 on `ui-ux-compose`.
- `run_detail.html`: strip → football + Read CIO cover `.btn` → Price vs analysis → Context → Valuation in `<details>` (“Bear / base / bull / model”). Dropped `.mono` on ticker h1; `run_id` stays muted. Compare form card after envelope/cover.
- Applied Wave 7 filters on the strip: `duration_label`, `cheap_claim_label`, `verdict_line_html`. No `| safe`.
- `page_run` exposes `sibling_links` (all other catalog sessions as `/runs/{id}`) and `comparable_siblings` (Grok `<select>`). Chart overlay keeps the comparable set. Did not reuse one `siblings` list with a flag.
- `.table-scroll` wraps strip / Context / Valuation tables. No `.stack-table` on property-row tables.
- Did not edit: `templating.py`, `runs.js`, `runs.html`, blotter columns.
- pytest `apps/analysis_web/tests` 225 passed. `eng_verify.py` PASS (816).
- Playwright MCP (separate verifier agent) on live `:8765` 4516.T: football + Read CIO cover above chart and Compare; verdict has no raw `**` / backticks; 390px `scrollWidth == clientWidth`; CIO artifact one H1 titled as cover. Report: `handoffs/playwright-wave8.md`.
- Next: Wave 9 ui-job (analyze wait page). Must not edit `app.css`, `runs.html`, `pages.py`, or `run_detail.html`.
- smart-commit auditor: leave `.playwright-mcp/` and root `ux-*.yml` untracked; retarget `START_NEXT_SESSION.md` to Wave 9; cover-first cells in `ARCHITECTURE.md` and `apps/analysis_web/README.md`.
