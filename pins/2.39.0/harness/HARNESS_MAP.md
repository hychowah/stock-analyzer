# Stock-Research Harness Map

**Purpose of this system:** investment-decision research — decision-grade fair value, risks, timing, and provenance.  
**North star for agents:** leave artifacts the **next** phase can use without re-guessing numbers or missing material risks.  
**Not the goal:** token thrift or shorter runs for their own sake.

**Mode A (this map):** equity research pipeline → writes `archive/research/`.  
**Mode B (product eng):** `eng/AGENTS.md` + `eng/HARNESS_MAP.md` — features/UI/catalog API; immutable `archive/research` + `archive/outcomes`; may **append** `archive/library/`.  
Catalog read API: `packages/catalog_api` (`python3 -m packages.catalog_api health`).

Normative rules: **`harness/RESEARCH_AGENTS.md`** (Mode A full law). Root `AGENTS.md` is dual-mode **router only**. Subagent templates: `harness/agent_prompts.md`. Pipeline design: `harness/design_phase_status_and_exemplars.md`. Industry research notes: `harness/research/`.

---

## 1. Session layout

```text
archive/
  library/<TICKER>/   # reusable filings/transcripts (harness/library.md) — not a session
  research/<TICKER>/<YYYY-MM-DD>/
    reports/   README + fundamental + technical
    data/      financials, prices, valuation_model.json, compute/, raw_sec/, transcripts/
    charts/
    registry/  configs, evidence JSON, phase_status, handoffs/, raw/, library_bind.json
    meta/      run_manifest, prediction_snapshot
```

**Ticker check:** `python3 scripts/verify_ticker.py --ticker T` then scaffold writes typed `ticker` with `quote_symbol` null. Live quote **or** Yahoo search listings → ok (typed folder). No quote and no listings → abort. Orchestrator confirms the listing with tools, stamps `quote_symbol`, then `scripts/verify_listing.py`, then `bind_library.py` **before** `sector_config`. Specialists and outcomes read the stamp only (no ticker fallback).

Scaffold: `python3 scripts/scaffold_session.py --ticker T --date YYYY-MM-DD --orchestrator-model <id>`  
→ folder `archive/research/T/<SESSION_KEY>/` where `SESSION_KEY` is `YYYY-MM-DD` or auto `YYYY-MM-DD__r2` if that day already has a run (`--slug` for named runs).

**Harness identity (every run):** `harness/VERSION` → `harness_version` + `harness_spec`; git → `harness_git_sha` / `harness_dirty` (or `PIN.json` `copied_from_sha` on a published pin). **Stamped at scaffold only.** Finalize **copies** those fields into `meta/run_manifest.json` and snapshot `provenance` — it does not recapture from live git / `harness/VERSION`. Never leave them null on a new run.  

**LLM identity (every new run):** `--orchestrator-model` (required) + optional `--subagent-model` → `run_manifest.orchestrator_model` / `default_subagent_model` at **scaffold only**. Preflight FAILs without it. Do not backfill from chat memory after Phase 0+.  

**Isolation:** same session agents share `S/`. New run: **do not** open other `session_key`s first (`registry/session_isolation.json`). Resume only if user names the folder. Document library: bind into `S` from `archive/library/<T>/` **before classify**; do not mine the live library (except 2b unlabeled). See `harness/library.md`.  

**Git (Mode A, light):** Prefer a clean tree at **finalize** so stamped `harness_git_sha` is meaningful (`harness_dirty=false`). Mid-phase WIP may stay uncommitted; durable resume is `registry/phase_status.json` + handoffs, not chat. **Never `git commit` without explicit user agreement** (same bar as Mode B). Optional post-finalize commit only if the user asks. Coding/product commits: **`eng/AGENTS.md` Git discipline**.

---

## 2. Phase graph → handoff promise

