# 2026-09-12-harness-3-0

Harness 3.0.0 / spec v3. Ready-set DAG + Damodaran lock-then-compute.

- Plan revised after team review (`tmp/harness-3.0/PLAN.md`, `REVIEW.md`).
- Graph: `PhaseNode.subagent_priors` / `subagent_entry`; `< 3.0.0` overlay restores 2.44 joins.
- Street: independent Y1 default on ≥ 3.0.0 (`StreetY1Policy.INDEPENDENT`).
- Catalog: `damodaran_gates.check_damodaran_v3`.
- Pin: `pins/3.0.0/`.
- `eng_verify`: PASS (1101 tests).
- No git commit (user agreement required).
