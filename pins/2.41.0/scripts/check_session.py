#!/usr/bin/env python3
"""Structural checker for a research session (light contracts only).

This validates STRUCTURE and PROVENANCE, not financial truth.
Every check reports PASS / FAIL / WARN / SKIPPED(reason). Exit code is
non-zero if any check FAILs (WARN does not fail the process).

Dispatch is packages.kd_research.check_catalog: --full runs session_full,
otherwise session_core (exclusive; never both).

Usage:
    python3 scripts/check_session.py --ticker JPM --date 2026-07-25 [--full]
    python3 scripts/check_session.py --session-dir archive/research/JPM/2026-07-25 [--full]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def write_session_acceptance(
    session: Path,
    ticker: str,
    session_date: str,
    rows: list[tuple[str, str, str]],
    out_path: Path | None = None,
) -> Path:
    """Write registry/session_acceptance.json from check rows."""
    checks = [
        {
            "id": check,
            "description": check,
            "status": status,
            "detail": detail or "",
        }
        for status, check, detail in rows
    ]
    n_fail = sum(1 for s, _, _ in rows if s == "FAIL")
    overall = "FAIL" if n_fail else "PASS"
    payload = {
        "ticker": ticker.upper(),
        "session_date": session_date,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall": overall,
        "checks": checks,
        "notes": (
            "Structural/provenance only — financial truth is owned by Phase 5 audit. "
            "Investment package readiness = overall PASS plus audit verdict PASS."
        ),
    }
    path = out_path or (session / "registry" / "session_acceptance.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date")
    ap.add_argument("--session-dir")
    ap.add_argument("--full", action="store_true", help="require all Phase 0-5 artifacts")
    ap.add_argument(
        "--write-acceptance",
        nargs="?",
        const="registry/session_acceptance.json",
        default=None,
        help=(
            "After checks, write session_acceptance.json (default path under session: "
            "registry/session_acceptance.json). Optional explicit relative/absolute path."
        ),
    )
    args = ap.parse_args()

    if args.session_dir:
        session = Path(args.session_dir).expanduser().resolve()
        ticker = session.parent.name
        session_date = session.name
    elif args.ticker and args.date:
        from packages.kd_research.paths import resolve_session

        resolved = resolve_session(args.ticker, args.date)
        if resolved is None:
            print(
                f"Session folder not found for {args.ticker.upper()} {args.date} "
                f"(checked archive/research/)"
            )
            return 2
        session = resolved
        ticker = args.ticker
        session_date = args.date
    else:
        ap.error("pass --session-dir or both --ticker and --date")

    if not session.exists():
        print(f"Session folder not found: {session}")
        return 2

    from packages.kd_research.check_catalog import (
        WHEN_SESSION_CORE,
        WHEN_SESSION_FULL,
        run_catalog,
    )

    when = WHEN_SESSION_FULL if args.full else WHEN_SESSION_CORE
    rows = run_catalog(session, when)

    n_fail = sum(1 for s, _, _ in rows if s == "FAIL")
    n_warn = sum(1 for s, _, _ in rows if s == "WARN")
    n_skip = sum(1 for s, _, _ in rows if s == "SKIPPED")
    for status, check, detail in rows:
        line = f"[{status:7s}] {check}"
        if detail:
            line += f" — {detail}"
        print(line)
    n_pass = len(rows) - n_fail - n_skip - n_warn
    print(f"\n{n_pass} passed, {n_fail} failed, {n_warn} warned, {n_skip} skipped")
    print(f"session: {session}")
    if n_warn:
        print("Note: WARN is signal for next runs / humans; exit code ignores WARN (FAIL only).")

    if args.write_acceptance is not None:
        out = Path(args.write_acceptance)
        if not out.is_absolute():
            out = session / out
        written = write_session_acceptance(session, ticker, session_date, rows, out_path=out)
        print(f"wrote acceptance: {written}")

    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
