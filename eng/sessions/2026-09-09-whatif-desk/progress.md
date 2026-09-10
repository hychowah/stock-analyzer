# Eng session 2026-09-09-whatif-desk

- Created: 2026-09-09
- Work type: W4
- Goal: What-if desk: holdings display math, combined buy/sell ticket, frozen-FX sentence, JSON POST without reload, client sort

## Log

- Scaffolded.
- Locked unknowns from the user: Downside vs the close on the row; weight vs quoted stock; FX and IB-join as planned.
- Probe: history `test` (id 1) has empty `fx_by_ccy` but a USD lot with `stmt_fx` 7.8397. History `Test2` (id 2) has USD 7.8397 on the map. Catalog US names are currency USD (AAPL/COHR empty). IB 700 → 0700.HK; HY9H → 000660.KS via `catalog_lookup_tickers`.
- Implemented: `CatalogSnap` + `HoldingRow`; `ticket_block` / `missing_fx_message`; `BookState.fx_for` uses a lot’s frozen `stmt_fx` when the map is empty (not a 1.0); TradeDesk (search + research list + one ticket for buy and sell); JSON POST `Accept: application/json` does not navigate; fills fragment; client header sort.
- Tests: histories/alt_history/book_state/templating 72 passed. `eng_verify` PASS 981.
- Live HTTP on :8777 (new process; :8765 was old code): editor has Weight/Downside/MoS, search, desk; no “Sell stays”; no `live_nav.js` / `data-downside-pct`. Held join: 0700.HK MoS 31.5, 2318.HK MoS 29.6 (padded overlay), HY9H MoS -136.2 (GDS overlay), 1008.HK uncovered —. History 1 USD ticket for ACGL is pickable with a cost (lot FX fallback). Did not POST a live fill.
- Playwright MCP browser was locked (`Browser is already in use`); JS click-path not exercised in Chrome. JSON POST 200 covered by fixture tests.

## Refactors

- One catalog projection (`CatalogSnap`) for the research list and the holdings join, instead of a dict bag plus an ad-hoc overlay.
- Frozen FX lookup lives on `BookState.fx_for` (map, then lot rate). Callers do not special-case empty maps.
- Ticket failure copy is one function (`ticket_block`), used by preview, pickable, and POST.

- SDR (Direction mixed → reshape): CatalogSnap all the way through the desk; one ticket policy. Dropped `buy_universe`, `_as_snaps`, and `quote_listing` on snap JSON. `EditorPage.universe` is snaps. `BuyCandidate` is snap + mark + block. Persist allowlist is `snap_for(catalog_snaps)`.
- SDR #2 (Direction mixed → reshape): One Ticket. Preview and persist are `Ticket` (`build_ticket` / `persist_ticket`). POST no longer has `resolve_buy`/`resolve_sell` or a separate `assert_buyable`. Empty snap currency is a block, not silent base/1.0. Buying power is on the ticket block. JS confirm is disabled iff block or empty qty; error text is `block.message`.

## Resume

Verifier: flip `desk` / `implement` after checking the Chrome sell-without-reload path if Playwright is free. Do not `git commit` until the user agrees.
