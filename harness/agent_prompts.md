# Subagent Prompt Templates

Copy-paste templates for each phase of the harness (see `AGENTS.md` §8). Substitute these variables everywhere:

| Variable | Example |
|---|---|
| `TICKER` | `JPM` |
| `DATE` | `2026-07-25` |
| `ROOT` | `/workspace-stock-research` |
| `S` | `/workspace-stock-research/archive/research/JPM/2026-07-25` (session root; never at repo root) |

Every template already carries the justification contract — do not strip it. Subagents see only their prompt; pass all context explicitly.

**Conventions for all agents:**
- **Hermetic scripts**: compute scripts must read session-cached data (`S/data/*.csv`, `S/registry/*.json`) when present and fetch live data only when absent. A rerun on the same session must reproduce the same numbers.
- **Scripted intermediates**: any number used inside an assumption build-up (e.g. realized beta, growth CAGR) must be computed by a script in `S/data/compute/`, not by unscripted mental math.
- **Benchmarks**: use the regional benchmark and sector index declared by the orchestrator in the session's required inputs; deviate only with a stated rationale.
- **Market / region context**: read `S/registry/market_context.json` when present (orchestrator writes it with sector_config). Cost of capital and governance dials are **local to listing and cash-flow currency** — do not paste US 10Y/ERP by default for non-USD models. Region modules (`region_*.md`) are advisory only; never apply hardcoded country WACC, ERP tables, or family-control discounts. Intensity `low` may no-op with explicit `noted_only` hooks; `medium`/`high` require real treatment. There is **no always-on region agent** — ownership depth is Agent 2e; CoC judgment is Agent 5.
- **Judgment exemplars (style only)**: before writing judgment-heavy outputs, match the GOOD patterns in `ROOT/harness/exemplars/` (index: `ROOT/harness/exemplars/index.json`). BAD patterns are FAIL-quality even if schema-valid. **Do not copy illustrative numbers into this session.** Agent map: valuation (5) and audit (13) → `rationale_quality.md` + `hooks_quality.md`; technical (4), TSR (12), deep dive (2e) → `rationale_quality.md`; **every agent** → `handoff_quality.md` for handoff style. Orchestrator injects the relevant paths into each subagent prompt (do not paste full exemplar banks into every template).
- **Handoff file (required of EVERY agent)**: before finishing, write `S/registry/handoffs/<your_agent_id>.md` (e.g. `2a_fundamentals.md`, `5_valuation.md`, `13_audit.md`) with four sections:
  1. **What I did** — 3-5 bullets: inputs read, outputs written, tools used.
  2. **Data issues & gaps** — anything that failed to fetch, was truncated, stale, missing, or had to be substituted (with the fallback used). If none, say "none".
  3. **Assumptions & deviations** — every judgment call that ISN'T already recorded with rationale in your output artifact: inferred inputs, template deviations, edge cases you resolved by choice.
  4. **For downstream agents & the auditor** — what the next agents must know: caveats, unreconciled numbers, suggested checks.
  Keep it under one page. This file is how the audit agent and the next session understand your run — the artifact shows WHAT you produced, the handoff shows WHERE it is soft. Match `ROOT/harness/exemplars/handoff_quality.md` GOOD pattern (honest gaps, concrete paths).

---

## Phase 0 — Background research swarm

`AgentSwarm`, subagent_type `explore`, one item per round. Rounds: (1) company & business model, (2) industry & competitive position, (3) moat & structural advantages, (4) TAM/SAM/SOM & growth drivers, (5) management & capital allocation, (6) regulatory & macro exposure, (7) bear case & historical failures, (8) sector-specific round (pick 2–3 questions from the sector module in `sector_config.json`). When `S/registry/market_context.json` has `intensity` medium or high, rounds (5) and (6) must also cover control/ownership (family, SOE, VIE, dual-class) and local rates / FX / capital-market access with sources — not only generic global macro.

prompt_template:

```text
You are a research analyst gathering background on {{item}} for TICKER (session S).

Read S/registry/sector_config.json and S/registry/market_context.json (if present) first for sector and region/intensity context. If intensity is medium/high, prioritize local institutional facts over US-default framing.

Research the assigned topic using web search. Return JSON only (do not write files):
{"topic": "...", "findings": ["3-6 specific, factual bullets with numbers where possible"],
 "sources": ["url1", "url2"],
 "downstream_relevance": "valuation_input | risk_candidate | context_only"}
No generic filler. Every quantitative claim needs a source in "sources".
```

