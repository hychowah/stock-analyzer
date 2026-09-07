# Risk PM audit — WACC-buildup identity (harness 2.40 draft)

Persona: capital allocator. The desk buys duration, not a schema-valid formula.  
Incident (read-only): `archive/research/CMCSA/2026-09-07`. Do not rewrite it.

---

## Lead answer

**Ship the draft identity. Do not ship it as written.**

The Sep 7 run would have been a **blocked ticket**, not a 55% MoS bid, if coupon-as-Kd and trough `current_market` weights were machine-illegal. Those two FAILs are load-bearing and low-collateral. Arithmetic identity and “coupon is not `kd_source`” are hygiene, not the risk.

What the draft still lets through is the thing a PM actually marks: **a 300 bp cost-of-capital miss that prints as franchise MoS, with governance parked in bear weights while every scenario is discounted at the same crushed WACC.** That is a risk-register hole, not a conservatism dial.

Do **not** average July 9.0% (`archive/research/CMCSA/2026-07-25/data/valuation_model.json` assumptions.wacc, +345 bp pad on ~5.55% raw CAPM) with Sep 6.145% (`archive/research/CMCSA/2026-09-07/data/valuation_model.json` `assumptions.wacc`). July hid a bad buildup behind a number that happened to sit near the tape. Sep obeyed `wacc_vs_buildup: matches_buildup` and printed a utility-like 6.14% as a **bid**. Neither is the required-return book. The tape overlay on the Sep base path is **9.13%** (`data/compute/valuation_result.json` `reverse_engineering.implied.wacc_on_base_path` = 0.09132). That overlay is not a compromise WACC and not a license to pad.

**Would this draft have stopped a PM from treating $59.83 as a bid on CMCSA at $26.49?**  
On paperwork: **yes** — pretax Kd 4.0% < Rf 4.784%, coupon comment in `data/compute/valuation.py` (`kd_pretax = 0.040  # ~coupon/effective...`), `wd` ≈ 0.490 with implied gap ≈ 299 bp. Gates 1–3 FAIL. Gate 5 FAILs a rationale that is only “tape is cheap” (`valuation_model.json` `reverse_engineering.rationale` is exactly that class).  
On economics, if Agent 5 “fixes” Kd to `rf_plus_spread` with **0 bp** and labels trough 49% debt `target`: **no**. WACC still ~6.4%. Base FV still a duration bid. The desk would still see ~55% MoS unless v1 also (a) forbids target-weights copying the trough, (b) prints the **dollar** left tail at tape-implied WACC, and (c) refuses `franchise_mos` / `initiate` while that tail is the whole MoS.

False-FAIL risk on a clean utility, net-cash software name, or JPY issuer is **real but containable** if hatches stay named and the distressed-weight tripwire stays `wd > 0.35` **and** (gap **or** equity ≤ book). Do not compare every Kd to `^TNX`. Do not WARN net-cash names for ignoring Kd. Do not name the Japan hatch only `negative_rate_market`.

---

## The left tail in dollars (this is the book)

From session files, not invented:

| Item | Value | Path |
|---|---|---|
| Price | $26.49 | `data/compute/valuation_result.json` |
| Base FV | $59.83 | `data/valuation_model.json` `fair_value.base` |
| MoS | 55.72% | same, `margin_of_safety_pct` |
| Bear FV | $39.56 | same (still 33% above tape at the **same** WACC) |
| g=0 equity | $40.20 | `roic_identity.g0_counterfactual.equity_fv` |
| Model WACC | 6.145% | `assumptions.wacc` / script |
| Ke | 9.092% | `assumptions.ke` |
| Rf | 4.784% (`^TNX`) | `data/market_inputs_snapshot.json` |
| Kd pretax | 4.0% coupon buckets 3.3–4.2% | `valuation.py` |
| we / wd | 0.510 / 0.490 on $94.0B mkt cap vs $90.4B gross debt | `valuation_result.json` intermediates |
| Tape-implied WACC | 9.13% on base path | reverse_engineering |
| Mid-cycle ROIC | 10.01% vs WACC 6.14% → `above_wacc` / `franchise_mos` | `roic_identity` |
| Dual-class premium | **0** | `assumptions.dual_class_governance_premium`; “risk via bear 0.34 and SOTP 10% haircut” |
| Sensitivity | WACC 5.14%–6.64% only; at 6.64% / 17% OM, FV **$51.30** | `valuation_model.json` `sensitivity.grid` |

