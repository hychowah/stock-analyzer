# Kimi CLI Native Swarm Runbook — kimi-datasource Research Harness

A ready-to-paste execution guide for running the `/workspace-stock-research` stock-research workflow using **kimi-datasource** (S&P Capital IQ + SEC EDGAR) as the primary data layer, with native `AgentSwarm` and `Agent` tools.

---

## 1. Quick start

### One-shot invocation

```bash
kimi -p "Run the AAPL research swarm for 2026-07-25 in /workspace-stock-research"
```

The assistant parses the request and executes the phases below.

### Enable swarm mode

Native `AgentSwarm` calls are auto-approved when swarm mode is on:

```text
/swarm on
```

Or start the CLI with the swarm flag:

```bash
kimi --swarm
```

### Conventions used below

Replace these variables in every prompt:

| Variable | Example | Meaning |
|---|---|---|
| `TICKER` | `AAPL` | Uppercase ticker symbol |
| `DATE` | `2026-07-25` | Session date in `YYYY-MM-DD` |
| `OUTPUT_DIR` | `/workspace-stock-research` | Project root |
| `SESSION_ROOT` | `/workspace-stock-research/AAPL/2026-07-25` | Per-session folder |

---

## 2. Phase-by-phase native mapping

### Orchestrator — sector detection (run once)

Tool: direct MCP call  
Server: `yfinance`  
Tool name: `classify_sector`  
Arguments: `{"ticker": "TICKER"}`  
Output: `SESSION_ROOT/registry/sector_config.json`

All later subagents must read this file first; it decides which sector module and metric substitutions to use.

### Phase 0 — Background research

Tool: `AgentSwarm`  
Subagent type: `explore`  
prompt_template:

```text
You are a sector-aware equity research analyst operating in /workspace-stock-research/.
Research {TICKER} for the round: "{item}".
Read /workspace-stock-research/{TICKER}/{DATE}/registry/sector_config.json to obtain primary_sector and substitutions.
Use WebSearch and FetchURL. Return 3-5 concise bullet points with source URLs.
Do not write files.
```

items:
- "Round 1: company overview and business segments"
- "Round 2: competitive moat using the sector-equivalent metric"
- "Round 3: management, governance, and capital allocation"
- "Round 4: growth drivers and reinvestment runway"
- "Round 5: risks, red flags, and why it might be cheap"
- "Round 6: industry structure and value chain"
- "Round 7: regional macro and regulatory context"
- "Round 8: sector-specific deep dive per prompt_adaptive_v2.md"

Main agent aggregates the swarm output and writes `registry/background.json`.

### Phase 1 — Data collection (parallel)

Launch four `coder` subagents in parallel.

#### Agent 2a — S&P fundamentals fetcher

Tool: `Agent`  
Subagent type: `coder`  
Prompt:

```text
You are Agent 2a (S&P fundamentals fetcher) for {TICKER} in /workspace-stock-research/.

1. Read SESSION_ROOT/registry/sector_config.json.
2. Use the kimi-datasource tool mcp__plugin-kimi-datasource_data__call_data_source_tool with data_source_name="sp_data".
3. Fetch annual standard financials for the last 5 completed fiscal years using sp_get_financials (ticker={TICKER}, period_type=annual, module=standard, fiscal_year_start=FY-4, fiscal_year_end=FY, limit=500).
4. Fetch quarterly standard financials for the current fiscal year through the latest quarter. Because quarterly calls hit row limits, fetch ONE data_item_id at a time from scripts.kd_research.sp_items.CANONICAL_ITEMS for key items (revenue, gross_profit, operating_income, net_income, eps_diluted, cash_from_operations, dividends_paid, total_assets, total_common_equity, total_debt_issued, total_debt_repaid). Use period_type=quarterly, fiscal_year_start=latest FY, limit=100.
5. Fetch consensus estimates with sp_get_estimates (period_type=annual, current and next fiscal year).
6. Fetch S&P competitors with sp_get_competitors and save to SESSION_ROOT/registry/sp_competitors.json.
7. Merge annual and quarterly results into a wide-format CSV: SESSION_ROOT/data/sp_financials.csv with columns: ticker, fiscal_year, fiscal_quarter, period_type, period_end_date, item_key, item_value, currency, unit_type.
8. Save estimates to SESSION_ROOT/data/sp_estimates.csv.

Cite S&P as the source. Do not compute ratios or valuation here.
```

