# Session artifact map

Read both sides. Cite `A:<rel>` / `B:<rel>` (or the full path once). Skip a file if it does not exist; note the gap. Do not treat absence as a hidden number.

## Always

| Rel path | Why |
|---|---|
| `meta/run_manifest.json` | Harness version, git sha, models |
| `meta/prediction_snapshot.json` | Catalog-shaped FV / MoS / verdict (may be missing if not finalized) |
| `data/valuation_model.json` | Model choice, FV, assumptions with rationale |
| `data/compute/valuation.py` (or the `compute_script` named in the model) | Actual math |
| `data/compute/valuation_result.json` | Runtime outputs (filename may vary; follow `compute_script`) |
| `data/price_snapshot.json` | Freeze price and as-of |
| `reports/00_*_README.md` | Session orientation |
| `reports/01_*_fundamental.md` | Written thesis and action language |
| `registry/audit.json` | Process audit, not investment truth |
| `registry/risk_bridge.json` | Scenario masses / stresses |
| `registry/operating_path_brief.json` | Path identity (demand, margins, capex) |

## Usually present (read when there)

| Rel path | Why |
|---|---|
| `registry/decision.json` | First-class action / cheap_claim (newer harness) |
| `registry/latest_quarter.json` | Print facts both sessions should share or diverge on |
| `registry/street_estimates.json` | Calibration, not a copy target |
| `registry/sec_filings.json` | Filing vintage |
| `registry/filing_deep_dive.json` | Accounting / segment detail |
| `data/market_inputs_snapshot.json` or `data/compute/market_inputs.json` | Rf, ERP inputs |
| `registry/raw/stress_*.json` and `registry/handoffs/phase25_*` | Phase 2.5 standalone stresses |
| `registry/handoffs/5_valuation.md` | Valuation handoff prose |
| `charts/` manifests / football-field | Cross-check published range, not a source of new math |

## Units and traps

- `margin_of_safety` is a 0–1 fraction; `margin_of_safety_pct` is percent points. Do not mix them.
- Probability-weighted FV is not the decision target unless the session says otherwise.
- Sessions may store dollars in billions vs raw USD, and shares in billions vs share count. Normalize before subtracting.
- `registry/audit.json` PASS grades provenance, not whether the DCF is right.
- Harness version gaps are methodological until proven otherwise. New facts between as-of dates are economic.

## Headline fields to extract

From `valuation_model.json` / `valuation_result.json` / `price_snapshot.json` / `run_manifest.json` / `decision.json` when present:

`harness_version`, freeze price + date, `model.name`, base/bear/bull/PW, MoS fraction and pct, `decision_usefulness`, posture, scenario masses, WACC, forecast years, TV share of EV, Y1 revenue / OM / FCFF, share count, net cash/(debt), `priced_for_perfection`, action verb.