**Merge protocol (main agent):** (1) write each round's verbatim return to `S/registry/raw/phase0_round{N}.json`; (2) merge into `S/registry/background.json` (`{"ticker", "rounds": [...]}` per `templates/background.schema.json`), deduplicating and resolving conflicts (note them in the finding text); (3) after merging, spot-check 3 headline numbers in the merged file against `S/data/sp_financials.csv` or the raw returns — the merge must not introduce new numbers.

---

## Phase 1 — Data collection (launch 2a, 2b, 2c in parallel)

### Agent 2a — fundamentals fetcher (`coder`)

```text
Fetch fundamentals for TICKER and its peers (peer list: read S/registry/sector_config.json; if absent, pick 3-5 closest peers and justify).

Primary source: kimi-datasource plugin — call get_data_source_desc("sp_data") then call_data_source_tool for income statement, balance sheet, cash flow, ratios (10 years annual + recent quarters). Also fetch the sector-module KPIs the plugin supports (banking: NII, provisions, deposits, loans, tangible equity; REIT: FFO/AFFO; etc.) and peers' KPIs (NIM, CET1 or equivalents) — if the plugin lacks them, say so in the fetch log so 2b/2d know to source them from filings. Fallback if the plugin errors: yfinance MCP statements — note the substitution.

Write:
- S/data/sp_financials.csv — long format: ticker,period_type(Annual|Quarterly),fiscal_year,fiscal_quarter,item,value,unit,currency,source
- S/data/peer_comparison.csv — peers' key multiples and growth rates, with a "source" column
- S/registry/data_fetch_log.json — {"ticker", "as_of", "fetched": [...], "failed": [...], "substitutions": [...], "downstream_instructions": [...]} — explicitly tell downstream agents which gaps to fill from filings

Numbers must come from the sources above — do not estimate. State units and currency. NOTE: data-provider "total revenue" for financial firms may be netted differently from filing-basis revenue — record which definition you stored.
```

### Agent 2b — SEC filings (`coder`)

```text
Fetch SEC (or local-jurisdiction) primary filings for TICKER and store them under the session tree for deep mining. Read S/registry/market_context.json when present and honor listing.primary_filing_source / filing_forms_expected — do not pretend EDGAR is primary if the annual is HKEX, DART, or another local venue.

REQUIRED fetch set:
1. At least the **three most recent annual reports** (US: 10-K; non-US: 20-F / annual report equivalents) — multi-year text is mandatory for Agent 2e's strategy arc.
2. The two most recent interim reports (10-Q / half-year / etc.).
3. The latest earnings 8-K exhibit (EX-99.1 and financial supplement EX-99.2 if any).

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

Cover: (1) 8-15 material news items from the last ~3 months (earnings, guidance changes, regulator actions, management changes, M&A); (2) positioning: analyst consensus and dispersion, short interest, insider transactions (search for these; if a data point is unavailable, say so explicitly rather than omitting the key); (3) catalyst calendar: next earnings date, known regulatory decisions, product/event dates.

Write S/registry/news_sentiment.json per ROOT/templates/news_sentiment.schema.json. Every item needs a source. Sentiment labels are your judgment — that's fine, they're labeled as such.
```

---

## Phase 1b — Agent 2d latest-quarter integrator (`coder`)

Run after 2a and 2b.

```text
Integrate the latest quarter for TICKER.

Inputs: S/registry/sec_filings.json, S/data/latest_supplement.* (the uncapped supplement from 2b — use it first), S/data/sp_financials.csv, S/registry/sector_config.json, S/registry/data_fetch_log.json (its downstream_instructions tell you which gaps to fill). Fetch the earnings-release/press summary via kimi-datasource sec_edgar or web search if not already covered.

Extract per ROOT/templates/latest_quarter.schema.json: fiscal_period (must match the numbers!), currency, sources (URLs), revenue/earnings vs prior year and vs consensus if findable, guidance (company guidance only — analyst price targets are NOT guidance; verify raise/cut claims against the prior quarter's guidance, not media headlines), segments, sector KPIs per the sector module, margins, balance sheet, cash flow, capital returns, management_tone, risks. For any historical series you quote (e.g. capital ratios over 4 quarters), verify each point against the prior-quarter supplements, not memory.

Then fill evidence_log: for each notable change vs prior trend, record metric / observation / materiality (is it >5% relative or >100bp? use YoY basis) / suggested_rule (two_quarter_rule | guidance_change_rule | inflection_rule | capital_rule | new_risk_rule | none) / source.

You log EVIDENCE ONLY. Do not change valuation assumptions — that is the valuation agent's job.
Write S/registry/latest_quarter.json.
```

