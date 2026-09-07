# Forensic accountant audit — WACC-buildup identity (harness 2.40 draft)

Persona: quality-of-earnings / cash-conversion skeptic. Reported earnings are a claim; the bridge to cash is the work. For WACC the bridge is: coupon vs current yield; book vs market capital structure; gross debt vs net debt; leases in Kd and in weights; preferred / NCI; cash as negative debt; a tax shield that will not be earned.

**This is not a rewrite brief.** CMCSA `archive/research/CMCSA/2026-09-07` is a read-only incident. Do not operate on that session.

---

## Lead answer

**Ship the identity. Do not ship arithmetic-as-quality.** Sep 7 already *matched* `we×Ke + wd×Kd(1−t)` to 5 bp and wrote `wacc_vs_buildup: matches_buildup` / `applies_in=none`. The machine that exists today (`packages/kd_research/valuation_hygiene.py` dial-key presence; `packages/kd_research/roic_identity.py` 5 bp WACC match to `assumptions.wacc`) would **PASS** the coupon-as-Kd print. The failure is ingredient identity, not algebra.

The Sep 7 stack, from the files:

| Bridge piece | What the session did | Forensic reading |
|---|---|---|
| Coupon vs current yield | `kd_pretax = 0.040` from FDD coupon buckets 3.3–4.2% (`archive/research/CMCSA/2026-09-07/data/compute/valuation.py` lines 186–189) | Accounting leftover. Rf from `^TNX` is 4.784% (`data/market_inputs_snapshot.json`). Pretax Kd sits **78 bp below Rf**. |
| Book vs market weights | `we=0.510` / `wd=0.490` on **current** market cap $94.003B vs **carrying** gross debt $90.4B (`data/compute/valuation_result.json` `intermediates`) | Trough equity × cheap coupon Kd. Book equity is $89.763B (`registry/latest_quarter.json`) — market is *slightly above* book, so an “equity at/below book” tripwire **does not fire**. The implied-WACC-gap prong must. |
| Gross vs net vs fair | EV bridge uses net debt $82.739B; WACC weights use gross carrying $90.4B; **debt fair value $79.7B sits unused** in the same LQ object | Gross-carrying in the weight of a below-Rf Kd *increases* the damage. The session had a market claim on the bonds and ignored it. |
| Leases | `opex_and_out_of_ic`; finance leases $2.1B already in the debt table; operating-lease liability $6,097m left out of IC and out of `wd` (FDD `debt_leases`) | Internally consistent with the ROIC lease convention. Not the Sep 7 killer. Still a v1 hole if a later session capitalizes leases in capex *and* net debt *and* WACC weights. |
| Preferred / NCI | `total_equity` $89,770m vs `shareholders_equity` $89,763m | Immaterial here. Identity should still declare the slot so a bank/REIT/pref stack cannot hide in `wd`. |
| Cash as negative debt | Cash $7.661B cut from EV, **not** from WACC weights | Opposite of the net-cash-tech hatch. Here, leaving cash out of weights raised `wd` on a 3.08% after-tax Kd. |
| Tax shield | `tax = 0.23` from FY2025 ETR 23.7%, applied as `kd_after = 0.040 × (1−0.23) = 0.0308` | Historical ETR pasted onto a coupon the firm cannot refinance at. After-tax Kd is **170 bp below Rf**. Terminal Gordon still discounts a firm that rolls 2015 coupons forever (`terminal_consistency.wacc_minus_g = 0.0414` on WACC 6.145% / g 2%). |

Tape-implied WACC on the base path is **9.13%** (`valuation_result.json` `reverse_engineering.implied.wacc_on_base_path = 0.091324…`). Gap vs model 6.145% is **~299 bp**. `cheap_claim.class = franchise_mos` because mid-cycle ROIC 10.01% cleared **in-model** WACC 6.14% (`data/valuation_model.json` `roic_identity`). That is the franchise license a too-low WACC buys.

July 25 padded raw CAPM ~5.55% by **+345 bp** to 9.0% (`archive/research/CMCSA/2026-07-25/data/valuation_model.json` `assumptions.wacc`). Later law taught “do not pad; match the buildup.” Sep 7 obeyed the *letter* and printed a utility-like 6.14%. **The draft is right that the cure is ingredient gates, not a pasted 9%.** It is wrong if v1 is only “WACC equals the formula” plus “coupon is a banned string.”

