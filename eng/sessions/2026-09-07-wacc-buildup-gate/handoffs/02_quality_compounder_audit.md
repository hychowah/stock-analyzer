# Quality-compounder audit — draft 2.40 `wacc_buildup`

Persona: Fisher–Munger franchise. Conservatism that liquidates a compounding engine is not a virtue. Cheap is not the same as accurate.

Incident is read-only. Do **not** rewrite `archive/research/CMCSA/2026-09-07`.

---

## Lead answer

**Ship the draft identity. The CMCSA failure is a poisoned *hurdle*, not a missing pad.**

Sep 7 printed mid-cycle owner-earnings ROIC 10.01% against in-model WACC 6.145% and licensed `quality_bucket=above_wacc` / `cheap_claim=franchise_mos` (`archive/research/CMCSA/2026-09-07/data/valuation_model.json` `roic_identity`). That is exactly what `harness/RESEARCH_AGENTS.md` §10d tells the machine to do: hurdle is **in-model WACC**, and `franchise_mos` is legal only when the bucket is `above_wacc`. The identity did not misfire. The WACC was not a going-concern cost of capital.

The 6.145% is coupon Kd (4.0% pretax, below session Rf 4.784%) mixed at trough market weights (we 51.0% / wd 49.0% on market cap $94.0B vs gross debt $90.4B) with after-tax Kd 3.08% (`data/compute/valuation.py` lines 149–189; `data/compute/valuation_result.json` `intermediates`). Ke itself was 9.092%. Tape-implied WACC on the base path was 9.13%. Matching the formula was treated as virtue (`conservatism_dials.wacc_vs_buildup` = `matches_buildup`, `applies_in=none`). A 10% ROIC is an average cable engine, not See’s. Against 6% it looks like a franchise. Against ~9% it is a thin spread. The DCF then capitalized that fake spread into base FV $59.83 vs price $26.49.

Draft 2.40 attacks the right objects: **illegal coupon-as-Kd**, **Kd < Rf**, **current-market weights alone when distressed-equity tripwire fires**, **arithmetic identity**, **implied-gap rationale that is not “tape is cheap / franchise MoS.”** Keep `wacc_vs_buildup: matches_buildup`. Named Ke sleeves (ops / size / governance) with use/reject are **part of the buildup**, not a silent add-on after cheap debt.

**Do not** paste a WACC, ERP, or Kd number into prompts. **Do not** mandate Blume-toward-1. **Do not** FAIL `franchise_mos` because the tape implies a higher WACC (that treats cheap as accurate and liquidates a real compounder). **Do not** fire the weight tripwire on `wd > 0.35` alone (levered going-concern franchises are not distress). **Do not** stack Damodaran country paste or family-control bp on cash-flow haircuts already in the path.

The load-bearing v1 is a **checker**, same spirit as `packages/kd_research/roic_identity.py`: fail impossible ingredients; leave Rf, beta, ERP, spread, and target weights as Agent 5 judgment.

---

## What the incident actually shows (read-only)

| Piece | Stored | Path |
|---|---|---|
| Price / base FV | $26.49 / $59.83 | `valuation_result.json`; `valuation_model.json` `column_a.equity_ps` |
| WACC / Ke / Rf | 6.145% / 9.092% / 4.784% (`^TNX`) | `assumptions`; `market_inputs_snapshot.json` |
| Beta | 0.719 raw → 0.812 Blume | snapshot + `valuation.py` |
| ERP | 5.0% historical US; implied ERP rejected | `assumptions.erp` |
| Kd pretax | **4.0%** from FDD coupon buckets 3.3–4.2% | `valuation.py`: `kd_pretax = 0.040` |
| Tax / weights | 23%; we 0.510 / wd 0.490 | `valuation_result.json` intermediates |
| Tape-implied WACC | 9.13% on base path | `reverse_engineering`; result `implied.wacc_on_base_path` |
| ROIC license | mid-cycle 10.01% vs WACC 6.14% → `above_wacc` → `franchise_mos` | `roic_identity` |
| Conservatism dial | `wacc_vs_buildup` matches buildup, `applies_in=none` | `conservatism_dials` |