**Mark:** $59.83 − $26.49 = **$33.34/sh**. That is not “upside from fiber/FWA.” It is the present value of discounting the same FCFF path at 6.14% instead of 9.13%. The sensitivity book never reaches the tape: +50 bp still prints $51.30 (48% MoS). g=0 still prints $40.20. Bear at the same WACC still prints $39.56. SOTP $37.40 (`multi_method_reconciliation.cross_check_fv`) is closer to tape and was **not** primary because |Δ| 37.5% < 40%.

Ke **9.092% ≈ tape 9.13%**. The equity required return already matches the overlay. The fake bid is **mixing 49% coupon debt at trough equity value**. A going-concern duration book is closer to Ke (target weights, current yield). The 6.14% number is a model that has given up on Kd and weights, then called the result a bid.

If a PM sizes 55% MoS as “I can be wrong on earnings,” they are unhedged on the **entire** CoC error. That is the left tail to watch: **FV(model WACC) − FV(tape-implied WACC)** on the **same** path, here ≈ $33/sh, 100% of reported MoS.

---

## 1. Residual analysis error (after this draft)

The machine will fail **impossible ingredients**. Agent 5 can still print an economically too-low (or too-high) WACC. Residual holes, ranked by whether they still let $59.83 print as a bid:

### Still too low (the live left tail)

1. **`rf_plus_spread` with 0 bp.** Gate 1 is `kd_pretax >= rf`. Kd = Rf PASSES. On Sep 7 weights that lifts WACC from 6.14% only to ~6.44% (0.510×9.092% + 0.490×4.784%×0.77). Implied gap still ~270 bp. Coupon illegal does not save this.

2. **`weight_policy=target` (or `blended`) with trough `wd`.** Gate 3 only forbids **only** `current_market` when the tripwire fires. Copying `wd=0.49` into `target` because “that is the structure today” PASSES. Distressed-equity hook `target_weights` becomes a label. This is the easiest game.

3. **Omit reverse-engineering implied WACC.** Gate 5 is “when present.” Agent 5 already writes reverse-eng (`agent_prompts.md` Agent 5 step 7). If implied WACC is dropped or only terminal OM is inverted, the 200 bp gap never fires. Circular: the gap that would have caught trough weights is optional.

4. **200 bp cliff.** Raise model WACC to ~7.2% (still ~190 bp below 9.13%). Tripwire off. Rationale not required. Duration still prints a fat MoS. Threshold gaming.

5. **ROIC identity still hurdles in-model WACC** (`harness/RESEARCH_AGENTS.md` §10d.1: “Hurdle is **in-model WACC**, not a 15% Buffett paste”; `packages/kd_research/roic_identity.py` matches `assumptions.wacc` within 5 bp). A too-low WACC **licenses** `above_wacc` / `franchise_mos`. Sep 7: 10.01% − 6.14% = 387 bp spread. Even at tape 9.13%, ROIC 10.01% is still `above_wacc` (88 bp > 50 bp band). So the franchise **bucket** is not only a 6% artifact — but the **55% MoS** is. Draft does not touch `cheap_claim` when the dollar gap is the whole MoS.

6. **Named Ke sleeve = 0, risk in bear weights, same WACC on all scenarios.** Law already allows CoC/governance dials to be 0 (`agent_prompts.md` Agent 5 step 2: “CoC/governance dials (may be 0)”; `region_us.md`: dual-class is a governance dial, not an automatic country premium; `region_integration.md` P4: no hardcoded family-control discounts). Sep 7 used that correctly **as anti-paste** and incorrectly **as a risk transfer**: dual-class 0, ops sleeve +25 bp, bear 0.34, SOTP 10% haircut — **bear still $39.56 at 6.14% WACC**. Scenario mass does not change duration. Putting broadband/spin/control risk only in `scenario_probabilities.bear` while WACC is crushed is a hole the draft does not FAIL.

