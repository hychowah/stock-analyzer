# Conservative-value audit — WACC-buildup identity (draft 2.40)

Persona: residual-claim / Graham–Buffett. Question: if writing a check today for the residual equity, which cost-of-capital rule can I trust **not to overstate** owner earnings and fair value?

This is a Mode B review of current law and a draft gate. CMCSA `archive/research/CMCSA/2026-09-07` is a **read-only incident**. Do not rewrite it.

---

## Lead answer

**Ship the identity, but do not ship the draft as written.** A WACC that “matches the buildup” is not conservative if pretax Kd is a coupon below session Rf, or if weights use crushed market equity to overweight that gift debt. That is a silent bull case: it inflates PV, inflates Gordon TV, and can license `franchise_mos` when mid-cycle ROIC is only modestly above a junk hurdle.

The Sep 7 failure was not a missing arithmetic check. `packages/kd_research/roic_identity.py` already matches `roic_identity.wacc` to `assumptions.wacc` within 5 bp, and `packages/kd_research/valuation_hygiene.py` already requires `wacc_vs_buildup` to exist. Sep 7 **passed both** and printed WACC 6.145% with `dial: matches_buildup`, `applies_in: none` (`archive/research/CMCSA/2026-09-07/data/valuation_model.json`). The machine certified the formula. It did not certify opportunity cost.

**v1 I would trust** is a checker in the `roic_identity.py` spirit (impossible ingredients FAIL; no shared rate-paste calculator; no hardcoded 9%):

1. **Coupon is illegal as the WACC Kd input.** `kd_source` ∈ {`current_yield`, `rf_plus_spread`} only, and the chosen source must bind to in-session evidence (quoted YTM, or Rf + numeric spread). Relabeling a coupon table as `current_yield` is FAIL.
2. **Pretax Kd ≥ session Rf** except a **Japan-style** hatch (`negative_rate_market` with local Rf evidence). Drop `current_yield_verified` as a license for Kd < Rf.
3. **Going-concern DCF may not use only `current_market` weights when the distressed-equity tripwire fires.** Keep the implied-WACC-gap clause; do not rely on “equity at/below book” (it would have **missed** this incident). Target/blended weights may not be a restatement of the trough `wd`.
4. **Keep `wacc_vs_buildup: matches_buildup`.** Named Ke sleeves (ops / size / governance) with use/reject live **inside** the buildup. A 25 bp sleeve does not pardon illegal Kd or trough weights.
5. **`franchise_mos` is illegal until this identity PASSES.** Hurdle stays in-model WACC — but only after WACC is an opportunity cost, not a coupon mix.

With those five, Sep 7’s stored stack would FAIL before the user ever saw $59.83 vs $26.49 as franchise MoS. Without tightening the Kd < Rf hatch and the target-weight game, Agent 5 can still print a utility-like WACC and call it matched.

I distrust destock-haircut theater and growth-perpetuity theater equally. I also distrust **destock-of-the-discount-rate**: coupon-as-Kd, trough `wd`, dual-class = 0 because the module forbids a paste, and `priced_for_perfection=false` used as a buy license. Capex is cash. SBC is a real cost. Terminal g must not smuggle the bull case. A too-low WACC is the same class of error.

---

## Incident (read-only; stored numbers only)

Session `archive/research/CMCSA/2026-09-07` (harness 2.39-era). Contrast only: `archive/research/CMCSA/2026-07-25/data/valuation_model.json` added a +345 bp company premium to 9.0% after raw CAPM ~5.55%. Sep 7 obeyed “do not pad; match the buildup.”

