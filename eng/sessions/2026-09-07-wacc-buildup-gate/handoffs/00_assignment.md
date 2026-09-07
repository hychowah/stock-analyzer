# WACC-buildup identity — investing-persona harness review

This is **not** a two-session valuation audit. It is a Mode B review of **current WACC law and a draft 2.40 gate** so new research runs cannot repeat a known cost-of-capital failure.

**Do not rewrite** any `archive/research/**` session. CMCSA `2026-09-07` is a **read-only incident**, not a patient to operate on.

Repo root: `C:\Users\user\OneDrive\Documents\Stock Research`  
OUT: `C:\Users\user\OneDrive\Documents\Stock Research\eng\sessions\2026-09-07-wacc-buildup-gate\handoffs`  
Write **only** your assigned file. Read OUT only for this assignment (and README if present). Do not read other persona files.

## Incident (verified from session files; do not invent)

Session: `archive/research/CMCSA/2026-09-07` (harness 2.39-era run).

| Piece | Stored value | File |
|---|---|---|
| Price | $26.49 | `data/compute/valuation_result.json` |
| WACC | 6.145% | `data/valuation_model.json` `assumptions.wacc` |
| Ke | 9.092% | same, `assumptions.ke` |
| Rf | 4.784% (`^TNX`) | `data/market_inputs_snapshot.json` |
| Beta | 0.719 raw → 0.812 Blume | snapshot + script |
| ERP | 5.0% | snapshot |
| Kd pretax | **4.0%** (coupon buckets 3.3–4.2%) | `data/compute/valuation.py` `kd_pretax = 0.040` |
| Tax | 23% | script |
| Weights | we 51.0% / wd 49.0% at **current** market cap $94.0B vs gross debt $90.4B | `valuation_result.json` intermediates |
| Tape-implied WACC on base path | **9.13%** | reverse_engineering |
| Base FV | $59.83 | valuation_model |
| `cheap_claim` | `franchise_mos` because mid-cycle ROIC 10.01% vs WACC 6.14% | `roic_identity` |
| `wacc_vs_buildup` | `matches_buildup`, `applies_in=none` | conservatism_dials |

July 25 CMCSA session saw raw CAPM ~5.55% and added a **+345 bp** company premium to **9.0%**. Later harness taught “do not pad; match the buildup.” Sep 7 obeyed that and printed a utility-like 6.14%.

Current machine gates check that WACC **equals** the formula and that `wacc_vs_buildup` exists. They do **not** check Kd vs Rf, Kd source, or distressed weights.

## What is already law (do not contradict without saying so)

- No hardcoded regional WACC / ERP / family-control discounts (`region_integration.md`, Agent 5 prompt).
- Every decided number `{value, rationale, basis}`.
- `wacc_vs_buildup` conservatism dial: padding WACC above buildup as silent conservatism is the thing the dial was built to catch.
- ROIC identity hurdles **in-model WACC**. A too-low WACC falsely licenses `above_wacc` / `franchise_mos`.
- Agent 5 writes a **new** `S/data/compute/valuation.py` every session. There is no shared WACC calculator. Shared **checker** is the existing pattern (`roic_identity.py`).

## Draft 2.40 design (attack this; it is not locked)

Ship a `wacc_buildup` identity (same spirit as `roic_identity`). Agent 5 still judges Rf, beta, ERP, spread, and target weights. The machine fails **impossible ingredients**, not “WACC must be 9%.”

Required object on `valuation_model.json` when the model is an FCFF/WACC DCF (`applies:true`). `applies:false` with ≥40 char reason for banks / insurance / REITs / other non-WACC natives.

Draft fields:

| Field | Intent |
|---|---|
| `rf`, `ke`, `kd_pretax`, `kd_aftertax`, `tax`, `we`, `wd`, `wacc` | Scripted; WACC = we×Ke + wd×Kd(1−t) within 5 bp |
| `kd_source` | `current_yield` **or** `rf_plus_spread` only. Coupon may be disclosed as a cross-check; **illegal as the WACC input** |
| `weight_policy` | `current_market` \| `target` \| `blended` |
| `beta_policy` | `raw` \| `blume` \| `unlever_relever_target` (judgment; not all mandated in v1) |
| `distressed_equity_hook` | `none` \| `target_weights` \| `blended` \| `unlever_relever` |
| `kd_below_rf_gate` | hatch name or omitted |
| `wacc_minus_rf` | identity |
| `implied_wacc_gap_bp` | vs reverse-engineering when present |

