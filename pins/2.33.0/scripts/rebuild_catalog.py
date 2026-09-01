#!/usr/bin/env python3
"""Rebuild archive/catalog/runs_index.json and tickers_index.json from disk.

Usage:
    python3 scripts/rebuild_catalog.py
    python3 scripts/rebuild_catalog.py --from-sqlite
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.kd_research.catalog_rebuild import (  # noqa: E402
    rebuild,
    rebuild_from_sqlite,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--from-sqlite",
        action="store_true",
        help="Rebuild thin JSON indexes from research_compare.sqlite (no disk walk)",
    )
    args = ap.parse_args()
    result = rebuild_from_sqlite() if args.from_sqlite else rebuild()
    print(
        f"Catalog rebuilt ({result.get('mode')}): {result['n_runs']} runs, "
        f"{result['n_tickers']} tickers -> {result['catalog']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
