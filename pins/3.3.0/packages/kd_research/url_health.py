#!/usr/bin/env python3
"""URL health checks for news/background sources (investment source reliability).

Writes a structured list of {url, status, http_code|error, checked_at}.
Does not render JS. Network failures → status=unknown (do not invent).

Usage:
  python3 -m packages.kd_research.url_health --urls-file urls.txt --out health.json
  python3 -m packages.kd_research.url_health --url https://example.com --url https://...
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

URL_RE = re.compile(r"^https?://", re.I)


def classify_source(source: str) -> str:
    s = (source or "").strip()
    if not s:
        return "not_url"
    if URL_RE.match(s):
        return "url"
    return "not_url"


def check_url(url: str, timeout: float = 8.0) -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if classify_source(url) != "url":
        return {
            "url": url,
            "status": "not_url",
            "http_code": None,
            "error": None,
            "checked_at": checked_at,
        }
    # Prefer HEAD; some hosts reject HEAD → GET with range-ish short read
    req = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "stock-research-harness-url-health/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            code = getattr(resp, "status", None) or resp.getcode()
            status = "ok" if int(code) < 400 else "dead"
            return {
                "url": url,
                "status": status,
                "http_code": int(code),
                "error": None,
                "checked_at": checked_at,
            }
    except urllib.error.HTTPError as e:
        # Retry GET on 405/403 from HEAD-only blocks
        if e.code in (403, 405, 501):
            return _get_probe(url, timeout, checked_at)
        return {
            "url": url,
            "status": "dead",
            "http_code": int(e.code),
            "error": str(e.reason),
            "checked_at": checked_at,
        }
    except Exception as e:  # noqa: BLE001
        # Network/DNS/timeout
        if "405" in str(e) or "HEAD" in str(e):
            return _get_probe(url, timeout, checked_at)
        return {
            "url": url,
            "status": "unknown",
            "http_code": None,
            "error": str(e),
            "checked_at": checked_at,
        }


def _get_probe(url: str, timeout: float, checked_at: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "stock-research-harness-url-health/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            code = getattr(resp, "status", None) or resp.getcode()
            # read at most a tiny bit
            try:
                resp.read(256)
            except Exception:  # noqa: BLE001
                pass
            status = "ok" if int(code) < 400 else "dead"
            return {
                "url": url,
                "status": status,
                "http_code": int(code),
                "error": None,
                "checked_at": checked_at,
            }
    except urllib.error.HTTPError as e:
        return {
            "url": url,
            "status": "dead",
            "http_code": int(e.code),
            "error": str(e.reason),
            "checked_at": checked_at,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "url": url,
            "status": "unknown",
            "http_code": None,
            "error": str(e),
            "checked_at": checked_at,
        }


def check_many(urls: list[str], timeout: float = 8.0) -> list[dict[str, Any]]:
    return [check_url(u, timeout=timeout) for u in urls]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", action="append", default=[], help="URL to check (repeatable)")
    ap.add_argument("--urls-file", type=Path, help="File with one URL per line")
    ap.add_argument("--out", type=Path, help="Write JSON results to this path")
    ap.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args(argv)

    urls: list[str] = list(args.url)
    if args.urls_file:
        text = args.urls_file.read_text(encoding="utf-8")
        urls.extend(line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#"))

    if not urls:
        print("No URLs provided", file=sys.stderr)
        return 2

    results = check_many(urls, timeout=args.timeout)
    payload = {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results": results,
    }
    text = json.dumps(payload, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out} ({len(results)} URLs)")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
