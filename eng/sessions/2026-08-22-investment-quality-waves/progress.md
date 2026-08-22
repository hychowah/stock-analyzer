# investment-quality-waves (2026-08-22)

## Goal
Three W1 waves on `harness/investment-quality-waves`: (1) enforce existing law 2.9.0, (2) decision object, (3) epistemology. No archive mutation. No Wave 4 mandate pack.

## Status
Wave 1 implemented (harness 2.9.0). `eng_verify` PASS. Alignment PASS-WITH-FIXES applied (A2 unique WARN; A7 no FCF classifier; A6 mixed SKIPPED). Implementer does not flip `passes`.

## Verify (implementer-run)
- pytest Wave 1 related: 134 passed
- `python scripts/eng_verify.py` PASS (VERSION bumped vs main, 11 runtime paths)
- cheap_claim omit: 2.9.0 FAIL twice; legacy SKIPPED

## Notes
- Live catalog dirt on `archive/catalog/*` is **out of scope** (do not commit).
- Implementer does not flip `passes: true`.