Kd **4.0% < Rf 4.784%**. That is not a utility sitting close to Treasuries. It is coupon paper used as the going-concern cost of debt.

July 25 contrast (`archive/research/CMCSA/2026-07-25/data/valuation_model.json` `assumptions.wacc`): raw CAPM ~5.55% plus a **+345 bp** company premium to **9.0%**. Later law taught “do not pad; match the buildup.” Sep 7 obeyed. The pendulum is the bug.

Dual-class premium was judged **0** and governance was pushed into bear weight 0.34 / SOTP haircut — consistent with `region_us.md` and `region_integration.md` (“no hardcoded family-control discounts”). That is **not** the failure. The failure is mixing coupon debt at trough equity so the *formula* prints a utility WACC, then §10d licenses a franchise.

Same-session book check (not a new number): IC $172.502B − net debt $82.739B ⇒ book equity ~$89.8B vs market cap $94.0B. Equity is **slightly above book**. The distressed tripwire must not depend on the book prong alone. It fires here on `wd > 0.35` **and** implied-WACC gap ~299 bp (> 200 bp).

---

## How `wacc_buildup` must sit next to `roic_identity`

`packages/kd_research/roic_identity.py` already enforces: WACC match 5 bp vs `assumptions.wacc`; mid-cycle ROIC = NOPAT/IC; `quality_bucket` from spread vs 50 bp; `franchise_mos` forbidden on below/approx; legal exits when ROIC ≤ WACC; banks/REITs `applies:false`. It **never asks whether WACC is a cost of capital**. Hygiene (`valuation_hygiene.py`) only checks that `wacc_vs_buildup` **exists**. Matching a poisoned buildup is PASS.

That is the interaction to design:

1. **`wacc_buildup` runs first** (same session, same scripted stack). It certifies ingredients. `roic_identity.wacc` must equal `wacc_buildup.wacc` and `assumptions.wacc` (draft FAIL 4).
2. **`quality_bucket` still hurdles in-model WACC.** After an honest WACC, a 20% ROIC compounder stays `above_wacc`. A 10% engine vs ~9% is a thin franchise or `approx_wacc` — **earned**, not pasted.
3. **Do not auto-reclassify `cheap_claim` from tape-implied WACC.** Implied 9.13% vs ROIC 10.01% would still be `above_wacc` on the 50 bp band, but using the tape as a FAIL hurdle is circular: cheap tape → high implied WACC → “not a franchise” → equity-near-book liquidation FV. A going-concern franchise FV is not a liquidation FV. Franchise claims need an **honest** hurdle, not the market’s.
4. **`wacc_vs_buildup: matches_buildup` stays.** The dial was built to catch silent *high* WACC (`RESEARCH_AGENTS.md` §10c.8; schema text “high WACC”; hygiene stacking copy). One-sided. v1 must teach the other side: matching is required **and** the buildup may not contain coupon-as-Kd or trough-only weights.

---

## 1. Residual analysis error

After this draft, Agent 5 can still print a WACC that is economically too low **or** too high. The machine should fail impossible ingredients, not “WACC must be 9%.”

### Still too low (franchise fake)

**Kd = Rf + 0 bp via `rf_plus_spread`.** Draft FAIL 1 is `kd_pretax >= rf`. A zero spread passes. CMCSA’s 4.0% would fail because it is *below* Rf; the next agent writes `kd_source=rf_plus_spread`, spread 0, Kd = 4.784%, still mixes at wd 49%, still prints ~6.6% WACC. Coupon-adjacent, not current yield.

**`current_yield_verified` hatch with coupon restated as YTM.** Draft allows Kd < Rf if `current_yield_verified` with a quoted YTM in-session. A lazy agent cites the same FDD 3.3–4.2% buckets (`valuation_model.json` FDD hook on Note 6/15: “Kd buildup stays ~4% pretax on coupon buckets”) and labels them YTM. Hatch without a **quoted** YTM/YTW/OAS from a session source is the CMCSA hole with a new name.