---

## Phase 1c — Agent 2e filing deep dive (`coder`)

Run after 2b (needs `S/data/raw_sec/`). May run **in parallel with 2d**. Prefer 2a `sp_financials.csv` for actuals when grading promises.

```text
Deep-mine multi-year filings and earnings-call transcripts for TICKER (session S). You produce STRUCTURED decision inputs — not a second background essay.

Read first: S/registry/sector_config.json, S/registry/sec_filings.json, S/registry/data_fetch_log.json, S/data/sp_financials.csv (if present), and ALL primary text under S/data/raw_sec/. Methodology: ROOT/harness/filing_deep_dive.md. Helpers (use them; do not re-implement mental joins):
- ROOT/scripts/kd_research/note_extract.py (split_notes, build_footnote_items, parse_guidance_outlook_block)
- ROOT/scripts/kd_research/promise_vs_actual.py (join_promises_to_actuals, hit_rate, scorecard_summary)

TRANSCRIPTS (secondary source):
- Obtain recent earnings-call transcripts (last 4–8 quarters when possible) via web-fetch / IR / reputable transcript hosts. Snapshot full text to S/data/transcripts/ with period in the filename.
- If transcripts cannot be obtained: write explicit missing entries under sources.transcripts (status=missing) and sources.gaps; set management_scorecard.data_quality to degraded_no_transcripts (or partial); do NOT invent quotes or paraphrases presented as quotes.
- Every scorecard row must set source_type to filing | transcript | filing+transcript. Filings win on conflicts unless the transcript is the only place a promise was stated.

Build and write S/registry/filing_deep_dive.json per ROOT/templates/filing_deep_dive.schema.json with ALL of:

1) footnotes.items — standard/growth checklist at minimum: revenue_disaggregation, segment, sbc_unrecognized, debt_leases, contingencies_legal, income_taxes, capex_commitments, related_party_dual_class. Each item status extracted|missing|not_applicable|partial with short excerpt (≤800 chars) and source path under data/raw_sec/. Prefer build_footnote_items() then enrich value{} with numbers you parse. Missing is allowed; silence is not. Read S/registry/market_context.json when present: if ownership.complexity is medium/high or intensity is high, related_party_dual_class (and any VIE/control/SOE/family facts in the filings) MUST be enriched with concrete stakes/structures when disclosed — not a bare status with empty value. Note accounting-regime differences that affect model inputs (leases, SBC, impairment, associates) when accounting_regime is non-US-GAAP.

2) strategy_arc — cover ≥3 annual report years when raw_sec has them (fewer only if fetch gaps, documented). stated_priorities_by_year with basis paths; continuity {value, rationale, basis}; pivot_flags; capital_allocation_story; implied_model_hooks; overall rationale (≥20 chars of real analysis).

3) management_scorecard — grade promises vs actuals for revenue, opex/opinc, capex, margins, capital returns, material segment paths, plus soft strategic milestones (too_early / abandoned as appropriate). Prefer quantitative rows with low/high/target joined via promise_vs_actual.join_promises_to_actuals against actuals from sp_financials / filings. Include credibility_summary with pattern, valuation_implication, rationale, basis, transcript_coverage; hit_rate_quantitative when n≥1 quantitative met|beat|miss rows (scripted).

4) sources.filings (required) + sources.transcripts (required key; may be empty with gaps) + sources.gaps.

5) Optional risk_factor_delta (new/removed/elevated Item 1A themes YoY).

Justification contract: continuity score and any decided hit-rate implications need rationale/basis. Never fabricate footnote numbers. Write S/registry/handoffs/2e_filing_deep_dive.md.
```

---

## Phase 2 — Modeling (launch 4, 5, 12 in parallel)

