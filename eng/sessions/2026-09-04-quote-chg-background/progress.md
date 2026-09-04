# Eng session 2026-09-04-quote-chg-background

- Work type: W4
- Goal: Green/red background chip on live price-change % (runs list + run detail)

## Log

- Scaffolded. Plan: chip on the `%` span, CSS-only, both Live surfaces.
- Strategic design review: from-scratch test passed. Absorbed (1) no shared `--pass-bg` tokens, (2) group chip chrome once, (3) dedicated CSS background test, not hung on the home smoke.
- Implemented grouped chip chrome + per-sign background in `app.css`. Dedicated `QuoteChgChipCssTests`. No JS/API/catalog/harness change.
- Verify: `pytest apps/analysis_web/tests` 120 passed; `eng_verify.py` PASS (673). Selenium on :8765: home 17 up / 29 down chips with `#bbf7d0` / `#fecaca`; hover keeps chip; 0% muted transparent; run detail 1 up chip; mobile same as desktop. 4 Live cells stayed em dash.
