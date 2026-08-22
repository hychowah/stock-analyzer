# Wave 1 plan — enforce existing investment law (harness 2.9.0)

Mode B **W1** (research runtime). Branch: `harness/investment-quality-waves`.
IDs: **A1–A8, A10, D1, D3, G2–G4**.

## Goal

Make the **already-written** decision-quality law mechanically fail on **new-runtime** sessions. Do not invent Wave 2 decision objects or Wave 3 destock/update mode. Do not rewrite `archive/research/**` or `archive/outcomes/**`.

## Alignment (Mode B + harness/research)

| Constraint | How this wave honors it |
|---|---|
| `eng/AGENTS.md` W1 | pytest on shipped gates + `eng_verify`; bump `harness/VERSION` in the same change set |
| Write allowlist | `harness/`, `templates/`, `scripts/`, `packages/`, `apps/`, `eng/` |
| Immutable archive | tests use **synthetic temp sessions**; no production session rewrite |
| No FV invention in Mode B | gates check **shape/identity**, never compute a fair value |
| Progressive disclosure (`harness/research` 2.1) | slice Agent 5/7/11/12/13 prompts; **do not** dump this plan into root `AGENTS.md` |
| Decision-grade artifacts (2.2) | snapshot/catalog must project PFP, DU, cheap_claim that already live on disk |
| Numeric rehydration (2.4) | README MoS still from registry; A10 is a **disclaimer line**, not a new number |
| Isolation F14/F16 | Wave 1 does **not** open prior FV; changelog is Wave 3 |
| H9 git | one verified commit on this branch after Wave 1 verify; no push |

## What already exists (do not re-implement)

- Missing `roic_identity` on harness ≥ 2.8.0 already **FAIL** (`scripts/kd_research/roic_identity.py`).
- `franchise_mos` already **FAIL** when `quality_bucket` is below/approx WACC.
- Missing `cheap_claim.class` already **FAIL** when `applies:true`.
- MoS dual-unit and probability-sum gates exist (`gates.py`).
- Thin `roic_identity` already projected into snapshot **if** the object exists.

## Gaps this wave closes

### A1 — cheap_claim / roic_identity on new runtime
- Keep omit-FAIL at ≥ 2.8.0 (already).
- **README / Agent 11:** if `roic_identity` exists, cheap_claim class **must appear next to MoS**; if class ≠ `franchise_mos`, do **not** lead with MoS as a franchise gift (prompt already says this — make Agent 13 Band 3 **major** when README leads with MoS while cheap_claim is not franchise_mos).
- `applies:false` (banks/REIT/pre-profit) **cannot** be used as a franchise-MoS headline either (prompt + README check via cheap_claim absence → no franchise language). Machine: if README/value table implies franchise cheapness without `cheap_claim=franchise_mos`, that is Agent 13 — Wave 1 machine gate is: **new-runtime valuation with applies:true missing cheap_claim FAIL** (already) and **Agent 12 ROC fail + franchise_mos FAIL** (A2).

### A2 — Agent 12 ROC screen vs franchise_mos (unique 2.9.0 bar)
Do **not** re-FAIL `franchise_mos` on below/approx (that is 2.8.0 ROIC).
- TSR `roc_vs_cost_of_capital=fail` **and** `cheap_claim=franchise_mos` **and** `quality_bucket=above_wacc` → **WARN** unless `roc_screen_rebuttal` ≥40 chars.
- Below/approx + franchise_mos: A2 PASSes (ROIC FAILs).
- Missing TSR / no identity: SKIPPED.

### A3 — template scenario masses
Extend valuation-side probability check (fair_value.scenario_probabilities **or** assumptions.scenario_probabilities):
- Masses rounding to `(0.30, 0.45, 0.25)` or `(0.25, 0.50, 0.25)` **FAIL** unless:
  - `fair_value.probability_method` (or assumptions sibling) is a non-empty string **and**
  - a **numeric counterfactual** appears (regex: another triple of 0–1 masses, or explicit “if X then bear=…” with a number ≠ the template).
- Machine only on **new runtime ≥ 2.9.0** so 2.8.0 sessions are not retroactively FAIL for this new bar (archive immutability). `check_session` SKIPPED below 2.9.0.

### A4 — priced_for_perfection not mechanical
- Extract PFP from `reverse_engineering.priced_for_perfection` **or** top-level (today `session_extract` only reads top-level → catalog **null**).
- Gate: if PFP is boolean, rationale must name at least one **dial** (`wacc`, `g`, `om`, `margin`, `growth`, `multiple`, `terminal`, `rotce`, `ke`) and must **not** be only `price > base` / `price > PW` / `price < bull`.
- New runtime ≥ 2.9.0; missing reverse_engineering SKIPPED if PFP absent.

### A5 — wide cone requires decision_usefulness
- If `(bull−bear)/base > 1.0` or `bear < 0.4 × base` (base > 0): `fair_value.decision_usefulness` required in `{high,medium,low}`.
- ≥ 2.9.0 FAIL; older SKIPPED.

