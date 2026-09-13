#!/usr/bin/env python3
"""Confirm that a session's stamped quote_symbol is a live Yahoo quote.

Exit codes:
  0  stamp quotes
  2  stamp missing or listing does not quote
  4  lookup error (yfinance missing / network)

Usage:
    python scripts/verify_listing.py --ticker ADYEN --date 2026-08-29
    python scripts/verify_listing.py --session-dir path/to/S
    python scripts/verify_listing.py --quote-symbol ADYEN.AS
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.kd_research.paths import resolve_session  # noqa: E402
from packages.kd_research.ticker_lookup import (  # noqa: E402
    confirm_listing,
    confirm_session_listing,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date", help="session_date or session_key")
    ap.add_argument("--session-dir", type=Path)
    ap.add_argument("--quote-symbol")
    args = ap.parse_args(argv)
    try:
        if args.quote_symbol:
            result = confirm_listing(args.quote_symbol)
        elif args.session_dir:
            result = confirm_session_listing(args.session_dir.resolve())
        elif args.ticker and args.date:
            found = resolve_session(args.ticker, args.date)
            if found is None:
                print(
                    json.dumps({"ok": False, "reason": "session not found"}),
                    flush=True,
                )
                print("ABORTED: session not found", file=sys.stderr)
                return 2
            result = confirm_session_listing(found)
        else:
            ap.error("pass --quote-symbol, or --session-dir, or --ticker and --date")
            return 2
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}), flush=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4
    payload = {
        "ok": result.ok,
        "symbol": result.symbol,
        "reason": result.reason,
        "quote_type": result.quote_type,
        "name": result.name,
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    if not result.ok:
        print(f"ABORTED: {result.reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
