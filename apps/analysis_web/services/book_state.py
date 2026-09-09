"""Reconstruct a cash book as of a date from the IB snapshot + trade ledger.

Pure function. No Yahoo, catalog, or writes. Listing is on the lot
(``holding_print_listing``). Live NAV does not use this walk.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from apps.analysis_web.services.ib_statement import IbBook, IbStatement, Trade
from apps.analysis_web.services.portfolio import holding_print_listing


def listing_for(ib_symbol: str, listing_exch: str | None) -> str:
    return holding_print_listing(ib_symbol, listing_exch) or (
        ib_symbol or ""
    ).strip().upper()


_QTY_EPS = 1e-9


@dataclass(frozen=True)
class Lot:
    """One stock lot. ``listing`` is the mark key; IB/catalog names are aliases."""

    listing: str
    currency: str
    qty: float
    stmt_fx: float | None
    ib_symbol: str | None = None
    catalog_ticker: str | None = None


@dataclass(frozen=True)
class BookState:
    """Cash book: lots + base cash + caveats. Actual and alt are both this.

    ``as_of`` is the date the lots and cash represent.
    """

    lots: tuple[Lot, ...]
    cash_base: float | None
    as_of: str
    caveats: tuple[str, ...]
    base_currency: str = ""
    fx_by_ccy: tuple[tuple[str, float], ...] = ()

    def lot_by_listing(self, listing: str) -> Lot | None:
        want = (listing or "").strip().upper()
        if not want:
            return None
        for lot in self.lots:
            if lot.listing == want:
                return lot
        return None

    def fx_for(self, currency: str) -> float | None:
        cur = (currency or "").strip().upper()
        base = (self.base_currency or "").strip().upper()
        if cur and cur == base:
            return 1.0
        for ccy, rate in self.fx_by_ccy:
            if ccy == cur:
                return rate
        return None

    def as_json(self) -> dict[str, Any]:
        return {
            "lots": [
                {
                    "listing": lot.listing,
                    "currency": lot.currency,
                    "qty": lot.qty,
                    "stmt_fx": lot.stmt_fx,
                    "ib_symbol": lot.ib_symbol,
                    "catalog_ticker": lot.catalog_ticker,
                }
                for lot in self.lots
            ],
            "cash_base": self.cash_base,
            "as_of": self.as_of,
            "caveats": list(self.caveats),
            "base_currency": self.base_currency,
            "fx_by_ccy": {ccy: rate for ccy, rate in self.fx_by_ccy},
        }

    @staticmethod
    def from_json(raw: dict[str, Any] | None) -> "BookState":
        if not isinstance(raw, dict) or not raw:
            raise ValueError("missing seed")
        lots: list[Lot] = []
        for row in raw.get("lots") or ():
            if not isinstance(row, dict):
                continue
            listing = str(row.get("listing") or "").strip().upper()
            if not listing:
                continue
            qty = _num(row.get("qty"))
            lots.append(
                Lot(
                    listing=listing,
                    currency=str(row.get("currency") or ""),
                    qty=0.0 if qty is None else qty,
                    stmt_fx=_num(row.get("stmt_fx")),
                    ib_symbol=row.get("ib_symbol"),
                    catalog_ticker=row.get("catalog_ticker"),
                )
            )
        cash = raw.get("cash_base")
        return BookState(
            lots=tuple(lots),
            cash_base=None if cash is None else _num(cash),
            as_of=str(raw.get("as_of") or ""),
            caveats=tuple(str(c) for c in (raw.get("caveats") or ())),
            base_currency=str(raw.get("base_currency") or ""),
            fx_by_ccy=_fx_pairs(raw.get("fx_by_ccy")),
        )


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


def trade_date(traded_at: str) -> str | None:
    """YYYY-MM-DD from an IB ``traded_at`` stamp, or None."""
    s = (traded_at or "").strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def day_before(as_of: str) -> str:
    """Calendar day before ``as_of`` (YYYY-MM-DD)."""
    d = date.fromisoformat(as_of[:10])
    return (d - timedelta(days=1)).isoformat()


def earliest_stock_date(ib_book: IbBook) -> str | None:
    days: list[str] = []
    for trade in ib_book.trades or ():
        if not _is_stock(trade.asset_category):
            continue
        day = trade_date(trade.traded_at)
        if day:
            days.append(day)
    period = (ib_book.snapshot.period_from or "").strip()[:10]
    if period:
        days.append(period)
    return min(days) if days else None


def seed_book(ib_book: IbBook, fork_date: str) -> BookState:
    """Holdings immediately before the copied ledger starts."""
    return as_of_book(ib_book, day_before(fork_date))


def _fx_pairs(raw: Any) -> tuple[tuple[str, float], ...]:
    if isinstance(raw, dict):
        items = raw.items()
    elif isinstance(raw, (list, tuple)):
        items = []
        for row in raw:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                items.append((row[0], row[1]))
    else:
        items = []
    out: list[tuple[str, float]] = []
    for key, val in items:
        ccy = str(key or "").strip().upper()
        rate = _num(val)
        if ccy and rate is not None:
            out.append((ccy, float(rate)))
    out.sort(key=lambda pair: pair[0])
    return tuple(out)


def freeze_fx(stmt: IbStatement) -> tuple[tuple[str, float], ...]:
    """Copy statement Forex closes onto a seed. Base currency is 1."""
    raw = dict(stmt.forex_closes or {})
    base = (stmt.base_currency or "").strip().upper()
    if base:
        raw.setdefault(base, 1.0)
    return _fx_pairs(raw)


def _is_stock(category: str | None) -> bool:
    return (category or "Stocks").strip().lower() == "stocks"


def _caveats(*, as_of: str, period_from: str) -> tuple[str, ...]:
    lines = [
        "Stock lots from the IB ledger as of this date. "
        "Cash is statement cash adjusted by stock-trade proceeds. "
        "Dividends, deposits outside the statement window, and FX conversions "
        "are not reversed."
    ]
    if period_from and as_of < period_from:
        lines.append(
            "This date is before the statement period. Cash is approximate."
        )
    return tuple(lines)


def _qty_factor(trade_day: str, *, as_of: str, period_to: str) -> float:
    """+1 apply (after snapshot), -1 reverse (before snapshot), else 0."""
    if as_of < period_to:
        return -1.0 if trade_day > as_of else 0.0
    if as_of > period_to:
        return 1.0 if period_to < trade_day <= as_of else 0.0
    return 0.0


def _stock_cash_effect(trade: Trade, stmt: IbStatement) -> float | None:
    proceeds = _num(trade.proceeds)
    commission = _num(trade.commission) or 0.0
    if proceeds is None:
        return None
    native = proceeds + commission
    ccy = (trade.currency or "").strip()
    return stmt.value_base(native, ccy)


def as_of_book(ib_book: IbBook, as_of: str) -> BookState:
    """Walk snapshot lots and cash to ``as_of`` using stock fills only."""
    day = (as_of or "").strip()
    if len(day) < 10 or day[4] != "-" or day[7] != "-":
        raise ValueError("as_of must be YYYY-MM-DD")
    day = day[:10]
    stmt = ib_book.snapshot
    period_to = (stmt.period_to or "").strip()[:10]
    period_from = (stmt.period_from or "").strip()[:10]

    exch: dict[str, str | None] = {}
    currency: dict[str, str] = {}
    qty: dict[str, float] = {}
    for pos in stmt.positions:
        if not _is_stock(pos.asset_category):
            continue
        sym = (pos.ib_symbol or "").strip()
        if not sym:
            continue
        exch[sym] = pos.listing_exch
        if pos.currency:
            currency[sym] = pos.currency
        q = _num(pos.quantity)
        if q is not None:
            qty[sym] = qty.get(sym, 0.0) + q
    for inst in stmt.instruments:
        if not _is_stock(inst.asset_category):
            continue
        sym = (inst.ib_symbol or "").strip()
        if not sym:
            continue
        exch.setdefault(sym, inst.listing_exch)

    cash: float | None = None
    nav_cash = stmt.nav_asset("Cash")
    if nav_cash is not None:
        cash = _num(nav_cash.current_total)

    for trade in ib_book.trades or ():
        if not _is_stock(trade.asset_category):
            continue
        tday = trade_date(trade.traded_at)
        if tday is None:
            continue
        signed = _num(trade.quantity)
        if signed is None:
            continue
        factor = _qty_factor(tday, as_of=day, period_to=period_to)
        if factor == 0.0:
            continue
        sym = (trade.ib_symbol or "").strip()
        if not sym:
            continue
        qty[sym] = qty.get(sym, 0.0) + factor * signed
        if trade.currency:
            currency.setdefault(sym, trade.currency)
        effect = _stock_cash_effect(trade, stmt)
        if cash is not None and effect is not None:
            cash = cash + factor * effect

    by_listing: dict[str, Lot] = {}
    for sym in sorted(qty):
        q = qty[sym]
        if abs(q) <= _QTY_EPS:
            continue
        listing = holding_print_listing(sym, exch.get(sym)) or sym.strip().upper()
        ccy = (currency.get(sym) or stmt.base_currency or "").strip().upper()
        fx = stmt.forex_close(ccy) if ccy else None
        prev = by_listing.get(listing)
        if prev is None:
            by_listing[listing] = Lot(
                listing=listing,
                currency=ccy,
                qty=q,
                stmt_fx=fx,
                ib_symbol=sym,
            )
            continue
        by_listing[listing] = Lot(
            listing=listing,
            currency=prev.currency or ccy,
            qty=prev.qty + q,
            stmt_fx=prev.stmt_fx if prev.stmt_fx is not None else fx,
            ib_symbol=prev.ib_symbol or sym,
            catalog_ticker=prev.catalog_ticker,
        )
    lots = tuple(sorted(by_listing.values(), key=lambda lot: lot.listing))
    return BookState(
        lots=lots,
        cash_base=cash,
        as_of=day,
        caveats=_caveats(as_of=day, period_from=period_from),
        base_currency=(stmt.base_currency or "").strip().upper(),
        fx_by_ccy=freeze_fx(stmt),
    )
