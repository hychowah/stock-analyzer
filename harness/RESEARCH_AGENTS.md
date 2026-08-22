# Mode A — Research Harness Spec (v2)

**This file is the full normative law for equity research (Mode A).**  
Root `AGENTS.md` is only a dual-mode **router** — agents must load **this file** before Phase 0.  
Subagent templates: `harness/agent_prompts.md`. One-page map: `harness/HARNESS_MAP.md`.  
Product eng (Mode B): `eng/AGENTS.md` — do not mix with research phases.

**Product purpose:** better **investment decisions** via decision-grade fair value, risks, timing, and provenance — not token thrift. Optimize **agent → next-phase** value transfer (usable artifacts, no lost risks, no invented numbers).

**Data plane:** write new sessions under `archive/research/<TICKER>/<SESSION_KEY>/`. Never overwrite completed sessions. Catalog/outcomes are projections.

### Quick map (read this first)

| Need | Where |
|------|--------|
| One-page pipeline + “if X missing don’t start Y” | `harness/HARNESS_MAP.md` |
| Subagent prompts | `harness/agent_prompts.md` |
| Phase preflight (evidence before valuation/reports) | `scripts/preflight_phase.py` |
| Structural session check | `scripts/check_session.py --full` |
| Schemas | `templates/*.schema.json` |
| Sector / region methodology (advisory) | `sector_*.md`, `region_*.md` |
| Filing deep-dive method | `harness/filing_deep_dive.md` |
| Judgment exemplars | `harness/exemplars/` |
| Industry research notes | `harness/research/` |

**Orchestrator order (new sessions):** scaffold → classify sector + market_context → write `registry/research_brief.json` → Phase 0… → **preflight** before Phase 2 / 2.5 / 4 / 5 → audit → prediction snapshot + catalog. Checklist: `harness/orchestrator_runbook.md` (includes `data/price_snapshot.json` freeze before Phase 2).

Also: `harness/region_integration.md`, `scripts/` helpers, `_archive/` (retired v1 — never follow).

## 1. Design principles

1. **LLM judges, code fetches.** Sector classification, valuation model choice, discount rates, growth/margin paths, multiples, scenario probabilities, stress haircuts, position sizing — all are agent decisions made with reasoning. The harness contains **no fixed formulas, no hardcoded probabilities, no hardcoded multiples**.
2. **Every judgment number is justified.** Any number an agent decides (rather than reads from a source) must be recorded with a `rationale` (why this value) and a `basis`/`source` (what it rests on). This is the **justification contract** (§6) and it is enforced structurally and by the audit agent.
3. **Runtime compute scripts.** Math is done by small ad-hoc Python scripts the agent writes into `data/compute/` for that specific company, runs, and cites. Never do multi-step arithmetic in prose. Each company gets the model that fits it.
4. **Light schemas + LLM audit.** Schemas (`templates/`) enforce structure and provenance only — they do not attempt to validate financial truth. A Phase 5 audit agent cross-checks reports against registry data.
5. **English only** for normative text (spec, prompts, schemas, registry keys, reports).
6. **Decision-grade handoffs.** Each phase’s primary product is on-disk evidence the next specialist can use; handoffs state gaps that must widen uncertainty. Swarm returns are signal-dense and sourced — not raw filing dumps and not hollow schema-valid shells.

## 2. Session folder convention

Research sessions are **archived records** under `archive/research/` (not at the repo root). Layout plan: `harness/plan_research_archive_layout.md`.

```text
archive/
├── catalog/                 # runs_index.json, tickers_index.json (rebuildable)
├── outcomes/                # optional later: realized marks + scorecards (never edit research)
└── research/
    └── <TICKER>/<YYYY-MM-DD>/   # one folder per research session, never overwritten
        ├── reports/   00_<TICKER>_README.md, 01_<TICKER>_fundamental.md, 02_<TICKER>_technical.md
        ├── data/      raw + processed data; valuation_model.json; compute/; raw_sec/; transcripts/
        ├── charts/    PNGs with descriptive names
        ├── registry/  sector_config, market_context, research_brief, background, sec_filings,
        │              filing_deep_dive, news_sentiment, latest_quarter, technical, tsr_validation,
        │              risk_bridge, audit, data_fetch_log, phase_status  (all .json);
        │              raw/; handoffs/  (see §8)
        └── meta/      run_manifest.json; prediction_snapshot.json  (frozen claims for lookback)
```

Rules:

1. Ticker uppercase. Date from the `date` command (never let an agent compute it).
2. Scaffold with: `python3 scripts/scaffold_session.py --ticker <T> --date <D> --orchestrator-model <id>` — creates `archive/research/<T>/<SESSION_KEY>/`.  
   - **`session_date`** = as-of `YYYY-MM-DD` (economics / price freeze).  
   - **`session_key`** = unique folder: plain `YYYY-MM-DD` for the first run that day, then auto **`YYYY-MM-DD__r2`**, `__r3`, … if that folder is taken; or explicit `--slug`.  
   - **`--orchestrator-model` is required** (e.g. `grok-4.5`; or env `RESEARCH_ORCHESTRATOR_MODEL`). Stamped into `meta/run_manifest.json` at scaffold — **never invent or “remember” the model id after a long context**. Optional `--subagent-model` (defaults to orchestrator). Preflight / `check_session` FAIL if missing on active runs.  
   - Refuses to overwrite a non-empty folder (use a free key or `--force` only for broken scaffolds).
3. Re-research → **new `session_key`** (new date and/or `__rN` / slug). **Never rewrite** a completed session to “fix” history.
4. **Cross-session isolation (default for a NEW research run):**  
   - **Within the current session** agents share freely via `S/registry`, handoffs, and `S/data`.  
   - **Prior sessions** (other `session_key`s — yesterday, last week, earlier today) are **out of scope** unless the user explicitly says **resume** that folder or **compare after** this run.  
   - **Do not** open, list, or “check whether yesterday’s SOFI/META/… run is complete and usable” before scaffolding a new run. That is contamination and waste. Scaffold today’s `S`, then work only under `S`.  
   - Prior sessions must **not** supply FV, MoS, scenario probabilities, WACC, thesis text, or handoffs as inputs to any phase (not only Agent 5).  
   - Optional compare to a prior run is **post-audit / post-finalize only**, and only if the user asked. Policy: `registry/session_isolation.json` (scaffolded).  