| Piece | Stored | Path |
|---|---|---|
| Price | $26.49 | `data/compute/valuation_result.json` |
| WACC / Ke | 6.145% / 9.092% | `data/valuation_model.json` `assumptions.wacc` / `ke` |
| Rf / beta / ERP | 4.784% `^TNX`; raw 0.719 → Blume 0.812; ERP 5.0% | `data/market_inputs_snapshot.json` + script |
| Kd pretax | **4.0%** (comment: coupon buckets 3.3–4.2%) | `data/compute/valuation.py` `kd_pretax = 0.040` |
| Tax / weights | 23%; we 0.510 / wd 0.490 at market cap $94.0B vs carrying debt $90.4B | `valuation_result.json` intermediates; LQ `total_debt_carrying_value` 90400 |
| Debt fair value (unused in WACC) | **79700** vs carrying 90400 | `registry/latest_quarter.json` |
| Book equity | 89763 | same LQ file; market cap is **above** book |
| Tape-implied WACC on base path | 9.13% | `valuation_result.json` `reverse_engineering.implied.wacc_on_base_path` |
| Base FV / g=0 | $59.83 / $40.20 | `valuation_model.json` |
| Mid-cycle ROIC | 10.01% vs WACC 6.14% → `above_wacc` → `cheap_claim.class=franchise_mos` | `roic_identity` |
| `wacc_vs_buildup` | `matches_buildup`, `applies_in=none` | `conservatism_dials` |
| Dual-class Ke sleeve | **0**; “governance via bear weight/range” | `assumptions.dual_class_governance_premium` |
| Ops sleeve | +25 bp on **Ke**, not a WACC pad | script `structural_ops_premium = 0.0025` |
| TV share / g | ~70% of EV; g=2%; `wacc_minus_g` 4.14% | `terminal_consistency` |

Residual-claim read: owner earnings on capital at 10.01% vs **Ke 9.09%** is a thin equity residual. The same ROIC vs **WACC 6.14%** is a 387 bp “franchise.” The gap is cheap coupon debt at 49% weight, not a demonstrated incremental ROIC machine. LQ already printed debt **fair value below par** — the market’s own Kd is above the coupon. The script still mixed 4.0% with Rf 4.784%.

Gordon is the amplifier: TV ~70% of EV at WACC − g = 4.14%. A too-low WACC does not need a destock haircut or a g-plug to overstate the check you would write.

---

## 1. Residual analysis error

After this draft, Agent 5 can still print a WACC that is economically too low (the danger I care about) or too high (the false-FAIL / scare-pad risk).

### Still too low (overstates FV / owner earnings)

**Kd theater the draft does not close**

- **`rf_plus_spread` with 0 bp.** Legal source, Kd = Rf, still below a going-concern credit spread. Cable with fiber/FWA share-shift is not a Treasury. Draft fields include `kd_source` but no `spread_bp` identity and no floor. Sep 7 could become `kd_source=rf_plus_spread`, spread 0, Kd 4.784%, WACC still pulled toward Rf by `wd≈0.49`.
- **`current_yield_verified` as a Kd < Rf hatch.** A quoted YTM on a 3.3% long bond that rallied is duration, not the rate at which the firm can issue the stack today. Sep 7 could relabel the FDD coupon buckets as “YTM.” LQ `debt_fair_value` 79700 vs carrying 90400 is evidence the stack does **not** yield 4%. The hatch would let them ignore that.
- **Coupon evidence, `current_yield` label.** Draft says coupon is illegal as the input. It does not bind `kd_source=current_yield` to a price/yield quote (issue, price, YTM) in-session. Comment-as-yield in `valuation.py` line 186 would survive if the JSON enum is clean.

**Weight theater**

- **Target `wd` set to the trough `wd`.** Tripwire fires (`wd>0.35` and implied gap ~299 bp > 200 bp). Agent 5 writes `weight_policy=target` with target = 49/51 — the current crushed mix. Draft requires `target` or `blended` with rationale; it does not require the target to be independent of trough market equity.
- **`equity at/below book` would not have fired.** Market cap $94.0B vs LQ book 89763. P/B slightly above 1. If a later tweak weakens the 200 bp gap clause, CMCSA-shaped names slip through. Do not treat that OR as load-bearing.
- **Par debt, not market debt.** Script used carrying $90.4B as `d_mkt`. Fair value is lower. Using par **overweights** the cheap Kd. Draft has no debt-valuation field.
- **Leases / preferred / cash.** `roic_identity.leases=opex_and_out_of_ic` keeps operating leases out of IC; they are also out of `wd`. Preferred is absent. Gross debt (not net) at coupon Kd **lowers** WACC. Net-cash tech with `wd≈0` is fine; levered IG with omitted lease-debt is not. v1 can defer preferred/leases if Agent 13 is told to grade them; do not pretend the identity covers them.

**Beta / ERP / local Rf (already in prompt; still un-gated)**

