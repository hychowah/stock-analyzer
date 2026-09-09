"""Mark a cash book with closes on a date.

Sibling of ``mark_live_nav``, different identity: nav = cash + Σ qty × close × fx.
Unquoted lots contribute 0 and are flagged. Not a valuation. Not Live NAV.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.analysis_web.services.book_state import BookState, Lot
from apps.analysis_web.services.price_history import PriceHistory, close_on


def _num(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        n = float(raw)
    except (TypeError, ValueError):
        return None
    if n != n or n in (float("inf"), float("-inf")):
        return None
    return n


@dataclass(frozen=True)
class AsOfMark:
    """Last Yahoo daily close on or before D for one listing.

    status is quoted | unquoted | unavailable. close and bar_date exist
    only when quoted. Not last print. Not a pending UI cell — pending is
    the as-of pane before this type exists.
    """

    listing: str
    as_of: str
    status: str
    close: float | None = None
    bar_date: str | None = None
    error: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "listing": self.listing,
            "as_of": self.as_of,
            "status": self.status,
            "close": self.close,
            "bar_date": self.bar_date,
            "error": self.error,
        }


def mark_on(history: PriceHistory, date: str) -> AsOfMark:
    """Map one series onto D. error on the series → unavailable;
    no bar on or before D → unquoted; else quoted."""
    listing = (history.symbol or "").strip().upper()
    day = (date or "").strip()[:10]
    if history.error:
        return AsOfMark(
            listing=listing,
            as_of=day,
            status="unavailable",
            error=history.error,
        )
    bar = close_on(history.bars, day)
    if bar is None:
        return AsOfMark(listing=listing, as_of=day, status="unquoted")
    t = (bar.t or "")[:10] or None
    return AsOfMark(
        listing=listing,
        as_of=day,
        status="quoted",
        close=bar.close,
        bar_date=t,
    )


def marks_on(
    histories: dict[str, PriceHistory],
    date: str,
) -> dict[str, AsOfMark]:
    """``mark_on`` for each listing. Keys are uppercased listings."""
    out: dict[str, AsOfMark] = {}
    for raw, hist in histories.items():
        listing = (raw or hist.symbol or "").strip().upper()
        if not listing:
            continue
        out[listing] = mark_on(hist, date)
    return out


@dataclass(frozen=True)
class MarkedLot:
    listing: str
    qty: float
    close: float | None
    value_base: float | None
    error: str | None
    ib_symbol: str | None = None
    catalog_ticker: str | None = None
    currency: str = ""
    stmt_fx: float | None = None
    bar_date: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "listing": self.listing,
            "qty": self.qty,
            "close": self.close,
            "value_base": self.value_base,
            "error": self.error,
            "ib_symbol": self.ib_symbol,
            "catalog_ticker": self.catalog_ticker,
            "currency": self.currency,
            "stmt_fx": self.stmt_fx,
            "bar_date": self.bar_date,
        }


@dataclass(frozen=True)
class MarkedNav:
    nav: float
    cash: float | None
    stock: float
    n_positions: int
    n_repriced: int
    n_unquoted: int
    as_of: str
    rows: tuple[MarkedLot, ...]
    n_unavailable: int = 0

    def as_json(self) -> dict[str, Any]:
        return {
            "nav": self.nav,
            "cash": self.cash,
            "stock": self.stock,
            "n_positions": self.n_positions,
            "n_repriced": self.n_repriced,
            "n_unquoted": self.n_unquoted,
            "n_unavailable": self.n_unavailable,
            "as_of": self.as_of,
            "rows": [r.as_json() for r in self.rows],
        }


def nav_delta_rows(
    actual: MarkedNav, alt: MarkedNav
) -> tuple[tuple[str, float], ...]:
    """Per-listing and cash contribution to ``alt.nav − actual.nav``.

    Unquoted value is 0. Cash is included when either book has cash
    (missing cash counts as 0). Does not rank or paint bars.
    """
    values: dict[str, float] = {}
    for row in actual.rows:
        key = (row.listing or "").strip().upper()
        if not key:
            continue
        values[key] = values.get(key, 0.0) - (
            0.0 if row.value_base is None else float(row.value_base)
        )
    for row in alt.rows:
        key = (row.listing or "").strip().upper()
        if not key:
            continue
        values[key] = values.get(key, 0.0) + (
            0.0 if row.value_base is None else float(row.value_base)
        )
    out: list[tuple[str, float]] = [
        (name, pl) for name, pl in values.items() if pl != 0.0
    ]
    if actual.cash is not None or alt.cash is not None:
        cash_pl = (0.0 if alt.cash is None else float(alt.cash)) - (
            0.0 if actual.cash is None else float(actual.cash)
        )
        if cash_pl != 0.0:
            out.append(("Cash", cash_pl))
    return tuple(out)


def _price_for(lot: Lot, prices: dict[str, float]) -> float | None:
    listing = (lot.listing or "").strip().upper()
    if not listing:
        return None
    return _num(prices.get(listing))


def _row(
    lot: Lot,
    *,
    close: float | None,
    value: float | None,
    error: str | None,
    bar_date: str | None = None,
) -> MarkedLot:
    return MarkedLot(
        listing=lot.listing,
        qty=lot.qty,
        close=close,
        value_base=value,
        error=error,
        ib_symbol=lot.ib_symbol,
        catalog_ticker=lot.catalog_ticker,
        currency=lot.currency,
        stmt_fx=lot.stmt_fx,
        bar_date=bar_date,
    )


def mark_book(state: BookState, prices: dict[str, float]) -> MarkedNav:
    """``nav = (cash or 0) + Σ qty × close × stmt_fx``. Unquoted → 0 + flag."""
    by = {str(k).strip().upper(): v for k, v in prices.items()}
    rows: list[MarkedLot] = []
    stock = 0.0
    n_repriced = 0
    n_unquoted = 0
    for lot in state.lots:
        px = _price_for(lot, by)
        fx = lot.stmt_fx
        err: str | None = None
        value: float | None = None
        if px is None:
            err = "unquoted"
            n_unquoted += 1
        elif fx is None:
            err = "missing_fx"
            n_unquoted += 1
        else:
            value = float(lot.qty) * float(px) * float(fx)
            stock += value
            n_repriced += 1
        rows.append(_row(lot, close=px, value=value, error=err))
    cash = state.cash_base
    nav = (0.0 if cash is None else float(cash)) + stock
    return MarkedNav(
        nav=nav,
        cash=cash,
        stock=stock,
        n_positions=len(state.lots),
        n_repriced=n_repriced,
        n_unquoted=n_unquoted,
        as_of=state.as_of,
        rows=tuple(rows),
    )


def mark_lots(state: BookState, marks: dict[str, AsOfMark]) -> MarkedNav:
    """Same NAV identity as ``mark_book``; preserves unavailable vs unquoted."""
    by = {str(k).strip().upper(): v for k, v in marks.items()}
    rows: list[MarkedLot] = []
    stock = 0.0
    n_repriced = 0
    n_unquoted = 0
    n_unavailable = 0
    for lot in state.lots:
        listing = (lot.listing or "").strip().upper()
        mark = by.get(listing)
        px: float | None = None
        bar_date: str | None = None
        err: str | None = None
        value: float | None = None
        if mark is None or mark.status == "unquoted":
            err = "unquoted"
            n_unquoted += 1
        elif mark.status == "unavailable":
            err = "unavailable"
            n_unavailable += 1
        else:
            px = mark.close
            bar_date = mark.bar_date
            fx = lot.stmt_fx
            if px is None:
                err = "unquoted"
                n_unquoted += 1
            elif fx is None:
                err = "missing_fx"
                n_unquoted += 1
            else:
                value = float(lot.qty) * float(px) * float(fx)
                stock += value
                n_repriced += 1
        rows.append(
            _row(lot, close=px, value=value, error=err, bar_date=bar_date)
        )
    cash = state.cash_base
    nav = (0.0 if cash is None else float(cash)) + stock
    return MarkedNav(
        nav=nav,
        cash=cash,
        stock=stock,
        n_positions=len(state.lots),
        n_repriced=n_repriced,
        n_unquoted=n_unquoted,
        n_unavailable=n_unavailable,
        as_of=state.as_of,
        rows=tuple(rows),
    )
