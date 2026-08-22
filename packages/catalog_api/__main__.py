"""CLI: python3 -m packages.catalog_api health|list-runs|get-run"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from packages.catalog_api.client import (
    CatalogApi,
    DbMissing,
    RunNotFound,
    default_archive_root,
)


def _api_from_env() -> CatalogApi:
    raw = os.environ.get("ARCHIVE_ROOT")
    root = Path(raw).expanduser().resolve() if raw else default_archive_root()
    return CatalogApi(archive_root=root, readonly=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="packages.catalog_api")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health", help="Catalog health probe")

    p_list = sub.add_parser("list-runs", help="List runs")
    p_list.add_argument("--ticker", help="Exact ticker match")
    p_list.add_argument("--ticker-prefix", help="Ticker starts-with (case-insensitive)")
    p_list.add_argument("--sector")
    p_list.add_argument("--region")
    p_list.add_argument("--experiment-id")
    p_list.add_argument("--audit-verdict")
    p_list.add_argument("--tech-signal")
    p_list.add_argument("--session-date-from", help="Inclusive YYYY-MM-DD")
    p_list.add_argument("--session-date-to", help="Inclusive YYYY-MM-DD")
    p_list.add_argument("--mos-min", type=float)
    p_list.add_argument("--mos-max", type=float)
    p_list.add_argument("--price-min", type=float)
    p_list.add_argument("--price-max", type=float)
    p_list.add_argument("--fv-base-min", type=float)
    p_list.add_argument("--fv-base-max", type=float)
    p_list.add_argument("--sort", help="Allowlisted runs column")
    p_list.add_argument("--dir", choices=["asc", "desc"], help="Sort direction")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--offset", type=int, default=0)

    p_get = sub.add_parser("get-run", help="Get one run by run_id")
    p_get.add_argument("run_id")

    p_rep = sub.add_parser("report-paths", help="Report paths for run_id")
    p_rep.add_argument("run_id")

    p_cal = sub.add_parser("calibration", help="MoS vs outcomes calibration")
    p_cal.add_argument("--horizon", default="1m")
    p_cal.add_argument("--all-audits", action="store_true", help="Include non-PASS audits")

    args = ap.parse_args(argv)
    api = _api_from_env()
    try:
        if args.cmd == "health":
            print(json.dumps(api.health(), indent=2))
            return 0 if api.health().get("db_exists") else 2
        if args.cmd == "list-runs":
            rows = api.list_runs(
                ticker=args.ticker,
                ticker_prefix=args.ticker_prefix,
                sector=args.sector,
                region=args.region,
                experiment_id=args.experiment_id,
                audit_verdict=args.audit_verdict,
                tech_signal=args.tech_signal,
                session_date_from=args.session_date_from,
                session_date_to=args.session_date_to,
                mos_min=args.mos_min,
                mos_max=args.mos_max,
                price_min=args.price_min,
                price_max=args.price_max,
                fv_base_min=args.fv_base_min,
                fv_base_max=args.fv_base_max,
                sort=args.sort,
                dir=args.dir,
                limit=args.limit,
                offset=args.offset,
            )
            print(json.dumps(rows, indent=2, default=str))
            return 0
        if args.cmd == "get-run":
            print(json.dumps(api.get_run(args.run_id), indent=2, default=str))
            return 0
        if args.cmd == "report-paths":
            print(json.dumps(api.get_report_paths(args.run_id), indent=2))
            return 0
        if args.cmd == "calibration":
            print(
                json.dumps(
                    api.calibration(
                        horizon=args.horizon,
                        pass_only=not args.all_audits,
                    ),
                    indent=2,
                )
            )
            return 0
    except DbMissing as e:
        print(f"DB missing: {e}", file=sys.stderr)
        return 2
    except RunNotFound as e:
        print(f"Run not found: {e}", file=sys.stderr)
        return 3
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