**`weight_policy=target` with target wd = trough wd.** Draft FAIL 3 forbids *only* `current_market` when the tripwire fires. Relabel `target` / `blended` at we 51 / wd 49 and the circular cheap-equity → cheap-WACC → fat FV loop survives. Sep 7 weights are the tape, not a going-concern structure.

**Omit reverse-engineering implied WACC.** FAIL 5 is conditional “when present.” Agent 5 prompt step 7 requires reverse-eng (`harness/agent_prompts.md` Agent 5). If `wacc_on_base_path` is missing, `implied_wacc_gap_bp` never computes and the 200 bp rationale never fires. CMCSA *did* write 9.13% and then explained it as “tape is cheap / distress pricing” (`reverse_engineering.rationale`) — exactly the rationale the draft wants to reject as *sole* text. Residual: skip the field.

**Beta / ERP still un-gated.** Realized 5y monthly 0.719 on a crushed name can be a trough beta. Blume toward 1 *raised* Ke here (helpful). A raw 0.5 with ERP 4.0% still prints a low Ke with no machine FAIL. Law already forbids a mandated ERP (`agent_prompts.md` Agent 5 “No mandated ERP value”; `valuation_decision_quality.md` Pair 4). Correct. Residual hole, not a v1 FAIL.

**Leases, preferred, cash.** `roic_identity.leases` already FAILs mixed Yahoo-grossed debt with opex leases. WACC can still ignore lease yield when `capitalized_both` (no `wl`) or ignore preferred. CMCSA used gross debt in weights and net debt in the EV bridge — that part is coherent. Using **net** debt in `wd` would have *raised* WACC (opposite error). Residual: preferred / lease slice not in v1.

**Local Rf.** Prompts already say do not paste US 10Y for non-USD (`agent_prompts.md` line 22; `RESEARCH_AGENTS.md` §5b). No machine check that `rf` currency matches cash-flow currency. A JPY compounder discounted at `^TNX` is too high, not too low — liquidation risk. A USD name with a local low Rf is the other way. Hatch `negative_rate_market` covers Japan-style Kd < Rf; it does not cover currency mismatch.

**Circular implied-gap as WACC.** If someone *sets* model WACC to the tape-implied 9.13% to close the gap, they have used price as the cost of capital. Draft correctly does **not** FAIL the tape for disagreeing. Do not “fix” the residual by forcing implied WACC into the model.

### Still too high (engine liquidated)

**Named sleeve treated as illegal pad.** July 25 +345 bp *after* mixing with debt is the anti-pattern. Sep 7 +25 bp structural ops sleeve *inside Ke* is the legal pattern. If 2.40 text says “match buildup, no add-on” without “sleeves live in Ke with use/reject,” agents will either (a) omit idiosyncratic risk or (b) hide it in a 0 bp Kd spread. Quality compounder wants (named Ke sleeve), not (a) or (b).

**Blume mandated toward 1 on a 0.3 beta.** Draft `beta_policy` is judgment, “not all mandated in v1.” Keep it that way. A true low-beta franchise (staples, some net-cash software) has Ke that should not be dragged to 1.0. Mandating Blume is a silent pad — the thing `wacc_vs_buildup` exists to catch.

**Family-control / Damodaran country paste stacked on CF haircuts.** Already illegal as hardcoded tables (`RESEARCH_AGENTS.md` §5b; `region_integration.md` reject row; Agent 5 “NEVER paste region-module ranges as mandated WACC/ERP/family discounts”; dual-class “may be 0”). Careless 2.40 text that “governance must appear in WACC” would re-open the stack: bear path already haircuts cash flows, then Ke is padded again. CMCSA’s 0 on WACC + bear 0.34 is the *correct* dual-class pattern for this law. Do not “fix” CMCSA by forcing a family bp.

