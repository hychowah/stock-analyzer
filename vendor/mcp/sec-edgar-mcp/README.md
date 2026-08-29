# SEC EDGAR MCP Server

A lightweight [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes SEC EDGAR filing lookup tools.

## Tools

| Tool | Description |
|------|-------------|
| `search_company_by_ticker(ticker)` | Map a ticker symbol to its SEC CIK, company name, SIC code, and recent-filing count. |
| `get_latest_filings(ticker, form_type="10-Q", count=5)` | Return metadata for the most recent filings of a given form type. |
| `get_filing_text(accession_number, cik)` | Fetch the primary document for a filing. Writes the **complete** extracted text to a local cache file and returns its `full_text_path` plus a 20,000-char `text_preview`, `preview_truncated` flag, and the SEC URL. |
| `get_latest_earnings_release(ticker)` | Convenience tool that finds the latest 8-K exhibit 99.1 (earnings release) and returns its URL, full-text path, and text preview. |

Full texts are cached under `~/.cache/sec-edgar-mcp/` (override with `SEC_EDGAR_CACHE_DIR`). Never rely on `text_preview` alone when `preview_truncated` is true — read the file at `full_text_path`.

## Setup

Create a dedicated virtual environment and install the package:

```bash
cd /workspace-stock-research/sec-edgar-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The console script `sec-edgar-mcp` is then available at:

```bash
/workspace-stock-research/sec-edgar-mcp/.venv/bin/sec-edgar-mcp
```

## Required: User-Agent

SEC EDGAR requires a descriptive `User-Agent` header containing contact information. Set it before running the server:

```bash
export SEC_USER_AGENT="Your Name you@example.com"
```

If `SEC_USER_AGENT` is not set, the server falls back to a placeholder (`research-agent contact@example.com`). The SEC may block or rate-limit requests that use a generic placeholder.

## Rate limiting

All requests are throttled to at most **10 requests per second** to stay polite to the SEC servers.

## Usage with Kimi CLI

Add the server to your `.mcp.json`:

```json
{
  "mcpServers": {
    "sec-edgar": {
      "command": "/workspace-stock-research/sec-edgar-mcp/.venv/bin/sec-edgar-mcp",
      "timeout": 60000,
      "env": {
        "SEC_USER_AGENT": "Your Name you@example.com"
      }
    }
  }
}
```

## Development / testing

Import check:

```bash
cd /workspace-stock-research/sec-edgar-mcp
source .venv/bin/activate
python -c "from sec_edgar_mcp.server import _mcp; print(_mcp.name)"
```

Quick smoke test (requires network access):

```python
from sec_edgar_mcp.server import search_company_by_ticker
print(search_company_by_ticker("AAPL"))
```
