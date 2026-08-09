"""FastMCP server exposing SEC EDGAR lookup tools.

All requests to SEC EDGAR are made with a descriptive User-Agent header and
are throttled to at most 10 requests per second. Set ``SEC_USER_AGENT`` in the
environment to provide a real contact email; otherwise a default placeholder is
used and the SEC may block heavy use.
"""

from __future__ import annotations

import html
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_USER_AGENT = "research-agent contact@example.com"
MAX_REQUESTS_PER_SECOND = 10
TICKER_TXT_URL = "https://www.sec.gov/include/ticker.txt"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES_BASE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}"

# Where full filing texts are written. Tools return only a short preview in
# their MCP response; the COMPLETE text always lands in this directory and the
# response carries its path (see get_filing_text).
CACHE_DIR = Path(os.environ.get("SEC_EDGAR_CACHE_DIR", Path.home() / ".cache" / "sec-edgar-mcp"))


# ---------------------------------------------------------------------------
# Rate limiter + shared session
# ---------------------------------------------------------------------------

class RateLimiter:
    """Sliding-window rate limiter enforcing ``max_requests`` per second."""

    def __init__(self, max_requests: int = 10, window_seconds: float = 1.0) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._times: list[float] = []
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until the next request is allowed."""
        with self._lock:
            now = time.monotonic()
            cutoff = now - self.window
            # Drop requests that fell outside the window
            while self._times and self._times[0] <= cutoff:
                self._times.pop(0)

            if len(self._times) >= self.max_requests:
                sleep_seconds = self.window - (now - self._times[0]) + 0.001
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
                    now = time.monotonic()
                    cutoff = now - self.window
                    while self._times and self._times[0] <= cutoff:
                        self._times.pop(0)

            self._times.append(now)


_limiter = RateLimiter(max_requests=MAX_REQUESTS_PER_SECOND, window_seconds=1.0)
_session = requests.Session()


def _user_agent() -> str:
    """Return the SEC-required User-Agent string."""
    return os.environ.get("SEC_USER_AGENT", DEFAULT_USER_AGENT)


def _sec_request(url: str, **kwargs: Any) -> requests.Response:
    """Make a polite, rate-limited GET request to SEC EDGAR."""
    _limiter.wait()
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", _user_agent())
    headers.setdefault("Accept-Encoding", "gzip, deflate")
    response = _session.get(url, headers=headers, timeout=30, **kwargs)
    response.raise_for_status()
    return response


# ---------------------------------------------------------------------------
# Ticker -> CIK mapping
# ---------------------------------------------------------------------------

_TICKER_TO_CIK: dict[str, str] = {}
_TICKER_LOCK = threading.Lock()


def _load_ticker_map() -> dict[str, str]:
    """Load and cache the SEC ticker.txt file in memory."""
    global _TICKER_TO_CIK
    with _TICKER_LOCK:
        if _TICKER_TO_CIK:
            return _TICKER_TO_CIK

        response = _sec_request(TICKER_TXT_URL)
        mapping: dict[str, str] = {}
        for line in response.text.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                ticker = parts[0].strip().lower()
                cik = parts[1].strip().zfill(10)
                mapping[ticker] = cik
        _TICKER_TO_CIK = mapping
        return mapping


def _lookup_cik(ticker: str) -> str | None:
    """Return the zero-padded CIK for a ticker, or None if unknown."""
    mapping = _load_ticker_map()
    return mapping.get(ticker.strip().lower())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_mcp = FastMCP("sec-edgar")


def _clean_cik(cik: str) -> str:
    """Return CIK as a zero-padded 10-digit string."""
    return str(int(cik)).zfill(10)


def _path_cik(cik: str) -> str:
    """Return CIK stripped of leading zeros for use in archive URLs."""
    return str(int(cik))


def _strip_dashes(accession: str) -> str:
    """Remove dashes from an accession number."""
    return accession.replace("-", "")


def _get_submissions(cik: str) -> dict[str, Any]:
    """Fetch the SEC submissions JSON for a CIK."""
    url = SUBMISSIONS_URL.format(cik=_clean_cik(cik))
    return _sec_request(url).json()


def _html_to_text(html_text: str) -> str:
    """Crude but dependency-free HTML-to-text conversion."""
    # Remove scripts and styles
    text = re.sub(
        r"<(script|style)[^>]*>.*?</\1>", " ", html_text, flags=re.S | re.I
    )
    # Convert common block-level tags to newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div|li|h[1-6]|tr|td|table)>", "\n", text, flags=re.I)
    # Remove remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@_mcp.tool()
def search_company_by_ticker(ticker: str) -> dict[str, Any]:
    """Map a ticker symbol to a SEC CIK, name, and SIC code.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL").

    Returns:
        dict with ticker, CIK, company name, SIC, and recent-filing metadata.
    """
    try:
        cik = _lookup_cik(ticker)
        if not cik:
            return {
                "error": f"Ticker '{ticker}' not found in SEC ticker mapping",
                "ticker": ticker,
            }

        data = _get_submissions(cik)
        recent = data.get("filings", {}).get("recent", {})
        accession_list = recent.get("accessionNumber", [])

        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "company_name": data.get("name") or data.get("entityName"),
            "sic": data.get("sic"),
            "sic_description": data.get("sicDescription"),
            "fiscal_year_end": data.get("fiscalYearEnd"),
            "state_of_incorporation": data.get("stateOfIncorporation"),
            "phone": data.get("phone"),
            "recent_filings_count": len(accession_list),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "ticker": ticker}


@_mcp.tool()
def get_latest_filings(
    ticker: str, form_type: str = "10-Q", count: int = 5
) -> dict[str, Any]:
    """Return recent SEC filings metadata for a ticker and form type.

    Args:
        ticker: Stock ticker symbol.
        form_type: SEC form to filter (default "10-Q").
        count: Maximum number of filings to return (default 5).

    Returns:
        dict with ticker, form_type, and a list of filing metadata records.
    """
    try:
        cik = _lookup_cik(ticker)
        if not cik:
            return {
                "error": f"Ticker '{ticker}' not found in SEC ticker mapping",
                "ticker": ticker,
            }

        data = _get_submissions(cik)
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])

        keys = [
            "accessionNumber",
            "filingDate",
            "reportDate",
            "acceptanceDateTime",
            "act",
            "form",
            "fileNo",
            "filmNumber",
            "items",
            "size",
            "isXBRL",
            "isInlineXBRL",
            "primaryDocument",
            "primaryDocDescription",
        ]

        filings: list[dict[str, Any]] = []
        for idx, form in enumerate(forms):
            if form != form_type:
                continue
            filing: dict[str, Any] = {}
            for key in keys:
                values = recent.get(key)
                filing[key] = values[idx] if isinstance(values, list) and idx < len(values) else None
            filings.append(filing)
            if len(filings) >= count:
                break

        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "form_type": form_type,
            "count": len(filings),
            "filings": filings,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "ticker": ticker, "form_type": form_type}


@_mcp.tool()
def get_filing_text(accession_number: str, cik: str) -> dict[str, Any]:
    """Fetch the primary document text for a SEC filing.

    IMPORTANT: the returned ``text_preview`` is TRUNCATED to 20,000 characters.
    The complete document text is always written to a local file; read it from
    ``full_text_path`` in the response (check ``preview_truncated``).

    Args:
        accession_number: Filing accession number (dashes optional).
        cik: Company CIK (leading zeros optional).

    Returns:
        dict with URL, content type, full-text file path, and a text preview.
    """
    try:
        cik_path = _path_cik(cik)
        acc_path = _strip_dashes(accession_number)
        base_url = ARCHIVES_BASE_URL.format(cik=cik_path, accession=acc_path)

        # Try to discover the primary document via the index JSON.
        document_name: str | None = None
        try:
            index = _sec_request(f"{base_url}/index.json").json()
            directory = index.get("directory", {})
            items = directory.get("item", []) or directory.get("itemList", [])

            def _item_size(item: dict[str, Any]) -> int:
                try:
                    return int(item.get("size", "0") or "0")
                except ValueError:
                    return 0

            html_items = [
                item
                for item in items
                if item.get("name", "").lower().endswith((".htm", ".html"))
                and "index" not in item.get("name", "").lower()
            ]
            txt_items = [
                item
                for item in items
                if item.get("name", "").lower().endswith(".txt")
            ]

            if html_items:
                document_name = max(html_items, key=_item_size).get("name")
            elif txt_items:
                document_name = max(txt_items, key=_item_size).get("name")
            elif items:
                document_name = items[0].get("name")
        except Exception:  # noqa: BLE001
            pass

        if not document_name:
            document_name = f"{accession_number}-index.html"

        doc_url = f"{base_url}/{document_name}"
        response = _sec_request(doc_url)
        content_type = response.headers.get("Content-Type", "")
        raw_text = response.text

        if (
            "html" in content_type.lower()
            or raw_text.strip().lower().startswith(("<!doctype html", "<html"))
        ):
            extracted_text = _html_to_text(raw_text)
        else:
            extracted_text = raw_text

        preview_limit = 20_000
        preview = extracted_text[:preview_limit].strip()

        # Always persist the complete text; the preview alone is a trap for
        # callers that assume they received the whole filing.
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{_clean_cik(cik)}_{acc_path}_{document_name}")
        full_path = CACHE_DIR / f"{safe_name}.txt"
        full_path.write_text(extracted_text, encoding="utf-8")

        return {
            "accession_number": accession_number,
            "cik": _clean_cik(cik),
            "url": doc_url,
            "content_type": content_type,
            "text_preview": preview,
            "text_length": len(extracted_text),
            "full_text_path": str(full_path),
            "preview_truncated": len(extracted_text) > preview_limit,
            "note": "text_preview is truncated to 20,000 chars; the COMPLETE filing text is at full_text_path.",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "error": str(exc),
            "accession_number": accession_number,
            "cik": cik,
        }


@_mcp.tool()
def get_latest_earnings_release(ticker: str) -> dict[str, Any]:
    """Find the latest 8-K exhibit 99.1 (earnings release) for a ticker.

    NOTE: ``text_preview`` is truncated to 20,000 characters; the complete
    release text is at ``full_text_path`` (see get_filing_text).

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with filing metadata, URL, full-text file path, and text preview.
    """
    try:
        cik = _lookup_cik(ticker)
        if not cik:
            return {
                "error": f"Ticker '{ticker}' not found in SEC ticker mapping",
                "ticker": ticker,
            }

        data = _get_submissions(cik)
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        primary_documents = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])
        items_list = recent.get("items", [])

        for idx, form in enumerate(forms):
            if form != "8-K":
                continue
            desc = (descriptions[idx] or "").lower()
            items = (items_list[idx] or "") if idx < len(items_list) else ""
            is_earnings = (
                "99.1" in desc
                or "earnings" in desc
                or "press release" in desc
                or "2.02" in str(items)
            )
            if not is_earnings:
                continue
            accession = accession_numbers[idx]
            text_result = get_filing_text(accession, cik)
            if "error" in text_result:
                return {
                    "error": text_result["error"],
                    "ticker": ticker.upper(),
                    "accession_number": accession,
                }
            return {
                "ticker": ticker.upper(),
                "cik": cik,
                "accession_number": accession,
                "filing_date": filing_dates[idx] if idx < len(filing_dates) else None,
                "form": "8-K",
                "primary_document": primary_documents[idx]
                if idx < len(primary_documents)
                else None,
                "primary_doc_description": descriptions[idx],
                "url": text_result["url"],
                "text_preview": text_result["text_preview"],
                "text_length": text_result.get("text_length"),
                "full_text_path": text_result.get("full_text_path"),
                "preview_truncated": text_result.get("preview_truncated"),
            }

        return {
            "error": "No recent 8-K earnings release (exhibit 99.1) found",
            "ticker": ticker.upper(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "ticker": ticker}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the SEC EDGAR MCP server over stdio."""
    _mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
