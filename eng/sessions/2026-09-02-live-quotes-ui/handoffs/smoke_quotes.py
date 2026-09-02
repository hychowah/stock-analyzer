"""One-off smoke against a running analysis_web. Not part of pytest."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8767"


def get(path: str) -> tuple[int, str]:
    req = urllib.request.Request(BASE + path)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def main() -> None:
    status, home = get("/")
    print("GET /", status)
    print(" As-of", "As-of" in home)
    print(" Price min absent", 'aria-label="Price min"' not in home)
    print(" As-of min", 'aria-label="As-of min"' in home)
    print(" quotes.js", "/static/quotes.js" in home)
    print(" quote-live cells", home.count("quote-live"))
    print(" data-quote-cell", home.count("data-quote-cell"))
    print(" data-quote-symbol", home.count("data-quote-symbol="))
    symbols = re.findall(r'data-quote-symbol="([^"]+)"', home)
    unique = list(dict.fromkeys(symbols))
    print(" unique listings", len(unique), unique[:8])

    status, frag = get("/fragments/runs")
    print("GET /fragments/runs", status, "quote-cell", "data-quote-cell" in frag)

    if unique:
        qs = urllib.parse.urlencode({"symbols": ",".join(unique[:8])})
        status, body = get("/api/quotes?" + qs)
        data = json.loads(body)
        print("GET /api/quotes", status, "count", data.get("count"), "ttl", data.get("ttl_sec"))
        for row in data.get("quotes", []):
            print(
                " ",
                row.get("symbol"),
                row.get("price"),
                row.get("print_kind"),
                row.get("error"),
            )
        run_m = re.search(r'href="/runs/([^"]+)"', home)
        if run_m:
            rid = run_m.group(1)
            st, detail = get("/runs/" + rid)
            print("GET /runs/...", st, "Live", ">Live<" in detail, "symbol", "data-quote-symbol=" in detail)


if __name__ == "__main__":
    main()