7. **Beta / ERP judgment.** Draft `beta_policy` is “not all mandated in v1.” Raw 0.719 or Yahoo 0.662 instead of Blume 0.812 lowers Ke. ERP 5.0% with a rejected implied competitor already satisfies `valuation_decision_quality.md` Pair 4 and Agent 5 “ERP / CoC” constraint. Too-low ERP still legal. Too-high ERP (July-style folklore) also legal. Machine will not catch either.

8. **Leases, preferred, cash, pensions.** ROIC already FAILs mixed leases (`opex_and_out_of_ic` vs `capitalized_both`). WACC weights can still ignore operating leases (Sep 7 did: leases out of IC **and** out of `wd`). Preferred not in the object. Cash: they weighted **gross** debt vs market equity (correct WACC practice) but then treated trough E as the going-concern weight. Net-cash names with tiny `wd` will not trip gate 3 — good — but a levered name that nets cash into E to shrink `wd` below 0.35 can dodge the tripwire.

9. **Local Rf / currency.** Existing law: cash-flow currency vs discount-rate currency (`agent_prompts.md` Agent 5 step 2; `RESEARCH_AGENTS.md` §5b). Draft does not add a currency identity. Agent 5 can still discount JPY FCFF at `^TNX` or USD ERP, or compare JPY Kd to US Rf and FAIL/PASS for the wrong reason.

10. **WACC too high (right tail, smaller for this incident).** Blume toward 1 on a 0.3 beta, fat ERP, `rf_plus_spread` with a junk spread on IG paper, target `wd` at a trough **low** (understate debt on a cash-rich cyclically-high equity). `wacc_vs_buildup` still `matches_buildup` / `applies_in=none`. Padding is what the dial was built to catch (`RESEARCH_AGENTS.md` §10c.8; `packages/kd_research/valuation_hygiene.py` `DIAL_KEYS`). The new identity must not re-teach padding as the fix for coupon-Kd.

### Circular implied-gap

Implied WACC is a **tape overlay** on a stated path. Using it as the required-return input makes WACC = price. Draft correctly does **not** FAIL the tape for disagreeing. Residual error: if `wacc_gap_rationale` is a 40-char essay that names Kd once, gate 5 PASSES and the PM still sees $59.83 as FV. Without a **dollar** identity (`fv_at_implied_wacc` vs `fair_value.base`), the rationale is theater.

---

## 2. Wrong prompt (what would reprint Sep 7, or a new failure)

### Already in law — this is why Sep 7 “obeyed”

- **`wacc_vs_buildup` exists to stop silent padding**, not to stop a junk buildup. `RESEARCH_AGENTS.md` §10c.8; Agent 5 4e; schema `conservatism_dials`; `valuation_hygiene.py` only checks key presence / stacking. Sep 7 wrote `dial: matches_buildup`, `applies_in: none`, rationale “No silent WACC pad above buildup.” Machine PASS. That prompt **caused** the failure mode once July’s +345 bp pad was taught as illegal.

- **“Do not paste module WACC / no hardcoded family discount.”** Agent 5 hard constraints + step 2; `RESEARCH_AGENTS.md` §1, §5b, §13 region row; `region_integration.md` item 6; `region_us.md` lines 6, 19. Agent 5 read this as: dual-class premium **must** be 0, and 6.14% is virtuous because it matches CAPM. `fair_value.posture` even boasts “WACC matches CAPM+ops-sleeve buildup without dual-class Ke paste.”

- **ROIC franchise license on in-model WACC.** Agent 5 2b; §10d.4 `franchise_mos` only when `above_wacc`; Agent 13 4-roic. A low WACC is a **license**, not a yellow flag. Agent 13 is told Gordon-with-ROIC≤WACC is major; it is **not** told that ROIC 10% vs WACC 6% with tape at 9% is a CoC miss.