- Agent 5 already requires scripted beta/Rf and ERP method + rejected competitor (`harness/agent_prompts.md` hard constraint “ERP / CoC”; `harness/exemplars/valuation_decision_quality.md` Pair 4). Sep 7 **did this** (historical 5.0%, rejected implied). The hole is not folklore ERP. It is mixing a decent Ke with junk Kd.
- **Raw 0.72 Blume’d toward 1 → 0.81** slightly *raised* Ke. Conservative for FV. The low-beta problem is forward operational risk not in 5y monthly vs `^GSPC` while broadband is losing share. Draft `beta_policy` is judgment, not a gate — correct for v1, but Agent 13 has **no WACC band** today (`harness/agent_prompts.md` Agent 13 has `4-roic` / `4-street`, nothing on Kd vs Rf).
- **`unlever_relever_target` at a low target D/E** after observing trough leverage can cut Ke. Judgment hatch in v1; easy game later.
- **Local Rf pasted as US 10Y** on a non-USD model is already forbidden (`agent_prompts.md` line 22; `RESEARCH_AGENTS.md` §5b / §9b). Draft does not add an Rf-currency identity. Residual miss for `intensity=medium/high`.

**Circular implied-gap**

- Implied WACC is price inverted on the **base path**. Draft correctly does **not** FAIL the tape for disagreeing (good: forcing WACC = implied makes MoS identically zero).
- Residual game: **haircut the path** (destock-in-base theater, crushed OM) until implied WACC falls inside 200 bp of the cheap model WACC. Then the weight tripwire never fires. Isolation from destock law is incomplete: `RESEARCH_AGENTS.md` §10c already FAILs destock-in-base without `destock_this_print`, but OM/capex haircuts still close the gap. **Primary FAILs must be Kd source and Kd vs Rf**, not the gap. Gap is a disclosure/WARN.

**ROIC franchise license (the residual-claim kill shot)**

- `RESEARCH_AGENTS.md` §10d: hurdle is **in-model WACC**; `franchise_mos` only when `above_wacc`. That is the right unlevered identity **if WACC is honest**. After a still-too-low WACC, 10.01% vs 6.14% licenses franchise MoS and a $59.83 check. Draft does not say `cheap_claim=franchise_mos` is illegal while `wacc_buildup` FAILs. It must.
- Even after a partial fix (Kd = Rf, same 49% `wd`), ROIC vs WACC can still look “above” while ROIC vs Ke is ~100 bp. Print `roic_minus_ke` for Agent 13. Do not machine-FAIL “ROIC must exceed Ke” (apples vs oranges). Do FAIL franchise paperwork on an illegal WACC.

**Gordon**

- Draft does not touch `terminal_consistency`. Existing TV-share tripwire (`Y8 growth ≥8%` and TV >60%) did **not** fire: Y8 g 1.8%. Low WACC + modest g still puts ~70% of EV in the terminal. Fixing Kd/weights is the WACC-side cure; do not add a g-cap in this gate.

### Still too high (undervalues; false conservatism)

- Scare-padding after CMCSA: Agent 5 re-learns July 25’s +345 bp WACC paste. That is the bug `wacc_vs_buildup` was built to catch (`RESEARCH_AGENTS.md` §10c.8; hygiene message literally says “high WACC” as a stacked conservative dial). Keep **matches_buildup**. Put idiosyncratic risk in **named Ke sleeves**, not a post-mix pad.
- Blume toward 1 on a true 0.3 utility beta raises Ke. Fine as judgment; do not mandate Blume in v1 (draft already says not all beta policies mandated).
- Forced dual-class Ke premium (contradicts “no hardcoded family discount”). May be 0 **after use/reject**, not because the module forbids a number.
- `weight_policy=target` with `wd=0` on a healthy levered IG (over-equity the WACC). Tripwire should not fire without distress.

---

## 2. Wrong prompt

What in current Agent 5 / Agent 13 / `RESEARCH_AGENTS.md` would cause Sep 7 again, or a new failure if draft text is pasted carelessly.

### Would re-cause CMCSA

1. **`wacc_vs_buildup` as a virtue when the buildup is junk.** §10c.8 and Agent 5 step 4e require the four dials; omit is FAIL. Hygiene FAILs silent **high** WACC stacking. Sep 7’s rationale is the obedience text: “No silent WACC pad above buildup.” The prompt never says matching a coupon-below-Rf mix is illegal. Agent 13 has no Kd check, so schema-valid hollow CoC PASSes.

