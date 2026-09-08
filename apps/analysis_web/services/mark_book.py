"""Mark a cash book with closes on a date.

Sibling of ``mark_live_nav``, different identity: nav = cash + Σ qty × close × fx.
Unquoted lots contribute 0 and are flagged. Not a valuation. Not Live NAV.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.analysis_web.services.book_state import BookState, Lot


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

    def as_json(self) -> dict[str, Any]:
        return {
            "nav": self.nav,
            "cash": self.cash,
            "stock": self.stock,
            "n_positions": self.n_positions,
            "n_repriced": self.n_repriced,
            "n_unquoted": self.n_unquoted,
            "as_of": self.as_of,
            "rows": [r.as_json() for r in self.rows],
        }


def _price_for(lot: Lot, prices: dict[str, float]) -> float | None:
    listing = (lot.listing or "").strip().upper()
    if not listing:
        return None
    return _num(prices.get(listing))


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
        rows.append(
            MarkedLot(
                listing=lot.listing,
                qty=lot.qty,
                close=px,
                value_base=value,
                error=err,
                ib_symbol=lot.ib_symbol,
                catalog_ticker=lot.catalog_ticker,
                currency=lot.currency,
                stmt_fx=lot.stmt_fx,
            )
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
        as_of=state.as_of,
        rows=tuple(rows),
    )
