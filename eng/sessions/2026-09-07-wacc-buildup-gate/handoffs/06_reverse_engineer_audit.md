# Reverse-engineer audit — WACC-buildup identity (draft 2.40)

Persona: implied-expectations. Start from the tape, work backward. Do not start from the draft’s narrative.  
Session under review is a **read-only incident**. Do not rewrite `archive/research/CMCSA/2026-09-07`.

---

## Lead answer

**`wacc_gap_rationale` does not change behavior.** It is a 40-character essay on a local sensitivity. CMCSA Sep 7 already wrote a named-dial reverse-eng paragraph that is longer than 40 characters, named WACC and OM, set `priced_for_perfection=false`, and then licensed `franchise_mos` off the same too-low in-model WACC. A WARN that “the rationale ignores Kd/weights” is theater: the agent can mention Kd and weights and still conclude “tape is cheap.” The draft’s implied-gap WARN must not become “the tape is wrong therefore franchise MoS.”

**Kd ≥ Rf does not close most of the ~300 bp gap. Target weights would close a large share of it — only if `wd_target` cannot be the trough `wd`.** Stored ingredients:

| Piece | Stored | File |
|---|---|---|
| Price | $26.49 | `archive/research/CMCSA/2026-09-07/data/compute/valuation_result.json` |
| Model WACC | 6.145% (`0.061448822380334965`) | same `intermediates.wacc`; `data/valuation_model.json` `assumptions.wacc` |
| Ke | 9.092% (`0.09092279762600491`) | `valuation_result.json` intermediates |
| Rf | 4.784% (`^TNX`) | `data/market_inputs_snapshot.json` |
| Kd pretax | 4.0% | `data/compute/valuation.py` `kd_pretax = 0.040` |
| Tax | 23% | same script |
| we / wd | 0.510 / 0.490 | `valuation_result.json` intermediates |
| Tape-implied WACC on **base volume+OM path** | 9.13% (`0.09132440709303408`) | `valuation_result.json` `reverse_engineering.implied.wacc_on_base_path` |
| Mid-cycle ROIC | 10.01% | `valuation_model.json` `roic_identity` |
| Base FV | $59.83 | `valuation_model.json` `fair_value.base` |

Tape-first identity, not a new FV:

- Implied WACC on the already-chosen base path (9.13%) **≈ model Ke (9.09%)**. Gap vs Ke is ~4 bp. The ~299 bp gap vs model WACC is almost entirely the levered mix: `wd≈0.49` at after-tax Kd `4.0%×(1−0.23)=3.08%`.
- **Kd pretax 4.0% vs Rf 4.784%** is a real FAIL (coupon below the local risk-free). Replacing Kd with Rf moves after-tax Kd to `4.784%×0.77≈3.68%` and model WACC only to **~6.44%**. That is ~30 bp of the 299 bp. Hygiene, not the gap.
- **Weights are the load-bearing term.** Current-market `wd=0.49` on a depressed residual claim is how a 9.09% Ke becomes a 6.14% WACC. A going-concern target that actually de-levers (wd well below 0.49) would close most of the gap toward Ke. **`wd_target=0.49` closes none of it.**
- Remaining ways to keep model WACC far below implied after the draft: **ERP 3%**, **beta 0.4 (raw, not Blume)**, **`wd_target` set to the trough `wd`**, **`rf_plus_spread` with 0 bp**. Those four survive every machine FAIL in the draft.

`priced_for_perfection` in this session is already the illegal mechanical flag, just inverted: compute sets PFP true only if implied WACC is **below** model WACC by 150 bp or implied terminal OM is at/above bull. Tape cheaper → PFP false → “distress pricing, not perfection” → ROIC 10.01% vs WACC 6.14% → `franchise_mos`. That loop is circular if model WACC is not a market-consistent hurdle. A reverse-eng that only perturbs WACC/OM on an already-chosen volume path is a **local sensitivity**, not an inversion of the tape’s company.

---

## Tape-first reconstruction (CMCSA 2026-09-07)

Do not start from “the model is CAPM-correct and the tape is cheap.” Start from $26.49.

