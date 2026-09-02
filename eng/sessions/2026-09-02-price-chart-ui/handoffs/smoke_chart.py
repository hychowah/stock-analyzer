"""Smoke the run-detail chart against a live UI. No FV writes."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8768"
RUN = "/runs/research:META:2026-08-03"


def get(path: str, timeout: int = 20) -> tuple[int, bytes]:
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main() -> int:
    code, raw = get(RUN)
    html = raw.decode("utf-8", "replace")
    print("DETAIL", code, len(html))
    for needle in (
        'id="price-chart"',
        'data-symbol="META"',
        "price_chart.js",
        "fv_bear",
        "fv_base",
        "fv_bull",
        'data-range="1y"',
        "Price vs analysis",
    ):
        print(" ", needle, needle in html)
        if needle not in html:
            return 1
    i = html.find("price-chart-overlay")
    print("OVERLAY", html[i : i + 360].replace("\n", " "))

    code, js = get("/static/price_chart.js")
    print("JS", code, len(js), b"/api/price-history" in js)
    if code != 200 or b"/api/price-history" not in js:
        return 1

    for rng in ("1y", "3m"):
        code, raw = get(f"/api/price-history?symbol=META&range={rng}", timeout=60)
        body = json.loads(raw.decode())
        bars = body.get("bars") or []
        print(
            "HIST",
            rng,
            code,
            "count",
            body.get("count"),
            "err",
            body.get("error"),
            "first",
            bars[0] if bars else None,
            "last",
            bars[-1] if bars else None,
        )
        if code != 200 or not bars:
            return 1

    code, _ = get("/api/price-history?symbol=META&range=1d")
    print("BADRANGE", code)
    if code != 400:
        return 1
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
