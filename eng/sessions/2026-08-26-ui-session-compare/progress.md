# Eng session 2026-08-26-ui-session-compare

- Created: 2026-08-26
- Work type: W4
- Goal: UI: select two same-ticker sessions, spawn session-valuation-audit in the background, show README + synthesis

## Log

- 2026-08-26 scaffolded
- 2026-08-26 baseline: recent git `eff17ce` ticker library 2.19.0; branch main ahead 18
- 2026-08-26 implemented data plane `archive/comparisons/`, job runner (`packages/compare_jobs`), catalog read, UI picker + result pages
- 2026-08-26 compare packet helpers live in `packages/compare_jobs/paths.py` (not `scripts/kd_research/paths.py`) so this is not a Mode A VERSION bump
- 2026-08-26 `python scripts/eng_verify.py` PASS (178 tests)
- 2026-08-26 refactor: skill OUT moved from `archive/research/<T>/tmp/` to `archive/comparisons/` so Mode B never writes immutable research history

## Resume hint

Verifier should run eng_verify + a local UI click-through (two same-ticker sessions, Compare, README + synthesis). Implementer has not flipped `passes`. No git commit until the user agrees.
