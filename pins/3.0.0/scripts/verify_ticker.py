#!/usr/bin/env python3
"""Existence-check a Mode A ticker before scaffolding.

Exit codes:
  0  Yahoo quote or search listings exist (scaffold the typed ticker)
  2  unknown / reserved / syntax — do not scaffold
  4  lookup error (yfinance missing / network)

Usage:
    python scripts/verify_ticker.py --ticker META
    python scripts/verify_ticker.py --ticker ADYEN
    python scripts/verify_ticker.py --ticker ZZZNOPE
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.kd_research.ticker_lookup import live_ticker_check  # noqa: E402

_EXIT = {
    "quoted": 0,
    "search_evidence": 0,
    "abort_unknown": 2,
    "abort_reserved": 2,
    "abort_syntax": 2,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    args = ap.parse_args(argv)
    try:
        result = live_ticker_check(args.ticker)
    except RuntimeError as exc:
        print(json.dumps({"status": "lookup_error", "reason": str(exc)}), flush=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4
    payload = {
        "typed": result.typed,
        "status": result.status,
        "reason": result.reason,
        "quote_type": result.quote_type,
        "name": result.name,
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    if not result.ok:
        print(f"ABORTED: {result.reason}", file=sys.stderr)
    return _EXIT.get(result.status, 2)


if __name__ == "__main__":
    raise SystemExit(main())
