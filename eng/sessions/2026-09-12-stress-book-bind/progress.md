# Eng session 2026-09-12-stress-book-bind

- Created: 2026-09-12T09:53:57Z
- Work type: W1
- Goal: Stress book bind — shocked-path FV, size_cap / expected loss, Unstressed vs stressed report card

## Log

- 2026-09-12T09:53:57Z scaffolded
- Implemented harness 2.44.0:
  - Agent 5 compute script exposes `fair_value_under` / `--under`; `shock_surface.keys` required
  - Phase 2.5 workers return a shock, not a guessed haircut
  - `python -m packages.kd_research.stress_apply` derives `stressed_fv` and reverse_stress
  - `compute_stress_bind` is the one book policy (EL 4/8/12% → size 1.00/0.50/0.25/0.00)
  - `restates_bear` cannot bind; `size_cap=0` forbids initiate/add/hold
  - Reports heading `## Unstressed vs stressed` (README + fundamental)
  - 2.29–2.43 keep the 25/15 cliff (version-banded)
  - Pin `pins/2.44.0/`
- Third design-review reshape: §1 constitution — agents judge shock dials; code derives haircuts and size_cap (§10f). Agent 7/11 Show contract is copy format_stress_card only.
- Second design-review reshape: merged scenario list is Apply input; one `applied` block; Bind refuses unapplied bridge; drop `required_mos_addon` twin; schema haircut not required so merge-before-apply is legal.
- Design-review reshape (same 2.44.0, uncommitted):
  - `shock_surface.dials` with current values; `--under {}` must equal base
  - Merge shocks first; Apply stamps raws and risk_bridge and reverse-stress via `fair_value_under`
  - Bind reads applied FV only; numeric restates_bear; liquidity on every scenario
  - `format_stress_card` is the report projector
- Did not rewrite `archive/research/**`
