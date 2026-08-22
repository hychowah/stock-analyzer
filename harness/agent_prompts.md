# Subagent Prompt Templates

Copy-paste templates for each phase of the harness (see `harness/RESEARCH_AGENTS.md` §8). Substitute these variables everywhere:

| Variable | Example |
|---|---|
| `TICKER` | `JPM` |
| `DATE` | `2026-07-25` |
| `ROOT` | `/workspace-stock-research` |
| `S` | `/workspace-stock-research/archive/research/JPM/2026-07-25` (session root; never at repo root) |

Every template already carries the justification contract — do not strip it. Subagents see only their prompt; pass all context explicitly.

**Conventions for all agents:**
- **Product purpose**: this harness produces **investment-decision research** (fair value, risks, timing, provenance). Optimize for **valuable results the next phase can use** — not for shorter chat or token thrift. Drop noise and raw dumps; never drop material risks, ownership facts, or footnote numbers to look concise.
- **Hermetic scripts**: compute scripts must read session-cached data (`S/data/*.csv`, `S/registry/*.json`) when present and fetch live data only when absent. A rerun on the same session must reproduce the same numbers.
- **Session sharing vs isolation**: **Within this session** agents must use each other’s artifacts under `S/` (handoffs, registry, data). **Across sessions** (other `session_key` under the same or other tickers): do **not** open, list, or mine prior runs for FV, MoS, thesis, handoffs, or “is yesterday complete?” — unless the user explicitly said **resume that folder** or **compare after this run**. Default new-run start: scaffold → work under `S` only. See `S/registry/session_isolation.json`.
- **Scripted intermediates / number integrity**: any number used inside an assumption build-up (e.g. realized beta, growth CAGR) must be computed by a script in `S/data/compute/`, not by unscripted mental math. Multi-step arithmetic belongs in compute scripts. Reports and later agents must **rehydrate** judgment numbers from registry/compute paths — never from chat memory.
- **Benchmarks**: use the regional benchmark and sector index declared by the orchestrator in the session's required inputs (and `S/registry/research_brief.json` when present); deviate only with a stated rationale.
- **Market / region context**: read `S/registry/market_context.json` when present (orchestrator writes it with sector_config). Cost of capital and governance dials are **local to listing and cash-flow currency** — do not paste US 10Y/ERP by default for non-USD models. Region modules (`region_*.md`) are advisory only; never apply hardcoded country WACC, ERP tables, or family-control discounts. Intensity `low` may no-op with explicit `noted_only` hooks; `medium`/`high` require real treatment. There is **no always-on region agent** — ownership depth is Agent 2e; CoC judgment is Agent 5.
- **Research brief**: when `S/registry/research_brief.json` exists, treat its investment objective and `must_answer_questions` as the coverage north star. Map findings to those questions; list unanswered items in the handoff so valuation can widen range or Phase 2.5 can add stress.
- **Research depth**: honor `research_brief.research_depth` (`standard` | `deep`) and `market_context.intensity`. **Deep** means more ownership/FX/control/primary-filing work — not skipping quality gates. Never skip filing deep dive. Stress scenarios remain ≥5.
- **Decision-grade return contract** (every agent):
  - **Primary product is on disk** (registry JSON, data CSVs, compute outputs, charts, reports). Chat to the parent is disposable.
  - **Specialist agents**: finish by writing the artifact + handoff. Parent-facing summary = handoff path + 3–5 bullets of what changed for downstream — do not paste full tables or filings into chat.
  - **Swarm workers (Phase 0 / 2.5)**: return **JSON only** with mandatory decision fields (see templates). Prefer **signal density**: 3–6 specific, sourced findings beat 20 generic industry platitudes. Put full text under `S/data/` (raw_sec, transcripts, caches); returns carry **paths + short excerpts**, not uncapped 10-K prose.
  - **Anti-patterns (FAIL-quality even if schema-valid)**: empty or missing `downstream_relevance` on Phase 0 findings; quantitative claims without sources; inventing litigation/contingent quanta; pasting full filing/HTML into return JSON or handoff; hollow “looks fine” handoffs that hide gaps; report numbers not present in registry/compute.
  - **Orchestrator merges**: write each raw return under `S/registry/raw/` **before** merging; merge for **coverage** (brief questions, risk candidates, stress library) and conflict notes; spot-check ≥3 headline numbers against data/raw — never invent merge numbers.
- **Judgment exemplars (style only)**: before writing judgment-heavy outputs, match the GOOD patterns in `ROOT/harness/exemplars/` (index: `ROOT/harness/exemplars/index.json`). BAD patterns are FAIL-quality even if schema-valid. **Do not copy illustrative numbers into this session.** Agent map: valuation (5) and audit (13) → `rationale_quality.md` + `hooks_quality.md` + `valuation_decision_quality.md`; technical (4), TSR (12), deep dive (2e) → `rationale_quality.md`; **every agent** → `handoff_quality.md` for handoff style. Orchestrator injects the relevant paths into each subagent prompt (do not paste full exemplar banks into every template).
- **Handoff file (required of EVERY agent)**: before finishing, write `S/registry/handoffs/<your_agent_id>.md` (e.g. `2a_fundamentals.md`, `5_valuation.md`, `13_audit.md`) with four sections:
  1. **What I did** — 3-5 bullets: inputs read, outputs written, tools used.
  2. **Data issues & gaps** — anything that failed to fetch, was truncated, stale, missing, or had to be substituted (with the fallback used). If none, say "none".
  3. **Assumptions & deviations** — every judgment call that ISN'T already recorded with rationale in your output artifact: inferred inputs, template deviations, edge cases you resolved by choice.
  4. **For downstream agents & the auditor** — decision-grade soft state:
     - Top 3 things the **next** agent must not miss (with paths).
     - Explicit gaps that should **widen** valuation range or add a stress scenario.
     - Authoritative file paths (not restated tables).
  Keep it under one page. The artifact shows WHAT you produced; the handoff shows WHERE it is soft and what downstream must do. Match `ROOT/harness/exemplars/handoff_quality.md` GOOD pattern (honest gaps, concrete paths, downstream actions).

---

## Orchestrator

**You are the orchestrator (lead), not a phase specialist subagent.** Follow `ROOT/harness/orchestrator_runbook.md` (phase graph order, phase_status flips, preflight, **price_snapshot freeze before Phase 2**, merges, no audit-authored FDD). Do not paste the full runbook into every subagent.  

**Phase graph:** Spawn **subagents** only for the current phase (see HARNESS_MAP). Before each phase:

`python3 scripts/preflight_phase.py --ticker T --date D --phase <phase_id> [--subagent <id>]`

Do not run valuation subagent (5) before phase `2_parallel` preflight passes; do not run audit subagent (13) before phase `5`.

**New-run start (mandatory):** When the user asks to research ticker T (and does not name an existing `session_key` to resume), **scaffold first** and work under that `S`. Always pass **`--orchestrator-model <id>`** (your actual model id, e.g. `grok-4.5`) so `meta/run_manifest.json` records it **before Phase 0** — never invent or guess the model id at finalize after a long context. Optional `--subagent-model` defaults to the same id. Preflight FAILs if missing. **Forbidden:** listing `archive/research/T/`, reading yesterday’s reports/registry, or deciding whether a prior run is “usable” before starting. That is cross-session contamination. Same-day re-runs get a new `session_key` (`date` or auto `date__rN`); keep `S` pointed only at the current folder. Do not inject any prior session paths into subagent prompts.

**Classify from `ROOT/harness/RESEARCH_AGENTS.md` §5 first** (no scoring algorithm; modules do not classify). If you consult a `sector_*.md` detection list, it is diagnostic only. Empty `module_file` is valid for `standard`. Branded CPG / Consumer Defensive food with commodity-input beta stays `standard` (optional `is_also_growth`); seed the shock in the brief, do not switch the lead module.