Kd ≥ Rf **alone** does not get this name off 6%. Swap 4.0% for Rf 4.784% pretax, keep trough `wd=49%`, after-tax Kd becomes ~3.68%, WACC ≈ **6.44%** — still a utility. The distressed-weight tripwire (`wd > 0.35` **and** implied gap > 200 bp) is the second load-bearing bolt. Arithmetic is hygiene, not the catch.

---

## 1. Residual analysis error

After this draft, Agent 5 can still print an economically too-low (or too-high) WACC. The holes, in forensic order:

### 1.1 Kd still an accounting leftover (too low)

- **`rf_plus_spread` with 0 bp.** Legal `kd_source`, `kd_pretax == rf`, Kd-vs-Rf PASS. CMCSA would print ~6.4% and keep `franchise_mos`. The spread must be a decided `{value, rationale, basis}` number (`harness/RESEARCH_AGENTS.md` §6) — the draft does not FAIL a silent 0.
- **`current_yield_verified` hatch that quotes the coupon.** FDD Note 6 already labels “weighted-average interest rates based on the **stated coupon rate**” and then starts a sentence about the **effective** rate (`registry/filing_deep_dive.json` `footnotes.debt_leases.excerpt`). A session can paste that effective-rate fragment, set `kd_source=current_yield`, and claim the hatch. v1 must require a **quoted market YTM / bond price in-session**, not a footnote coupon restated as “yield.”
- **Unused `debt_fair_value`.** LQ stores `debt_fair_value: 79700` next to `total_debt_carrying_value: 90400` (`registry/latest_quarter.json`). Valuation.py never reads it. Carrying $90.4B vs FV $79.7B is a market claim that coupons are **below** current yields (bonds at a discount). Draft FAIL #1–2 catch coupon-below-Rf; they do **not** FAIL “had FV, used carrying.” That is the next coupon-shaped hole.
- **Tax-rate game.** `Kd(1−t)` with t = statutory 35% (or a one-time-high ETR) crushes after-tax Kd even when pretax Kd ≥ Rf. Sep 7 used 23% cash-tax proxy for *both* NOPAT and Kd — consistent, but the identity does not forbid a higher t on Kd only. A shield the firm will not earn (spin, NOLs, pretax loss, non-US mix) still lowers WACC.
- **Refinancing ignored in terminal.** Draft forces market Kd at t=0. It does not force the Gordon denominator to assume the book is **rolled at that Kd**. A session can put current YTM in year-1 WACC and still narrate “embedded 3.8% coupons persist.” Forensic bar: going-concern TV refinances at today’s Kd, not 2015 coupons.

### 1.2 Weights: missing cost or spent twice (too low *or* too high)

- **`target` / `blended` labeled, trough `wd` kept.** Tripwire fires; Agent 5 sets `weight_policy=target` with `wd=0.49` and a 40-char essay. Machine PASS. Need a WARN (not necessarily FAIL) when tripwire fired and `|wd_used − wd_current_market| < 200 bp`.
- **Gross carrying vs net vs FV.** Draft checks `we+wd≈1` and policy enum, not **which** D is in the weight. Using gross carrying + coupon Kd is how Sep 7 spent cheap debt twice (heavy `wd` × too-low Kd). Using net debt as the WACC weight **and** subtracting cash again at EV is the opposite double-count (too-high WACC on net-cash names). Identity should name `debt_measure` (`carrying` | `fair` | `net`) and `cash_in_weights` (`none` | `netted` | `surplus_out`).
- **Leases.** ROIC already forbids mixing Yahoo lease-grossed debt with opex leases (`RESEARCH_AGENTS.md` §10d.1; `roic_identity.py` `LEASES_OK`). Draft WACC object has no lease slot. Residual: `capitalized_both` without putting the lease liability in `wd` and a lease Kd in the blend (cost missing); or `opex_and_out_of_ic` while still adding operating leases to net debt / capex / WACC (spent three times). FDD already has operating-lease liability $6,097m and imputed interest $3,549m — a lease implicit rate exists and was not used as Kd.
- **Preferred / NCI / hybrids.** Not in the draft object. CMCSA NCI is noise. The next pref-heavy industrial or REIT-that-someone-forgot-to-`applies:false` will dump pref into `wd` at coupon Kd, or omit it from weights while subtracting it from equity value.
- **Unlever/relever at trough wd.** `distressed_equity_hook=unlever_relever` can *raise* levered beta (too high Ke) while `weight_policy=current_market` keeps 49% cheap debt (too low Kd weight). Or unlever at trough and relever at a cosmetic target — two different capital structures in one WACC. v1 should forbid mixing `current_market` weights with a relever-to-target beta unless `weight_policy` is `target`/`blended`.

