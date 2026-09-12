# Valuation checks (harness ≥ 3.0.0)

Run before publishing a number. Machine: `packages.kd_research.damodaran_gates`.

- **Growth triad:** `g = RR × ROC` (or payout identity). Never exogenous long-term g.
- **g_n ≤ session rf** in that currency. Gordon spread `r − g > 0`.
- **Never** close intrinsic TV with a comps exit multiple (that is **price**).
- **Never** average DCF and a multiple. Label value vs price.
- **Never** FCFF/WACC/EV on banks/insurers.
- **Never** grow EBIT≤0. Never ROC from a loss.
- **Never** bury failure in WACC. If truncation binds, `fair_value.base = (1−p)×GC + p×failure`.
- **3P possible** strands: `revenue_in_dcf = 0`.
- Street is a prior. 5% band only if you claimed `street_baseline`.
