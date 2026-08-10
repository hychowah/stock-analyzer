#!/usr/bin/env python3
"""Fetch realized price marks for finished research runs (outcomes layer).

Writes archive/outcomes/<TICKER>/<SESSION_KEY>/price_path.json (+ mechanical scorecard)
and upserts into archive/catalog/research_compare.sqlite outcomes table.

Does NOT edit archive/research/ sessions.

Usage:
    python3 scripts/fetch_outcome_marks.py --ticker META --date 2026-08-03
    python3 scripts/fetch_outcome_marks.py --all --horizons 1d,1w,1m
    python3 scripts/fetch_outcome_marks.py --all --dry-run

Prefers yfinance-market-mcp/.venv/bin/python when available for yfinance.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.kd_research.compare_db import open_db  # noqa: E402
from scripts.kd_research.outcomes import (  # noqa: E402
    DEFAULT_HORIZONS,
    HORIZON_DAYS,
    mechanical_scorecard,
    outcomes_dir_for,
    pct_return,
    research_snapshot_fields,
    session_identity,
    target_date_for,
    upsert_outcomes_rows,
    utc_now,
    write_json,
)
from scripts.kd_research.paths import (  # noqa: E402
    iter_research_sessions,
    resolve_session,
)


# Session ticker → yfinance symbol when they differ.
YAHOO_SYMBOL_MAP = {
    "ADYEN": "ADYEN.AS",
    "02618.HK": "2618.HK",
    "MC.PA": "MC.PA",
}


def yahoo_symbol(ticker: str) -> str:
    t = ticker.upper()
    if t in YAHOO_SYMBOL_MAP:
        return YAHOO_SYMBOL_MAP[t]
    # HKEX sessions sometimes zero-pad (02618.HK → 2618.HK)
    if t.endswith(".HK") and t[0] == "0":
        return t.lstrip("0") if t.lstrip("0") else t
    return t


def _import_yfinance():
    try:
        import yfinance as yf  # type: ignore

        return yf
    except ImportError as e:
        raise SystemExit(
            "yfinance not installed. Use: yfinance-market-mcp/.venv/bin/python "
            "scripts/fetch_outcome_marks.py ..."
        ) from e


def _close_on_or_after(hist, target: date) -> tuple[date | None, float | None]:
    """hist: DataFrame indexed by date with Close column."""
    if hist is None or getattr(hist, "empty", True):
        return None, None
    # Normalize index to dates
    for idx, row in hist.iterrows():
        try:
            d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
        except Exception:  # noqa: BLE001
            continue
        if d < target:
            continue
        close = row.get("Close") if hasattr(row, "get") else row["Close"]
        try:
            return d, float(close)
        except (TypeError, ValueError):
            continue
    return None, None


def fetch_price_series(ticker: str, start: date, end: date):
    yf = _import_yfinance()
    # yfinance end is exclusive-ish; pad one day
    end_excl = end + timedelta(days=2)
    sym = yahoo_symbol(ticker)
    t = yf.Ticker(sym)
    hist = t.history(start=start.isoformat(), end=end_excl.isoformat(), auto_adjust=True)
    return hist


def _default_benchmark(region: str | None, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    r = (region or "").lower()
    if r in ("", "us"):
        return "SPY"
    if r == "hk_china":
        return "2800.HK"  # Tracker Fund / broad HK proxy often available; may fail
    if r == "japan":
        return "^N225"
    if r == "eu_uk":
        return "SX5E.DE"
    if r == "korea":
        return "^KS11"
    return "SPY"


def build_marks_for_session(
    session: Path,
    *,
    horizons: list[str],
    asof_today: date | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    ticker, session_key, session_date, rid = session_identity(session)
    fields = research_snapshot_fields(session)
    today = asof_today or date.today()
    gaps: list[str] = []

    asof = fields.get("asof_price")
    if asof is None:
        gaps.append("asof_price missing; cannot compute returns")

    bench_sym = _default_benchmark(fields.get("region"), fields.get("benchmark"))
    # Fetch a single window covering all horizon targets that are due
    due_targets: list[date] = []
    for h in horizons:
        td = target_date_for(session_date, h)
        if td <= today:
            due_targets.append(td)
    marks: list[dict[str, Any]] = []
    hist = None
    bench_hist = None
    if due_targets and not dry_run:
        start = min(due_targets) - timedelta(days=5)
        end = max(due_targets) + timedelta(days=10)
        try:
            hist = fetch_price_series(ticker, start, end)
        except Exception as e:  # noqa: BLE001
            gaps.append(f"yfinance history failed for {ticker}: {e}")
            hist = None
        if bench_sym:
            try:
                bench_hist = fetch_price_series(bench_sym, start, end)
            except Exception as e:  # noqa: BLE001
                gaps.append(f"benchmark {bench_sym} failed: {e}")
                bench_hist = None

    # Need asof-date close for benchmark return baseline — use session asof_price for stock
    session_d = date.fromisoformat(session_date)
    for h in horizons:
        td = target_date_for(session_date, h)
        mark: dict[str, Any] = {
            "horizon": h,
            "target_date": td.isoformat(),
            "mark_date": None,
            "price": None,
            "total_return_pct": None,
            "benchmark_return_pct": None,
            "excess_return_pct": None,
            "status": "pending",
            "source": "yfinance",
            "fetched_at": None,
            "notes": "",
        }
        if td > today:
            mark["status"] = "pending"
            mark["notes"] = f"target {td} is in the future relative to {today}"
            marks.append(mark)
            continue
        if dry_run:
            mark["status"] = "pending"
            mark["notes"] = "dry_run"
            marks.append(mark)
            continue
        if hist is None:
            mark["status"] = "error"
            mark["notes"] = "no price history"
            marks.append(mark)
            continue
        md, px = _close_on_or_after(hist, td)
        if md is None or px is None:
            mark["status"] = "unavailable"
            mark["notes"] = f"no trading bar on/after {td}"
            marks.append(mark)
            continue
        mark["mark_date"] = md.isoformat()
        mark["price"] = round(px, 6)
        mark["total_return_pct"] = pct_return(asof, px)
        if bench_hist is not None and asof is not None:
            # benchmark return: close on/after session_date → close on/after mark
            b0d, b0 = _close_on_or_after(bench_hist, session_d)
            b1d, b1 = _close_on_or_after(bench_hist, td)
            br = pct_return(b0, b1)
            mark["benchmark_return_pct"] = br
            if br is not None and mark["total_return_pct"] is not None:
                mark["excess_return_pct"] = round(mark["total_return_pct"] - br, 4)
            mark["notes"] = f"benchmark={bench_sym} b0={b0d} b1={b1d}"
        mark["status"] = "ok"
        mark["fetched_at"] = utc_now()
        marks.append(mark)

    price_path = {
        "schema_version": 1,
        "run_id": rid,
        "ticker": ticker,
        "session_date": session_date,
        "session_key": session_key,
        "asof_price": asof,
        "currency": fields.get("currency") or "",
        "benchmark": bench_sym,
        "built_at": utc_now(),
        "marks": marks,
        "compute_script": "scripts/fetch_outcome_marks.py",
        "gaps": gaps,
        "research_path": str(session),
    }
    return {
        "price_path": price_path,
        "fields": fields,
        "ticker": ticker,
        "session_key": session_key,
        "session_date": session_date,
        "run_id": rid,
    }


def process_session(
    session: Path,
    *,
    horizons: list[str],
    write_db: bool,
    dry_run: bool,
    asof_today: date | None,
) -> dict[str, Any]:
    built = build_marks_for_session(
        session, horizons=horizons, asof_today=asof_today, dry_run=dry_run
    )
    price_path = built["price_path"]
    fields = built["fields"]
    scorecard = mechanical_scorecard(
        run_id=built["run_id"],
        ticker=built["ticker"],
        session_date=built["session_date"],
        session_key=built["session_key"],
        fields=fields,
        price_path=price_path,
    )

    out_dir = outcomes_dir_for(built["ticker"], built["session_key"])
    if not dry_run:
        write_json(out_dir / "price_path.json", price_path)
        write_json(out_dir / "scorecard.json", scorecard)
        notes = out_dir / "notes.md"
        if not notes.is_file():
            notes.write_text(
                f"# Outcomes notes — {built['run_id']}\n\n"
                f"Mechanical scorecard generated {scorecard.get('graded_at')}.\n"
                f"Overall: {scorecard.get('overall_label')}\n",
                encoding="utf-8",
            )

        if write_db:
            conn = open_db(rebuild=False)
            # Ensure run row exists (FK); if missing, skip DB with gap
            row = conn.execute(
                "SELECT run_id FROM runs WHERE run_id = ?", (built["run_id"],)
            ).fetchone()
            if row is None:
                price_path.setdefault("gaps", []).append(
                    "run not in research_compare.sqlite; run export_compare_db first"
                )
                write_json(out_dir / "price_path.json", price_path)
            else:
                upsert_outcomes_rows(conn, built["run_id"], price_path, scorecard)
                conn.commit()
            conn.close()

    ok = sum(1 for m in price_path["marks"] if m.get("status") == "ok")
    pending = sum(1 for m in price_path["marks"] if m.get("status") == "pending")
    return {
        "run_id": built["run_id"],
        "path": str(out_dir),
        "ok_marks": ok,
        "pending_marks": pending,
        "overall": scorecard.get("overall_label"),
        "dry_run": dry_run,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker")
    ap.add_argument("--date", help="Session date or session_key")
    ap.add_argument("--session-dir")
    ap.add_argument("--all", action="store_true")
    ap.add_argument(
        "--horizons",
        default=",".join(DEFAULT_HORIZONS),
        help="Comma-separated horizons (default: all)",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-db", action="store_true", help="Write files only, skip SQLite")
    ap.add_argument(
        "--asof-today",
        default=None,
        help="Override 'today' YYYY-MM-DD (testing / hermetic)",
    )
    ap.add_argument("--archive-only", action="store_true")
    args = ap.parse_args()

    horizons = [h.strip() for h in args.horizons.split(",") if h.strip()]
    for h in horizons:
        if h not in HORIZON_DAYS:
            ap.error(f"unknown horizon {h}")

    asof_today = date.fromisoformat(args.asof_today) if args.asof_today else None

    sessions: list[Path] = []
    if args.all:
        for _t, _k, p in iter_research_sessions(include_legacy=not args.archive_only):
            sessions.append(p)
    elif args.session_dir:
        sessions.append(Path(args.session_dir))
    elif args.ticker and args.date:
        p = resolve_session(args.ticker, args.date)
        if p is None:
            print(f"Session not found: {args.ticker} {args.date}", file=sys.stderr)
            return 2
        sessions.append(p)
    else:
        ap.error("pass --all, --session-dir, or --ticker and --date")

    results = []
    for s in sessions:
        try:
            results.append(
                process_session(
                    s,
                    horizons=horizons,
                    write_db=not args.no_db and not args.dry_run,
                    dry_run=args.dry_run,
                    asof_today=asof_today,
                )
            )
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {s}: {e}", file=sys.stderr)
            raise

    for r in results:
        print(
            f"OK {r['run_id']} marks_ok={r['ok_marks']} pending={r['pending_marks']} "
            f"overall={r['overall']} -> {r['path']}"
        )
    print(f"Processed {len(results)} session(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