2. **“Do not pad; match the buildup” without a legal-ingredient list.** July 25’s pad was a real error (unscripted 345 bp after mixing). The correction overshot: padding is forbidden, opportunity-cost Kd is unmentioned. `agent_prompts.md` step 2 asks for “discount rate build-up” and “CoC/governance dials **(may be 0)**” and “NEVER paste region-module ranges as mandated WACC/ERP/family discounts.” That is how dual-class = 0 and Kd = 4.0% both felt like law.

3. **Governance via bear weight, not Ke.** Sep 7: Roberts Class B is “material agency risk” but “`region_us` forbids pasting a family-control module discount into Ke.” `region_us.md` actually says dual-class is a **governance dial, not an automatic country premium** — a use/reject, not a zero mandate. `region_integration.md` rejects hardcoded family % tables. Agent 5 read “may be 0” + “never paste” as **must be 0**, then dumped the risk into bear mass 0.34. Bear mass does not change **base** FV. Primary MoS uses base (`agent_prompts.md` MoS constraint). Residual equity is still discounted at 6.14%.

4. **ROIC franchise on in-model WACC.** Agent 5 2b + §10d + Agent 13 `4-roic`: `franchise_mos` on `above_wacc` is the GOOD pattern. Sep 7 followed it. If 2.40 text says “keep matches_buildup” and “hurdle is in-model WACC” without “identity must PASS first,” Agent 13 will again PASS a 10% vs 6% franchise.

5. **PFP=false as cheapness.** Reverse-eng rationale: tape is cheap because matching $26.49 needs WACC ~300 bp above model. That is exactly “tape is cheap / franchise MoS.” Draft’s implied-gap rule (rationale **not only** that sentence) is load-bearing. Agent 13 item 9 grades PFP surface, not whether implied WACC is a **Kd/weights** problem.

6. **No Agent 13 WACC band.** `4-street` and `4-roic` are specific. CoC is only “justification contract + scripted intermediates” and “ERP method.” A coupon constant with a comment will not fail Band 3.

### New failures if draft text is careless

- **Contradiction with “no hardcoded WACC.”** Pasting 9%, “use July 25’s 9%,” or a module table into Agent 5/13 or `region_us.md` violates `RESEARCH_AGENTS.md` §5b / §9b and `region_integration.md` (“Never validate Rf magnitudes or enforce family-discount enums in machine checks”). State **hatches and identities**, not rates.
- **Contradiction with `wacc_vs_buildup`.** If the prompt says both “match the buildup, do not pad” and “add a company premium to WACC after mixing,” Agent 5 will either pad (July 25) or drop the sleeve (Sep 7). Resolve: sleeves on **Ke**, then WACC **equals** that full buildup.
- **Dual-class = 0 as a machine rule.** Do not write “governance premium must be 0.” Write: named Ke sleeve with **use or reject**; reject may be 0 with rationale; dumping the whole residual into bear mass while quoting base MoS is a finding.
- **`applies:false` abuse.** Banks/insurance/REITs/non-WACC natives need the hatch (`roic_identity` already does this). If Agent 5 can `applies:false` a levered FCFF cable because “WACC is hard,” the gate is theater. Bind `applies:false` to sector analog (banking / insurance / reit / other non-WACC) the way §10d does — not a free essay.
- **Shared calculator in the prompt.** “Call the library WACC at 8%” or a helper that returns Rf+ERP defaults. Law is: Agent 5 still judges Rf, beta, ERP, spread, target weights; the machine fails **impossible ingredients**. Same split as ROIC (`roic_identity.py` docstring: never writes g or FV).

---

## 3. Bad harness

How the gate itself becomes harmful.

### False FAIL (do not overfit Sep 7)

| Case | Risk | v1 treatment |
|---|---|---|
| Banks / insurance / REITs | Industrial WACC object required | `applies:false` + ≥40 char reason + native analog (`roe_vs_ke` / NAV-AFFO), copy `roic_identity` |
| Japan / negative-rate | Kd < local Rf is possible | Hatch `negative_rate_market` with **local** Rf evidence; do not use US `^TNX` as the comparison |
| Utilities | Kd near Rf; sector module even shows illustrative WACC 5.37% (`harness/modules/sector_utility.md`, advisory) | If Kd is **current YTM or Rf+spread**, Kd ≥ Rf should hold. Coupon-below-Rf still FAIL. Do **not** special-case utilities into `current_yield_verified` for Kd < Rf |
| Net-cash tech | `wd` tiny; `we≈1` | `we+wd≈1` with `wd=0` is PASS. Distressed tripwire must not fire (`wd>0.35` protects this — keep it as the leverage half, not as the only half) |
| Healthy IG, P/B > 1, modest implied gap | `wd>0.35` alone would force target weights on a normal 40% debt industrial | **AND** with gap > 200 bp (or a real distress hook). Do not FAIL on `wd>0.35` alone |

