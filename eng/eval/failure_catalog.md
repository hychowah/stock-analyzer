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
| F11 | Catalog runs lack model/harness identity | Snapshot/finalize not stamping provenance | W1 |
| F12 | Mode A runtime changed without version bump | Forgot `harness/VERSION` on W1 ship | W1/W5 |
| F13 | Next session cannot resume; half-done mess | No commit / no progress note after increment | W5 |
| F14 | New valuation barely moves prior FV | Cross-session anchoring; Agent 5 saw old snapshot | W1 |
| F15 | Same-day re-run overwrote prior folder | Scaffold used --force / no auto __rN | W1 |
| F16 | Agent opens yesterday’s session before new scaffold | “Check if prior is usable” orientation | W1 |
| F17 | Valuation subagent runs before phase 2_parallel | Phase graph / preflight skipped | W1 |
| F18 | Agent committed without user asking | Missing user-agreement gate on git commit | W5 |
| F17 | Technical lens cites valuation/FDD paths | Agent 4 context contamination / solo mega-context | W1 |
| F18 | phase_status complete / pending lag vs disk | Orchestrator resume map not updated | W1 |
| F19 | Missing phase0/phase25 swarm handoffs | Merge without decision-grade swarm lead note | W1 |
| F20 | medium/high intensity all market_context_hooks noted_only | Hollow region treatment | W1 |
| F21 | Branded CPG/eggs labeled cyclical | Module ANY-of Rule 3 (“linked to” commodity) overrode §5; audit rubber-stamped sector_fit | W1 — **machine FAIL** on harness ≥ 2.9.0 (`sector_identity_tripwire`); Agent 13 tripwire is **major** |
| F22 | MoS vs residual-claim DCF narrated as franchise cheap while mid-cycle ROIC ≤ WACC / EV≈IC | Agent 5 DCF and Agent 12 ROC screen never had to agree; Gordon `g` with capex≤D&A; `terminal_consistency` disclosure instead of identity | W1 — 2.8.0 `roic_identity` + 2.9.0 `roc_vs_cheap_claim` (TSR fail + franchise_mos without above_wacc) |
| F23 | Template 30/45/25 scenario masses with a fig-leaf rationale | Machine only checked sum=1.0 | W1 — FAIL on ≥ 2.9.0 without `probability_method` + numeric counterfactual |
| F24 | `priced_for_perfection` from price≷base/PW; catalog PFP null | Extracted only top-level `valuation.priced_for_perfection`, not `reverse_engineering` | W1 — named-dial gate + extract from reverse_engineering |
| F25 | Wide FV cone still presented as a target; `inside` band on 6× span | `decision_usefulness` prompt-only; outcomes scored `inside` | W1 — DU required on width trigger; `fv_band_at_mark=ineligible` when span>100% |
| F26 | Audit PASS used as buy-list / calibration default | `CatalogApi.calibration(pass_only=True)`; `/calibration` default yes | W1 — defaults false; UI label says completeness not a buy list |
| F27 | Always-long technical setup; no pass action; README invents a second verdict | Agent 4 required stop-below-entry; no decision.json | W1 — 2.10.0 `side=pass` legal; duration.action including pass; initiate blocked on useless cone |

Add rows when audits or production incidents recur.
