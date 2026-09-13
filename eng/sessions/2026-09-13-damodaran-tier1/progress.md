# Eng session 2026-09-13-damodaran-tier1

- Created: 2026-09-13T06:59:11Z
- Work type: W1
- Goal: Tier-1 Damodaran integration: ref wiring, buyer/option router branches, mandatory life-cycle+truncation, market-neutral inputs + per-share bridge

## Log

- 2026-09-13T06:59:11Z scaffolded
- Baseline `eng_verify` was RED: 8 pre-existing Windows-locale failures (UTF-8 schema/law files read with the GBK codec). Root cause in shared loaders (`check_core.py`, `consumption.py`, `phase_status.py`, `provenance.py`) and four tests calling `read_text()` with no encoding. Normalized those to `encoding="utf-8"`; the four test files now pass (45 passed).
- Implemented Tier-1 as harness **3.3.0** (all new gates gated `TIER1_SINCE = (3,3,0)` so stamped history stays green):
  - Router (`harness/modules/valuation_router.md`): added the buyer question and two primary ids `contingent_claim` / `asset_based`; added a ref-recipe table (each playbook/overlay -> the `ref/Investment Valuation/` file to open). Agent 5 prompt now opens that ref file.
  - Gates (`packages/kd_research/damodaran_gates.py`): `_check_lifecycle_stage`, `_check_buyer_identity`, `_check_market_contest`, `_check_option_screens` (incl. distressed-call replaces equity), `_check_truncation_assessed`, `_check_market_neutral` (erp/beta/currency), `_check_per_share_bridge`. `_allowed_playbooks` admits the two extra ids only at >= 3.3.0.
  - Schemas: `narrative_bind.schema.json` (life_cycle_stage/who_leads/stage_fit/buyer/market_contest/option_screens/distressed_call + overlays) and `valuation_model.schema.json` (`per_share_bridge` + `wacc_buildup` erp/beta/currency fields).
  - Prompt: Agent 5 step 1b (market contest + hostile review) and new-field self-check; Agent 13 band `4-tier1`.
  - Law: `RESEARCH_AGENTS.md` §10g; `valuation_checks.md` bullets; `law_history.md` 3.3.0 band; `HARNESS_MAP.md` identity line.
  - `harness/VERSION` -> 3.3.0; `python scripts/publish_harness_release.py` -> `pins/3.3.0/`.
- ARCHITECTURE.md: updated the one-valuer note (the value slot may now be an option for `contingent_claim` or an asset-based floor for `asset_based`).
- Verification: `pytest packages/kd_research/tests scripts/tests` 619 passed; `python scripts/eng_verify.py` PASS (1156 tests at Tier-1 time; 1162 after the reshape below) incl. version-bump + pin check.
- Not committed: awaiting explicit user agreement.

## Strategic-design-review reshape (same change set, still 3.3.0)

`/strategic-design-review` returned Direction `mixed` / Do `reshape`. Applied the three candidates marked `this change`:
- **Unbypassable gates.** `wacc_buildup.erp_method`/`beta_method = not_applicable` now FAIL while `applies=true`. Buyer: a private/undiversified buyer needs a numeric `illiquidity_discount > 0`; a diversified public buyer must state numeric `illiquidity_discount = 0` (a prose string no longer passes); `vc_pe` needs `ke_stepdown`. This closes the "pick the exempt enum value" loophole.
- **Ref wiring completed + machine-checked.** `valuation_router.md` ref table now has one row per primary id and per overlay (adds `asset_based`, `asset_based_floor`, `private_buyer`, `macro_neutral`, `value_enhancement`, `growth_assets`, `distressed`). New test `ValuationRouterRefRecipeTests` asserts every id has a ref row and each named `knowledge-hub*` path exists.
- **Typed bind schema.** `narrative_bind.schema.json` now types `life_cycle_stage`/`who_leads` (enums), `stage_fit` (minLength), `buyer`, `market_contest`, `option_screens`, `distressed_call` with properties/required/const instead of untyped stubs.
- Docs updated to match (valuation_checks, RESEARCH_AGENTS §10g, Agent 5 note). Pin refreshed; `eng_verify` PASS (1162 tests).

Deferred (reviewer marked `later`): wrong-stage veto that constrains the engine (positive terminal g on young/idea, perpetual growth on decline); apply market-neutral discipline to cost-of-equity builds, not only firm WACC.

## Follow-ups (Tier 2/3, not in this bump)

- Whole-firm risk ledger (one risk in one slot across CF / discount rate / stress book).
- Consistency-identity suite (FCFE<->FCFF, WACC<->APV w/ bankruptcy costs, DDM-vs-FCFE control gap, terminal reset beyond g, tax marginal/NOL).
- Double-count catalog coverage for the operating-model pairs (R&D, leases, SBC, cash+NCI, control/synergy).
- Bias pre-commitment artifact; user/client classification and output matching; staleness expiry.
- Firm-type repair engines (intangibles, EM, SOTP/users, mature-control, decline).
