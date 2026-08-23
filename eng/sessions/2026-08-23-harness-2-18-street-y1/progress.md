# Progress — harness 2.18 Street Y1

Mode B W1. Implementer does not mark `passes: true` except orient.

## Done

- Bumped `harness/VERSION` to **2.18.0**.
- Street FY+1 is required base Y1 (`used_as:fy1_baseline`; `|delta|>5%` FAIL; `keep_independent_vs_street` illegal).
- Wave 3 + Wave 4 inverted when Street is usable: destock analog in bear PASSES; destock-in-base FAILS (DU=low is not an escape).
- 1d_merge / 1d_rev / Agent 5 4d/4e / Agent 13 4-street / Pair 0 / Pair 6 replaced (not appended).
- Same-period typed box floor (`guidance.revenue_box_*` vs `street_bind.intra_year`).
- Stacking pair FAIL: `volume_vs_guide` ∧ `sbc_in_fcff` in base while Y1 off Street band.
- TV>75% any-g requires DU=low or extend/switch; bear TV>1 requires `bear_tv_role=stress_only`.
- §10d.1: ROIC numerator is DCF NOPAT (no second SBC subtraction). `fcff_identity` schema added.
- Agent 11: DU=low leads with cone + pass.
- Tests: `test_wave10_street_y1.py` plus version-gated street_bind / wave3 / wave4.
- Live META A/B not rewritten.

## Not in this increment (plan W2)

- Catalog `comparable_only` still only `fv_base IS NOT NULL`. Snapshot already has `decision_usefulness`; `rebuild_catalog.py` does not project it. Follow-up W2.

## Verify

```
python -m pytest scripts/tests/test_street_bind.py scripts/tests/test_wave3_epistemology.py scripts/tests/test_wave4_destock_default.py scripts/tests/test_wave10_street_y1.py scripts/tests/test_wave8_readme_cio.py -q
python scripts/eng_verify.py
```