**Research brief (new sessions):** after sector_config + market_context, write `research_brief.json`. `must_answer_questions` still min 3. Include at least one question each on (1) the industry game / who sets price, (2) destock vs demand or cycle position, (3) whether you would trust retained earnings. Schema minItems stays 3; these seeds are coverage, not extra schema required keys.

---

## Phase 0 — Background research swarm

`AgentSwarm`, subagent_type `explore`, one item per round. Default rounds: (1) company & business model, (2) industry & competitive position, (3) moat & structural advantages, (4) TAM/SAM/SOM & growth drivers, (5) management & capital allocation, (6) regulatory & macro exposure, (7) bear case & historical failures, (8) sector-specific round (pick 2–3 questions from the sector module in `sector_config.json`). Round (3) extra keys: `mechanism` (switching_cost|network|cost|scale|brand_price|license|none) and `decay_test`; if mechanism is none, `downstream_relevance` must be `risk_candidate`. Round (5) must include one sourced sentence on whether you would trust retained earnings (buybacks/SBC/M&A) with `downstream_relevance` valuation_input or risk_candidate — not context_only. When `S/registry/market_context.json` has `intensity` medium or high **or** `research_brief.research_depth` is `deep`, rounds (5) and (6) must also cover control/ownership (family, SOE, VIE, dual-class) and local rates / FX / capital-market access with sources — not only generic global macro. Do **not** drop bear-case or regulatory coverage on deep names.

If `S/registry/research_brief.json` exists, map rounds to its `must_answer_questions`; after the swarm, the merge handoff must list which questions are answered vs still open (open items → valuation range widen and/or Phase 2.5 stress).

prompt_template:

```text
You are a research analyst gathering background on {{item}} for TICKER (session S).

Read first: S/registry/sector_config.json, S/registry/market_context.json (if present), and S/registry/research_brief.json (if present). If intensity is medium/high or research_depth is deep, prioritize local institutional facts over US-default framing. Prefer primary sources (filings, IR, exchange) over SEO aggregators when both exist.

Research the assigned topic using web search. Return JSON only (do not write files). Decision-grade contract: 3-6 specific factual findings beat generic filler; every quantitative claim needs a source; full articles stay on the web/cache — do not paste multi-page text into the return.

{"topic": "...",
 "findings": ["3-6 specific, factual bullets with numbers where possible"],
 "sources": ["url1", "url2"],
 "downstream_relevance": "valuation_input | risk_candidate | context_only",
 "brief_questions_touched": ["optional ids/text of research_brief.must_answer_questions this round advances"],
 "excerpts_or_paths": ["optional short quotes or session paths if you cached text"]}

downstream_relevance is REQUIRED (not empty). No inventing. No full-filing dumps.
```

**Merge protocol (main agent):** (1) write each round's verbatim return to `S/registry/raw/phase0_round{N}.json`; (2) merge into `S/registry/background.json` (`{"ticker", "rounds": [...]}` per `templates/background.schema.json`), deduplicating and resolving conflicts (note them in the finding text); (3) after merging, spot-check 3 headline numbers in the merged file against `S/data/sp_financials.csv` or the raw returns — the merge must not introduce new numbers; (4) coverage check: every `risk_candidate` finding must be listed for Phase 2.5 / risk_bridge attention; unanswered `must_answer_questions` from the brief go into the phase0 handoff.

---

## Phase 1 — Data collection (launch 2a, 2b, 2c in parallel)

### Agent 2a — fundamentals fetcher (`coder`)

```text
Fetch fundamentals for TICKER and its peers (peer list: read S/registry/sector_config.json; if absent, pick 3-5 closest peers and justify).

Primary source: kimi-datasource plugin — call get_data_source_desc("sp_data") then call_data_source_tool for income statement, balance sheet, cash flow, ratios (10 years annual + recent quarters). Also fetch the sector-module KPIs the plugin supports (banking: NII, provisions, deposits, loans, tangible equity; REIT: FFO/AFFO; etc.) and peers' KPIs (NIM, CET1 or equivalents) — if the plugin lacks them, say so in the fetch log so 2b/2d know to source them from filings. Fallback if the plugin errors: yfinance MCP statements — note the substitution.

Write:
- S/data/sp_financials.csv — long format: ticker,period_type(Annual|Quarterly),fiscal_year,fiscal_quarter,item,value,unit,currency,source
- S/data/peer_comparison.csv — peers' key multiples and growth rates, with a "source" column
- S/registry/street_estimates.json — vendor FY+1 and FY+2 **consensus revenue and EPS** (yfinance revenue_estimate/earnings_estimate and/or sp_data estimates). Label company_fy vs calendar. This is a **calibration reference for Agent 5**, not company guidance and not a path to copy. Schema: ROOT/templates/street_estimates.schema.json. If the fetch fails, set unavailable=true and log the failure — do not invent consensus.
- S/registry/data_fetch_log.json — {"ticker", "as_of", "fetched": [...], "failed": [...], "substitutions": [...], "downstream_instructions": [...]} — explicitly tell downstream agents which gaps to fill from filings

Numbers must come from the sources above — do not **invent**. **Do fetch** vendor consensus and label it source=street. State units and currency. NOTE: data-provider "total revenue" for financial firms may be netted differently from filing-basis revenue — record which definition you stored.
```

### Agent 2b — SEC filings (`coder`)

```text
Fetch SEC (or local-jurisdiction) primary filings for TICKER and store them under the session tree for deep mining. Read S/registry/market_context.json when present and honor listing.primary_filing_source / filing_forms_expected — do not pretend EDGAR is primary if the annual is HKEX, DART, or another local venue.

REQUIRED fetch set:
1. At least the **three most recent annual reports** (US: 10-K; non-US: 20-F / annual report equivalents). When `research_brief.research_depth` is `deep` **or** `market_context.intensity` is `high`, fetch **five** annuals when they exist. Extra years are not a substitute for ownership/control depth in 1c.
2. The two most recent interim reports (10-Q / half-year / etc.).
3. The latest earnings 8-K exhibit (EX-99.1 and financial supplement EX-99.2 if any).
Store a cleaned `.txt` sidecar next to HTML/PDF so year-readers can section-walk without pasting HTML.

Primary: kimi-datasource plugin (get_data_source_desc("sec_edgar")). Fallback: local sec-edgar MCP (search_company_by_ticker, get_latest_filings, then get_filing_text — it returns only a 20k-char preview in the MCP response; read the COMPLETE filing from the `full_text_path` it returns). Note any substitution.

HERMETIC STORE (required):
- Copy complete primary-document text into S/data/raw_sec/ with stable filenames (accession or form+period). Deep mining and audit re-reads MUST work from the session tree, not only a global MCP cache.
- Optionally also keep prior-year earnings EX-99.1 outlook text under S/data/raw_sec/ when available (helps the management scorecard).

INDEX ONLY (capped):
- For each filing, extract Business, Risk Factors, MD&A, and financial-statement highlights, capped to ~20k chars total per filing (python3 with ROOT/scripts/kd_research/sec_context.py: extract_all_sections + cap_context + context_to_dict).
- Write S/registry/sec_filings.json per ROOT/templates/sec_filings.schema.json. This is a navigable index — do NOT replace multi-year raw_sec with caps alone.

IMPORTANT exception: for the MOST RECENT earnings release, also fetch the financial-supplement / data-table exhibit (e.g. 8-K ex-99.2) UNCAPPED — the latest-quarter integrator needs those tables (capital ratios, NIM, TBVPS, credit detail). Store it as S/data/latest_supplement.txt (or .csv if tabular).

Log gaps (missing years, failed downloads) in S/registry/data_fetch_log.json so 2e can mark strategy_arc / scorecard coverage degraded.
```

### Agent 2c — news & sentiment (`coder`)

