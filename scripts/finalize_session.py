#!/usr/bin/env python3
"""Finalize a research session for lookback: snapshot + compare DB + catalog.

Run after Phase 5 audit (PASS or FAIL both exportable).

Usage:
    python3 scripts/finalize_session.py --ticker SOFI --date 2026-08-09
    python3 scripts/finalize_session.py --session-dir archive/research/META/2026-08-03
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.build_prediction_snapshot import build_for_session  # noqa: E402
from scripts.export_compare_db import export_session  # noqa: E402
from scripts.kd_research.compare_db import open_db  # noqa: E402
from scripts.kd_research.paths import resolve_session  # noqa: E402
from scripts.rebuild_catalog import patch_run_into_catalog, rebuild  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date", help="Session date or session_key")
    ap.add_argument("--session-dir")
    ap.add_argument("--skip-catalog", action="store_true", help="Skip thin JSON catalog update")
    ap.add_argument(
        "--full-catalog-rebuild",
        action="store_true",
        help="Full disk scan rebuild instead of O(1) patch (recovery / migration)",
    )
    ap.add_argument(
        "--include-legacy",
        action="store_true",
        help="With full rebuild, also scan legacy root sessions",
    )
    args = ap.parse_args()

    if args.session_dir:
        session = Path(args.session_dir)
    elif args.ticker and args.date:
        found = resolve_session(args.ticker, args.date)
        if found is None:
            print(f"Session not found: {args.ticker} {args.date}", file=sys.stderr)
            return 2
        session = found
    else:
        ap.error("pass --session-dir or --ticker and --date")

    snap = build_for_session(session, force=True)
    print(f"snapshot OK {snap['run_id']}")

    conn = open_db(rebuild=False)
    row = export_session(session, conn, refresh_snapshot=False)
    conn.commit()
    conn.close()
    print(
        f"compare_db OK {row['run_id']} price={row.get('asof_price')} "
        f"fv_base={row.get('fv_base')} audit={row.get('audit_verdict')}"
    )

    if not args.skip_catalog:
        ticker = str(row.get("ticker") or session.parent.name).upper()
        session_key = str(row.get("session_key") or session.name)
        if args.full_catalog_rebuild:
            result = rebuild(include_legacy=bool(args.include_legacy))
        else:
            result = patch_run_into_catalog(ticker, session_key, session)
        print(
            f"catalog OK mode={result.get('mode')} "
            f"{result['n_runs']} runs, {result['n_tickers']} tickers"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
