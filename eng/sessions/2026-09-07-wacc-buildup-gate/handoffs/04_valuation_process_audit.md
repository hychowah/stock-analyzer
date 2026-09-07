# Valuation-process audit — WACC-buildup identity (draft 2.40)

Persona: DCF architect. Grade **model specification and harness design**, not the CMCSA story.  
Incident cited as a read-only specimen. Do not rewrite `archive/research/CMCSA/2026-09-07`.  
Action verbs (pass, hold) are outputs, not inputs to this memo.

---

## Lead answer

**Ship a shared checker, not a shared calculator.** Copy the `roic_identity.py` pattern: Agent 5 still writes a new `S/data/compute/valuation.py` every run and still judges Rf, beta, ERP, spread, and weights; the machine fails **impossible ingredients** and **broken identities**, never “WACC must be 9%.”

**v1 (2.40) is load-bearing if and only if it does four things the current law does not:**

1. **Coupon is not Kd.** `kd_source` ∈ {`current_yield`, `rf_plus_spread`}. Coupon may be disclosed as a cross-check; it is illegal as the WACC input. Require a **numeric** YTM or spread field evidenced in-session — an enum plus a comment in `valuation.py` is how CMCSA Sep 7 happened (`kd_pretax = 0.040  # ~coupon/effective from FDD debt note`).
2. **`kd_pretax >= rf`** unless a named hatch resolves against session artifacts (`negative_rate_market` with **local** Rf, or `current_yield_verified` with a quoted YTM). Skip the inequality when `wd` is economically zero (net-cash).
3. **Rewrite `wacc_vs_buildup`.** Today `matches_buildup` + `applies_in=none` is a **conservatism PASS** for mixing a legal-looking CAPM Ke with illegal cheap debt. Keep the dial for silent **pads above** a *legal* buildup. Matching an illegal buildup is a **new identity FAIL**, not a conservatism virtue. Do **not** prompt “always match the buildup” without saying “legal ingredients.”
4. **Distressed-equity tripwire on weights.** Going-concern FCFF may not use **only** `current_market` when `wd > 0.35` **and** (implied-WACC gap > 200 bp **or** equity at/below book). Then `target` or `blended`, with a target `wd` that is not a relabel of the trough `wd`.

Arithmetic identity (WACC = `we×Ke + wd×Kd(1−t)` within 5 bp, matching `assumptions.wacc` and `roic_identity.wacc`) is necessary and **would have PASSed CMCSA**. The algebra was correct. The ingredients were not. Do not ship arithmetic alone and call the incident closed.

**Drop from v1:** mandated Blume, mandated unlever/relever, any pasted WACC/ERP/Kd table, a shared Python WACC calculator that returns a rate, `dual-class` Ke ≠ 0 as a machine FAIL, and `applies:false` as a 40-character essay hatch on an FCFF DCF.

**Add in v1, cheap, anti-game:** bind `applies:true` to FCFF/WACC model family; `kd_aftertax = kd_pretax×(1−t)` within 5 bp; `we+wd≈1` (v1; preferred later); skip Kd-vs-Rf when `wd < 0.05`; require `implied_wacc_gap_bp` from reverse-engineering when that object exists; WARN (not FAIL) if TV share > 60% **and** the gap > 200 bp while `terminal_consistency.response` names only “mature FCF,” not CoC.

A later wave can take leases-in-weights vs `roic_identity.leases`, preferred/hybrids, Hamada at target, beta-window policy, and a structured Ke-sleeve object. Those would not have been required to catch Sep 7.

---

## Specimen (process facts only; do not treat as a patient)

From `archive/research/CMCSA/2026-09-07` (harness 2.39-era). Stored values, not invented:

| Piece | Stored | Where |
|---|---|---|
| Price | $26.49 | `data/compute/valuation_result.json` |
| WACC | 6.145% | `data/valuation_model.json` `assumptions.wacc` |
| Ke | 9.092% | same |
| Rf | 4.784% (`^TNX`) | `data/market_inputs_snapshot.json` |
| Beta | 0.719 raw → 0.812 Blume | snapshot + `valuation.py` `beta = 0.67 * beta_raw + 0.33 * 1.0` |
| ERP | 5.0% | snapshot `erp_historical_us_selected` |
| Kd pretax | **4.0%** coupon buckets 3.3–4.2% | `data/compute/valuation.py` `kd_pretax = 0.040` |
| Tax | 23% | script → Kd after-tax 3.08% |
| Weights | we 51.0% / wd 49.0% at **current** mkt cap vs **gross** debt | `valuation_result.json` intermediates |
| Tape-implied WACC on base path | 9.13% | reverse-engineering (~299 bp gap) |
| Base FV | $59.83 | valuation_model |
| `wacc_minus_g` | 4.14% (g 2.0%) | `terminal_consistency` |
| TV share of EV | 69.66% | same; Y8 growth 1.8% |
| `cheap_claim` | `franchise_mos` because mid-cycle ROIC 10.01% vs WACC 6.14% | `roic_identity` |
| `wacc_vs_buildup` | `matches_buildup`, `applies_in=none` | `conservatism_dials` |

