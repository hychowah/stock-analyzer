# Stock Research Toolchain

This document describes the MCP servers and orchestration scripts that power the
autonomous stock-research workflow in `/workspace-stock-research/`.

## 1. yfinance MCP (`yfinance-market-mcp`)

Path: `/workspace-stock-research/yfinance-market-mcp/`
Entry point: `yfinance-mcp` / `yfinance-market-mcp`

### Market data tools

| Tool | Purpose |
|------|---------|
| `get_price_history` | OHLCV price history (daily/intraday) |
| `get_dividends` | Dividend history |
| `get_splits` | Stock split history |
| `get_fast_info` | Quick snapshot: price, market cap, 52w range, averages |
| `get_ticker_info` | Full `Ticker.info` dump (sector, industry, description, financials) |
| `get_ticker_summary` | Composite of price, fundamentals, news, analyst targets |

### News & search

| Tool | Purpose |
|------|---------|
| `get_ticker_news` | Recent news for a ticker |
| `search_news` | General market news by keyword |
| `search_tickers` | Search tickers by company name or keyword |

### Options

| Tool | Purpose |
|------|---------|
| `get_options_expirations` | Available expiration dates |
| `get_options_chain` | Calls/puts chain for a given expiration |

### Financial statements & estimates

| Tool | Purpose |
|------|---------|
| `get_income_statement` | Income statement (yearly/quarterly/trailing) |
| `get_balance_sheet` | Balance sheet (yearly/quarterly) |
| `get_cash_flow` | Cash flow statement (yearly/quarterly) |
| `get_analyst_price_targets` | Low/high/mean/median analyst targets |
| `get_recommendations` | Buy/sell/hold recommendation history |
| `get_upgrades_downgrades` | Upgrade/downgrade history |
| `get_earnings_estimate` | EPS estimates by period |
| `get_revenue_estimate` | Revenue estimates by period |
| `get_growth_estimates` | Growth-rate estimates |
| `get_eps_trend` | EPS estimate revision trend |

### Holders & events

| Tool | Purpose |
|------|---------|
| `get_institutional_holders` | Top institutional holders |
| `get_insider_transactions` | Recent insider transactions |
| `get_major_holders` | Insider/institutional breakdown |
| `get_earnings_dates` | Upcoming/past earnings dates |
| `get_calendar` | Dividend/earnings calendar |

### Sector & screening

| Tool | Purpose |
|------|---------|
| `get_sector_data` | Sector overview, top companies, ETFs, industries |
| `get_industry_data` | Industry overview, top companies, top growth companies |
| `screen_stocks` | Predefined Yahoo Finance screeners |

### Trade-advisor tools

| Tool | Purpose |
|------|---------|
| `check_fed_earnings` | Proximity to Fed meetings and earnings reports |
| `calculate_range` | Options RANGO (operating price range) |

## 2. Running research with Kimi CLI native swarm

The fastest way to run the full sector-aware research workflow is through Kimi Code CLI's native `AgentSwarm` and `Agent` tools instead of the sequential orchestrator.

**Why use native swarm**

- Parallel phases reduce wall-clock time (Phase 1, Phase 2, and Phase 4 agents run concurrently).
- Each subagent has an isolated context, reducing prompt leakage and cross-agent hallucination.
- `AgentSwarm` dispatches up to 128 subagents with built-in concurrency ramping.

**Enable swarm mode**

```bash
# One-shot with swarm enabled
kimi --swarm -p "Run the AAPL research swarm for 2026-07-19"

# Or inside an interactive Kimi session
/swarm on
```

**Full AAPL example (kimi-datasource-first)**

```bash
kimi -p "Run the AAPL research swarm for session date 2026-07-25 in /workspace-stock-research. \
  Create AAPL/2026-07-25/{reports,data,charts,registry}. \
  Use TodoList to track phases. \
  Orchestrator: classify_sector(AAPL) via yfinance MCP and write registry/sector_config.json. \
  Phase 0: AgentSwarm(explore) for 8 background-research rounds. \
  Phase 1: parallel Agent(coder) data agents: \
    - Agent 2a fetch S&P fundamentals (data/sp_financials.csv + data/sp_estimates.csv + registry/sp_competitors.json); \
    - Agent 2b fetch SEC filings (registry/sec_filings.json); \
    - Agent 2c run 5-year trajectory & accounting review (registry/trajectory_review.json); \
    - Agent 2d integrate latest quarter (registry/latest_quarter.json). \
  Phase 2: Agent(coder) valuation reasoning + scripts/agent5_kd_valuation.py for deterministic math; Agent 4 technical; Agent 12 TSR. \
  Phase 2.5: AgentSwarm(coder) for 4+ stress scenarios, merge into registry/risk_bridge.json. \
  Phase 3: generate_charts(AAPL, AAPL/2026-07-25/charts) via yfinance MCP. \
  Phase 4: parallel Agent(coder) for README, fundamental, and technical reports. \
  Validate registry JSON against templates/*.schema.json."
```