### 1.3 Ke / beta / ERP (both directions; not the Sep 7 killer)

- **Beta policy is judgment.** Blume toward 1 on raw 0.719 *raised* Ke here (`intermediates.beta_blume = 0.8117`). On a 0.30 beta it would also raise Ke (conservative). The game is the opposite: **raw** 0.30 kept, or unlever-relever to a 0.4 asset beta at 15% target debt, while `wd` stays 49% in the WACC weights.
- **ERP still a folklore pick.** Agent 5 already must name a method and reject ≥1 competitor (`agent_prompts.md` Agent 5 ERP/CoC bullet; `valuation_decision_quality.md` Pair 4). Draft does not gate ERP vs Rf or vs implied. A 3.5% ERP on this stack prints WACC even closer to Rf.
- **Sleeves all zero while trough `wd` does the crushing.** Sep 7: `dual_class_premium = 0.0`, `structural_ops_premium = 0.0025` (`valuation.py` 155–157). Governance via bear 0.34 + SOTP 10% haircut (`assumptions.dual_class_governance_premium`). That is legal under “CoC/governance dials (may be 0)” (`agent_prompts.md` step 2) and “no hardcoded family-control discounts” (`RESEARCH_AGENTS.md` §5b). Residual: every named Ke sleeve = 0 **and** `weight_policy=current_market` **and** `wd>0.35`. Dual-class spent in bear/SOTP *and* in Ke is the opposite double-count; **all-zero + trough wd** is the Sep 7 shape.
- **FX sleeve on Ke and local WACC paste.** Sep 7’s +25 bp is labeled “Sky FX translation (not a UK country WACC paste)” — the right *comment*. Draft does not detect a second local-WACC paste in `market_context_hooks`.

### 1.4 Circular implied-gap (too high WACC if naively inverted)

- Reverse-engineered WACC is **path-dependent**. Optimistic FCFF + cheap tape → large implied WACC. Pessimistic FCFF + the same tape → small gap. FAIL #5 correctly does **not** FAIL the tape. Residual: Agent 5 writes a 40-char `wacc_gap_rationale` that names “Kd/weights” as tokens and keeps coupon Kd. Token-match is gameable. Require the rationale to **rehydrate** `kd_source` and `weight_policy` (same class as ROIC 5 bp / Street `delta_pct` identity), not a synonym of “tape is cheap / franchise MoS.”
- Using implied WACC **as** model WACC is circular (price in, price out). Draft does not invite that; keep it banned in the prompt.

### 1.5 ROIC franchise license (too low WACC → false friend)

Already law: hurdle is **in-model WACC** (`RESEARCH_AGENTS.md` §10d.1; `roic_identity.py` matches `assumptions.wacc` within 5 bp). A 6.14% hurdle turned 10.01% ROIC into `above_wacc` and licensed `franchise_mos`. If model WACC were the tape’s 9.13%, spread ≈ 88 bp — still `above_wacc` inside the 50 bp bucket, but the Gordon TV (70% of EV, `tv_share_of_ev_base = 0.6966`) would not survive. Residual after 2.40: franchise license still keys off whatever WACC the (now cleaner) buildup prints. That is correct **if** Kd/weights are market claims. It is still a false friend if `rf_plus_spread` 0 bp + trough `wd` survive.

---

## 2. Wrong prompt

What in current Agent 5 / Agent 13 / `RESEARCH_AGENTS.md` would cause Sep 7 again, or a new failure if draft text is pasted carelessly.

### 2.1 Would cause CMCSA-again (already on disk)

