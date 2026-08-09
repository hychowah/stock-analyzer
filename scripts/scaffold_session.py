#!/usr/bin/env python3
"""Create the session folder structure for a research session.

Usage:
    python scripts/scaffold_session.py --ticker JPM --date 2026-07-25

Creates archive/research/<TICKER>/<DATE>/{reports,data/...,charts,registry,meta},
writes registry/phase_status.json (resume skeleton), and refuses to overwrite an
existing non-empty session folder.

Legacy path (root/<TICKER>/<DATE>) is only used with --legacy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.kd_research.paths import (  # noqa: E402
    ensure_archive_tree,
    session_root,
)
from scripts.kd_research.phase_status import write_phase_status_skeleton  # noqa: E402

SUBDIRS = [
    "reports",
    "data/compute",
    "data/raw_sec",
    "data/transcripts",
    "charts",
    "registry/handoffs",
    "registry/raw",
    "meta",
]


def scaffold(
    ticker: str,
    session_date: str,
    output_dir: str | None = None,
    force: bool = False,
    *,
    legacy: bool = False,
) -> Path:
    if not legacy:
        ensure_archive_tree(output_dir)
    prefer = "legacy" if legacy else "archive"
    root = session_root(ticker, session_date, output_dir, prefer=prefer)
    if root.exists() and any(root.iterdir()) and not force:
        raise SystemExit(
            f"Refusing to overwrite existing session folder: {root}\n"
            "Use a new date, or pass --force if you really mean it."
        )
    for sub in SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    write_phase_status_skeleton(root, ticker, session_date)
    return root


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--date", required=True, help="Session date, YYYY-MM-DD")
    ap.add_argument(
        "--output-dir",
        default=None,
        help="Project root override (default: workspace root). "
        "Sessions are written under <root>/archive/research/ unless --legacy.",
    )
    ap.add_argument(
        "--legacy",
        action="store_true",
        help="Write to root/<TICKER>/<DATE> instead of archive/research/ (tests/compat).",
    )
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    root = scaffold(args.ticker, args.date, args.output_dir, args.force, legacy=args.legacy)
    print(f"Session scaffolded: {root}")
    for sub in SUBDIRS:
        print(f"  {root / sub}/")
    print(f"  {root / 'registry' / 'phase_status.json'}")


if __name__ == "__main__":
    main()