5. After Phase 5 (audit): run `python3 scripts/finalize_session.py --ticker <T> --date <D_or_session_key>` (snapshot + compare SQLite + thin catalog). Finalize **always** stamps `harness_version` (from `harness/VERSION`) + `harness_git_sha` (+ dirty flag) into `meta/run_manifest.json` and `prediction_snapshot.provenance` — never leave these null. It **preserves** scaffold-time `orchestrator_model` / `default_subagent_model` into the compare DB (does not invent them). Use full `session_key` when the folder is `date__rN`.
6. Path resolution (`scripts/kd_research/paths.py`): prefer `archive/research/...`; fall back to legacy root `<TICKER>/<DATE>/` during migration only. **New-run orientation does not include browsing other session folders.**
7. Repo root holds harness code only (`harness/`, `scripts/`, `templates/`, sector/region modules, MCP packages) — not ticker session trees.

## 3. Required inputs

Confirm or infer before starting: ticker, company name, market region/exchange, reporting currency, regional benchmark index, 3–5 closest peers, latest fiscal quarter/filing date. Also establish **market/region context** (§5b): accounting basis, ownership/control hints, cost-of-capital flags, and `intensity`. Document inferences in `00_<TICKER>_README.md` and write `registry/market_context.json`.

**Investment research brief (new sessions):** after sector_config + market_context and **before Phase 0**, write `registry/research_brief.json` per `templates/research_brief.schema.json`: investment objective, `must_answer_questions`, peers, benchmarks, currency, `research_depth` (`standard`|`deep`) with rationale. Phase 0 maps findings to those questions; open questions feed valuation range width and/or Phase 2.5. Legacy sessions without a brief are OK (checks SKIPPED).

## 4. Data sources

| Layer | Tool | Use for |
|---|---|---|
| Primary fundamentals & SEC | `kimi-datasource` plugin (`sp_data`, `sec_edgar`, `yahoo_finance` sources) | Financial statements, estimates, filings |
| Local MCPs | `yfinance`, `sec-edgar`, `web-fetch` (wired in `.mcp.json`) | Prices/technicals, filing text fallback, page fetches |
| Web | WebSearch / FetchURL | News, sentiment, **earnings-call transcripts** (secondary to filings), investor materials |

Fallback rule: if a primary source is unavailable or errors, state the failure in the registry file, use the fallback source, and note the substitution. Never silently proceed on partial data — degraded data must widen the valuation range (§12). Transcripts are **secondary** for management-promise tracking: if none can be obtained, record `sources.transcripts` as missing/empty, set scorecard `data_quality` degraded, and widen uncertainty — never invent quotes.

## 5. Sector classification (agent judgment)

Run **once**, by the main agent, before anything else. There is **no scoring algorithm** — classify by reasoning over objective inputs. **Sector modules do not classify.** Any “Automatic Detection Logic,” scoring matrix, or “classified if ANY of” list in `sector_*.md` is a diagnostic hint **after** this judgment. If a module hint contradicts this section, **this section wins.**

1. Pull objective inputs: yfinance sector/industry, business description, revenue mix (latest 10-K), and which sector KPIs exist (NIM/CET1? FFO/AFFO? combined ratio? ARR/NRR? rate base? commodity exposure?).
2. Judge the primary sector: `banking | insurance | growth | reit | utility | cyclical | standard`. Meanings (heuristics, not a scorecard):
   - **banking** — loans/deposits/NII/regulatory capital are the identity.
   - **insurance** — underwriting, float, combined ratio / embedded value.
   - **reit** — FFO/NAV, property or mortgage pass-through.
   - **utility** — regulated rate base / allowed earnings.
   - **growth** — lead model is path-to-profit / SBC-dilution because that **is** the identity (typically negative-FCF tech/biotech). Profitable branded consumer names are usually `standard` with optional `is_also_growth`.
   - **cyclical** — **the cycle is the investment thesis** (mean-reverting earnings; peak multiples can be expensive). Judgment inputs (not a formula): a named cyclical sub-type or cousin (metals, E&P, steel, chemicals, fertilizers, shipping, semis, machinery, autos, airlines, unbranded posted-price protein/ag, cruise≈airlines/shipping, tires≈auto parts) **or** a majority of revenue **realized at** commodity spot / index / posted producer prices (`revenue ≈ volume × commodity price`).
   - **standard** — residual ordinary DCF. **Includes branded CPG / consumer staples / farm-products brands** whose household demand is not a GDP cycle.
3. **Demand staple vs supply shock stay split.** Households still buy eggs, coffee, chocolate, packaged meat in recessions → primary **standard** on the merits (not via the confidence fallback). HPAI, flock rebuild, oversupply, farm-gate feed, competitor price-gaps → Phase 2.5 / `research_brief.must_cover_risks`. That overlay does **not** switch the lead module to `sector_cyclical.md`.
4. Illustrative (no ticker exceptions): branded retail carton / list-promo eggs → `standard` + shock overlay; unbranded posted-price shell eggs → `cyclical`; cruise capacity / berth-days ≈ airlines/shipping → `cyclical` (a defensive GICS label is not “never cyclical”).
5. Classify from these meanings **first**. If you consult a module detection list, treat it as hints. If considering `cyclical` and no sub-type **or cousin** fits and revenue is not majority spot-realized, that is a strong veto. Then set `module_file` (`""` is valid for `standard`).
6. Write `registry/sector_config.json` per `templates/sector_config.schema.json`: `primary_sector`, self-assessed `confidence`, `signals` (the evidence), `rationale` (why this sector, why this confidence), `is_also_growth`, `module_file`, plus `runner_up` (second-best hypothesis + why rejected) and `disconfirming_signals` (evidence against the choice that was weighed). For genuinely borderline cases, run two independent classification passes and reconcile.
7. Confidence < 0.70 → use `standard`, set `requires_manual_review: true`, and say so prominently in the README. That fallback is for **uncertain** names, not for branded staples (those are `standard` on the merits).
8. If `is_also_growth`: primary sector's model still leads; add growth-module SBC/dilution analysis at critical intensity; extend the explicit forecast to 7–10 years.
9. Material commodity-input or protein-supply beta on a `standard` name **must** appear in `research_brief.must_cover_risks` / `must_answer_questions` so Agent 5 does not freeze a peak-year margin as mid-cycle.