**References**

- Full prompt templates and phase-by-phase mapping: `/workspace-stock-research/KIMI_CLI_SWARM_RUNBOOK.md`
- Sequential fallback (non-interactive or when native swarm is unavailable): `scripts/_legacy/orchestrator.py`
- Sector detection and quality gates: `/workspace-stock-research/AGENTS.md`
- Original agent task descriptions: `/workspace-stock-research/prompt_adaptive_v2.md`

## 3. Research tools added to yfinance MCP

The yfinance MCP is still used for sector detection, price history, and charts.
Fundamental data now comes from the **kimi-datasource** S&P Capital IQ and SEC
EDGAR sources (see Section 6).

| Tool | Purpose |
|------|---------|
| `classify_sector(ticker)` | Classify a ticker into `banking`, `insurance`, `growth`, `reit`, `utility`, `cyclical`, or `standard` using `Ticker.info` and key financials. Returns `primary_sector`, `confidence`, `is_also_growth`, `trigger_reasons`, and `suggested_module_file`. |
| `generate_charts(ticker, output_dir)` | Generate `price_trend.png` (price + 50/200 MA + volume) and `valuation_sensitivity.png` (fair value vs WACC/growth grid) using matplotlib. |

> Legacy tools `get_latest_quarter_snapshot`, `compute_valuation_model`, and
> `get_peer_snapshot` are retained in the MCP server but are no longer the
> primary path. Their equivalents are now produced by the Phase 1 data agents
> and `scripts/agent5_kd_valuation.py`.

## 4. SEC EDGAR MCP (`sec-edgar-mcp`)

Path: `/workspace-stock-research/sec-edgar-mcp/`
Entry point: `sec-edgar-mcp`

| Tool | Purpose |
|------|---------|
| `search_company_by_ticker(ticker)` | Map ticker to CIK, company name, and SIC via SEC EDGAR submissions API. Caches `https://www.sec.gov/include/ticker.txt` in memory. |
| `get_latest_filings(ticker, form_type="10-Q", count=5)` | Recent filings metadata (accession number, filing date, form, primary document, description). |
| `get_filing_text(accession_number, cik)` | Fetch the primary document or index page for a filing and return URL + extracted text/HTML snippet. |
| `get_latest_earnings_release(ticker)` | Convenience tool that finds the latest 8-K exhibit 99.1 (earnings release) and returns URL + text preview. |

Configuration:

- `SEC_USER_AGENT`: required by SEC EDGAR. Must include a contact email. Example:
  `ResearchAgent contact@example.com`. Falls back to `research-agent contact@example.com`.
- Built-in rate limiting: max 10 requests/sec with polite delays.

## 5. Web-fetch MCP (`web-fetch-mcp`)

Path: `/workspace-stock-research/web-fetch-mcp/`
Entry point: `web-fetch-mcp`

| Tool | Purpose |
|------|---------|
| `fetch_url(url, max_chars=50000)` | Fetch a URL with a browser-like User-Agent, strip script/style/nav/header/footer/aside markup with BeautifulSoup, and return clean readable text. Returns `url`, `title`, `text`, `status`, `content_type`, `chars_returned`. |

Configuration:

- `WEB_FETCH_USER_AGENT`: override the default browser-like User-Agent.
- Polite delay: minimum 0.1s between requests (max ~10/sec).

## 6. Orchestrator / runbook

The primary driver is now the **native Kimi CLI swarm runbook** documented in
`/workspace-stock-research/KIMI_CLI_SWARM_RUNBOOK.md`. The assistant executes
phases via `Agent`/`AgentSwarm` tools; data fetching is done by subagents using
the kimi-datasource plugin and SEC/web-fetch MCPs.

A legacy sequential fallback still exists for non-interactive use but is no
longer maintained:

Path: `/workspace-stock-research/scripts/_legacy/orchestrator.py`

```bash
python scripts/_legacy/orchestrator.py --ticker AAPL --date 2026-07-19 --output-dir /workspace-stock-research
```

The new harness produces:

```text
/workspace-stock-research/AAPL/2026-07-25/
├── reports/
│   ├── 00_AAPL_README.md
│   ├── 01_AAPL_fundamental.md
│   └── 02_AAPL_technical.md
├── data/
│   ├── sp_financials.csv
│   ├── sp_estimates.csv
│   ├── valuation_model.json
│   └── sec_10k_text.csv
├── charts/
│   ├── price_trend.png
│   └── valuation_sensitivity.png
└── registry/
    ├── sector_config.json
    ├── sp_competitors.json
    ├── sec_filings.json
    ├── trajectory_review.json
    ├── latest_quarter.json
    ├── valuation_judgment.json
    ├── risk_bridge.json
    ├── technical.json
    └── tsr_validation.json
```