### Agent 4 — technical analysis (`coder`)

```text
Technical analysis for TICKER as of DATE. You must NOT read any fundamental artifact (no valuation model, no filings, no background, no news). Price/volume data only. The orchestrator will tell you the latest earnings DATE (date only, no content) so you can note any price gap around it.

Fetch ~2 years of daily prices for TICKER, the regional benchmark, and the sector index declared by the orchestrator (deviate only with rationale) via the yfinance MCP (get_price_history) or yahoo_finance datasource. Cache them to S/data/prices_*.csv.

Write a runtime script S/data/compute/technical_indicators.py that READS the cached CSVs (fetches only if absent) and computes: trend (SMAs), momentum (RSI, MACD), volatility (ATR), volume profile, relative strength vs both benchmarks, support/resistance, max drawdown. Run it.

Then YOU decide: entry level, stop-loss (must be below entry), targets, and ATR-based position sizing (state the account-risk assumption) — each with rationale. If your highest-probability near-term scenario is a pullback, set the entry where that scenario says to buy — internal coherence between scenarios and levels is required.

Write S/registry/technical.json per ROOT/templates/technical.schema.json, including compute_script path.
```

### Agent 5 — valuation (`coder`)

```text
Value TICKER as of DATE.

Judgment style: read ROOT/harness/exemplars/rationale_quality.md and ROOT/harness/exemplars/hooks_quality.md (GOOD patterns; do not copy illustrative numbers).

Inputs: S/registry/sector_config.json, S/registry/market_context.json (REQUIRED for new sessions — region intensity, accounting_regime, cost_of_capital_flags, ownership), S/registry/latest_quarter.json, S/registry/filing_deep_dive.json (REQUIRED — footnotes, strategy_arc, management_scorecard), S/registry/data_fetch_log.json, S/data/sp_financials.csv, S/data/peer_comparison.csv, S/registry/background.json, the sector module file named in sector_config.json, and the region module named in market_context.module_file (both advisory; numbers are reference ranges, not mandates). Fill peer KPI gaps (e.g. NIM/CET1) from filings if the peer comparison needs them.

1. CHOOSE the valuation model that fits this company (sector module guidance + your judgment + strategy_arc implied_model_hooks). If the company has materially different business lines, run a SOTP or multi-method cross-check in addition to the primary model. Justify the choice in model.rationale.
2. DECIDE every assumption yourself: discount rate (state how you build it up — cash-flow currency vs discount-rate currency must match or FX policy must be explicit; any intermediate like realized beta or local Rf series must be scripted in S/data/compute/), growth path, margin path, terminal approach, multiples. Include explicit CoC/governance dials as assumptions where relevant (e.g. risk_free_rate, country_risk_or_erp_adjustment which may be 0, accounting_basis_for_model, ownership_governance_adjustment which may be none/0) — each {value, rationale, basis}. Check terminal state for internal consistency. Use footnote findings for SBC/dilution, tax, debt/leases, segment economics when status=extracted. NEVER paste region-module reference ranges as mandated WACC/ERP/family discounts.
3. Apply latest-quarter overrides you judge warranted from latest_quarter.json evidence_log (materiality: >5% relative or >100bp; symmetric — improvements count too). Log each in overrides_applied; explicitly note any evidence you reject and why.
4. CONSUME the deep dive: write filing_deep_dive_hooks[] — for each material footnote / strategy / scorecard finding either action used_as:<assumption> with old/new or action rejected|noted_only with reason. Credibility_summary.valuation_implication may inform scenario weights or range width; it does NOT auto-set a formula. If scorecard data_quality is degraded (no transcripts / thin history), widen the valuation range and say so.
4b. CONSUME market context: write market_context_hooks[] — for listing/intensity, accounting_regime, cost_of_capital_flags, and ownership/control either action used_as:<assumption> with old/new or rejected|noted_only with reason. intensity=low: a single noted_only no-op is enough. intensity=medium/high: local Rf/ERP framing and governance/control must be addressed (use or explicit reject). If market_context.requires_manual_review or confidence < 0.70, widen the range and say so. Avoid double-counting country risk in WACC and cash flows and stress haircuts — disclose posture.
5. Write a runtime script S/data/compute/valuation.py implementing YOUR model, reading data from the session files (never refetch live data). Run it. Its output must match what you write in the model JSON.
6. SENSITIVITY (required): compute base-case FV across a grid of your two most judgment-dependent assumptions (typically discount rate x terminal profitability), ~4x4 cells. Store as "sensitivity" in the model JSON and verify the base cell reproduces base FV exactly. If your stack of judgments leans one direction, say so in a "posture" note.
7. Reverse-engineer the current price: test the full grid of implied combinations, not just extremes. Set reverse_engineering.priced_for_perfection with rationale.
8. Compute margin of safety as 1 - price/fair_value (signed). State which book-value/anchor vintage you use and use it consistently.

Write S/data/valuation_model.json per ROOT/templates/valuation_model.schema.json, including compute_script, sensitivity, filing_deep_dive_hooks, and market_context_hooks (when market_context.json exists).
Fair value bear/base/bull plus probability_weighted (your weights, justified — these become scenario_probabilities in risk_bridge; keep them consistent).
```

