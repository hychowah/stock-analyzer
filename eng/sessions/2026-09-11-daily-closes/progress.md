# Eng session 2026-09-11-daily-closes

- Created: 2026-09-11T00:00:00Z
- Work type: W4
- Goal: Daily closes live on disk; heatmap GETs read them; Yahoo is a writer, not a click

## Log

- Scaffolded
- Implemented DailyCloses (`daily_closes.sqlite` in local home) + CloseRefresh (Yahoo writer).
- Retired HistoryService RAM TTL. GET `/mtm-interval`, `/mtm-path`, alt-history marks, and `/price-history` read `series()`. `/portfolio` HTML primes CloseRefresh without waiting. IB CLI import waits on ensure. Idle pass every 30 minutes.
- Live NAV stays QuoteService last prints.
- Heatmap JS caches an interval body only when it has rows (empty store is not sticky).
- Tests: pytest targeted suite 95 passed; `eng_verify` PASS 1033.
- Design-review reshape: `series(listings)` has no `since`; GET `/price-history` is store-only; CloseRefresh no longer owns the IB book or idle; `create_app(history_backend=)` (no PYTEST sniff); run-detail HTML primes `quote_listing`.
- Implementer did not flip `passes: true` (verifier role).