#### Agent 2b — SEC filing fetcher

Tool: `Agent`  
Subagent type: `coder`  
Prompt:

```text
You are Agent 2b (SEC filing fetcher) for {TICKER} in /workspace-stock-research/.

1. Use the kimi-datasource tool mcp__plugin-kimi-datasource_data__call_data_source_tool with data_source_name="sec_edgar".
2. Call sec_edgar_get_company_info to obtain CIK and fiscal year end.
3. Call sec_edgar_get_filings (form_type=10-K, limit=6) to list the last 6 annual reports.
4. Call sec_edgar_get_filings (form_type=10-Q, limit=2) to list the latest quarterly report.
5. Call sec_edgar_get_filings (form_type=8-K, limit=5) to find the latest earnings-release 8-K/exhibit 99.1 if available.
6. For each of the last 5 10-Ks and the latest 10-Q, fetch the full filing text using mcp__web-fetch__fetch_url on the filing URL from sec_edgar_get_filings (or sec_edgar_get_financial_statements metadata).
7. Use scripts.kd_research.sec_context.extract_all_sections to extract Business, Risk Factors, MD&A, Financial Statements, and Notes sections where present.
8. Save SESSION_ROOT/registry/sec_filings.json with a list of filings containing: ticker, form, fiscal_year, fiscal_period, filing_date, url, sections {business, risk_factors, md_and_a, financial_statements, notes}, raw_headings.

Do not analyze here; just fetch and structure.
```

#### Agent 2c — Trajectory & accounting analyst

Tool: `Agent`  
Subagent type: `coder`  
Prompt:

```text
You are Agent 2c (trajectory & accounting analyst) for {TICKER} in /workspace-stock-research/.

Inputs:
- SESSION_ROOT/registry/sec_filings.json
- SESSION_ROOT/registry/sector_config.json

Tasks:
1. Compare the latest 10-Q MD&A and the latest earnings-release language to the MD&A sections of the prior 5 annual 10-Ks.
2. For each 10-K, extract the 3-5 most important strategic priorities or plans stated by management. Then score whether the latest 10-Q shows the company is on track, drifting, or has pivoted.
3. Identify accounting policy changes, restatements, or unusual/non-recurring items mentioned in the latest 10-Q or recent 10-K Notes.
4. Track risk-factor evolution: flag risks that are new, escalating, or diminishing across the 5-year window.
5. Summarize guidance trajectory: revenue, EPS, margin, capex guidance changes over the last 5 years and the latest quarter.
6. Look for hidden accounting tricks: aggressive revenue recognition, capitalization vs. expense, inventory/build-up, channel stuffing, SBC classification changes, pension/lease assumptions, or off-balance-sheet items.

Save SESSION_ROOT/registry/trajectory_review.json with:
- plan_alignment_score (high/medium/low) and evidence
- plan_evolution: [{year, stated_priorities, current_status, evidence}]
- accounting_red_flags: [{category, description, severity, evidence, source_filing}]
- risk_evolution: [{risk_theme, first_seen_year, latest_assessment, trend}]
- guidance_trajectory: [{period, metric, guidance, change_vs_prior}]
- key_quotes: [{topic, quote, source_filing, url}]
```

#### Agent 2d — Latest-quarter integrator

Tool: `Agent`  
Subagent type: `coder`  
Prompt:

```text
You are Agent 2d (latest-quarter integrator) for {TICKER} in /workspace-stock-research/.

Inputs:
- SESSION_ROOT/data/sp_financials.csv
- SESSION_ROOT/data/sp_estimates.csv
- SESSION_ROOT/registry/sec_filings.json
- SESSION_ROOT/registry/trajectory_review.json
- SESSION_ROOT/registry/sector_config.json

Tasks:
1. Extract the most recent quarter's numbers from sp_financials.csv (revenue, gross_profit, operating_income, net_income, eps_diluted, cash_from_operations, capex proxy, SBC if available, total_assets, total_common_equity, total_debt, cash).
2. Extract guidance, segment performance, sector KPIs, margins, balance sheet, cash flow, capital returns, and management tone from the latest 10-Q and earnings-release text.
3. Apply AGENTS.md Section 6.4 override rules:
   - Two-quarter rule: if a key metric deteriorates for two consecutive quarters, downgrade base-case assumption and add a risk-bridge entry.
   - Guidance change rule: if management materially raises/lowers guidance, update forecast trajectory and widen/narrow valuation range.
   - Inflection rule: if gross/operating margin inflects, adjust operating-leverage assumptions.
   - Capital rule: if major buyback/dividend/capex/equity-raise announced, update capital-structure projections.
   - New risk rule: if a new risk appears, add a custom stress scenario.
4. Log every override in the override_log array.

Save SESSION_ROOT/registry/latest_quarter.json matching templates/latest_quarter.schema.json exactly.
```

