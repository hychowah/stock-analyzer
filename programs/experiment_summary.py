#!/usr/bin/env python3
"""Summarize catalog runs grouped by experiment_id (Mode B program).

Usage:
    python3 programs/experiment_summary.py
    python3 programs/experiment_summary.py --experiment exp-model-bakeoff --json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from packages.catalog_api.client import CatalogApi, default_archive_root  # noqa: E402


def _nums(rows: list[dict[str, Any]], key: str) -> list[float]:
    out: list[float] = []
    for r in rows:
        v = r.get(key)
        if isinstance(v, (int, float)):
            out.append(float(v))
    return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fv = _nums(rows, "fv_base")
    mos = _nums(rows, "margin_of_safety_pct")
    pass_n = sum(1 for r in rows if str(r.get("audit_verdict") or "").upper() == "PASS")
    return {
        "n": len(rows),
        "n_pass": pass_n,
        "fv_base_mean": statistics.mean(fv) if fv else None,
        "fv_base_stdev": statistics.stdev(fv) if len(fv) > 1 else (0.0 if len(fv) == 1 else None),
        "mos_mean": statistics.mean(mos) if mos else None,
        "tickers": sorted({str(r.get("ticker")) for r in rows if r.get("ticker")}),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", help="Filter to one experiment_id")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--limit", type=int, default=1000)
    args = ap.parse_args(argv)

    root = default_archive_root()
    api = CatalogApi(archive_root=root, readonly=True)

    runs = api.list_runs(
        experiment_id=args.experiment,
        limit=max(1, min(args.limit, 1000)),
    )
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in runs:
        groups[str(r.get("experiment_id") or "(none)")].append(r)

    report = {
        "archive_root": str(root),
        "groups": {k: summarize(v) for k, v in sorted(groups.items())},
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"ARCHIVE_ROOT={root}")
    print(f"runs_scanned={len(runs)}")
    for eid, stats in report["groups"].items():
        print(f"\n## {eid}")
        print(f"  n={stats['n']} pass={stats['n_pass']}")
        print(f"  fv_base_mean={stats['fv_base_mean']}")
        print(f"  mos_mean={stats['mos_mean']}")
        print(f"  tickers={','.join(stats['tickers'][:12])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
