# Damodaran integration review — harness v3.1.0

**Work type:** W1 (research runtime)
**Date:** 2026-09-13
**Author:** eng session `2026-09-13-damodaran-integration-review`
**Question:** How well does the latest harness (`harness/VERSION` = 3.1.0) integrate the
principles and core values of the reference material in `ref/Investment Valuation/`
(Damodaran: *Investment Valuation* 4e, *Narrative and Numbers*, *The Dark Side of Valuation*)?

**Method:** five-part read-only audit — doctrine cartography of the three `ref/` knowledge
hubs; harness law/prompt audit (`harness/RESEARCH_AGENTS.md`, `agent_prompts.md`, runbook,
map); machine-enforcement audit (`packages/kd_research/*` gates + JSON schemas); router /
sector-module / design audit; and an adversarial claim-vs-delivery red-team. Findings carry
`file:line` evidence and were spot-checked by the maintainer.

---

## 1. Verdict

**Doctrine-integration score ≈ 5.2 / 10.**

The harness integrates the **valuation-arithmetic half** of Damodaran well — value vs price,
engine-from-the-asset for four playbooks, `g = RR × ROC`, WACC/ROIC identities, Street-Y1
discipline, provenance/audit. The **narrative-analytic half** (*Narrative and Numbers*) and
the **dark-side discipline half** (*The Dark Side of Valuation*) are largely **declared, not
enforced**: schema fields exist that no code reads and gates are opt-in behind
agent-controlled flags.

| Doctrine cluster | Weight | Score | Status |
|---|---|---|---|
| Value ≠ price (label, never average, price never FV) | 15% | 8/10 | Structural; detection is string/regex-based |
| Engine-from-asset / model-to-asset fit | 15% | 6/10 | Real for 4 playbooks; option/private/other-assets/control/pricing-primary absent |
| Story↔numbers bind (Narrative) | 15% | 2/10 | Cosmetic: status string + unread fields |
| Consistency identities | 12% | 4/10 | Only `g=RR×ROC`, WACC arithmetic, ROIC; ~9 triads absent |
| Double-count / risk-one-slot | 10% | 4/10 | Only p_fail-vs-WACC; whole-firm risk stacking unledgered |
| Terminal-value discipline | 8% | 6/10 | TV-method gate strong; no reset/fade; triad skippable |
| Life-cycle & specials | 10% | 5/10 | Financials/REIT strong; losses-by-cause, options, private absent |
| Bias / uncertainty / market-neutral / provenance | 15% | 6/10 | Provenance/audit strong; bias & market-neutral cosmetic |
| **Weighted total** | | **≈ 5.2/10** | |

---

## 2. Genuinely integrated (Tier 1 — real teeth)

- **Value vs price is architectural.** `pricing` is a labeled column that may not write
  `fair_value.base` (`harness/schemas/valuation_model.schema.json:76-80`); price-needle model
  names and `pricing.used_as` are rejected (`packages/kd_research/damodaran_gates.py:368-393`);
  exit/ARR/NAV are banned as TV (`:332-365`); DCF-vs-multiple averaging is scanned (`:420-441`).
- **Engine routing is real for four playbooks.** Required `iv_playbook` from a closed set
  (`damodaran_gates.py:160-190`); sector→playbook forced for banking/insurance→`financial_service`
  and REIT→`real_estate` (`:31-35`).
- **Financial-service ban has teeth.** `wacc_buildup.applies=true` and FCFF/EV model names are
  rejected on banks/insurers (`damodaran_gates.py:199-226`).
- **Growth is earned.** `g_n = RR×ROC ±0.005`, `g_n ≤ rf` (`damodaran_gates.py:258-329`);
  `wacc_buildup.py:241-358`; `roic_identity.py:523-570`.
- **Failure is a probability.** `(1−p)·GC + p·failure` base check (`damodaran_gates.py:444-474`);
  p_fail-vs-WACC double-count (`:396-417`).
- **Uncertainty / provenance / Street.** bear/base/bull required; audit-verdict gate
  (`phase_status.py:539-554`); Street-FY+1 default with 5% band (`street_y1.py:51`,
  `street_bind.py:395-542`).

## 3. Evadable in practice (Tier 2 — nominal compliance)

