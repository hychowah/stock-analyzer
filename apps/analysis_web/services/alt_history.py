"""Priced-fill replay and POST policy for alternative histories.

Replay is a pure function on already-priced fills. Catalog allowlist and
Yahoo close-or-override happen at POST, then the fill is stored.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Iterable

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
from apps.analysis_web.services.mark_book import AsOfMark, MarkedLot, MarkedNav, mark_book
from apps.analysis_web.services.paper_account import PaperAccount
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

    @classmethod
    def from_block(cls, block: "TicketBlock", **extra: Any) -> "ReplayError":
        """POST raises the same block preview already returned."""
        merged = dict(block.extra)
        merged.update(extra)
        return cls(block.code, block.message, **merged)


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


@dataclass(frozen=True)
class CatalogSnap:
    """One latest catalog run for display and the buy allowlist.

    Stored snapshots only. Not a valuation.
    """

    ticker: str
    listing: str
    currency: str
    run_id: Any = None
    margin_of_safety_pct: float | None = None
    fv_bear: float | None = None
    fv_base: float | None = None
    audit_verdict: Any = None
    session_date: Any = None
    session_key: Any = None
    decision_action: Any = None

    def as_json(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "listing": self.listing,
            "currency": self.currency,
            "run_id": self.run_id,
            "margin_of_safety_pct": self.margin_of_safety_pct,
            "fv_bear": self.fv_bear,
            "fv_base": self.fv_base,
            "audit_verdict": self.audit_verdict,
            "session_date": self.session_date,
            "session_key": self.session_key,
            "decision_action": self.decision_action,
        }


@dataclass(frozen=True)
class TicketBlock:
    """Why confirm is dead. Preview and persist share this value."""

    code: str
    message: str
    extra: tuple[tuple[str, Any], ...] = ()

    def as_json(self) -> dict[str, Any]:
        body = {"error": self.code, "message": self.message}
        for key, val in self.extra:
            body[key] = val
        return body


@dataclass(frozen=True)
class Ticket:
    """One desk ticket. GET preview and POST persist are this value.

    Buy identity is the catalog snap. Sell identity is the held lot.
    Mark is Yahoo daily close on D (or unavailable/unquoted). Empty snap
    currency is a block, not a silent 1.0. Block is why confirm is dead.
    """

    view_date: str
    side: str
    listing: str
    ticker: str | None
    snap: CatalogSnap | None
    lot: MarkedLot | None
    mark: AsOfMark
    currency: str
    fx: float | None
    quantity: float | None
    fill_price: float | None
    price_mode: str
    cost_base: float | None
    after: PaperAccount | None
    block: TicketBlock | None
    account: PaperAccount

    def as_json(self) -> dict[str, Any]:
        return {
            "view_date": self.view_date,
            "side": self.side,
            "listing": self.listing,
            "ticker": self.ticker,
            "quantity": 0.0 if self.quantity is None else self.quantity,
            "mark": self.mark.as_json(),
            "cost_base": self.cost_base,
            "currency": self.currency,
            "account": self.account.as_json(),
            "after": None if self.after is None else self.after.as_json(),
            "held_qty": None if self.lot is None else self.lot.qty,
            "block": None if self.block is None else self.block.as_json(),
        }

    def as_fill(self) -> PricedFill:
        """Priced fill when this ticket can post. Call persist_ticket instead."""
        if self.block is not None:
            raise ReplayError.from_block(self.block)
        if (
            self.quantity is None
            or self.fill_price is None
            or self.fill_price <= 0
            or self.fx is None
        ):
            raise ReplayError("zero_qty", "Enter a quantity or a notional amount")
        lot = self.lot
        snap = self.snap
        if self.side == "sell":
            catalog_ticker = None if lot is None else lot.catalog_ticker
        else:
            catalog_ticker = None if snap is None else snap.ticker
        return PricedFill(
            as_of=self.view_date,
            side=self.side,
            listing=self.listing,
            quantity=self.quantity,
            fill_price=self.fill_price,
            currency=self.currency,
            stmt_fx=self.fx,
            catalog_ticker=catalog_ticker,
            ib_symbol=None if lot is None else lot.ib_symbol,
            price_mode=self.price_mode,
        )


def persist_ticket(ticket: Ticket) -> PricedFill:
    """POST: raise the ticket's block or return the fill."""
    if ticket.block is not None:
        extra: dict[str, Any] = {}
        if ticket.block.code == "oversell" and ticket.lot is not None:
            extra = {
                "held": ticket.lot.qty,
                "quantity": ticket.quantity,
                "listing": ticket.listing,
            }
        raise ReplayError.from_block(ticket.block, **extra)
    return ticket.as_fill()


def missing_fx_message(currency: str, base: str) -> str:
    """English block for a currency with no frozen statement rate."""
    ccy = (currency or "").strip().upper() or "this currency"
    base_ccy = (base or "").strip().upper() or "base"
    return (
        f"This paper copy has no {ccy} rate in the IB Forex map frozen at copy "
        f"(base {base_ccy}). A {ccy} name cannot be converted into {base_ccy} NAV. "
        f"Copy a new history from a statement that lists {ccy}, or pick a {base_ccy} name."
    )


