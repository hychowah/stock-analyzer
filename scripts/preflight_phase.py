#!/usr/bin/env python3
"""Phase-entry and phase-complete evidence preflight for research sessions.

Investment purpose: do not start valuation/reports (or mark swarm phases
complete) on incomplete evidence — prevents false-precision investment output.

Also enforces the **phase graph**:
- prior phases must be complete|skipped before entry
- optional ``--subagent`` must belong to that phase (specialist workers only;
  orchestrator is the lead, not a phase subagent)

Usage:
  python3 scripts/preflight_phase.py --ticker GRAB --date 2026-08-09 --phase 2_parallel
  python3 scripts/preflight_phase.py --session-dir archive/research/GRAB/2026-08-09 --phase 4_parallel
  python3 scripts/preflight_phase.py --ticker T --date D --phase 2_parallel --subagent 5
  python3 scripts/preflight_phase.py --ticker T --date D --phase 0 --mode complete
  python3 scripts/preflight_phase.py --ticker T --date D --phase 2_5 --mode complete
  python3 scripts/preflight_phase.py --ticker T --date D --phase 0 --show-next

Exit code non-zero if any FAIL (WARN/SKIPPED do not fail the process).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.kd_research.gates import complete_checks, entry_checks  # noqa: E402
from scripts.kd_research.paths import resolve_session, session_root  # noqa: E402
from scripts.kd_research.phase_graph import (  # noqa: E402
    PHASE_ORDER,
    next_open_phase,
)

VALID_PHASES = set(PHASE_ORDER)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date", help="As-of date or full session_key")
    ap.add_argument("--session-dir", type=Path)
    ap.add_argument(
        "--phase",
        required=True,
        help="phase_id (e.g. 2_parallel, 2_5, 4_parallel, 5)",
    )
    ap.add_argument(
        "--subagent",
        default=None,
        dest="subagent_id",
        help=(
            "Optional subagent id (e.g. 5, 2e, phase0_swarm, valuation) — "
            "must belong to --phase. Use for specialist workers, not the orchestrator."
        ),
    )
    # Deprecated alias (still accepted)
    ap.add_argument(
        "--agent",
        default=None,
        help=argparse.SUPPRESS,  # hidden; prefer --subagent
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
    ap.add_argument(
        "--show-next",
        action="store_true",
        help="Print next open phase from phase_status and exit 0 (ignores other gates)",
    )
    args = ap.parse_args()

    if args.phase not in VALID_PHASES:
        print(f"Unknown phase_id={args.phase!r}. Valid: {PHASE_ORDER}", file=sys.stderr)
        return 2

    if args.session_dir:
        session = args.session_dir.resolve()
        ticker = args.ticker or session.parent.name
    else:
        if not args.ticker or not args.date:
            print("Provide --session-dir or both --ticker and --date", file=sys.stderr)
            return 2
        found = resolve_session(args.ticker, args.date)
        session = found if found is not None else session_root(args.ticker, args.date)
        ticker = args.ticker

    if not session.is_dir():
        print(f"Session not found: {session}", file=sys.stderr)
        return 2

    if args.show_next:
        nxt = next_open_phase(session)
        print(f"next_open_phase={nxt} session={session}")
        return 0

    subagent = args.subagent_id or args.agent

    if args.mode == "entry":
        rows = entry_checks(
            session,
            args.phase,
            ticker=ticker,
            strict_optional=args.strict_optional,
            subagent_id=subagent,
        )
    else:
        rows = complete_checks(session, args.phase)

    fails = 0
    warns = 0
    print(f"preflight mode={args.mode} phase={args.phase} session={session}")
    if subagent:
        print(f"  subagent={subagent}")
    for status, check_id, detail in rows:
        if status == "WARN":
            warns += 1
        if status == "FAIL":
            fails += 1
        print(f"  {status:7}  {check_id}: {detail}")

    print(f"Summary: {fails} FAIL, {warns} WARN, {len(rows)} checks")
    if fails:
        print(
            "PREFLIGHT FAIL — fix upstream phase/subagent graph or evidence; "
            "do not invent numbers for the next phase."
        )
        return 1
    print("PREFLIGHT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