| # | Principle | Loophole |
|---|---|---|
| 1 | One primary playbook | sector→playbook forced only for bank/insurance/REIT |
| 2 | Truncation two-step | fires only if `truncation.material is True` (`damodaran_gates.py:445-447`); `material` is agent-set |
| 3 | 3P possible ⇒ `revenue_in_dcf=0` | returns `[]` unless `3p.possible` is a list (`:485-486`) |
| 4 | Lock-then-compute | only `status=="locked"` checked; no order/content check (`:148-157`) |
| 5 | Financials never FCFF/WACC/EV | `FINANCIALS={banking,insurance}`; banned-name list is 4 substrings (`:20,217`) |
| 6 | No averaging value/price | keyword scan only; silent numeric blend passes |
| 7 | Market-neutral / no iterate-to-price | no implied-ERP gate; `reverse_engineering` optional |

## 4. Prose-only / cosmetic (Tier 3)

- **Narrative bind is a status string.** `narrative_bind.schema.json:8` requires only
  `ticker`+`status`; `story`, `map`, `3p`, `who_leads`, `fairy_tale_flag` are unconstrained
  and never read (`:15-31`).
- **Life-cycle loss routing unenforced.** "Never grow EBIT≤0" is prose (`valuation_checks.md:13`);
  `roic_identity` rejects only `roc_n == 0` (`damodaran_gates.py:290-291`).
- **Bias pre-input absent.** No field/prompt for the `01-philosophy.md:24-38` rule.
- **Risk not held to one slot.** Beyond p_fail/WACC, no cross-risk ledger; Phase 2.5 derives
  `expected_loss_pct`/`size_cap` from probability-weighted FVs (`decision.py:213-333`), a
  latent "double haircut" drift vs `ds/01-jedi.md:107-113`.
- **Market-contest map, WACC/beta fade, cycle normalisation of margin/capex, news
  break/change/shift, founder/manager tests, match-output-to-user** — prose or absent.

## 5. Absent doctrine (Tier 4)

- **Contingent-claim / option family** — named in `valuation_router.md:10,13`, no playbook,
  overlay id, schema field, or gate.
- **Private/undiversified-buyer** (total beta, illiquidity discount, VC step-down).
- **Never-cash-flow `other_assets`** (art, bitcoin, owner-occupied house, franchise).
- **Acquisition / control** (two-DCF control, synergy).

## 6. Internal defects found

1. **Version stamp is the root of trust.** `_v3()` gates the whole layer; missing/unparseable
   `harness_version` → `SKIPPED` (`damodaran_gates.py:110-117`, `check_core.py:47-52`).
2. **Stale law trigger.** `RESEARCH_AGENTS.md:27` says `law_history.md` loads when `< 2.28`;
   `:234`, `:335`, `HARNESS_MAP.md:62` say `< 3.0.1`.
3. **Schema vs law mismatch.** `risk_bridge.schema.json:71` enum `["sector","macro"]` rejects
   the `region` scenario the law requires (`agent_prompts.md:408`).
4. **Sector modules breach their own "advisory only" rule.** `sector_utility.md:1-7` lacks the
   banner and declares "The Core Model"; `sector_growth.md:1040-1048` closes a "DCF Conclusion"
   with an ARR-based terminal value; `sector_insurance.md:415,1192` says brokers use "Standard DCF".
5. **Prompt layer weakest link.** No subagent template asks for 3P, story→input map,
   consistency triads, double-count catalog, real-options screens, or control overlays.

## 7. Ranked gap register

| Rank | Gap | Severity |
|---|---|---|
| 1 | Narrative bind is a status string, not a story↔input map | Critical |
| 2 | Risk not held to one slot; probability-weighted stress stacked on DCF | Critical |
| 3 | Version stamp bypasses the constitution | High |
| 4 | Truncation voluntary (`material:true`) | High |
| 5 | Option / contingent-claim family absent | High |
| 6 | Consistency-identity suite mostly absent | High |
| 7 | Life-cycle loss routing unenforced | High |
| 8 | Bias / fairy-tale work cosmetic | High |
| 9 | 3P opt-in; lock-then-compute unverified | High |
| 10 | Financials ban misses brokers/AM/payments; sector modules pick engines | Medium-High |