## 5b. Market / region classification (agent judgment)

Run **once**, by the main agent, with sector classification (before Phase 0). There is **no scoring algorithm** and **no hardcoded** regional WACC, country ERP tables, or family-control discounts.

1. Pull objective inputs: exchange / listing venue(s), reporting currency, filing form type (10-K vs 20-F / HKEX / DART / other), yfinance country, quick ownership signals (widely held, dual-class, family, SOE, VIE headlines), and whether cash flows are multi-currency.
2. Judge `primary_region`: `us | hk_china | korea | japan | eu_uk | other` and `intensity`: `low | medium | high`.
3. Write `registry/market_context.json` per `templates/market_context.schema.json`: `primary_region`, `intensity`, self-assessed `confidence`, `signals`, `rationale`, `module_file` (`region_us.md` | `region_hk_china.md` | `region_generic.md` or a future dedicated module), `listing`, `accounting_regime`, `cost_of_capital_flags` (**flags only** — judged Rf/ERP/FX numbers belong in valuation assumptions), `ownership`, `requires_manual_review`, plus `runner_up` / `disconfirming_signals` when useful.
4. **Intensity gate (load-bearing):**
   - **low** — typical US widely-held, US GAAP, USD model: downstream may no-op with a single valuation `market_context_hooks` entry `noted_only`; do not invent country haircuts or mandatory regional stress.
   - **medium** — local rates/accounting/FX need explicit treatment; 2e ownership status enriched; regional stress expected when material.
   - **high** — family/SOE/VIE/pyramid/control, dual-list institutional risk, capital controls, or thin non-US disclosure: deep 2e ownership/related-party work; valuation must address local CoC + governance dials with hooks; Phase 2.5 includes ≥1 region/governance/FX scenario; widen range when data quality is degraded.
5. Confidence < 0.70 → set `requires_manual_review: true`, widen valuation range, and say so in the README — do **not** fake `primary_region=us` to avoid work.
6. Read the advisory module in `module_file` before valuation (same rule as sector modules: numbers are reference ranges, not mandates). Decision record: `harness/region_integration.md`.
7. **No always-on region agent** and **no Agent 2f** in the default graph. Ownership depth stays with Agent 2e; cost-of-capital judgment stays with Agent 5. A gated 2f may be considered later only if audits show systematic high-intensity misses.

## 6. The justification contract

Applies to every agent, every artifact:

- Any **decided** number (probability, WACC, growth rate, margin path, multiple, haircut, weight, entry/stop level, sizing) → `{value, rationale, basis}` in the registry JSON. `rationale` ≥ 1 real sentence; `basis` = data/source/reasoning it rests on.
- Any **sourced** number → cite the source (filing URL, tool, dataset).
- Reports must restate the key judgment numbers with their rationale — a reader must be able to see *why* without opening the JSON.
- Sector modules' numeric ranges are **advisory** (§9): deviating is allowed with rationale; copying a range default without thinking is not.
- `scripts/check_session.py` enforces non-empty `rationale` fields structurally; the Phase 5 audit agent enforces that rationales are substantive.

## 7. Runtime compute scripts

- Location: `SESSION_ROOT/data/compute/<descriptive_name>.py`. One script per model/task (e.g. `excess_return_jpm.py`, `technical_indicators.py`, `tsr_dilution.py`).
- The script reads inputs from the session's data/registry files (or embeds fetched values as constants with a comment citing their source), prints/writes a JSON result, and the agent records `compute_script` in the output artifact.
- Use the environment's `python3`. Use only installed libraries (check first; `yfinance-market-mcp/.venv` has yfinance/matplotlib/pandas).
- The script is part of the deliverable: it must be reproducible — rerunning it reproduces the artifact's numbers.
- **Hermetic rule**: fetched market/fundamental data must be snapshotted into `data/*.csv` at session time; scripts read the cached files and fetch live data only when the cache is absent. A rerun next month must produce the same numbers. Any rerun difference is data drift — investigate, never wave off as float noise.
- **Scripted intermediates**: any number used inside an assumption build-up (realized beta, historical CAGR, ERP inputs) must come from a script in `data/compute/`, never unscripted mental math.

## 8. Workflow

Subagent prompt templates for every phase are in `harness/agent_prompts.md`. Track phases with `TodoList` **and** `registry/phase_status.json` (durable resume map). Each subagent prompt must state its exact input paths, output paths, and the justification contract — subagents see only their prompt.

### Phase status resume map (orchestrator-only)

`scaffold_session.py` writes `registry/phase_status.json` (all phases/agents `pending`). **Only the orchestrator writes this file.** Subagents write artifacts + handoffs; the orchestrator flips status after each return.

**MUST:**

