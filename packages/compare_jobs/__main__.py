"""CLI: python -m packages.compare_jobs start|get|list|cancel"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from packages.catalog_api.client import default_archive_root
from packages.compare_jobs.jobs import (
    CompareBusy,
    CompareError,
    CompareNotFound,
    CompareValidationError,
    GrokMissing,
    cancel_compare,
    get_compare,
    list_compares,
    start_compare,
)


def _archive() -> Path:
    raw = os.environ.get("ARCHIVE_ROOT")
    return Path(raw).expanduser().resolve() if raw else default_archive_root()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="packages.compare_jobs")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start")
    p_start.add_argument("--run-a", required=True)
    p_start.add_argument("--run-b", required=True)
    p_start.add_argument("--force", action="store_true")

    p_get = sub.add_parser("get")
    p_get.add_argument("compare_id")

    p_list = sub.add_parser("list")
    p_list.add_argument("--ticker")

    p_cancel = sub.add_parser("cancel")
    p_cancel.add_argument("compare_id")

    args = ap.parse_args(argv)
    root = _archive()
    try:
        if args.cmd == "start":
            job = start_compare(root, args.run_a, args.run_b, force=bool(args.force))
            print(json.dumps(job, indent=2, default=str))
            return 0
        if args.cmd == "get":
            print(json.dumps(get_compare(root, args.compare_id), indent=2, default=str))
            return 0
        if args.cmd == "list":
            print(json.dumps(list_compares(root, ticker=args.ticker), indent=2, default=str))
            return 0
        if args.cmd == "cancel":
            print(json.dumps(cancel_compare(root, args.compare_id), indent=2, default=str))
            return 0
    except CompareValidationError as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 2
    except CompareBusy as e:
        print(f"busy: {e}", file=sys.stderr)
        return 4
    except GrokMissing as e:
        print(f"grok missing: {e}", file=sys.stderr)
        return 3
    except CompareNotFound as e:
        print(f"not found: {e}", file=sys.stderr)
        return 5
    except CompareError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