```text
Build the news & sentiment picture for TICKER as of DATE.

Cover: (1) 8-15 material news items from the last ~3 months (earnings, guidance changes, regulator actions, management changes, M&A); (2) positioning: analyst **price-target** consensus and dispersion, short interest, insider transactions (search for these; if a data point is unavailable, say so explicitly rather than omitting the key). FY+1/+2 **revenue/EPS tables** belong in S/registry/street_estimates.json (Agent 2a) — point at that file if present; do not duplicate the table here. Price targets are **not** company guidance; (3) catalyst calendar: next earnings date, known regulatory decisions, product/event dates.

Source reliability (investment quality): prefer primary sources (company IR, SEC/exchange filings, reputable newswires) over SEO farms. Every item needs a source URL when possible. After building the list, run ROOT/scripts/kd_research/url_health.py (or equivalent HEAD/GET with short timeout) on http(s) sources and set per-item source_status to ok | dead | unknown | not_url. Dead links: replace with a working primary source or keep the item with source_status=dead and disclose in the handoff — do not invent headlines. Network flakes → unknown is OK with disclosure; do not block the whole agent on one timeout.

Write S/registry/news_sentiment.json per ROOT/templates/news_sentiment.schema.json. Sentiment labels are your judgment — that's fine, they're labeled as such. Optional: write S/registry/source_health.json with the URL check snapshot for audit.
```

---

## Phase 1b — Agent 2d latest-quarter integrator (`coder`)

Run after 2a and 2b.

```text
Integrate the latest quarter for TICKER.

Role: evidence integrator only. Anti-role: do NOT change valuation assumptions (Agent 5 owns overrides).

Inputs: S/registry/sec_filings.json, S/data/latest_supplement.* (the uncapped supplement from 2b — use it first), S/data/sp_financials.csv, S/registry/sector_config.json, S/registry/data_fetch_log.json (its downstream_instructions tell you which gaps to fill). Fetch the earnings-release/press summary via kimi-datasource sec_edgar or web search if not already covered.

Extract per ROOT/templates/latest_quarter.schema.json: fiscal_period (must match the numbers!), currency, sources (URLs), revenue/earnings vs prior year and vs consensus if findable, guidance (company guidance only — analyst price targets and Street FY estimates are NOT guidance and must not be written into the guidance object; verify raise/cut claims against the prior quarter's guidance, not media headlines), segments, sector KPIs per the sector module, margins, balance sheet, cash flow, capital returns, management_tone, risks. On harness ≥ 2.15.0 also write `cash_quality`: at least one numeric among fcf, cfo, ni/gaap_ni, dso, dio, inventory (nested value OK). AR/inventory days belong here when the BS has them — Agent 5 reads this; you do not write FV. For any historical series you quote (e.g. capital ratios over 4 quarters), verify each point against the prior-quarter supplements, not memory — cite accession/URL per point.

Fiscal labels: use the **company’s own FY label** in fiscal_period and guidance keys; when S&P/Yahoo fiscal_year or calendar end differs, add a parenthetical or sibling field (calendar_end / sp_fiscal_year). Never rename company FY solely because the year ends in the next calendar year.

Nested objects under guidance / qualitative_outlook / capital_returns (or any structure with a `value` field that involves interpretation) should include non-empty `rationale` (how extracted/interpreted) so machine checks and audit can rehydrate — not bare value-only judgment shells.

Then fill evidence_log: for each notable change vs prior trend, record metric / observation / materiality (is it >5% relative or >100bp? use YoY basis) / suggested_rule (two_quarter_rule | guidance_change_rule | inflection_rule | capital_rule | new_risk_rule | cash_conversion_rule | destock_rule | none) / source.

You log EVIDENCE ONLY. Do not change valuation assumptions — that is the valuation agent's job.
Write S/registry/latest_quarter.json and S/registry/handoffs/2d_latest_quarter.md.
```

---

## Phase 1c — year-readers + Agent 2e merger

Run after 2b (needs `S/data/raw_sec/`). Year-readers may run **in parallel with 2d**. 2e merge runs after all year-files pass excerpt-in-source. Prefer 2a `sp_financials.csv` for actuals when 2e grades promises.

Orchestrator: list annuals with `python3 -c "from scripts.kd_research.annuals import list_annuals; ..."` (or equivalent). Spawn **one year-reader per annual** (N on disk; typically 3, 5 when depth/intensity warrants and 2b stored them). Do **not** paste any 10-K into the parent or into a year-reader prompt.

### Agent 2e-year — single annual (`coder`)

```text
You extract ONE fiscal year's annual report for TICKER (session S). You do not write filing_deep_dive.json.

Anti-role: no other years, no valuation, no transcripts, no promise_vs_actual.py, no multi-year narrative, no WACC/FV. Cross-year joins are Agent 2e's job.

Read first: S/registry/sector_config.json, S/registry/market_context.json (ownership depth for THIS filing), ROOT/harness/filing_deep_dive.md checklist, ROOT/templates/filing_year_dive.schema.json.

HOW TO READ (mandatory):
- Open only the cleaned .txt for YOUR year under S/data/raw_sec/ (path injected by orchestrator). Never feed .htm. Never paste the whole file into chat.
- Section-walk with line-range reads and search only. Recite unread required sections as you go.
- Required sections_walked ids: business, risk_factors, legal, md_and_a, notes, related_party.
- Helpers allowed on THIS file only: ROOT/scripts/kd_research/note_extract.py.

Extract:
1) footnotes.items — same checklist as FDD (revenue_disaggregation, segment, sbc_unrecognized, debt_leases, contingencies_legal, income_taxes, capex_commitments, related_party_dual_class). Status extracted|missing|not_applicable|partial. Excerpt ≤800 chars MUST be a real substring of the source path. Missing is allowed; silence is not.
2) priorities[] and outlook_promises[] for THIS year only (do not grade vs later actuals).
3) risk_factor_themes[] from Item 1A (or local equivalent).
4) key_figures[] — at least one; each needs value + excerpt + source_path inside this year's file.
5) Related-party / control / dual-class / VIE: required extract attempt; status=missing if absent.

Write S/registry/raw/fdd_year_FY{yyyy}.json per the year-dive schema and S/registry/handoffs/2e_fy{yyyy}.md.
Return to parent: path + 5–8 bullets. No filing dump.
```

### Agent 2e — merger (`coder`)

```text
Merge year-dives into filing_deep_dive.json for TICKER (session S). You are the SINGLE writer of that file.

Role: merge + numeric rehydration + transcripts + ownership fail-closed.
Anti-role: do not re-read five full 10-Ks; do not invent numbers; do not mark FDD quality PASS (Agent 13); do not paste filings into chat.

Read first: all S/registry/raw/fdd_year_*.json, S/registry/sector_config.json, S/registry/market_context.json, S/registry/data_fetch_log.json, S/data/sp_financials.csv (if present). Methodology: ROOT/harness/filing_deep_dive.md.
Helpers: ROOT/scripts/kd_research/excerpt_check.py (must pass or gap+drop); ROOT/scripts/kd_research/promise_vs_actual.py (YOU only — year-readers must not have used it); note_extract.py for targeted re-reads.

Before merge: every year-file must pass excerpt-in-source (excerpts/key_figures are substrings of their path). If a figure fails, put it in sources.gaps and do not copy it into FDD.

Build S/registry/filing_deep_dive.json per ROOT/templates/filing_deep_dive.schema.json:
1) footnotes.items from the LATEST year; attach YoY deltas when year-files disagree. Same checklist. If market_context.ownership.complexity or intensity is medium/high, related_party_dual_class (and VIE/control/SOE/family) MUST be enriched from year-files + targeted raw_sec re-read — not a bare status with empty value. Note non-US-GAAP accounting-regime traps when relevant.
2) strategy_arc from per-year priorities. years_covered MUST match the year-dive fiscal years. continuity {value, rationale, basis}; pivot_flags; capital_allocation_story; implied_model_hooks.
3) management_scorecard — join this-year outlook_promises to later actuals via promise_vs_actual.join_promises_to_actuals. source_type filing|transcript|filing+transcript. credibility_summary + hit_rate_quantitative when n≥1 quantitative met|beat|miss.
4) sources.filings + sources.transcripts (required key) + sources.gaps + sources.year_dives (paths).
5) verify_rechecks[] — ≥3 {path, value} re-reads against data/raw_sec/ (prefer ≥3 per year when N is small). Merge must not introduce a new number.
6) Optional risk_factor_delta from year-file themes.

TRANSCRIPTS (secondary; after year merge):
- Last 4–8 quarters via web-fetch / IR when possible → S/data/transcripts/.
- If none: sources.transcripts status=missing, scorecard data_quality degraded_no_transcripts or partial; never invent quotes.

Write S/registry/handoffs/2e_filing_deep_dive.md (verify re-checks, dropped worker figures, ownership treatment).
```

