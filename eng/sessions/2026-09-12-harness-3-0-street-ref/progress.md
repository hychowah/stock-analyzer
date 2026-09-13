# Eng session 2026-09-12-harness-3-0-street-ref

- Created: 2026-09-12T14:30:34Z
- Work type: W1
- Goal: Restore Street FY+1 as the default Y1 forecast on harness 3.0.1; independent Y1 needs a named gate

## Log

- 2026-09-12T14:30:34Z scaffolded
- Street Y1: `StreetY1Policy.STREET_REF` on >= 3.0.1 (`fy1_baseline_required`, `gate_optional=False`). 3.0.0 keeps `INDEPENDENT`.
- `story_fail` on >= 3.0.1 requires `narrative_bind.street_restory.will_own=false` (40-char hatch is 3.0.0-only).
- `ttc_midcycle` accepts `primary_sector=cyclical` or a cyclical overlay on `narrative_bind`.
- Live §10c: Street is the default Y1 forecast. Independent default / no-gate is `law_history.md` 3.0.0.
- Agent 13 4-street grades live law on >= 3.0.1; loads history when `< 3.0.1`.
- Schema `independence_gate` enum adds `story_fail` and `ttc_midcycle`.
- Pin: `pins/3.0.1/`.
- Reshape: named exits and `story_fail` tightness live on `StreetY1Policy` (`legal_gates`, `story_fail_requires_will_own`). `GATED` is `GATES_228`; `INDEPENDENT` and `STREET_REF` are `GATES_300`; only `STREET_REF` requires `will_own=false`. `street_bind` applies those fields. Deleted `GATES_SINCE_300` / bind-side version `if`s for the gate set.
- `eng_verify`: PASS (1110 tests) after Street-default; reshape Street tests 84 passed; pin copies refreshed.
- Not in this increment: required Gordon TV, sector-cookbook demotion, truncation-at-life-cycle, implied ERP.
- No git commit (user agreement required).
