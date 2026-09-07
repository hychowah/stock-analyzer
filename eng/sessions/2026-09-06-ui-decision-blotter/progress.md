# Eng session 2026-09-06-ui-decision-blotter

- Created: 2026-09-06T10:37:38Z
- Work type: W4
- Goal: Make Runs and run detail scan as ticker, prices, FV, MoS, Downside, duration, audit — display stored snapshot fields only.

## Log

- 2026-09-06T10:37:38Z scaffolded
- 2026-09-07 orient: on `ui-ux-compose` at `457aefb` (includes Wave 2 `e3f9755` and Wave 1 `d21af66`). Read `eng/AGENTS.md`, parent PLAN.md § Session 3 + file-ownership + How a later agent starts, `AGENT_BRIEF.md`, `handoffs/sdr-wave3-decision-blotter.md`. Predecessor `eng/sessions/2026-09-06-ui-nav-ia/`. SDR mixed/reshape: `catalog_api` + `RunQuery` is the blotter; HTML only ranks and labels it. Do not unique LIMIT 50 in Python, parse `extras_json` in Jinja, or pipe duration through `verdict_badge`. Stale `:8765` has Wave 2 chrome but unreadable git SHA; this-tree UI booted on `:8774`.
- 2026-09-07 implemented Wave 3 (implementer; `passes` left for verifier).
- **project-decision:** `list_runs` / `get_run` hydrate `verdict_line`, `decision_action`, `cheap_claim`. extras blob is not a UI API (`extras_json` popped). Missing → null. No `Run` dataclass. Export/sqlite schema untouched.
- **query-grains:** `RunQuery.latest` in SQL (window after filters, then sort/limit). GET `latest` through `RUN_QUERY_KEYS`, `_filter_href`, `runs.js` `QUERY_KEYS`. Visible Latest vs All; empty `/` and Reset omit the key. Sort `asof_downside_pct` is SQL on stored as-of vs bear — not a run field, not the live cell.
- **duration-not-audit:** Duration prints stored action as text. `verdict_badge` docstring: process audit only. Audit label “Audit (process)”. `verdict_line` is the run-detail subhead; cheap claim on the strip. `.below-bear` is signed ink, not a fill.
- **paint:** Column order Ticker · Session · As-of · Live · FV · MoS · Downside · Duration · Audit; context `desktop-only`; currency on As-of; session cell links to the run. `.decision` type. Quote chip (price default ink, loading `…` + `aria-busy`, first 50 if over cap). Run detail: strip + full-width Valuation above `#price-chart`; Context is not a twin `.grid2`. Own `.decision` / `.below-bear` in `app.css`.
- Verify (implementer, not flipping `passes`): `pytest packages/catalog_api apps/analysis_web/tests` 245 passed; `eng_verify.py` PASS (783, was 779). Live this-tree `:8774` SHA `457aefb…`: empty `/` omits Latest key; `/?latest=1` is 49 unique tickers (catalog match, not a page unique); duration `pass` is text not Audit green; run detail strip + Valuation above `#price-chart`, no `.grid2`. Did not rewrite report viewer, `price_chart.js`, 1100px queries, `base.html`, football PNG, or export/sqlite schema.
- `ARCHITECTURE.md` § How the product reads research + website table. No `harness/VERSION` bump (W4).
- No git commit (needs user agreement). Stay on `ui-ux-compose`.
- 2026-09-07 verifier (skeptical): pytest catalog_api+analysis_web 245 passed; eng_verify PASS 783. progress.md names predecessor ui-nav-ia. extras.decision_action hydrates as run.decision_action; extras_json absent from templates and /api/runs. Latest is ROW_NUMBER in SQL after filters (test_latest_is_catalog_grain_not_page_unique). Duration `pass` is not `class="badge pass"`; Audit (process) still is. run_detail strip and Valuation sit before `#price-chart`; no `.grid2`. TestClient live archive: 49 unique tickers on `latest=1`; 39 PASS+duration pass names; sample `research:01378.HK:2026-08-24`. Forbidden files vs HEAD untouched (`base.html`, `price_chart.js`, export/sqlite schema, `harness/VERSION`). `ARCHITECTURE.md` updated. Flipped `feature_list` passes; wrote `ship_note.json`. Did not git commit as part of verify.
