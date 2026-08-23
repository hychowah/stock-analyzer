#!/usr/bin/env python3
"""Ingest primary documents into archive/library/<TICKER>/.

Usage:
    python scripts/ingest_library.py --ticker META
    python scripts/ingest_library.py --ticker META --label "foo.pdf:annual:FY2025:2026-01-29"
    python scripts/ingest_library.py --ticker META --from-file path/to/10k.txt --kind annual --period FY2025
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.kd_research.library import (  # noqa: E402
    LibraryError,
    apply_label,
    ingest_file,
    ingest_inbox,
    load_manifest,
    ticker_library,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest files into the ticker document library")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--output-dir", default=None, help="Project root or archive/")
    ap.add_argument(
        "--label",
        action="append",
        default=[],
        help='filename:kind:period[:filing_date]  e.g. "x.pdf:annual:FY2025:2026-01-29"',
    )
    ap.add_argument("--from-file", dest="from_file", default=None)
    ap.add_argument("--kind", default=None)
    ap.add_argument("--period", default=None)
    ap.add_argument("--filing-date", default=None)
    ap.add_argument("--from", dest="ingested_from", default="typed_folder")
    args = ap.parse_args(argv)

    ticker = args.ticker.strip().upper()
    results: list[dict] = []
    try:
        if args.from_file:
            results.append(
                ingest_file(
                    ticker,
                    Path(args.from_file),
                    output_dir=args.output_dir,
                    kind=args.kind,
                    fiscal_period=args.period,
                    filing_date=args.filing_date,
                    ingested_from=args.ingested_from,
                )
            )
        else:
            results.extend(ingest_inbox(ticker, output_dir=args.output_dir))
        for spec in args.label:
            parts = spec.split(":")
            if len(parts) < 3:
                raise LibraryError(f"bad --label {spec!r}; want file:kind:period[:date]")
            fname, kind, period = parts[0], parts[1], parts[2]
            date = parts[3] if len(parts) > 3 else None
            apply_label(
                ticker, fname, kind, period, filing_date=date, output_dir=args.output_dir
            )
            results.append({"status": "labeled", "file": fname, "kind": kind, "period": period})
    except LibraryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"ticker": ticker, "results": results}, indent=2, ensure_ascii=False))
    lib = ticker_library(ticker, args.output_dir)
    man = load_manifest(lib)
    unlabeled = [
        d.get("files", {}).get("original")
        for d in man.get("documents") or []
        if isinstance(d, dict) and d.get("needs_label")
    ]
    if unlabeled:
        print(f"needs_label ({len(unlabeled)}): {unlabeled}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