July 25 (`archive/research/CMCSA/2026-07-25/data/valuation_model.json`) saw raw CAPM ~5.55% and added a **+345 bp company premium to 9.0%**. Later harness taught “do not pad; match the buildup.” Sep 7 obeyed that sentence and printed a utility-like 6.14% with legal-looking CAPM Ke mixed with coupon Kd and trough weights.

Current machines (`packages/kd_research/valuation_hygiene.py` `check_conservatism_dials`, `packages/kd_research/roic_identity.py` 5 bp WACC match) check that WACC **equals** the formula and that the dial **exists**. They do not check Kd vs Rf, Kd source, or distressed weights.

---

## 1. Residual analysis error

After the draft as written, Agent 5 can still print a WACC that is economically too low or too high. Ranked by whether the hole is already in current law.

### 1.1 Holes the draft **does** close (if predicates are not gamed)

- **Coupon-as-Kd.** Sep 7: `kd_pretax = 0.040` with FDD coupon buckets, Rf 4.784% → pretax Kd **below** the risk-free used in Ke. Draft FAIL 1 + FAIL 2 catch this **if** `current_yield_verified` requires a quoted YTM, not the coupon restated as yield.
- **Trough-weight circularity.** `we = e_mkt / (e_mkt + d_mkt)` with `e_mkt` from the tape. Trough equity → high `wd` → low WACC → high FV → larger implied gap → “tape is cheap.” Draft FAIL 3 is the right tripwire **if** `target` cannot equal current `wd` without a basis that is not the trough itself.
- **Franchise license from a too-low hurdle.** `roic_identity` hurdles **in-model WACC** (`harness/RESEARCH_AGENTS.md` §10d; Agent 5 step 2b). A 10% ROIC vs 6% WACC is `above_wacc` → `franchise_mos`. The ROIC gate will keep licensing franchise until WACC ingredients are legal. Draft does not change ROIC law; it changes the hurdle’s inputs. That is correct. Do not add a second ROIC hurdle.

### 1.2 Residuals the draft leaves open (v1 acceptable if named)

**Beta window and Blume (too low).** Sep 7 used 5y monthly vs `^GSPC`, then Blume toward 1. Draft `beta_policy` is “judgment; not all mandated in v1.” Residual: a 0.3 raw beta Blume-adjusts to ~0.53; a trough “bond-proxy” 0.72 becomes 0.81. Neither unlever/relevers at **current** or **target** leverage. Historical equity beta was earned at **lower** leverage than today’s 49% `wd`. Hamada at target would raise Ke; the draft will not catch a too-low beta. **Leave for a later wave.** Mandating Blume in v1 would **raise** some 0.3 betas toward 1 (false high Ke on true defensives) and would not have been the Sep 7 kill shot.

**ERP (too low or too high).** Agent 5 already requires method + rejected competitor (`harness/agent_prompts.md` Hard constraints; `valuation_decision_quality.md` Pair 4). No mandated ERP value — keep that. Residual: `data/market_inputs_snapshot.json` stored `erp_historical_us_selected: 0.05`, i.e. the **method was pre-selected** in the snapshot. Agent 5 then “chose” what the snapshot already named. Not a 2.40 machine FAIL. Later: snapshot stores candidate series; Agent 5 writes the selection on `wacc_buildup.erp_method`.

**Rf vintage / tenor / currency.** `^TNX` last close is a point 10Y. Process alternatives (30Y, TIPS+inflation, local JGB) stay judgment. Residual: a JPY model discounted at `^TNX` can make JPY Kd look “below Rf” or US Kd look fine. Agent 5 already says cash-flow currency must match discount-rate currency (`agent_prompts.md` step 2). Draft should require `wacc_buildup.rf` **equals** the Rf inside Ke (5 bp), and that Rf is the **local** series named by `market_context` when `use_local_rf` is true. Do not FAIL Japan for Kd < US 10Y.

