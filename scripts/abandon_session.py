#!/usr/bin/env python3
"""Abandon a research session (terminal). Do not continue; do not finalize.

Use when a required specialist subagent cannot be spawned. The orchestrator
must not do that specialist's work inline.

Usage:
    python scripts/abandon_session.py --ticker META --date 2026-08-28 \\
        --reason spawn_failed --phase 2_parallel --subagent 5 \\
        --detail "spawn_subagent unavailable"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.kd_research.paths import resolve_session  # noqa: E402
from scripts.kd_research.spawn_gate import write_abandon  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date", help="session_date or session_key")
    ap.add_argument("--session-dir", type=Path)
    ap.add_argument("--reason", required=True)
    ap.add_argument("--phase", dest="phase_id", default=None)
    ap.add_argument("--subagent", dest="subagent_id", default=None)
    ap.add_argument("--detail", default=None)
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

    payload = write_abandon(
        session,
        reason=args.reason,
        phase_id=args.phase_id,
        subagent_id=args.subagent_id,
        detail=args.detail,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(
        "SESSION ABANDONED — do not continue; do not write specialist work as the lead.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
