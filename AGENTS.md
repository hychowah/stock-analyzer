# Autonomous Stock Research Agent — Harness Spec (v2)

This file is the **single normative spec** for the research harness. It is auto-loaded into every session in this workspace. The only other normative file is `harness/agent_prompts.md` (subagent prompt templates). Everything else is reference or contract.

**Product purpose:** better **investment decisions** via decision-grade fair value, risks, timing, and provenance — not token thrift. Optimize **agent → next-phase** value transfer (usable artifacts, no lost risks, no invented numbers).

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
2. Scaffold with: `python3 scripts/scaffold_session.py --ticker <T> --date <D>` — creates `archive/research/<T>/<D>/`; refuses to overwrite an existing non-empty session.
3. Re-research on a new date → new dated folder; reference the prior run if useful. Never rewrite a completed session to “fix” history.
4. After Phase 5 (audit): run `python3 scripts/finalize_session.py --ticker <T> --date <D>` (snapshot + compare SQLite + thin catalog) so the run is indexed for future comparison.
5. Path resolution (`scripts/kd_research/paths.py`): prefer `archive/research/...`; fall back to legacy root `<TICKER>/<DATE>/` during migration only.
6. Repo root holds harness code only (`harness/`, `scripts/`, `templates/`, sector/region modules, MCP packages) — not ticker session trees.

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

Run **once**, by the main agent, before anything else. There is **no scoring algorithm** — classify by reasoning over objective inputs:

1. Pull objective inputs: yfinance sector/industry, business description, revenue mix (latest 10-K), and which sector KPIs exist (NIM/CET1? FFO/AFFO? combined ratio? ARR/NRR? rate base? commodity exposure?).
2. Judge the primary sector: `banking | insurance | growth | reit | utility | cyclical | standard`.
3. Write `registry/sector_config.json` per `templates/sector_config.schema.json`: `primary_sector`, self-assessed `confidence`, `signals` (the evidence), `rationale` (why this sector, why this confidence), `is_also_growth`, `module_file`, plus `runner_up` (second-best hypothesis + why rejected) and `disconfirming_signals` (evidence against the choice that was weighed). For genuinely borderline cases, run two independent classification passes and reconcile.
4. Confidence < 0.70 → use `standard`, set `requires_manual_review: true`, and say so prominently in the README.
5. If `is_also_growth`: primary sector's model still leads; add growth-module SBC/dilution analysis at critical intensity; extend the explicit forecast to 7–10 years.

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
| Orchestrator | main agent | — | `registry/sector_config.json`, `registry/market_context.json`, `registry/research_brief.json` (new sessions), maintains `registry/phase_status.json`; **MUST** run `scripts/preflight_phase.py` (or equivalent evidence check) before Phase 2 / 2.5 / 4 / 5 |
| 0 — Background | swarm × research rounds (`explore`) | sector_config, market_context, research_brief (when present) | main agent merges → `registry/background.json`; coverage vs brief + risk_candidates in handoff |
| 1 — Data (parallel) | 2a fundamentals, 2b SEC filings, 2c news & sentiment (`coder`) | sector_config, market_context | `data/sp_financials.csv` (+ peers), `registry/sec_filings.json` + `data/raw_sec/` (+ multi-year annuals), `registry/news_sentiment.json` |
| 1b — Latest quarter | 2d integrator (`coder`) | 2a, 2b | `registry/latest_quarter.json` |
| 1c — Filing deep dive | 2e deep dive (`coder`) | 2b (and 2a when actuals needed); reads market_context for ownership depth | `registry/filing_deep_dive.json`; may add `data/transcripts/*` |
| 2 — Modeling (parallel) | 4 technical, 5 valuation, 12 TSR (`coder`) | 1, 1b, **1c** (valuation/TSR read deep dive + market_context; technical does not) | `registry/technical.json`, `data/valuation_model.json`, `registry/tsr_validation.json` |
| 2.5 — Stress | swarm × 5 scenarios (`coder`) | valuation model + deep dive + market_context | main agent merges → `registry/risk_bridge.json` |
| 3 — Charts | 6 charts (`coder`) | valuation model | `charts/*.png` |
| 4 — Reports (parallel) | 7 fundamental, 8 technical, 11 README (`coder`) | all above | `reports/*.md` |
| 5 — Audit | 13 audit (`coder`) | Phase 4 | `registry/audit.json` |