- **Agent 13 has no Kd / weights / implied-gap band.** Checks 4-roic and 4-midcycle; reverse-eng is PFP surface (check 9). A 300 bp WACC gap disclosed as “tape is cheap / not priced-for-perfection” is **GOOD** under Pair 2 of `valuation_decision_quality.md` (implied WACC named, PFP false). Auditor is trained to reward the disclosure that a PM would treat as a bid.

- **SELF-CHECK list** (`agent_prompts.md` Agent 5, items 1–11): MoS units, rationales, terminal_consistency, PFP, ERP competitor, Street, four dials, `roic_identity`, mid-cycle window. **No Kd vs Rf. No coupon ban. No weight policy.** Adding `wacc_buildup` as item 12 without changing 4e’s “matches_buildup = virtuous” will produce Sep 7 plus a filled object.

### If we add the draft text carelessly

- **Contradiction with “no hardcoded WACC.”** Any prompt that says “use ~9%,” “utilities 6%,” “never below 8%,” or “match July CMCSA” violates `RESEARCH_AGENTS.md` §1 and `region_integration.md`. The hatch must stay a **name** (`negative_rate_market`, `current_yield_verified`), not a number.

- **Contradiction with `wacc_vs_buildup`.** If Agent 5 is told both “do not pad above buildup” and “if implied gap > 200 bp, lift WACC,” the agent will pad again (July). Draft’s “idiosyncratic risk is a **named Ke sleeve** with use/reject — not a silent add-on after mixing with cheap debt” is the right sentence. Do not write “add 300 bp to WACC to close the gap.”

- **Dual-class = 0 vs crushed WACC.** If 2.40 text says “keep dual-class 0; put risk in bear,” we **encode** the Sep 7 hole. Region law forbids a **module paste**. It does not forbid a **judged** Ke sleeve with basis. Prompt must say: dial may be 0 **only if** the same risk is not already erasing duration via trough `wd` × coupon Kd; bear mass at an unchanged WACC is not a substitute.

- **`franchise_mos` + implied gap.** If gate 5 allows a rationale “franchise MoS, tape is cheap” (Sep 7 `cheap_claim.rationale` + `reverse_engineering.rationale`), we teach Agent 5 the exact essay that failed. Draft already says the rationale must **not only** be that. **Keep that clause.** Agent 13 4-roic must get a sibling: implied-gap essay that is only cheap/franchise is **major**.

- **Banks / insurance / REITs.** Agent 5 2b and §10d.5 already `applies:false` for industrial ROIC. If `wacc_buildup.applies` is not mirrored in the prompt as the same hatch, Agent 5 will invent a WACC for a bank to satisfy a new required object, **or** Agent 13 will major a bank for missing it. Copy the ROIC sentence: `applies:false` with ≥40 char reason + native analog (`roe_vs_ke` / NAV / AFFO).

- **Exemplars.** `rationale_quality.md` Pair 1 GOOD is a 9.5% tech WACC with 12% debt weight and after-tax Kd 3.8%. That is a **shape**, not a rate. If Agent 5 copies 3.8% Kd into a 4.8% Rf world, we reprint coupon-Kd. Add a BAD twin: “matches_buildup” with coupon < Rf and trough `wd`. Do not paste a mandated WACC into the exemplar.

---

## 3. Bad harness (how the gate itself hurts)

### False FAIL (collateral)

