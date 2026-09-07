# Eng session 2026-09-07-ui-readable

- Created: 2026-09-07T07:28:43Z
- Work type: W4
- Goal: Wave 6 ui-readable — Night through-bear AA, SR cell-label, chrome --muted, list overflow, favicon 204

## Log

- 2026-09-07T07:28:43Z scaffolded
- Wave 6 implemented. Predecessors: compose Waves 1–5 on `ui-ux-compose`. Plan: `PLAN_POST_COMPOSE.md`.
- `--below-bear` light `#7f1d1d`, Night `#fca5a5` (Playwright ~7.7:1 on `--card`). Header tagline/Lab `--muted` (~7.9:1 on Night header).
- Deleted `labelStackedCells`. `.cell-label` clipped span in `runs_table.html` + `portfolio.html`.
- Desktop `.card:has(.runs-table|.stack-table)` overflow-x auto. `thead th` uppercase. `table:has(thead) tr:hover`. stack-form skin on base sheet; 16px/44px stay in 1100px query. Dropped `.chart-stage` 220px leftover.
- `GET /favicon.ico` → 204.
- Did not: Duration copy, Latest hrefs, `.table-scroll`, `#compare-btn:disabled`, run_detail order.
- Verify: `pytest apps/analysis_web/tests` 221 passed; `eng_verify.py` PASS; Playwright Night contrast, skip-link first Tab, favicon 204, no `td[aria-label=MoS]`.