| Phase | Agents | Must produce (evidence) | Next phase needs |
|-------|--------|-------------------------|------------------|
| **orch** | main | `sector_config.json`, `market_context.json`, `research_brief.json` (new sessions) | Scope, sector model family, intensity, investment questions. **§5 identity; modules advisory** (detection lists do not classify). |
| **0** | background swarm | `background.json`, `raw/phase0_*.json`, handoff | Valuation/risk themes; `risk_candidate` list; brief coverage gaps |
| **1_parallel** | 2a, 2b, 2c | financials CSV, `street_estimates.json`, orchestrator `library_bind.json` then 2b `sec_filings` + `raw_sec/` + index + `data_fetch_log.freshness`, `news_sentiment`, handoffs | Actuals, primary text, catalysts |
| **1b** | 2d | `latest_quarter.json` + evidence_log | Overrides input for Agent 5; risks for 2.5 |
| **1c** | year-readers + 2e merger | `raw/fdd_year_*.json` (new runtime) + excerpt check + `filing_deep_dive.json` (+ transcripts if any) | Footnotes, strategy_arc, scorecard for valuation hooks |
| **1d** | 1d_rev ∥ 1d_ind ∥ 1d_ol then 1d_merge | `raw/oppath_*.json` + `operating_path_brief.json` (after Phase 0 + 1b + 1c) | Growth/industry/leverage facts + conflict map for Agent 5 |
| **2_parallel** | 4, 5, 12 | `technical.json`, `valuation_model.json`, `tsr_validation.json` | FV/MOS for reports & stress; levels for technical report |
| **2_5** | stress swarm | `risk_bridge.json`, ≥5 `raw/stress_*.json` | Risk lens, scenario probs, sizing input |
| **3** | 6 | `charts/*.png` (after 2.5) | Visuals for reports |
| **4_parallel** | 7, 8, 11 | three `reports/*.md` | Investor-readable package |
| **5** | 13 | `audit.json` verdict | Gate for “complete” |
| **done** | — | audit PASS (or waived in README) | Catalog snapshot |

**Dependency rule of thumb:** do not start **2** without 1b+1c+1d (1d also waits on Phase 0); do not start **3** or **4** without 2.5; do not claim **done** without audit PASS. `1_parallel` may overlap Phase 0.

**Specialist quality (machine + process):** specialists **must** be spawned (`spawn_subagent` + `registry/spawns.json`). Spawn failure **abandons** the session — the lead must not write specialist artifacts inline. Outcomes (hooks, isolation, handoffs, phase↔disk) still apply. Agent 5 stays **single-writer**. Do **not** fan out multi-valuer or parallel report-section authorship. Agent 4 must not read/cite fundamental artifacts (including `library_bind` / live library). When FDD exists, valuation must log `filing_deep_dive_hooks`. When `operating_path_brief.json` exists, valuation must log `operating_path_hooks` (not all `noted_only`). When `street_estimates.json` exists, Agent 5 logs `street_bind` / `street_hooks`. Street FY+1 is the **default** Y1 start (`street_baseline`; |delta|>5% FAIL); `independent_y1` needs a resolved evidence gate; destock-in-base is legal only when `destock_this_print`. Current Street/Y1/destock: `RESEARCH_AGENTS.md` §10c. Historical bands: `harness/law_history.md`. Agent 5 writes `roic_identity` (same-script NOPAT/IC vs WACC; legal exits; cheap_claim) — Agent 12 stays parallel. `check_session --full` runs decision-quality gates (template masses, named-dial PFP, `decision_usefulness` on wide cones, ROC-vs-cheap_claim, F21 identity, branded-CPG-not-growth). Agent 5 writes `registry/decision.json` (`pass` is legal; `initiate` blocked on a useless cone) and Agent 4 may emit `side=pass`. Update mode needs a facts-only changelog (no prior FV). Mid-cycle construction is required; last-year/peak SOI cannot license `franchise_mos` / `above_wacc`. Duration verb is provisional in Phase 2; the orchestrator lead reopens `decision.json` after 2.5 (do not spawn `5` in `2_5`). Material stress (haircut≥25% and p≥0.15) forbids `initiate`/`add` via `decision.stress_bind`. Bind library before classify; Phase 0 is 3 rounds (4 if deep); `1_parallel` may overlap Phase 0; 1d still waits on Phase 0. Phase 2 stays parallel; ROC vs franchise_mos joins on `decision.roc_screen_rebuttal` at 5b. Latest-quarter `cash_quality` is required gather. README leads with `duration.action` before FV/MoS. Growth-module decay/TAM-penetration is not a paste path; low classification confidence does not force `standard`. Audit PASS is process completeness, not a buy list. Catalog projects `decision_action` and kill triggers.

---

## 3. If X is missing, do not start Y

