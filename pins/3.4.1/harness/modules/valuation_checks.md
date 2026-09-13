# Valuation checks (harness ≥ 3.0.0)

Run before publishing a number. Machine: `packages.kd_research.damodaran_gates`.

- **Playbook ( ≥ 3.1.0):** one router id. Sector modules do not choose it. ≥ 3.4.0: the id lives only on `classification.json`. `< 3.4.0`: `narrative_bind.iv_playbook`.
- **TV method ( ≥ 3.1.0):** `terminal_consistency` is required. Legal: Gordon / stable growth / perpetuity / liquidation / excess_return. Exit multiple, ARR, NAV, TTC×EBIT are **price**.
- **Narrative substance ( ≥ 3.2.0):** story + map + 3P buckets. `possible` strands set `revenue_in_dcf = 0`. ≥ 3.4.0: map keys are story carriers; 3P buckets live on `narrative_3p.json`; lock is `verdict=PASS`; Agent 5 writes `story_input_bind` and `buyer_dials`.
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
- **Life cycle ( ≥ 3.3.0):** `narrative_bind.life_cycle_stage` is one of `idea|young_growth|scaling_growth|mature|decline`; `who_leads` is `story|numbers`; `stage_fit` states why the story matches the stage (≥40 chars). A wrong-stage story is a fail, not a variant.
- **Buyer ( ≥ 3.3.0):** `narrative_bind.buyer.class` + rationale. A private/undiversified buyer needs `total_beta=true` and numeric `illiquidity_discount > 0`; a diversified public buyer must state numeric `illiquidity_discount = 0`; `vc_pe` needs `ke_stepdown` (≥20 chars).
- **Market contest ( ≥ 3.3.0):** `narrative_bind.market_contest` has non-empty `accept[]` and `contest[]` (contest names company cash flows/margins). Presume the market is right until model and inputs survive a hostile check.
- **Options ( ≥ 3.3.0):** `contingent_claim` / `real_options` need `option_screens` (`exclusivity`, `materiality`, `no_double_count` all true). A `distressed_call` **replaces** DCF equity — it is never added on top.
- **Truncation answered ( ≥ 3.3.0):** every model carries a `truncation` block. `p=0` needs `why_not_material` (≥40 chars); `p>0` writes `fair_value.base = (1−p)×GC + p×failure`.
- **Market-neutral inputs ( ≥ 3.3.0):** `wacc_buildup.erp_method` (implied default; `not_applicable` is illegal while `applies=true`; historical needs `erp_reject_implied_reason`), `beta_method` (bottom_up default; `not_applicable` illegal while `applies=true`; otherwise `beta_reason`), and `discount_currency` = `cash_flow_currency` (or an `fx_policy`).
- **Per-share bridge ( ≥ 3.3.0):** `per_share_bridge` (`shares_used`, `net_debt_subtracted`, `cash_added`, `rationale`) or `applies:false` + a reason. Financials and option primaries are exempt.
