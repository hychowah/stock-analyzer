# Failure catalog (seed)

Systemic issues that should become eng work (W1–W5), not one-off chat fixes.

| ID | Symptom | Suspected cause | Work type |
|----|---------|-----------------|-----------|
| F1 | Mode B files never in git | Top-level folder named `build/` (gitignored) | W5 |
| F2 | Product dir scanned as ticker | `ROOT_RESERVED_NAMES` incomplete | W2 |
| F3 | UI shows empty after finalize | Catalog not exported / sqlite missing | W2 |
| F4 | UI crashes mid-list | Non-atomic index rewrite / no readonly open | W2 |
| F5 | Path traversal via report deep-link | Missing open_artifact containment | W2/W4 |
| F6 | Mode B agent runs Phase 0–5 | Root AGENTS mega-spec pollution | W5 |
| F7 | Finalize slow as archive grows | Full `rebuild_catalog` every run | W2 |
| F8 | Empty filing_deep_dive_hooks | Valuation skipped deep dive | W1 |
| F9 | Fixture numbers ≠ live | Path string binding / no re-export | W2 |
| F10 | Agent invents MoS in UI | Hardcoded demo numbers | W4 |

Add rows when audits or production incidents recur.
