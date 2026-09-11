"""Assemble what-if page payloads. Three views; do not call Live NAV.

PaperView      — lots and cash as of D. Replay only; no Yahoo, no path, no History.
AsOfAccount    — marked lots plus PaperAccount as of D. Never path, never cash-today.
PathView       — one NAV walk from fork; last point is header Δ.
EditorPage     — HTML: History + paper + cash today + sold-later + universe + fills.
HistoryDocument — GET /{id}: identity + hyp fills. No lots, no path.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

from apps.analysis_web.services.alt_history import (
    CatalogSnap,
    History,
    ReplayError,
    Ticket,
    TicketBlock,
    actual_state,
    listings_for_path,
    qty_or_notional,
    snap_for,
    state_on,
    ticket_block,
    utc_today,
    walk_compare,
)
from apps.analysis_web.services.book_state import BookState, earliest_stock_date
from apps.analysis_web.services.mark_book import (
    AsOfMark,
    MarkedLot,
    mark_lots,
    mark_on,
    marks_on,
    nav_delta_rows,
)
from apps.analysis_web.services.portfolio import catalog_lookup_tickers
from apps.analysis_web.services.signed_bars import signed_bar_rows
from apps.analysis_web.services.paper_account import (
    FundingError,
    PaperAccount,
    assert_buyable,
    paper_account,
    preview_buy,
    preview_sell,
)
from apps.analysis_web.templating import downside_pct
from apps.analysis_web.services.daily_closes import DailyCloses
from apps.analysis_web.services.price_history import (
    PriceBar,
)


def _span(hist: History) -> str:
    hyp = hist.hyp_fills()
    if not hyp:
        return hist.fork_date
    days = [f.as_of for f in hyp]
    return f"{min(days)} → {max(days)}"


@dataclass(frozen=True)
class PaperLot:
    """Lot on the paper book as of D. No close, no value, no sold-later."""

    listing: str
    qty: float
    ib_symbol: str | None = None
    catalog_ticker: str | None = None
    currency: str = ""


@dataclass(frozen=True)
class PaperView:
    """Paper book as of D. No History, no path, no Yahoo, no sold-later."""

    view_date: str
    fork_date: str
    held: tuple[PaperLot, ...]
    cash: float | None
    caveats: tuple[str, ...]
    base_currency: str


@dataclass(frozen=True)
class AsOfAccount:
    """Paper account on D: marked lots plus PaperAccount.

    Not cash-today. Not the path. HTML first paint is not this type.
    """

    view_date: str
    fork_date: str
    held: tuple[MarkedLot, ...]
    account: PaperAccount
    base_currency: str

    def as_json(self) -> dict[str, Any]:
        return {
            "view_date": self.view_date,
            "fork_date": self.fork_date,
            "held": [lot.as_json() for lot in self.held],
            "account": self.account.as_json(),
            "base_currency": self.base_currency,
        }


@dataclass(frozen=True)
class HoldingRow:
    """Display math on a marked lot.

    Weight is of quoted stock, not NAV. Downside is the close on this
    row versus stored bear FV. MoS is the stored snapshot. Not a
    valuation. Not Live NAV.
    """

    lot: MarkedLot
    weight_pct: float | None
    snap: CatalogSnap | None
    downside_pct: float | None


@dataclass(frozen=True)
class BuyCandidate:
    """Desk row: catalog snap plus close on D. Same composition as HoldingRow."""

    snap: CatalogSnap
    mark: AsOfMark
    block: TicketBlock | None = None

    @property
    def pickable(self) -> bool:
        return self.block is None

    def as_json(self) -> dict[str, Any]:
        body = self.snap.as_json()
        body["mark"] = self.mark.as_json()
        body["pickable"] = self.pickable
        body["block"] = None if self.block is None else self.block.as_json()
        return body


@dataclass(frozen=True)
class EditorPage:
    """HTML editor: History plus the D book, cash today, and sold-later."""

    history: History
    paper: PaperView
    cash_today: float | None
    universe: tuple[CatalogSnap, ...]
    decisions: tuple[dict[str, Any], ...]
    error: str | None
    min_date: str
    max_date: str
    sold_later: frozenset[str]
    holdings: tuple[HoldingRow, ...] = ()


@dataclass(frozen=True)
class HistoryDocument:
    """GET /{id}: identity + hyp fills. No lots, no path, no Yahoo."""

    id: int | None
    name: str
    notes: str
    fork_date: str
    fills: tuple[dict[str, Any], ...]
    base_currency: str

    def as_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "notes": self.notes,
            "fork_date": self.fork_date,
            "decisions": list(self.fills),
            "base_currency": self.base_currency,
        }


@dataclass(frozen=True)
class PathView:
    """NAV walk from fork. Last point is header Δ. No lots."""

    fork_date: str
    until: str
    path: list[dict[str, Any]]
    svg: str
    actual_nav: float | None
    alt_nav: float | None
    delta: float | None
    base_currency: str
    breakdown: tuple[dict[str, Any], ...] = ()

    def as_json(self) -> dict[str, Any]:
        return {
            "fork_date": self.fork_date,
            "until": self.until,
            "base_currency": self.base_currency,
            "actual_nav": self.actual_nav,
            "alt_nav": self.alt_nav,
            "delta": self.delta,
            "path": self.path,
            "svg": self.svg,
            "breakdown": list(self.breakdown),
        }


def card_for(
    hist: History,
    bars: dict[str, tuple[PriceBar, ...]],
    *,
    until: str,
) -> dict[str, Any]:
    fork = hist.fork_date
    walked = path_on_bars(hist, bars, until=until)
    return {
        "id": hist.id,
        "name": hist.name,
        "notes": hist.notes,
        "fork_date": fork,
        "n_decisions": len(hist.hyp_fills()),
        "date_span": _span(hist),
        "actual_nav": walked.actual_nav,
        "alt_nav": walked.alt_nav,
        "delta": walked.delta,
        "path": walked.path,
        "svg": walked.svg,
    }


def list_payload(
    histories: list[History],
    svc: DailyCloses,
    *,
    until: str | None = None,
) -> dict[str, Any]:
    end = until or utc_today()
    listings: set[str] = set()
    forks: list[str] = []
    for hist in histories:
        forks.append(hist.fork_date)
        listings.update(listings_for_path(hist))
    start = min(forks) if forks else end
    bars = {k: v.bars for k, v in svc.series(sorted(listings)).items()}
    cards = [card_for(hist, bars, until=end) for hist in histories]
    overlay = None
    if len(cards) >= 2:
        overlay = overlay_svg_from_cards(cards, start, end)
    base = ""
    if histories:
        base = histories[0].seed.base_currency
    return {
        "cards": cards,
        "until": end,
        "overlay_svg": overlay,
        "max_date": end,
        "base_currency": base,
    }


def _clamp_view(hist: History, view_date: str | None, until: str) -> str:
    view = (view_date or until).strip()[:10] or until
    if view < hist.fork_date:
        view = hist.fork_date
    if view > until:
        view = until
    return view


def _paper_lots(state: BookState) -> tuple[PaperLot, ...]:
    rows: list[PaperLot] = []
    for lot in state.lots:
        rows.append(
            PaperLot(
                listing=lot.listing,
                qty=lot.qty,
                ib_symbol=lot.ib_symbol,
                catalog_ticker=lot.catalog_ticker,
                currency=lot.currency,
            )
        )
    return tuple(rows)


def sold_later_listings(hist: History, view: str) -> frozenset[str]:
    """Listings in the D book that are absent from this copy’s actual today."""
    paper = {lot.listing for lot in state_on(hist, view).lots if lot.listing}
    today = {lot.listing for lot in actual_state(hist, utc_today()).lots if lot.listing}
    return frozenset(paper - today)


def paper_on(
    hist: History,
    *,
    view_date: str | None = None,
) -> PaperView:
    """Paper book as of D. Replay only — no Yahoo, no path, no History."""
    end = utc_today()
    view = _clamp_view(hist, view_date, end)
    as_of = state_on(hist, view)
    return PaperView(
        view_date=view,
        fork_date=hist.fork_date,
        held=_paper_lots(as_of),
        cash=as_of.cash_base,
        caveats=as_of.caveats,
        base_currency=hist.seed.base_currency,
    )


def _snap_for_lot(
    lot: MarkedLot,
    by_key: dict[str, CatalogSnap],
) -> CatalogSnap | None:
    """Join a holding to a catalog snap. Overlay is catalog-only, not the mark listing."""
    seen: list[str] = []

    def add(raw: str | None) -> None:
        key = (raw or "").strip().upper()
        if key and key not in seen:
            seen.append(key)

    add(lot.catalog_ticker)
    add(lot.listing)
    add(lot.ib_symbol)
    for cand in catalog_lookup_tickers(lot.ib_symbol or ""):
        add(cand)
    for cand in catalog_lookup_tickers(lot.listing or ""):
        add(cand)
    for key in seen:
        snap = by_key.get(key)
        if snap is not None:
            return snap
    return None


def _snap_index(snaps: tuple[CatalogSnap, ...] | list[CatalogSnap]) -> dict[str, CatalogSnap]:
    by_key: dict[str, CatalogSnap] = {}
    for snap in snaps:
        by_key[snap.ticker] = snap
        if snap.listing and snap.listing not in by_key:
            by_key[snap.listing] = snap
    return by_key


def pending_holding_rows(paper: PaperView) -> tuple[HoldingRow, ...]:
    """First-paint rows: paper lots, extra columns pending until the fragment."""
    rows: list[HoldingRow] = []
    for lot in paper.held:
        marked = MarkedLot(
            listing=lot.listing,
            qty=lot.qty,
            close=None,
            value_base=None,
            error=None,
            ib_symbol=lot.ib_symbol,
            catalog_ticker=lot.catalog_ticker,
            currency=lot.currency,
        )
        rows.append(
            HoldingRow(lot=marked, weight_pct=None, snap=None, downside_pct=None)
        )
    return tuple(rows)


def holding_rows(
    account: AsOfAccount,
    snaps: tuple[CatalogSnap, ...] | list[CatalogSnap],
) -> tuple[HoldingRow, ...]:
    """Holdings-table rows: marked lots plus weight, stored MoS, Downside vs close."""
    by_key = _snap_index(snaps)
    stock = float(account.account.stock or 0)
    rows: list[HoldingRow] = []
    for lot in account.held:
        snap = _snap_for_lot(lot, by_key)
        weight: float | None = None
        if lot.value_base is not None and stock > 0:
            weight = 100.0 * float(lot.value_base) / stock
        down = None
        if snap is not None:
            down = downside_pct(lot.close, snap.fv_bear)
        rows.append(
            HoldingRow(
                lot=lot,
                weight_pct=weight,
                snap=snap,
                downside_pct=down,
            )
        )
    return tuple(rows)


def editor_page(
    hist: History,
    *,
    view_date: str | None = None,
    universe: tuple[CatalogSnap, ...] | list[CatalogSnap] | None = None,
    error: str | None = None,
) -> EditorPage:
    """HTML adapter: History plus the D book and cash today. Header NAV is absent."""
    paper = paper_on(hist, view_date=view_date)
    today = utc_today()
    return EditorPage(
        history=hist,
        paper=paper,
        cash_today=state_on(hist, today).cash_base,
        universe=tuple(universe or ()),
        decisions=tuple(f.as_json() for f in hist.hyp_fills()),
        error=error,
        min_date=paper.fork_date,
        max_date=today,
        sold_later=sold_later_listings(hist, paper.view_date),
        holdings=pending_holding_rows(paper),
    )


def _missing_mark(listing: str, day: str) -> AsOfMark:
    return AsOfMark(
        listing=listing,
        as_of=day,
        status="unavailable",
        error="unavailable",
    )


def account_on(
    hist: History,
    svc: DailyCloses,
    *,
    view_date: str | None = None,
) -> AsOfAccount:
    """state_on + marks for held listings (fork→D) + mark_lots + paper_account.

    Does not load catalog snaps. Does not call paper_on.
    """
    view = _clamp_view(hist, view_date, utc_today())
    as_of = state_on(hist, view)
    listings = [lot.listing for lot in as_of.lots if lot.listing]
    histories = svc.series(listings)
    marks = marks_on(histories, view)
    for listing in listings:
        key = listing.strip().upper()
        if key not in marks:
            marks[key] = _missing_mark(key, view)
    marked = mark_lots(as_of, marks)
    acct = paper_account(marked, base_currency=hist.seed.base_currency)
    return AsOfAccount(
        view_date=view,
        fork_date=hist.fork_date,
        held=marked.rows,
        account=acct,
        base_currency=hist.seed.base_currency,
    )


def mark_listing(
    hist: History,
    svc: DailyCloses,
    listing: str,
    *,
    view_date: str,
) -> AsOfMark:
    """One listing's close on D. Disk read of DailyCloses.series."""
    key = (listing or "").strip().upper()
    day = _clamp_view(hist, view_date, utc_today())
    if not key:
        return _missing_mark("", day)
    histories = svc.series([key])
    series = histories.get(key)
    if series is None:
        return _missing_mark(key, day)
    return mark_on(series, day)


