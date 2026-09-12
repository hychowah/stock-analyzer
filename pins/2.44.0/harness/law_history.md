# Mode A law history (JIT)

**Not current law.** Live Agent 5 / orchestrator must **not** load this file. Agent 13 loads it **only** when `S/meta/run_manifest.json` `harness_version` is `< 2.28.0` (Street/Y1/destock). Stress-bind policy is machine-banded in `packages.kd_research.decision` — do not paste the 25/15 cliff into a ≥ 2.44.0 session.

Current Street/Y1/destock law: `harness/RESEARCH_AGENTS.md` §10c. Current stress book: §10f / §8 5b. Current machine gates: `harness/RESEARCH_AGENTS.md` §13 (unbanded).

---

## 2.29.0–2.43.x — 25/15 haircut cliff

`decision.stress_bind` is required after `risk_bridge.json`. Material = any scenario with `fair_value_haircut_pct ≥ 0.25` (or ≥25 percent points) **and** `probability ≥ 0.15`. If material: `duration.action` must not be `initiate` or `add`. No DCF rewrite. No override hatch. `narrative_only` illegal on material scenarios. Haircuts may be worker-guessed percents grounded in the sensitivity grid. Sessions on ≥ 2.44.0 use the shocked-path book bind (`size_cap`, expected loss) instead.

---

## 2.18.0–2.27.x — Street FY+1 is required base Y1

Street FY+1 revenue is the required Y1 start (`used_as:fy1_baseline`). `|delta_pct| > 0.05` FAILs unless `response=street_unusable`. `keep_independent_vs_street` is illegal. Destock analog belongs in **bear** while Street is usable. Destock-in-base is FAIL. `4d` does **not** win `4e`. Destock-in-base is legal only if Street is unusable **and** the analog matches this print.

## 2.12.0–2.17.x — destock-in-base default

Unresolved flatten-vs-destock cannot park destock in bear while duration stays in base. Destock-in-base / `decision_usefulness=low` / `duration.action=pass|too_hard` are the legal exits. Destock conflict of any status cannot park destock in bear while duration stays in base. Destock-inverse two-quarter raise is WARN. Copying Street into the revenue path is FAIL. `|delta|>20%` is a calibration WARN.

## 2.11.0–2.17.x — destock vs duration (pre-2.18)

Unresolved flatten-vs-destock cannot be duration-in-base unless destock is in base, DU=low, or duration=pass. Street `|delta|>20%` is a calibration WARN (**copying Street still FAIL**). On 2.18+ this invert: Street usable → destock analog in bear.

## 2.7.0–2.11.x — independent-then-calibrate

Street FY+1 is calibration after an independent company-evidence stack. Path-copy (`used_as:revenue_path` / `street_mean`) is FAIL. `keep_independent_vs_street` is a legal response.