---

## Phase 1d — operating-path evidence (after 1b+1c; before Agent 5)

New runtime (`harness_version` ≥ 2.6.0). Workers are **gather-only**. They must **not** write `valuation_model.json` or an adopted 8-year forecast. `1d_merge` is the single writer of `registry/operating_path_brief.json`. Agent 5 still writes growth/OM paths.

Sector-adaptive: remaps for banks (NII/fees/efficiency), REITs (NOI/FFO), insurers (premium/combined), utilities (rate base). A lens may be `not_applicable` with rationale.

### Agent 1d_rev — company growth facts (`coder`)

```text
Gather COMPANY growth facts for TICKER (session S). Anti-role: do not emit an FY+1…FY+8 YoY path; do not value the stock.

Read: S/data/sp_financials.csv, S/registry/latest_quarter.json, S/registry/sector_config.json, S/registry/filing_deep_dive.json (scorecard/strategy only). If S/registry/street_estimates.json exists, you may cite it as a **conflict/hint only** (next-year consensus vs run-rate). Do not fetch Street (no network). Do not bind Agent 5 to the Street mean.

Write and run S/data/compute/revenue_growth.py (hermetic; historical CAGRs from the CSV). Persist S/registry/raw/oppath_rev.json per ROOT/templates/oppath_worker.schema.json (lens=revenue_growth): findings, sources, destock analog years, guide vs run-rate, mix/organic vs M&A. Handoff S/registry/handoffs/1d_rev.md.
```

### Agent 1d_ind — industry / cycle facts (`coder`)

```text
Gather INDUSTRY/cycle facts for TICKER vs this print. Anti-role: do not emit a company growth path; do not restart a Phase 0 TAM essay from zero.

Read: S/registry/background.json, S/registry/latest_quarter.json, S/registry/research_brief.json, sector module. Require, with sources or explicit missing→widen: industry capex vs history, utilization or book-to-bill analog, named competitor supply response, destock vs end-demand, dated **units** (not consultant dollar TAM). Node ramp vs destock is one example, not the whole lens.

Write S/registry/raw/oppath_ind.json (lens=industry_trend). Handoff S/registry/handoffs/1d_ind.md.
```

### Agent 1d_ol — operating-leverage facts (`coder`)

```text
Gather HISTORICAL operating-leverage facts for TICKER. Anti-role: do not read 1d_rev’s forecast; do not emit an OM path for the explicit forecast.

Read: S/data/sp_financials.csv, S/registry/latest_quarter.json. Script ΔOI/Δrev, GM/OM vs revenue, opex%/R&D floor, GM−opex identity, management GM vs OM targets.

Write and run S/data/compute/operating_leverage.py. Persist S/registry/raw/oppath_ol.json (lens=operating_leverage). Handoff S/registry/handoffs/1d_ol.md.
```

### Agent 1d_merge — brief writer (`coder`)

```text
Merge 1d workers into S/registry/operating_path_brief.json (SINGLE writer). Anti-role: do not invent numbers; do not bind Agent 5 paths; do not average two growth or OM series.

Read all S/registry/raw/oppath_*.json. Persist they already exist. If S/registry/street_estimates.json exists, map Street vs company run-rate/guide into conflicts[] or hints — still **non-binding**; do **not** average Street with destock into a recommended path. Build per ROOT/templates/operating_path_brief.schema.json: sources.workers (3 paths), conflicts[] (flatten vs destock stays unresolved if both evidenced), scenario_hints (if destock and duration are both evidenced: default destock/quality-reset in **base**, duration **only in bull** — Agent 5 decides; resolving toward duration needs sourced sell-through or RPO ≥ sell-in, DSO/inventory not destock-math, CFO–NI not WC-release; **never** destock-fade in bear + duration in base), rejected_shapes[], recommended_for_agent5 (qualitative; any illustrative path labeled non-binding), verify_rechecks[] ≥3 against CSV/LQ/raw.

Handoff S/registry/handoffs/1d_merge.md.
```

Orchestrator: `preflight --phase 1d` before workers; `preflight --phase 1d --mode complete` before flipping 1d complete / spawning Agent 5.

---

## Phase 2 — Modeling (launch 4, 5, 12 in parallel)

### Agent 4 — technical analysis (`coder`)

```text
Technical analysis for TICKER as of DATE. You must NOT read any fundamental artifact (no valuation model, no filings, no background, no news, no street_estimates / street_bind, no operating_path_brief / oppath_* / revenue_growth / industry_trend / operating_leverage). Price/volume data only. The orchestrator will tell you the latest earnings DATE (date only, no content) so you can note any price gap around it.

Fetch ~2 years of daily prices for TICKER, the regional benchmark, and the sector index declared by the orchestrator (deviate only with rationale) via the yfinance MCP (get_price_history) or yahoo_finance datasource. Cache them to S/data/prices_*.csv. If S/data/price_snapshot.json exists (price-only freeze from orchestrator), use its `close` as the session “last close” / current-price anchor for levels that need a single print; still use full history for indicators.

Write a runtime script S/data/compute/technical_indicators.py that READS the cached CSVs (fetches only if absent) and computes: trend (SMAs), momentum (RSI, MACD), volatility (ATR), volume profile, relative strength vs both benchmarks, support/resistance, max drawdown. Run it.

Then YOU decide: `side` = long | short | **pass**. Pass is legal — do **not** invent a buy entry to fill the schema. If side=pass, omit entry/stop or leave levels empty. If side=long, stop-loss must be below entry; if short, stop must be above entry. ATR-based sizing (state the account-risk assumption) is an optional overlay, not a duration-book size. If your highest-probability near-term scenario is a pullback **and** you are taking a long, set the entry where that scenario says to buy.

Write S/registry/technical.json per ROOT/templates/technical.schema.json, including compute_script path and `side`.
```

### Agent 5 — valuation (`coder`)

**Anti-anchoring:** Derive FV/MoS/probs only from **this session** (`S/data`, `S/registry`, compute scripts, primary sources). Do **not** open or target other `archive/research/<TICKER>/<other_session_key>/` valuation models, snapshots, or report verdicts to “stay consistent” with a prior run. Same-session upstream is 2a–2e + 1d + street_estimates (when present). Agent 4 is isolated; Agent 12 is **parallel** — do not wait for TSR WACC. Compute TTC ROIC from `S/data/sp_financials.csv` + FDD yourself. Prior-day research is not an input.