### Phase 2 — Calculation & modeling

#### Agent 4 — Technical analysis

Reuse the existing technical agent. It reads price data from yfinance MCP and is independent of fundamentals.

Prompt:

```text
You are Agent 4 (technical analysis). For {TICKER}, fetch 1-2 years of daily price history via yfinance get_price_history.
Calculate 50/200-day MAs, RSI, MACD, ATR, support/resistance, drawdown, and relative strength vs the benchmark index and sector.
Compute concrete entry/exit/stop-loss levels and save SESSION_ROOT/registry/technical.json.
This is pure price/volume analysis; do not use fundamentals.
```

#### Agent 5 — Valuation math (script)

Run the deterministic valuation script directly:

```bash
/workspace-stock-research/yfinance-market-mcp/.venv/bin/python \
  scripts/agent5_kd_valuation.py \
  --ticker {TICKER} --date {DATE} --output-dir {OUTPUT_DIR}
```

The script reads `data/sp_financials.csv`, `registry/latest_quarter.json`, and `registry/sector_config.json`; it writes `data/valuation_model.json` and `registry/risk_bridge.json`.

#### Agent 5 — Valuation reasoning (agent)

Tool: `Agent`  
Subagent type: `coder`  
Prompt:

```text
You are Agent 5 (valuation reasoning) for {TICKER} in /workspace-stock-research/.

Inputs:
- SESSION_ROOT/data/valuation_model.json
- SESSION_ROOT/registry/risk_bridge.json
- SESSION_ROOT/registry/latest_quarter.json
- SESSION_ROOT/registry/trajectory_review.json
- SESSION_ROOT/registry/sector_config.json

Tasks:
1. Review the deterministic model outputs and the base/bull/bear scenarios.
2. Use the trajectory_review to adjust scenario narratives: e.g., if plan alignment is low or accounting red flags exist, explain how that shifts probability toward the bear case.
3. Refine risk-bridge probabilities and parameter impacts based on the latest-quarter override log and trajectory findings.
4. Write SESSION_ROOT/registry/valuation_judgment.json with:
   - scenario_narratives: {bear, base, bull} updated stories
   - risk_bridge_refinements: list of adjustments with rationale
   - override_recommendations: list of model assumptions to change
   - red_flag_implications: how accounting/trajectory issues affect fair value
   - probability_weighted_fv_usd: optionally revised estimate
   - recommended_position_sizing_input
```

#### Agent 12 — TSR validation

Update the TSR script to read S&P fundamentals (shares, dividends, SBC) and run:

```bash
/workspace-stock-research/yfinance-market-mcp/.venv/bin/python \
  scripts/agent12_tsr.py \
  --ticker {TICKER} --date {DATE} --output-dir {OUTPUT_DIR}
```

### Phase 2.5 — Stress testing

Tool: `AgentSwarm`  
Subagent type: `coder`  
prompt_template:

```text
You are Agent 13 (stress test) for {TICKER} in /workspace-stock-research/.
Scenario: "{{item}}".
Read SESSION_ROOT/registry/sector_config.json, SESSION_ROOT/data/valuation_model.json, and SESSION_ROOT/registry/risk_bridge.json.
Estimate probability (low/medium/high), valuation parameter impacts, survival metric, and fair-value haircut.
Return JSON only: {scenario, probability, affected_parameters, survival_metric, fair_value_haircut_pct, narrative}.
```

items (read from sector_config.substitutions.stress_test_scenarios + one macro):
- Scenario A: <sector-specific A>
- Scenario B: <sector-specific B>
- Scenario C: <sector-specific C>
- Scenario D: <sector-specific D>
- Scenario E: Global recession / macro shock

Main agent merges swarm results into `registry/risk_bridge.json` under `stress_test`.

### Phase 3 — Charts