1. **`wacc_vs_buildup` as a quality badge.** Agent 5 step 4e requires the four dials; omit is FAIL (`agent_prompts.md`; `RESEARCH_AGENTS.md` §10c.8; `valuation_hygiene.py` `DIAL_KEYS`). Sep 7 wrote `dial: matches_buildup`, `applies_in: none`, rationale “No silent WACC pad above buildup.” That is exactly what the dial was built to catch (silent *high* WACC). The prompt never says the buildup’s **Kd must be a market claim**. Agent 5 treated matching a coupon formula as conservatism-complete.
2. **“Do not pad; match the buildup.”** After July 25’s +345 bp company premium, that teaching is load-bearing *against silent Ke padding*. It is also the instruction that produced 6.14%. Draft text “Keep `wacc_vs_buildup: matches_buildup`” is right **only if** the next sentence is: idiosyncratic risk is a **named Ke sleeve** (ops / size / governance) with use/reject — not a substitute for market Kd and going-concern weights.
3. **“CoC/governance dials (may be 0)”** + **“NEVER paste region-module ranges as mandated WACC/ERP/family discounts”** (`agent_prompts.md` step 2; `RESEARCH_AGENTS.md` §5b line 122; `harness/modules/region_us.md` “no mandated WACC”). Sep 7 set dual-class = 0 *because the law told it not to paste a family discount*, then let `wd=49%` at 4% coupon do the work. Careless 2.40 text that repeats “may be 0” without the trough-weight tripwire recreates the incident.
4. **ROIC franchise on in-model WACC.** Agent 5 step 2b and Agent 13 `4-roic` grade NOPAT/IC vs the DCF stack and forbid `franchise_mos` on below/approx. They **do not** grade Kd vs Rf. Schema-valid `above_wacc` + `franchise_mos` was the Sep 7 cheapness story. Agent 13 would not have a Band-3 major on coupon Kd under current `4-roic`.
5. **Pair 1 GOOD in `harness/exemplars/rationale_quality.md`.** The GOOD WACC rationale is a blended CoE plus “after-tax cost of debt 3.8% at 12% debt weight” and then “Slightly above peer median ~9.0% to reflect higher capex/execution risk.” That last clause is the **pad-above-buildup** the conservatism dial exists to catch. After-tax 3.8% vs Rf 4.2% in the exemplar is at least not coupon-below-Rf, but the exemplar never names YTM vs coupon. Agent 5 copying Pair 1 will either pad WACC (dial FAIL) or drop the pad and keep a vague “cost of debt 3.8%” (CMCSA-shaped).
6. **Agent 5 self-check list** (output contract items 1–11) has ERP competitor, four dials, ROIC identity, mid-cycle window. **No Kd source, no Kd vs Rf, no weight policy.** The self-check is where Sep 7 thought it was done.
7. **Footnotes for “debt/leases”** (step 2) are a disclosure ask, not an identity. Sep 7 footnoted coupons and still used them as Kd.

### 2.2 New failures if draft text is added carelessly

- **Contradiction with “no hardcoded WACC.”** Putting “WACC should be ~9%” or “utilities sit near 6%” in Agent 5/13 or a region module recreates the thing §5b forbids. Hatch names (`negative_rate_market`, `current_yield_verified`) are the legal form. Do not paste a rate table.
- **Contradiction with `wacc_vs_buildup`.** If Agent 5 is told both “match the buildup, `applies_in=none`” and “raise WACC when the tape implies 9%,” the pad returns through the back door. Implied gap is a **rationale obligation**, not a second WACC.
- **Dual-class = 0 vs bear vs SOTP.** Prompt already allows governance via range/probs (`assumptions.dual_class_governance_premium` rationale). If 2.40 *requires* a Ke sleeve > 0 on dual-class, it double-counts names that already spent it in bear/SOTP. If it *requires* 0, trough `wd` remains the hidden lever. Forensic ask: **declare the spending location** (Ke sleeve | bear/range | SOTP haircut | rejected) — one place, not three, not none-while-`wd` crushes.
- **`applies:false` copy-paste from ROIC.** Banks/insurance/REITs already skip industrial IC (`RESEARCH_AGENTS.md` §10d.5; Agent 13 “Do not fail banks for missing industrial IC”). If the WACC-buildup `applies:false` reason is the same 40-char bank sentence on a **cable FCFF DCF**, Agent 5 will hatch out of the gate. Tie `applies` to model family (FCFF/WACC DCF → true), not to sector vibes.
- **Agent 13 Band 3 without a WACC-ingredient line.** Adding law in §13 tables but not a `4-wacc` check next to `4-roic` means the auditor still PASSes coupon Kd as “scripted intermediates present.”
- **Blume mandated in the prompt.** Not the bug. Mandating it would move WACC on high-beta names *down* toward 1 and look like a rate paste.