def ticket_block(
    hist: History,
    *,
    side: str,
    mark_status: str,
    close: float | None,
    currency: str,
    fx: float | None,
    listing: str = "",
    view_date: str = "",
    held_qty: float | None = None,
    qty: float | None = None,
) -> TicketBlock | None:
    """Why this ticket cannot post. Preview, pickable, and POST share this."""
    kind = (side or "").strip().lower()
    key = (listing or "").strip().upper()
    day = (view_date or "").strip()[:10]
    if kind == "sell" and held_qty is None:
        if key and day:
            return TicketBlock(
                "oversell",
                f"No holding {key} on {day}. Sell a listing from the holdings table.",
            )
        return TicketBlock("oversell", "Sell a listing from the holdings table.")
    if kind == "buy" and not (currency or "").strip():
        base = (hist.seed.base_currency or "").strip().upper() or "base"
        return TicketBlock(
            "missing_currency",
            f"This researched name has no currency in the catalog, so it cannot be converted into {base} NAV.",
        )
    if fx is None:
        return TicketBlock(
            "missing_fx", missing_fx_message(currency, hist.seed.base_currency)
        )
    status = (mark_status or "").strip().lower()
    if status == "unavailable":
        if key:
            return TicketBlock("unavailable", f"No stored close for {key}.")
        return TicketBlock("unavailable", "No stored close for this listing.")
    if status != "quoted" or close is None:
        if key and day:
            return TicketBlock("no_close", f"No close for {key} on or before {day}.")
        if day:
            return TicketBlock("no_close", f"No close on or before {day}.")
        return TicketBlock("no_close", "No close on or before this date.")
    if (
        kind == "sell"
        and qty is not None
        and held_qty is not None
        and qty > held_qty + _QTY_EPS
    ):
        return TicketBlock("oversell", "Cannot sell more than the alt book holds.")
    return None


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
    ``overlay_fills`` first. What-if buys may drive cash negative —
    that cash is the loan. Copied IB buys already do. Buying-power
    math is ``assert_buyable`` at POST, not this function.

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
                raise ReplayError(
                    "missing_fx", missing_fx_message(ccy, state.base_currency)
                )
        existing = lots.get(listing)

        def _cash_delta(apply_qty: float) -> float:
            if fill.cash_effect is not None and qty > 0:
                return float(fill.cash_effect) * (apply_qty / qty)
            signed = apply_qty * px * float(fx)
            return signed if side == "sell" else -signed

        if side == "buy":
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


@dataclass(frozen=True)
class CompareWalk:
    """One actual-vs-alt walk. ``points`` is the overlay series; last marks explain Δ."""

    points: tuple[dict[str, Any], ...]
    actual: MarkedNav | None
    alt: MarkedNav | None


def walk_compare(
    hist: History,
    bars_by_listing: dict[str, tuple[PriceBar, ...] | list[PriceBar]],
    *,
    until: str | None = None,
) -> CompareWalk:
    """NAV path as one walk: overlay once, two running books, last close ≤ day.

    Always starts at ``hist.fork_date``. Overlay alignment is the overlay's
    problem. ``compare_at`` is the single-day identity check, not this
    algorithm. Last ``actual`` / ``alt`` are the marks of the last point.
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
    last_actual: MarkedNav | None = None
    last_alt: MarkedNav | None = None
    for day, prices in zip(days, price_days):
        actual, i_real = _apply_through(actual, real, i_real, day)
        alt, i_alt = _apply_through(alt, alt_fills, i_alt, day)
        a = mark_book(actual, prices)
        b = mark_book(alt, prices)
        last_actual = a
        last_alt = b
        points.append(
            {
                "t": day,
                "actual_nav": a.nav,
                "alt_nav": b.nav,
                "delta": b.nav - a.nav,
            }
        )
    return CompareWalk(points=tuple(points), actual=last_actual, alt=last_alt)


def compare_path(
    hist: History,
    bars_by_listing: dict[str, tuple[PriceBar, ...] | list[PriceBar]],
    *,
    until: str | None = None,
) -> list[dict[str, Any]]:
    """Overlay series from ``walk_compare``. Last-day marks stay on the walk."""
    return list(walk_compare(hist, bars_by_listing, until=until).points)


def snap_for(
    snaps: tuple[CatalogSnap, ...] | list[CatalogSnap],
    *,
    ticker: str = "",
    listing: str = "",
) -> CatalogSnap | None:
    """Allowlist lookup: ticker or listing against the desk projection."""
    want_t = (ticker or "").strip().upper()
    want_l = (listing or "").strip().upper()
    if not want_t and not want_l:
        return None
    for snap in snaps:
        if want_t and (snap.ticker == want_t or snap.listing == want_t):
            return snap
        if want_l and (snap.listing == want_l or snap.ticker == want_l):
            return snap
    return None


def catalog_snaps(api: CatalogApi, *, limit: int = 200) -> tuple[CatalogSnap, ...]:
    """Latest catalog runs as one projection. Same object for the list and holdings join."""
    try:
        rows = api.list_runs(latest=True, comparable_only=False, limit=limit)
    except (DbMissing, ValueError):
        return ()
    out: list[CatalogSnap] = []
    for run in rows:
        ticker = str(run.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        listing = str(run.get("quote_listing") or ticker).strip().upper()
        out.append(
            CatalogSnap(
                ticker=ticker,
                listing=listing,
                currency=str(run.get("currency") or "").strip().upper(),
                run_id=run.get("run_id"),
                margin_of_safety_pct=_num(run.get("margin_of_safety_pct")),
                fv_bear=_num(run.get("fv_bear")),
                fv_base=_num(run.get("fv_base")),
                audit_verdict=run.get("audit_verdict"),
                session_date=run.get("session_date"),
                session_key=run.get("session_key"),
                decision_action=run.get("decision_action"),
            )
        )
    out.sort(key=lambda r: r.ticker)
    return tuple(out)


def qty_or_notional(
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