**Target wd set far below going-concern (under-lever).** Tripwire gaming the other way: `target` wd 10% on a structural 35% issuer. WACC ≈ Ke, franchise spread shrinks, `g_zero` / `equity_near_book` legal exits fire, compounding engine is written down to book. v1 should require target-weight *rationale*, not a mandated wd.

**Shared calculator that pastes rates.** Assignment already says Agent 5 writes a new `S/data/compute/valuation.py` every session; shared **checker** is the `roic_identity.py` pattern. A library function with Rf=4.784 or ERP=5.0 would be a hardcoded WACC by another name.

---

## 2. Wrong prompt

What in Agent 5 / Agent 13 / `RESEARCH_AGENTS.md` would cause CMCSA again, or a new failure if draft text is pasted carelessly.

**“Match the buildup / do not pad” as the whole CoC religion.**  
§10c.8 requires `wacc_vs_buildup`. Agent 5 4e: four conservatism dials, omit is FAIL. Hygiene FAIL copy: “do not stack volume + GAAP OM + SBC-as-cash + **high WACC** silently into base.” Schema `stacking_justification`: “Silent stacking of … **high WACC** into base is FAIL-quality.” Sep 7’s dial rationale is the obedience text: “No silent WACC pad above buildup.” That sentence, without an ingredients identity, **reproduces coupon Kd**. v1 prompt must say: matching is required; coupon is not a legal Kd; Kd < Rf is FAIL unless a named hatch; trough `current_market` alone is illegal when the tripwire fires.

**§10d “hurdle is in-model WACC, not a 15% Buffett paste.”**  
Keep this sentence. It is the anti-liquidation rule. Careless add-on “also compare to implied WACC / 9% / 15%” contradicts it and will false-kill compounders. The fix is to make in-model WACC honest, not to add a second hurdle number.

**`cheap_claim=franchise_mos` only when `above_wacc`.**  
Correct license (`RESEARCH_AGENTS.md` §10d.4; Agent 5 2b; Agent 13 4-roic). It will keep licensing franchise whenever WACC is still a bit low (ERP/beta residual). That is acceptable if ingredients are honest. It is **not** acceptable to add “`franchise_mos` illegal when implied gap > 200 bp.” That is the tape as auditor. Agent 13 should **grade** whether the franchise note addresses Kd/weights (draft WARN), not flip the class.

**Dual-class = 0 / no family-control paste.**  
Agent 5 step 2: “CoC/governance dials (may be 0).” `region_us.md`: dual-class is a governance dial, not an automatic country premium. CMCSA followed this and still failed on Kd/weights. Do not “correct” 2.40 by requiring a non-zero governance sleeve. Require **use-or-reject** (already the hook pattern). Zero remains legal.

**“Do not paste module WACC/decay tables.”**  
Agent 5 Y1 LAW and step 2. Agents read this as “do not raise WACC above the formula.” Draft must not introduce a module table *or* a prompt table of “typical WACCs.” Hatch names (`negative_rate_market`, `current_yield_verified`), not 9%.

**Pair 1 GOOD in `rationale_quality.md`.**  
Build-up with after-tax Kd 3.8% at **12%** debt weight, Rf 4.2%. Illustrative, not coupon-labeled, and wd is not trough. Still silent on `kd_source`. A reader can copy “after-tax cost of debt 3.8%” as a coupon. Add one GOOD clause in v1 (or a 2.40 exemplar): Kd is **current yield or Rf+spread**, coupon is a cross-check only. Do not copy the 9.5% into live sessions (exemplar already says illustrative).

**Agent 13 4-roic / 4-midcycle.**  
Grades NOPAT/IC vs DCF, Gordon-free-growth, `franchise_mos` on below/approx, last-year license. **Does not grade Kd vs Rf, kd_source, or distressed weights.** ERP “industry standard / mid of band” is already a finding (`valuation_decision_quality.md` Pair 4). Band 3 will PASS a 6% WACC that matches the script. Add a **4-wacc** band that grades the identity and treats “tape is cheap / franchise MoS” as insufficient gap rationale — without failing banks for missing industrial WACC (`applies:false`, same hatch as ROIC).