---

## 3. Bad harness

How the gate itself becomes harmful.

### 3.1 False FAIL (protect these hatches; do not overfit CMCSA)

| Case | Why a naive gate hurts | v1 treatment |
|---|---|---|
| **Banks / insurance / REITs** | Not WACC-native. ROIC already `applies:false` + `native_analog`. | Same hatch, **≥40 char reason**, model-family test. Do not FAIL a bank for missing `kd_pretax`. |
| **Japan / negative-rate market** | Local Rf can sit above some JGBs’ YTM, or Kd < local Rf in a genuine quoted market. | `kd_below_rf_gate=negative_rate_market` **with local Rf evidence in-session**. US `^TNX` is not that evidence. |
| **Utilities** | May sit close to Rf; coupons on old 30-year notes often **are** below today’s Rf. | Coupon-as-Kd should still FAIL. Current utility YTM ≥ Rf should PASS even if WACC is “low.” Do **not** FAIL `wacc − rf` small. FAIL `wacc ≤ rf` without hatch (draft’s spirit). |
| **Net-cash tech** | Tiny `wd`; dummy `kd_pretax=0` would trip Kd < Rf even though debt is not in the WACC. | If `wd` < 5 bp, **SKIP** Kd-vs-Rf (or WARN), still require `kd_source` if `wd>0`. Do not force a 4% Kd onto a cash pile. |
| **Healthy IG, cheap on volume** | `wd>0.35` is ordinary for cable, telco, staples. Implied gap > 200 bp fires whenever the tape is cheap on the base path — circular with a bullish FCFF. | Tripwire must not auto-rewrite `wd` to a harness number. It forbids **`current_market` alone**. Agent 5 still judges target. Implied-gap FAIL #5 stays a rationale duty, not a WACC rewrite. |
| **Equity slightly above book** | CMCSA $94.0B cap vs $89.8B book. “At/below book” false-misses the incident. | Keep the **OR implied-gap > 200 bp** prong. Do not require book breach. |

### 3.2 Easy to game (forensic)

1. `kd_source=rf_plus_spread`, spread = 0, rationale “IG name.”
2. `kd_source=current_yield`, YTM = coupon, hatch `current_yield_verified`.
3. `weight_policy=target` with `wd` ≈ trough current.
4. `tax` on Kd higher than DCF cash-tax.
5. `applies:false` on an FCFF DCF.
6. `wacc_gap_rationale` that says “not only franchise MoS” and then is only franchise MoS with a Kd clause appended.
7. Blume toward 1 on a 0.3 beta **as theater** while Kd/weights stay coupon/trough (looks conservative on Ke, still 6% WACC).
8. Shared calculator that pastes `rf=0.0478`, `erp=0.05`, `kd=rf` into every USD session — a hardcoded regional WACC by another name. **Checker yes; calculator no.** Pattern is `roic_identity.py`: rehydrate, never write g or FV. Same here: never write Kd.

### 3.3 Overfit to CMCSA

- `wd > 0.35` is a cable-shaped constant. A 36% levered industrial that is cheap on destock will trip; a 34% levered cable at trough equity will not. Prefer **identity language**: going-concern DCF may not take **only** spot market-cap weights when spot equity is distressed relative to the same DCF (implied WACC gap or equity ≤ book). Keep 0.35 as a machine constant if you must, but disclose it as a tripwire not a target structure.
- Do not encode “CMCSA should have been 9%.” July 25’s 9% was a pad. The forensic object is: **Kd is a market yield; weights are going-concern; TV refinances at that Kd.**

### 3.4 Shared calculator / rate paste

Agent 5 **must** keep writing a new `S/data/compute/valuation.py` (`RESEARCH_AGENTS.md` valuation single-writer; assignment: no shared WACC calculator). A `packages/kd_research/wacc.py` that returns 6.5% would become the new coupon. Shared **checker** (`wacc_buildup.py` analog to `roic_identity.py`) is the existing pattern and is the right one.