1. Own `registry/phase_status.json` as the **sole resume map** for the session.
2. After each agent finishes: update that agent row (`status`, `artifacts[]`, `handoff` path), then re-check the phase completeness gate before advancing.
3. On re-entry: read `phase_status.json` and `resume_hint` first; set `current_phase` to the first phase that is not `complete`/`skipped`; **do not re-run agents already `complete`** unless fixing an audit FAIL (then reset that agent to `pending` with a note).
4. Never set `phase.status = complete` if a required artifact path is missing on disk or a required handoff is missing/stub. For Phase 0 and 2.5, also pass merge/coverage preflight: `python3 scripts/preflight_phase.py --ticker T --date D --phase 0|2_5 --mode complete`.
5. Keep `resume_hint` as one plain-English sentence for the next shift; set `updated_at` from the `date` command (UTC ISO-8601).
6. Before starting Phase `2_parallel`, `2_5`, `4_parallel`, or `5`, run entry preflight: `python3 scripts/preflight_phase.py --ticker T --date D --phase <id>`. FAIL → fix upstream; do not invent evidence.

Statuses: `pending | in_progress | complete | failed | blocked | skipped`. Design + agent pre-fill: `harness/design_phase_status_and_exemplars.md`, schema `templates/phase_status.schema.json`. Legacy sessions without the file are OK (`check_session` → SKIPPED).

| Phase | Agents (subagent type) | Depends on | Writes (single writer) |
|---|---|---|---|
| Orchestrator | lead (not a phase subagent) | — | `registry/sector_config.json`, `registry/market_context.json`, `registry/research_brief.json` (new sessions), maintains `registry/phase_status.json`; **MUST** run `scripts/preflight_phase.py --phase … [--subagent …]` before entering a phase / spawning that subagent |
| 0 — Background | swarm × research rounds (`explore`) | sector_config, market_context, research_brief (when present) | main agent merges → `registry/background.json`; coverage vs brief + risk_candidates in handoff |
| 1 — Data (parallel) | 2a fundamentals, 2b SEC filings, 2c news & sentiment (`coder`) | sector_config, market_context | `data/sp_financials.csv` (+ peers), `registry/street_estimates.json` (2a; new runtime ≥ 2.7.0), `registry/sec_filings.json` + `data/raw_sec/` (+ multi-year annuals), `registry/news_sentiment.json` |
| 1b — Latest quarter | 2d integrator (`coder`) | 2a, 2b | `registry/latest_quarter.json` |
| 1c — Filing deep dive | year-readers (`coder`) then 2e merger (`coder`) | 2b (and 2a when actuals needed); reads market_context for ownership depth | `registry/raw/fdd_year_*.json` (new runtime) + excerpt-in-source; `registry/filing_deep_dive.json`; may add `data/transcripts/*` |
| 1d — Operating path | 1d_rev, 1d_ind, 1d_ol then 1d_merge (`coder`) | 1b + 1c (new runtime ≥ 2.6.0) | `registry/raw/oppath_*.json`; `registry/operating_path_brief.json` (single merger writer) |
| 2 — Modeling (parallel) | 4 technical, 5 valuation, 12 TSR (`coder`) | 1, 1b, **1c**, **1d** on new runtime (valuation reads FDD + market_context + operating_path_brief; technical does not) | `registry/technical.json`, `data/valuation_model.json`, `registry/tsr_validation.json` |
| 2.5 — Stress | swarm × 5 scenarios (`coder`) | valuation model + deep dive + market_context | main agent merges → `registry/risk_bridge.json` |
| 3 — Charts | 6 charts (`coder`) | valuation model | `charts/*.png` |
| 4 — Reports (parallel) | 7 fundamental, 8 technical, 11 README (`coder`) | all above | `reports/*.md` |
| 5 — Audit | 13 audit (`coder`) | Phase 4 | `registry/audit.json` |

Dependency rules (do not violate — v1 shipped a broken graph):

