# roic-identity-gate (2026-08-22)

## Goal
Same-script owner-earnings ROIC as a Street-bind-class gate on Agent 5. Dual column A/B. Legal exits when mid-cycle ROIC ≤ WACC. Cheap-claim cannot be franchise_mos on below/approx. Thin lookback into snapshot + run_metrics.

## Status
Implementation complete. Implementer does **not** flip `passes` or write `ship_note`.

## Verify (implementer-run, not a ship_note)
- `python -m pytest scripts/tests/test_roic_identity.py scripts/tests/test_street_bind.py scripts/tests/test_gates_preflight.py scripts/tests/test_provenance.py -q` → 72 passed
- `python scripts/eng_verify.py` → PASS (VERSION 2.8.0 bumped with 13 runtime paths)
- `python scripts/check_session.py --ticker GT --date 2026-08-22 --full` → 126 passed, 0 failed; `roic_identity` SKIPPED (harness 2.7.0)

## Notes
- Clone Street skip: `parse_semver is None` ⇒ not runtime.
- No archive/fixture snapshot refresh.
- `run_metrics.posture` stays cheap/fair/expensive.
