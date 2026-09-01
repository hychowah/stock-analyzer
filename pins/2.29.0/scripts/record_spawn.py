#!/usr/bin/env python3
"""Record a specialist spawn_subagent event on the session ledger.

Call **launch** immediately before spawn_subagent, **return** after the
subagent comes back, **fail** if spawn is unavailable or errors — fail also
writes registry/abandon.json and stops the run.

Usage:
    python scripts/record_spawn.py --ticker META --date 2026-08-28 --subagent 5 --phase 2_parallel --event launch
    python scripts/record_spawn.py --ticker META --date 2026-08-28 --subagent 5 --phase 2_parallel --event return
    python scripts/record_spawn.py --ticker META --date 2026-08-28 --subagent 5 --phase 2_parallel --event fail --reason "spawn_subagent unavailable"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.kd_research.paths import resolve_session  # noqa: E402
from packages.kd_research.spawn_gate import record_spawn_event  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date", help="session_date or session_key")
    ap.add_argument("--session-dir", type=Path)
    ap.add_argument("--subagent", required=True, dest="subagent_id")
    ap.add_argument("--phase", required=True, dest="phase_id")
    ap.add_argument(
        "--event",
        required=True,
        choices=("launch", "return", "fail"),
    )
    ap.add_argument("--subagent-type", default=None, help="explore | coder | general-purpose")
    ap.add_argument("--reason", default=None, help="Required-ish for --event fail")
    args = ap.parse_args(argv)

    if args.session_dir:
        session = args.session_dir.resolve()
    elif args.ticker and args.date:
        found = resolve_session(args.ticker, args.date)
        session = found if found is not None else None
    else:
        ap.error("pass --session-dir or both --ticker and --date")
        return 2

    if session is None or not session.is_dir():
        print("ERROR: session not found", file=sys.stderr)
        return 2

    if args.event == "fail" and not (args.reason or "").strip():
        print("ERROR: --reason required for --event fail", file=sys.stderr)
        return 2

    try:
        row = record_spawn_event(
            session,
            subagent_id=args.subagent_id,
            phase_id=args.phase_id,
            event=args.event,
            subagent_type=args.subagent_type,
            fail_reason=args.reason,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(row, indent=2, ensure_ascii=False))
    if args.event == "fail":
        print(
            "SESSION ABANDONED — do not write specialist artifacts as the lead; "
            "do not continue the phase graph.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