- Phase 1 agents 2a/2b/2c are genuinely parallel. 2d must run **after** 2a and 2b — it reads their outputs.
- **1c runs after 2b** (needs multi-year `data/raw_sec/`). Spawn **one year-reader per annual on disk** (isolated window; section-walk the cleaned `.txt` via line-range/search — never paste a full 10-K). Year-readers may run **in parallel with 2d**. After excerpt-in-source passes, **2e is the single merger** of `filing_deep_dive.json` (cross-year scorecard via `promise_vs_actual.py`, transcripts secondary). When `market_context.ownership.complexity` is medium/high (or intensity is high), 2e must deepen related-party / control / dual-class / VIE-relevant notes — not leave silence. Extra annuals are not a substitute for that depth. New-runtime 1c complete: `preflight --phase 1c --mode complete` (year-files + excerpts + `verify_rechecks`). Legacy sessions without year-files stay valid on FDD alone.
- **1d (new runtime ≥ 2.6.0)** runs after 1b+1c. Workers gather only (no 8-year forecast). `1d_merge` writes `operating_path_brief.json`. Do not average flatten vs destock. Legacy sessions without 1d stay valid (SKIPPED).
- Phase 2 agents are parallel with each other but need Phase 1/1b/**1c** (and **1d** on new runtime) complete for valuation. Agent 4 must not read any fundamental artifact (including `filing_deep_dive.json`, `market_context.json`, or `operating_path_brief.json`).
- Agent 5 **must** read `registry/filing_deep_dive.json` and log `filing_deep_dive_hooks` (use or explicit reject-with-reason). Agent 5 **must** read `registry/market_context.json` and the region module in `module_file`, and log `market_context_hooks` (use / reject / noted_only). When `operating_path_brief.json` exists, Agent 5 **must** log `operating_path_hooks` (not all `noted_only`). When `registry/street_estimates.json` exists (new runtime ≥ 2.7.0), Agent 5 **must** independently build FY+1 from company evidence, then log `street_bind` + `street_hooks` as a **calibration check** — never copy consensus into base (§10c). On new runtime ≥ 2.8.0, Agent 5 **must** write `roic_identity` on the same NOPAT/WACC stack as the DCF (§10d) — Agent 12 is parallel and is not this identity. Agent 5 remains the only writer of adopted growth/OM paths. Phase 2.5 must ground legal/contingency and credibility-driven bear weight in the deep dive when present, and include ≥1 region/governance/FX scenario when `market_context.intensity` is `high` (expected when `medium` if material). Agent 7 must cover footnotes, multi-year strategy arc, management scorecard, and **market & institutional context** (one-paragraph no-op OK when intensity is `low`) in non-stub sections.
- Phase 2.5 needs `data/valuation_model.json`. Phase 4 needs everything. Phase 5 is last.
- **No always-on region agent** in this graph. Region work is orchestrator judgment + advisory modules + hooks (see §5b).

### Handoff files (every agent)

Every agent — including swarm leads and the audit agent — writes `registry/handoffs/<agent_id>.md` before finishing, with four sections: **What I did**, **Data issues & gaps** (failed/truncated/stale/substituted data, with the fallback used), **Assumptions & deviations** (judgment calls not already recorded with rationale in the artifact), **For downstream agents & the auditor**. The artifact shows *what* was produced; the handoff shows *where it is soft*. The audit agent reads all handoffs as part of its sweep.

### Merge protocol (Phases 0 and 2.5)

When the main agent merges swarm returns: (1) write each verbatim return to `registry/raw/` **before** merging; (2) merge, deduplicating and resolving conflicts in-line; (3) spot-check 3 headline numbers of the merged file against the raw returns or data — a merge must never introduce a new number. The persisted raw returns make the merge auditable. Phase **1c** uses the same rule: persist `fdd_year_*.json`, run excerpt-in-source, then 2e merges (no new numbers; `verify_rechecks` records the re-reads).

### Phase 5 — audit and fix loop

The audit agent (template in `harness/agent_prompts.md`) audits the orchestrator too (merges, classifications — **including market_context / intensity**). It verifies: report numbers match registry/compute outputs; registry headline numbers match the data layer; **at least 5 filing-grade numbers verified against external primary sources** (consistency is not truth); **at least 3 footnote/deep-dive figures re-checked against `data/raw_sec/` primary text**; valuation has `filing_deep_dive_hooks` (or equivalent documented consumption) for material deep-dive findings; when `market_context.json` exists, valuation has non-empty `market_context_hooks` and cost-of-capital / accounting / ownership dials are justified (US low-intensity `noted_only` is OK); fundamental report has non-stub footnotes / strategy-arc / management-track-record coverage and market/institutional context appropriate to intensity; every judgment number has a substantive rationale with scripted intermediates; all compute scripts rerun deterministically from cached data; citations exist; no lost findings (every `latest_quarter.json.risks[]` entry maps to risk_bridge or is explicitly dropped); README required-inputs match what agents actually used. It writes `registry/audit.json` with `verdict: PASS|FAIL`. On FAIL, fix the issues (max 2 iterations), re-audit, and record resolutions. After the final audit, update the README's audit-verdict line and list any waived issues. A session is not complete until audit passes or issues are explicitly waived in the README.

### Machine check

`python3 scripts/check_session.py --ticker <T> --date <D> --full` (use `yfinance-market-mcp/.venv/bin/python` for full JSON-schema validation) — structural PASS/FAIL/SKIPPED report; exits non-zero on FAIL. Verifies required files, schema validity, non-empty rationales, `compute_script` paths exist, probability sums, confidence-gate consistency, and that `audit.json.verdict == "PASS"`. **`registry/market_context.json` is optional for legacy sessions** (absent → SKIPPED); when present, it is schema-checked and valuation must carry non-empty `market_context_hooks`. **`registry/phase_status.json` is optional for legacy sessions** (absent → SKIPPED); when present, schema/keys + designed phase coverage are checked. Run after Phase 5.

## 9. Sector modules (advisory reference)

Read the module for the classified sector **after** §5 identity, before valuation: `sector_banking.md`, `sector_insurance.md`, `sector_growth.md`, `sector_reit.md`, `sector_utility.md`, `sector_cyclical.md`. Empty `module_file` is valid for `standard` (ordinary CPG/industrial DCF). They contain sound methodology (excess-return for banks, float-cost framing for insurers, AFFO/NAV for REITs, through-cycle normalization for cyclicals, SBC discipline for growth). Use them to *choose and shape* the model. Their numbers are reference ranges, not mandates — justify what you pick (§6). Module “detection” / “automatic classification” / scoring-matrix sections are **diagnostic only** — they do not set `primary_sector`. If they contradict §5, §5 wins.

## 9b. Region modules (advisory reference)

Read the module named in `market_context.module_file` before valuation: `region_us.md`, `region_hk_china.md`, `region_generic.md` (add dedicated modules later as needed). They cover local cost-of-capital framing, accounting-regime peer traps, ownership/control (family, SOE, VIE, dual-class), filings maps, and stress seeds. **Advisory only** — never paste module defaults as WACC, country premiums, or family discounts without a `market_context_hooks` use/reject reason (§5b, §6).

## 10. Latest-quarter evidence & overrides

- Agent 2d extracts the latest quarter per `templates/latest_quarter.schema.json` and logs notable changes in `evidence_log` (metric, observation, materiality, suggested rule). **2d logs evidence only.**
- The **valuation agent** decides whether evidence changes assumptions and logs each applied change in `valuation_model.json.overrides_applied` (rule, old, new, reason).
- Rules (symmetric, with materiality):
  - **Two-quarter rule**: a key metric moves >5% relative (or >100bp) in the same direction for two consecutive quarters → adjust the assumption that way. Seasonal metrics compare YoY, not QoQ.
  - **Guidance-change rule**: company guidance (not analyst targets) materially raised/lowered → update trajectory, widen/narrow range. Analyst **price targets** and Street **FY+1/+2 estimates** are not company guidance — never apply this rule to a consensus revision; bind Street separately (§10c).
  - **Inflection rule**: margin inflection → adjust operating-leverage path.
  - **Capital rule**: major buyback/dividend/capex/raise → update capital structure and cash flows.
  - **New-risk rule**: new material risk → add a stress scenario to Phase 2.5.

## 10b. Filing deep dive (multi-year notes, strategy, credibility)

Phase **1c** is a gather/merge: **N year-readers** write `registry/raw/fdd_year_FY{yyyy}.json` (one annual each; schema `templates/filing_year_dive.schema.json`); a machine **excerpt-in-source** check; then Agent **2e** is the **single writer** of `registry/filing_deep_dive.json` per `templates/filing_deep_dive.schema.json` (methodology: `harness/filing_deep_dive.md`). Year-readers must not call `promise_vs_actual.py` or see other years. 2e merges, rehydrates numbers, fetches transcripts, and fail-closes on silent ownership at medium/high intensity. Agent 13 still evaluates FDD substance. Required FDD blocks:

1. **Footnotes** — targeted note extractions (revenue disaggregation, segments, SBC unrecognized, debt/leases, contingencies/legal, tax, commitments, related-party/dual-class) with status `extracted|missing|not_applicable|partial` and short excerpts. Prefer code helpers in `scripts/kd_research/note_extract.py`. Full note text stays in `data/raw_sec/`; do **not** dump uncapped 10-K prose into `sec_filings.json`.
2. **Strategy arc** — typically **≥3 annual reports** (Item 1 + MD&A priorities): stated priorities by year, continuity score `{value, rationale, basis}`, pivot flags, capital-allocation story, implied model hooks.
3. **Management scorecard** — grade historical company promises (revenue/opex/capex/margins/capital returns/segment paths, plus soft milestones) against actuals. **Filings first** (prior EX-99.1 outlooks, 10-K/10-Q MD&A); **earnings-call transcripts second** (`data/transcripts/`, each scorecard row labeled `source_type`: `filing` | `transcript` | `filing+transcript`). Use `scripts/kd_research/promise_vs_actual.py` for numeric join/grades when possible. Qualitative vision promises are `too_early` / narrative_shift — never fake precision. If transcripts are unavailable, declare the gap, set degraded quality, and widen valuation uncertainty.

Valuation must record `filing_deep_dive_hooks` for material findings (or explicit reject). Deep dive does **not** auto-set WACC or probabilities — the LLM still judges. Valuation must also record `market_context_hooks` when `market_context.json` exists (intensity `low` may be a single `noted_only`). IR / 8-K CEO dollar quotes (EX-99.1) are **first-class** for AI/segment run-rate; missing transcripts **widen range** and degrade scorecard quality — they do **not** license dropping a printed company outlook from the independent base path.

## 10c. Independent FY+1 forecast vs Street calibration (new runtime ≥ 2.7.0)

**Skill, not copy.** Next-year Street revenue consensus is usually a decent *reference* for what the company will report. A good research agent should **independently** land near that number from company evidence. It must **not** paste consensus into the model.

1. **Agent 2a** fetches vendor FY+1 / FY+2 revenue and EPS into `registry/street_estimates.json` (label company FY vs calendar). Do not invent. Fetch failure → `unavailable` or `data_fetch_log.failed[]`; Agent 5 **widens range**.
2. **Agent 2d** still writes **company** guidance only. Street never enters `latest_quarter.guidance`.
3. **Agent 5** first builds **base** FY+1 revenue from **company** evidence: printed guide (if any), segment stack (e.g. AI + software + non-AI), run-rate / sequential, RPO conversion. Haircuts belong in **bear / range / explicit overlay**, not a silent Y1 that exiles the guide.
4. **Then** write `street_bind`: `guide` × `street` × `base` (independent) and `delta_pct = (base − street) / street`. `street` must **match** `street_estimates.json` FY+1 when that value is numeric (`response=street_unusable` to skip). `independent_construction.rationale` must show the stack. `street_hooks[]`: `used_as:calibration_check` or `rejected` — **forbidden** `used_as:revenue_path` / copying the mean. Do not average Street with guide into base (same sin as averaging flatten vs destock). Numeric `base ≈ street` with a calibration hook is allowed (landing near consensus); paste-without-needle is Agent 13 Band 3, not a machine FAIL.
5. If `|delta_pct| > 0.20`, that is a **research miss until proven otherwise**: `response=reopen_path` and rebuild from missing segment/guide/run-rate. `keep_independent_vs_street` needs a transmission mechanism (why the independent stack should differ from a typically accurate next-year consensus). Being 21% off is **not** machine FAIL; missing the response is FAIL. The harness never auto-sets `base = street`.
6. **Conservatism stacking:** on new runtime, valuation **must** write `conservatism_dials[]` with keys `volume_vs_guide`, `gaap_om_vs_guide`, `sbc_in_fcff`, `wacc_vs_buildup` (`applies_in` base | bear_only | none). Omitting the array is FAIL (silent stacking). `stacking_justification` when ≥3 apply in base. Economic SBC-as-cash remains allowed; stacking it with a haircut-the-guide volume path as “base” is FAIL-quality.
7. **SOTP vs DCF:** when both run (model.name / methods / assumption keys), write `multi_method_reconciliation` — omit is FAIL on new runtime. If `|cross − primary| / primary > 0.40`, reopen the independent volume path or explain why the gap is real (cash vs earnings, segments). Do not keep a 40%+ gap with `why_primary_wins` theater.

Legacy sessions without `street_estimates.json` and harness < 2.7.0 → SKIPPED.

## 10d. Owner-earnings ROIC identity (new runtime ≥ 2.8.0)

**Skill, not a formula.** DCF defines value. ROIC decides whether that DCF is a business or a spreadsheet. Agent 5’s compute script must print owner-earnings ROIC on the **same** NOPAT, cash-tax, lease, and WACC stack as the DCF. Agent 12’s historical GAAP ROC screen is a prior, not this identity. Phase 2 stays parallel (4 ∥ 5 ∥ 12).

| Mid-cycle NOPAT / invested capital | What growth does | What “cheap” means |
|---|---|---|
| Above WACC | Friend | Discount to a franchise DCF can be a margin of safety |
| ≈ WACC | Irrelevant | EV should sit near invested capital; equity near book after debt |
| Below WACC | Enemy | Extra capital destroys value; a Gordon `g > 0` with no reinvestment is a wish |

1. **Same script as the DCF.** Numerator: SOI (or the DCF’s EBIT KPI) − corporate other − **cash tax** (not a 21% GAAP paste when a VA exists) − excess pension cash − SBC. Denominator: notes + current LT + LT + equity − cash; consider unfunded pension; do not inflate IC with VA’d DTAs. Leases: `opex_and_out_of_ic` **or** `capitalized_both` — never mix Yahoo lease-grossed debt with opex leases. Print TTC ROIC (history) and mid-cycle ROIC. Hurdle is **in-model WACC**, not a 15% Buffett paste.
2. **Dual column** that must reconcile: **A** residual-claim FCFF (keep) vs **B** `EV = IC + PV of (ROIC − WACC) × IC` on the same NOPAT and WACC. Also print a **g=0 counterfactual** from the same engine (trough years can hide a Gordon plug).
3. **Legal exits when mid-cycle ROIC ≤ WACC** (`quality_bucket` below or ≈, 50 bp check tolerance — not an investment opinion; same class as Street’s 20%/40%): `g_zero` | `cut_earnings_power` | `reinvestment_in_engine` (`FCFF = NOPAT × (1 − g/ROC)`; mismatch=false) | `reconciled_to_ic` (|A−IC|/IC ≤ 8% **and** cheap_claim is `equity_near_book` / `residual_option` / `not_cheap`). The harness **never writes g**. Disclosure in `terminal_consistency` is not a substitute.
4. **`cheap_claim.class`:** `franchise_mos` only when bucket is `above_wacc`. Below/approx → `equity_near_book` | `residual_option` | `not_cheap`. You may not call equity cheap on MoS vs residual-claim DCF alone.
5. **`applies: false`** with `not_applicable_reason` (≥40 chars) + `native_analog` for banking (`roe_vs_ke`), insurance, REIT NAV/AFFO, pre-profit growth (negative IC). Do not invent industrial IC for those names.
6. TTC ROIC < WACC is **printed + Agent 13**, not a machine FAIL (would nuke trough cyclicals). Tires may use mid-cycle FCFF; mines keep advisory `g=0`. `sector_cyclical.md` quality threshold is not a substitute for coding the identity.

Check tolerances (not opinions): WACC match 5 bp; mid-cycle ROIC = NOPAT/IC 25 bp; bucket band 50 bp; A vs IC noise 8%. Legacy / missing `harness_version` / harness < 2.8.0 → SKIPPED.

## 11. Analytical perspectives

Reports must address five lenses — and each lens must be **fed by data**, not asserted:

- **Value**: margin of safety (1 − price/FV, signed), normalized earnings, capital-allocation assessment, balance-sheet floor (footnote debt/leases when available).
- **Growth**: TAM/SAM/SOM with sources, organic vs M&A split, concentration, reinvestment runway (from Phase 0/1 data **and** strategy_arc).
- **Contrarian/catalyst**: catalyst calendar, analyst dispersion, short interest, insider activity (from `news_sentiment.json`); why is it cheap; management credibility pattern from scorecard.
- **Risk**: stress scenarios with probabilities + rationale, liquidity/contingents (footnote contingencies / Item 3 before web legal $), concentration, covenants/refinancing, position-sizing input; region/governance/FX when `market_context.intensity` warrants it.
- **Technical/timing**: entry/stop/targets, ATR-based sizing, relative strength vs regional benchmark and sector index — computed independently of fundamentals (Agents 4 and 8 never read fundamental artifacts).

Document cross-lens contradictions explicitly in the fundamental report ("Perspective conflicts"). The fundamental report must also include non-stub subsections on **footnote findings**, **multi-year strategy alignment**, **management track record** fed by `filing_deep_dive.json`, and **market & institutional context** fed by `market_context.json` (one-paragraph no-op OK when intensity is `low`).

## 12. Fallbacks & escalation

- Missing/partial data → document the gap, use the closest proxy with rationale, **widen** the valuation range.
- Sector confidence < 0.70 → `standard` + manual-review flag.
- Market-context confidence < 0.70 or intensity `high` with thin local filings → `requires_manual_review` + **widen** the valuation range (do not fake a US no-op).
- Conflicting lenses → do not force one verdict; present bull/base/bear and state which perspective dominates under which assumption.
- Pre-revenue/binary companies → milestone-based scenarios per `sector_growth.md`.
- A tool/API failure → record it in the artifact, use the fallback source (§4), flag degraded quality in the README.

## 13. Quality gates

**Process principle:** enforce **specialist outcomes** (isolation, hooks, handoffs, phase↔disk), not Task/subagent API spawn IDs. Valuation stays **single-writer** (Agent 5). Parallel fan-out is for independent gather (Phase 0, 1 data, stress), not multi-valuer or parallel report-section authorship.

| Gate | Enforced by |
|---|---|
| Required artifacts exist, parse, validate against `templates/*.schema.json`, have non-empty rationales | `[machine]` check_session.py |
| `compute_script` paths exist; ticker/date match folder; confidence-gate consistency | `[machine]` check_session.py |
| scenario_probabilities sums to 1.0; ≥5 stress scenarios | `[machine]` check_session.py |
| audit verdict is PASS | `[machine]` check_session.py |
| When `filing_deep_dive.json` + valuation exist: non-empty `filing_deep_dive_hooks[]` with `from`/`action`/`reason` (F8) | `[machine]` check_session + preflight `2_5` entry / `2_parallel` complete |
| New-runtime `operating_path_brief.json`: 3 worker raws + `verify_rechecks` ≥3; valuation `operating_path_hooks` non-empty and not all-`noted_only`. Absent on legacy → SKIPPED | `[machine]` 1d `--mode complete` + `check_session --full` |
| New-runtime `street_estimates.json` + valuation: `street_bind` independent construction; `delta_pct` identity; `|delta|>20%` must-respond (not auto-copy Street); `street_hooks` non-empty, not all-`noted_only`, no path-copy action. Absent on legacy → SKIPPED | `[machine]` `check_session --full` + `2_parallel` complete |
| New-runtime `roic_identity` on valuation: same-script NOPAT/IC vs WACC; dual column; legal exit when ROIC ≤ WACC; `franchise_mos` forbidden on below/approx; `applies:false` with reason for banks/REITs/growth. Absent on legacy / missing version → SKIPPED | `[machine]` `check_session --full` + `2_parallel` complete |
| Harness ≥ 2.9.0: template masses `30/45/25` or `25/50/25` need `probability_method` **and** a numeric counterfactual; `priced_for_perfection` must name a dial (not price≷base/PW); `(bull−bear)/base > 100%` or `bear < 0.4×base` requires `decision_usefulness`; Agent 12 `roc_vs_cost_of_capital=fail` cannot sit with `cheap_claim=franchise_mos` unless `quality_bucket=above_wacc`; branded staple + `primary_sector=cyclical` without spot evidence FAIL (F21); branded consumer/CPG/staples cannot use `primary_sector=growth`. Legacy / missing version → SKIPPED | `[machine]` `check_session --full` + `2_parallel` complete |
| Outcomes `overall_label` uses `horizon_primary` only (default 3m); 1d/1w MoS-sign is tape hygiene. `fv_band_at_mark=inside` ineligible when span >100%. Catalog comparable rankings exclude null `fv_base`. Calibration/portfolio must not default to audit PASS as a buy list | `[machine]` outcomes scorer + catalog_api |
| Agent 4 isolation: `technical.json` + `handoffs/4*` must not cite fundamental paths (FDD, valuation, background, latest_quarter, market_context, sec_filings, sp_financials, street_estimates) | `[machine]` WARN default / FAIL `--full` |
| Handoffs ≥300B for specialists **and** swarm leads (`phase0_*`, `phase25_*` aliases); four section headers | `[machine]` size FAIL `--full`; headers **WARN** |
| `phase_status` complete ⇒ primary artifacts on disk; pending/in_progress with artifact on disk → lag | `[machine]` FAIL complete-without-artifact; **WARN** lag |
| Reports non-stub; report numbers match registry AND data layer; ≥5 filing-grade numbers verified externally; rationales substantive with scripted intermediates; scripts rerun deterministically; no lost findings | `[audit]` Phase 5 agent |
| `filing_deep_dive.json` structure (footnotes + strategy_arc + scorecard); hook *consumption quality* / report sections | `[machine]` structure + `[audit]` substance |
| New-runtime `registry/raw/fdd_year_*.json`: required sections walked, non-empty `key_figures`, excerpt-in-source; FDD `verify_rechecks` ≥3; `years_covered` matches year-files. Absent on legacy/slim → SKIPPED | `[machine]` 1c `--mode complete` + `check_session --full` |
| `market_context.json` when present: schema + rationale; valuation `market_context_hooks` non-empty; medium/high intensity not all-`noted_only`; absent → SKIPPED (legacy) | `[machine]` + `[audit]` |
| `phase_status.json` when present: schema + designed phase coverage; absent → SKIPPED (legacy); new sessions scaffold it | `[machine]` |
| `research_brief.json` when present: schema + depth + ≥3 questions; absent → SKIPPED (legacy); new sessions write before Phase 0 | `[machine]` + `[audit]` |
| Phase entry/complete preflight (`preflight_phase.py`); orchestrator MUST use before 2/2.5/4/5 and before marking 0/1_parallel/1c/2_parallel/2.5 complete | `[human]`/`[orchestrator]` (script exists; not auto-CI) |
| Decision-grade returns: Phase 0 `downstream_relevance`; handoffs with downstream actions; no filing dumps in swarm JSON | `[audit]` + merge preflight (raw counts) |
| ≥3 footnote/deep-dive figures verified against `data/raw_sec/`; multi-year annual text retained under session tree | `[audit]` Phase 5 agent |
| Sector module read and model choice justified | `[audit]` Phase 5 agent |
| Region module read when market_context present; CoC/accounting/ownership dials justified (no silent regional haircuts); intensity gate respected | `[audit]` Phase 5 agent |
| Reverse-engineering done; priced-for-perfection explicitly flagged true/false with rationale | `[audit]` Phase 5 agent |
| SBC/dilution at critical intensity for growth / is_also_growth | `[audit]` Phase 5 agent |
| No fabricated numbers: every number sourced or justified | `[audit]` Phase 5 agent |
| Subagent *API* spawn proof / token counts | **Not machine-enforced** (optional process telemetry later) |
| Manual-review flag acted on when confidence < 0.70 | `[human]` |

## 14. Quick start

```bash
# one-shot
kimi -p "Run the JPM research swarm for $(date +%F) in /workspace-stock-research"

# evidence gates (orchestrator)
python3 scripts/preflight_phase.py --ticker JPM --date $(date +%F) --phase 2_parallel
python3 scripts/check_session.py --ticker JPM --date $(date +%F) --full --write-acceptance
```

The **orchestrator** (lead): scaffolds the session (§2, including `registry/phase_status.json`), classifies the sector (§5) and market/region context (§5b), writes `registry/research_brief.json`, then executes Phases 0–5 **in graph order**, spawning only the **subagents** for the current phase (templates in `harness/agent_prompts.md`). Update `phase_status` after each subagent return. **MUST** run `preflight_phase.py --phase …` (and `--subagent …` when spawning a specialist) before entering a phase — FAIL means do not spawn. Finish with `check_session.py --full` (optionally `--write-acceptance`). See `harness/HARNESS_MAP.md`.
