#!/usr/bin/env python3
"""Copy slim session trees from live archive into eng/fixtures/archive.

Does not refresh prediction snapshots on the live archive.
Re-exports a tiny sqlite from the fixture research tree when possible.

Usage:
    python3 scripts/sync_eng_fixtures.py --tickers META,JPM --dates 2026-08-03,2026-07-25
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Skip bulky trees when copying
SKIP_DIR_NAMES = frozenset({"raw_sec", "transcripts", "__pycache__"})


def _copy_session(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    def ignore(directory: str, names: list[str]) -> set[str]:
        skipped = set()
        for n in names:
            p = Path(directory) / n
            if p.is_dir() and n in SKIP_DIR_NAMES:
                skipped.add(n)
        return skipped

    shutil.copytree(src, dst, ignore=ignore)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tickers", required=True, help="Comma-separated tickers")
    ap.add_argument("--dates", required=True, help="Comma-separated session keys/dates")
    ap.add_argument(
        "--dest",
        type=Path,
        default=PROJECT_ROOT / "eng" / "fixtures" / "archive",
        help="Fixture ARCHIVE_ROOT destination",
    )
    args = ap.parse_args(argv)

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    if len(tickers) != len(dates):
        # Allow all-pairs if counts differ? Prefer zip with explicit pairs.
        # Support equal length zip OR single date for all tickers.
        if len(dates) == 1:
            pairs = [(t, dates[0]) for t in tickers]
        elif len(tickers) == 1:
            pairs = [(tickers[0], d) for d in dates]
        else:
            print("ERROR: pass equal-length tickers/dates or one date for all", file=sys.stderr)
            return 1
    else:
        pairs = list(zip(tickers, dates))

    dest_root: Path = args.dest
    src_root = PROJECT_ROOT / "archive" / "research"
    copied = 0
    for ticker, key in pairs:
        src = src_root / ticker / key
        if not src.is_dir():
            print(f"SKIP missing: {src}")
            continue
        dst = dest_root / "research" / ticker / key
        print(f"Copy {src} -> {dst}")
        _copy_session(src, dst)
        copied += 1

    if copied == 0:
        print("ERROR: no sessions copied", file=sys.stderr)
        return 1

    # Best-effort fixture catalog export without refreshing live snapshots
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from scripts.export_compare_db import export_session  # type: ignore
    except Exception:
        export_session = None

    if export_session is not None:
        # export_compare_db uses project paths; for fixtures we may only copy sqlite later
        print("NOTE: re-export of fixture sqlite may require export_compare_db --session-dir")
    else:
        print("NOTE: copy complete; run export manually if needed for fixture sqlite")

    # Copy live sqlite as optional bootstrap if fixture db missing (paths still resolve via run_id)
    live_db = PROJECT_ROOT / "archive" / "catalog" / "research_compare.sqlite"
    dest_cat = dest_root / "catalog"
    dest_cat.mkdir(parents=True, exist_ok=True)
    if live_db.is_file():
        # Do not copy full prod DB by default (may list runs without local trees).
        # Instead leave a marker; tests use synthetic mini archives.
        (dest_cat / "README.md").write_text(
            "Fixture catalog: prefer synthetic sqlite from tests or "
            "`export_compare_db --session-dir eng/fixtures/archive/research/...` "
            "with output_dir pointing at eng/fixtures.\n"
        )
    print(f"Done. copied={copied} dest={dest_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