| Book | How draft false-FAILs | What v1 must do |
|---|---|---|
| **Clean utility** | IG current YTM can sit **a few bp below 10Y** (shorter tenor, curve). `kd_pretax >= rf` vs `^TNX` FAILs a real quote. High `wd` is **normal**, not distressed; `wd > 0.35` alone must not trip. | Compare Kd to **same-currency, similar-tenor** Rf, or accept `current_yield_verified` with a quoted YTM even if slightly < 10Y. Tripwire is `wd > 0.35` **and** (gap > 200 bp **or** equity ≤ book). A utility at book with honest current yield and no 200 bp gap PASSES. WACC may sit close to Rf; still require **WACC > Rf** (draft hatch text is right). |
| **Net-cash software** | Tiny `wd` is legal. If the name is cheap, implied WACC ≫ model (duration/growth, not Kd). Gate 5 WARN “rationale ignores Kd/weights” is a **false WARN**. | WARN on Kd/weights **only if** `wd > 0.20` or Kd vs Rf is live. Otherwise duration/growth/ERP is a complete rationale. Do not force `target_weights` on `wd` ≈ 0. |
| **JPY issuer** | Hatch name `negative_rate_market` is **stale**. JGBs can be low-positive with Kd ≤ local 10Y on a curve/tenor mismatch. Comparing to US `^TNX` FAILs or passes for the wrong Rf. | Hatch must accept **local curve / quoted YTM** (`current_yield_verified` with local Rf evidence), not only negative-rate folklore. Currency match already law — enforce Rf source = cash-flow currency in the identity (`rf` field vs `market_context.cost_of_capital_flags`). |
| **Banks / REITs / insurance** | Forcing `applies:true` industrial WACC. | Same pattern as `roic_identity.py`: `applies:false` + ≥40 char reason; **SKIPPED** ingredients. Do not FAIL missing Kd. |

### Overfit to CMCSA

- `wd > 0.35` is a cable/leverage constant. A 30% debt name with coupon Kd and equity at 0.4× book would **miss** the tripwire. Prefer **or** equity ≤ book (already in the draft — **keep**, do not drop).
- Coupon buckets 3.3–4.2% vs Rf 4.78% is this vintage. Next year’s 5.5% coupons vs 4.8% Rf PASSES gate 1 and can still be the wrong **source** (coupon ≠ yield). Gate 2 (illegal `coupon`) is what generalizes. **Do not** bake 4.0% or 9% anywhere (`issue.json` non_goals already).
- Implied 200 bp matches this 299 bp incident. It will miss a 180 bp, $20/sh duration error on a long-duration name. Complementary **dollar** gate (below) is the anti-overfit.

### Easy to game (if v1 ships as drafted)

1. `kd_source=rf_plus_spread`, spread = 0.  
2. `weight_policy=target`, `wd` = current 0.49, `distressed_equity_hook=target_weights`.  
3. Drop `implied.wacc_on_base_path`.  
4. Nudge WACC +190 bp.  
5. 40-char rationale that mentions “current yield” and “tape cheap.”  
6. Blume on/off to taste (not gated).  
7. Shared calculator that pastes Rf/ERP/Kd — **do not build**. Pattern is `roic_identity.py`: rehydrate, never write g or FV. Same here: never write WACC.

### Shared calculator temptation

Agent 5 writes a new `S/data/compute/valuation.py` every session (`RESEARCH_AGENTS.md` §1.3; assignment). A shared WACC function with default ERP 5%, spread 0, Blume on, will become the pasted table the harness forbids. Checker only.

---

## 4. Load-bearing change — require / drop / add

Rank: **(A) would have caught Sep 7** × **(B) false-FAIL on a healthy book**. Ship one v1; park the rest.

### Require in v1 (ship)

