# investment-quality-waves (2026-08-22)

## Goal
Three W1 waves on `harness/investment-quality-waves`: (1) enforce existing law 2.9.0, (2) decision object, (3) epistemology. No archive mutation. No Wave 4 mandate pack.

## Status
Wave 1 committed (2.9.0). Wave 2 implemented (2.10.0): `registry/decision.json` including pass; initiate blocked on useless cone; TA `side=pass` legal; duration pass + TA long legal (C2 demoted). Implementer does not flip `passes`.

## Verify (implementer-run)
- pytest Wave 1 related: 134 passed
- `python scripts/eng_verify.py` PASS (VERSION bumped vs main, 11 runtime paths)
- cheap_claim omit: 2.9.0 FAIL twice; legacy SKIPPED

## Notes
- Live catalog dirt on `archive/catalog/*` is **out of scope** (do not commit).
- Implementer does not flip `passes: true`.
