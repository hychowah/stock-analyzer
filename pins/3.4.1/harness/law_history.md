# Mode A law history (JIT)

**Not current law.** Live Agent 5 / orchestrator must **not** load this file. Agent 13 loads it when `harness_version < 3.0.1` for Street bands (3.0.0 independent Y1 default; Street default Y1 2.28–2.44; required-Street 2.18–2.27; independent-then-calibrate 2.7–2.17; 2.44 graph joins). On 3.0.0–3.0.1, skip `4-engine` (omit-TV was legal); do **not** load this file for that skip. Stress-bind policy is machine-banded in `packages.kd_research.decision` — do not paste the 25/15 cliff into a ≥ 2.44.0 session.

Current Street/Y1/destock law: `harness/RESEARCH_AGENTS.md` §10c. Current stress book: §10f / §8 5b. Current machine gates: `harness/RESEARCH_AGENTS.md` §13 (unbanded). Current graph: `packages.kd_research.phase_graph` (`READY_SET_SINCE` 3.0.0). Current value-vs-price / playbook constitution: `packages.kd_research.damodaran_gates` (`CONSTITUTION_SINCE` 3.1.0).

---

## 3.4.0 — bind copied classification stamps; 3p locked the bind

Sessions stamped `3.4.0` copied `iv_playbook` / life-cycle / buyer / contest onto `narrative_bind`, matched them with twin checkers, and had the 3P critic set `narrative_bind.status=locked`. Sessions on ≥ 3.4.1 keep identity only on `classification.json`; lock is `narrative_3p.verdict=PASS`; Agent 5 writes `story_input_bind` and `buyer_dials` only.

## 3.3.0–3.3.x — Agent 5 classified and locked the story

Sessions stamped `< 3.4.0` have no phase `1e`. Agent 5 walked `valuation_router.md`, wrote `narrative_bind.json` (status=locked) in the same spawn as `valuation_model.json`, and stamped `iv_playbook` / life-cycle / buyer / market_contest itself. Sessions on ≥ 3.4.0 move engine classification to orch (`classification.json`) and the story lock to specialists `story` + `3p`. Agent 5 compute-only. 3.4.0 still copied stamps onto the bind; ≥ 3.4.1 does not.

## 3.3.0 — Tier-1 asset/buyer/option + life-cycle + market-neutral

Sessions ≥ 3.3.0 add: `contingent_claim` / `asset_based` primary ids and the buyer question; `narrative_bind` `life_cycle_stage` / `who_leads` / `stage_fit`, `buyer`, `market_contest`, `option_screens`, `distressed_call`; a required `truncation` assessment (`p=0` + `why_not_material`, or `p>0` weighted base); `wacc_buildup.erp_method` / `beta_method` / `discount_currency` / `cash_flow_currency`; and `per_share_bridge`. Sessions `< 3.3.0` keep 3.2.0 behavior (these gates SKIP).

## 3.0.0–3.0.1 — omit `terminal_consistency` / `iv_playbook` is not FAIL

Sessions stamped `< 3.1.0` keep the 3.0 confession-detector: missing `terminal_consistency` skips the TV and growth-triad gates; `iv_playbook` is optional; REIT NAV/AFFO may skip WACC. Sessions on ≥ 3.1.0 require a router playbook and a Gordon/liquidation/excess_return TV; exit/ARR/NAV as `fair_value.base` FAILs.

## 3.0.0 — independent Y1 default

Street FY+1 is a restory/calibration prior, not the DCF statute. Default `street_bind.response` is `independent_y1` (**no gate required**). `street_baseline` is legal when you explicitly copy Street as the Y1 level — then the 5% identity still applies. Legal gates when you name one: `destock_this_print` | `definition_mismatch` | `native_kpi` | `street_unusable` | `story_fail` | `ttc_midcycle`. `story_fail` may resolve on `will_own=false` **or** a ≥40 character rationale. `keep_independent_vs_street` remains illegal. Destock still never averaged with Street. Sessions on ≥ 3.0.1 restore Street as the default Y1 forecast; `independent_y1` needs a named gate; `story_fail` requires `will_own=false`.

## 2.44.x graph joins

`1d` waited on Phase 0 + 1b + 1c. `1b`/`1c` waited on `1_parallel` complete (so 2c serialized 1c). Agent 4/12 waited on 1d. Charts (phase 3) and reports (phase 4) started after 2.5. Audit waited on charts and reports. Sessions on ≥ 3.0.0 use file-shaped ready-sets (`1b`/`1c` after orch + files; `1d` after 0+1b; Agent 4/12 skip 1d; charts after valuation_model; audit after reports).

---

## 2.29.0–2.43.x — 25/15 haircut cliff

`decision.stress_bind` is required after `risk_bridge.json`. Material = any scenario with `fair_value_haircut_pct ≥ 0.25` (or ≥25 percent points) **and** `probability ≥ 0.15`. If material: `duration.action` must not be `initiate` or `add`. No DCF rewrite. No override hatch. `narrative_only` illegal on material scenarios. Haircuts may be worker-guessed percents grounded in the sensitivity grid. Sessions on ≥ 2.44.0 use the shocked-path book bind (`size_cap`, expected loss) instead.

---

## 2.28.0–2.44.x — Street FY+1 is the default Y1 start

Street FY+1 is the *default* Y1 start (`street_baseline`; `|delta|>5%` FAIL). `independent_y1` is legal when a named evidence gate resolves (`destock_this_print` | `definition_mismatch` | `native_kpi` | `street_unusable`). `ttc_midcycle` is **not** a Y1 license. `keep_independent_vs_street` remains illegal. Sessions stamped **3.0.0** used independent Y1 as default (see 3.0.0 band). Sessions on ≥ 3.0.1 restore Street as the default Y1 forecast and keep the 3.0 gates.

## 2.18.0–2.27.x — Street FY+1 is required base Y1

Street FY+1 revenue is the required Y1 start (`used_as:fy1_baseline`). `|delta_pct| > 0.05` FAILs unless `response=street_unusable`. `keep_independent_vs_street` is illegal. Destock analog belongs in **bear** while Street is usable. Destock-in-base is FAIL. `4d` does **not** win `4e`. Destock-in-base is legal only if Street is unusable **and** the analog matches this print.

## 2.12.0–2.17.x — destock-in-base default

Unresolved flatten-vs-destock cannot park destock in bear while duration stays in base. Destock-in-base / `decision_usefulness=low` / `duration.action=pass|too_hard` are the legal exits. Destock conflict of any status cannot park destock in bear while duration stays in base. Destock-inverse two-quarter raise is WARN. Copying Street into the revenue path is FAIL. `|delta|>20%` is a calibration WARN.

## 2.11.0–2.17.x — destock vs duration (pre-2.18)

Unresolved flatten-vs-destock cannot be duration-in-base unless destock is in base, DU=low, or duration=pass. Street `|delta|>20%` is a calibration WARN (**copying Street still FAIL**). On 2.18+ this invert: Street usable → destock analog in bear.

## 2.7.0–2.11.x — independent-then-calibrate

Street FY+1 is calibration after an independent company-evidence stack. Path-copy (`used_as:revenue_path` / `street_mean`) is FAIL. `keep_independent_vs_street` is a legal response.
