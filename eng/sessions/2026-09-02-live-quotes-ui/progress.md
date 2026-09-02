# Eng session 2026-09-02-live-quotes-ui

- Work type: W4
- Goal: Display-only Yahoo last print on runs list and run detail

## Log

- Scaffolded session; plan adjusted after strategic design review.
- Implemented listing identity on `CatalogApi.list_runs` / `get_run` (read-only `run_manifest` + `price_snapshot`; no sqlite column, no `harness/VERSION`).
- Quote module: `apps/analysis_web/services/quotes.py`, `GET /api/quotes`, in-process TTL cache + single-flight, `FakeQuoteBackend` in tests.
- UI: As-of column + filter relabel; Live column; `quotes.js` rebinds on `quotes-refresh` after `#runs-results` swap; run detail Live row. Did not edit `portfolio.html`.
- Constraint: live archive has 0 `run_manifest.quote_symbol` stamps (immutable history). Display listing is stamp, else snapshot `quote_symbol`/`yahoo_ticker`, else folder ticker (no suffix map).
- Verify: `pytest packages/catalog_api/tests apps/analysis_web/tests` 147 passed; `eng_verify.py` PASS. Manual Yahoo `AAPL` + `ADYEN.AS` last print ok. Smoke on :8767: 50 Live cells, 31 unique listings, `/api/quotes` 200.
- No git commit (needs user agreement).
