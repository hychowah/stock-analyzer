# Eng session 2026-09-10-one-home-reshape

- Created: 2026-09-10T02:54:07Z
- Work type: W1
- Goal: One home per invariant; completed research is not rewritten by projection or verify

## Log

- 2026-09-10T02:54:07Z scaffolded
- Implemented four increments of the highest-leverage reshape:
  1. PhaseNode is the gate and the dump (display, handoff globs, versioned extras, price_snapshot as 2_parallel entry since 2.42.0).
  2. Operator files point at §10c–e; Agent 5/13 and HARNESS_MAP no longer restate Y1/ROIC/WACC.
  3. session_is_completed moved to session_state; export is insert-only; write_abandon refuses completed sessions.
  4. Mode B map/runbook thinned; eng_verify fails tracked completed research/outcomes instead of printing wallpaper.
- Bumped harness/VERSION to 2.42.0 and published pins/2.42.0.
- Refactored: deleted PATH_EXTRAS, PHASE_DISPLAY, HANDOFF_SPECS tables, operating_path.designed_phase_ids pass-through, and gates domain-check re-exports.