Direct MCP call:

```text
Server: yfinance
Tool name: generate_charts
Arguments: {"ticker": "TICKER", "output_dir": "SESSION_ROOT/charts"}
```

### Phase 4 — Report writing (parallel)

Tool: `Agent` × 3 parallel  
Subagent type: `coder`

Agent 7 — Fundamental report:

```text
You are Agent 7 for {TICKER}. Write SESSION_ROOT/reports/01_{TICKER}_fundamental.md.
Read all files in registry/ and data/. Follow the 11-section report structure in ADAPTIVE_FRAMEWORK_MASTER.md Part 4.
Explicitly cover the five perspectives in AGENTS.md Section 5.
Use sector-equivalent metrics from sector_config.json. Pay special attention to trajectory_review.json and valuation_judgment.json.
Do not fabricate numbers; cite sources.
```

Agent 8 — Technical report:

```text
You are Agent 8 for {TICKER}. Write SESSION_ROOT/reports/02_{TICKER}_technical.md.
Read registry/technical.json, data/valuation_model.json, and registry/latest_quarter.json.
Provide concrete entry/exit/stop-loss levels, ATR-based position sizing, relative strength, drawdown, and technical-fundamental gap analysis.
```

Agent 11 — README:

```text
You are Agent 11 for {TICKER}. Write SESSION_ROOT/reports/00_{TICKER}_README.md.
Summarize sector classification, key metrics, latest-quarter headline, valuation snapshot, verdict, and quality-gate checklist.
```

---

## 3. TodoList integration

Initial list:

```text
Tool: TodoList
- {title: "Orchestrator: sector detection", status: pending}
- {title: "Phase 0: background research swarm", status: pending}
- {title: "Phase 1a: S&P fundamentals fetch", status: pending}
- {title: "Phase 1b: SEC filing fetch", status: pending}
- {title: "Phase 1c: trajectory & accounting review", status: pending}
- {title: "Phase 1d: latest quarter integration", status: pending}
- {title: "Phase 2: valuation math + reasoning", status: pending}
- {title: "Phase 2.5: stress test swarm", status: pending}
- {title: "Phase 3: chart generation", status: pending}
- {title: "Phase 4: report writing", status: pending}
- {title: "Quality gates and validation", status: pending}
```

---

## 4. Validation

After all phases complete:

```bash
/workspace-stock-research/yfinance-market-mcp/.venv/bin/python \
  scripts/validate_registry.py \
  --ticker {TICKER} --date {DATE}
```

Expected result: `All registry files are valid and cross-checks passed.`

---

## 5. One-shot command

```bash
kimi --swarm -p "Run the AAPL research swarm for session date 2026-07-25 in /workspace-stock-research. \
Use TodoList to track phases. \
1. classify_sector(AAPL) via yfinance MCP -> write AAPL/2026-07-25/registry/sector_config.json. \
2. AgentSwarm(explore): 8 background-research rounds. \
3. Agent(coder) x4 parallel: Agent 2a S&P fundamentals -> data/sp_financials.csv + data/sp_estimates.csv + registry/sp_competitors.json; Agent 2b SEC filings -> registry/sec_filings.json; Agent 2c 5-year trajectory & accounting review -> registry/trajectory_review.json; Agent 2d latest-quarter integration -> registry/latest_quarter.json. \
4. Agent(coder) valuation reasoning -> registry/valuation_judgment.json; run scripts/agent5_kd_valuation.py, scripts/agent4_technical.py, and scripts/agent12_tsr.py. \
5. AgentSwarm(coder): 5 stress scenarios, merge into registry/risk_bridge.json. \
6. generate_charts(AAPL, AAPL/2026-07-25/charts). \
7. Agent(coder) x3 parallel: Agent 7 fundamental report, Agent 8 technical report, Agent 11 README. \
8. Validate with scripts/validate_registry.py --ticker AAPL --date 2026-07-25."
```

---

## 6. References

- `ADAPTIVE_FRAMEWORK_MASTER.md` — sector detection, metric substitutions, report structure.
- `prompt_adaptive_v2.md` — original agent task descriptions (adapted above).
- `AGENTS.md` — workspace conventions, five-perspective workflow, latest-quarter rules, quality gates.
- `README_TOOLS.md` — MCP server overview.
- `scripts/kd_research/` — shared data-access utilities.
