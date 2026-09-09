"""Copy an IB activity CSV into .local and merge it into the portfolio sqlite book.

Usage:
    python -m apps.analysis_web.import_ib
    python -m apps.analysis_web.import_ib --src path/to/U*.csv
    python -m apps.analysis_web.import_ib --rebuild
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.analysis_web.services.ib_statement import parse_activity_csv
from apps.analysis_web.services.portfolio_store import StoreError, db_path, ingest_statement


def statements_dir() -> Path:
    from apps.analysis_web.config import local_dir

    return local_dir() / "ib" / "statements"


def find_default_csv(*, now: datetime | None = None) -> Path:
    """Newest U*.csv in Downloads (last 24h), else newest under .local/ib/statements."""
    clock = now or datetime.now()
    cutoff = clock - timedelta(hours=24)
    downloads = Path.home() / "Downloads"
    recent: list[Path] = []
    if downloads.is_dir():
        for p in downloads.glob("U*.csv"):
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime)
            except OSError:
                continue
            if mtime >= cutoff:
                recent.append(p)
    if recent:
        return max(recent, key=lambda p: p.stat().st_mtime)
    local = statements_dir()
    if local.is_dir():
        local_csvs = list(local.glob("U*.csv"))
        if local_csvs:
            return max(local_csvs, key=lambda p: p.stat().st_mtime)
    raise FileNotFoundError(
        f"No U*.csv in Downloads (last 24h) or {statements_dir()}/"
    )


def copy_into_local(src: Path) -> Path:
    dest_dir = statements_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    src_res = src.resolve()
    dest_res = dest.resolve()
    if src_res != dest_res:
        shutil.copy2(src, dest)
    pdf = src.with_suffix(".pdf")
    if pdf.is_file():
        pdf_dest = dest_dir / pdf.name
        if pdf.resolve() != pdf_dest.resolve():
            shutil.copy2(pdf, pdf_dest)
    return dest


def stock_value_base_sum(stmt) -> tuple[float, int]:
    total = 0.0
    missing = 0
    for p in stmt.positions:
        if (p.asset_category or "").lower() != "stocks":
            continue
        vb = stmt.value_base(p.value, p.currency)
        if vb is None:
            missing += 1
            continue
        total += vb
    return total, missing


def _checksum_warning(stmt) -> str | None:
    stock_sum, missing = stock_value_base_sum(stmt)
    nav_stock = stmt.nav_asset("Stock")
    checksum = nav_stock.current_total if nav_stock is not None else None
    if checksum is None or missing:
        return None
    denom = max(abs(checksum), abs(stock_sum), 1.0)
    if abs(stock_sum - checksum) / denom > 0.005 and abs(stock_sum - checksum) > 1.0:
        return (
            f"stock value_base sum {stock_sum:.2f} disagrees with NAV Stock "
            f"{checksum:.2f} (sleeve totals are checksum only)"
        )
    return None


def _result(src: Path, dest: Path, stmt, ing) -> dict:
    return {
        "src": str(src),
        "imported": str(dest),
        "account_id": stmt.account_id,
        "period_from": stmt.period_from,
        "period_to": stmt.period_to,
        "trades_inserted": ing.inserted,
        "trades_skipped": ing.skipped,
        "trades_conflicts": ing.conflicts,
        "positions": len(stmt.positions),
        "json_rewritten": False,
        "checksum_warning": _checksum_warning(stmt),
    }


def import_statement(src: Path, *, db: Path | None = None) -> dict:
    dest = copy_into_local(src)
    stmt = parse_activity_csv(dest)
    ing = ingest_statement(stmt, path=db)
    return _result(src, dest, stmt, ing)


def rebuild_book(*, db: Path | None = None) -> list[dict]:
    """Wipe sqlite and replay every archived U*.csv. The only supported start-over."""
    csvs = sorted(statements_dir().glob("U*.csv"))
    if not csvs:
        raise FileNotFoundError(
            f"No U*.csv in {statements_dir()}/ to rebuild from"
        )
    target = db or db_path()
    if target.is_file():
        target.unlink()
    out: list[dict] = []
    for csv_path in csvs:
        stmt = parse_activity_csv(csv_path)
        ing = ingest_statement(stmt, path=target)
        out.append(_result(csv_path, csv_path, stmt, ing))
    return out


def _print_result(result: dict) -> None:
    print(f"imported {result['imported']}")
    print(f"account {result['account_id']} {result['period_from']}..{result['period_to']}")
    print(
        f"trades_inserted={result['trades_inserted']} "
        f"trades_skipped={result['trades_skipped']} "
        f"trades_conflicts={result['trades_conflicts']}"
    )
    print(f"positions={result['positions']}")
    if result["checksum_warning"]:
        print(f"WARNING: {result['checksum_warning']}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=None, help="Activity statement CSV")
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete sqlite and replay every U*.csv under .local/ib/statements/",
    )
    args = ap.parse_args(argv)
    try:
        if args.rebuild:
            if args.src:
                src = Path(args.src)
                if not src.is_file():
                    raise FileNotFoundError(str(src))
                copy_into_local(src)
            results = rebuild_book()
            for result in results:
                _print_result(result)
            return 0
        src = Path(args.src) if args.src else find_default_csv()
        if not src.is_file():
            raise FileNotFoundError(str(src))
        result = import_statement(src)
        _print_result(result)
    except (OSError, ValueError, FileNotFoundError, StoreError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
