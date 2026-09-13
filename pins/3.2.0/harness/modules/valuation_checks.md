# Valuation checks (harness ≥ 3.0.0)

Run before publishing a number. Machine: `packages.kd_research.damodaran_gates`.

- **Playbook ( ≥ 3.1.0):** `narrative_bind.iv_playbook` is one router id. Sector modules do not choose it.
- **TV method ( ≥ 3.1.0):** `terminal_consistency` is required. Legal: Gordon / stable growth / perpetuity / liquidation / excess_return. Exit multiple, ARR, NAV, TTC×EBIT are **price**.
- **Narrative substance ( ≥ 3.2.0):** `narrative_bind` needs `story.paragraph` (≥20 chars), a non-empty `map` whose keys name real `valuation_model` inputs, and non-empty `3p{possible,plausible,probable}` buckets. `possible` strands set `revenue_in_dcf = 0`.
- **Truncation ( ≥ 3.2.0):** a `truncation` block with `p>0` must set `fair_value.base = (1−p)×GC + p×failure`; there is no `material` flag to bypass it.
- **Price column ( ≥ 3.2.0):** `pricing.used_as` / `role` is a closed price-only role set (`cross_check | relative_reference | sanity_check | reference_only`); anything else FAILs.
- **Root of trust ( ≥ 3.2.0):** a v3-stamped session with a `valuation_model.json` and no parseable `harness_version` FAILs, not SKIPs.
- **Growth triad:** `g = RR × ROC` (or payout identity). Never exogenous long-term g.
- **g_n ≤ session rf** in that currency. Gordon spread `r − g > 0`.
- **Never** close intrinsic TV with a comps exit multiple (that is **price**).
- **Never** average DCF and a multiple. Label value vs price. Optional `pricing` column is not `fair_value.base`.
- **Never** FCFF/WACC/EV on `financial_service` (banks, insurers, brokers, AM, payments).
- **REIT ( ≥ 3.1.0):** after-tax DCF; keep WACC. NAV/AFFO is the price column.
- **Never** grow EBIT≤0. Never ROC from a loss.
- **Never** bury failure in WACC. If truncation binds, `fair_value.base = (1−p)×GC + p×failure`.
- **3P possible** strands: `revenue_in_dcf = 0`.
- Street FY+1 is the default Y1 forecast. 5% band when you claimed `street_baseline`. `independent_y1` needs a named gate.
