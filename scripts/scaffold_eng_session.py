#!/usr/bin/env python3
"""Scaffold a Mode B (product eng) work session under eng/sessions/.

Usage:
    python3 scripts/scaffold_eng_session.py --slug catalog-api-mvp
    python3 scripts/scaffold_eng_session.py --slug ui-mvp --date 2026-08-10 --work-type W4

This is NOT research scaffold — does not create archive/research sessions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scaffold(
    slug: str,
    *,
    session_date: str | None = None,
    work_type: str = "W2",
    goal: str = "",
    project_root: Path | None = None,
) -> Path:
    if not SLUG_RE.match(slug):
        raise ValueError(f"slug must match {SLUG_RE.pattern}, got {slug!r}")
    root = project_root or PROJECT_ROOT
    day = session_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    session_key = f"{day}-{slug}"
    session_dir = root / "eng" / "sessions" / session_key
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(f"Non-empty eng session already exists: {session_dir}")

    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "handoffs").mkdir(exist_ok=True)

    now = _utc_now()
    issue: dict[str, Any] = {
        "goal": goal or f"Eng work: {slug}",
        "non_goals": [
            "Do not run research Phases 0–5",
            "Do not mutate archive/research or archive/outcomes history",
        ],
        "work_type": work_type,
        "success_criteria": [
            "eng_verify.py passes",
            "Feature list items verified before passes=true",
        ],
        "write_allowlist": [
            "eng/",
            "packages/",
            "apps/",
            "programs/",
            "scripts/",
            "archive/library/",
        ],
        "write_denylist": [
            "archive/research/**",
            "archive/outcomes/**",
        ],
        "verify_commands": [
            "python3 scripts/eng_verify.py",
        ],
    }
    features = {
        "features": [
            {
                "id": "orient",
                "description": "Read eng/AGENTS.md + fill issue.json success criteria",
                "passes": False,
                "verify": "issue.json has non-empty success_criteria",
            },
            {
                "id": "implement",
                "description": "Implement the primary change for this slug",
                "passes": False,
                "verify": "python3 scripts/eng_verify.py",
            },
            {
                "id": "verify",
                "description": "Verifier marks features after real checks",
                "passes": False,
                "verify": "ship_note.json present when complete",
            },
        ]
    }
    status = {
        "slug": slug,
        "session_key": session_key,
        "status": "scaffolded",
        "created_at": now,
        "updated_at": now,
        "work_type": work_type,
        "resume_hint": "Read issue.json and implement the first feature with passes=false.",
    }
    progress = (
        f"# Eng session {session_key}\n\n"
        f"- Created: {now}\n"
        f"- Work type: {work_type}\n"
        f"- Goal: {issue['goal']}\n\n"
        "## Log\n\n"
        f"- {now} scaffolded\n"
    )

    (session_dir / "issue.json").write_text(json.dumps(issue, indent=2) + "\n")
    (session_dir / "feature_list.json").write_text(json.dumps(features, indent=2) + "\n")
    (session_dir / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    (session_dir / "progress.md").write_text(progress)
    return session_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", required=True, help="Short work slug (no spaces)")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: UTC today)")
    ap.add_argument(
        "--work-type",
        default="W2",
        choices=["W1", "W2", "W3", "W4", "W5"],
        help="Primary work type",
    )
    ap.add_argument("--goal", default="", help="One-line goal")
    args = ap.parse_args(argv)
    try:
        path = scaffold(
            args.slug,
            session_date=args.date,
            work_type=args.work_type,
            goal=args.goal,
        )
    except (ValueError, FileExistsError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"Scaffolded eng session: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
