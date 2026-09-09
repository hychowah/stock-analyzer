"""Priced-fill replay and POST policy for alternative histories.

Replay is a pure function on already-priced fills. Catalog allowlist and
Yahoo close-or-override happen at POST, then the fill is stored.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from packages.catalog_api.client import CatalogApi, DbMissing

from apps.analysis_web.services.book_state import (
    BookState,
    Lot,
    earliest_stock_date,
    listing_for,
    seed_book,
    trade_date,
)
from apps.analysis_web.services.ib_statement import IbBook, Trade
from apps.analysis_web.services.mark_book import MarkedNav, mark_book
from apps.analysis_web.services.portfolio import latest_run
from apps.analysis_web.services.price_history import PriceBar, close_on


_QTY_EPS = 1e-9
_SIDES = frozenset({"buy", "sell"})


class ReplayError(Exception):
    """Policy failure on replay or POST. ``code`` is a stable token."""

    def __init__(self, code: str, message: str, **extra: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra

    def as_json(self) -> dict[str, Any]:
        body = {"error": self.code, "message": self.message}
        body.update(self.extra)
        return body


class NotFoundError(Exception):
    """History or fill id does not exist. Not a replay failure."""


@dataclass(frozen=True)
class PricedFill:
    """One fill. Price and listing are already resolved.

    ``source`` is ``real`` (copied IB trade) or ``hyp`` (what-if).
    """

    as_of: str
    side: str
    listing: str
    quantity: float
    fill_price: float
    currency: str
    stmt_fx: float | None
    catalog_ticker: str | None = None
    ib_symbol: str | None = None
    price_mode: str = "close"
    notes: str = ""
    id: int | None = None
    source: str = "hyp"
    cash_effect: float | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "as_of": self.as_of,
            "side": self.side,
            "listing": self.listing,
            "quantity": self.quantity,
            "fill_price": self.fill_price,
            "currency": self.currency,
            "stmt_fx": self.stmt_fx,
            "catalog_ticker": self.catalog_ticker,
            "ib_symbol": self.ib_symbol,
            "price_mode": self.price_mode,
            "notes": self.notes,
            "source": self.source,
            "cash_effect": self.cash_effect,
        }


@dataclass(frozen=True)
class History:
    """Self-contained paper book: frozen seed plus copied IB fills plus what-if fills."""

    name: str
    fork_date: str
    fills: tuple[PricedFill, ...]
    seed: BookState
    notes: str = ""
    id: int | None = None

    def hyp_fills(self) -> tuple[PricedFill, ...]:
        return tuple(f for f in self.fills if f.source != "real")

    def real_fills(self) -> tuple[PricedFill, ...]:
        return tuple(f for f in self.fills if f.source == "real")


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


def _day(raw: str) -> str:
    s = (raw or "").strip()[:10]
    if len(s) < 10 or s[4] != "-" or s[7] != "-":
        raise ReplayError("bad_date", "Date must be YYYY-MM-DD")
    return s


def _listing(raw: str | None) -> str:
    s = str(raw or "").strip().upper()
    if not s:
        raise ReplayError("empty_listing", "Listing is required")
    return s


def utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _fill_order(fill: PricedFill) -> tuple[str, int]:
    return (fill.as_of, fill.id if fill.id is not None else 0)


def _stamp_as_of(state: BookState, day: str) -> BookState:
    """Set the snapshot date. Lots and cash are unchanged."""
    want = _day(day)
    if state.as_of == want:
        return state
    return replace(state, as_of=want)


def overlay_fills(seed: BookState, fills: Iterable[PricedFill]) -> tuple[PricedFill, ...]:
    """Clip later real sells that a what-if sell already consumed.

    Stored real rows stay the IB copy. Returned fills are what strict
    ``replay`` will apply. What-if oversell is not clipped here.
    """
    qty_held: dict[str, float] = {lot.listing: lot.qty for lot in seed.lots}
    out: list[PricedFill] = []
    for fill in sorted(fills, key=_fill_order):
        listing = _listing(fill.listing)
        qty = _num(fill.quantity)
        if qty is None or qty <= _QTY_EPS:
            out.append(fill)
            continue
        side = (fill.side or "").strip().lower()
        held = qty_held.get(listing, 0.0)
        if side == "buy":
            qty_held[listing] = held + qty
            out.append(fill)
            continue
        apply_qty = qty
        if fill.source == "real" and held + _QTY_EPS < qty:
            apply_qty = max(0.0, held)
            if apply_qty <= _QTY_EPS:
                continue
            scale = apply_qty / qty
            cash_effect = (
                None if fill.cash_effect is None else float(fill.cash_effect) * scale
            )
            fill = replace(fill, quantity=apply_qty, cash_effect=cash_effect)
        qty_held[listing] = held - apply_qty
        if abs(qty_held[listing]) <= _QTY_EPS:
            qty_held.pop(listing, None)
        out.append(fill)
    return tuple(out)


def replay(state: BookState, fills: Iterable[PricedFill]) -> BookState:
    """Apply priced fills in as-of then id order. No catalog, no Yahoo.

    Oversell fails for every fill — clip later real sells with
    ``overlay_fills`` first. Cash shortfall fails for what-if buys.
    Copied IB buys still apply if statement cash goes negative: that
    cash is approximate, and those fills are the frozen ledger.

    Fill floor is ``state.as_of`` (seed vintage on the first call).
    This function copies that field through; ``state_on`` / ``_apply_through``
    stamp the through-date on the snapshot.
    """
    lots: dict[str, Lot] = {lot.listing: lot for lot in state.lots}
    cash = 0.0 if state.cash_base is None else float(state.cash_base)
    for fill in sorted(fills, key=_fill_order):
        day = _day(fill.as_of)
        if day < state.as_of:
            raise ReplayError(
                "before_fork",
                "Decision date is before the copied ledger starts.",
                as_of=day,
                fork=state.as_of,
            )
        side = (fill.side or "").strip().lower()
        if side not in _SIDES:
            raise ReplayError("bad_side", "Side must be buy or sell")
        listing = _listing(fill.listing)
        qty = _num(fill.quantity)
        px = _num(fill.fill_price)
        if qty is None or qty <= _QTY_EPS:
            raise ReplayError("zero_qty", "Quantity must be positive")
        if px is None or px <= 0:
            raise ReplayError("bad_price", "Fill price must be positive")
        fx = fill.stmt_fx
        ccy = (fill.currency or state.base_currency or "").strip().upper()
        if fx is None:
            if ccy and ccy == (state.base_currency or "").upper():
                fx = 1.0
            else:
                raise ReplayError("missing_fx", "No statement FX for this currency")
        existing = lots.get(listing)

        def _cash_delta(apply_qty: float) -> float:
            if fill.cash_effect is not None and qty > 0:
                return float(fill.cash_effect) * (apply_qty / qty)
            signed = apply_qty * px * float(fx)
            return signed if side == "sell" else -signed

        if side == "buy":
            base = -_cash_delta(qty)
            if cash + _QTY_EPS < base and fill.source != "real":
                raise ReplayError(
                    "insufficient_cash",
                    "Not enough cash for this buy.",
                    need=base,
                    cash=cash,
                    short=base - cash,
                )
            cash += _cash_delta(qty)
            new_qty = (existing.qty if existing else 0.0) + qty
            lots[listing] = Lot(
                listing=listing,
                currency=ccy,
                qty=new_qty,
                stmt_fx=fx,
                ib_symbol=(existing.ib_symbol if existing else fill.ib_symbol),
                catalog_ticker=fill.catalog_ticker
                or (existing.catalog_ticker if existing else None),
            )
            continue
        held = existing.qty if existing else 0.0
        if held + _QTY_EPS < qty:
            raise ReplayError(
                "oversell",
                "Cannot sell more than the alt book holds.",
                held=held,
                quantity=qty,
                listing=listing,
            )
        cash += _cash_delta(qty)
        new_qty = held - qty
        if abs(new_qty) <= _QTY_EPS:
            lots.pop(listing, None)
        elif existing is not None:
            lots[listing] = replace(existing, qty=new_qty)
    out_lots = tuple(sorted(lots.values(), key=lambda lot: lot.listing))
    return BookState(
        lots=out_lots,
        cash_base=cash,
        as_of=state.as_of,
        caveats=state.caveats,
        base_currency=state.base_currency,
        fx_by_ccy=state.fx_by_ccy,
    )


def fills_from_ib(ib_book: IbBook) -> tuple[PricedFill, ...]:
    """Copy stock trades from the IB ledger as already-priced real fills."""
    stmt = ib_book.snapshot
    exch: dict[str, str | None] = {}
    for pos in stmt.positions:
        if (pos.ib_symbol or "").strip():
            exch[pos.ib_symbol.strip()] = pos.listing_exch
    for inst in stmt.instruments:
        if (inst.ib_symbol or "").strip():
            exch.setdefault(inst.ib_symbol.strip(), inst.listing_exch)
    out: list[PricedFill] = []
    for trade in ib_book.trades or ():
        fill = _fill_from_trade(trade, stmt, exch)
        if fill is not None:
            out.append(fill)
    out.sort(key=lambda f: (f.as_of, f.listing))
    return tuple(out)


def _fill_from_trade(
    trade: Trade,
    stmt: Any,
    exch: dict[str, str | None],
) -> PricedFill | None:
    if (trade.asset_category or "Stocks").strip().lower() != "stocks":
        return None
    day = trade_date(trade.traded_at)
    if day is None:
        return None
    signed = _num(trade.quantity)
    if signed is None or abs(signed) <= _QTY_EPS:
        return None
    side = "buy" if signed > 0 else "sell"
    qty = abs(signed)
    px = _num(trade.trade_price)
    if px is None or px <= 0:
        proceeds = _num(trade.proceeds)
        if proceeds is None or qty <= 0:
            return None
        px = abs(proceeds) / qty
    if px <= 0:
        return None
    sym = (trade.ib_symbol or "").strip()
    if not sym:
        return None
    listing = listing_for(sym, exch.get(sym))
    if not listing:
        return None
    ccy = (trade.currency or stmt.base_currency or "").strip().upper()
    fx = stmt.forex_close(ccy)
    if fx is None and ccy == (stmt.base_currency or "").upper():
        fx = 1.0
    proceeds = _num(trade.proceeds)
    commission = _num(trade.commission) or 0.0
    cash_effect = None
    if proceeds is not None:
        cash_effect = stmt.value_base(proceeds + commission, ccy)
    return PricedFill(
        as_of=day,
        side=side,
        listing=listing,
        quantity=qty,
        fill_price=px,
        currency=ccy,
        stmt_fx=fx,
        ib_symbol=sym,
        price_mode="ib",
        source="real",
        cash_effect=cash_effect,
    )


def history_from_ib(ib_book: IbBook, *, name: str, notes: str = "") -> History:
    fork = earliest_stock_date(ib_book)
    if not fork:
        raise ReplayError("bad_date", "IB book has no stock trades to copy")
    hist = History(
        name=(name or "").strip() or "Untitled",
        fork_date=fork,
        fills=fills_from_ib(ib_book),
        seed=seed_book(ib_book, fork),
        notes=notes or "",
    )
    trial_replay(hist)
    return hist


def trial_replay(hist: History) -> BookState:
    """Replay the overlay fill list. Raises ReplayError if it is not a book."""
    return replay(hist.seed, overlay_fills(hist.seed, hist.fills))


def actual_state(hist: History, as_of: str | None = None) -> BookState:
    fills: Iterable[PricedFill] = hist.real_fills()
    if as_of is not None:
        fills = fills_through(fills, as_of)
    book = replay(hist.seed, fills)
    if as_of is not None:
        return _stamp_as_of(book, as_of)
    return book


def alt_state(hist: History, as_of: str | None = None) -> BookState:
    fills: Iterable[PricedFill] = hist.fills
    if as_of is not None:
        fills = fills_through(fills, as_of)
    book = replay(hist.seed, overlay_fills(hist.seed, fills))
    if as_of is not None:
        return _stamp_as_of(book, as_of)
    return book


def state_on(hist: History, as_of: str) -> BookState:
    return alt_state(hist, as_of)


def with_hyp_fill(hist: History, fill: PricedFill) -> History:
    proposed = replace(
        hist,
        fills=hist.fills + (replace(fill, source="hyp"),),
    )
    trial_replay(proposed)
    return proposed


def drop_hyp_fill(hist: History, fill_id: int) -> History:
    target = next((f for f in hist.fills if f.id == fill_id), None)
    if target is None:
        raise NotFoundError("Decision not found")
    if target.source == "real":
        raise ReplayError("protected", "Copied IB fills cannot be removed")
    proposed = replace(
        hist,
        fills=tuple(f for f in hist.fills if f.id != fill_id),
    )
    trial_replay(proposed)
    return proposed


def fills_through(fills: Iterable[PricedFill], as_of: str) -> list[PricedFill]:
    day = _day(as_of)
    return [f for f in fills if _day(f.as_of) <= day]


def prices_on(
    bars_by_listing: dict[str, tuple[PriceBar, ...] | list[PriceBar]],
    date: str,
) -> dict[str, float]:
    out: dict[str, float] = {}
    for listing, bars in bars_by_listing.items():
        bar = close_on(bars, date)
        if bar is not None:
            out[listing.strip().upper()] = bar.close
    return out


def _apply_through(
    state: BookState,
    fills: tuple[PricedFill, ...] | list[PricedFill],
    index: int,
    day: str,
) -> tuple[BookState, int]:
    batch: list[PricedFill] = []
    n = len(fills)
    while index < n and fills[index].as_of <= day:
        batch.append(fills[index])
        index += 1
    if batch:
        state = replay(state, batch)
    return _stamp_as_of(state, day), index


def _pointer_prices(
    bars_by_listing: dict[str, tuple[PriceBar, ...] | list[PriceBar]],
    days: list[str],
) -> list[dict[str, float]]:
    listings = list(bars_by_listing.keys())
    series = [bars_by_listing[k] for k in listings]
    idxs = [0] * len(listings)
    last: dict[str, float] = {}
    out: list[dict[str, float]] = []
    for day in days:
        for j, listing in enumerate(listings):
            bars = series[j]
            i = idxs[j]
            n = len(bars)
            while i < n:
                t = (bars[i].t or "")[:10]
                if t and t <= day:
                    last[listing.strip().upper()] = bars[i].close
                    i += 1
                else:
                    break
            idxs[j] = i
        out.append(dict(last))
    return out


def mark_actual(hist: History, date: str, prices: dict[str, float]) -> MarkedNav:
    return mark_book(actual_state(hist, date), prices)


def mark_alt(hist: History, date: str, prices: dict[str, float]) -> MarkedNav:
    return mark_book(alt_state(hist, date), prices)


def compare_at(
    hist: History,
    date: str,
    prices: dict[str, float],
) -> dict[str, Any]:
    actual = mark_actual(hist, date, prices)
    alt = mark_alt(hist, date, prices)
    return {
        "date": date,
        "actual_nav": actual.nav,
        "alt_nav": alt.nav,
        "delta": alt.nav - actual.nav,
        "actual": actual.as_json(),
        "alt": alt.as_json(),
    }


def path_dates(
    bars_by_listing: dict[str, tuple[PriceBar, ...] | list[PriceBar]],
    fork_date: str,
    until: str,
) -> list[str]:
    fork = _day(fork_date)
    end = _day(until)
    days: set[str] = {fork, end}
    for bars in bars_by_listing.values():
        for bar in bars:
            t = (bar.t or "")[:10]
            if t and fork <= t <= end:
                days.add(t)
    return sorted(days)


def compare_path(
    hist: History,
    bars_by_listing: dict[str, tuple[PriceBar, ...] | list[PriceBar]],
    *,
    until: str | None = None,
) -> list[dict[str, Any]]:
    """NAV path as one walk: overlay once, two running books, last close ≤ day.

    Always starts at ``hist.fork_date``. Overlay alignment is the overlay's
    problem. ``compare_at`` is the single-day identity check, not this
    algorithm.
    """
    end = _day(until or utc_today())
    days = path_dates(bars_by_listing, hist.fork_date, end)
    overlay = overlay_fills(hist.seed, hist.fills)
    real = tuple(sorted(hist.real_fills(), key=_fill_order))
    alt_fills = tuple(sorted(overlay, key=_fill_order))
    actual = hist.seed
    alt = hist.seed
    i_real = 0
    i_alt = 0
    price_days = _pointer_prices(bars_by_listing, days)
    points: list[dict[str, Any]] = []
    for day, prices in zip(days, price_days):
        actual, i_real = _apply_through(actual, real, i_real, day)
        alt, i_alt = _apply_through(alt, alt_fills, i_alt, day)
        a = mark_book(actual, prices)
        b = mark_book(alt, prices)
        points.append(
            {
                "t": day,
                "actual_nav": a.nav,
                "alt_nav": b.nav,
                "delta": b.nav - a.nav,
            }
        )
    return points


def buy_universe(api: CatalogApi, *, limit: int = 200) -> list[dict[str, Any]]:
    try:
        rows = api.list_runs(latest=True, comparable_only=False, limit=limit)
    except (DbMissing, ValueError):
        return []
    out: list[dict[str, Any]] = []
    for run in rows:
        ticker = str(run.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        listing = str(run.get("quote_listing") or ticker).strip().upper()
        out.append(
            {
                "ticker": ticker,
                "run_id": run.get("run_id"),
                "session_date": run.get("session_date"),
                "session_key": run.get("session_key"),
                "audit_verdict": run.get("audit_verdict"),
                "margin_of_safety_pct": run.get("margin_of_safety_pct"),
                "decision_action": run.get("decision_action"),
                "quote_listing": listing,
                "currency": run.get("currency"),
                "fv_base": run.get("fv_base"),
            }
        )
    out.sort(key=lambda r: r["ticker"])
    return out


def resolve_buy(
    api: CatalogApi,
    hist: History,
    *,
    ticker: str,
    as_of: str,
    quantity: float | None,
    notional: float | None,
    override_price: float | None,
    get_close: Callable[[str, str], float | None],
) -> PricedFill:
    day = _day(as_of)
    sym = (ticker or "").strip().upper()
    if not sym:
        raise ReplayError("not_in_catalog", "Buy ticker is required")
    run = latest_run(api, sym, pass_only=False)
    if run is None:
        raise ReplayError("not_in_catalog", f"{sym} is not on the researched list")
    listing = str(run.get("quote_listing") or sym).strip().upper()
    ccy = str(run.get("currency") or hist.seed.base_currency or "").strip().upper()
    fx = hist.seed.fx_for(ccy)
    if fx is None:
        raise ReplayError("missing_fx", f"No statement FX for {ccy}")
    mode = "override"
    px = _num(override_price)
    if px is None:
        mode = "close"
        got = get_close(listing, day)
        px = _num(got)
    if px is None or px <= 0:
        raise ReplayError("no_close", f"No daily close for {listing} on {day}")
    qty = _qty_or_notional(quantity, notional, px)
    return PricedFill(
        as_of=day,
        side="buy",
        listing=listing,
        quantity=qty,
        fill_price=px,
        currency=ccy,
        stmt_fx=fx,
        catalog_ticker=sym,
        price_mode=mode,
    )


def resolve_sell(
    held: BookState,
    hist: History,
    *,
    listing: str,
    as_of: str,
    quantity: float | None,
    notional: float | None,
    override_price: float | None,
    get_close: Callable[[str, str], float | None],
) -> PricedFill:
    day = _day(as_of)
    key = _listing(listing)
    lot = held.lot_by_listing(key)
    if lot is None:
        raise ReplayError(
            "oversell",
            f"No holding {key} on {day}. Sell a listing from the holdings table.",
        )
    ccy = (lot.currency or hist.seed.base_currency or "").strip().upper()
    fx = lot.stmt_fx
    if fx is None:
        fx = hist.seed.fx_for(ccy)
    if fx is None:
        raise ReplayError("missing_fx", f"No statement FX for {ccy}")
    mode = "override"
    px = _num(override_price)
    if px is None:
        mode = "close"
        got = get_close(key, day)
        px = _num(got)
    if px is None or px <= 0:
        raise ReplayError("no_close", f"No daily close for {key} on {day}")
    qty = _qty_or_notional(quantity, notional, px)
    if lot.qty + _QTY_EPS < qty:
        raise ReplayError(
            "oversell",
            "Cannot sell more than the alt book holds.",
            held=lot.qty,
            quantity=qty,
            listing=key,
        )
    return PricedFill(
        as_of=day,
        side="sell",
        listing=key,
        quantity=qty,
        fill_price=px,
        currency=ccy,
        stmt_fx=fx,
        catalog_ticker=lot.catalog_ticker,
        ib_symbol=lot.ib_symbol,
        price_mode=mode,
    )


def _qty_or_notional(
    quantity: float | None,
    notional: float | None,
    fill_price: float,
) -> float:
    qty = _num(quantity)
    if qty is not None and qty > _QTY_EPS:
        return qty
    notion = _num(notional)
    if notion is not None and notion > _QTY_EPS and fill_price > 0:
        return notion / fill_price
    raise ReplayError("zero_qty", "Enter a quantity or a notional amount")


def listings_for_path(hist: History) -> list[str]:
    """Listings on the frozen seed or any fill on this history."""
    seen: set[str] = set()
    for lot in hist.seed.lots:
        if lot.listing:
            seen.add(lot.listing)
    for fill in hist.fills:
        if fill.listing:
            seen.add(fill.listing.strip().upper())
    return sorted(seen)
