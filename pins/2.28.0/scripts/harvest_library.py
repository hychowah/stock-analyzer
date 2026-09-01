#!/usr/bin/env python3
"""Copy session raw_sec/transcripts into archive/library/ (ops; not Mode A).

Never mutates archive/research or archive/outcomes. Extension allowlist only.

Usage:
    python scripts/harvest_library.py --ticker META
    python scripts/harvest_library.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.kd_research.library import harvest_ticker  # noqa: E402
from packages.kd_research.paths import iter_research_sessions  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Harvest session documents into the library")
    ap.add_argument("--ticker", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)
    if not args.ticker and not args.all:
        print("ERROR: pass --ticker T or --all", file=sys.stderr)
        return 2

    tickers: list[str]
    if args.all:
        seen: set[str] = set()
        for t, _k, _p in iter_research_sessions(args.output_dir):
            seen.add(t)
        tickers = sorted(seen)
    else:
        tickers = [args.ticker.strip().upper()]

    summary: dict[str, int] = {}
    for t in tickers:
        rows = harvest_ticker(t, output_dir=args.output_dir)
        n_new = sum(1 for r in rows if r.get("status") == "ingested")
        n_dup = sum(1 for r in rows if r.get("status") == "duplicate")
        summary[t] = n_new
        print(f"{t}: ingested={n_new} duplicate={n_dup} rows={len(rows)}")
    print(json.dumps({"ingested_new": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
