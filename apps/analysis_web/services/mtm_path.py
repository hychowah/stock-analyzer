"""Reconstructed period MTM for the live IB book.

Walks ``as_of_book`` and marks with Yahoo daily closes. Display math, not
a valuation and not the IB statement MTM file. Does not import what-if.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from apps.analysis_web.services.book_state import as_of_book, trade_date
from apps.analysis_web.services.ib_statement import IbBook, IbStatement
from apps.analysis_web.services.mark_book import AsOfMark, MarkedLot, MarkedNav, mark_lots, marks_on
from apps.analysis_web.services.price_history import (
    HistoryService,
    PriceHistory,
    range_for_span,
)
from apps.analysis_web.services.signed_bars import signed_bar_rows


PERIODS = frozenset({"1w", "1m", "ytd", "statement"})
_QTY_EPS = 1e-9


class PeriodError(ValueError):
    """Unknown or unusable period token."""


def utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def resolve_period(
    period: str,
    stmt: IbStatement,
    *,
    today: str | None = None,
) -> tuple[str, str]:
    """Inclusive calendar window. Live is not a period of this resource."""
    p = (period or "").strip().lower()
    if p not in PERIODS:
        raise PeriodError("period must be one of 1w, 1m, ytd, statement")
    start_stmt = (stmt.period_from or "").strip()[:10]
    end_stmt = (stmt.period_to or "").strip()[:10]
    if p == "statement":
        if len(start_stmt) < 10 or len(end_stmt) < 10:
            raise PeriodError("statement period is missing")
        return start_stmt, end_stmt
    day = (today or utc_today()).strip()[:10]
    if len(day) < 10:
        raise PeriodError("today is missing")
    end = day
    if p == "1w":
        start = (date.fromisoformat(day) - timedelta(days=7)).isoformat()
    elif p == "1m":
        start = (date.fromisoformat(day) - timedelta(days=30)).isoformat()
    else:
        start = f"{day[:4]}-01-01"
    return start, end


def window_listings(ib_book: IbBook, start: str, end: str) -> list[str]:
    """Listings that can appear on the walk (start, end, and in-window fills)."""
    days = {start[:10], end[:10]}
    for trade in ib_book.trades or ():
        day = trade_date(trade.traded_at)
        if day and start[:10] <= day <= end[:10]:
            days.add(day)
    seen: list[str] = []
    have: set[str] = set()
    for day in sorted(days):
        book = as_of_book(ib_book, day)
        for lot in book.lots:
            key = (lot.listing or "").strip().upper()
            if key and key not in have:
                have.add(key)
                seen.append(key)
    return seen


def _held(row: MarkedLot | None) -> bool:
    if row is None:
        return False
    qty = row.qty
    return qty is not None and abs(float(qty)) > _QTY_EPS


def _side_value(row: MarkedLot | None, *, held: bool) -> float | None:
    """0 if not held; None if held but unquoted; else mark."""
    if not held:
        return 0.0
    if row is None or row.value_base is None:
        return None
    return float(row.value_base)


def _close_of(mark: AsOfMark | None) -> float | None:
    if mark is None or mark.status != "quoted" or mark.close is None:
        return None
    return float(mark.close)


def _by_listing(marked: MarkedNav) -> dict[str, MarkedLot]:
    out: dict[str, MarkedLot] = {}
    for row in marked.rows:
        key = (row.listing or "").strip().upper()
        if key:
            out[key] = row
    return out


def _frame_dates(histories: dict[str, PriceHistory], start: str, end: str) -> list[str]:
    a = start[:10]
    b = end[:10]
    days: set[str] = {a}
    for hist in histories.values():
        for bar in hist.bars or ():
            t = (bar.t or "")[:10]
            if len(t) >= 10 and a < t <= b:
                days.add(t)
    return sorted(d for d in days if a <= d <= b)


def _frame_rows(
    *,
    start_by: dict[str, MarkedLot],
    t_by: dict[str, MarkedLot],
    start_marks: dict[str, AsOfMark],
    t_marks: dict[str, AsOfMark],
    start_nav: float | None,
) -> list[dict[str, Any]]:
    listings = sorted(set(start_by) | set(t_by))
    out: list[dict[str, Any]] = []
    for listing in listings:
        s_row = start_by.get(listing)
        t_row = t_by.get(listing)
        held_s = _held(s_row)
        held_t = _held(t_row)
        if not held_s and not held_t:
            continue
        val_s = _side_value(s_row, held=held_s)
        val_t = _side_value(t_row, held=held_t)
        pl: float | None
        if val_s is None or val_t is None:
            pl = None
        else:
            pl = val_t - val_s
        c0 = _close_of(start_marks.get(listing))
        c1 = _close_of(t_marks.get(listing))
        change_pct: float | None = None
        if c0 is not None and c1 is not None and c0 != 0:
            change_pct = (c1 / c0 - 1.0) * 100.0
        contrib: float | None = None
        if pl is not None and start_nav not in (None, 0):
            contrib = float(pl) / float(start_nav) * 100.0
        ib = ""
        if t_row is not None and t_row.ib_symbol:
            ib = str(t_row.ib_symbol)
        elif s_row is not None and s_row.ib_symbol:
            ib = str(s_row.ib_symbol)
        else:
            ib = listing
        out.append(
            {
                "ib_symbol": ib,
                "listing": listing,
                "pl": pl,
                "change_pct": change_pct,
                "contrib_pct": contrib,
            }
        )
    return out


def build_mtm_path(
    ib_book: IbBook,
    histories: dict[str, PriceHistory],
    *,
    start: str,
    end: str,
) -> dict[str, Any]:
    """Frames from start through end. ``pl`` is value(t) − value(start)."""
    a = (start or "").strip()[:10]
    b = (end or "").strip()[:10]
    stmt = ib_book.snapshot
    if len(a) < 10 or len(b) < 10:
        return {
            "start": a,
            "end": b,
            "start_nav": None,
            "base_currency": (stmt.base_currency or "").strip(),
            "frames": [],
            "error": "period dates are missing",
        }
    if a > b:
        return {
            "start": a,
            "end": b,
            "start_nav": None,
            "base_currency": (stmt.base_currency or "").strip(),
            "frames": [],
            "error": "period start is after end",
        }
    start_book = as_of_book(ib_book, a)
    start_marks = marks_on(histories, a)
    start_marked = mark_lots(start_book, start_marks)
    start_by = _by_listing(start_marked)
    start_nav = float(start_marked.nav)
    frames: list[dict[str, Any]] = []
    for t in _frame_dates(histories, a, b):
        t_book = as_of_book(ib_book, t)
        t_marks = marks_on(histories, t)
        t_marked = mark_lots(t_book, t_marks)
        rows = _frame_rows(
            start_by=start_by,
            t_by=_by_listing(t_marked),
            start_marks=start_marks,
            t_marks=t_marks,
            start_nav=start_nav,
        )
        pairs = [
            (str(r["ib_symbol"]), float(r["pl"]))
            for r in rows
            if r.get("pl") is not None and float(r["pl"]) != 0.0
        ]
        total = sum(p[1] for p in pairs)
        frames.append(
            {
                "t": t,
                "nav": t_marked.nav,
                "total_pl": total,
                "rows": rows,
                "bars": signed_bar_rows(pairs),
            }
        )
    return {
        "start": a,
        "end": b,
        "start_nav": start_nav,
        "base_currency": (stmt.base_currency or "").strip(),
        "frames": frames,
        "error": None if frames else "No daily closes in this period",
    }


def mtm_path_for(
    ib_book: IbBook,
    svc: HistoryService,
    period: str,
    *,
    today: str | None = None,
) -> dict[str, Any]:
    start, end = resolve_period(period, ib_book.snapshot, today=today)
    listings = window_listings(ib_book, start, end)
    range_key = range_for_span(start, end)
    histories = svc.get_many(listings, range_key) if listings else {}
    body = build_mtm_path(ib_book, histories, start=start, end=end)
    body["period"] = period
    return body