Draft machine FAILs (new runtime ≥ 2.40.0 only; old stamps SKIPPED):

1. **Kd vs Rf:** `kd_pretax >= rf` unless `kd_below_rf_gate` resolves (`negative_rate_market` with local Rf evidence, or `current_yield_verified` with a quoted YTM in-session). Coupon-below-Rf as Kd is FAIL.
2. **Kd source:** `coupon` is not a legal `kd_source`.
3. **Weights:** `we + wd` ≈ 1. Going-concern DCF may not use **only** `current_market` when a distressed-equity tripwire fires: e.g. `wd > 0.35` **and** (implied WACC gap > 200 bp **or** equity at/below book). Then `target` or `blended`, with rationale.
4. **Arithmetic:** WACC matches the weighted formula within 5 bp; matches `assumptions.wacc` and `roic_identity.wacc`.
5. **Implied gap:** if reverse-engineered WACC is >200 bp above model, require `wacc_gap_rationale` ≥40 chars that is **not only** “tape is cheap / franchise MoS.” WARN if the rationale ignores Kd/weights. Do not FAIL the tape for disagreeing.

Keep `wacc_vs_buildup: matches_buildup`. Idiosyncratic risk is a **named Ke sleeve** (ops / size / governance) with use/reject — not a silent add-on after mixing with cheap debt.

**Do not** paste a WACC number into prompts or modules.

Hatch, not a number: Japan-style Kd < Rf; utilities may sit close to Rf but still WACC > Rf; net-cash tech can have tiny `wd`.

## Four questions (every auditor)

1. **Residual analysis error:** After this draft, how can Agent 5 still print a WACC that is economically too low or too high (Kd, beta, ERP, weights, leases, preferred, cash, local Rf, circular implied-gap)? Cite current prompt/law lines if the hole is already there.
2. **Wrong prompt:** What in Agent 5 / Agent 13 / `RESEARCH_AGENTS.md` would cause the CMCSA failure again, or cause a new failure if we add the draft text carelessly (contradiction with “no hardcoded WACC”, `wacc_vs_buildup`, dual-class = 0, ROIC franchise license)?
3. **Bad harness:** What would make the gate itself harmful — false FAIL on banks/REITs/Japan/utilities/net-cash, overfitting to CMCSA, easy to game (`rf_plus_spread` with 0 bp, target wd set to the trough wd, Blume toward 1 on a 0.3 beta), or a shared calculator that pastes rates?
4. **Load-bearing change:** What would you **require**, **drop**, or **add** before shipping 2.40? Rank by whether it would have caught CMCSA Sep 7 and whether it false-fails a healthy session. One shippable v1 vs later wave is allowed.

Lead with the answer. Stay inside your persona lens. Disagreement is useful.

## Files to read (this repo)

- `harness/RESEARCH_AGENTS.md` (especially §10c conservatism, §10d ROIC, §13 gates)
- `harness/agent_prompts.md` (Agent 5 and Agent 13)
- `harness/schemas/valuation_model.schema.json`
- `packages/kd_research/valuation_hygiene.py`
- `packages/kd_research/roic_identity.py` (pattern to copy, not WACC math)
- `harness/exemplars/rationale_quality.md` Pair 1
- `harness/exemplars/valuation_decision_quality.md`
- `harness/modules/region_us.md` (advisory; no mandated WACC)
- Incident only: `archive/research/CMCSA/2026-09-07/data/valuation_model.json`, `data/compute/valuation.py` (WACC section), `data/compute/valuation_result.json` intermediates, `data/market_inputs_snapshot.json`
- Optional contrast (isolation does **not** apply to this Mode B review): `archive/research/CMCSA/2026-07-25/data/valuation_model.json` WACC rationale

Do not browse other tickers unless you need a false-FAIL example; if you do, name the path.

## Assigned files

| File | Persona |
|---|---|
| `01_conservative_value_audit.md` | Conservative value |
| `02_quality_compounder_audit.md` | Quality compounder |
| `03_forensic_accountant_audit.md` | Forensic accountant |
| `04_valuation_process_audit.md` | Valuation process |
| `05_risk_pm_audit.md` | Risk PM |
| `06_reverse_engineer_audit.md` | Reverse engineer |
