# Eng session 2026-08-23-destock-street-law-freeze

Mode B W1. Implementer does not mark `law_surface_freeze` `passes: true`.

## Goal

Freeze current destock/Street law at harness **2.18.1**. Machines unchanged (Street Y1; destock analog in bear while Street usable). Live Agent 5 / §10c / HARNESS_MAP no longer teach 2.12 destock-in-base or 2.7 never-copy-Street as current.

## Done

- Bumped `harness/VERSION` to **2.18.1**.
- §10c is current-only; 2.7–2.17 calibration points at §13.
- §10b + `filing_deep_dive.md`: printed box low is a same-period floor; no “independent base path.”
- §13: unbounded ≥2.11 row keeps TV/RP/changelog; destock/Street-copy FAIL is `≥ 2.11.0 and < 2.18.0`.
- Agent 5 4d: dropped “this prompt is 2.18” historical parenthetical. 4e header is `harness ≥ 2.18.0` only.
- Agent 13 4-street historical grading kept.
- HARNESS_MAP specialist destock/Street is 2.18 current; `4d wins 4e` gone; pointer to §13.
- Pair 0 BAD `reason` is 2.18 (“Y1 destock while Street FY+1 is usable”); 2.12 wording in caption only.
- F28 stamped 2.11–2.17; F30 is destock-in-base while Street usable.
- `wave_list.md` + `wave4_destock_plan.md` HISTORICAL banners.
- `epistemology.py` docstrings only (no branch changes).
- Tests: `scripts/tests/test_law_surface_freeze.py`.

## Not in this increment

- Catalog `catalog_du` / comparable_only DU drop.
- 5b at `4_parallel` entry; Y2–Y8 destock clawback; `harness_at_least` helper collapse.
- Silent destock + DU=low PASS on 2.18 (machine).

## Verify

```
python -m pytest scripts/tests/test_law_surface_freeze.py scripts/tests/test_wave10_street_y1.py scripts/tests/test_wave4_destock_default.py scripts/tests/test_wave3_epistemology.py scripts/tests/test_street_bind.py scripts/tests/test_sector_classification_law.py -q
python scripts/eng_verify.py
```