| Missing / broken | Do not start | Fix first |
|------------------|--------------|-----------|
| Ticker not a real market quote and Yahoo search has no listings | scaffold / Phase 0 | Abort; do not invent a company |
| Typed ticker has no live quote but Yahoo search has listings | classification / Phase 0 | Scaffold the typed folder; stamp `quote_symbol` then `verify_listing.py` then `bind_library.py` before classify |
| `library_bind.json` | classify / 1_parallel / 2b | Orchestrator `bind_library.py` after listing stamp (never a finished session) |
| `sector_config` or `market_context` | Phase 0 / 1 | Orchestrator classification (after bind) |
| `research_brief` (new sessions) | Phase 0 fan-out | Write brief after classification |
| `sp_financials.csv` or `sec_filings` / raw_sec | 1b / 1c / 2 | Agents 2a / 2b |
| `filing_index.json` / `ir_listing.json` + `data_fetch_log.freshness` | 1_parallel complete | Agent 2b (fetch only `session_missing[]`) |
| `latest_quarter` or `filing_deep_dive` | Phase 2 valuation | 2d / 1c (year-readers + 2e) |
| `operating_path_brief` | Agent 5 | 1d workers + 1d_merge (after Phase 0) |
| `street_estimates.json` | Agent 5 bind | Agent 2a fetch (or explicit fetch-fail + widen range) |
| `valuation_model.json` | 2.5, 3, 4 | Agent 5 |
| `risk_bridge` or technical / tsr | Phase 4 reports | 2.5 / 4 / 12 |
| Three reports | Phase 5 | Agents 7 / 8 / 11 |
| `registry/abandon.json` | any later phase / finalize | Terminal — scaffold a new `session_key`; **never** inline |
| Specialist artifacts without a returned `registry/spawns.json` row | phase complete / next phase / finalize | `record_spawn.py` + `spawn_subagent`; **never** write those artifacts as the lead |

**Mechanical preflight (phase graph + evidence):**

```bash
python3 scripts/preflight_phase.py --ticker T --date D --phase 2_parallel
python3 scripts/preflight_phase.py --ticker T --date D --phase 2_parallel --subagent 5
python3 scripts/preflight_phase.py --ticker T --date D --phase 1c --mode complete
python3 scripts/preflight_phase.py --ticker T --date D --phase 1d
python3 scripts/preflight_phase.py --ticker T --date D --phase 1d --mode complete
python3 scripts/preflight_phase.py --ticker T --date D --phase 2_5
python3 scripts/preflight_phase.py --ticker T --date D --phase 4_parallel
python3 scripts/preflight_phase.py --ticker T --date D --phase 5
```

- **Orchestrator** = lead; **subagent** = specialist on the phase graph (ids: 2a, 5, 13, …).  
- Preflight checks **prior phases complete** and optional **`--subagent` belongs to `--phase`**.  
- Orchestrator **MUST** preflight before starting a phase / spawning its subagents. FAIL → fix upstream; do not invent.

---

## 4. Intensity & research depth (investment complexity)

| Signals | Depth | Behavior |
|---------|-------|----------|
| intensity `low`, confidence ≥0.70, widely held US GAAP | `standard` | Full quality gates; region hooks may be `noted_only` |
| intensity `medium`, multi-currency, local filings | `deep` | Ownership/FX/local CoC in Phase 0 + 2e + valuation hooks; stress region if material |
| intensity `high`, family/SOE/VIE, confidence &lt;0.70, thin disclosure | `deep` + **widen FV range** | Mandatory control/related-party work; ≥1 region/gov stress; `requires_manual_review` as warranted |

Set `research_depth` on `registry/research_brief.json`. Depth **adds** research on hard names; it never strips deep dive, ≥5 stress scenarios, or audit.

---

## 5. Decision-grade returns (agent → next agent)

1. **Artifact on disk** is the product; chat is disposable.  
2. Swarm JSON: specific findings + sources + `downstream_relevance` (Phase 0) / grounded haircuts (2.5).  
3. Handoff section 4: top 3 miss-nots, range wideners, paths.  
4. Full filings live in `data/raw_sec/` — not in return JSON.  
5. Numbers in reports come from registry/compute only.

Details: `harness/agent_prompts.md` conventions + `harness/exemplars/`.

---

## 6. Where things live

| Need | Path |
|------|------|
| Normative research law | `harness/RESEARCH_AGENTS.md` |
| Dual-mode router | root `AGENTS.md` |
| Orchestrator checklist | `harness/orchestrator_runbook.md` |
| Prompt templates | `harness/agent_prompts.md` |
| Schemas | `harness/schemas/*.schema.json` |
| Structural check | `scripts/check_session.py --full` |
| Phase preflight | `scripts/preflight_phase.py` |
| Session acceptance | `check_session.py --full --write-acceptance` |
| Sector methodology | `harness/modules/sector_*.md` (advisory) |
| Region methodology | `harness/modules/region_*.md` (advisory) |
| Filing deep-dive method | `harness/filing_deep_dive.md` |
| Ticker document library | `harness/library.md` |
| Resume map design | `harness/design_phase_status_and_exemplars.md` |
| Judgment exemplars | `harness/exemplars/` |

---

## 7. Session complete?

1. `registry/audit.json` → `verdict: PASS` (or README waivers)  
2. `python3 scripts/check_session.py --ticker T --date D --full` green  
3. Optional: `--write-acceptance registry/session_acceptance.json` for a machine checklist  

Then: `build_prediction_snapshot.py` + `rebuild_catalog.py`.
