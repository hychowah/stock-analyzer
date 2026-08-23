#!/usr/bin/env python3
"""Copy the library required set into an in-progress research session.

Usage:
    python scripts/bind_library.py --ticker META --date 2026-08-23
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.kd_research.library import (  # noqa: E402
    LibraryError,
    bind_to_session,
    compare_freshness,
    load_index_items,
    required_annual_count,
)
from scripts.kd_research.paths import resolve_session  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bind library required set into session")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--date", required=True, help="session_date or session_key")
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    ticker = args.ticker.strip().upper()
    session = resolve_session(ticker, args.date, args.output_dir)
    if session is None or not session.is_dir():
        print(f"ERROR: session not found for {ticker} {args.date}", file=sys.stderr)
        return 2
    try:
        bind = bind_to_session(ticker, session, output_dir=args.output_dir)
    except LibraryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    items, source = load_index_items(session)
    freshness = None
    if source:
        n_annual = required_annual_count(session)
        bound_docs = list(bind.get("bound") or [])
        freshness = compare_freshness(items, bound_docs, n_annual=n_annual)
        bind["index_source"] = source
        bind["session_missing"] = freshness["session_missing"]
        bind["library_gaps"] = freshness["library_gaps"]
        # Do not treat this as data_fetch_log.freshness — 2b must write that after the check.

    print(json.dumps(bind, indent=2, ensure_ascii=False, default=str))
    missing = (freshness or {}).get("session_missing") or []
    if missing:
        print(f"session_missing: {len(missing)} (2b must fetch these into S)", file=sys.stderr)
    else:
        print("session_missing: [] (no required-set download unless index is added)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