### Agent 12 — TSR & dilution validation (`coder`)

```text
Validate TICKER's historical shareholder returns and dilution as of DATE — this is the value-trap screen.

Fetch price history (5-10y) and dividends for TICKER and the benchmarks declared by the orchestrator (deviate only with rationale) via yfinance MCP or yahoo_finance datasource; cache to S/data/prices_tsr_*.csv (or reuse prices_*.csv if the technical agent already cached the same tickers). Get share-count history, SBC, and buybacks from S/data/sp_financials.csv (fallback: yfinance, cached).

Write and run S/data/compute/tsr_dilution.py (READS cached data; fetches only if absent) computing: TSR over 1/3/5/10y vs benchmarks, share-count CAGR, compound dilution/buyback effect, SBC % revenue, SBC-adjusted FCF. For growth/is_also_growth names (check S/registry/sector_config.json): also Rule of 40 and Burn Multiple — CRITICAL intensity for them; otherwise note why SBC treatment is light.

Then assess value-trap flags yourself (e.g. TSR vs fundamental growth gap, return-on-capital trend vs cost of capital, buyback effectiveness at the current multiple). Each flag: status pass/warn/fail/unknown with evidence. Never assert a pass without computed evidence.

Write S/registry/tsr_validation.json per ROOT/templates/tsr_validation.schema.json, including compute_script.
```

---

## Phase 2.5 — stress-test swarm