| Rank | Change | Catch Sep 7? | False FAIL? |
|---|---|---|---|
| **R1** | **Coupon illegal as `kd_source`.** Only `current_yield` or `rf_plus_spread`. Coupon may be disclosed as cross-check. | **Yes** (`valuation.py` coupon comment; FDD buckets as input). | **No.** Utilities/net-cash/JPY can quote YTM or Rf+spread. |
| **R2** | **`kd_pretax >= rf` unless named hatch** (`current_yield_verified` with in-session quote, or local-curve hatch — not only `negative_rate_market`). Coupon-below-Rf is always FAIL. | **Yes** (4.0% < 4.784%). | **Low** if hatch accepts a real quote slightly under 10Y and local Rf for JPY. **High** if Rf is always `^TNX`. |
| **R3** | **Distressed-weight tripwire** as drafted (`wd > 0.35` **and** (implied gap > 200 bp **or** equity ≤ book)) → cannot use **only** `current_market`. **Plus anti-copy:** when the tripwire fires, `target`/`blended` `wd` may not equal current `wd` within 3 pp unless a going-concern target is evidenced (peer/management **target** structure, not today’s trough E). | **Yes** (0.490 and 299 bp). Anti-copy stops the game that would otherwise reprint $59.83. | **Low** if utilities without 200 bp gap / equity≪book stay on `current_market`. Net-cash `wd` < 0.35 never trips. |
| **R4** | **Arithmetic 5 bp** vs formula, `assumptions.wacc`, `roic_identity.wacc`. Same spirit as `roic_identity.py` `WACC_EPS`. | Hygiene (Sep 7 already matched). | **No.** |
| **R5** | **Implied-gap rationale not “tape is cheap / franchise MoS.”** Require `wacc_gap_rationale` ≥40 chars that names **Kd and/or weights** when `wd > 0.20`; else duration/growth/ERP is enough (protects net-cash). **Do not FAIL the tape.** | **Yes** (Sep rationale is the forbidden class). | **Low** with the `wd > 0.20` qualifier. |
| **R6** | **Dollar left-tail print (new, load-bearing).** When reverse-eng implied WACC exists, script must emit `fv_at_implied_wacc` on the **same** base path (or the sensitivity grid must include that WACC cell). Identity: `|fv_at_implied_wacc − price|` small. **WARN** if `(base FV − fv_at_implied_wacc) / price > 0.25` (25% of spot) and `cheap_claim=franchise_mos`. Do not auto-rewrite FV. | **Yes.** Sep 7: $59.83 vs ~$26.49 is 126% of spot. Sensitivity never showed it. A PM cannot treat $59.83 as a bid if the ticket shows the CoC tail **is** the MoS. | **No FAIL** on utilities/net-cash that already sit near tape. WARN, not FAIL, so we do not force WACC = implied. |
| **R7** | **`applies:false` hatch** for banks/insurance/REITs/non-WACC natives, ≥40 chars, mirror ROIC. Version-band ≥ 2.40.0; old stamps SKIPPED. | n/a (CMCSA applies). | **Prevents** bank/REIT collateral. |
| **R8** | **Keep `wacc_vs_buildup: matches_buildup`.** Idiosyncratic risk = **named Ke sleeve** (ops / size / governance) with use/reject. Prompt: **do not** close an implied gap by padding WACC after mixing cheap debt. | Prevents July regression. | **No.** |

### Drop / do not ship in v1

| Item | Why |
|---|---|
| **Any pasted WACC/ERP/Kd number in prompts or modules** | Contradicts §1 / region law; reprints July with extra steps. |
| **Mandated `beta_policy=blume`** | False-moves low-beta utilities and net-cash; Blume toward 1 is a **judgment**. Enum is enough. |
| **FAIL the tape for implied gap** | Circular; makes WACC a price. Overlay stays overlay. |
| **FAIL dual-class premium ≠ some module %** | Forbidden family-control table. |
| **Shared WACC calculator** | Becomes the hardcoded table. |
| **Averaging 9% and 6%** | Not a required return. |
| **Rewriting CMCSA 2026-09-07** | Immutable incident. |

### Add in v1 (small, high leverage)

