# Eng session 2026-09-08-alt-history

- Created: 2026-09-08T08:16:50Z
- Work type: W4
- Goal: Alternative histories under /portfolio/histories

## Log

- 2026-09-08T08:16:50Z scaffolded
- Absorbed SDR (Direction mixed → reshape): one cash book. Actual and alt use the same `mark` (cash + Σ qty × daily close × stmt_fx). Today’s Δ is that mark at today, same as the chart end. Do not call Live NAV / last print from what-if. Persist `fork_date`. Replay already-priced fills. Listing is on the lot from increment 1.
- `book_state.py`: `as_of_book` walks snapshot lots/cash with stock fills only. Mini fixture: Jan 5 empty, Jan 12 0700.HK=100, Feb 1 META=12, Mar 31 snapshot.
- `mark_book.py`: sibling of `mark_live_nav`; unquoted lot contributes 0 + flag.
- `alt_history.py` + `alt_history_store.py`: priced-fill replay; catalog/Yahoo at POST; overlay sqlite never writes IB trades.
- Pages: `/portfolio/histories`, `/new`, `/{id}`. Portfolio sub-nav Book · What-if. No `live_nav.js` on what-if.
- Playwright :8774 desktop+390px: create fork 2026-03-01, duplicate, sell ACGL, overlay chart, card Δ matches; `/portfolio` still GET `/api/portfolio/live-nav` only. Smoke histories deleted.
- Tests: analysis_web what-if 38 passed; full analysis_web 312; `eng_verify` PASS 915.
- SDR reshape + UI: copy whole IB stock ledger first (no fork-date form). Date picker shows holdings that day, including names later sold. Sell is listing-keyed qty on the row. History is a typed aggregate; add/delete trial-replay; real sells after a what-if sell clip. Sticky NAV/cash are today. Lots emit one per listing.
- Latest SDR (compact): Direction mixed / reshape. See `CONTINUE.md`. Persist seed on History; actual must replay the copy’s real fills, not live `as_of_book`. Rewrite `handoffs/plan.md`. Not commit-ready.
- Absorbed that SDR: `History.seed` frozen at copy; `Actual = mark(replay(seed, real fills))`; `Alt = mark(replay(seed, overlay_fills))`; later real sells clipped in `overlay_fills`, not inside `replay`; persist via `save(History)`. Live IB is not walked on compare/deceased. Copied IB buys may still run cash negative (statement cash is approximate); what-if buys cannot overspend. `handoffs/plan.md` rewritten (fork-and-hold deleted). Implementer does not flip `frozen-paper-book` passes. Not commit-ready.
- Next SDR (mixed / reshape): HTTP still `load_ib_book()` on list/editor/JSON/POST; FX from live statement. Plan increment `history-only-after-copy` written. Do not implement until agreed.
- Implemented `history-only-after-copy`: `BookState.fx_by_ccy` + `fx_for` frozen at `as_of_book`/`seed_book`; `resolve_buy`/`resolve_sell` take `History`; list/editor/JSON/POST buy-sell do not load IB. GET `/new` is the only IB read. Named `fx_by_ccy` (not `stmt_fx`) so it does not collide with `Lot.stmt_fx`. Implementer does not flip `passes`.
- Smart-commit debt pass: ship_note matches copy-and-overlay; plan/CONTINUE IB-only-at-copy; list/editor FX copy says frozen at copy; overlay chart asserted in `test_copy`; `local_dir` docstring mentions the overlay. Did not flip `passes`.

## Refactors

- Cash-book type is new, not Live NAV with extra parameters. `mark_live_nav` snapshot identity stays on `/portfolio`.
- Compare identity moved off live `as_of_book`. A history is self-contained: seed JSON + fills in overlay sqlite. Re-ingest of `portfolio.sqlite` cannot change a saved Δ.
