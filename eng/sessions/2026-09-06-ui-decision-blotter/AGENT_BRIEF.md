# Agent brief — ui-decision-blotter (post-SDR)

Mode B W4. Read `eng/AGENTS.md` and parent `PLAN.md` § Session 3 plus `handoffs/sdr-wave3-decision-blotter.md`.

**Start after** `ui-nav-ia`. `catalog_api` + `RunQuery` **is** the blotter interface.

SDR verdict: **mixed / reshape**. Do not unique the LIMIT 50 page in Python. Do not parse `extras_json` in Jinja. Do not pipe duration through `verdict_badge`.

## Goal

First glance is ticker · as-of/live · FV · MoS · Downside · duration · audit. Audit stays process completeness. Duration from snapshot. **Do not invent** actions.

## Slices

1. **project-decision** — Hydrate in `list_runs` / `get_run`: `verdict_line`, `decision_action`, cheap claim. UI never reads `extras_json`.
2. **query-grains** — `RunQuery.latest`; GET key in `RUN_QUERY_KEYS` + `runs.js` `QUERY_KEYS`. Sort `asof_downside_pct` from stored as-of vs bear. Empty `/` omits Latest.
3. **duration-not-audit** — Duration column is the stored action, not `verdict_badge`. Audit labeled process. `verdict_line` subhead. `.below-bear` signed ink.
4. **paint** — Column order + `.decision` + quote chip + full-width valuation **above** chart. Session cell links to the run. Own `.decision` / `.below-bear` in `app.css`.

Named files you will touch: `packages/catalog_api/client.py`, `apps/analysis_web/services/runs_query.py`, `static/runs.js`, `routes/pages.py`, `partials/runs_table.html`, `runs.html`, `run_detail.html`, `quotes.js`, `templating.py`, `static/app.css` (blotter selectors only).

## Non-goals

No live MoS. No JS DCF. No football PNG. No 1100px query change (Wave 5). Do not unique-by-ticker on the current page of 50.

## Verify

pytest catalog_api + analysis_web. Latest toggle returns at most one row per ticker **across the catalog match**, not among 50. A PASS + duration `pass` name shows both, and duration is not a green Audit pill. `eng_verify`.

No commit until the user agrees.
