"""Reconstructed period MTM for the live IB book.

Walks ``as_of_book`` and marks with Yahoo daily closes. P/L is mark change
net of IB fill cash, not position-value change. Display math, not a
valuation and not the IB statement MTM file. Does not import what-if.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from apps.analysis_web.services.book_state import (
    as_of_book,
    listing_for,
    stock_fill_cash_base,
    trade_date,
)
from apps.analysis_web.services.ib_statement import IbBook, IbStatement
from apps.analysis_web.services.mark_book import AsOfMark, MarkedLot, MarkedNav, mark_lots, marks_on
from apps.analysis_web.services.price_history import (
    HistoryService,
    PriceHistory,
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


def _is_stock_cat(category: str | None) -> bool:
    return (category or "Stocks").strip().lower() == "stocks"


def _exch_by_symbol(ib_book: IbBook) -> dict[str, str | None]:
    exch: dict[str, str | None] = {}
    stmt = ib_book.snapshot
    for pos in stmt.positions or ():
        if not _is_stock_cat(pos.asset_category):
            continue
        sym = (pos.ib_symbol or "").strip()
        if sym:
            exch[sym] = pos.listing_exch
    for inst in stmt.instruments or ():
        if not _is_stock_cat(inst.asset_category):
            continue
        sym = (inst.ib_symbol or "").strip()
        if sym:
            exch.setdefault(sym, inst.listing_exch)
    return exch


def _listing_of(ib_symbol: str, exch: dict[str, str | None]) -> str:
    sym = (ib_symbol or "").strip()
    return listing_for(sym, exch.get(sym))


def window_listings(ib_book: IbBook, start: str, end: str) -> list[str]:
    """Listings that can appear: start lots, end lots, and in-window fills."""
    a = start[:10]
    b = end[:10]
    exch = _exch_by_symbol(ib_book)
    seen: list[str] = []
    have: set[str] = set()

    def _add(key: str) -> None:
        k = (key or "").strip().upper()
        if k and k not in have:
            have.add(k)
            seen.append(k)

    for lot in as_of_book(ib_book, a).lots:
        _add(lot.listing)
    for lot in as_of_book(ib_book, b).lots:
        _add(lot.listing)
    for trade in ib_book.trades or ():
        if not _is_stock_cat(trade.asset_category):
            continue
        day = trade_date(trade.traded_at)
        if day and a <= day <= b:
            _add(_listing_of(trade.ib_symbol, exch))
    return seen


def trade_cash_by_listing(
    ib_book: IbBook,
    *,
    after: str,
    through: str,
) -> tuple[dict[str, float], set[str]]:
    """Fill cash in base with ``after < trade_day <= through``.

    Unknown cash (no proceeds and no qty×price) is listed separately so
    that listing's P/L stays None instead of looking like a market-value
    change.
    """
    a = after[:10]
    b = through[:10]
    exch = _exch_by_symbol(ib_book)
    stmt = ib_book.snapshot
    cash: dict[str, float] = {}
    unknown: set[str] = set()
    for trade in ib_book.trades or ():
        if not _is_stock_cat(trade.asset_category):
            continue
        day = trade_date(trade.traded_at)
        if day is None or day <= a or day > b:
            continue
        key = _listing_of(trade.ib_symbol, exch)
        if not key:
            continue
        effect = stock_fill_cash_base(trade, stmt)
        if effect is None:
            unknown.add(key)
            continue
        cash[key] = cash.get(key, 0.0) + float(effect)
    return cash, unknown


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
    days: set[str] = {a, b}
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
    cash_by: dict[str, float],
    cash_unknown: set[str],
    ib_by_listing: dict[str, str],
) -> list[dict[str, Any]]:
    listings = sorted(set(start_by) | set(t_by) | set(cash_by) | set(cash_unknown))
    out: list[dict[str, Any]] = []
    for listing in listings:
        s_row = start_by.get(listing)
        t_row = t_by.get(listing)
        held_s = _held(s_row)
        held_t = _held(t_row)
        cash = float(cash_by.get(listing, 0.0))
        if not held_s and not held_t and abs(cash) <= _QTY_EPS and listing not in cash_unknown:
            continue
        val_s = _side_value(s_row, held=held_s)
        val_t = _side_value(t_row, held=held_t)
        pl: float | None
        if listing in cash_unknown or val_s is None or val_t is None:
            pl = None
        else:
            pl = val_t - val_s + cash
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
            ib = ib_by_listing.get(listing) or listing
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


def _ib_by_listing(ib_book: IbBook) -> dict[str, str]:
    exch = _exch_by_symbol(ib_book)
    out: dict[str, str] = {}
    for trade in ib_book.trades or ():
        if not _is_stock_cat(trade.asset_category):
            continue
        key = _listing_of(trade.ib_symbol, exch)
        if key and (trade.ib_symbol or "").strip() and key not in out:
            out[key] = str(trade.ib_symbol).strip()
    return out


def build_mtm_interval(
    ib_book: IbBook,
    histories: dict[str, PriceHistory],
    *,
    start: str,
    end: str,
) -> dict[str, Any]:
    """One still: value(end) − value(start) + fill cash after start through end.

    Same row identity as the last frame of ``build_mtm_path``. No frames, no bars.
    """
    a = (start or "").strip()[:10]
    b = (end or "").strip()[:10]
    stmt = ib_book.snapshot
    base: dict[str, Any] = {
        "start": a,
        "end": b,
        "start_nav": None,
        "base_currency": (stmt.base_currency or "").strip(),
        "rows": [],
        "error": None,
    }
    if len(a) < 10 or len(b) < 10:
        base["error"] = "period dates are missing"
        return base
    if a > b:
        base["error"] = "period start is after end"
        return base
    start_book = as_of_book(ib_book, a)
    start_marks = marks_on(histories, a)
    start_marked = mark_lots(start_book, start_marks)
    start_by = _by_listing(start_marked)
    start_nav = float(start_marked.nav)
    t_book = as_of_book(ib_book, b)
    t_marks = marks_on(histories, b)
    t_marked = mark_lots(t_book, t_marks)
    cash_by, cash_unknown = trade_cash_by_listing(ib_book, after=a, through=b)
    rows = _frame_rows(
        start_by=start_by,
        t_by=_by_listing(t_marked),
        start_marks=start_marks,
        t_marks=t_marks,
        start_nav=start_nav,
        cash_by=cash_by,
        cash_unknown=cash_unknown,
        ib_by_listing=_ib_by_listing(ib_book),
    )
    base["start_nav"] = start_nav
    base["rows"] = rows
    return base


def build_mtm_path(
    ib_book: IbBook,
    histories: dict[str, PriceHistory],
    *,
    start: str,
    end: str,
) -> dict[str, Any]:
    """Frames from start through end.

    ``pl`` is value(t) − value(start) + fill cash after start through t.
    Buys and sells are cash, not fake P/L.
    """
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
    ib_by_listing = _ib_by_listing(ib_book)
    frames: list[dict[str, Any]] = []
    for t in _frame_dates(histories, a, b):
        t_book = as_of_book(ib_book, t)
        t_marks = marks_on(histories, t)
        t_marked = mark_lots(t_book, t_marks)
        cash_by, cash_unknown = trade_cash_by_listing(ib_book, after=a, through=t)
        rows = _frame_rows(
            start_by=start_by,
            t_by=_by_listing(t_marked),
            start_marks=start_marks,
            t_marks=t_marks,
            start_nav=start_nav,
            cash_by=cash_by,
            cash_unknown=cash_unknown,
            ib_by_listing=ib_by_listing,
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
    histories = svc.get_many(listings, since=start) if listings else {}
    body = build_mtm_path(ib_book, histories, start=start, end=end)
    body["period"] = period
    return body


def parse_window_dates(start: str, end: str) -> tuple[str, str]:
    """Inclusive YYYY-MM-DD pair. Raises PeriodError if unusable."""
    a = (start or "").strip()[:10]
    b = (end or "").strip()[:10]
    if len(a) < 10 or len(b) < 10:
        raise PeriodError("start and end must be YYYY-MM-DD")
    try:
        date.fromisoformat(a)
        date.fromisoformat(b)
    except ValueError as e:
        raise PeriodError("start and end must be YYYY-MM-DD") from e
    if a > b:
        raise PeriodError("period start is after end")
    return a, b


def mtm_path_window(
    ib_book: IbBook,
    svc: HistoryService,
    start: str,
    end: str,
) -> dict[str, Any]:
    a, b = parse_window_dates(start, end)
    listings = window_listings(ib_book, a, b)
    histories = svc.get_many(listings, since=a) if listings else {}
    body = build_mtm_path(ib_book, histories, start=a, end=b)
    body["period"] = ""
    return body


def mtm_interval_for(
    ib_book: IbBook,
    svc: HistoryService,
    period: str,
    *,
    today: str | None = None,
) -> dict[str, Any]:
    start, end = resolve_period(period, ib_book.snapshot, today=today)
    listings = window_listings(ib_book, start, end)
    histories = svc.get_many(listings, since=start) if listings else {}
    body = build_mtm_interval(ib_book, histories, start=start, end=end)
    body["period"] = period
    return body


def mtm_interval_window(
    ib_book: IbBook,
    svc: HistoryService,
    start: str,
    end: str,
) -> dict[str, Any]:
    a, b = parse_window_dates(start, end)
    listings = window_listings(ib_book, a, b)
    histories = svc.get_many(listings, since=a) if listings else {}
    body = build_mtm_interval(ib_book, histories, start=a, end=b)
    body["period"] = ""
    return body


def choose_path_args(
    period: str | None,
    start: str | None,
    end: str | None,
) -> tuple[str, str, str]:
    """Either a named period or a free window. Not both.

    Returns ``("period", period, "")`` or ``("window", start, end)``.
    """
    p = (period or "").strip()
    a = (start or "").strip()
    b = (end or "").strip()
    has_p = bool(p)
    has_a = bool(a)
    has_b = bool(b)
    if has_p and (has_a or has_b):
        raise PeriodError("pass period= or start= and end=, not both")
    if has_a != has_b:
        raise PeriodError("start and end must both be set")
    if has_p:
        return ("period", p, "")
    if has_a:
        return ("window", a, b)
    raise PeriodError("pass period= or start= and end=")
