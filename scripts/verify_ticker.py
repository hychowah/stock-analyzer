#!/usr/bin/env python3
"""Check that a Mode A ticker is a real market symbol before scaffolding.

Exit codes:
  0  real ticker
  2  unknown — not a real ticker and no obvious match
  3  not real, but an obvious match exists (re-run with that symbol)
  4  lookup error (yfinance missing / network)

Usage:
    python scripts/verify_ticker.py --ticker META
    python scripts/verify_ticker.py --ticker APPL
    python scripts/verify_ticker.py --ticker ZZZNOPE
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.kd_research.ticker_lookup import check_ticker  # noqa: E402

_EXIT = {
    "ok": 0,
    "abort_unknown": 2,
    "abort_match": 3,
    "abort_reserved": 2,
    "abort_syntax": 2,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    args = ap.parse_args(argv)
    try:
        result = check_ticker(args.ticker)
    except RuntimeError as exc:
        print(json.dumps({"status": "lookup_error", "reason": str(exc)}), flush=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4
    payload = {
        "typed": result.typed,
        "status": result.status,
        "canonical": result.canonical,
        "matches": result.matches,
        "reason": result.reason,
        "quote_type": result.quote_type,
        "name": result.name,
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    if result.status != "ok":
        print(f"ABORTED: {result.reason}", file=sys.stderr)
    return _EXIT.get(result.status, 2)


if __name__ == "__main__":
    raise SystemExit(main())