**Leases in weights (usually too-low WACC if omitted, or mixed stack).** Sep 7: `roic_identity.leases = opex_and_out_of_ic` and WACC weights used **gross carrying debt**, not capitalized operating leases. That is internally consistent with the lease convention. The residual is the opposite error: Yahoo lease-grossed debt in `wd` while ROIC leaves leases in opex — already forbidden for IC (`RESEARCH_AGENTS.md` §10d.1) but **not** forbidden for WACC weights. Draft is silent. **Later wave:** `wacc_buildup.leases` must equal `roic_identity.leases`; capitalized-both ⇒ leases in `D`; opex-out ⇒ leases not in `D`. v1 can WARN on mismatch; do not FAIL utilities that use book regulatory capital.

**Preferred / hybrids (too-low WACC if stuffed into cheap debt or ignored).** Not in the draft. v1 `we+wd≈1` will **PASS** a name that buries preferred in `D` at Kd. Later: `wp` + `kp` or an explicit `none` with “no preferred on BS.”

**Cash / net vs gross (weights).** Sep 7 used **gross** debt for `wd` and **net** debt for the equity bridge. That is a defensible Damodaran split and it **maximized** `wd` (worse WACC, not better). Net-cash tech with tiny gross debt is the other tail: `wd≈0`, Kd unused. Draft FAIL 1 would still compare a dummy coupon to Rf. **v1 must skip Kd-vs-Rf when `wd < 0.05`.** Otherwise net-cash FAILS for a rate that does not enter WACC.

**Named Ke sleeve vs silent WACC pad.** Draft: idiosyncratic risk is a **named Ke sleeve** (ops / size / governance) with use/reject — not a silent add-on after mixing with cheap debt. Sep 7 had +25 bp `structural_ops_premium` **inside Ke** and dual-class **0**. That is the legal shape. Residual: Agent 5 can still set the sleeve to 0 and dump risk into bear weight (`assumptions.dual_class_governance_premium` rationale: “region_us forbids pasting a family-control module discount into Ke”). That is **not** a WACC-algebra fail; it is a risk-placement choice. Do not machine-FAIL dual-class = 0. Do FAIL a **WACC pad after** `we×Ke+wd×Kd(1−t)` unless `wacc_vs_buildup.applies_in=base` (the original conservatism dial).

**Circularity of the implied-gap tripwire.** Implied WACC is reverse-engineered from **price given the base path**. An optimistic volume/OM path inflates implied WACC even when model WACC is fair. Draft correctly: do **not** FAIL the tape for disagreeing; require `wacc_gap_rationale` ≥40 chars that is **not only** “tape is cheap / franchise MoS”; WARN if the rationale ignores Kd/weights. Residual: Agent 5 writes 40 characters about Kd/weights and keeps coupon Kd. **Kd-source FAIL must fire first.** The gap rationale is a documentation gate, not the kill shot.

**Gordon `wacc_minus_g` and TV share.** Sep 7: `wacc_minus_g = 0.0414`, TV share 69.7%, Y8 growth 1.8%. Existing machine (`packages/kd_research/epistemology.py` `check_tv_share_duration`) FAILs TV>60% only when Y8 growth ≥8%, or TV>75% without extend/switch/`decision_usefulness=low`. A **low WACC** inflates TV share **without** high Y8 g, so the current TV gate is blind to this incident. Gordon multiple on terminal FCFF is `1/(wacc−g)`: 6.14% vs 2% is a fat multiple; 9.13% vs 2% is not. Residual after draft: FAIL 5 does not touch `terminal_consistency`. **v1 WARN:** if `tv_share_of_ev_base > 0.60` **and** `implied_wacc_gap_bp > 200`, `terminal_consistency.response` must name CoC/Kd/weights, not only “mature FCF.” Do **not** FAIL `wacc_minus_g` below a hardcoded floor (Japan, utilities).

**Compute-script hermeticity.** `harness/RESEARCH_AGENTS.md` §7: scripts may **embed fetched values as constants with a comment citing source**. Agent 5 **must** write a new `valuation.py` every session (`agent_prompts.md` step 5). Coupon hardcodes **live there by design**. A checker that parses Python comments will lose. The identity object on `valuation_model.json` + numeric fields on `valuation_result.json` intermediates is the only hermetic surface. If Agent 5 writes `kd_source=current_yield` and `kd_pretax=0.040` with no YTM in snapshot/FDD, that is FAIL — same class as Street `delta_pct` identity.

