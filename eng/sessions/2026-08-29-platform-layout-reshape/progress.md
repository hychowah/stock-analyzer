# Eng session 2026-08-29-platform-layout-reshape

- Created: 2026-08-29T01:08:29Z
- Work type: W1
- Goal: Reshape platform layout: kd_research package, one archive root, colocated tests, harness schemas/modules, vendor MCP

## Log

- 2026-08-29T01:08:29Z scaffolded
- Filled feature_list A/B/C from the platform-layout-reshape plan. Starting increment A (kd_research package + archive root + colocated tests + delete _legacy). Catalog JSON dirty files left unstaged.
- Increment A implemented: `packages/kd_research` (incl. `scaffold.py`, `catalog_rebuild.py`), env-aware `archive_root`, no repo-root session scan, tests colocated, `scripts/_legacy` deleted, VERSION 2.23.0. `python scripts/eng_verify.py` PASS (544 tests). Implementer does not mark `passes: true`.
- Increment B implemented: Mode A schemas → `harness/schemas/`; sector/region modules → `harness/modules/`; VERSION 2.24.0. `eng_verify` PASS.
- Increment C implemented: MCP trees → `vendor/mcp/`; `.mcp.json` and `archive/README.md` paths updated; no VERSION bump.
- Second-pass 1–3: live path strings + shrink TICKER_BLOCKLIST; pytest.ini pythonpath + tests import PROJECT_ROOT; scaffold tests import packages.kd_research.scaffold; spawn-gate library vs CLI split; catalog/compare/experiment_summary use default_archive_root(). VERSION 2.25.0.
- Leftover reshape debris (small): `harness/schemas/sec_filings.schema.json` scripts/kd_research → packages/kd_research; check_session `TEMPLATES`/`no template` → `SCHEMAS`/`no schema`; plan_mode_a_analyze_ui ROOT_RESERVED_NAMES + worker allowlist; merge duplicate paths imports; drop unused test ROOT/Path and leftover `# noqa: E402`. VERSION notes updated; still 2.25.0 (uncommitted vs main).