The compute script inverts **two** dials on the **base volume and OM path** (`archive/research/CMCSA/2026-09-07/data/compute/valuation.py` lines 310–359):

1. Binary-search WACC so base-path equity value equals price → implied WACC **9.13%**.
2. Binary-search terminal OM at **model** WACC 6.14% → implied terminal OM **7.81%** (vs base Y8 OM 17.0% / bull 19.0% in `valuation_model.json` `reverse_engineering.implied.note`).

Then:

```356:359:archive/research/CMCSA/2026-09-07/data/compute/valuation.py
    priced_for_perfection = bool(
        implied["wacc_on_base_path"] < wacc - 0.015
        or implied["terminal_om_on_base_wacc"] >= om_bull[-1] - 0.002
    )
```

That boolean is `price ≷ base` with extra arithmetic. Implied WACC 9.13% is **above** model 6.14%, not 150 bp below, and 7.81% OM is not bull-class, so PFP is false. The written rationale then treats the gap as evidence the tape is cheap (`valuation_model.json` `reverse_engineering.rationale`: “Tape is cheap vs base, not rich… priced_for_perfection=false because price does not need bull-class dials”).

What the tape actually said, identified only up to a path:

- **Either** the unlevered required return on this residual claim is ~9.13% **on the model’s volume path**,
- **or** the volume/OM path that $26.49 is pricing is far worse than base (terminal OM ~7.8% at model WACC),
- **or** some mix. Two dials, one price. Unidentified.

What the model then did with that unidentified gap:

- Kept WACC at the scripted mix 6.14%.
- Set `wacc_vs_buildup` to `matches_buildup`, `applies_in=none` (`valuation_model.json` conservatism_dials).
- Set `roic_identity.quality_bucket=above_wacc` because mid-cycle ROIC 10.01% − 6.14% = 3.87% spread, window `multi_year_avg` 2023–2025.
- Set `cheap_claim.class=franchise_mos` because that spread licenses it under `harness/RESEARCH_AGENTS.md` §10d.4.

The franchise license is an **in-model WACC** hurdle (`RESEARCH_AGENTS.md` §10d.1: “Hurdle is **in-model WACC**, not a 15% Buffett paste”). If the hurdle is 6.14% because coupon debt is 49% of a trough equity value, `above_wacc` is a spreadsheet identity, not a market-consistent franchise.

July 25 contrast (`archive/research/CMCSA/2026-07-25/data/valuation_model.json` `assumptions.wacc`): raw CAPM ~5.55%, then **+345 bp** company premium to 9.0%. That pad was economically closer to this tape’s implied 9.13% than Sep 7’s “honest” 6.14%. Later law taught “do not pad; match the buildup.” Sep 7 obeyed and printed a utility-like WACC. The tape did not move to 6%.

---

## Q1 — Residual analysis error (how Agent 5 still prints an economically wrong WACC)

After the draft, the machine fails **impossible ingredients**, not “WACC must be 9%.” That is the right spirit. These holes remain.

### 1. Implied-gap circularity (the residual that matters)

Draft field `implied_wacc_gap_bp` and FAIL/WARN #5: if reverse-engineered WACC is >200 bp above model, require `wacc_gap_rationale` ≥40 chars that is not only “tape is cheap / franchise MoS.” WARN if the rationale ignores Kd/weights. **Do not FAIL the tape for disagreeing.**

Problems from this persona:

- The implied WACC is computed on the **model’s** volume+OM path (`valuation.py` 310–332). It is not a market-consistent hurdle. It is “what discount rate makes *our* FCFF path hit $26.49.” If that path is optimistic, implied WACC is high even with a correct CoC. Using the gap as a distressed-equity **tripwire** (draft FAIL #3) therefore mixes a path error into a weight policy. That is still better than using the gap as “tape is wrong,” but it is not an inversion of the tape’s company.
- Agent 5 prompt already requires a surface reverse-eng (`harness/agent_prompts.md` step 7 and PFP bullet): invert Street/print Y1, name dials, write `path_inverted`. Sep 7 inverted WACC and terminal OM on **its own** base path, not a separate Street-implied volume path. Schema `reverse_engineering` (`harness/schemas/valuation_model.schema.json` lines 331–338) still only has `implied`, `priced_for_perfection`, `rationale` — `path_inverted` is prompt-only and unenforced.
- A ≥40 char rationale that is “not only tape is cheap” is the same class as current PFP: `packages/kd_research/decision_quality.py` `check_priced_for_perfection` already requires a named dial (needles include `"wacc"`) and rejects only mechanical `price>base` language. Sep 7 **passes** that gate today. The new gap essay will pass the same way.

**Behavior that does not change:** model WACC, PFP boolean, `cheap_claim`, FV. The WARN is paperwork on a local sensitivity.

### 2. Kd vs Rf is real, and small

Draft FAIL #1 (`kd_pretax >= rf` unless hatch) would FAIL Sep 7: coupon 4.0% < Rf 4.784%, source is FDD coupon buckets (`valuation.py` line 186; FDD hook in `valuation_model.json` says “Kd buildup stays ~4% pretax on coupon buckets”). That is a correct identity FAIL. It does not close the gap (see lead arithmetic, ~30 bp).

Residual after the FAIL: **`rf_plus_spread` with 0 bp** sets Kd = Rf = 4.784%, which **passes** Kd≥Rf and **passes** `kd_source` (coupon is illegal; Rf+0 is legal). After-tax Kd ~3.68%, WACC ~6.44% vs implied 9.13%. The 300 bp story survives.

`current_yield_verified` hatch with a quoted YTM is the right hatch. Coupon-below-Rf as Kd is correctly FAIL. Do not let `rf_plus_spread` + 0 bp become coupon-by-another-name.

### 3. Weights: the 300 bp live here; the draft can be gamed

Draft FAIL #3: going-concern DCF may not use **only** `current_market` when `wd > 0.35` **and** (implied WACC gap > 200 bp **or** equity at/below book). Then `target` or `blended`.

Sep 7 trips the first conjunct: `wd=0.490` and gap ~299 bp. Book does **not** trip: LQ `shareholders_equity` $89,763m (`registry/latest_quarter.json`) vs market cap $94,003m — equity slightly **above** book. The OR with implied gap is what fires.

Residuals:

- **`wd_target=0.49`.** `weight_policy=target` with target equal to current trough weights satisfies the letter. Gap unchanged.
- **`blended` as 99% current / 1% target.** Same.
- **Gross vs net.** Weights use **gross** carrying debt (`valuation.py` `d_mkt = total_debt`) against market equity. Cash is subtracted only later as net debt from EV. Gross debt inflates `wd` and **lowers** WACC whenever Kd < Ke. Draft does not mention gross vs net.
- **Leases.** `roic_identity.leases=opex_and_out_of_ic`. Capitalizing operating leases would raise `wd` and lower WACC further — the cheap-WACC direction. Sep 7 did not take it. Still unenforced for WACC weights.
- **Preferred / hybrids.** No field. A name with preferred can hide a cheap Kd sleeve or omit a Ke-like claim.
- **Cash-rich / net-cash.** Tiny `wd` is correctly allowed by the draft hatch note. Inverse residual: net-cash tech can still print a low WACC via low beta / low ERP with `wd≈0`. That is a Ke problem, not a weight problem.

### 4. Ke ingredients the draft does not touch (Agent 5 still judges)

Current law: **no mandated ERP** (`agent_prompts.md` ERP/CoC bullet; `valuation_decision_quality.md` Pair 4: “Value still free judgment”). **No hardcoded regional WACC / ERP / family-control discounts** (`RESEARCH_AGENTS.md` §5 line 122; `region_us.md` lines 5–6, 14–19; `region_integration.md` rejects hardcoded Rf/CRP/family tables). Dual-class premium **may be 0** (`agent_prompts.md` step 2: “CoC/governance dials (may be 0)”).

Sep 7 used that law:

- ERP 5.0% historical US; **rejected market-implied ERP** as “too thin” (`assumptions.erp`). Reverse-eng note: they rejected the tape’s ERP and then used the tape’s cheapness as franchise MoS.
- Beta: raw 0.719 → Blume 0.812. Blume **raised** Ke. The cheap WACC was not Blume.
- Dual-class premium **0** because `region_us.md` forbids pasting a family-control module discount into Ke; risk moved to bear 0.34 / range (`assumptions.dual_class_governance_premium`).
- Structural ops sleeve **+25 bp** (named Ke sleeve — the draft’s “idiosyncratic risk is a named Ke sleeve” is already how Sep 7 avoided a WACC pad). +25 bp on a 49% equity weight is ~13 bp of WACC. Not the gap.

**After 2.40, Agent 5 can still print a too-low WACC by:**

| Game | Why the draft allows it | Direction vs implied 9.13% |
|---|---|---|
| ERP 3% | “No mandated ERP value”; Pair 4 GOOD still allows 5% with a rejected competitor | Ke = Rf + 0.812×3% + 25 bp ≈ 7.26%; mixed WACC even lower than 6.14% |
| Beta 0.4 raw | `beta_policy` is judgment; v1 does not mandate Blume or unlever-relever | Ke = 4.784% + 0.4×5% + 25 bp ≈ 7.03% |
| Blume toward 1 on a **0.3** beta | Raises beta (0.67×0.3+0.33=0.53) — this game **raises** WACC, not lowers it | False worry for cheap-WACC; real cheap-beta game is **raw** / Yahoo 0.662 as sole input |
| `wd_target=0.49` | Target is judged; tripwire only forbids `current_market` **label** | Gap unchanged |
| `rf_plus_spread` 0 bp | Legal `kd_source`; Kd = Rf passes Kd≥Rf | ~30 bp fix, ~270 bp remain |
| Keep implied inversion on base path only | Draft stores `implied_wacc_gap_bp`; does not require a volume-path invert | Local sensitivity remains |

**Too-high WACC residual** (the other side): Agent 5 can still pick ERP 8%, beta 1.4, or a fat named Ke sleeve. `wacc_vs_buildup: matches_buildup` will PASS because the pad is inside Ke, not after the mix. Draft says idiosyncratic risk is a named Ke sleeve with use/reject — that is disclosure, not a cap. Reverse-eng does **not** want a numeric Ke floor/ceiling in the prompt (that is a hardcoded WACC). The check is: if implied WACC on the Street path is **below** model WACC by 200 bp, that is the PFP surface, not a machine FAIL on the tape.

### 5. ROIC franchise license remains coupled to the cheap hurdle

`packages/kd_research/roic_identity.py` matches `roic_identity.wacc` to `assumptions.wacc` within 5 bp and forbids `franchise_mos` on below/approx buckets. It never asks whether that WACC is economically a hurdle. Draft FAIL #4 (arithmetic match) copies this pattern. Sep 7 would still be `above_wacc` at WACC 6.14% vs ROIC 10.01%. Even at implied 9.13%, spread is ~88 bp > 50 bp bucket — `above_wacc` / `franchise_mos` can still license. The **false franchise** is not only the bucket; it is capitalizing that spread at 6.14% into FV $59.83 vs $26.49 (MoS 55.7%). g=0 counterfactual is still $40.20 (`terminal_consistency.g0_counterfactual_ps`) — above the tape, so “even g=0 clears price” is another circular comfort while WACC is 6.14%.

---

## Q2 — Wrong prompt (what would cause CMCSA again, or a new failure)

### Already-written law that produced Sep 7

1. **`wacc_vs_buildup` exists to catch padding above buildup, not a too-low mix.**  
   `RESEARCH_AGENTS.md` §10c.8 and `valuation_hygiene.py` `DIAL_KEYS`: the four keys must exist; `applies_in` is `base | bear_only | none`. Sep 7 wrote `matches_buildup` / `none` with a true sentence: “No silent WACC pad above buildup.” That is what the dial was built to catch (`00_assignment.md`: “padding WACC above buildup as silent conservatism”). July 25’s +345 bp would have been `applies_in=base`. The prompt taught the wrong lesson: **honesty about the mix is not market-consistency of the mix.**

2. **“Do not paste module WACC / no hardcoded WACC”** (`agent_prompts.md` Y1 LAW, step 2, step 4b; `RESEARCH_AGENTS.md` §1.1 and §5). If 2.40 prompt text says “do not print a utility-like 6%” or “cable WACC should be ~9%,” that **is** a hardcoded WACC and contradicts §1. The draft correctly says do not paste a WACC number. Keep that. The failure mode is the opposite: Agent 5 reads “match the buildup” + “governance dial may be 0” + “no country add-on” and produces 6.14% again.

3. **Dual-class = 0.** `region_us.md` lines 19, 27–29: dual-class is a governance dial, not an automatic country premium. `agent_prompts.md` step 2: CoC/governance dials may be 0. Sep 7 followed this exactly. Reverse-eng does not want a mandated family-control % (that is the rejected table in `region_integration.md`). The hole is using “dial = 0” as permission to ignore that the residual claim is a controlled, levered equity whose tape-implied unlevered return is 9.13%. Put control risk in Ke **or** in the path **or** in weights; do not put it nowhere and then call the tape irrational.

4. **ROIC franchise license.** `agent_prompts.md` 2b: `cheap_claim=franchise_mos` only when bucket is `above_wacc`. Agent 13 `4-roic`: franchise on below/approx is major. Neither side asks “above *which* WACC.” Prompt carelessness: adding “if implied WACC >> model, the tape is cheap so franchise MoS is allowed” would **encode the CMCSA error**. Adding “if implied WACC >> model, FAIL the session until WACC equals implied” would **destroy independent valuation** (match the tape). Neither.

5. **PFP law is one-sided.**  
   - Prompt: “never from PW vs price×k or price>base alone” (`agent_prompts.md` PFP bullet).  
   - Exemplar Pair 2 GOOD (`valuation_decision_quality.md`): PFP **true** because price needs bull OM or WACC ~200 bp **below** base.  
   - Agent 13 item 9: FAIL if boolean is threshold-only in compute **without surface rationale**.  
   - Machine: `decision_quality.py` `PFP_MECHANICAL` is only price>base / price>PW / inside-the-grid.  

   Sep 7 has a surface rationale and named dials, so Agent 13 and the machine **PASS**. The compute threshold is the **inverse** of Pair 2: PFP false because implied WACC is **above** model. That inverse is not in `PFP_MECHANICAL`. If 2.40 prompt text copies Pair 2 GOOD as “PFP false when implied WACC is above model,” you have just legalized CMCSA.

6. **Agent 13 will not save you.** Band 3 item 9 grades PFP style, not whether implied WACC is a hurdle. `4-roic` grades NOPAT/IC vs in-model WACC. Conservatism-dial omit is a machine FAIL; `matches_buildup` with a true formula is a PASS. Without a new reverse-eng band (“implied WACC ≈ Ke while WACC << Ke is a leverage/Kd finding, not a cheap-tape finding”), Agent 13 will rubber-stamp the essay.

7. **`rationale_quality.md` Pair 1 GOOD** shows a WACC “slightly above peer median ~9.0% to reflect higher capex/execution risk.” That is the July 25 pad pattern. It is still the taught GOOD example. Agent 5 on Sep 7 followed the **newer** `wacc_vs_buildup` law instead. If 2.40 adds “match the buildup” into Agent 5 without retiring Pair 1’s “above peer median” as a **named Ke sleeve** (not a post-mix pad), you get contradiction: old GOOD = pad; new FAIL = pad; CMCSA-style mix = PASS.

### New failures if draft text is pasted carelessly

- **Banks / insurance / REITs:** `roic_identity.applies:false` already exists (`RESEARCH_AGENTS.md` §10d.5). Draft `wacc_buildup.applies:false` with ≥40 char reason is the parallel. If Agent 5 prompt says “always write wacc_buildup ingredients” without the hatch, banks get a fake industrial WACC. Agent 13 already says do not fail banks for missing industrial IC — keep that join.
- **“Do not FAIL the tape” + ROIC franchise:** Agent 5 will read both as “keep 6% and write 40 characters.” That is Sep 7.
- **Distressed-equity tripwire using implied gap:** if the prompt says “when implied WACC is 200 bp above model, switch to target weights,” Agent 5 can still set target = current. If the prompt says “raise WACC toward implied,” that is matching the tape. The prompt must say: **current-market weights are illegal as the sole policy when the tripwire fires; target weights are a going-concern policy whose `wd` is not the trough print; the implied gap is a check, not a setpoint.**

---

## Q3 — Bad harness (how the gate itself harms)

### False FAIL

| Case | Risk | Draft mitigation | Residual |
|---|---|---|---|
| Banks / insurance / REITs | FCFF/WACC identity on a non-WACC native | `applies:false` ≥40 chars | Prompt must not require Kd/Rf on deposit/float cost |
| Japan-style Kd < Rf | Local YTM below local Rf | `kd_below_rf_gate=negative_rate_market` | Hatch must require **local** Rf evidence, not US 10Y |
| `current_yield_verified` | Quoted YTM can be below Rf in a negative-rate or super-AAA sleeve | Hatch with in-session quote | Do not accept coupon as the quote |
| Utilities | WACC close to Rf is economically possible | Draft note: still WACC > Rf | Kd≥Rf + small wd can sit close; do not FAIL “WACC too close to Rf” as a number |
| Net-cash tech | Tiny `wd` | Allowed | Do not force target wd 0.25 on net cash |
| Healthy `wd>0.35` going-concern | Many levered IG names run wd > 0.35 without distress | Tripwire needs **and** (gap>200 bp **or** E≤book) | A levered IG with a conservative (high) model WACC will **not** have implied WACC 200 bp **above** model; tripwire silent. Good. |
| Implied gap from an optimistic path | Tripwire fires because volume path is rich, not because weights are distressed | Unmitigated | This is the circularity; do not FAIL weights solely on a path-local implied WACC |

Overfitting to CMCSA: `wd>0.35` and `gap>200bp` are CMCSA-shaped. A name with `wd=0.34` and coupon Kd below Rf would **fail Kd≥Rf** (good) but **skip the weight tripwire** (gap remains if Ke mix still has a lot of debt just below the cutoff). 0.35 is a knife-edge. Prefer: tripwire if `wd × (ke − kd_aftertax) > 200 bp` of WACC, which is the actual mix contribution (Sep 7: `0.49 × (9.09−3.08) ≈ 294 bp` — the whole gap). That is an identity on stored ingredients, not a CMCSA constant.

### Easy to game (draft as written)

1. `kd_source=rf_plus_spread`, spread = 0 bp.  
2. `weight_policy=target`, `wd_target=wd_current=0.49`.  
3. ERP 3% with Pair 4 theater (choose historical, reject implied — Sep 7 already did this at 5%).  
4. `beta_policy=raw`, beta 0.4 / Yahoo 0.662 sole input. Blume-toward-1 on a low beta is the **opposite** game.  
5. Reverse-eng only WACC and terminal OM on base volume; write 40 characters that mention Kd and weights; keep `franchise_mos`.  
6. `applies:false` with a 40-char reason on an industrial FCFF DCF (“WACC identity noisy this year”). Must FAIL `applies:false` unless native analog is bank/insurance/REIT/pre-profit (same list as ROIC).

### Shared calculator

`RESEARCH_AGENTS.md` §1.3: Agent 5 writes a new `S/data/compute/valuation.py` every session. Shared **checker** is the existing pattern (`roic_identity.py`). A shared WACC **calculator** that pastes Rf/ERP/beta would violate “LLM judges, code fetches” and “no hardcoded formulas.” Reverse-eng agrees: **checker only**. The checker rehydrates `we×Ke + wd×Kd(1−t)`, Kd vs Rf, source enum, weight policy vs tripwire. It does not emit 9%.

---

## Q4 — Load-bearing change for 2.40 (ranked)

Rank is: **would it have caught Sep 7’s cheap-hurdle loop**, and **does it false-FAIL a healthy session**. Catching coupon-below-Rf is necessary and not sufficient.

### Ship in v1 (require)

**R1 — Kd source ≠ coupon, and Kd pretax ≥ Rf unless a named hatch.**  
Caught Sep 7 coupon 4.0% < Rf 4.784%. False-FAIL only Japan / verified YTM, which the hatch already names. **Do not treat this as the 300 bp fix.** Add: `rf_plus_spread` with **0 bp is illegal** unless a second hatch (`gov_backed` / `negative_rate_market`) with in-session evidence. Otherwise game (1) survives.

**R2 — Distressed-equity weight identity, with a non-trough target.**  
Caught Sep 7 `wd=0.49` on trough equity. **This is the 300 bp term.** v1 must not stop at “`weight_policy` may not be only `current_market`.” Require:

- `we_target`, `wd_target` as decided `{value, rationale, basis}` whose basis is **not** “current market cap / current gross debt.”
- When the tripwire fires, `|wd_target − wd_current|` below a small epsilon (e.g. 200 bp of weight) is FAIL unless a named hatch explains why going-concern target **equals** the trough print.
- `blended` must disclose the blend weights; a 99/1 blend FAILs the same epsilon.

Without the epsilon, `wd_target=0.49` keeps model WACC at 6.14%. **Do not paste a target wd number into the prompt** (no “use 20% debt”). Agent 5 still judges the target; the machine only forbids disguising current as target.

**R3 — PFP / implied-gap may not license franchise MoS.**  
Caught Sep 7’s loop. Machine:

- FAIL if compute sets `priced_for_perfection` from `implied_wacc < model_wacc` (or the inverse) without a surface path argument — extend `PFP_MECHANICAL` in `decision_quality.py` analogously, but the **identity** belongs in `wacc_buildup`.
- **WARN** (not FAIL the tape) when `implied_wacc_gap_bp > 200` **and** `cheap_claim=franchise_mos`. Rationale that is only “tape is cheap / PFP false / distress pricing” FAILs this WARN’s sibling: it is not a legal `wacc_gap_rationale`. Mentioning Kd/weights is **not** enough if the conclusion is still franchise MoS off the cheap mix.
- Stronger v1 join (recommended): `franchise_mos` illegal while `weight_policy=current_market` **and** the distressed tripwire fired. That would have blocked Sep 7’s cheap_claim without forcing WACC = 9.13%.

**R4 — Ke-vs-implied identity (the reverse-eng tell).**  
When `|implied_wacc − ke| < 50 bp` and `|implied_wacc − wacc| > 200 bp`, the gap **is the debt mix**, not “the tape is irrational vs CAPM.” Sep 7: implied 9.13% vs Ke 9.09% vs WACC 6.14%. Machine WARN, require the gap rationale to say that in those words. This is the one rationale check that is not theater, because it is a numeric identity on stored fields.

**R5 — Keep `wacc_vs_buildup: matches_buildup`. Named Ke sleeve, not a post-mix pad.**  
Do not revive July 25 silent +345 bp. Idiosyncratic risk stays a named Ke sleeve with use/reject. Arithmetic FAIL #4 (5 bp) as in `roic_identity.py`.

### Drop or demote in v1

**D1 — `wacc_gap_rationale` ≥40 chars as the implied-gap control.**  
Would **not** have changed Sep 7. They already wrote more than 40 characters naming WACC and OM. Keep the field as disclosure; do not ship it as the load-bearing gate. If kept, it is subordinate to R3/R4.

**D2 — Mandating Blume or unlever-relever in v1.**  
Sep 7’s Blume **raised** beta. Forcing Blume toward 1 on a 0.3 beta would **raise** WACC on low-beta names (possible false tightness, not the CMCSA bug). Leave `beta_policy` as judged disclosure in v1.

**D3 — Shared WACC calculator / pasted rates / ERP floors.**  
Hardcoded WACC by another name. Violates `RESEARCH_AGENTS.md` §1.1 and `region_integration.md`. Checker only.

**D4 — FAIL the tape for disagreeing.**  
Draft already refuses this. Keep the refusal. Reverse-eng inverts; it does not replace the model with the implied WACC. Matching implied 9.13% as the required hurdle is July 25’s pad with extra steps.

### Add in v1 (small)

**A1 — Gross vs net disclosure on weights.** Sep 7 used gross debt vs market equity, which maximized `wd`. Require `debt_for_weights: gross | net` as a labeled field. Do not mandate one; FAIL silent gross-as-market.

**A2 — `applies:false` allowlist** = same natives as ROIC (`banking`, `insurance`, `reit`, pre-profit). Industrial FCFF with `applies:false` is FAIL.

**A3 — Reverse-eng must invert at least one **volume** dial at model WACC, not only WACC/OM on the base path.** Prompt already says “full grid not only extremes” and `path_inverted`. Schema should store it. Sep 7’s 7.81% terminal OM **is** a volume/profitability invert; the bug was treating the complementary 9.13% WACC invert as “tape is cheap.” The add is: `implied.note` must not conclude PFP false / franchise MoS from the WACC invert alone.

### Later wave (not v1)

- Unlever-relever at **target** weights (draft `beta_policy=unlever_relever_target`). Would have moved Sep 7 beta, second-order vs the 49% wd term.
- Leases in the WACC stack when `capitalized_both`; preferred / hybrids.
- Mix-contribution identity `wd × (ke − kd_aftertax)` as the tripwire instead of `wd>0.35` (less CMCSA-overfit; can wait if R2 epsilon ships).
- Agent 13 band that grades R4 (implied ≈ Ke) as a major if missing. v1 machine WARN is enough.

---

## Shippable v1 vs later

**v1 checker** (copy `roic_identity.py` spirit, no WACC math in a shared engine): `wacc_buildup` object on FCFF/WACC DCFs; arithmetic 5 bp; Kd source enum; Kd≥Rf unless hatch; 0 bp spread illegal without hatch; weight policy vs tripwire **plus** non-trough target epsilon; `applies:false` allowlist; implied−Ke vs implied−WACC WARN; franchise_mos illegal on current-market weights once the tripwire fired; PFP not set from implied-WACC sign.

**v1 prompt edits:** Agent 5 — coupon is not Kd; current-market weights are not a going-concern policy when equity is the residual that just implied a 9% unlevered return on your own path; PFP false is not a franchise license; named Ke sleeve ≠ post-mix pad; do not paste a WACC number. Agent 13 — grade R4 and the franchise join; do not PASS named-dial PFP that is compute-threshold inverted. `valuation_decision_quality.md` Pair 2 — add a BAD that is CMCSA-shaped (implied WACC 300 bp **above** model → PFP false → franchise MoS). Pair 1 GOOD — re-label “above peer median” as a **named Ke sleeve**, not a WACC pad.

**Not v1:** ERP/beta numeric floors, shared calculator, forcing WACC toward implied, rewriting CMCSA 2026-09-07.

---

## Direct answers to the assignment’s reverse-eng tests

1. **Does requiring `wacc_gap_rationale` actually change behavior?** No. Sep 7 already has a long named-dial rationale. The cheap-hurdle loop lives in weights, coupon Kd, PFP inverse, and ROIC’s in-model hurdle — none of which an essay moves.

2. **Would Kd≥Rf and target weights close most of the 300 bp gap?** Kd≥Rf alone: **no** (~30 bp). Target weights that de-lever from `wd=0.49` toward a going-concern mix: **yes, most of the gap**, because implied WACC ≈ Ke already. Target weights that reprint `wd=0.49`: **no**.

3. **Remaining ways to keep model WACC far below implied:** ERP 3%; beta 0.4 raw; `wd_target=0.49`; `rf_plus_spread` with 0 bp. Also: gross-debt weights, `blended` 99/1, `applies:false` theater, and treating the path-local implied WACC as proof the tape is wrong.

4. **`priced_for_perfection` as mechanical price>base (or its inverse) is illegal.** Sep 7 compute lines 356–359 plus `reverse_engineering.rationale` are that inverse. Draft WARN #5 without R3/R4 will not stop it.