**Agent 5 self-check (1)–(11).**  
No Kd, no weights policy, no implied-gap rationale. Add (12) `wacc_buildup` present or `applies:false` with reason; coupon illegal; Kd vs Rf; tripwire.

**Contradiction with `wacc_vs_buildup` if sleeves are called pads.**  
If draft text says “keep `matches_buildup`” **and** “idiosyncratic risk is a named Ke sleeve,” that is coherent. If it says “any number above Rf+β×ERP is a pad,” it forbids the sleeve and recreates July 25’s *hidden* premium (agents will stuff risk into Kd=coupon or into OM haircuts). Write the distinction once: **Ke sleeve ∈ buildup**; **WACC add-on after mixing with Kd ∉ buildup**.

---

## 3. Bad harness

How the gate itself becomes harmful.

**False FAIL — banks / insurance / REITs.**  
ROIC already uses `applies:false` + native analog (`roe_vs_ke`, NAV/AFFO). Draft copies this. Enforce it. Do not FAIL a bank for missing industrial Kd/we/wd. Agent 13: “Do not fail banks for missing industrial IC” (`agent_prompts.md` 4-roic) needs a sibling for WACC.

**False FAIL — Japan / negative-rate.**  
Hatch `negative_rate_market` with **local** Rf evidence. Do not use `^TNX` as the comparison for JPY Kd. `region_integration.md` already forbids hardcoded CRP; the hatch is evidence, not a country table.

**False FAIL — utilities.**  
Assignment: utilities may sit close to Rf but still WACC > Rf. Gate 1 is **Kd vs Rf**, not a minimum WACC−Rf spread of 200 bp. A utility with Kd 20–50 bp over Rf and modest wd can print WACC only slightly above Rf. That is not CMCSA (Kd *below* Rf). Do not add a “WACC ≥ Rf + 200 bp” machine FAIL.

**False FAIL — net-cash tech.**  
Tiny `wd` is legal. Tripwire is `wd > 0.35` **and** (gap > 200 bp **or** equity ≤ book). Net-cash never trips. Do not force `target_weights` on cash-rich compounders.

**`wd > 0.35` without the AND.**  
Capital-intensive going-concern franchises (some infrastructure-like quality names, levered but solvent) can sit above 35% debt without a 200 bp implied-WACC gap. Firing on wd alone overfits CMCSA and forces target-weight theater. **Keep the AND.**

**Overfit to CMCSA book prong.**  
Sep 7 equity is *above* book. A tripwire that is only “equity ≤ book” misses this incident. Keep implied-gap **or** book, not book only.

**Easy games (already named in residual):** `rf_plus_spread` 0 bp; target wd = trough wd; Blume mandated on 0.3 beta (too high, not too low); coupon labeled YTM; omit implied WACC field.

**Shared calculator that pastes rates.** Harmful. Checker only. Agent 5 still judges Rf, beta, ERP, spread, target weights (`00_assignment.md` draft design — keep).

**Machine FAIL of the tape.** Draft already says do not FAIL the tape for disagreeing. Agree. FAIL-ing FV because implied WACC is 300 bp higher would encode “the market’s hurdle is the true hurdle.” Quality compounder rejects that. WARN on gap rationale that ignores Kd/weights.

**`franchise_mos` auto-kill when gap > 200 bp.** Harmful. Would have turned Sep 7 into `equity_near_book` *even after* an honest ~9% WACC, because the tape can stay distressed. Cheap ≠ accurate. Disclose and grade; do not re-bucket.

**Version band.** New runtime ≥ 2.40.0; old stamps SKIPPED — same as `roic_identity.py` `session_since`. Do not FAIL July 25 or Sep 7 as live patients.

---

## 4. Load-bearing change (ranked)

Rank is **caught Sep 7?** × **false-FAIL a healthy franchise?** One shippable v1 vs later wave.

### v1 — require (ship)

