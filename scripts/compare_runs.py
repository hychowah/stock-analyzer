#!/usr/bin/env python3
"""Compare prediction snapshots for the same ticker across session dates.

Usage:
    python3 scripts/compare_runs.py --ticker META --dates 2026-07-30,2026-08-03
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.compare_jobs.headline import headline_for_keys  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--dates", required=True, help="Comma-separated session keys")
    args = ap.parse_args()
    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    if len(dates) < 2:
        ap.error("need at least two dates")

    try:
        table = headline_for_keys(args.ticker, dates)
    except FileNotFoundError as e:
        raise SystemExit(str(e)) from e

    header = ["field"] + table["sessions"]
    print("\t".join(header))
    for row in table["fields"]:
        vals = [str(row["values"].get(k)) for k in table["sessions"]]
        print("\t".join([row["field"], *vals]))

    print("\nkey_risks:")
    for key in table["sessions"]:
        print(f"  {key}: {table['key_risks'].get(key)}")
    if table.get("degraded"):
        print("\n(degraded: one or more prediction_snapshot.json missing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
