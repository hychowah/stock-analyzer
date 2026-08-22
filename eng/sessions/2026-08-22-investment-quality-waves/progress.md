# investment-quality-waves (2026-08-22)

## Goal
Three W1 waves on `harness/investment-quality-waves`: (1) enforce existing law 2.9.0, (2) decision object, (3) epistemology. No archive mutation. No Wave 4 mandate pack.

## Status
Waves 1–3 implemented on `harness/investment-quality-waves` (2.9.0 / 2.10.0 / 2.11.0). Implementer does not flip `passes`.

## Verify (implementer-run)
- pytest Wave 1 related: 134 passed
- `python scripts/eng_verify.py` PASS (VERSION bumped vs main, 11 runtime paths)
- cheap_claim omit: 2.9.0 FAIL twice; legacy SKIPPED

## Notes
- Live catalog dirt on `archive/catalog/*` is **out of scope** (do not commit).
- Implementer does not flip `passes: true`.
