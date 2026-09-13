# Valuation router (harness ≥ 3.0.0)

Classify the **asset** then pick **one** primary playbook. Overlays stack. A distressed bank is still a bank. Do not start in `ref/` extracts.

Full recipes (optional JIT): `ref/Investment Valuation/knowledge-hub/00-router.md`. This file is the pinned map.

## Questions in order

1. **Object** — operating non-financial | bank/insurer/broker/AM | REIT/property | other.
2. **Cash flows** — now/soon (DCF legal, even if negative) | only if a contingency hits (option, not PW-DCF) | never (price only).
3. **Earnings / life cycle** — EBIT>0 history usable → mature operating. Losses: diagnose cause (one-time / cycle / commodity / chronic / young). Young/pre-profit → young-startup, not a cyclical normalize.
4. **Leverage** — stable D% → equity or firm DCF. Changing D% → firm DCF or APV. DCF equity ~ 0 + limited liability → distress-call **replaces** DCF equity.
5. **Job** — default **value** (DCF). Pricing is a labeled column, never averaged into FV.

## Primary playbook

| If | Playbook id | Never |
|---|---|---|
| Bank, insurer, broker, AM, payments | `financial_service` | FCFF, WACC, EV multiples |
| REIT / cash-flowing property | `real_estate` | NAV as intrinsic (NAV is **price**) |
| Young / pre-profit / no working model | `young_startup` | Grow a negative base; VC hurdle as ke |
| Cyclical/commodity EBIT on an operating firm | host playbook + `cyclical` overlay | Peak/trough base year; TTC × multiple as value |
| Distressed, operations not dead | `distressed` overlay | Bury p_fail in WACC |
| Listed non-financial, EBIT>0, history usable | `mature_operating` | Exit multiple as TV |

## Overlays (stack)

`cyclical` | `distressed` | `intangibles_sbc` | `em` | `truncation` | `sotp_users` | `growth_assets` | `macro_neutral`

## After classify

Stamp `narrative_bind.iv_playbook` to the playbook id (harness ≥ 3.1.0). Overlays go in `narrative_bind.overlays`. Sector modules are KPI/stress only — they do not choose this table.

Lock the story (`registry/narrative_bind.json`) then compute. Checks: `harness/modules/valuation_checks.md`. Optional `valuation_model.pricing` is a labeled **price** column (NAV, ARR, TTC×EBIT, exit multiple). It never writes `fair_value.base`.