### Easy games (must close in v1 or name as Agent 13 major)

- `rf_plus_spread` + 0 bp.
- `kd_source=current_yield` with coupon table / FDD bucket comment, no quote.
- `current_yield_verified` hatch for Kd < Rf (drop it).
- `weight_policy=target` with target = trough `wd`.
- `distressed_equity_hook=none` while `wd>0.35` and gap > 200 bp (machine must ignore the self-grade and FAIL).
- Blume toward 1 on 0.3 beta: **not** a Sep 7-class undervalue; do not FAIL. Unlever-relever to a cosmetic low D/E: Agent 13 later.
- Haircut FCFF path until implied gap < 200 bp: cannot be the primary FAIL (see Q1).
- `applies:false` on a WACC-native FCFF.

### Shared calculator that pastes rates

Do not ship `packages/kd_research/wacc.py` that returns 8%, Damodaran tables, or “US large-cap default.” Pattern to copy is `roic_identity.py`: rehydrate identities, forbid illegal paperwork, never write the rate. Agent 5 still writes a **new** `S/data/compute/valuation.py` each session (`RESEARCH_AGENTS.md` runtime scripts). A shared **checker** is the product. A shared **numerator** is how 9% becomes folklore.

### Overfit to CMCSA

- Magic `wd>0.35` without the gap clause is Comcast-shaped. The economic rule is: **do not let crushed equity increase the weight of below-opportunity-cost debt.** Net-cash + huge implied gap is “tape cheap vs Ke,” which can be a real MoS — not this bug.
- Magic 200 bp is a tolerance, not a law of nature. Keep it as a **tripwire for weights and for rationale**, not as “WACC must equal implied.”
- Do not encode 6.14%, 9.13%, 4.0%, or July 25’s 9.0% anywhere in prompts, schemas, or modules.

---

## 4. Load-bearing changes (require / drop / add)

Ranked by: (A) would it have caught Sep 7, (B) false-FAIL risk on a healthy session.

### Require in v1 (ship 2.40)

| # | Change | Catch Sep 7? | False FAIL? |
|---|---|---|---|
| R1 | **`kd_source` ∈ {`current_yield`, `rf_plus_spread`} only; `coupon` illegal.** Bind `current_yield` to an in-session quoted YTM (issue/price/yield or debt fair-value vs par implying yield ≠ coupon). Bind `rf_plus_spread` to numeric `spread_bp` + rationale. | **Yes** (script comment is coupon buckets; LQ fair value 79700 vs 90400 unused). | Low if quotes can be a single on-the-run issue or a note YTM. |
| R2 | **`kd_pretax >= rf` except `negative_rate_market` + local Rf evidence.** Coupon-below-Rf is FAIL with no other hatch. | **Yes** (4.0% < 4.784%). | Japan needs the hatch. Utilities using **YTM** should sit ≥ Rf; if a tight utility YTM prints 1–20 bp below Rf, that is a rare miss I will take vs re-opening the coupon hatch. |
| R3 | **Arithmetic:** WACC = we×Ke + wd×Kd(1−t) within 5 bp; equals `assumptions.wacc` and `roic_identity.wacc`; `we+wd≈1`. | No (already true). Needed so the identity is not theater. | None (same as ROIC 5 bp). |
| R4 | **Distressed weights:** going-concern DCF cannot use **only** `current_market` when `wd > 0.35` **and** implied WACC gap > 200 bp. Then `target` or `blended`. | **Yes** (wd 0.49 and gap ~299 bp). Book-equity OR is unnecessary for this catch. | Net-cash / low-debt protected by `wd>0.35`. Healthy high-debt with small gap protected by 200 bp AND. |
| R5 | **Target/blended may not restate trough `wd`.** When R4 fires, target D/(D+E) must come from a non-trough basis (book mix, historical pre-crush mix, or rating-agency/structure the firm can refinance at) with rationale ≥40 chars. Optional mechanical: `|target_wd − current_wd| < 200 bp` is FAIL when the tripwire fired. | **Yes** if they try `target=0.49`. | Low; Agent 5 already writes structure rationale. |
| R6 | **Implied gap > 200 bp → `wacc_gap_rationale` ≥40 chars that is not only “tape is cheap / franchise MoS.” WARN if rationale ignores Kd/weights. Do not FAIL the tape.** | **Yes** (stored reverse-eng text is exactly tape-cheap). | None if it is rationale/WARN, not a rate mandate. |
| R7 | **`franchise_mos` / `above_wacc` license is illegal while `wacc_buildup` FAILs** (or `applies:false` on a WACC-native model). | **Yes** (the user-visible harm). | None; it is a sequencing rule like Street 5%. |
| R8 | **Keep `wacc_vs_buildup: matches_buildup`.** Idiosyncratic risk = named **Ke** sleeve (ops / size / governance) with use/reject. Sleeve is inside the buildup; WACC still matches. A sleeve does not waive R1–R5. | Partial (Sep 7 had +25 bp and still 6.14%). Prevents July 25 regression. | None if we do not mandate a non-zero sleeve. |
| R9 | **`applies:false` hatch** for banks/insurance/REITs/other non-WACC natives, ≥40 chars, same spirit as §10d. WACC-native FCFF cannot take it. | n/a (CMCSA is native). | Prevents bank/REIT false FAIL. |
| R10 | **Prompts, not numbers.** Agent 5 self-check + Agent 13 new `4-wacc` band: Kd source evidence, Kd vs Rf, weight policy vs tripwire, gap rationale substance. No pasted WACC/ERP/Kd. Legacy < 2.40 SKIPPED. Checker module, not a rate library. | Prompt was the cause. | None. |