**Local Rf / negative-rate hatch.** Needed for Japan. Residual: hatch text without a local Rf series in-session. Resolve like `independence_gate`: pointer must hit `market_inputs_snapshot` / `market_context.cost_of_capital_flags`, not a 40-char essay.

**Too-high WACC (the July 25 over-correction).** Draft + “keep `wacc_vs_buildup: matches_buildup`” will **prevent** a silent +345 bp WACC pad, which is what the dial was built for. If the +345 bp is moved **into Ke** as a named sleeve, arithmetic still matches and the machine PASSes a 12% Ke. That is judgment, not an impossible ingredient. Agent 13 already grades “industry standard / mid of band” as empty ERP. Do not add a “Ke sleeve too large” machine FAIL in v1 — it becomes a hardcoded WACC.

---

## 2. Wrong prompt

The Sep 7 failure is a **prompt-taught virtue**. Adding draft text carelessly will either re-run it or create a new one.

### 2.1 Lines that would cause CMCSA-class failure again

**`wacc_vs_buildup` as currently specified.**  
`harness/RESEARCH_AGENTS.md` §10c.8 and Agent 5 step 4e: required keys include `wacc_vs_buildup`; omitting the array is FAIL; stacking ≥3 in base needs justification. The **semantic** taught in Sep 7 (`conservatism_dials[wacc_vs_buildup].rationale`): “No silent WACC pad above buildup.” Combined with July 25’s pad-to-9%, the live agent read: **matching the weighted formula is conservative and complete.** It is not, when Kd is a coupon and `wd` is the trough.

Draft sentence “Keep `wacc_vs_buildup: matches_buildup`” will **re-encode** that reading unless you add: *matches_buildup means WACC equals `we×Ke+wd×Kd(1−t)` using legal `kd_source` and a legal `weight_policy`. Matching a coupon buildup is identity FAIL, not conservatism PASS. A named pad **above** a legal buildup is `applies_in=base` (the original dial).*

**Exemplars Pair 1 GOOD teaches the opposite pad.**  
`harness/exemplars/rationale_quality.md` Pair 1 GOOD: “Slightly above peer median ~9.0% to reflect higher capex/execution risk.” That is a **WACC add-on after the buildup**, exactly what `wacc_vs_buildup` was built to catch. Agent 5 is told to read this file (`agent_prompts.md` Judgment style). **Rewrite Pair 1 GOOD** before 2.40 ships: legal Kd (YTM or Rf+spread), weights stated as `current_market` or `target` with a reason, risk inside a **named Ke sleeve**, WACC = formula. Peer median is a cross-check, not a paste and not a silent pad.

**`sector_utility.md` teaches coupon-as-Kd.**  
Advisory table: “Cost of debt | 5.0% | Weighted avg coupon” (`harness/modules/sector_utility.md`). Agent 5 is told modules are advisory and “Do not paste module WACC/decay tables” (Y1 LAW; step 2 NEVER paste region-module ranges). A utility session that **does** follow the module’s cost-of-debt line will FAIL the new Kd-source gate. That is **intended** if coupon is illegal — but Agent 13 will then fight the module. Add one line to Agent 5 and, in a later module edit, to the utility file: *module coupon tables are cross-checks; WACC Kd is YTM or Rf+spread.* Do not paste 5.0% into the prompt.

**Dual-class = 0 as a misread of “never hardcode family-control discounts.”**  
`region_us.md`: “Dual-class / founder control is a **governance** dial, not an automatic country premium.”  
`region_integration.md` / Agent 5 conventions: never apply **hardcoded** family-control discounts.  
Sep 7: “region_us **forbids** pasting a family-control module discount into Ke. Dial judged 0.”  
That is a category error: **forbidding a hardcoded table is not a mandate that the dial is 0.** Agent 5 step 2 already says CoC/governance dials **may be 0**. Keep that. Add: *zero is a use/reject judgment, not compliance with the no-hardcode rule. Dual-class risk may sit in a named Ke sleeve **or** in bear weight; silence is not required.* Do not machine-FAIL a 0.

**ROIC franchise license + matched low WACC.**  
Agent 5 step 2b / §10d: `cheap_claim=franchise_mos` only when `quality_bucket=above_wacc`; hurdle is **in-model WACC**. Agent 13 `4-roic` grades franchise on below/approx as major. Neither grades “the hurdle is a 6% coupon mix.” After 2.40, Agent 13 `4-roic` should **read** `wacc_buildup` before treating `above_wacc` as a real franchise. Do not let Agent 13 invent a 9% hurdle.

