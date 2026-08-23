## Summary

This W4 increment aligns with Mode B law. Catalog sqlite remains the source of `harness_version`; the UI/CLI only display and exact-match that stamp. `list_runs` still returns `list[dict]`, filter SQL is `harness_version = ?` (not LIKE/contains), table ORDER BY and the facet dropdown both use major/minor/patch so `2.17.0` sorts after `2.7.0`, and a legacy sqlite without the column lists runs, returns empty for a version filter, and raises `ValueError` (HTTP 400) on sort instead of 500. Shared `runs_list_q` / `catalog_filters` feed HTML, `/fragments/runs`, and `/api/runs`; CLI `--harness-version` calls the same `CatalogApi.list_runs`. No archive/research or outcomes writes, no invented FV/MoS, no `harness/VERSION` bump (correct for W2–W4), and listed pytest is green (71 passed). Working tree also has unrelated dirty Mode A / catalog files — they are not in this intended set and must not be staged with it.

## Issues

None.

## Verdict

- Aligns with eng law: yes
- Blocking issues (must fix before commit): none
- Commit recommendation: commit intended W4 set
- Suggested subject: Show harness version on the runs list and filter by exact catalog version

Stage only the intended paths (`packages/catalog_api/`, `apps/analysis_web/` listed files, `eng/runbook.md`, `scripts/tests/test_catalog_api.py`, `scripts/tests/test_analysis_web.py`, `eng/sessions/2026-08-23-runs-list-harness-version/`). Do not add `archive/catalog/**`, `harness/**`, `scripts/kd_research/**`, other eng sessions, or `scripts/tests/test_law_surface_freeze.py`.