### Drop or do not ship in v1

| # | Drop | Why |
|---|---|---|
| D1 | **`current_yield_verified` as a license for Kd < Rf.** | This is how Sep 7 survives 2.40. A YTM below Rf is not opportunity cost outside negative-rate markets. Keep current yield as a **source**; do not keep it as a **below-Rf hatch**. |
| D2 | **Reliance on `equity at/below book` as the distress OR.** | Would **not** have fired (market cap $94.0B vs book 89763). Keep as optional disclosure, not as the clause that “saves” the gate. |
| D3 | **Shared WACC calculator / pasted 9% / July 25 premium / module default.** | Violates existing law (`RESEARCH_AGENTS.md` §5b, `region_integration.md`, Agent 5 “NEVER paste”). Recreates folklore. |
| D4 | **Mandated Blume, mandated unlever-relever, mandated non-zero dual-class bp.** | Overfit; contradicts “dials may be 0” after honest reject; false-FAILs utilities and widely-held names. |
| D5 | **FAIL when tape-implied WACC ≠ model.** | Forces FV = price. Conservative value wants a **honest hurdle**, not a no-MoS identity. Draft already says do not FAIL the tape — keep that. |
| D6 | **WACC > Rf as the primary FAIL.** | Sep 7 WACC 6.145% is **already** > Rf 4.784% (spread 136 bp). It would not have caught the incident. Optional WARN later; not v1 load-bearing. |

### Add (v1 if cheap; else wave 2)

| # | Add | Wave | Catch Sep 7? | False FAIL? |
|---|---|---|---|---|
| A1 | **`spread_bp` identity; `rf_plus_spread` with 0 bp is FAIL** except a named gov/AAA hatch (not cable, not “IG”). | **v1** | If they flee coupon into 0 bp spread, **yes**. | AAA/gov only. Do not paste “150 bp minimum.” |
| A2 | **Print `roic_minus_ke` (and Ke vs WACC) next to `spread_mid_cycle`.** Agent 13 grades leverage-driven franchise theater. No machine FAIL that ROIC must exceed Ke. | **v1** (field + prompt; not a FAIL) | Would have shown 10.01% vs Ke 9.09% vs WACC 6.14%. | None. |
| A3 | **If LQ/FDD has `debt_fair_value` materially below carrying, coupon/par Kd is FAIL** (market already said YTM > coupon). | **v1** | **Yes** (79700 vs 90400). | Only when the session already extracted the fair-value note. |
| A4 | **Agent 5: dual-class/control reject may be 0, but “risk via bear weight only” while primary MoS uses base is an Agent 13 finding.** | **v1** prompt | Would have flagged dual-class = 0 + base $59.83. | None (finding, not machine FAIL). |
| A5 | **Rf currency vs cash-flow currency identity** (or explicit FX policy), machine WARN. | Wave 2 | No (USD model). | Avoids non-US false comfort. |
| A6 | **Lease liability in `wd` when `leases=capitalized_both`; preferred as a third claim.** | Wave 2 | Unlikely material vs coupon Kd. | Mixing leases is already an ROIC FAIL; do not double-FAIL opex-lease names. |
| A7 | **Do not let a destock/OM haircut close R4.** If `independence_gate` or crushed OM sits next to a <200 bp gap and `kd_source` was recently coupon-like, Agent 13 major. | Wave 2 | Sep 7 used Street Y1 (gap was visible). | Destock-in-base already gated by §10c. |

