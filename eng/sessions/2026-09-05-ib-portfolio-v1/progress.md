# Eng session 2026-09-05-ib-portfolio-v1

- Created: 2026-09-05T00:45:36Z
- Work type: W4
- Goal: Ingest IB activity statement into app-local sqlite and show NAV/TWR plus a statement-true performance graph on /portfolio

## Log

- 2026-09-05T00:45:36Z scaffolded
- Absorbed strategic design review: sqlite-only book, three modules, IB identity, one FX rule, HTML performance (no chart JS).
- Copied a gitignored IB activity CSV/PDF into `.local/ib/statements/`. Import CLI stored every `Trades,Data` row; `value_base` sum matches NAV Stock. No Name/Address in the object or DB.
- Parser `ib_statement.py`, store `portfolio_store.py`, view compose in `portfolio.py`, CLI `import_ib.py`. `/portfolio` HTML waterfall + MTM bars.
- Tests: fixture mini CSV; JSON fallback unchanged; corrupt sqlite does not fall back to JSON.
- Verify: `pytest apps/analysis_web/tests` 153 passed; `eng_verify.py` PASS (706). Selenium :8771 desktop + mobile. Existing :8765 is old code until restart.

## Refactors

- Did not dual-write `portfolio.json`. Mapping is a view-time function, not a sqlite `symbol_map` table.