| Rank | Change | Caught Sep 7? | False-FAIL healthy franchise? |
|---|---|---|---|
| **R1** | **`kd_source` ∈ {`current_yield`, `rf_plus_spread`} only. Coupon illegal as WACC input; coupon may be disclosed as cross-check.** | **Yes.** Script comment and FDD hook are coupon buckets. | No. Healthy names already have YTM or a spread. |
| **R2** | **`kd_pretax >= rf` unless named hatch (`negative_rate_market` + local Rf evidence, or `current_yield_verified` + **quoted** YTM/YTW/OAS in-session — not coupon restated).** | **Yes.** 4.0% < 4.784%. | Japan hatch; utilities with Kd ≥ Rf pass. |
| **R3** | **Arithmetic: WACC = we×Ke + wd×Kd(1−t) within 5 bp; equals `assumptions.wacc` and `roic_identity.wacc`. `we+wd` ≈ 1. `wacc_minus_rf` identity printed.** | Partial (Sep 7 already matched). Prevents the next “close enough” drift. | Same 5 bp as existing ROIC WACC match. |
| **R4** | **Distressed-equity: going-concern DCF may not use *only* `current_market` when `wd > 0.35` AND (implied WACC gap > 200 bp **or** equity at/below book). Then `target` or `blended` + rationale.** | **Yes** on the AND (wd 49% and ~299 bp gap). Book prong alone would **miss**. | Keep the AND so levered compounders without a gap do not trip. |
| **R5** | **Implied gap > 200 bp → `wacc_gap_rationale` ≥40 chars that is *not only* “tape is cheap / franchise MoS.” WARN if rationale ignores Kd/weights. Do not FAIL the tape. Do not FAIL `franchise_mos`.** | **Yes** as paperwork (Sep 7 rationale is exactly the forbidden sole text). | WARN-not-FAIL protects real compounders the tape hates. |
| **R6** | **`applies:false` + ≥40 char reason for banks / insurance / REITs / other non-WACC natives. Version-band ≥ 2.40.0; legacy SKIPPED. Shared checker, not a rate calculator. No WACC number in prompts/modules.** | N/A (CMCSA is FCFF). | Prevents bank/REIT carnage. |
| **R7** | **Prompt distinction: keep `wacc_vs_buildup: matches_buildup`. Idiosyncratic risk = named **Ke** sleeve (ops/size/governance) with use/reject. Dual-class **may be 0**. Sleeves ∈ buildup; post-mix WACC add-on ∉ buildup.** | Distinguishes July 25 pad from Sep 7 +25 bp sleeve. Does not itself catch coupon Kd. | Prevents liquidation via mandatory family/country bp. |
| **R8** | **Agent 13 `4-wacc` band + Agent 5 self-check item: grade identity, kd_source, Kd vs Rf, tripwire, gap rationale. Do not fail banks. Do not treat Audit PASS as a bid.** | Catch as audit if machine hatch is gamed. | Same as 4-roic discipline. |

### v1 — add (small, still ship)

| Rank | Change | Why |
|---|---|---|
| **A1** | **`rf_plus_spread` must store `credit_spread_bp`. Spread = 0 requires a hatch (`quoted_ytm_equals_rf` or `net_cash_or_aaa`), else FAIL.** | Closes the 0 bp game after R1–R2. Not a pasted Kd. |
| **A2** | **If `weight_policy=target` or `blended`, require `target_wd` (and current wd) **and** either a material difference from trough current **or** ≥40 char why going-concern structure equals current.** | Closes relabel-as-target at we 51 / wd 49. |
| **A3** | **`current_yield_verified` hatch: pointer to a session quote (bond, YTW, OAS). Coupon table is not a quote.** | Stops FDD coupon buckets wearing a YTM hat. |
| **A4** | **When `cheap_claim=franchise_mos` and implied gap > 200 bp: require `franchise_hurdle_note` ≥40 chars that mid-cycle ROIC was also *discussed* vs Ke (or vs a WACC rebuilt with legal Kd + non-trough weights). Disclosure only — **no** machine re-bucket, **no** 15% paste.** | Makes the franchise claim honest without liquidating the engine. Sep 7’s cheap_claim rationale compares only to 6.14% in-model WACC. |