Dependency rules (do not violate — v1 shipped a broken graph):

- Phase 1 agents 2a/2b/2c are genuinely parallel. 2d must run **after** 2a and 2b — it reads their outputs.
- **2e (filing deep dive) runs after 2b** (needs multi-year `data/raw_sec/`) and should use 2a actuals when grading promises; it may run **in parallel with 2d**. When `market_context.ownership.complexity` is medium/high (or intensity is high), 2e must deepen related-party / control / dual-class / VIE-relevant notes — not leave silence.
- Phase 2 agents are parallel with each other but need Phase 1/1b/**1c** complete for valuation. Agent 4 must not read any fundamental artifact (including `filing_deep_dive.json` or `market_context.json`).
- Agent 5 **must** read `registry/filing_deep_dive.json` and log `filing_deep_dive_hooks` (use or explicit reject-with-reason). Agent 5 **must** read `registry/market_context.json` and the region module in `module_file`, and log `market_context_hooks` (use / reject / noted_only). Phase 2.5 must ground legal/contingency and credibility-driven bear weight in the deep dive when present, and include ≥1 region/governance/FX scenario when `market_context.intensity` is `high` (expected when `medium` if material). Agent 7 must cover footnotes, multi-year strategy arc, management scorecard, and **market & institutional context** (one-paragraph no-op OK when intensity is `low`) in non-stub sections.
- Phase 2.5 needs `data/valuation_model.json`. Phase 4 needs everything. Phase 5 is last.
- **No always-on region agent** in this graph. Region work is orchestrator judgment + advisory modules + hooks (see §5b).

### Handoff files (every agent)

Every agent — including swarm leads and the audit agent — writes `registry/handoffs/<agent_id>.md` before finishing, with four sections: **What I did**, **Data issues & gaps** (failed/truncated/stale/substituted data, with the fallback used), **Assumptions & deviations** (judgment calls not already recorded with rationale in the artifact), **For downstream agents & the auditor**. The artifact shows *what* was produced; the handoff shows *where it is soft*. The audit agent reads all handoffs as part of its sweep.

### Merge protocol (Phases 0 and 2.5)

When the main agent merges swarm returns: (1) write each verbatim return to `registry/raw/` **before** merging; (2) merge, deduplicating and resolving conflicts in-line; (3) spot-check 3 headline numbers of the merged file against the raw returns or data — a merge must never introduce a new number. The persisted raw returns make the merge auditable.

### Phase 5 — audit and fix loop

The audit agent (template in `harness/agent_prompts.md`) audits the orchestrator too (merges, classifications — **including market_context / intensity**). It verifies: report numbers match registry/compute outputs; registry headline numbers match the data layer; **at least 5 filing-grade numbers verified against external primary sources** (consistency is not truth); **at least 3 footnote/deep-dive figures re-checked against `data/raw_sec/` primary text**; valuation has `filing_deep_dive_hooks` (or equivalent documented consumption) for material deep-dive findings; when `market_context.json` exists, valuation has non-empty `market_context_hooks` and cost-of-capital / accounting / ownership dials are justified (US low-intensity `noted_only` is OK); fundamental report has non-stub footnotes / strategy-arc / management-track-record coverage and market/institutional context appropriate to intensity; every judgment number has a substantive rationale with scripted intermediates; all compute scripts rerun deterministically from cached data; citations exist; no lost findings (every `latest_quarter.json.risks[]` entry maps to risk_bridge or is explicitly dropped); README required-inputs match what agents actually used. It writes `registry/audit.json` with `verdict: PASS|FAIL`. On FAIL, fix the issues (max 2 iterations), re-audit, and record resolutions. After the final audit, update the README's audit-verdict line and list any waived issues. A session is not complete until audit passes or issues are explicitly waived in the README.

### Machine check

`python3 scripts/check_session.py --ticker <T> --date <D> --full` (use `yfinance-market-mcp/.venv/bin/python` for full JSON-schema validation) — structural PASS/FAIL/SKIPPED report; exits non-zero on FAIL. Verifies required files, schema validity, non-empty rationales, `compute_script` paths exist, probability sums, confidence-gate consistency, and that `audit.json.verdict == "PASS"`. **`registry/market_context.json` is optional for legacy sessions** (absent → SKIPPED); when present, it is schema-checked and valuation must carry non-empty `market_context_hooks`. **`registry/phase_status.json` is optional for legacy sessions** (absent → SKIPPED); when present, schema/keys + designed phase coverage are checked. Run after Phase 5.

## 9. Sector modules (advisory reference)

Read the module for the classified sector before valuation: `sector_banking.md`, `sector_insurance.md`, `sector_growth.md`, `sector_reit.md`, `sector_utility.md`, `sector_cyclical.md`. They contain sound methodology (excess-return for banks, float-cost framing for insurers, AFFO/NAV for REITs, through-cycle normalization for cyclicals, SBC discipline for growth). Use them to *choose and shape* the model. Their numbers are reference ranges, not mandates — justify what you pick (§6).

## 9b. Region modules (advisory reference)

Read the module named in `market_context.module_file` before valuation: `region_us.md`, `region_hk_china.md`, `region_generic.md` (add dedicated modules later as needed). They cover local cost-of-capital framing, accounting-regime peer traps, ownership/control (family, SOE, VIE, dual-class), filings maps, and stress seeds. **Advisory only** — never paste module defaults as WACC, country premiums, or family discounts without a `market_context_hooks` use/reject reason (§5b, §6).

## 10. Latest-quarter evidence & overrides

- Agent 2d extracts the latest quarter per `templates/latest_quarter.schema.json` and logs notable changes in `evidence_log` (metric, observation, materiality, suggested rule). **2d logs evidence only.**
- The **valuation agent** decides whether evidence changes assumptions and logs each applied change in `valuation_model.json.overrides_applied` (rule, old, new, reason).
- Rules (symmetric, with materiality):
  - **Two-quarter rule**: a key metric moves >5% relative (or >100bp) in the same direction for two consecutive quarters → adjust the assumption that way. Seasonal metrics compare YoY, not QoQ.
  - **Guidance-change rule**: company guidance (not analyst targets) materially raised/lowered → update trajectory, widen/narrow range.
  - **Inflection rule**: margin inflection → adjust operating-leverage path.
  - **Capital rule**: major buyback/dividend/capex/raise → update capital structure and cash flows.
  - **New-risk rule**: new material risk → add a stress scenario to Phase 2.5.

## 10b. Filing deep dive (multi-year notes, strategy, credibility)

Agent **2e** writes `registry/filing_deep_dive.json` per `templates/filing_deep_dive.schema.json` (methodology note: `harness/filing_deep_dive.md`). Required blocks:

1. **Footnotes** — targeted note extractions (revenue disaggregation, segments, SBC unrecognized, debt/leases, contingencies/legal, tax, commitments, related-party/dual-class) with status `extracted|missing|not_applicable|partial` and short excerpts. Prefer code helpers in `scripts/kd_research/note_extract.py`. Full note text stays in `data/raw_sec/`; do **not** dump uncapped 10-K prose into `sec_filings.json`.
2. **Strategy arc** — typically **≥3 annual reports** (Item 1 + MD&A priorities): stated priorities by year, continuity score `{value, rationale, basis}`, pivot flags, capital-allocation story, implied model hooks.
3. **Management scorecard** — grade historical company promises (revenue/opex/capex/margins/capital returns/segment paths, plus soft milestones) against actuals. **Filings first** (prior EX-99.1 outlooks, 10-K/10-Q MD&A); **earnings-call transcripts second** (`data/transcripts/`, each scorecard row labeled `source_type`: `filing` | `transcript` | `filing+transcript`). Use `scripts/kd_research/promise_vs_actual.py` for numeric join/grades when possible. Qualitative vision promises are `too_early` / narrative_shift — never fake precision. If transcripts are unavailable, declare the gap, set degraded quality, and widen valuation uncertainty.

Valuation must record `filing_deep_dive_hooks` for material findings (or explicit reject). Deep dive does **not** auto-set WACC or probabilities — the LLM still judges. Valuation must also record `market_context_hooks` when `market_context.json` exists (intensity `low` may be a single `noted_only`).

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

| Gate | Enforced by |
|---|---|
| Required artifacts exist, parse, validate against `templates/*.schema.json`, have non-empty rationales | `[machine]` check_session.py |
| `compute_script` paths exist; ticker/date match folder; confidence-gate consistency | `[machine]` check_session.py |
| scenario_probabilities sums to 1.0; ≥5 stress scenarios | `[machine]` check_session.py |
| audit verdict is PASS | `[machine]` check_session.py |
| Reports non-stub; report numbers match registry AND data layer; ≥5 filing-grade numbers verified externally; rationales substantive with scripted intermediates; scripts rerun deterministically; no lost findings | `[audit]` Phase 5 agent |
| `filing_deep_dive.json` present with footnotes + strategy_arc + management_scorecard; scorecard rows source-labeled; valuation hooks / report sections consume deep dive | `[machine]` + `[audit]` |
| `market_context.json` when present: schema + rationale; valuation `market_context_hooks` non-empty; absent on legacy sessions → SKIPPED (not FAIL) | `[machine]` + `[audit]` |
| `phase_status.json` when present: schema + designed phase coverage; absent on legacy sessions → SKIPPED (not FAIL); new sessions scaffold it | `[machine]` |
| `research_brief.json` when present: schema + depth + ≥3 questions; absent → SKIPPED (legacy); new sessions write before Phase 0 | `[machine]` + `[audit]` |
| Phase entry/complete preflight available (`preflight_phase.py`); orchestrator MUST use before 2/2.5/4/5 and before marking 0/2.5 complete | `[human]`/`[orchestrator]` |
| Decision-grade returns: Phase 0 `downstream_relevance`; handoffs with downstream actions; no filing dumps in swarm JSON | `[audit]` + merge preflight |
| ≥3 footnote/deep-dive figures verified against `data/raw_sec/`; multi-year annual text retained under session tree | `[audit]` Phase 5 agent |
| Sector module read and model choice justified | `[audit]` Phase 5 agent |
| Region module read when market_context present; CoC/accounting/ownership dials justified (no silent regional haircuts); intensity gate respected | `[audit]` Phase 5 agent |
| Reverse-engineering done; priced-for-perfection explicitly flagged true/false with rationale | `[audit]` Phase 5 agent |
| SBC/dilution at critical intensity for growth / is_also_growth | `[audit]` Phase 5 agent |
| No fabricated numbers: every number sourced or justified | `[audit]` Phase 5 agent |
| Manual-review flag acted on when confidence < 0.70 | `[human]` |

## 14. Quick start

```bash
# one-shot
kimi -p "Run the JPM research swarm for $(date +%F) in /workspace-stock-research"

# evidence gates (orchestrator)
python3 scripts/preflight_phase.py --ticker JPM --date $(date +%F) --phase 2_parallel
python3 scripts/check_session.py --ticker JPM --date $(date +%F) --full --write-acceptance
```

The main agent: scaffolds the session (§2, including `registry/phase_status.json`), classifies the sector (§5) and market/region context (§5b), writes `registry/research_brief.json`, then executes Phases 0–5 using the templates in `harness/agent_prompts.md` while updating the phase_status resume map and running preflight before Phase 2/2.5/4/5, finishing with `check_session.py --full` (optionally `--write-acceptance`). See `harness/HARNESS_MAP.md`.
