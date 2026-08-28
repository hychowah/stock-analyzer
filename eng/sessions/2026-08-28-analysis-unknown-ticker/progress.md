# Eng session 2026-08-28-analysis-unknown-ticker

- Created: 2026-08-28
- Work type: W4
- Goal: Abort analysis when the user types a ticker that is not in the catalog.

## Log

- Scaffolded W4 session.
- CatalogApi: `ticker_in_catalog` / `require_ticker` / `TickerNotFound`.
- Runs list, fragment, `/api/runs`, and `/compares?ticker=` abort HTTP 404 with Aborted copy when the typed ticker/prefix is unknown.
- Known ticker + other filters with zero rows still 200 “No runs”.
- Tests: `test_analysis_web` + `test_catalog_api` 84 passed.
- HTTP smoke on fixtures :8767: `/?ticker_prefix=ZZZNOPE` 404; `/?ticker=META` 200; `/api/runs?ticker=NOPE` 404; `/compares?ticker=NOPE` 404.