**“Do not paste module WACC” × “Kd pretax ≥ Rf”.**  
`RESEARCH_AGENTS.md` §1.1: “The harness contains **no fixed formulas**, no hardcoded probabilities, no hardcoded multiples.” §5b / `region_integration.md`: no hardcoded regional WACC / ERP tables. If 2.40 is phrased as “use WACC ≥ 8%” or “ERP = 5%,” Agent 5 will (correctly) refuse, or Agent 13 will FAIL a legal 6.5% utility. Phrase the gate as an **identity of the agent’s own ingredients** — same class as Street `|delta|>5%` and ROIC 5 bp WACC match — not as a rate table. Put that sentence in §1.1 or §10e so it does not look like a contradiction.

### 2.2 Specific prompt-line edits (v1)

**Agent 5 — insert after step 2 “NEVER paste region-module ranges…”** (not inside Y1 LAW):

> WACC BUILDUP IDENTITY (harness ≥ 2.40.0): when the model is an FCFF/WACC DCF, write `wacc_buildup` (`applies:true`). Banks / insurance / REITs / other non-WACC natives: `applies:false` with ≥40 char reason **and** `native_analog`; you may not set `applies:false` on an FCFF/WACC `model.name`. Script `rf, ke, kd_pretax, kd_aftertax, tax, we, wd, wacc`. `kd_source` is `current_yield` or `rf_plus_spread` only — coupon is a cross-check, never the WACC input. `kd_pretax >= rf` unless `kd_below_rf_gate` resolves (`negative_rate_market` with local Rf in-session, or `current_yield_verified` with a quoted YTM in-session). Skip Kd-vs-Rf when `wd < 0.05`. `weight_policy` `current_market` may not be the **sole** policy when the distressed-equity tripwire fires (`wd > 0.35` and (implied WACC gap > 200 bp or equity at/below book)) — then `target` or `blended` with a target `wd` basis that is not the trough print. WACC = `we×Ke + wd×Kd(1−t)` within 5 bp, matching `assumptions.wacc` and `roic_identity.wacc`. Named Ke sleeves (ops / size / governance) are part of Ke (use or reject). `wacc_vs_buildup: matches_buildup` means this identity with **legal ingredients**; it does not license coupon Kd or trough-only weights. A pad above a legal buildup is `applies_in=base`. Do **not** paste a WACC, ERP, or Kd number from this prompt or any module.

**Agent 5 self-check — add (12):** `wacc_buildup` present on ≥2.40; `kd_source` legal; Kd vs Rf or hatch; `we+wd≈1`; arithmetic; if reverse-engineered WACC exists and gap >200 bp, `wacc_gap_rationale` names Kd and/or weights, not only “tape is cheap / franchise MoS.”

**Agent 5 step 4e conservatism sentence:** after the four keys, add the matches-vs-illegal distinction above. Do not say “always `applies_in=none`.”

**Agent 13 — new Band 3 item `4-wacc` (after `4-roic`):**

> On harness ≥ 2.40.0: `wacc_buildup` present or `applies:false` with reason on a non-WACC native. Grade hatch **substance** the way you grade `independence_gate`: `current_yield_verified` must be a quoted YTM in snapshot/FDD, not the coupon relabeled; `target`/`blended` weights must not equal trough `wd` without a non-tape basis; `negative_rate_market` needs local Rf. Do not fail banks/REITs for missing industrial WACC. Do not fail Japan solely because Kd < US 10Y. Do not fail net-cash because a dummy Kd < Rf when `wd` is tiny. Do not fail a utility whose YTM sits close to local Rf if WACC > Rf and weights are target/book-regulatory. **Do not recompute a “correct” WACC.** Coupon-as-Kd or trough-only weights on a tripped going-concern DCF is **major** even if `wacc_vs_buildup` says `matches_buildup`. `franchise_mos` that depends on an illegal buildup is major (the ROIC bucket is not a defense).

**`RESEARCH_AGENTS.md`:** new §10e (or a row in §13) mirroring §10d: skill not a formula; machine rehydrates identities; never writes g or FV; SKIPPED < 2.40.0. One sentence under §1.1: identities of the agent’s own CoC ingredients are not “hardcoded WACC.”

**Do not** add a number (9%, 200 bp as a “right WACC,” ERP 5%) to any of those lines. The 200 bp figure is a **gap tripwire**, same class as Street 5% — keep it in the gate spec, not as a taught WACC.

---

## 3. Bad harness

### 3.1 Shared checker vs shared calculator