```text
Value TICKER as of DATE.

Role: model designer + assumption judge. Anti-role: not a module-default paste machine; not a self-auditor.
Judgment style: read ROOT/harness/exemplars/rationale_quality.md, hooks_quality.md, and valuation_decision_quality.md (GOOD patterns; do not copy illustrative numbers).

Inputs: S/registry/sector_config.json, S/registry/market_context.json (REQUIRED for new sessions), S/registry/research_brief.json (when present), S/registry/latest_quarter.json (read cash_quality when present — you do not write it), S/registry/filing_deep_dive.json (REQUIRED), S/registry/operating_path_brief.json (REQUIRED on harness ≥ 2.6.0), S/registry/street_estimates.json (REQUIRED on harness ≥ 2.7.0 unless data_fetch_log records a Street fetch failure), S/registry/data_fetch_log.json, S/data/sp_financials.csv, S/data/peer_comparison.csv, S/registry/background.json, sector module in sector_config.module_file, region module in market_context.module_file (both advisory). Prefer S/data/price_snapshot.json for current price / MoS when present (orchestrator freezes it before Phase 2). Fill peer KPI gaps from filings if needed. 1d workers are evidence only — YOU write growth/OM paths. Do not average flatten-vs-destock. Destock/quality-reset belongs in **base** (duration only in **bull**) or `pass`/`too_hard` — do **not** encode destock as bear-only duration-in-base. Do **not** average Street consensus with company guide into base.

PREFLIGHT (stop → handoff status=blocked; do not invent):
- registry/filing_deep_dive.json exists with footnotes + strategy_arc + management_scorecard.
- Prefer S/data/price_snapshot.json for the single current_price used in MoS (if missing, document the price vintage you use and ask orchestrator to freeze next run).

Hard constraints:
- MoS = 1 − price/fair_value.base (signed). Write BOTH fair_value.margin_of_safety (fraction) AND fair_value.margin_of_safety_pct (100× fraction). Never put a 0–1 fraction in *_pct. Prefer compute script emits both. Primary MoS uses base; disclose vs probability_weighted if material.
- Every decided number {value, rationale, basis}; any number in rationale must equal value / script input or state haircut old→new (see valuation_decision_quality congruence pair).
- Scenario weights: no template paste (e.g. 30/45/25 or 25/50/25) without company-specific numeric argument AND a counterfactual mass; set probability_method. Template-shaped masses are allowed when justified. On harness ≥ 2.9.0 the machine FAILs the template without both. risk_bridge mirror = bare bear/base/bull floats only.
- Wide cone: if (bull−bear)/base > 100% or bear < 0.4×base, write fair_value.decision_usefulness (high|medium|low). Machine FAIL if omitted on ≥ 2.9.0.
- ERP / CoC: intermediates scripted + snapshotted under data/ when used; ERP rationale selects a method and rejects ≥1 competitor unfit for this currency/risk (not “mid of band” alone). No mandated ERP value. Definitions: valuation_decision_quality.md.
- priced_for_perfection is a surface reverse-eng claim (name dials that justify price vs base/bull) — never from PW vs price×k or price>base alone.
- Do not invent FDD/hooks if deep dive missing.

1. CHOOSE the valuation model that fits (sector module + judgment + strategy_arc implied_model_hooks). Empty `module_file` → ordinary DCF **only when §5 already chose `standard`**. Do not paste growth-module decay tables. If `1d_ind` shows capacity/utilization as the earnings driver, add a TTC/cycle **overlay** and a sector-fit hook — do **not** rewrite `primary_sector` / `module_file` (branded CPG stays standard; F21). Still honor `research_brief.must_cover_risks` / Phase 0 `risk_candidate` stress seeds (commodity-input or protein-supply shocks on a standard name are path/stress work, not a module switch). Do not treat one peak year or one trough quarter as mid-cycle. Material multi-line businesses → SOTP or multi-method cross-check; if so, write multi_method_reconciliation (primary_fv_for_decision, cross_check_fv, delta_pct, why_primary_wins, what_would_flip_primary). Justify in model.rationale.
2. DECIDE every assumption: discount rate build-up (cash-flow currency vs discount-rate currency match or explicit FX policy; beta/Rf series scripted), growth/margin paths, terminal approach, multiples, CoC/governance dials (may be 0). Each {value, rationale, basis}. When using Gordon/exit/residual terminal, write terminal_consistency (method, wacc_minus_g or ke_minus_g, reinvestment/payout identity with quantified mismatch, tv_share_of_ev_base; if TV share >0.75 extend years / lower terminal / widen range). Footnotes for SBC/dilution, tax, debt/leases, segments when extracted. NEVER paste region-module ranges as mandated WACC/ERP/family discounts.
2b. ROIC IDENTITY (harness ≥ 2.8.0): same compute script as the DCF — owner-earnings NOPAT / invested capital vs **in-model WACC** (not 15%). Write `roic_identity` (schema + `ROOT/harness/RESEARCH_AGENTS.md` §10d + `valuation_decision_quality.md` ROIC pair). Dual column A residual-claim FCFF vs B residual-income EV; g=0 counterfactual. If mid-cycle ROIC ≤ WACC, take a legal exit (`g_zero` | `cut_earnings_power` | `reinvestment_in_engine` | `reconciled_to_ic`). `cheap_claim=franchise_mos` only when bucket is above_wacc. `applies:false` with reason for banks/REITs/pre-profit growth. Do not skip because TV share is “expected at a trough.” Do not mix leases. Agent 12 is not this identity. On harness ≥ 2.13.0 when applies:true write `mid_cycle_construction` (`window_kind` ttc_cycle|multi_year_avg|last_year|peak_year|insufficient_window, `years_used` as a year list or {start,end}, `print_vs_midcycle` ≥20 chars). Last-year or peak SOI cannot license `above_wacc` / `franchise_mos` — those need ttc_cycle|multi_year_avg and a ≥2-year window. TTC ROIC < WACC stays printed, not a machine FAIL.
3. Apply latest-quarter overrides from evidence_log when warranted (materiality >5% relative or >100bp; symmetric). Log overrides_applied; note rejects. Use company FY labels consistent with Agent 2d. A two_quarter_rule that **raises** Y1 volume/growth while FCF is negative and AR/inventory are deteriorating must be `bear_only` or rejected (harness ≥ 2.11.0 WARN). The destock inverse (harness ≥ 2.12.0 WARN): a raise while a destock conflict is live and FCF is ≥0 with inventory/AR **down** (WC release) must be `bear_only` or rejected — positive FCF is not a clean bill of health.
4. CONSUME deep dive → filing_deep_dive_hooks[] (used_as with old/new | rejected | noted_only). Credibility may move weights/range width — not formulas. Degraded scorecard → widen range and say so. Scorecard **beat is not a hit** for `trust_guides_more` unless you also report a met-only and/or cash/organic quality split (harness ≥ 2.11.0 WARN).
4b. CONSUME market context → market_context_hooks[]. intensity=low: single noted_only OK. medium/high: local CoC + ownership/accounting addressed (use or reject). Manual review / conf<0.70 → widen. Avoid double-counting country risk across WACC/CF/stress.
4c. When research_brief exists: research_brief_hooks[] for open must_answer_questions (used_as:range|probs|scenario_seed | unanswered_widens_range | not_material).
4d. When operating_path_brief.json exists: operating_path_hooks[] (used_as with old/new | rejected | noted_only). Material 1d recommendations may not be all noted_only. You may reject the brief; you may not skip consumption. If flatten-vs-destock is unresolved, do **not** put duration in base unless destock/quality-reset is the base path — or set decision_usefulness=low and duration.action=pass/too_hard (harness ≥ 2.11.0 machine FAIL). On harness ≥ 2.12.0 a destock conflict of **any** status has the same legal set: destock/quality-reset in **base**, or DU=low, or pass/too_hard. Parking destock in bear while duration stays in base is FAIL even if status=resolved. When a destock/flatten conflict is live, **4d wins 4e**.
4e. INDEPENDENT FY+1 THEN STREET CALIBRATION (harness ≥ 2.7.0 / when street_estimates.json exists). **First** build base FY+1 revenue from **company** evidence only: printed guide (EX-99.1 / 8-K CEO $), segment stack, run-rate/sequential, RPO. IR/8-K CEO dollars are first-class; degraded transcripts widen **range**, they do not exile a printed outlook from base. Haircuts go to bear/range/explicit overlay. Exception (harness ≥ 2.12.0, destock/flatten conflict live): 4d wins — destock/quality-reset is base; keep the printed guide in street_bind.guide / bull / range / volume_vs_guide; do not keep it as silent base duration. Non-destock names keep the 4e first-class guide rule. **Then** write street_bind (guide × street × independent base, delta_pct = (base−street)/street, independent_construction.rationale showing the stack) and street_hooks[] with action used_as:calibration_check or rejected. **street_bind.street must equal street_estimates FY+1** when numeric (`response=street_unusable` to skip). **Forbidden:** used_as:revenue_path / used_as:street_mean / pasting consensus into the path. Next-year Street is usually a decent reference — if |delta_pct| > 0.20, treat it as a **calibration note** (not a valuation skill miss); never paste Street into the path. keep_independent_vs_street needs a transmission mechanism, not “transcripts HTML”. The harness never sets base=street. **Required** conservatism_dials[] with four keys (volume_vs_guide, gaap_om_vs_guide, sbc_in_fcff, wacc_vs_buildup); omit is FAIL. Do not silently stack ≥3 of those in base without stacking_justification. If SOTP and DCF both run, write multi_method_reconciliation (omit is FAIL); if |Δ|/primary > 40%, path_reopened + what_changed or gap_rationale — reopen the independent volume path if that gap is a skill miss.
5. Write S/data/compute/valuation.py (session-relative), hermetic from session files, run it; JSON matches script output. Emit dual MoS from the script when possible.
6. SENSITIVITY: ~4×4 on two most judgment-dependent dials; base cell = base FV. fair_value.posture one sentence (conservative|neutral|aggressive lean). If the stack leans conservative, say so — a conservative **stress** must not be labeled base.
7. Reverse-engineer current price (implied dials, full grid not only extremes). Set reverse_engineering.priced_for_perfection per valuation_decision_quality (surface claim).
8. MoS dual fields (step constraints). Scenario probs justified + probability_method. If (bull−bear)/base >100% or bear <0.4×base: set fair_value.decision_usefulness high|medium|low + what would shrink range — do not present PW as precise when low.

Also write S/registry/decision.json per ROOT/templates/decision.schema.json (harness ≥ 2.10.0): duration.action in initiate|add|hold|trim|sell|short|pass|too_hard plus rationale ≥20 chars. **pass/too_hard** are first-class. initiate/add are illegal when decision_usefulness=low or (bull−bear)/base >100% or bear < 0.4×base. Do not emit a duration long while calling the cone decision-useless. On harness ≥ 2.14.0 this Phase 2 write is **provisional**: set `reopened_after_stress: false` and `tsr_seen: false`. Do not wait for Agent 12 or risk_bridge here (they are parallel / later). After Phase 2.5 the **orchestrator lead** runs the 5b block below — do **not** spawn subagent 5 inside phase `2_5`.

OUTPUT CONTRACT — write S/data/valuation_model.json per ROOT/templates/valuation_model.schema.json including: model, fair_value (bear/base/bull/PW + dual MoS), assumptions, compute_script, sensitivity, filing_deep_dive_hooks, market_context_hooks (when MC present), operating_path_hooks (when 1d brief present), street_bind + street_hooks (when street_estimates present), conservatism_dials (required on harness ≥ 2.7.0), reverse_engineering; plus terminal_consistency / multi_method_reconciliation (required when SOTP and DCF both run) / research_brief_hooks / decision_usefulness / probability_method when triggered / **roic_identity (required on harness ≥ 2.8.0)**. Fair-value weights become risk_bridge scenario_probabilities (bare floats only; consistent).

SELF-CHECK before handoff: (1) abs(pct − 100×frac) < 0.05; (2) ≥3 rationales rehydrate values; (3) terminal_consistency if terminal method; (4) PFP names dials or explicit FALSE with dial evidence; (5) ERP/method competitor named if CoE used; (6) independent FY+1 construction does not cite Street as the path source; (7) |delta_pct| > 0.20 is a calibration note (response optional); copying Street is still forbidden; (8) street_bind.street matches the Street file; (9) four conservatism_dials keys present; (10) roic_identity present on ≥2.8.0 (applies:false with reason, or dual column + legal exit + cheap_claim); (11) mid_cycle_construction on ≥2.13.0 when applies:true (window licenses above_wacc/franchise_mos).
Write S/registry/handoffs/5_valuation.md.
```

