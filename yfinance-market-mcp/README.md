# yfinance-market-mcp

MCP server that exposes Yahoo Finance market data to AI assistants (Claude Code, Claude Desktop, or any MCP-compatible client).

30 tools covering: price history, options chains, news, financials, analyst estimates, holders, screener, sector/industry data, and more.

---

## Quick Start

### Install

```bash
pip install yfinance-market-mcp
```

Or run directly without installing (requires [uv](https://docs.astral.sh/uv/)):

```bash
uvx yfinance-market-mcp
```

For local development (editable install):

```bash
git clone https://github.com/hachecito/yfinance-market-mcp.git
cd yfinance-market-mcp
pip install -e .
```

### Verify Installation

```bash
yfinance-mcp --help
```

If the command is found, the server is ready.

---

## Usage

### With Claude Code

Create a `.mcp.json` file in your project root:

Using pip:
```json
{
  "mcpServers": {
    "yfinance": {
      "command": "yfinance-mcp"
    }
  }
}
```

Using uvx (no install needed):
```json
{
  "mcpServers": {
    "yfinance": {
      "command": "uvx",
      "args": ["yfinance-market-mcp"]
    }
  }
}
```

Then restart Claude Code. The 30 tools will be available automatically — just ask Claude about any stock, options chain, or market news.

### With Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

Using pip:
```json
{
  "mcpServers": {
    "yfinance": {
      "command": "yfinance-mcp"
    }
  }
}
```

Using uvx:
```json
{
  "mcpServers": {
    "yfinance": {
      "command": "uvx",
      "args": ["yfinance-market-mcp"]
    }
  }
}
```

Restart Claude Desktop. Done.

### With Any MCP Client

The server uses **stdio** transport. Launch it with:

```bash
yfinance-mcp
# or
uvx yfinance-market-mcp
```

Connect your MCP client to stdin/stdout of that process.

---

## Available Tools (30)

### Price
| Tool | Description |
|------|-------------|
| `get_price_history` | OHLCV data (configurable period, interval, date range) |
| `get_dividends` | Dividend history |
| `get_splits` | Stock split history |

### Info
| Tool | Description |
|------|-------------|
| `get_ticker_info` | Full company info (sector, industry, description, financials) |
| `get_fast_info` | Quick snapshot (price, volume, market cap, 52w range) |
| `get_ticker_summary` | Composite: price + fundamentals + news + analyst targets |

### News
| Tool | Description |
|------|-------------|
| `get_ticker_news` | Recent news articles for a ticker |
| `search_news` | General market news search by keyword |

### Options
| Tool | Description |
|------|-------------|
| `get_options_expirations` | Available expiration dates |
| `get_options_chain` | Calls/puts with strike, bid, ask, volume, OI, IV |

### Financial Statements
| Tool | Description |
|------|-------------|
| `get_income_statement` | Income statement (yearly/quarterly/trailing) |
| `get_balance_sheet` | Balance sheet (yearly/quarterly) |
| `get_cash_flow` | Cash flow statement (yearly/quarterly) |

### Analysis & Estimates
| Tool | Description |
|------|-------------|
| `get_analyst_price_targets` | Price targets (low, high, mean, median, current) |
| `get_recommendations` | Buy/sell/hold ratings over time |
| `get_upgrades_downgrades` | Analyst rating changes |
| `get_earnings_estimate` | EPS estimates by period |
| `get_revenue_estimate` | Revenue estimates by period |
| `get_growth_estimates` | Growth rate estimates |
| `get_eps_trend` | EPS trend / estimate revisions |

### Holders
| Tool | Description |
|------|-------------|
| `get_institutional_holders` | Top institutional holders |
| `get_insider_transactions` | Recent insider buys/sells |
| `get_major_holders` | Major holder breakdown |

### Events & Search
| Tool | Description |
|------|-------------|
| `get_earnings_dates` | Upcoming/past earnings dates |
| `get_calendar` | Upcoming events (dividends, earnings) |
| `search_tickers` | Search tickers by company name or keyword |

### Sector & Industry
| Tool | Description |
|------|-------------|
| `get_sector_data` | Sector overview, top companies, and industry breakdown |
| `get_industry_data` | Industry overview, top companies, and top growth companies |

### Screener
| Tool | Description |
|------|-------------|
| `screen_stocks` | Predefined screeners (most actives, day gainers/losers, undervalued, etc.) |

### Batch
| Tool | Description |
|------|-------------|
| `batch_download` | Download OHLCV data for multiple tickers at once |

---

## Example Prompts

Once connected, just ask Claude naturally:

- *"Show me AAPL's options chain for the nearest expiration"*
- *"What's the latest news on TSLA?"*
- *"Compare MSFT and GOOGL fundamentals"*
- *"Get analyst price targets for NVDA"*
- *"Show me AMZN's quarterly income statement"*
- *"What are the most active stocks today?"*
- *"Show me the top companies in the semiconductor industry"*

---

## Publishing to PyPI

### 1. Prerequisites

Create a PyPI account at [pypi.org](https://pypi.org/account/register/) and generate an API token:

1. Go to [pypi.org/manage/account](https://pypi.org/manage/account/)
2. Scroll to **API tokens** > **Add API token**
3. Name: `yfinance-market-mcp`, Scope: **Entire account** (first time) or project-scoped later
4. Copy the token (starts with `pypi-`)

### 2. Install Build Tools

```bash
pip install build twine
```

### 3. Build the Package

```bash
cd yfinance_mcp
python -m build
```

### 4. Publish to PyPI

```bash
twine upload dist/*
```

Credentials:
- Username: `__token__`
- Password: your PyPI API token (the `pypi-` one from step 1)

### Updating Versions

1. Bump version in `pyproject.toml` and `src/yfinance_mcp/__init__.py`
2. Rebuild: `python -m build`
3. Upload: `twine upload dist/*`

---

## Project Structure

```
yfinance_mcp/
├── pyproject.toml                  # Package metadata + entry points
├── LICENSE
├── README.md
├── src/
│   └── yfinance_mcp/
│       ├── __init__.py             # Package version
│       ├── server.py               # FastMCP server + 30 tools
│       └── utils.py                # DataFrame/Series serialization
└── tests/
    └── test_server.py              # Unit tests
```

## License

MIT