| Rank | Add | Catch Sep 7? | False FAIL? |
|---|---|---|---|
| **A1** | **Two-line CoC header on the object:** `required_return_wacc` (target/blended weights, legal Kd) vs `tape_implied_wacc` (overlay, may be null). Machine: they must not be silently the same field. PM can see whether a low WACC is a **bid** or a **model that gave up**. | **Yes** (6.14% vs 9.13% would be two numbers). | **No** if overlay is optional when reverse-eng missing (then WARN, not FAIL). |
| **A2** | **Same-WACC / bear-weight hole:** if a named Ke sleeve is 0 (dual-class, size, ops) **and** the tripwire in R3 fires, FAIL unless the reject rationale says how duration is **not** being used as the dump. “Bear weight 0.34” at unchanged WACC is **not** an accept. | **Yes** (the risk-register hole). | **Low** — only fires with distressed weights. Clean utility/net-cash with sleeve=0 PASSES. |
| **A3** | **Agent 13 band `4-wacc`:** coupon as Kd = major; Kd < Rf without hatch = major; implied-gap essay only cheap/franchise = major; `applies:false` banks not a miss. Mirror Street’s 4-street. Machine FAIL is not enough if audit still PASS-theaters. | **Yes.** | Same hatches as R2/R7. |
| **A4** | **Rf tenor note (disclosure, not a number):** `rf_tenor` / `kd_tenor` or one sentence in rationale. Stops utility 5Y YTM vs 10Y `^TNX` false FAIL by making the hatch checkable. | n/a | **Reduces** collateral. |

### Later wave (not v1)

- Dual ROIC hurdle vs `required_return_wacc` (not only in-model WACC) before `franchise_mos`. Sep 7 would still be `above_wacc` at 9.13% (10.01% − 9.13% = 88 bp) — so this would **not** have been the catch; R6’s dollar tail would. Still worth a later wave so a 7% WACC cannot license a 7.2% ROIC franchise.
- Operating leases in WACC `wd` when `leases=capitalized_both`; preferred as a third claim; net-cash policy (`wd` floor 0, do not lever cash).
- Gate 5 dollar threshold calibrated on more names than CMCSA.
- `initiate`/`add` illegal when R6 WARN fires **and** `decision_usefulness=high` solely from crushed-WACC MoS. That is a decision-law change; keep it off v1 so 2.40 stays an identity, not a trading rule. Flag for 2.41.

---

## Shippable v1 vs later

**v1 (2.40.0):** R1–R8 + A1–A4. Checker patterned on `packages/kd_research/roic_identity.py` (rehydrate, version-band, `applies:false`, never write the rate). Prompts: Agent 5 new 2c + self-check item; Agent 13 `4-wacc`; §10e in `RESEARCH_AGENTS.md`; §13 one machine row. Exemplar BAD: matches_buildup + coupon < Rf + trough `wd` + franchise MoS. No rate table.

**Not v1:** ROIC dual hurdle, lease/preferred weights, `initiate` block, shared calculator, any “correct” WACC.

---

## Direct answers to the four questions

1. **Residual error:** Yes. 0 bp spread, copied target `wd`, omitted implied WACC, 190 bp nudge, ROIC licensed on in-model WACC, dual-class 0 with same WACC on bear, ERP/beta judgment, leases/preferred/cash, wrong-currency Rf. The dollar tail can still equal the whole MoS.

2. **Wrong prompt:** `wacc_vs_buildup` + no-pad + dual-class-may-be-0 + franchise on in-model WACC + Agent 13 with no CoC band **reprinted Sep 7**. Careless 2.40 text that says “lift WACC toward the tape” reprints July. Careless “put governance in bear” reprints the risk-register hole.

3. **Bad harness:** False FAIL if Rf is always `^TNX`, if `wd > 0.35` alone trips utilities, if net-cash WARNs for ignoring Kd, if Japan hatch is only negative-rate, if banks must apply. Games: 0 bp spread, target=trough, drop implied WACC. Shared calculator = hardcoded table.

4. **Load-bearing:** Require R1–R3 (ingredients + anti-copy weights) and R6/A1 (dollar tail + duration book vs tape overlay). Those would have stopped treating **$59.83 as a bid at $26.49**. Drop pasted rates, mandated Blume, FAIL-the-tape, and rewriting the incident. Add A2 so dual-class 0 + crushed WACC cannot hide in bear weights.

A low WACC is a **bid** only if Kd is a current claim and weights are a going-concern book. Sep 7 was a **model that gave up**, then labeled the output margin of safety. 2.40 should make that ticket unprintable — not 7.5% prettier.