---

## 8. Fix plan for this session (harness 3.2.0)

**In scope (this change set):**

- **N1 — narrative substance gate** (≥ 3.2.0): `narrative_bind` must carry a non-empty
  `story.paragraph`, a non-empty `map` (story→input bind), and a `3p` object with
  `possible`/`plausible`/`probable` lists. Closes ranked #1 and #9.
- **N2 — strict 3P** (≥ 3.2.0): a present `3p` whose `possible` is not a list is a FAIL
  (was silently ignored).
- **N3 — truncation materiality gate** (≥ 3.2.0): a present `truncation` object must declare
  `material` as a bool; `p > 0` with `material: false` needs a `why_not_material` rationale.
  Closes ranked #4. **Superseded by §10.3** (derive the weighted base from `p`; no `material`
  bypass).
- **N4 — price-column `used_as` normalisation** (≥ 3.2.0): catch `Fair Value`, `fv`, `base`,
  `decision_value` variants, not just four exact strings.
- **D1 — `RESEARCH_AGENTS.md:27`** stale `2.28` trigger → `3.0.1`.
- **D2 — `risk_bridge.schema.json`** add `region` to the scenario `type` enum.
- **D3 — sector module banners/examples** so modules stop picking engines
  (`sector_utility.md`, `sector_growth.md`, `sector_insurance.md`).
- Prompt + `valuation_checks.md` updated so new runs comply.
- Tests, `harness/VERSION` → 3.2.0, release pin.

**Deferred (recorded, not in this bump):** version-stamp root-of-trust (#3), whole-firm risk
ledger (#2), option/private/other-assets engine families (#5), the broader consistency-identity
suite (#6), life-cycle EBIT≤0 gate (#7), bias artifact (#8), financials sector-enum coverage
and full sector-module rewrite (#10). Each needs its own W1 session.

## 9. Sources

- Doctrine: `ref/Investment Valuation/{AGENTS.md,knowledge-hub,knowledge-hub-narrative,knowledge-hub-dark-side}`
- Harness law: `harness/RESEARCH_AGENTS.md`, `harness/HARNESS_MAP.md`, `harness/agent_prompts.md`
- Gates: `packages/kd_research/{damodaran_gates,check_core,wacc_buildup,roic_identity,street_bind,phase_status}.py`
- Schemas: `harness/schemas/{narrative_bind,valuation_model,risk_bridge}.schema.json`
- Modules: `harness/modules/{valuation_router,valuation_checks,sector_utility,sector_growth,sector_insurance}.md`

---

## 10. Post-review reshape (still 3.2.0, uncommitted)

A strategic design review (`/strategic-design-review`) judged the first 3.2.0 cut `mixed` /
`reshape` and named four candidates. All four were then implemented before commit:

1. **Bind the narrative map to real inputs.** `_check_narrative_substance` now uses the
   `valuation_model`, requires each `map` key to name a real input present in the model
   (`assumptions` / `wacc_buildup` / `terminal_consistency` / `roic_identity` /
   `explicit_forecast` / `street_bind`) via `_model_input_names`, and requires each `3p`
   bucket non-empty. Schema descriptions updated.
2. **Root of trust.** `check_damodaran_v3` now FAILs (`damodaran.version_root`) when a
   `harness_spec: v3` session has a `valuation_model.json` but no parseable
   `harness_version`; non-v3/legacy sessions keep SKIPPED so immutable history stays green.
3. **Derive truncation materiality.** The `material` flag no longer bypasses the overlay;
   any `truncation` block with `p>0` must write `fair_value.base = (1−p)×GC + p×failure`.
   The inline `material is True` test in `_check_truncation_writes_base` was replaced with the
   `p>0` derivation (there was no separate `_check_truncation_materiality` in HEAD).
4. **Closed price-role contract.** `pricing.used_as`/`role` is now a closed set
   (`cross_check | relative_reference | sanity_check | reference_only`), not a substring
   denylist; schema documents the roles.

Verification: 30 gate tests (incl. new bind / root-of-trust / derived-truncation / role
cases), `eng_verify` PASS (1138 tests), `pins/3.2.0/` re-published to match.
