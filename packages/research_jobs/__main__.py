"""CLI: python -m packages.research_jobs start|get|list|cancel|discard|resume|reconcile"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from packages.catalog_api.client import default_archive_root
from packages.research_jobs.jobs import (
    AnalyzeBusy,
    AnalyzeDiscardRefused,
    AnalyzeError,
    AnalyzeGrokMissing,
    AnalyzeNotFound,
    AnalyzeResumeConflict,
    AnalyzeRunbookMissing,
    AnalyzeTickerError,
    AnalyzeValidationError,
    cancel_analyze,
    discard_analyze,
    get_analyze,
    list_analyzes,
    reconcile_analyze_jobs,
    resume_analyze,
    start_analyze,
)


def _archive() -> Path:
    return default_archive_root()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="packages.research_jobs")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start")
    p_start.add_argument("--ticker", required=True)
    p_start.add_argument("--date")
    p_start.add_argument("--slug")
    p_start.add_argument("--model", default="grok-4.5")
    p_start.add_argument("--subagent-model")
    p_start.add_argument("--notes")

    p_get = sub.add_parser("get")
    p_get.add_argument("analyze_id")

    p_list = sub.add_parser("list")
    p_list.add_argument("--ticker")

    p_cancel = sub.add_parser("cancel")
    p_cancel.add_argument("analyze_id")

    p_discard = sub.add_parser("discard")
    p_discard.add_argument("analyze_id")

    p_resume = sub.add_parser("resume")
    p_resume.add_argument("analyze_id")

    sub.add_parser("reconcile")

    args = ap.parse_args(argv)
    root = _archive()
    try:
        if args.cmd == "start":
            job = start_analyze(
                root,
                args.ticker,
                session_date=args.date,
                slug=args.slug,
                orchestrator_model=args.model,
                subagent_model=args.subagent_model,
                notes=args.notes,
            )
            print(json.dumps(job, indent=2, default=str))
            return 0
        if args.cmd == "get":
            print(json.dumps(get_analyze(root, args.analyze_id), indent=2, default=str))
            return 0
        if args.cmd == "list":
            print(json.dumps(list_analyzes(root, ticker=args.ticker), indent=2, default=str))
            return 0
        if args.cmd == "cancel":
            print(json.dumps(cancel_analyze(root, args.analyze_id), indent=2, default=str))
            return 0
        if args.cmd == "discard":
            print(json.dumps(discard_analyze(root, args.analyze_id), indent=2, default=str))
            return 0
        if args.cmd == "resume":
            print(json.dumps(resume_analyze(root, args.analyze_id), indent=2, default=str))
            return 0
        if args.cmd == "reconcile":
            print(json.dumps(reconcile_analyze_jobs(root), indent=2, default=str))
            return 0
    except AnalyzeTickerError as e:
        print(json.dumps({"status": e.status, "reason": e.reason}))
        return 2
    except AnalyzeValidationError as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 2
    except AnalyzeBusy as e:
        print(f"busy: {e}", file=sys.stderr)
        return 4
    except AnalyzeGrokMissing as e:
        print(f"grok missing: {e}", file=sys.stderr)
        return 3
    except AnalyzeRunbookMissing as e:
        print(f"runbook: {e}", file=sys.stderr)
        return 3
    except AnalyzeDiscardRefused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 6
    except AnalyzeResumeConflict as e:
        print(f"conflict: {e}", file=sys.stderr)
        return 6
    except AnalyzeNotFound as e:
        print(f"not found: {e}", file=sys.stderr)
        return 5
    except AnalyzeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