`roic_identity.py` is the right pattern: it **rehydrates** NOPAT/IC/WACC/spread/bucket from objects the session already wrote; it never authors g or FV (`packages/kd_research/roic_identity.py` header). `valuation_hygiene.py` only checks that `wacc_vs_buildup` **exists** among four keys — existence, not economics.

A `packages/kd_research/wacc.py` that **returns** Rf+β×ERP or a default spread **is a hardcoded WACC** under `region_integration.md` (“Hardcoded Rf / CRP / family % tables | Reject”) and `RESEARCH_AGENTS.md` §1.1 / §1.3 (“each company gets the model that fits”; Agent 5 writes the script). Agent 5 would import it, freeze the paste, and the “never hardcode” rule would be theater.

**v1 = `wacc_buildup.py` checker only.** Inputs: `valuation_model.wacc_buildup`, `assumptions.*`, `roic_identity.wacc`, `valuation_result.json` intermediates, reverse-engineering implied WACC when present, `market_inputs_snapshot` Rf. Outputs: PASS/FAIL/SKIPPED rows. No rate library.

### 3.2 False-FAIL surfaces

| Surface | Why it false-FAILs if v1 is sloppy | Hatch / skip |
|---|---|---|
| **Banks / insurance / REITs** | Excess-return / Ke / AFFO-NAV; industrial WACC object is the wrong native. Same as ROIC `applies:false` (`roic_identity.py` returns early on reason ≥40 chars). | `applies:false` + `native_analog` (`roe_vs_ke` / float-cost / NAV). **Bind:** if `model.name` is FCFF/WACC/DCF family, `applies` must be true — otherwise CMCSA writes a 40-char “hybrid media” skip. |
| **Japan / negative-rate** | JGB 10Y can sit below some coupons; some names issue through JGB. Kd < **local** Rf can be real. Kd < `^TNX` on a JPY model is a **currency** bug, not a Japan hatch. | `kd_below_rf_gate=negative_rate_market` with local Rf in snapshot. Rf in the identity = Ke’s Rf. |
| **Utilities** | Target `wd` often 50–70% (>0.35). YTM can sit close to Rf. `sector_utility.md` even shows WACC 5.37% in a worked example. Distressed tripwire must **not** fire on `wd>0.35` alone. | Tripwire is `wd>0.35` **AND** (gap>200 bp **OR** equity≤book). Fairly priced utility: gap small → no fire. YTM ≥ local Rf → Kd gate PASSes even if tight. Do not FAIL “WACC close to Rf.” FAIL WACC **≤** Rf on a going-concern (no free lunch). |
| **Net-cash tech** | Tiny `wd`; dummy Kd is unused. | Skip Kd-vs-Rf and Kd-source when `wd < 0.05` (or `we ≥ 0.95`). Still require arithmetic and `weight_policy`. |
| **IG industrial at book-ish leverage** | `wd=0.40` at fair value, implied gap small. | No tripwire. `current_market` legal. |

### 3.3 Gameable predicates (attack the draft)

1. **`kd_source=rf_plus_spread` with 0 bp.** Kd = Rf. FAIL 1 PASSes at equality. This is coupon-below-Rf **laundered** into a zero spread. **v1 add:** store `spread_bp` (signed). If `kd_source=rf_plus_spread` and `spread_bp < 50`, require `ig_floor_hatch` with an in-session rating/YTM — or FAIL. Do not hardcode 200 bp as the “right” spread.

2. **`kd_source=current_yield` that is the coupon.** Sep 7 already called 4.0% “~coupon/effective.” Enum change without a **numeric YTM field** + source path is paperwork. **v1:** `kd_ytm` number + `kd_evidence` path that `load_json` can see (snapshot, FDD footnote extract, LQ). Agent 13 grades substance; machine FAILs missing number/path.

3. **`current_yield_verified` hatch on FAIL 1** used to keep Kd < Rf. If YTM is truly below Rf, the hatch is for verified **market** YTM (Japan, or a structured floater), not for “FDD coupon 3.3%.” Machine: hatch legal only if `kd_source=current_yield` **and** `kd_ytm` is present **and** `kd_ytm >= kd_pretax - 5 bp` (they actually used the quoted yield). Coupon-below-Rf remains FAIL.

4. **`weight_policy=target` with target `wd` = trough `wd`.** Relabel. **v1:** when tripwire fires, require `wd_target` and `wd_current`; if `|wd_target − wd_current| < 0.02` and no `structural_leverage_hatch` with a **non-price** basis (mgmt target, rating-agency, indenture, peer book), FAIL. Structural-leverage hatch still cannot use coupon Kd.