def universe_on(
    hist: History,
    svc: DailyCloses,
    snaps: tuple[CatalogSnap, ...] | list[CatalogSnap],
    *,
    view_date: str | None = None,
) -> tuple[BuyCandidate, ...]:
    """Catalog snaps plus AsOfMark on listing. Second fetch vs account_on."""
    view = _clamp_view(hist, view_date, utc_today())
    listings = [snap.listing for snap in snaps if snap.listing]
    histories = svc.series(listings)
    out: list[BuyCandidate] = []
    for snap in snaps:
        listing = snap.listing or snap.ticker
        ccy = (snap.currency or "").strip().upper()
        series = histories.get(listing)
        mark = mark_on(series, view) if series is not None else _missing_mark(listing, view)
        fx = hist.seed.fx_for(ccy) if ccy else None
        block = ticket_block(
            hist,
            side="buy",
            mark_status=mark.status,
            close=mark.close,
            currency=ccy,
            fx=fx,
            listing=listing,
            view_date=view,
        )
        out.append(BuyCandidate(snap=snap, mark=mark, block=block))
    return tuple(out)


def ticket_listing(
    *,
    side: str,
    listing: str,
    ticker: str | None,
    snaps: tuple[CatalogSnap, ...] | list[CatalogSnap],
) -> tuple[str, CatalogSnap | None]:
    """Resolve the mark listing and buy snap for a ticket."""
    kind = (side or "").strip().lower()
    snap = snap_for(snaps, ticker=ticker or "", listing=listing)
    if kind == "buy" and snap is not None:
        return (snap.listing or snap.ticker), snap
    key = (listing or ticker or (snap.listing if snap else "") or "").strip().upper()
    return key, snap


