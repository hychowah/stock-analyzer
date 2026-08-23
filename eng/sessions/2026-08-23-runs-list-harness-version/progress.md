# Eng session 2026-08-23-runs-list-harness-version

- Created: 2026-08-23
- Work type: W4
- Goal: Show harness version on the research runs list and filter by a specific catalog version

## Log

- scaffolded
- filled issue.json + feature_list.json
- recent git: abef011 Street FY+1 (2.18.0); 16a9740 stop canned decay (2.17.0); 6f1d2c7 README duration (2.16.0)
- working tree already dirty: archive/catalog JSON indexes, investment-quality-waves, destock-street-law-freeze (not this session)
- baseline `python scripts/eng_verify.py`: PASS (129 tests) before product edits; no harness/VERSION bump needed (W4)
- **catalog-harness-filter:** exact `harness_version` on `_runs_filter_sql` / `list_runs` / `count_runs` / CLI `--harness-version`. Facet dropdown values sorted as semver (2.17.0 after 2.7.0). Allowlisted sort. Legacy sqlite without the column: list still works; filter returns empty; sort raises ValueError (HTTP 400) instead of 500.
- **runs-list-harness:** table column + Harness `<select>`; shared `runs_list_q` / `catalog_filters`; run detail Context row. No-JS GET and `/fragments/runs` live path.
- **verify:** `eng_verify.py` PASS (134 tests). Live HTTP on :8768: dropdown `2.1.0 … 2.7.0, 2.17.0`; `/?harness_version=2.17.0` selects that option; `/api/runs?harness_version=2.17.0` and fragment match; META r2 detail shows 2.17.0. CLI `list-runs --harness-version 2.17.0` returns AVGO/GT/MELI/META. No browser driver — HTTP smoke + TestClient used.
- **semver-sort + click-filter:** sqlite ORDER BY harness_version now uses major/minor/patch (2.17.0 > 2.7.0). First click sorts newest-first. Version cells are links that set the exact `harness_version` filter (live JS + no-JS href). Tests: catalog asc `2.4.0, 2.7.0, 2.17.0, 2.17.0`.

## Git

Not committed. Proposed subject: **Show harness version on the runs list and filter by exact catalog version**