5. **`weight_policy=blended` = 99% current.** Same as (4). Require blend weights that sum to 1 and `wd` used = the blend within 5 bp of weight.

6. **Blume toward 1 on a 0.3 beta / skip unlever.** Not a v1 FAIL (see 1.2). Document as residual so 2.41 does not “fix” it by mandating Blume.

7. **`applies:false` 40-char reason on an FCFF DCF.** Copy ROIC’s early return (`roic_identity.py` applies is False → PASS if reason ≥40). **v1 bind to model family.** Also: if `assumptions.wacc` exists and is used to discount FCFF, `applies` must be true regardless of sector label.

8. **Implied-gap rationale theater.** “Tape is cheap because franchise MoS vs 6% WACC; Kd 4% is the company’s coupon so weights are fine” — 40 chars, names Kd, still wrong. Machine cannot NLP this well. **Do not make FAIL 5 the kill shot.** Keep it as WARN unless the rationale is **only** the forbidden phrases (cheap/franchise/tape) with no Kd/weight tokens. Kd-source + tripwire do the work.

9. **Reverse-engineering path games.** Implied WACC is path-dependent. Agent 5 can invert a **bear** path to shrink the gap, or omit reverse-engineering. Agent 5 step 7 already requires reverse-engineering. **v1:** if `reverse_engineering.implied` has a WACC-like key, compute `implied_wacc_gap_bp`; if the object is missing on an FCFF DCF, FAIL like missing `conservatism_dials`. Do not FAIL a missing implied WACC on `applies:false` natives.

10. **Overfit to CMCSA numbers.** `wd > 0.35` and 200 bp are CMCSA-shaped (0.49 and ~299 bp). They are still reasonable **tripwires**, not rates. Do not add “Kd must exceed Rf by 150 bp” or “cable WACC ≥ 8%.” That is the July 25 pad, automated.

### 3.4 Interaction with existing gates (do not double-count)

- **ROIC 5 bp WACC match** stays. Draft FAIL 4 should reuse `WACC_EPS = 0.0005` and the same `assumptions.wacc` helper — one epsilon, two identities.
- **TV share >60% × Y8≥8%** stays; it did not catch Sep 7. Add the WARN in 1.2; do not overload `check_tv_share_duration` with a WACC floor.
- **`priced_for_perfection`:** Sep 7 correctly set false (tape cheaper than base). PFP does not catch a too-low WACC; it catches a too-high price. Do not overload PFP.
- **Legacy SKIPPED** like ROIC: missing `harness_version` / < 2.40.0 / object absent → SKIPPED; presence on an old stamp still validates. Do not rewrite CMCSA 2026-09-07 to make tests green (`eng/AGENTS.md` Hard constraint 1).

---

## 4. Load-bearing change — require / drop / add

Rank: **would it have caught Sep 7?** vs **false-FAIL on a healthy session?**

### Ship in 2.40 (one checker + prompt/schema; no rate table)

| Rank | Change | Catch Sep 7? | False-FAIL risk |
|---|---|---|---|
| **R1 Require** | `kd_source` ∈ {`current_yield`, `rf_plus_spread`}; coupon illegal as WACC input; **numeric** `kd_ytm` or `spread_bp` + in-session path | **Yes** (coupon 4.0% is the kill shot) | Low if utility/module coupon is reclassified as cross-check; Agent 5 already may not paste module numbers |
| **R2 Require** | `kd_pretax >= rf` unless named hatch; hatch pointers resolve; skip if `wd < 0.05` | **Yes** (4.0% < 4.784%) | Japan/utilities/net-cash covered by skip + hatches; **do not** use US 10Y as Rf for non-USD |
| **R3 Require** | Distressed tripwire: not **only** `current_market` when `wd>0.35` ∧ (gap>200 bp ∨ equity≤book); `target`/`blended` with `wd_target` ≠ trough without structural hatch | **Yes** (wd 49% and gap ~299 bp) | Utilities at fair value: gap small → no fire. Levered IG at book: no fire. Distressed value names **should** switch to target — that is the point, not a false FAIL |
| **R4 Require** | Arithmetic: WACC = `we×Ke+wd×Kd(1−t)` within 5 bp; `kd_aftertax = kd_pretax×(1−t)` within 5 bp; match `assumptions.wacc` and `roic_identity.wacc`; `we+wd≈1` | **No** (Sep 7 already matched) | Negligible — same class as existing ROIC WACC match |
| **R5 Require** | Prompt rewrite of `wacc_vs_buildup` + Pair 1 GOOD + Agent 13 `4-wacc`; keep dial for pads **above** a legal buildup | **Yes** (without this, R1–R3 get taught away as “match the buildup”) | Low if the rewrite is identity-language, not a 9% paste |
| **R6 Require** | `applies:true` bound to FCFF/WACC model family; `applies:false` only for non-WACC natives with reason + analog; version-band SKIPPED < 2.40 | Prevents skip-game | Banks/REITs already have this pattern on ROIC |
| **R7 Add (cheap)** | If reverse-engineering present and gap>200 bp: `wacc_gap_rationale` ≥40 chars **not only** cheap/franchise/tape; WARN if it ignores Kd/weights; **do not FAIL the tape** | Partial (Sep 7 rationale **was** “tape is cheap vs base”) | Low — documentation, not a rate |
| **R8 Add (cheap)** | WARN if TV share >60% **and** gap>200 bp while `terminal_consistency.response` does not name CoC/Kd/weights | Partial (Sep 7 TV 70%, Y8 1.8% PASSed the old TV gate) | Low if WARN not FAIL; Japan/utilities with small gap stay quiet |