def build_ticket(
    hist: History,
    *,
    account: PaperAccount,
    held: tuple[MarkedLot, ...],
    side: str,
    view_date: str,
    mark: AsOfMark,
    snaps: tuple[CatalogSnap, ...] | list[CatalogSnap] = (),
    listing: str = "",
    ticker: str | None = None,
    quantity: float | None = None,
    notional: float | None = None,
    override_price: float | None = None,
) -> Ticket:
    """Preview and persist are this value. POST calls persist_ticket on it."""
    kind = (side or "").strip().lower()
    key, snap = ticket_listing(side=kind, listing=listing, ticker=ticker, snaps=snaps)
    if key and mark.listing and mark.listing != key:
        mark = AsOfMark(
            listing=key,
            as_of=mark.as_of,
            status=mark.status,
            close=mark.close,
            bar_date=mark.bar_date,
            error=mark.error,
        )
    lot = next((row for row in held if row.listing == key), None)
    ticker_out = (ticker or (snap.ticker if snap else "") or "").strip().upper() or None
    block: TicketBlock | None = None
    ccy = ""
    fx: float | None = None
    if kind == "buy":
        sym = (ticker_out or key)
        if not sym:
            block = TicketBlock("not_in_catalog", "Buy ticker is required")
        elif snap is None:
            block = TicketBlock("not_in_catalog", f"{sym} is not on the researched list")
        else:
            ccy = (snap.currency or "").strip().upper()
            fx = hist.seed.fx_for(ccy) if ccy else None
    else:
        if lot is not None:
            ccy = (lot.currency or hist.seed.base_currency or "").strip().upper()
            fx = lot.stmt_fx
            if fx is None:
                fx = hist.seed.fx_for(ccy)
    override = None if override_price is None else float(override_price)
    if override is not None and override <= 0:
        override = None
    mode = "override" if override is not None else "close"
    fill_px = override if override is not None else mark.close
    status = "quoted" if override is not None else mark.status
    close_for_block = fill_px if override is not None else mark.close
    qty: float | None = None
    if fill_px is not None and fill_px > 0 and (quantity is not None or notional is not None):
        try:
            qty = qty_or_notional(quantity, notional, fill_px)
        except ReplayError:
            qty = None
    if block is None:
        block = ticket_block(
            hist,
            side=kind,
            mark_status=status,
            close=close_for_block,
            currency=ccy,
            fx=fx,
            listing=key,
            view_date=view_date,
            held_qty=None if lot is None else lot.qty,
            qty=qty,
        )
    cost: float | None = None
    if (
        block is None
        and fill_px is not None
        and fx is not None
        and qty is not None
        and qty > 0
    ):
        cost = qty * float(fill_px) * float(fx)
    after: PaperAccount | None = None
    if cost is not None:
        if kind == "buy":
            after = preview_buy(account, cost)
            try:
                assert_buyable(account, cost)
            except FundingError as e:
                block = TicketBlock(
                    e.code,
                    e.message,
                    extra=(
                        ("need", e.need),
                        ("buying_power", e.buying_power),
                        ("excess_after", e.excess_after),
                    ),
                )
                after = None
        elif kind == "sell":
            after = preview_sell(account, cost)
    return Ticket(
        view_date=view_date,
        side=kind,
        listing=key,
        ticker=ticker_out,
        snap=snap,
        lot=lot,
        mark=mark,
        currency=ccy,
        fx=fx,
        quantity=qty,
        fill_price=fill_px,
        price_mode=mode,
        cost_base=cost,
        after=after,
        block=block,
        account=account,
    )


