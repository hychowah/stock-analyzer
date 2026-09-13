# Eng session 2026-09-13-valuation-constitution

- Created: 2026-09-13T05:28:51Z
- Work type: W1
- Goal: A+B valuation constitution: value vs price and engine from the asset (harness 3.1.0)

## Log

- 2026-09-13T05:28:51Z scaffolded
- Implemented A+B constitution as harness 3.1.0: required `iv_playbook` + `terminal_consistency`; price recipes (NAV/ARR/exit/TTC) cannot be `fair_value.base`; sector modules KPI/stress only; Agent 5 classifies on the router; Agent 13 grades engine without re-valuing. C/D/E (funded g, truncation, Street-as-prior) not in this bump.
- `python scripts/publish_harness_release.py` → `pins/3.1.0/`
- `python scripts/eng_verify.py` PASS (1122 tests)
