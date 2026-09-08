# Eng session 2026-09-08-live-nav

- Created: 2026-09-08T06:21:44Z
- Work type: W4
- Goal: Live NAV on /portfolio from holdings x Yahoo last print; one marked-book poll

## Log

- 2026-09-08T06:21:44Z scaffolded
- Absorbed SDR (Direction right / proceed): one marked-book poll, lots not catalog view, one print listing.
- Join emits `print_listing` via `holding_print_listing` (holding market) + `stmt_fx`. Catalog overlay stays for research join only.
- `live_nav.py`: `mark_live_nav(lots, quotes, *, ending_nav, cash)` identity formula. `GET /api/portfolio/live-nav`.
- `/portfolio` `data-quote-poll="0"`; `live_nav.js` is the only Yahoo-facing fetch; `quotes.js` paints from `quotes-applied`.
- GDS trap: `HY9H` on FWB was marked with `000660.KS` KRW (~249M vs 2.0M statement). Print listing now stays on the holding (`HY9H` → 1140). Live NAV ~1.985M HKD vs statement 2.031M (−2.29%).
- Tests: analysis_web 269 passed; `eng_verify` PASS 877. Playwright :8773 desktop+390px: Live NAV paints; network is `/api/portfolio/live-nav` only; Runs still GET `/api/quotes`.
- Header drop: Period, Ending NAV, deposits, TWR, stock/cash, Δ vs statement, IB Close / Value (base). Card is Live NAV + day P/L.

## Refactors

- Split catalog overlay from print listing: `_PRINT_OVERRIDES` (suffix forms) vs `_CATALOG_OVERRIDES` (includes GDS → local). Unknown IB exchanges keep the IB symbol rather than falling back to a research stamp.
