#!/usr/bin/env python3
"""Phase-entry and phase-complete evidence preflight for research sessions.

Investment purpose: do not start valuation/reports (or mark swarm phases
complete) on incomplete evidence — prevents false-precision investment output.

Usage:
  python3 scripts/preflight_phase.py --ticker GRAB --date 2026-08-09 --phase 2_parallel
  python3 scripts/preflight_phase.py --session-dir archive/research/GRAB/2026-08-09 --phase 4_parallel
  python3 scripts/preflight_phase.py --ticker T --date D --phase 0 --mode complete
  python3 scripts/preflight_phase.py --ticker T --date D --phase 2_5 --mode complete

Exit code non-zero if any FAIL (WARN/SKIPPED do not fail the process).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.kd_research.gates import complete_checks, entry_checks  # noqa: E402
from scripts.kd_research.paths import session_root  # noqa: E402

VALID_PHASES = {
    "orch",
    "0",
    "1_parallel",
    "1b",
    "1c",
    "2_parallel",
    "2_5",
    "3",
    "4_parallel",
    "5",
    "done",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date")
    ap.add_argument("--session-dir", type=Path)
    ap.add_argument(
        "--phase",
        required=True,
        help="phase_id (e.g. 2_parallel, 2_5, 4_parallel, 5)",
    )
    ap.add_argument(
        "--mode",
        choices=("entry", "complete"),
        default="entry",
        help="entry=before starting phase; complete=merge/coverage before flipping phase complete",
    )
    ap.add_argument(
        "--strict-optional",
        action="store_true",
        help="FAIL if optional new-session files (e.g. research_brief) are missing",
    )
    args = ap.parse_args()

    if args.phase not in VALID_PHASES:
        print(f"Unknown phase_id={args.phase!r}. Valid: {sorted(VALID_PHASES)}", file=sys.stderr)
        return 2

    if args.session_dir:
        session = args.session_dir.resolve()
        ticker = args.ticker or session.parent.name
    else:
        if not args.ticker or not args.date:
            print("Provide --session-dir or both --ticker and --date", file=sys.stderr)
            return 2
        session = session_root(args.ticker, args.date)
        ticker = args.ticker

    if not session.is_dir():
        print(f"Session not found: {session}", file=sys.stderr)
        return 2

    if args.mode == "entry":
        rows = entry_checks(
            session,
            args.phase,
            ticker=ticker,
            strict_optional=args.strict_optional,
        )
    else:
        rows = complete_checks(session, args.phase)

    # Normalize WARN into display; only FAIL affects exit
    fails = 0
    warns = 0
    print(f"preflight mode={args.mode} phase={args.phase} session={session}")
    for status, check_id, detail in rows:
        if status == "WARN":
            warns += 1
        if status == "FAIL":
            fails += 1
        print(f"  {status:7}  {check_id}: {detail}")

    print(f"Summary: {fails} FAIL, {warns} WARN, {len(rows)} checks")
    if fails:
        print("PREFLIGHT FAIL — fix upstream evidence; do not invent numbers for the next phase.")
        return 1
    print("PREFLIGHT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
