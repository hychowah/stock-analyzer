# Mode A law history (JIT)

**Not current law.** Live Agent 5 / orchestrator must **not** load this file. Agent 13 loads it **only** when `S/meta/run_manifest.json` `harness_version` is `< 2.28.0`.

Current Street/Y1/destock law: `harness/RESEARCH_AGENTS.md` §10c and §13.

---

## 2.18.0–2.27.x — Street FY+1 is required base Y1

Street FY+1 revenue is the required Y1 start (`used_as:fy1_baseline`). `|delta_pct| > 0.05` FAILs unless `response=street_unusable`. `keep_independent_vs_street` is illegal. Destock analog belongs in **bear** while Street is usable. Destock-in-base is FAIL. `4d` does **not** win `4e`. Destock-in-base is legal only if Street is unusable **and** the analog matches this print.

## 2.12.0–2.17.x — destock-in-base default

Unresolved flatten-vs-destock cannot park destock in bear while duration stays in base. Destock-in-base / `decision_usefulness=low` / `duration.action=pass|too_hard` are the legal exits. Copying Street into the revenue path is FAIL. `|delta|>20%` is a calibration WARN.

## 2.7.0–2.11.x — independent-then-calibrate

Street FY+1 is calibration after an independent company-evidence stack. Path-copy (`used_as:revenue_path` / `street_mean`) is FAIL. `keep_independent_vs_street` is a legal response.