def ticket_on(
    hist: History,
    svc: DailyCloses,
    *,
    view_date: str | None,
    side: str,
    listing: str,
    ticker: str | None = None,
    quantity: float | None = None,
    snaps: tuple[CatalogSnap, ...] | list[CatalogSnap] = (),
) -> dict[str, Any]:
    """GET /ticket: the same Ticket POST will persist."""
    asof = account_on(hist, svc, view_date=view_date)
    key, _snap = ticket_listing(
        side=side, listing=listing, ticker=ticker, snaps=snaps
    )
    mark = mark_listing(hist, svc, key, view_date=asof.view_date)
    return build_ticket(
        hist,
        account=asof.account,
        held=asof.held,
        side=side,
        view_date=asof.view_date,
        mark=mark,
        snaps=snaps,
        listing=listing,
        ticker=ticker,
        quantity=quantity,
    ).as_json()


def path_on_bars(
    hist: History,
    bars: dict[str, tuple[PriceBar, ...]],
    *,
    until: str,
) -> PathView:
    walked = walk_compare(hist, bars, until=until)
    path = list(walked.points)
    last = path[-1] if path else None
    pairs: tuple[tuple[str, float], ...] = ()
    if walked.actual is not None and walked.alt is not None:
        pairs = nav_delta_rows(walked.actual, walked.alt)
    return PathView(
        fork_date=hist.fork_date,
        until=until,
        path=path,
        svg=nav_path_svg(path),
        actual_nav=None if last is None else last["actual_nav"],
        alt_nav=None if last is None else last["alt_nav"],
        delta=None if last is None else last["delta"],
        base_currency=hist.seed.base_currency,
        breakdown=tuple(signed_bar_rows(pairs)),
    )


