"""FastMCP server exposing lightweight web-fetch and readable-text extraction."""

import os
import re
import time
import urllib.parse
from typing import Any

from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("web-fetch")

# Simple process-level rate limiter: max 10 requests/sec with 0.1s between calls.
_last_request_time: float = 0.0
_MIN_REQUEST_INTERVAL = 0.1

# Browser-like User-Agent to reduce blocks.
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Tags that are generally not part of the readable article content.
_NOISE_TAGS = {
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "form",
    "button",
    "input",
    "select",
    "textarea",
    "label",
}


def _polite_delay() -> None:
    """Enforce a minimum delay between consecutive requests."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def _normalize_url(url: str) -> str:
    """Add scheme if missing and strip fragments."""
    url = url.strip()
    if not url:
        raise ValueError("URL is empty")
    if not urllib.parse.urlparse(url).scheme:
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    # Remove fragment; keep query string.
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, "")
    )


def _extract_text(soup: BeautifulSoup, max_chars: int) -> str:
    """Extract readable text from BeautifulSoup, removing noise tags."""
    # Drop noisy tags first.
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    # Prefer <article> or <main> if present.
    body = soup.find("article") or soup.find("main") or soup.find("body") or soup

    # Collect text from remaining visible block/inline tags.
    chunks: list[str] = []
    for element in body.find_all(string=True):
        parent = element.parent
        if parent is None:
            continue
        parent_name = parent.name.lower() if parent.name else ""
        if parent_name in _NOISE_TAGS:
            continue
        text = str(element).strip()
        if not text:
            continue
        # Skip inline script/style contents that slipped through.
        if "{" in text and "}" in text and len(text) < 200:
            continue
        chunks.append(text)

    # Join with newlines and collapse excessive whitespace.
    joined = "\n".join(chunks)
    joined = re.sub(r"\n\s*\n+", "\n\n", joined)
    joined = re.sub(r"[ \t]+", " ", joined)
    joined = joined.strip()

    if max_chars > 0:
        joined = joined[:max_chars]

    return joined


def _fetch(url: str, max_chars: int) -> dict[str, Any]:
    """Internal fetch implementation returning a result dict."""
    normalized = _normalize_url(url)
    user_agent = os.environ.get("WEB_FETCH_USER_AGENT", _DEFAULT_USER_AGENT)
    # Only advertise encodings that the requests library is guaranteed to
    # decode automatically. Brotli ('br') is omitted unless brotli is installed.
    try:
        import brotli  # noqa: F401
        accept_encoding = "gzip, deflate, br"
    except Exception:
        accept_encoding = "gzip, deflate"

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": accept_encoding,
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    _polite_delay()
    resp = requests.get(normalized, headers=headers, timeout=30, allow_redirects=True)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "").lower()
    is_html = "text/html" in content_type or "application/xhtml" in content_type

    final_url = resp.url
    title = ""
    text = ""

    if is_html:
        soup = BeautifulSoup(resp.content, "html.parser")
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
        text = _extract_text(soup, max_chars)
    else:
        # Plain text or binary-ish content: decode as text.
        text = resp.text[:max_chars] if max_chars > 0 else resp.text

    return {
        "url": final_url,
        "title": title,
        "text": text,
        "status": resp.status_code,
        "content_type": resp.headers.get("Content-Type", ""),
        "chars_returned": len(text),
    }


@mcp.tool()
def fetch_url(url: str, max_chars: int = 50000) -> dict:
    """Fetch a URL and extract readable text using BeautifulSoup.

    Removes script/style/nav/header/footer/aside and other noisy tags to return
    a clean text representation of the page. Useful for reading SEC filings,
    earnings releases, and news articles.

    Args:
        url: The URL to fetch. A scheme is added if missing.
        max_chars: Maximum characters of extracted text to return (default 50000).

    Returns:
        dict with url, title, text, status, content_type, and chars_returned.
        On failure returns an error dict with url and error keys.
    """
    try:
        return _fetch(url, max_chars)
    except requests.exceptions.Timeout:
        return {"error": "Request timed out", "url": url}
    except requests.exceptions.HTTPError as e:
        return {
            "error": f"HTTP {e.response.status_code}: {str(e)}",
            "url": getattr(e.response, "url", url),
            "status": e.response.status_code,
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}", "url": url}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}", "url": url}


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
