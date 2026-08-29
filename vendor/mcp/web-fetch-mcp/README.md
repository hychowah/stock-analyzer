# web-fetch-mcp

A lightweight MCP server that fetches web pages and returns clean, readable text.

## Tools

### `fetch_url(url: str, max_chars: int = 50000) -> dict`

Fetches a URL with a browser-like `User-Agent`, removes noisy markup (`script`,
`style`, `nav`, `header`, `footer`, `aside`, etc.), and returns the extracted
readable text.

Returns:

```json
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "text": "Clean article body...",
  "status": 200,
  "content_type": "text/html; charset=utf-8",
  "chars_returned": 12345
}
```

On failure it returns an `error` string alongside the requested `url`.

## Setup

Create a virtual environment and install the package:

```bash
cd /workspace-stock-research/web-fetch-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run the server:

```bash
.venv/bin/web-fetch-mcp
```

## Configuration

- `WEB_FETCH_USER_AGENT`: override the default browser-like User-Agent.
- The server enforces a polite delay of at least 0.1s between requests
  (max ~10 requests/sec).

## .mcp.json snippet

```json
{
  "mcpServers": {
    "web-fetch": {
      "command": "/workspace-stock-research/web-fetch-mcp/.venv/bin/web-fetch-mcp",
      "timeout": 60000,
      "env": {
        "WEB_FETCH_USER_AGENT": "research-agent contact@example.com"
      }
    }
  }
}
```