def path_on(
    hist: History,
    svc: DailyCloses,
    *,
    until: str | None = None,
) -> PathView:
    """NAV walk from fork. Last point is header Δ. No holdings table."""
    end = until or utc_today()
    listings = listings_for_path(hist)
    bars = {k: v.bars for k, v in svc.series(listings).items()}
    return path_on_bars(hist, bars, until=end)


def history_document(hist: History) -> HistoryDocument:
    """Identity + fills. No Yahoo, no lots, no path."""
    return HistoryDocument(
        id=hist.id,
        name=hist.name,
        notes=hist.notes,
        fork_date=hist.fork_date,
        fills=tuple(f.as_json() for f in hist.hyp_fills()),
        base_currency=hist.seed.base_currency,
    )


def _domain(vals: list[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 1.0
    lo = min(vals)
    hi = max(vals)
    if hi == lo:
        pad = abs(lo) * 0.05 or 1.0
        return lo - pad, hi + pad
    pad = (hi - lo) * 0.08
    return lo - pad, hi + pad


def nav_path_svg(points: list[dict[str, Any]], *, width: int = 640, height: int = 160) -> str:
    if len(points) < 2:
        return ""
    vals = [
        float(p[k])
        for p in points
        for k in ("actual_nav", "alt_nav")
        if p.get(k) is not None
    ]
    ymin, ymax = _domain(vals)
    pad_l, pad_r, pad_t, pad_b = 8, 8, 8, 8
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)
    n = len(points)

    def xy(i: int, value: float) -> str:
        x = pad_l + (inner_w * i / (n - 1))
        y = pad_t + inner_h * (1 - (value - ymin) / (ymax - ymin))
        return f"{x:.1f},{y:.1f}"

    actual = " ".join(xy(i, float(p["actual_nav"])) for i, p in enumerate(points))
    alt = " ".join(xy(i, float(p["alt_nav"])) for i, p in enumerate(points))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" class="nav-chart-svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" role="img" '
        f'aria-label="Actual versus this history, daily close">'
        f'<polyline class="nav-path-actual" fill="none" points="{actual}"/>'
        f'<polyline class="nav-path-alt" fill="none" points="{alt}"/>'
        f"</svg>"
    )