### One shippable v1 vs later

**v1 (2.40.0):** R1–R10 + D1–D6 + A1–A4. Checker like `roic_identity.py`. Schema object `wacc_buildup` with `applies`. Agent 5 self-check item (12) and Agent 13 `4-wacc`. Exemplar Pair 1 in `harness/exemplars/rationale_quality.md` should add a **BAD** “matches_buildup / coupon Kd / trough wd” next to the existing BAD “industry standard WACC” — the GOOD exemplar already uses after-tax Kd 3.8% at **12%** debt, which is the healthy shape, but it does not teach Kd vs Rf.

**Later:** A5–A7, beta-policy substance, lease/preferred claims, any `WACC > Rf` WARN.

Do **not** rewrite CMCSA `2026-09-07`. New runs on ≥2.40 fail closed; old stamps SKIPPED.

---

## What I would trust, as the person writing the check

I will write a check for residual equity only if the discount rate is an **opportunity cost**: Rf for the cash-flow currency, a beta I can defend as forward, ERP with a rejected alternative, **Kd at which the firm could issue today** (YTM or Rf+spread, never the coupon it lucked into), and **weights the going concern will actually run at**, not the tape’s D/(D+E) after equity has been crushed.

I will not trust:

- `matches_buildup` on a 4% coupon vs 4.78% Rf.
- `franchise_mos` because 10.01% > 6.14% when 10.01% is barely above Ke 9.09%.
- Dual-class = 0 because a module forbids a paste, with the residual dumped into bear mass while **base** FV is the MoS.
- A +25 bp “ops sleeve” as the idiosyncratic-risk control.
- `priced_for_perfection=false` as permission to treat a 300 bp implied-WACC gap as MoS rather than as a CoC bug.
- Gordon at WACC − g = 4.14% with ~70% of EV in TV, funded by that WACC.
- A hatch that says “we quoted a YTM below Rf, so the identity is satisfied.”

July 25’s pad was the wrong fix (unscripted conservatism). Sep 7’s match was the wrong obedience. 2.40 should make the **ingredients** legal and keep the **arithmetic** honest. That is the same skill as ROIC identity: the DCF defines value only after the hurdle is a cost of capital, not a coupon.

---

## Citations (law and pattern)

- Conservatism dials / high-WACC stacking: `harness/RESEARCH_AGENTS.md` §10c.8; `packages/kd_research/valuation_hygiene.py` (`DIAL_KEYS`, stacking message).
- ROIC hurdle = in-model WACC; `franchise_mos` only on `above_wacc`: `harness/RESEARCH_AGENTS.md` §10d; `packages/kd_research/roic_identity.py`; Agent 5 2b; Agent 13 `4-roic`.
- No hardcoded regional WACC / family discounts: `harness/RESEARCH_AGENTS.md` §5b, §9b; `harness/region_integration.md`; `harness/modules/region_us.md`; Agent 5 step 2 “may be 0” / “NEVER paste.”
- ERP judgment, no mandated value: Agent 5 hard constraint; `harness/exemplars/valuation_decision_quality.md` Pair 4.
- WACC rationale exemplar (healthy 12% debt weight, not trough 49%): `harness/exemplars/rationale_quality.md` Pair 1.
- Schema today has no `wacc_buildup` object; `conservatism_dials` and `roic_identity` only: `harness/schemas/valuation_model.schema.json`.
- Incident files as listed in `eng/sessions/2026-09-07-wacc-buildup-gate/handoffs/00_assignment.md`.
