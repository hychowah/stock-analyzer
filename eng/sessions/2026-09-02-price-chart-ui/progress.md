# Eng session 2026-09-02-price-chart-ui

- Work type: W4
- Goal: Interactive price history chart on run detail with catalog bull/base/bear overlay

## Log

- Scaffolded session.
- Plan: extract Yahoo daily-bar download into `yahoo_bars.py` (shared with last-print quotes). New `price_history.py` + `GET /api/price-history`. Run detail SVG chart with range buttons; overlay is catalog FV only. Sibling sessions as markers. No harness/VERSION bump.
- Git: `7901d34` live quotes already on main. Leave `archive/catalog/*` uncommitted.
- Implemented: `yahoo_bars.py` shared by last-print quotes and history. `GET /api/price-history`. Run detail SVG chart with 1M–MAX, catalog FV band/lines, as-of marker, sibling session markers.
- Verify: analysis_web + catalog tests 161 passed; `eng_verify.py` PASS (664). Live smoke on :8768: META 1y 253 bars, 3m 65 bars; overlay `fv_bear/base/bull` 149.34 / 493.9 / 961.07. Edge headless: 3M click redraws path; mobile 390px stage 222px.
- No git commit (needs user agreement). Do not include `archive/catalog/*`.
- Applied strategic design review: Y domain is price + base/as-of (bear/bull clip); removed live "price vs base" percent; stale range replies ignored via loadGen; HistoryService caches successes only; JS range allowlist is the buttons, Python `RANGES` is the Yahoo map.
- Follow-ups (not this slice): ticker-level chart; 1M intraday bars. Committing UI + eng session; leave `archive/catalog/*` uncommitted.

## Design

- Price path is Yahoo listing daily close (same `quote_listing` as Live). Not a catalog fact.
- Bear / base / bull / weighted / as-of are catalog `get_run` fields. Mode B does not compute FV.
- This run: full-width horizontal levels + vertical as-of marker.
- Other same-ticker sessions: range bar at their session date (click → that run).
- Timeline: 1M / 3M / 6M / 1Y / 2Y / 5Y / MAX. Default 1Y.
