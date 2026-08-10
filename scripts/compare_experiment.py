#!/usr/bin/env python3
"""Summarize research runs for experiment / model / harness variation analysis.

Reads archive/catalog/research_compare.sqlite (rebuild with export_compare_db.py).

Usage:
    python3 scripts/compare_experiment.py --experiment exp-model-bakeoff
    python3 scripts/compare_experiment.py --ticker META --group-by orchestrator_model
    python3 scripts/compare_experiment.py --ticker META --group-by agents_md_sha256
    python3 scripts/compare_experiment.py --all --group-by primary_sector
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.kd_research.compare_db import connect, db_path  # noqa: E402

GROUPABLE = {
    "orchestrator_model",
    "default_subagent_model",
    "agents_md_sha256",
    "prompts_sha256",
    "harness_git_sha",
    "primary_sector",
    "region",
    "experiment_id",
    "model_name",
    "audit_verdict",
    "tech_signal",
}


def _calibration_report(conn, *, horizon: str, pass_only: bool) -> dict[str, Any]:
    """Join runs × outcomes for MoS direction hit rates."""
    sql = """
    SELECT r.run_id, r.ticker, r.session_date, r.margin_of_safety_pct, r.primary_sector,
           r.audit_verdict, o.horizon, o.total_return_pct, o.direction_hit, o.realized_price
    FROM runs r
    JOIN outcomes o ON o.run_id = r.run_id
    WHERE o.horizon = ?
      AND o.realized_price IS NOT NULL
    """
    params: list[Any] = [horizon]
    if pass_only:
        sql += " AND r.audit_verdict = 'PASS'"
    rows = [dict(x) for x in conn.execute(sql, params).fetchall()]

    def bucket(mos: float | None) -> str:
        if mos is None:
            return "mos_unknown"
        if mos >= 15:
            return "cheap_mos>=15"
        if mos <= -15:
            return "expensive_mos<=-15"
        return "fair_|mos|<15"

    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        b = bucket(r.get("margin_of_safety_pct"))
        groups.setdefault(b, []).append(r)

    def stats(items: list[dict[str, Any]]) -> dict[str, Any]:
        hits = [i["direction_hit"] for i in items if i.get("direction_hit") is not None]
        rets = [
            float(i["total_return_pct"])
            for i in items
            if isinstance(i.get("total_return_pct"), (int, float))
        ]
        return {
            "n": len(items),
            "n_scored": len(hits),
            "direction_hit_rate": (sum(hits) / len(hits)) if hits else None,
            "mean_return_pct": (sum(rets) / len(rets)) if rets else None,
        }

    return {
        "horizon": horizon,
        "n_joined": len(rows),
        "overall": stats(rows),
        "by_mos_bucket": {k: stats(v) for k, v in sorted(groups.items())},
    }


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _std(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    m = _mean(xs)
    assert m is not None
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def col(name: str) -> list[float]:
        out = []
        for r in rows:
            v = r.get(name)
            if isinstance(v, (int, float)):
                out.append(float(v))
        return out

    fv = col("fv_base")
    pw = col("fv_weighted")
    mos = col("margin_of_safety_pct")
    pb = col("p_bear")
    audit_pass = sum(1 for r in rows if (r.get("audit_verdict") or "").upper() == "PASS")
    return {
        "n": len(rows),
        "n_pass": audit_pass,
        "fv_base_mean": _mean(fv),
        "fv_base_std": _std(fv),
        "fv_weighted_mean": _mean(pw),
        "fv_weighted_std": _std(pw),
        "mos_mean": _mean(mos),
        "mos_std": _std(mos),
        "p_bear_mean": _mean(pb),
        "p_bear_std": _std(pb),
        "run_ids": [r.get("run_id") for r in rows],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", help="Filter by experiment_id")
    ap.add_argument("--ticker", help="Filter by ticker")
    ap.add_argument(
        "--group-by",
        default="orchestrator_model",
        help=f"Column to group by ({', '.join(sorted(GROUPABLE))})",
    )
    ap.add_argument("--pass-only", action="store_true", help="Only audit PASS rows")
    ap.add_argument("--all", action="store_true", help="No experiment filter required")
    ap.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    ap.add_argument(
        "--calibration",
        action="store_true",
        help="Report MoS-bucket direction hit rates joined to outcomes marks",
    )
    ap.add_argument(
        "--horizon",
        default="1m",
        help="Outcomes horizon for --calibration (default 1m)",
    )
    args = ap.parse_args()

    if not args.calibration and not args.experiment and not args.ticker and not args.all:
        ap.error("pass --experiment, --ticker, --all, and/or --calibration")

    if not args.calibration and args.group_by not in GROUPABLE:
        ap.error(f"--group-by must be one of {sorted(GROUPABLE)}")

    try:
        conn = connect(readonly=True)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        print("Run: python3 scripts/export_compare_db.py --all --rebuild", file=sys.stderr)
        return 2

    if args.calibration:
        report = _calibration_report(conn, horizon=args.horizon, pass_only=args.pass_only)
        conn.close()
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
            return 0
        print(f"Calibration horizon={report['horizon']} joined_rows={report['n_joined']}")
        o = report["overall"]
        print(
            f"  overall n={o['n']} scored={o['n_scored']} "
            f"hit_rate={_fmt(o['direction_hit_rate'])} mean_ret%={_fmt(o['mean_return_pct'])}"
        )
        for b, s in report["by_mos_bucket"].items():
            print(
                f"  {b}: n={s['n']} scored={s['n_scored']} "
                f"hit_rate={_fmt(s['direction_hit_rate'])} mean_ret%={_fmt(s['mean_return_pct'])}"
            )
        return 0

    sql = "SELECT * FROM runs WHERE 1=1"
    params: list[Any] = []
    if args.experiment:
        sql += " AND experiment_id = ?"
        params.append(args.experiment)
    if args.ticker:
        sql += " AND ticker = ?"
        params.append(args.ticker.upper())
    if args.pass_only:
        sql += " AND audit_verdict = 'PASS'"
    sql += " ORDER BY ticker, session_date, session_key"

    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = r.get(args.group_by)
        label = "(null)" if key is None or key == "" else str(key)
        groups[label].append(r)

    report = {
        "db": str(db_path()),
        "filters": {
            "experiment_id": args.experiment,
            "ticker": args.ticker,
            "pass_only": args.pass_only,
        },
        "group_by": args.group_by,
        "n_runs": len(rows),
        "groups": {k: _summarize(v) for k, v in sorted(groups.items())},
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
        return 0

    print(f"DB: {report['db']}")
    print(f"Runs: {report['n_runs']}  group_by={args.group_by}")
    if not rows:
        print("No matching runs.")
        return 0
    for gname, s in report["groups"].items():
        print(f"\n## {gname}")
        print(f"  n={s['n']} pass={s['n_pass']}")
        print(
            f"  fv_base mean={_fmt(s['fv_base_mean'])} std={_fmt(s['fv_base_std'])}  "
            f"weighted mean={_fmt(s['fv_weighted_mean'])} std={_fmt(s['fv_weighted_std'])}"
        )
        print(
            f"  mos% mean={_fmt(s['mos_mean'])} std={_fmt(s['mos_std'])}  "
            f"p_bear mean={_fmt(s['p_bear_mean'])} std={_fmt(s['p_bear_std'])}"
        )
    return 0


def _fmt(v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"{v:.4g}"


if __name__ == "__main__":
    sys.exit(main())