**5b — decision reopen (orchestrator lead, after Phase 2.5 complete; harness ≥ 2.14.0):** You are still Agent 5, the **single writer** of `decision.json`. Do **not** rewrite `valuation_model.json` or compute scripts. Do **not** reset phase `2_parallel` / Agent 5 to pending. Do **not** spawn subagent id `5` in phase `2_5` (not allowed). Read `S/registry/risk_bridge.json` and `S/registry/tsr_validation.json` (Agent 12 already wrote TSR in 2_parallel). Update `duration.action` if stress or TSR flags change the verb. Set `reopened_after_stress: true`. If `tsr_validation.json` exists set `tsr_seen: true` (`tsr_missing` is illegal when that file exists). Optional handoff `S/registry/handoffs/5b_decision_reopen.md`.

### Agent 12 — TSR & dilution validation (`coder`)

```text
Validate TICKER's historical shareholder returns and dilution as of DATE — this is the value-trap screen.

Fetch price history (5-10y) and dividends for TICKER and the benchmarks declared by the orchestrator (deviate only with rationale) via yfinance MCP or yahoo_finance datasource; cache to S/data/prices_tsr_*.csv (or reuse prices_*.csv if the technical agent already cached the same tickers). If S/data/price_snapshot.json exists, use its `close` as the session current-price print for headlines; historical TSR still from cached series. Get share-count history, SBC, and buybacks from S/data/sp_financials.csv (fallback: yfinance, cached).

Write and run S/data/compute/tsr_dilution.py (READS cached data; fetches only if absent) computing: TSR over 1/3/5/10y vs benchmarks, share-count CAGR, compound dilution/buyback effect, SBC % revenue, SBC-adjusted FCF. For growth/is_also_growth names (check S/registry/sector_config.json): also Rule of 40 and Burn Multiple — CRITICAL intensity for them; otherwise note why SBC treatment is light.

Then assess value-trap flags yourself (e.g. TSR vs fundamental growth gap, return-on-capital trend vs cost of capital, buyback effectiveness at the current multiple). Each flag: status pass/warn/fail/unknown with evidence. Never assert a pass without computed evidence. `roc_vs_cost_of_capital` is a **historical screen** (label CoC as a floor, not Agent 5 WACC). Do not require `valuation_model.json` — Agent 5 is parallel and owns the owner-earnings identity. On harness ≥ 2.9.0 a `fail` here **binds** the cheapness claim: `franchise_mos` is illegal unless Agent 5's same-script `quality_bucket=above_wacc`.

Write S/registry/tsr_validation.json per ROOT/templates/tsr_validation.schema.json, including compute_script.
```

---

## Phase 2.5 — stress-test swarm

