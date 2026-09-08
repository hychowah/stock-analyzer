# Eng session 2026-09-08-ib-statement-merge

- Created: 2026-09-08T04:24:12Z
- Work type: W4
- Goal: Merge overlapping IB activity statements into a trade ledger plus latest snapshot (IbBook)

## Log

- 2026-09-08T04:24:12Z scaffolded
- Absorbed SDR reshape: load a book, not a restuffed IbStatement.
- Types: `IbBook`, `IngestResult`, `trade_fingerprint`, in-file `dedupe_trades`.
- Store schema v2: trades are account-level (no CASCADE). `ingest_statement` upserts snapshot children, appends new fills. `load()` returns IbBook; snapshot.trades empty.
- v1 live sqlite migrated in place: 130 trades, 21 positions kept.
- CLI: inserted/skipped/conflicts; `--rebuild` replays archived U*.csv.
- /portfolio + API trade_count is the ledger; disclaimer on snapshot vs trades.
- Tests: overlap, reverse order, re-ingest A does not drop B, second account refused, v1 migrate, rebuild.
- Verify: pytest analysis_web 251; eng_verify PASS 859; Playwright 8772 desktop+mobile.
- Debt pass: `load()` no longer commits schema on every GET (would bump sqlite mtime and live-reload `/portfolio`). Migrate v1 only when needed; second load leaves mtime unchanged.

## Refactors

- Replaced `replace_statement` with `ingest_statement`. Split report (`IbStatement`) from book (`IbBook`) so period dates cannot filter the ledger.
