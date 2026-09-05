# 2.36.0 — catalog is the only when-table; one Street policy

Design review of 2.34.0–2.35.0: trajectory is right (catalog + check_core + knowledge homes). What shipped is still a patch around the old God modules. This increment finishes that from-scratch shape for the two `this change` items. Phase-files table merge stays later.

## Constraints

- No Mode A statute / prompt / FAIL-WARN band changes
- Do not rewrite `pins/2.34.0`, `pins/2.35.0`, or `archive/research`
- No `session_checks.py` / `phase_coverage.py` / `agent4_isolation.py`
- Path-evidence tables (`PHASE_ENTRY_*`, `PATH_EXTRAS`) stay in `gates.py` until a later merge

## N1 — one CheckRow table

1. `CheckRow.run` is always `session → rows`. Delete unused `CheckRow.since`. No catalog lambdas, no `_year_dive_session_full` FDD strip, no `full=` / `include_reports=` adapters.
2. Named functions live in knowledge homes:
   - `isolation.check_agent4_isolation` / `check_agent4_isolation_full`
   - `decision_quality.check_wave1_decision_quality` (core vs reports via two names)
   - `decision.check_wave2_phase2_complete` / `check_wave2_phase4_complete` / `check_wave2_decision`
   - `annuals.check_year_dives` (no FDD exists row) vs `check_1c_year_dive_complete`
   - leftover CLI sandwich: identity/meta → `provenance`; MC/FDD content → `consumption`; brief/phase_status/handoffs/audit → `phase_status`; isolation → `isolation`; library → `library`; spawn → `spawn_gate`; risk_bridge → `decision`; structured files → `check_core.check_structured_file`
3. Move `check_path`, `_infer_ticker`, `_report_rows`, `check_reports` to `check_core`. Catalog does not import `gates`.
4. `scripts/check_session.py` is argparse + `run_catalog(session_core|session_full)` + print + optional `write_session_acceptance(rows)`. No `record()` / `results` global.
5. `entry_checks` / `complete_checks`: abandon short-circuit, phase-graph (needs `phase_id`), path tables, then `run_catalog`. LLM identity on `{phase}:entry` catalog tags.

## N2 — one StreetY1Policy

1. `StreetY1Policy.for_session` is the floor. `session_is_street_y1_runtime` / `session_is_gated_y1_runtime` are one-line facades on `policy.y1` / `policy.gated`.
2. Epistemology destock-in-base branches on `policy.y1` / `policy.gated` + `destock_this_print`, not a second 2.18/2.28 copy.
3. Collapse `_apply_y1_policy` statute returns and the hook-copy / `noted_only` / `fy1_baseline` ladder into one policy application (bands, legal responses, hook needles). Add `path_copy_legal` on the policy object if bind still needs it.
4. Pull conservatism dials / stacking / SOTP / box floor out of `check_street_bind` into `valuation_hygiene.check_street_hygiene(session)` and give it its own catalog row.

## Later (not this increment)

One `(phase, rel, required, since)` table next to `check_path`; `PATH_EXTRAS` leaves the check catalog.

## Version

`harness/VERSION` → 2.36.0 and `pins/2.36.0` in the same change set.
