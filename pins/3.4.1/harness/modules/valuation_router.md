# Valuation router (harness ≥ 3.0.0; buyer/option branches ≥ 3.3.0)

Classify the **asset** and the **buyer**, then pick **one** primary playbook. Overlays stack. A distressed bank is still a bank. Do not start in `ref/` extracts. **Open the ref recipe named below for the chosen playbook and each overlay** — those files are the full method; this file is only the pinned map.

Full recipes: `ref/Investment Valuation/knowledge-hub/00-router.md`, plus `knowledge-hub-dark-side/` (traps and repaired recipes) and `knowledge-hub-narrative/` (story process).

## Questions in order

1. **Object** — operating non-financial | bank/insurer/broker/AM | REIT/property | other (franchise/practice, commodity-as-asset, currency/collectible) | separable marketable assets.
2. **Cash flows** — now/soon (DCF legal, even if negative) | only if a contingency hits (option, not PW-DCF) | never (price only; DCF illegal).
3. **Buyer** — public diversified (market beta, no illiquidity discount) | private/undiversified (total beta + illiquidity treatment) | IPO/public buyer (market beta, no illiquidity) | VC/PE (stepped ke).
4. **Earnings / life cycle** — EBIT>0 history usable → mature operating. Losses: diagnose cause (one-time / cycle / commodity / chronic / young). Young/pre-profit → young-startup, not a cyclical normalize.
5. **Leverage** — stable D% → equity or firm DCF. Changing D% → firm DCF or APV. DCF equity ~ 0 + limited liability → distress-call **replaces** DCF equity.
6. **Job** — default **value** (DCF). Pricing is a labeled column, never averaged into FV.

## Primary playbook

| If | Playbook id | Never |
|---|---|---|
| Bank, insurer, broker, AM, payments | `financial_service` | FCFF, WACC, EV multiples |
| REIT / cash-flowing property | `real_estate` | NAV as intrinsic (NAV is **price**) |
| Young / pre-profit / no working model | `young_startup` | Grow a negative base; VC hurdle as ke |
| Cyclical/commodity EBIT on an operating firm | host playbook + `cyclical` overlay | Peak/trough base year; TTC × multiple as value |
| Distressed, operations not dead | `distressed` overlay | Bury p_fail in WACC |
| Listed non-financial, EBIT>0, history usable | `mature_operating` | Exit multiple as TV |
| Contingent / exclusive payoff (patent, undeveloped reserve, undeveloped land, staged R&D) | `contingent_claim` (≥ 3.3.0) | Probability-weighted DCF instead of an option |
| Separable marketable assets used as a floor | `asset_based` (≥ 3.3.0) | Primary tool for a growth firm |

## Overlays (stack)

`cyclical` | `distressed` | `intangibles_sbc` | `em` | `truncation` | `sotp_users` | `growth_assets` | `macro_neutral` | `real_options` | `distressed_call` | `asset_based_floor` | `private_buyer` | `value_enhancement`

## Ref recipe (open every named file — full method, not this map)

One row per primary id and per overlay. Paths are relative to `ref/Investment Valuation/`.

| Id | Open |
|---|---|
| `mature_operating` | `knowledge-hub/playbooks/mature-operating.md`, then the `knowledge-hub/inputs/` files in estimation order (rf-erp-country → beta-ke → kd-wacc-apv → earnings → cash-flows → growth → terminal-value → narrative-3p → per-share-bridge) |
| `financial_service` | `knowledge-hub/playbooks/financial-service.md`, `knowledge-hub/special/banks.md` |
| `real_estate` | `knowledge-hub/playbooks/real-estate.md`, `knowledge-hub/special/real-estate.md` |
| `young_startup` | `knowledge-hub/playbooks/young-startup.md`, `knowledge-hub/special/startups.md`, `knowledge-hub/inputs/narrative-3p.md` |
| `contingent_claim` | `knowledge-hub/special/real-options.md`, `knowledge-hub/formulas/options.md` |
| `asset_based` | `knowledge-hub/playbooks/other-assets.md`, `knowledge-hub/special/other-assets.md` |
| `cyclical` | `knowledge-hub/playbooks/cyclical-commodity.md`, `knowledge-hub-dark-side/playbooks/cyclical-commodity.md` |
| `distressed` | `knowledge-hub/playbooks/distressed.md`, `knowledge-hub-dark-side/playbooks/declining.md` |
| `intangibles_sbc` | `knowledge-hub-dark-side/playbooks/intangibles.md` |
| `em` | `knowledge-hub-dark-side/playbooks/emerging-markets.md` |
| `truncation` | `knowledge-hub-dark-side/overlays/truncation.md` |
| `sotp_users` | `knowledge-hub-dark-side/playbooks/sotp-users.md` |
| `growth_assets` | `knowledge-hub-dark-side/playbooks/growth.md` |
| `macro_neutral` | `knowledge-hub-dark-side/overlays/macro-neutral.md` |
| `real_options` | `knowledge-hub/special/real-options.md`, `knowledge-hub-dark-side/overlays/real-options-screens.md` |
| `distressed_call` | `knowledge-hub/special/distressed-call.md`, `knowledge-hub-dark-side/overlays/distress-call.md` |
| `asset_based_floor` | `knowledge-hub/playbooks/other-assets.md`, `knowledge-hub/special/other-assets.md` |
| `private_buyer` | `knowledge-hub/playbooks/private.md`, `knowledge-hub/special/private-firms.md` |
| `value_enhancement` | `knowledge-hub/special/value-enhancement.md` |
| `any` | `knowledge-hub/checks/consistency-triads.md`, `knowledge-hub/checks/double-counts.md`, `knowledge-hub/checks/dcf-vs-pricing.md`; story process: `knowledge-hub-narrative/` |

The `mature_operating` row lists the input files in estimation order; other rows use the matching `knowledge-hub/inputs/` and `knowledge-hub/checks/` files the playbook names.

Sector/region modules are KPI/stress only — they do not choose this table.

## After classify

On harness ≥ 3.4.0 the **orchestrator** stamps `registry/classification.json` (`iv_playbook`, `buyer`, overlays, life-cycle, market-contest, job) **before Phase 0**. That card is the only identity. The 1e story specialist writes story/map/hooks; the 3P critic writes `narrative_3p.json` only. Lock is `verdict=PASS`. Agent 5 must not reclassify.

On `< 3.4.0` Agent 5 stamped `narrative_bind.iv_playbook` itself (harness ≥ 3.1.0) and `narrative_bind.buyer` (harness ≥ 3.3.0).

Checks: `harness/modules/valuation_checks.md`. Optional `valuation_model.pricing` is a labeled **price** column (NAV, ARR, TTC×EBIT, exit multiple). It never writes `fair_value.base`.
