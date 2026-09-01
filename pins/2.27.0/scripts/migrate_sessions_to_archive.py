#!/usr/bin/env python3
"""Move legacy root/<TICKER>/<DATE> sessions into archive/research/<TICKER>/<DATE>.

Usage:
    python3 scripts/migrate_sessions_to_archive.py --dry-run
    python3 scripts/migrate_sessions_to_archive.py --execute

Default is dry-run (no changes). Refuses to overwrite non-empty destinations.
Writes archive/catalog/migration_log.jsonl on execute.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from packages.kd_research.paths import (  # noqa: E402
    DATE_DIR_RE,
    PROJECT_ROOT,
    TICKER_BLOCKLIST,
    ensure_archive_tree,
    rel_to_project,
    research_root,
)


def discover_legacy_sessions(root: Path = PROJECT_ROOT) -> list[tuple[str, str, Path]]:
    found: list[tuple[str, str, Path]] = []
    for ticker_dir in sorted(root.iterdir()):
        if not ticker_dir.is_dir():
            continue
        name = ticker_dir.name
        if name in TICKER_BLOCKLIST or name.startswith("."):
            continue
        # Skip if this is somehow under archive already
        if "archive" in ticker_dir.parts:
            continue
        for date_dir in sorted(ticker_dir.iterdir()):
            if not date_dir.is_dir() or not DATE_DIR_RE.match(date_dir.name):
                continue
            if not ((date_dir / "registry").is_dir() or (date_dir / "reports").is_dir()):
                continue
            found.append((name.upper(), date_dir.name, date_dir))
    return found


def _dir_nonempty(path: Path) -> bool:
    return path.is_dir() and any(path.iterdir())


def migrate_one(
    ticker: str,
    session_date: str,
    src: Path,
    *,
    execute: bool,
    log_lines: list[dict],
) -> str:
    dest = research_root() / ticker / session_date
    entry = {
        "ticker": ticker,
        "session_date": session_date,
        "src": rel_to_project(src),
        "dest": rel_to_project(dest),
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if dest.exists() and _dir_nonempty(dest):
        # If already migrated (same content path used), skip
        entry["status"] = "skip_dest_exists"
        log_lines.append(entry)
        return f"SKIP dest exists: {dest}"
    if execute:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and not _dir_nonempty(dest):
            dest.rmdir()
        shutil.move(str(src), str(dest))
        # Remove empty ticker parent
        parent = src.parent
        try:
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            pass
        # Ensure meta/
        (dest / "meta").mkdir(exist_ok=True)
        entry["status"] = "moved"
        log_lines.append(entry)
        return f"MOVED {src} -> {dest}"
    entry["status"] = "dry_run_would_move"
    log_lines.append(entry)
    return f"DRY-RUN would move {src} -> {dest}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", default=True, help="Print plan only (default)")
    ap.add_argument("--execute", action="store_true", help="Actually move files")
    args = ap.parse_args()
    execute = bool(args.execute)
    if execute:
        # --execute wins over default dry-run
        pass

    ensure_archive_tree()
    sessions = discover_legacy_sessions()
    if not sessions:
        print("No legacy sessions found at repo root.")
        return 0

    log_lines: list[dict] = []
    print(f"Found {len(sessions)} legacy session(s). execute={execute}")
    for ticker, date, src in sessions:
        print(migrate_one(ticker, date, src, execute=execute, log_lines=log_lines))

    log_path = PROJECT_ROOT / "archive" / "catalog" / "migration_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if execute:
        with log_path.open("a", encoding="utf-8") as f:
            for line in log_lines:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        print(f"Appended {len(log_lines)} line(s) to {log_path}")
    else:
        print("Dry-run only. Re-run with --execute to move.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