---

## 4. Load-bearing change (ranked)

Rank: **(A)** would have caught CMCSA Sep 7, **(B)** false-FAIL risk on a healthy session.

### v1 — ship these

| Rank | Change | A. Catch Sep 7? | B. False-FAIL risk | Persona note |
|---|---|---|---|---|
| **R1 REQUIRE** | `kd_source` ∈ {`current_yield`, `rf_plus_spread`} only. `coupon` illegal as the WACC input. Coupon may be disclosed as a cross-check. | **Yes.** Line 186 is the incident. | Low if banks/REITs `applies:false`. | This is the cash-vs-accrual gate. |
| **R2 REQUIRE** | `kd_pretax >= rf` unless `kd_below_rf_gate` is `negative_rate_market` (local Rf in-session) or `current_yield_verified` (**quoted YTM / bond price in-session**, not the coupon table). | **Yes.** 4.0% < 4.784%. | Japan needs the hatch. Net-cash `wd≈0`: SKIP this comparison. Utilities with quoted YTM ≥ Rf PASS. | Do not hatch “effective coupon from Note 6.” |
| **R3 REQUIRE** | Distressed-equity tripwire: going-concern FCFF DCF may not use **only** `weight_policy=current_market` when `wd > 0.35` **and** (implied WACC gap > 200 bp **or** equity ≤ book). Then `target` or `blended` with rationale. | **Yes, and this is the WACC-level catch.** Kd≥Rf alone → ~6.4%. Tape gap 299 bp + `wd=49%` fires. Book prong would **miss** ($94B vs $89.8B). | Medium: ordinary 36% leverage + cheap tape. Mitigate: do not paste a target `wd`; forbid current-only; WARN if `|wd_used − wd_spot| < 200 bp` after trip. | Trough equity must not capitalize 2015 coupons as half the capital stack. |
| **R4 REQUIRE** | Arithmetic: `wacc = we×ke + wd×kd_aftertax` within 5 bp; equals `assumptions.wacc` and `roic_identity.wacc`. `we+wd≈1`. | **No** (Sep 7 already matched). | Very low. | Hygiene, copy `WACC_EPS = 0.0005` from `roic_identity.py`. Without R1–R3 this is theater. |
| **R5 REQUIRE** | Implied gap: if reverse-engineered WACC > 200 bp above model, `wacc_gap_rationale` ≥40 chars that is **not only** “tape is cheap / franchise MoS.” WARN if it does not rehydrate Kd source **and** weight policy. Do not FAIL the tape. | **Partial.** Sep 7’s reverse-eng rationale *is* “tape is cheap… distress/share-shift pricing” (`valuation_model.json` `reverse_engineering.rationale`). Would FAIL/WARN the franchise-only story. Would not by itself raise WACC. | Low if it stays WARN/rationale. High if someone inverts implied WACC into the model. | Franchise MoS cannot be the entire bridge from 6.14% to 9.13%. |
| **R6 ADD (cheap, high catch)** | If `debt_fair_value` (or a bond price) is **in-session**, `kd_source=coupon` is still illegal, and `current_yield` must be reconcilable to that FV vs carrying (direction: FV < carrying ⇒ YTM > coupon). Unused FV is WARN on new runtime. | **Yes.** $79.7B FV vs $90.4B carrying was sitting in LQ. | Low: only fires when the session already extracted FV. | This is the forensic-specific bolt the draft is missing. |
| **R7 ADD** | `kd_spread` required when `kd_source=rf_plus_spread`. Spread = 0 needs a ≥40 char rationale (IG current YTM ≈ Rf is legal; “forgot the spread” is not). | Would have forced a decided spread; 0 bp still possible with an essay. | Low. | Blocks the 0 bp game without mandating a spread number. |
| **R8 ADD** | Agent 5 self-check + Agent 13 new `4-wacc` next to `4-roic`: grade Kd vs Rf, Kd source, weight policy, unused debt FV. Keep `wacc_vs_buildup: matches_buildup`. | Yes as process. | Low. | Without this, 13 PASSes coupon Kd as scripted. |
| **R9 ADD** | Prompt surgery, not a number: (i) matching buildup is not a quality badge until Kd is a market claim; (ii) dual-class/gov sleeve “may be 0” **only if** the spending location is named and trough `wd` is not the hidden Ke; (iii) Pair 1 GOOD exemplar must stop teaching pad-above-peer-median as the GOOD WACC. | Prevents recurrence. | Low if no rate table. | Careless paste of “may be 0” without R3 recreates Sep 7. |
| **R10 KEEP as-is** | `applies:false` ≥40 char for banks/insurance/REITs/other non-WACC natives. No hardcoded WACC/ERP. No shared calculator. Legacy SKIPPED. | n/a | These *prevent* false FAILs. | Do not contradict §5b. |

