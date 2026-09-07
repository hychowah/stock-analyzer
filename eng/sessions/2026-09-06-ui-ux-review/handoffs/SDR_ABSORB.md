# Strategic design review — absorb (2026-09-06)

Six independent Plan-mode reviews (Ousterhout lens). All six: **Direction mixed, Do reshape.**

Reports: `sdr-wave1-trust-p0.md` … `sdr-wave4c-jobs-portfolio.md`.

This file is the coordinator’s judgement. Parent `PLAN.md` and each `AGENT_BRIEF.md` were updated to match.

## Sequence after absorb

```text
Wave 1  ui-trust-p0
Wave 2  ui-nav-ia                 after Wave 1
Wave 3  ui-decision-blotter       after Wave 2
Wave 4  ui-run-reading            after Wave 3 (run_detail)
        ui-jobs-portfolio         after Wave 1 (job files); portfolio Duration is — until Wave 3 extras exist
Wave 5  ui-a11y-phone             after Wave 2 AND Wave 3 (app.css: disclose + .decision/.below-bear)
```

Wave 4b is no longer parallel with Wave 3. Both write `app.css`.

## Accepted (`this change`)

| Wave | Candidate | Action |
|------|-----------|--------|
| 1 | Headline view in Python, not `row['values']` in Jinja | Project `{label, cells}` in templating / page_compare_detail. Do not rename on-disk `"values"`. |
| 1 | 404 is content negotiation | HTML if Accept prefers text/html; JSON for `/api` JSON Accept. |
| 2 | One `render_page` injects `nav` | Collapse cloned `_render` helpers in `templating.py`. Fragments stay chrome-less. |
| 2 | Wrap each disclose pair | Two labeled `<nav>`s; each checkbox+panel in its own box so Menu cannot open Lab. |
| 2 | Stop crumbs-empty at chrome + Lab | No `runs_table.html`; no portfolio empty copy. |
| 3 | Catalog blotter record | Hydrate `decision_action` / `verdict_line` / cheap claim in `catalog_api`. Templates never parse `extras_json`. |
| 3 | Latest + as-of Downside are `RunQuery` | Not unique-ing the LIMIT 50 page in Python. GET key in `QUERY_KEYS`. |
| 3 | Duration is not Audit | Do not pipe duration through `verdict_badge`. |
| 3 | Name omitted files; valuation full-width | Own `runs_query.py`, `runs.js` keys, `_SORT_HEADERS`, `.decision` in `app.css`. |
| 4a | `render_session_report` ≠ sanitizer | Architecture/harness keep `render_markdown()`. |
| 4a | `page_run` computes `football_href` | Template does not guess the PNG. |
| 4a | One chart copy path; stage height outside 800px query | Do not edit the media-query block a11y-phone will move. |
| 4b | One 1100px contract for every `app.css` 800px query | Including `.chart-stage` query width; height values are 4a. |
| 4b | Do not clip `.stack-table thead` | Keep `display:none`; `aria-label` from `data-label` after swap. Clip recreates invisible tab stops. |
| 4b | List replacement = live node + `runs-table-updated` | Not `catalog-changed` (would re-fetch). |
| 4b | Drop harness 900px from this session | Architecture frame + mermaid icons stay; pipeline column is later. |
| 4c | One wait loop | Patch status in JS; meta refresh; **drop `data-live-reload`** on analyze/compare pages. No list fragments. |
| 4c | Job errors stay on the task | Busy/Grok/Resume conflict re-render the form or job page. Missing resources still `error.html`. |
| 4c | Portfolio reuses Runs blotter cells | Same `data-quote-*` / `data-downside-pct`. Do not edit `app.css` `.perf-bar`. Do not edit `quotes.js`. |

## Rejected or deferred

| Item | Why |
|------|-----|
| Unify all router `_error()` in Wave 1 | Change amplification into files later waves own. |
| Ticker strip `META · 5 runs · Start · Compare` in Wave 2 | Crumb is the chrome piece; strip is a later product if still wanted. |
| UI phase-name map (`orch` → “Valuation”) | `resume_hint` is already the human sentence. |
| Real `.cell-label` in stacked cells | `later`, after blotter is the only `runs_table.html` writer. |
| Harness pipeline column / fake tablist | `later` lab pass; not the 1100px `app.css` contract. |
| `/fragments/analyze` | Lists are not an 8-hour working query; drop live-reload instead. |
| Rebuild artifact `<ul>` from job JSON | API has no artifact index; names-only growth waits for meta/terminal reload. |

## Product shape (unchanged)

Winner A: compose in the FastAPI+Jinja tree. No SPA, no second FV.