Pipeline order:

1. Sector detection (`classify_sector` via yfinance MCP).
2. Phase 0 — AgentSwarm(explore) background research.
3. Phase 1 — parallel Agent(coder) data agents (S&P fundamentals, SEC filings,
   trajectory/accounting review, latest-quarter integration).
4. Phase 2 — Agent(coder) valuation reasoning + `scripts/agent5_kd_valuation.py`
   deterministic math; Agent 4 technical; Agent 12 TSR.
5. Phase 2.5 — AgentSwarm(coder) stress scenarios, merged into `risk_bridge.json`.
6. Phase 3 — Chart generation (`generate_charts` via yfinance MCP).
7. Phase 4 — parallel Agent(coder) report writing (README, fundamental, technical).

## 6a. Standalone agent scripts

Each phase can also be run standalone for debugging or incremental updates.
All scripts accept `--ticker`, `--date`, and `--output-dir`.

| Script | Output | Purpose |
|---|---|---|
| `scripts/agent4_technical.py` | `registry/technical.json` | Technical analysis with valid entry/stop logic and sector RS |
| `scripts/agent5_kd_valuation.py` | `data/valuation_model.json`, `registry/risk_bridge.json` | kimi-datasource-aware DCF, relative multiples, risk bridge |
| `scripts/agent12_tsr.py` | `registry/tsr_validation.json` | TSR validation and value-trap red flags |
| `scripts/validate_registry.py` | console | Schema and cross-file validation |
| `scripts/kd_research/` | shared | S&P item map, SEC context helpers, registry I/O |

Legacy scripts are preserved in `scripts/_legacy/` for reference but are not
used by the new harness.

Run with the project venv:

```bash
/workspace-stock-research/yfinance-market-mcp/.venv/bin/python \
  scripts/agent5_kd_valuation.py --ticker AAPL --date 2026-07-25 --output-dir /workspace-stock-research
```

## 7. Registry validation

Path: `/workspace-stock-research/scripts/validate_registry.py`

Validates registry schemas, checks that all required artifacts exist, and runs
cross-file consistency checks (debt, FCF, stop-loss sanity, scenario count/probabilities).

```bash
/workspace-stock-research/yfinance-market-mcp/.venv/bin/python \
  scripts/validate_registry.py --ticker AAPL --date 2026-07-19
```

## 8. Example `.mcp.json` snippet

```json
{
  "mcpServers": {
    "yfinance": {
      "command": "/workspace-stock-research/yfinance-market-mcp/.venv/bin/yfinance-mcp",
      "timeout": 60000,
      "env": {
        "PYTHONPATH": ""
      }
    },
    "sec-edgar": {
      "command": "/workspace-stock-research/sec-edgar-mcp/.venv/bin/sec-edgar-mcp",
      "timeout": 60000,
      "env": {
        "SEC_USER_AGENT": "ResearchAgent contact@example.com"
      }
    },
    "web-fetch": {
      "command": "/workspace-stock-research/web-fetch-mcp/.venv/bin/web-fetch-mcp",
      "timeout": 60000,
      "env": {
        "WEB_FETCH_USER_AGENT": "ResearchAgent contact@example.com"
      }
    }
  }
}
```

> Replace `contact@example.com` with a real contact email before fetching SEC data.
> SEC EDGAR blocks requests without a valid User-Agent.

## 9. Recommended next steps

1. **Add sector-specific valuation models** in `scripts/agent5_kd_valuation.py`
   for `banking`, `insurance`, `reit`, `utility`, and `cyclical`. The current
   implementation handles `standard` and `growth` fully; other sectors write a
   placeholder error.
2. **Configure a real web-search MCP with an API key.** A search MCP
   (Brave Search, Exa, Tavily) lets Phase 0/1 agents discover new sources
   automatically. Keep the API key in an environment variable and reference it
   in `.mcp.json`.
3. **Add a FRED macro MCP** for interest-rate, inflation, and recession-indicator
   data. This improves WACC, risk-free rate, and macro-scenario inputs.
4. **Add an ESG data source** for materiality screening required by the Risk
   Manager lens.
5. **Add persistent caching** for yfinance, S&P, and SEC calls to avoid repeated
   requests and reduce the chance of rate limits.
6. **Add unit tests** under `scripts/tests/` covering DCF math, technical
   indicators, S&P item mapping, and SEC section extraction.