### v1 — drop / do not ship

| Drop | Why |
|---|---|
| Mandated `beta_policy=blume` | Not the incident. Blume *raised* Ke. Mandating it is a rate-shaped rule. |
| Shared `wacc.py` calculator | Rate paste. Checker only. |
| Any pasted WACC / “use 9%” / utility band | Contradicts §5b and `region_us.md`. |
| FAIL the tape for implied-gap | Draft already says do not. Keep that. |
| `equity ≤ book` as a **necessary** tripwire | Would have **missed** Sep 7. Keep as OR, not AND with the gap. |
| Forcing a Ke dual-class premium > 0 | Double-count vs bear/SOTP; the crush was Kd/weights. |

### Wave 2 — later (real holes, not v1 blockers)

| Later | Why wait |
|---|---|
| `debt_measure` + `cash_in_weights` enums with net-vs-gross identity | Sep 7’s gross-vs-net was second-order vs coupon. Needed to stop the next double-count. |
| Lease-in-WACC identity (`opex_and_out_of_ic` ⇒ lease not in `wd`; `capitalized_both` ⇒ lease in `wd` + lease Kd) | ROIC already covers mix. WACC slot is the residual. |
| Preferred / NCI weight slot | Immaterial on this incident. |
| Tax-shield identity: Kd tax rate vs DCF cash-tax; WARN if Kd uses a higher t | Real earnability issue; needs a careful bank/loss hatch. |
| Terminal refinancing sentence in `terminal_consistency` (Kd_tv = Kd_wacc unless a named runoff hatch) | Forensic TV test; don’t block 2.40 on it. |
| Forbid mixing `current_market` weights with relever-to-target beta | Beta/weight identity; smaller than R3. |
| Tight `|target_wd − spot_wd|` FAIL (vs WARN) | Overfit risk; WARN first, promote if gamed. |

---

## Three tests, applied to the incident (not a rewrite)

1. **Does Kd match a market claim or an accounting leftover?** Leftover. Coupon buckets 3.3–4.2% vs Rf 4.784%. Debt FV $79.7B vs carrying $90.4B was the unused market claim.
2. **Is a financing cost missing or spent twice?** Cheap coupon Kd spent at **49%** current-market weight (gross carrying, not FV, not net). Dual-class Ke = 0 while bear 0.34 + SOTP 10% haircut spent governance. Operating leases $6.1B consistently out of IC/`wd` (not double-counted). Cash cut from EV but not from weights — raised `wd` on a 3.08% after-tax Kd.
3. **Does TV still discount a firm that must refinance at today’s rates?** No. Gordon at 6.145% − 2% = 4.14% with ~70% of EV in TV is a perpetual 2015 coupon book. Tape-implied 9.13% is what refinancing-at-today looks like on the same FCFF path.

When a session prints WACC below Rf-like levels, inspect the Kd/weight identity before the franchise footnote. Sep 7’s `franchise_mos` rationale is the footnote. The identity is lines 177–189 of `valuation.py` plus unused `debt_fair_value`.

---

## Bottom line for 2.40

Ship **R1 + R2 + R3 + R4 + R5** as the machine, **R6–R9** as the forensic tightenings that make R1–R3 hard to game, and keep the no-hardcoded-WACC / no-shared-calculator / `applies:false` hatches. Arithmetic without R1–R3 would have stamped `PASS` on 6.145%. Kd≥Rf without R3 would have stamped `PASS` on ~6.4%. That is not a cost-of-capital identity; it is a coupon remainder.

Do not rewrite `archive/research/CMCSA/2026-09-07`.