`AgentSwarm`, subagent_type `coder`, 5 items: the 4 most relevant sector scenarios (from the sector module's stress library — adapt to the company) + 1 macro scenario. Also add any scenario required by a `new_risk_rule` evidence entry. When S/registry/market_context.json has intensity `high`, at least one of the five must be region/governance/FX/policy (from the region module stress seeds or company-specific); when intensity is `medium`, include one if material. (If you judge a different 5-scenario mix more decision-relevant, deviate — and record the deviation with rationale in risk_bridge.json.)

prompt_template:

```text
Stress scenario for TICKER: {{item}}

Inputs: S/data/valuation_model.json, S/registry/sector_config.json, S/registry/market_context.json (intensity, ownership, accounting — use for region/governance/FX scenarios; do not invent folklore EM haircuts), S/registry/latest_quarter.json, S/registry/filing_deep_dive.json (footnotes contingencies/legal, risk_factor_delta, management_scorecard credibility pattern — use filing/transcript-labeled facts before web legal dollar claims).

Return JSON only (do not write files):
{"name": "...", "type": "sector|macro|region",
 "probability": <0-1 number YOU decide>, "rationale": "<why this probability — reference history/base rates/company specifics; cite deep-dive or filings when legal/contingent>",
 "affected_parameters": ["..."], "fair_value_haircut_pct": <number, your estimate>,
 "narrative": "<2-4 sentences: transmission mechanism and impact>",
 "deep_dive_refs": ["optional paths into filing_deep_dive.json used"],
 "market_context_refs": ["optional paths into market_context.json used"]}
Probability semantics: this is a STANDALONE conditional estimate of this event occurring. Scenarios are NOT mutually exclusive and do NOT need to sum to 1.0. Check any historical anchor you cite (e.g. trough multiples in past crises) against the actual historical record before using it.
Ground the haircut in the valuation model's sensitivities where possible. No canned numbers. Do not invent litigation quanta when the deep dive / Item 3 / contingency note is silent — say unknown. Do not apply a fixed family-control or country discount from a region module.
```

**Merge protocol (main agent):** (1) write each verbatim return to `S/registry/raw/stress_{id}.json`; (2) merge into `S/registry/risk_bridge.json` per `templates/risk_bridge.schema.json`: `risks` (every `latest_quarter.json.risks[]` entry must map to a risk here or be explicitly dropped with a reason; fold material deep-dive legal/contingency findings into risks or explicit drops), `scenario_probabilities` (bear/base/bull ONLY — mirrors the valuation model's weights, sums to 1.0; if valuation raised bear weight from scorecard credibility, keep consistent), `stress_test.probability_semantics` (state the standalone-conditional convention), `stress_test.scenarios`.

---

## Phase 3 — Agent 6 charts (`coder`)

```text
Generate charts for TICKER session S.

Write and run S/data/compute/charts.py (matplotlib; use ROOT/yfinance-market-mcp/.venv/bin/python if system python3 lacks it). Read only session-cached data (prices_*.csv, valuation_model.json, risk_bridge.json). Produce at minimum:
- price_trend.png (1y price + volume, benchmark-relative)
- valuation_football_field.png (bear/base/bull FV, probability-weighted FV, current price — from S/data/valuation_model.json)
- sensitivity grid heatmap from valuation_model.json sensitivity block
- 1-3 sector-appropriate charts (e.g. capital-ratio trend vs requirement for banks, scenario tornado, SBC/dilution for growth)
Labels and titles in English, descriptive file names, cite data source on each chart.
```

---

## Phase 4 — reports (launch 7, 8, 11 in parallel)

### Agent 7 — fundamental report (`coder`)

```text
Write S/reports/01_TICKER_fundamental.md.

Read: all of S/registry/ (sector_config, market_context, background, sec_filings, filing_deep_dive, news_sentiment, latest_quarter, tsr_validation, risk_bridge, data_fetch_log), S/data/valuation_model.json, S/data/peer_comparison.csv. Skim sec_filings.json sections as needed; use filing_deep_dive.json for footnotes/strategy/scorecard (do not re-hallucinate from web when deep dive has primary excerpts). Use market_context.json for listing/accounting/ownership/intensity (do not invent regional haircuts not in the valuation model).

Structure:
- executive summary & verdict
- latest-quarter takeaways
- business & moat
- **Market & institutional context** (non-stub when intensity medium/high; one short paragraph no-op OK when intensity low): primary_region, intensity, accounting basis, ownership/control, how CoC/FX were framed — restate market_context_hooks that moved dials
- **Footnote findings** (non-stub): 3–8 bullets from filing_deep_dive.footnotes with sources — what changes dilution, tax, net debt, legal risk, segments
- **Multi-year strategy alignment** (non-stub): strategy_arc priorities by year, continuity, pivots, capital-allocation story
- **Management track record** (non-stub): scorecard table or bullets (promise → actual → outcome → source_type filing/transcript); credibility_summary implication for trusting current guides
- valuation (model choice + key assumptions WITH their rationales — restate them; INCLUDE sensitivity grid; restate filing_deep_dive_hooks and market_context_hooks that moved dials)
- five lenses (value, growth, contrarian, risk, technical-cross-reference)
- stress tests & risk bridge
- perspective conflicts
- bull-base-bear with probabilities and rationale
- position-sizing input

Rules: every number cites a source (registry file, filing URL, or compute script). Key judgment numbers must be restated with their rationale. No new numbers that are not in the registry. If the assumption stack leans one direction, disclose it. When two vintages of a metric exist (e.g. latest-quarter vs FY book value), use one consistently and say which. Label transcript-sourced claims as secondary.
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

Read S/registry/sector_config.json, S/registry/market_context.json (if present), S/data/valuation_model.json, S/registry/latest_quarter.json, S/registry/risk_bridge.json, S/registry/technical.json, S/registry/tsr_validation.json.

Cover: sector classification + confidence + one-line rationale; market/region + intensity + one-line rationale (or "legacy session: market_context absent"); fair value vs price + margin of safety; latest-quarter headline; key risks (top 3); verdict (bull/base/bear in one line each); required inputs AS EXECUTED (peers, benchmarks, currency, exchange actually used — not the plan); data-quality notes (fallbacks used, degraded sources, manual-review flags); pointer to the other two reports. Leave a one-line placeholder for the audit verdict — Phase 5 will fill it.
```

---

## Phase 5 — Agent 13 audit (`coder`)

```text
Audit the TICKER session at S. You are the last line of defense before the user reads this. The main agent's merges and judgments are IN SCOPE — you audit the orchestrator too.

Judgment-quality anchors (style only): ROOT/harness/exemplars/rationale_quality.md, hooks_quality.md, handoff_quality.md — grade rationales/hooks/handoffs against GOOD vs BAD patterns; schema-valid hollow work is still a finding.

Read S/reports/*.md, all of S/registry/ — including registry/raw/ (diff the raw swarm returns against the merged files), registry/phase_status.json when present (resume map / completeness claims vs artifacts), and registry/handoffs/ (every agent's own account of its data issues and assumptions; cross-check them against what the artifacts actually show — an agent that hit a data problem but didn't disclose it in its artifact is a finding), and S/data/valuation_model.json, and the scripts in S/data/compute/.

Checks:
1. Number consistency: report numbers match registry/compute outputs within rounding. ALSO check registry↔data: spot-check 3-5 headline numbers in background.json and latest_quarter.json against sp_financials.csv and the raw returns.
2. EXTERNAL VERIFICATION (required): pick >=5 filing-grade numbers (prior-quarter capital ratios, prior-year comparatives, historical anchors cited in stress narratives) and verify them against primary sources (EDGAR, IR pages, web). Consistency is not truth.
2b. DEEP-DIVE VERIFICATION (required): registry/filing_deep_dive.json exists with footnotes + strategy_arc + management_scorecard; re-check >=3 footnote/excerpt figures against S/data/raw_sec/ primary text; scorecard actuals match sp_financials/filings where quantitative; each scorecard row has source_type; transcripts labeled secondary; multi-year annual files present under raw_sec or gaps documented.
2c. Deep-dive consumption: valuation_model.filing_deep_dive_hooks present for material findings (or explicit rejects); fundamental report has non-stub Footnote findings / Multi-year strategy alignment / Management track record sections; stress/legal narratives do not invent quanta contradicted by deep dive.
2d. MARKET CONTEXT (when registry/market_context.json exists): non-empty valuation_model.market_context_hooks; intensity gate coherent (low may be single noted_only; medium/high must address local CoC and ownership/accounting — not silent US defaults); region module was read (hooks or assumptions cite it); no hardcoded family/country discounts without rationale; fundamental report has Market & institutional context appropriate to intensity; if intensity=high, risk_bridge has a region/governance/FX-style scenario or an explicit drop reason.
3. Reproducibility: rerun ALL compute scripts (not "if cheap"). Any rerun difference is data drift — investigate, never wave off as float noise. Scripts must read cached session data, not refetch live.
4. Justification contract: every judgment number has a substantive rationale AND its intermediates are scripted (flag unscripted build-up numbers). "Industry standard" alone is not substantive.
5. Citations: sourced numbers have citations; sec_filings/news items have URLs.
6. Lost-findings sweep: every latest_quarter.json.risks[] entry maps to a risk_bridge risk or is explicitly dropped with a reason; scan background.json for findings with downstream_relevance=risk_candidate that no report used.
7. Cross-artifact contradictions: README required-inputs (benchmarks, peers, currency/exchange) must match what technical.json/tsr_validation.json and market_context actually used; metric vintages consistent.
8. Sector fit: model choice consistent with sector_config and the module was actually used; sensitivity block present.
8b. Region fit: when market_context present, primary_region/intensity/module_file coherent with listing signals; CoC currency matches cash-flow policy stated in assumptions.
9. Reverse-engineering present and priced_for_perfection is a real, argued conclusion.
10. For growth/is_also_growth: SBC/dilution analysis present at critical intensity (deep-dive sbc_unrecognized should inform it when extracted).

Write S/registry/audit.json per ROOT/templates/audit.schema.json: verdict PASS only if no critical/major issues; list every issue with severity, location, and concrete fix.
```

On `FAIL`: fix issues (max 2 iterations), record `resolution` per issue, re-run audit. After the final audit, update the README's audit-verdict line and any waived issues (AGENTS.md §8).