### Drop from 2.40 (later wave or never)

| Drop | Why |
|---|---|
| Shared WACC **calculator** / default ERP / default spread in `packages/` | Hardcoded CoC; fights §1.1 / §1.3 / region_integration P4 |
| Mandated `beta_policy=blume` or `unlever_relever_target` | False-high Ke on 0.3 betas; Hamada is real process but not the Sep 7 kill shot |
| Dual-class Ke ≠ 0 machine FAIL | Misreads “no hardcoded family discount”; 0 with reject is legal |
| `wacc_minus_g` floor or “WACC must exceed Rf by X bp” as FAIL | Japan, utilities; becomes a rate table |
| FAIL 5 as a hard FAIL on the tape | Reverse-engineered WACC is path-dependent; would overfit CMCSA’s 9.13% |
| Rewriting CMCSA 2026-09-07 (or any completed session) so the new gate looks green | Immutable archive; test with fixtures under `eng/fixtures/` |

### Later wave (2.41+) — real process, not this incident’s blocker

- Leases-in-weights must match `roic_identity.leases`.
- Preferred / hybrids as `wp`, `kp`.
- Unlever/relever at **target** weights (Hamada) as an allowed `beta_policy` with a checker that the relevered beta is the Ke beta — still not mandated.
- Snapshot stores ERP **candidates**; Agent 5 selects `erp_method`.
- Structured `ke_sleeves[]` (ops / size / governance) with use/reject, parallel to hooks — documentation, not a size cap.
- `structural_leverage_hatch` peer/book evidence if target ≈ current after a tripwire.

### What I would not require even later

- A taught WACC (9%, utility 7%, cable 8%). July 25’s +345 bp was the other failure mode.
- Agent 13 recomputing WACC.
- Making `franchise_mos` illegal whenever implied WACC > model WACC (that **is** FAIL-the-tape).

---

## Gate-predicate sketch (checker, for implementers)

Mirror `check_roic_identity`: `WACC_SINCE = (2, 40, 0)`; object absent on old stamp → SKIPPED; new runtime without object → FAIL; `applies is False` → reason ≥40 + analog + **model family is not FCFF/WACC** else FAIL; then rehydrate floats from `wacc_buildup` and cross-check assumptions / result intermediates / `roic_identity.wacc`.

Do **not** parse `valuation.py`. Coupon hardcodes will keep living there until the JSON identity forbids them.

`rf` in the identity must equal snapshot/assumption Rf used in Ke (5 bp). That single equality prevents “Japan hatch vs `^TNX`” theater.

---

## Process bottom line

Sep 7 is not a missing 9% WACC. It is a **legal-looking identity on illegal ingredients**: coupon Kd below the same Rf that built Ke, trough `wd` in a going-concern Gordon with `wacc_minus_g` ≈ 4%, TV ≈ 70%, and a conservatism dial that **rewarded** matching that mix. ROIC then licensed `franchise_mos` because the hurdle was the mix.

2.40 should fail **impossible ingredients** the way Street identity fails `|delta|>5%` and ROIC fails franchise-on-below. It should not author a rate. If the prompt still says “match the buildup” without “legal Kd and legal weights,” the next Agent 5 will print 6% again and the checker will PASS.
)