### A6 — F21 branded staple as cyclical (machine FAIL)
New `check_sector_identity_tripwire(session)`:
- `primary_sector == cyclical` **and** sector_config JSON (signals/rationale/gics/yfinance) matches Consumer Defensive / Consumer Staples / Farm Products **and** branded/retail/CPG language **and** no majority spot / posted-price / unbranded evidence → **FAIL**.
- Agent 13 prompt: tripwire is **major**, not passable `sector_fit`.
- Do **not** classify in Mode B; only FAIL a forbidden combination already on disk.

### A7 — branded consumer must not be `primary_sector=growth`
Mode B does **not** classify from FCF/OM.
- FAIL only if `primary_sector==growth` **and** sector_config already contains branded consumer / CPG / staples / farm-products language.
- Missing staple language → SKIPPED (SaaS/path-to-profit growth stays legal).

### A8 — snapshot/catalog project PFP, DU, cheap_claim
- `session_extract`: PFP from `reverse_engineering`; `decision_usefulness` from `fair_value`; cheap_claim already in thin ROIC.
- `build_prediction_snapshot` + `export_compare_db` + schema: persist `decision_usefulness` (new optional column/field; missing on old rows OK).
- `key_risks`: coerce to **plain strings** only (G4) — never `str(dict)`.

### A10 — Audit PASS is not investable
- Agent 11 README: required one-liner that audit PASS = process completeness, **not** a buy.
- Agent 13: major if README leads with Audit PASS as the investment sentence.
- Optional light machine: if README exists and contains `Audit` + `PASS` but lacks the completeness disclaimer phrase → WARN (FAIL would break every live README; Wave 1 does not rewrite archive). New-runtime sessions: WARN in check_session; prompt is the load-bearing fix.

### D1 — 1d/1w MoS-sign is not overall skill
- `mechanical_scorecard`: `overall_label` comes **only** from `horizon_primary` (default 3m). If 3m is pending/unavailable → `too_early`. **Never** fold 1d/1w `correct`/`incorrect` into overall.
- Keep 1d/1w `direction_vs_price` metrics as **tape hygiene** with rule text that they are not the skill label.

### D3 — `inside` ineligible when span >100%
- If `(fv_bull−fv_bear)/fv_base > 1.0`, `fv_band_at_mark` value is `ineligible` (not `inside`), with rationale.

### G2 — PASS is not a buy-list default
- `CatalogApi.calibration(pass_only=False)` default.
- `/calibration` page default `pass_only=0`.
- Portfolio already defaults false; keep it. Label in UI: “audit PASS filter (process completeness, not a buy list)”.

### G3 — null-FV rows quarantined from comparable rankings
- `list_runs` / ranking helpers: `comparable=false` (or exclude by default) when `fv_base` is null.
- Optional query flag `include_incomplete=true` to see them.
- Do not delete rows from sqlite.

## Files (expected)

- `harness/VERSION` → **2.9.0**
- `harness/RESEARCH_AGENTS.md` §10d/§13 gates table (2.9.0 rows)
- `harness/HARNESS_MAP.md` specialist-quality line
- `harness/agent_prompts.md` Agents 5, 7, 11, 12, 13 (sliced)
- `templates/prediction_snapshot.schema.json`, maybe `valuation_model.schema.json` (DU already there)
- `scripts/kd_research/gates.py` (or new `decision_quality.py` imported by gates/check_session)
- `scripts/kd_research/session_extract.py`, `outcomes.py`
- `scripts/build_prediction_snapshot.py`, `export_compare_db.py`, `compare_db.py` if a column is needed
- `packages/catalog_api/client.py`, `apps/analysis_web/routes/pages.py` + calibration template label
- `scripts/tests/test_wave1_decision_quality.py` (and extend test_roic, test_archive_paths, test_portfolio, test_catalog_api)
- `eng/eval/failure_catalog.md` F21/F22 status + F23 template-mass / F24 PFP-mechanical / F25 wide-cone-no-DU / F26 calibration-pass-default if we add rows
- this session `progress.md`

## Tests (synthetic only)

Drive **shipped** functions:

1. 2.8.0 omit `roic_identity` → FAIL; missing version → SKIPPED (existing).
2. TSR ROC fail + franchise_mos without above_wacc → FAIL; with above_wacc rebuttal → PASS.
3. 30/45/25 no method → FAIL on 2.9.0; SKIPPED on 2.8.0; with method+counterfactual → PASS.
4. PFP true + “price > base” only → FAIL; named WACC dial → PASS; extract from `reverse_engineering`.
5. bull 200 / bear 0 / base 50 without DU → FAIL; with `low` → PASS.
6. cyclical + Consumer Defensive + branded, no spot → FAIL; unbranded posted-price → PASS.
7. growth + two profitable signals → FAIL; growth + negative FCF path-to-profit → PASS.
8. Snapshot bundle has PFP/DU/cheap_claim; key_risks all `str`.
9. Scorecard overall too_early when only 1d is correct; 3m correct → mostly_right.
10. Wide band → `ineligible` not `inside`.
11. `calibration()` default pass_only is False; null fv_base excluded from comparable list.

## Non-goals this wave

Wave 2 decision.json / technical pass. Wave 3 destock/update. NLP grading of stacking_justification. Archive rewrites. git push.
