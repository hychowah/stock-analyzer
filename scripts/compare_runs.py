#!/usr/bin/env python3
"""Compare prediction snapshots for the same ticker across session dates.

Usage:
    python3 scripts/compare_runs.py --ticker META --dates 2026-07-30,2026-08-03
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.kd_research.paths import resolve_session  # noqa: E402


def _load_snap(ticker: str, date: str) -> dict[str, Any]:
    path = resolve_session(ticker, date)
    if path is None:
        raise SystemExit(f"Session not found: {ticker} {date}")
    snap_path = path / "meta" / "prediction_snapshot.json"
    if not snap_path.is_file():
        raise SystemExit(
            f"Missing {snap_path}. Run: python3 scripts/build_prediction_snapshot.py "
            f"--ticker {ticker} --date {date}"
        )
    return json.loads(snap_path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--dates", required=True, help="Comma-separated YYYY-MM-DD list")
    args = ap.parse_args()
    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    if len(dates) < 2:
        ap.error("need at least two dates")

    snaps = [(d, _load_snap(args.ticker, d)) for d in dates]
    keys = [
        ("asof_price", lambda s: s.get("asof_price")),
        ("fv_base", lambda s: (s.get("fair_value") or {}).get("base")),
        ("fv_bear", lambda s: (s.get("fair_value") or {}).get("bear")),
        ("fv_bull", lambda s: (s.get("fair_value") or {}).get("bull")),
        ("margin_of_safety_pct", lambda s: s.get("margin_of_safety_pct")),
        ("audit_verdict", lambda s: s.get("audit_verdict")),
        ("primary_sector", lambda s: s.get("primary_sector")),
        ("region", lambda s: s.get("region")),
        ("verdict_line", lambda s: (s.get("verdict_line") or "")[:80]),
    ]

    header = ["field"] + [d for d, _ in snaps]
    print("\t".join(header))
    for name, fn in keys:
        row = [name] + [str(fn(s)) for _, s in snaps]
        print("\t".join(row))

    print("\nkey_risks:")
    for d, s in snaps:
        print(f"  {d}: {s.get('key_risks')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