def overlay_svg_from_cards(
    cards: list[dict[str, Any]],
    start: str,
    end: str,
    *,
    width: int = 640,
    height: int = 180,
) -> str:
    if len(cards) < 2:
        return ""
    by_t: list[dict[str, dict[str, Any]]] = []
    days: set[str] = set()
    for card in cards:
        lookup: dict[str, dict[str, Any]] = {}
        for pt in card.get("path") or []:
            t = str(pt.get("t") or "")[:10]
            if t:
                lookup[t] = pt
                days.add(t)
        by_t.append(lookup)
    ordered = [d for d in sorted(days) if start <= d <= end]
    if len(ordered) < 2:
        return ""
    actual_pts: list[float] = []
    series: list[list[float]] = []
    for t in ordered:
        row = by_t[0].get(t)
        actual_pts.append(0.0 if row is None else float(row["actual_nav"]))
    for lookup in by_t:
        line: list[float] = []
        for t in ordered:
            row = lookup.get(t)
            line.append(0.0 if row is None else float(row["alt_nav"]))
        series.append(line)
    vals = actual_pts + [v for line in series for v in line]
    ymin, ymax = _domain(vals)
    pad_l, pad_r, pad_t, pad_b = 8, 8, 8, 8
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)
    n = len(ordered)

    def xy(i: int, value: float) -> str:
        x = pad_l + (inner_w * i / (n - 1))
        y = pad_t + inner_h * (1 - (value - ymin) / (ymax - ymin))
        return f"{x:.1f},{y:.1f}"

    actual = " ".join(xy(i, v) for i, v in enumerate(actual_pts))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" class="nav-chart-svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" role="img" '
        f'aria-label="Actual versus alternative histories, daily close">',
        f'<polyline class="nav-path-actual" fill="none" points="{actual}"/>',
    ]
    for i, line in enumerate(series):
        pts = " ".join(xy(j, v) for j, v in enumerate(line))
        cls = f"nav-path-alt nav-path-h{i % 6}"
        name = escape(str(cards[i].get("name") or f"History {i + 1}"))
        parts.append(
            f'<polyline class="{cls}" fill="none" points="{pts}">'
            f"<title>{name}</title></polyline>"
        )
    parts.append("</svg>")
    return "".join(parts)
