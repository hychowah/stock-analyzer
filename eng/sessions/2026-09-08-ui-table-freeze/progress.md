# Eng session 2026-09-08-ui-table-freeze

- Created: 2026-09-08T01:31:38Z
- Work type: W4
- Goal: Entity lists are a spreadsheet freeze pane at every width

## Log

- 2026-09-08T01:31:38Z scaffolded
- Implemented `.table-freeze`: 2D pane (`overflow: auto`, `max-height: 70vh`), lead-strip sticky (first column, plus `.pick + *` on Runs), opaque paint only on frozen cells. Deleted `.stack-table` phone card restyle and card `overflow-x`. Callers wrap only — no `.sticky-id`.
- Wrapped Runs, Portfolio positions, Analyze, Compares, Experiments, Calibration. Dropped `desktop-only`, `data-label`, `.cell-label`.
- Tests rewritten to the freeze contract. README: freeze pane, not stacked cards.
- Implementer checks (not a verifier flip): `pytest apps/analysis_web/tests` 226 passed; `eng_verify.py` PASS (834). Playwright on `:8779`: desktop and 390×844 / 844×390 stay `<table>` (not cards); pane scrolls both ways; titles and ticker/symbol stay; page `scrollWidth === clientWidth`; Night frozen cells use `--card`; row hover tints MoS through transparent unfrozen cells; sort header and compare pick still work; live ticker filter swap keeps the pane; Portfolio Symbol and Analyze Ticker freeze at `left: 0`.
- smart-commit debt pass: dropped leftover `.cell-label` clip CSS and `quotes.js` take/restore helpers (templates no longer emit the span). Left `feature_list` `passes: false` (gen ≠ eval). Did not write a verifier `ship_note`.