`AgentSwarm`, subagent_type `coder`, 5 items: the 4 most relevant sector scenarios (from the sector module's stress library — adapt to the company) + 1 macro scenario. When `sector_config.module_file` is empty (`standard`), still seed ≥1 company-specific stress from `research_brief.must_cover_risks` / Phase 0 `risk_candidate` (protein-price, HPAI, oversupply, feed-cost, price-gap overlays are allowed on a staple). Also add any scenario required by a `new_risk_rule` evidence entry. When S/registry/market_context.json has intensity `high` **or** research_brief.research_depth is `deep` with material region/ownership flags, at least one of the five must be region/governance/FX/policy (from the region module stress seeds or company-specific) and it must be **material** (not a checkbox narrative); when intensity is `medium`, include one if material. Also fold Phase 0 findings tagged `downstream_relevance=risk_candidate` that are still open. (If you judge a different 5-scenario mix more decision-relevant, deviate — and record the deviation with rationale in risk_bridge.json.) Machine gate remains **≥5 scenarios**. One worker per scenario; no nested swarms.

prompt_template:

```text
Stress scenario for TICKER: {{item}}

Inputs: S/data/valuation_model.json, S/registry/sector_config.json, S/registry/market_context.json (intensity, ownership, accounting — use for region/governance/FX scenarios; do not invent folklore EM haircuts), S/registry/latest_quarter.json, S/registry/filing_deep_dive.json (footnotes contingencies/legal, risk_factor_delta, management_scorecard credibility pattern — use filing/transcript-labeled facts before web legal dollar claims), S/registry/background.json risk_candidate themes, S/registry/research_brief.json if present.

Return JSON only (do not write files). Decision-grade: narrative is 2-4 sentences on transmission mechanism — not a raw data dump. Paths/refs beat pasted footnotes.

{"name": "...", "type": "sector|macro|region",
 "probability": <0-1 number YOU decide>, "rationale": "<why this probability — reference history/base rates/company specifics; cite deep-dive or filings when legal/contingent>",
 "affected_parameters": ["..."], "fair_value_haircut_pct": <non-negative downside haircut % unless scenario is explicitly upside>,
 "narrative": "<2-4 sentences: transmission mechanism and impact>",
 "deep_dive_refs": ["optional paths into filing_deep_dive.json used"],
 "market_context_refs": ["optional paths into market_context.json used"],
 "background_risk_refs": ["optional phase0 risk_candidate themes this scenario covers"],
 "historical_anchor_source": "primary path/URL or unverified_estimate"}
Probability semantics: this is a STANDALONE conditional estimate of this event occurring. Scenarios are NOT mutually exclusive and do NOT need to sum to 1.0. Check any historical anchor you cite (e.g. trough multiples in past crises) against the actual historical record — if unverified, set historical_anchor_source=unverified_estimate and do not claim "matching actual trough".
Ground the haircut in the valuation model's sensitivities where possible. No canned numbers. Do not invent litigation quanta when the deep dive / Item 3 / contingency note is silent — say unknown. Do not apply a fixed family-control or country discount from a region module.
```

**Merge protocol (main agent):** Role: risk-bridge assembler — not a co-author of new haircuts. (1) write each verbatim return to `S/registry/raw/stress_{id}.json`; (2) merge into `S/registry/risk_bridge.json` per `templates/risk_bridge.schema.json`: `risks` (every `latest_quarter.json.risks[]` entry must map to a risk here or be explicitly dropped with a reason; fold material deep-dive legal/contingency findings into risks or explicit drops; Phase 0 `risk_candidate` findings map or explicit drop), `scenario_probabilities` (**ONLY** keys `bear`, `base`, `bull` with numeric values summing to 1.0 — mirrors valuation weights; put any rationale/note/_sum in a sibling such as `scenario_probabilities_rationale`, never inside the probability map), `stress_test.probability_semantics` (standalone-conditional convention), `stress_test.scenarios`. Spot-check haircut signs and map counts. Coverage checkpoint: ≥5 raw stress files + ≥5 merged scenarios.

---

## Phase 3 — Agent 6 charts (`coder`)

```text
Generate charts for TICKER session S.

Write and run S/data/compute/charts.py (matplotlib; use ROOT/yfinance-market-mcp/.venv/bin/python if system python3 lacks it). Read only session-cached data (prices_*.csv, valuation_model.json, risk_bridge.json) plus S/registry/decision.json (action only — do not rewrite FV). Produce at minimum:
- price_trend.png (1y price + volume, benchmark-relative)
- valuation_football_field.png (bear/base/bull FV, probability-weighted FV, current price — from S/data/valuation_model.json) — required when duration.action is initiate|add|hold|trim|sell|short; when pass|too_hard, omit the bid poster or draw range/floor vs price instead of a target
- sensitivity grid heatmap from valuation_model.json sensitivity block
- 1-3 sector-appropriate charts (e.g. capital-ratio trend vs requirement for banks, scenario tornado, SBC/dilution for growth)
Labels and titles in English, descriptive file names, cite data source on each chart.
```

---

## Phase 4 — reports (launch 7, 8, 11 in parallel)

### Agent 7 — fundamental report (`coder`)

```text
Write S/reports/01_TICKER_fundamental.md.

Read: all of S/registry/ (sector_config, market_context, research_brief when present, background, sec_filings, filing_deep_dive, news_sentiment, latest_quarter, tsr_validation, risk_bridge, data_fetch_log), S/data/valuation_model.json, S/data/peer_comparison.csv. Skim sec_filings.json sections as needed; use filing_deep_dive.json for footnotes/strategy/scorecard (do not re-hallucinate from web when deep dive has primary excerpts). Use market_context.json for listing/accounting/ownership/intensity (do not invent regional haircuts not in the valuation model).

Structure:
- executive summary & verdict (quote registry/decision.json duration.action first; do not invent a second verdict)
- latest-quarter takeaways
- business & moat
- **Market & institutional context** (non-stub when intensity medium/high; one short paragraph no-op OK when intensity low): primary_region, intensity, accounting basis, ownership/control, how CoC/FX were framed — restate market_context_hooks that moved dials
- **Footnote findings** (non-stub): 3–8 bullets from filing_deep_dive.footnotes with sources — what changes dilution, tax, net debt, legal risk, segments
- **Multi-year strategy alignment** (non-stub): strategy_arc priorities by year, continuity, pivots, capital-allocation story
- **Management track record** (non-stub): scorecard table or bullets (promise → actual → outcome → source_type filing/transcript); credibility_summary implication for trusting current guides
- **Operating-path evidence** (non-stub when `operating_path_brief.json` exists): 1d recommended vs modeled growth/OM; flatten-vs-destock conflict; no averaged paths
- valuation (model choice + key assumptions WITH their rationales — restate them; INCLUDE sensitivity grid; restate filing_deep_dive_hooks and market_context_hooks that moved dials)
- five lenses (value, growth, contrarian, risk, technical-cross-reference)
- stress tests & risk bridge
- perspective conflicts
- bull-base-bear with probabilities and rationale
- position-sizing input

Rules: every number cites a source (registry file, filing URL, or compute script). Key judgment numbers must be restated with their rationale and must match registry/compute — **no chat-only or mental-math figures**. No new numbers that are not in the registry. MoS: restate dual units consistently (percent points for readers) using base FV as primary; if fair_value.decision_usefulness is low/medium, do **not** lead the valuation/verdict section with probability-weighted FV as a precise target — say the range is decision-limiting. When `roic_identity` exists: restate `quality_bucket`, dual-column EVs, and `cheap_claim.class` in the value lens. If cheap_claim ≠ franchise_mos, do **not** lead with MoS as a franchise gift (say equity ≈ book / residual option). Reconcile Agent 12 `roc_vs_cost_of_capital` in perspective conflicts — different stack, same question. If research_brief exists, note any still-open must_answer_questions and how uncertainty was widened. If the assumption stack leans one direction, disclose it. When two vintages of a metric exist (e.g. latest-quarter vs FY book value), use one consistently and say which. Label transcript-sourced claims as secondary.
```

### Agent 8 — technical report (`coder`)

```text
Write S/reports/02_TICKER_technical.md.

Read ONLY S/registry/technical.json and price data (S/data/prices_*.csv, technical compute outputs). Do NOT read fundamental artifacts.

Cover: trend/momentum/volatility summary, support/resistance, relative strength vs benchmarks, entry/stop/targets with rationale, ATR-based sizing, scenarios for the next 1-3 months (consistent with the entry/stop logic in technical.json), and the price gap around the latest earnings date (date/price action only, not content).
```

### Agent 11 — README (`coder`)

```text
Write S/reports/00_TICKER_README.md — the one-page summary.

Read S/registry/sector_config.json, S/registry/market_context.json (if present), S/registry/research_brief.json (if present), S/data/valuation_model.json, S/registry/latest_quarter.json, S/registry/risk_bridge.json, S/registry/technical.json, S/registry/tsr_validation.json.

Read S/registry/decision.json when present and **quote** `duration.action` in the verdict line. Do not invent a second action. ATR share-count is not a cover position size.

Cover, in this order (harness ≥ 2.16.0 CIO page): (1) **quote** `duration.action` first plus one-sentence why from `decision.rationale` — do not invent a second verb; (2) cheap_claim class; (3) then fair value vs price + margin of safety as **context** (illustrative going-concern, not a bid, when action is pass/too_hard or cheap_claim ≠ franchise_mos); (4) TA overlay side — not the duration book; (5) sector/market identity headers; latest-quarter headline; key risks (top 3); required inputs AS EXECUTED; data-quality notes; pointer to the other two reports. Do **not** lead with fair value vs price + MoS or a bull/base/bear cover verdict. Leave a one-line placeholder for the audit verdict — Phase 5 will fill it with **Audit PASS = process completeness (provenance/hooks), not an investment recommendation or buy list.** Do not put ATR share-count on this cover as a position size.
```

---

## Phase 5 — Agent 13 audit (`coder`)

```text
Audit the TICKER session at S. You are the last line of defense before the user reads this. The main agent's merges and judgments are IN SCOPE — you audit the orchestrator too.

Judgment-quality anchors (style only): ROOT/harness/exemplars/rationale_quality.md, hooks_quality.md, handoff_quality.md — grade rationales/hooks/handoffs against GOOD vs BAD patterns; schema-valid hollow work is still a finding.

Read S/reports/*.md, all of S/registry/ — including registry/raw/ (diff the raw swarm returns against the merged files), registry/phase_status.json when present (resume map / completeness claims vs artifacts), and registry/handoffs/ (every agent's own account of its data issues and assumptions; cross-check them against what the artifacts actually show — an agent that hit a data problem but didn't disclose it in its artifact is a finding), and S/data/valuation_model.json, and the scripts in S/data/compute/.

Checks (ordered bands — do not skip later bands after early PASS items):

**Band 1 — Units & identity**
1. Number consistency / integrity: report numbers match registry/compute within rounding; registry↔data spot-check 3–5 headlines; FAIL if FV/MOS/probs/entry/stop/key KPIs not rehydratable from registry/compute (chat-only = defect).
1b. MoS units: dual fields consistent when both present; flag fraction-in-`margin_of_safety_pct`; primary MoS uses base. Dual price: if val / technical / tsr current prices differ by >0.5%, require README disclosure of MoS anchor.
1c. scenario_probabilities: only bear/base/bull numerics (extra keys / string rationale inside map = major until fixed). Machine check_session may WARN/FAIL — treat as structural.

**Band 2 — Consumption & process integrity**
2. EXTERNAL VERIFICATION: ≥5 filing-grade numbers vs primary sources. Consistency is not truth. ≥1 of the ≥5 must be multi-period series or historical stress anchor (not five lines from the same EX-99.1 only).
2b–2d. Deep-dive structure + re-checks; hooks consumption; market_context hooks + intensity gate (high intensity all-noted_only is FAIL-quality). When `operating_path_brief.json` exists: non-empty `operating_path_hooks` that are not all-`noted_only`. Machine check_session enforces non-empty filing_deep_dive_hooks when FDD exists (F8) and medium/high all-noted_only — still grade *substance* of use/reject.
2c+. If filing_deep_dive was created during Phase 5 after valuation with empty material hooks → major FAIL (backfill-without-revalue is not PASS) unless re-value or explicit README waive that FV did not consume FDD. **You must not author missing FDD or rewrite valuation as auditor.**
2e–2g. Decision-grade handoffs (four sections); research_brief coverage; news URL sample.
2h. **Agent 4 isolation:** technical.json / handoffs/4* must not cite fundamental paths (valuation_model, filing_deep_dive, background, latest_quarter, market_context, sec_filings, sp_financials, street_estimates). Machine may FAIL under --full; confirm independence of TA lens.
2i. Swarm lead handoffs present (phase0_* / phase25_*); hollow “none” gaps when artifacts show problems = finding.

**Band 3 — Judgment quality sample**
3. Reproducibility: rerun ALL compute scripts from cache.
4. Justification contract + scripted intermediates. Sample ≥3 path assumptions: FAIL major if rationale cites a different level than value without explicit haircut. "Industry standard" / "mid of band" alone not substantive for ERP. Grade PFP/MoS/probs style against valuation_decision_quality.md GOOD vs BAD.
4-street. When street_estimates.json exists: independent_construction must be a company-evidence stack (guide/segments/run-rate/RPO), not “use consensus.” |delta_pct|>20% is a calibration note (not major by itself). Copying Street into base is major even if schema-valid. Numeric base==street with a calibration hook is machine-allowed (landing near consensus); paste-without-needle is still Band 3 FAIL. Degraded transcripts that exile a printed IR/8-K outlook from base are major **except** when a destock/flatten conflict is live (4d wins; destock-in-base is not a skill miss). Destock-in-bear + duration-in-base is **major** even if the conflict is `resolved` (harness ≥ 2.12.0). Omit conservatism_dials or omit multi_method_reconciliation when both SOTP and DCF ran is machine FAIL on ≥2.7.0. `trust_guides_more` without a met-only / cash-quality split is a finding (beat is not a hit). two_quarter_rule that raises Y1 into worse FCF/AR/inventory without bear_only is a finding. two_quarter_rule that raises Y1 while destock conflict is live and FCF is ≥0 with inventory/AR down (WC release) is a finding (destock inverse; cannot raise).
4-roic. On harness ≥ 2.8.0: `roic_identity` present (or applies:false with reason). Grade NOPAT/IC definitions vs the DCF stack (cash tax, leases both-or-neither). Gordon free growth while mid-cycle ROIC ≤ WACC without a legal exit is major. `franchise_mos` / “why cheap” as franchise MoS on a below/approx bucket is major even if schema-valid. Do not fail banks for missing industrial IC. TTC ROIC ignored while mid-cycle is capitalized as a franchise is a finding. See valuation_decision_quality.md ROIC pair.
4-midcycle. On harness ≥ 2.13.0 when applies:true: missing `mid_cycle_construction` is major. `last_year` / `peak_year` / `insufficient_window` (or a <2-year window) licensing `above_wacc` or `franchise_mos` is major. last_year + approx/below + equity_near_book is not a miss. Do not invent a mid-cycle NOPAT formula.
9. Reverse-engineering present; priced_for_perfection is a surface dial argument — FAIL if boolean is threshold-only in compute without surface rationale.
10. growth/is_also_growth: SBC/dilution critical intensity.

**Band 4 — Fit & merge**
7–8b. Cross-artifact inputs; **sector fit vs identity** (not consistency with the chosen module); region fit. Challenge the **lead module vs identity**. Tripwire: GICS Consumer Defensive / Farm Products / Packaged Foods **and** branded retail mix **and** `primary_sector=cyclical` → **major** (machine FAIL on harness ≥ 2.9.0) unless a majority of revenue is realized at spot/index/posted producer prices. Lead `module_file` vs identity mismatch → finding. Do not PASS on schema-valid `sector_fit`. Branded CPG with a protein/feed shock is a 2.5 overlay, not proof that `sector_cyclical.md` should lead. Branded consumer / CPG / staples with `primary_sector=growth` → **major** (use native module + `is_also_growth`; do not infer this from FCF alone). Template 30/45/25 without method+counterfactual, mechanical PFP (price≷base only), or wide cone without `decision_usefulness` → **major** on ≥ 2.9.0. README that treats Audit PASS as investable without the completeness disclaimer → **major**. README that leads with fair value vs price / margin of safety **before** quoting duration.action is **major** on ≥ 2.16.0 (any action). Agent 12 `roc_vs_cost_of_capital=fail` next to `franchise_mos` without `quality_bucket=above_wacc` → **major**. After Phase 2.5, `decision.json` with `reopened_after_stress` false/missing is **major** on ≥ 2.14.0 (5b not run). Missing `latest_quarter.cash_quality` on ≥ 2.15.0 is **major**.
11. Merge integrity (raw counts; no invented merge numbers).
12. phase_status lag (pending agents with files on disk) = minor (machine WARN); phase complete without primary artifact = major if not waived; do not author missing FDD yourself as auditor.
13. Process note: multi-agent *spawn API* is not required for PASS; decision-grade specialist *artifacts* and isolation are.

Write S/registry/audit.json per ROOT/templates/audit.schema.json: verdict PASS only if no critical/major issues; list every issue with severity, location, and concrete fix.
```

On `FAIL`: fix issues (max 2 iterations), record `resolution` per issue, re-run audit. After the final audit, update the README's audit-verdict line and any waived issues (AGENTS.md §8).