### v1 — drop / do not ship

| Drop | Why |
|---|---|
| Mandated `beta_policy=blume` | Silent pad on 0.3-beta compounders. Judgment in v1. |
| Any WACC / ERP / Kd / “use 9%” number in Agent 5, Agent 13, modules, or schema examples that look copyable | Contradicts §5b / region_integration / “no hardcoded WACC.” July 25 9.0% is incident history, not law. |
| FAIL tape for implied gap; FAIL `franchise_mos` because gap > 200 bp | Cheap ≠ accurate. Going-concern ≠ liquidation. |
| Tripwire on `wd > 0.35` alone | Overfit; false-FAIL levered franchises. |
| Mandatory family-control / Damodaran country bp | Stacks on CF haircuts; liquidates. Dual-class may stay 0. |
| Shared WACC calculator with snapshotted “house” rates | Hardcode by another name. Checker only. |
| Rewrite of CMCSA `2026-09-07` (or July 25) | Immutable archive. New runs only. |

### Later wave (not v1)

- Lease yield / preferred slice in the weighted formula when `capitalized_both` or preferred is material.
- Currency match: `rf` vs cash-flow currency (machine WARN).
- Optional unlever-relever-at-target as a *policy enum*, still not mandated.
- Agent 13 finding if `franchise_mos` spread vs honest WACC is thin (< ~100 bp) **and** the engine has no reinvestment runway — still not a machine FAIL (would nuke mature cash cows that are allowed to be “above WACC, low g”).
- Do **not** add a Buffett 15% ROIC paste in any wave (`RESEARCH_AGENTS.md` §10d.1).

---

## Persona test on the draft

Ask only this of a new run: **is the economic engine still high-ROIC with a reinvestment runway, or has it broken?** That question is unanswerable if the hurdle is coupon×trough leverage.

- A too-low WACC makes every average business look like a franchise (`above_wacc`, `franchise_mos`). **Sep 7.** Draft R1–R5 would have stopped the *impossible ingredients*. They would **not** have forced a 15% hurdle. A 10% ROIC vs an honest ~9% WACC is a thin franchise; the DCF FV compresses; the bucket may stay `above_wacc`. That is the right residual. Cheap tape is then a margin of safety **or** a value trap — Agent 12 / duration / stress, not a WACC paste.
- A too-high WACC (silent pad, country table, family haircut stacked on OM cuts, Blume-to-1 on a 0.3 beta) liquidates a real compounder into `approx_wacc` / `g_zero` / `equity_near_book`. Draft must not do that. Matching buildup + named Ke sleeves + no hardcoded rates is the anti-liquidation half.

**Shippable 2.40:** identity object + FAILs R1–R6 + prompt distinction R7–R8 + small adds A1–A4. Checker patterned on `roic_identity.py`. Agent 5 still writes the session script. No rewrite of CMCSA.

---

## Files read

- `eng/sessions/2026-09-07-wacc-buildup-gate/handoffs/00_assignment.md`
- `eng/sessions/2026-09-07-wacc-buildup-gate/issue.json`
- `harness/RESEARCH_AGENTS.md` (§5b, §6, §10c.8, §10d, §13)
- `harness/agent_prompts.md` (Agent 5, Agent 13)
- `harness/schemas/valuation_model.schema.json`
- `packages/kd_research/valuation_hygiene.py`
- `packages/kd_research/roic_identity.py`
- `harness/exemplars/rationale_quality.md` Pair 1
- `harness/exemplars/valuation_decision_quality.md` (Pairs 2, 4, 7, 8)
- `harness/modules/region_us.md`
- `harness/region_integration.md`
- Incident: `archive/research/CMCSA/2026-09-07/data/valuation_model.json`, `data/compute/valuation.py`, `data/compute/valuation_result.json`, `data/market_inputs_snapshot.json`
- Contrast only: `archive/research/CMCSA/2026-07-25/data/valuation_model.json` WACC rationale
