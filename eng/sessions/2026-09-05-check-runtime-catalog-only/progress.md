# 2026-09-05-check-runtime-catalog-only

Shipped 2.36.0.

- N1: Check catalog is the only when-table. Named session→rows functions; leftover CLI sandwich on the catalog; `check_session` is argparse + `run_catalog` + print. `check_path` lives in `check_core`. No `record()`.
- N2: `StreetY1Policy.for_session` is the Street-era floor. Destock and bind bands/hooks apply one policy object. Hygiene is `check_street_hygiene`, not inside `check_street_bind`.
- Later (not this increment): merge phase-file tables.

`eng_verify.py` PASS (725 pytest). `pins/2.36.0` published.
