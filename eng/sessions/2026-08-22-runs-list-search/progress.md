# Eng session 2026-08-22-runs-list-search

- Created: 2026-08-22
- Work type: W4
- Goal: Instant prefix ticker search, live filters, and column sort on the Research runs list

## Log

- scaffolded
- filled issue.json + feature_list.json
- recent git: 9f6d640 refactor-when-it-pays; ca950d4 street bind; 6f9d34e portfolio; 9a1a605 SSE live reload
- working tree already dirty: archive/catalog JSON indexes (not this session)
- baseline `python scripts/eng_verify.py`: PASS (84 tests) before product edits; no harness/VERSION bump needed
- **catalog-query:** extracted shared `_runs_filter_sql` / `_runs_order_sql` (replaces duplicated v1/v2 WHERE+ORDER). Added `ticker_prefix` (escaped LIKE starts-with), allowlisted `sort`/`dir` (ValueError on invalid), `count_runs`. `list_runs` still returns `list[dict]`. CLI `--ticker-prefix --sort --dir`. Tests: exact `ticker=M` empty; prefix `M` → MELI/META/MSFT; LIKE literals; bad sort raises.
- **runs-instant-search + column-sort:** `GET /fragments/runs` table partial; `static/runs.js` debounce 100ms / AbortController / replaceState; form field `ticker_prefix`; no-JS GET remains. Sortable header links. `live.js` dispatches `catalog-changed` when `data-live-partial=1` so catalog SSE refetches the fragment instead of wiping the ticker box. README HTMX teaser removed (H15).
- **verify:** `eng_verify.py` PASS (104 tests). Live HTTP on :8766: `/?ticker_prefix=M` → MC.PA/MELI/META; `ME` → MELI/META; `/?ticker=META` exact; fragment has no `<header>`; invalid sort 400; `/api/runs?ticker=M` count 0; prefix total 7. No browser driver available — HTTP smoke + TestClient used.
- refactor why (constraint 11): one WHERE/ORDER builder for list+count; one meaning per query param on HTML/JSON/CLI (not HTML `ticker=`=prefix).
- **range-filters:** session_date_from/to, mos_min/max, price_min/max, fv_base_min/max on CatalogApi + HTML/JSON/CLI. Sector/region/tech are exact dropdowns from `list_run_facets()`. Shared `apps/analysis_web/services/runs_query.py` so page, fragment, and `/api/runs` cannot drift. Invalid range/date → 400. `eng_verify.py` PASS (118 tests).

## Git

Not committed. Proposed subject: **Add instant ticker prefix search, live filters, and column sort on the runs list**
