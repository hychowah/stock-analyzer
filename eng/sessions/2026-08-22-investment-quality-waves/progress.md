# investment-quality-waves (2026-08-22)

## Goal
Persona-review prompt-law waves 4–9 after 2.11.0 (destock default → mid-cycle → decision-after-2.5 → gather → README CIO → stop-the-plug). Waves 1–3 already shipped. Not the old Wave 4 mandate pack. No archive mutation.

## Status
Waves 1–4 implemented (through 2.12.0 destock default). Wave 5 mid-cycle construction implemented (2.13.0): last-year/peak cannot license above_wacc/franchise_mos. Next: Wave 6 decision-after-2.5. Implementer does not flip `passes`.

## Verify (Wave 4)
- pytest `test_wave4_destock_default.py` + `test_wave3_epistemology.py`: 30 passed
- `python scripts/eng_verify.py` PASS (VERSION 2.12.0 vs main)

## Verify (Wave 5)
- pytest `test_wave5_midcycle.py` + `test_roic_identity.py` + Wave 4: 53 passed
- `python scripts/eng_verify.py` PASS (VERSION 2.13.0 vs main)
- Live catalog dirt on `archive/catalog/*` is **out of scope** (do not commit).

## Verify (implementer-run)
- pytest Wave 1 related: 134 passed
- `python scripts/eng_verify.py` PASS (VERSION bumped vs main, 11 runtime paths)
- cheap_claim omit: 2.9.0 FAIL twice; legacy SKIPPED

## Notes
- Live catalog dirt on `archive/catalog/*` is **out of scope** (do not commit).
- Implementer does not flip `passes: true`.
