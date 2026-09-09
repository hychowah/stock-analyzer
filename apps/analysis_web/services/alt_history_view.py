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
from typing import Any, Callable

from apps.analysis_web.services.alt_history import (
    History,
    actual_state,
    listings_for_path,
    state_on,
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
from apps.analysis_web.services.signed_bars import signed_bar_rows
from apps.analysis_web.services.paper_account import (
    PaperAccount,
    paper_account,
    preview_buy,
    preview_sell,
)
from apps.analysis_web.services.price_history import (
    HistoryService,
    PriceBar,
    PriceHistory,
    close_on,
    range_for_span,
)


def close_getter(
    svc: HistoryService,
    *,
    start: str,
    end: str | None = None,
) -> Callable[[str, str], float | None]:
    until = end or utc_today()
    range_key = range_for_span(start, until)

    def get_close(listing: str, date: str) -> float | None:
        hist = svc.get(listing, range_key)
        bar = close_on(hist.bars, date)
        return None if bar is None else bar.close

    return get_close


def load_histories(
    svc: HistoryService,
    listings: list[str],
    *,
    start: str,
    end: str,
) -> dict[str, PriceHistory]:
    """One PriceHistory per listing, including series with error set."""
    range_key = range_for_span(start, end)
    keys: list[str] = []
    seen: set[str] = set()
    for raw in listings:
        listing = (raw or "").strip().upper()
        if not listing or listing in seen:
            continue
        seen.add(listing)
        keys.append(listing)
    if not keys:
        return {}
    return svc.get_many(keys, range_key)


def load_bars(
    svc: HistoryService,
    listings: list[str],
    *,
    start: str,
    end: str,
) -> dict[str, tuple[PriceBar, ...]]:
    return {k: v.bars for k, v in load_histories(svc, listings, start=start, end=end).items()}


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
class BuyCandidate:
    """Catalog name plus close on D. Not pickable unless quoted with FX."""

    ticker: str
    listing: str
    mark: AsOfMark
    audit_verdict: str | None
    margin_of_safety_pct: float | None
    session_date: str | None
    currency: str
    pickable: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "listing": self.listing,
            "mark": self.mark.as_json(),
            "audit_verdict": self.audit_verdict,
            "margin_of_safety_pct": self.margin_of_safety_pct,
            "session_date": self.session_date,
            "currency": self.currency,
            "pickable": self.pickable,
        }


@dataclass(frozen=True)
class EditorPage:
    """HTML editor: History plus the D book, cash today, and sold-later."""

    history: History
    paper: PaperView
    cash_today: float | None
    universe: tuple[dict[str, Any], ...]
    decisions: tuple[dict[str, Any], ...]
    error: str | None
    min_date: str
    max_date: str
    sold_later: frozenset[str]


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
    svc: HistoryService,
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
    bars = load_bars(svc, sorted(listings), start=start, end=end)
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


def editor_page(
    hist: History,
    *,
    view_date: str | None = None,
    universe: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> EditorPage:
    """HTML adapter: History plus the D book and cash today. Header NAV is absent."""
    paper = paper_on(hist, view_date=view_date)
    today = utc_today()
    return EditorPage(
        history=hist,
        paper=paper,
        cash_today=state_on(hist, today).cash_base,
        universe=tuple(universe or []),
        decisions=tuple(f.as_json() for f in hist.hyp_fills()),
        error=error,
        min_date=paper.fork_date,
        max_date=today,
        sold_later=sold_later_listings(hist, paper.view_date),
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
    svc: HistoryService,
    *,
    view_date: str | None = None,
) -> AsOfAccount:
    """state_on + marks for held listings (fork→D) + mark_lots + paper_account.

    Does not load the buy universe. Does not call paper_on.
    """
    view = _clamp_view(hist, view_date, utc_today())
    as_of = state_on(hist, view)
    listings = [lot.listing for lot in as_of.lots if lot.listing]
    histories = load_histories(svc, listings, start=hist.fork_date, end=view)
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
    svc: HistoryService,
    listing: str,
    *,
    view_date: str,
) -> AsOfMark:
    """One listing's close on D. Cache-hot when the as-of pane already loaded D."""
    key = (listing or "").strip().upper()
    day = _clamp_view(hist, view_date, utc_today())
    if not key:
        return _missing_mark("", day)
    histories = load_histories(svc, [key], start=hist.fork_date, end=day)
    series = histories.get(key)
    if series is None:
        return _missing_mark(key, day)
    return mark_on(series, day)


def universe_on(
    hist: History,
    svc: HistoryService,
    universe: list[dict[str, Any]],
    *,
    view_date: str | None = None,
) -> tuple[BuyCandidate, ...]:
    """Catalog rows plus AsOfMark on quote_listing. Second fetch vs account_on."""
    view = _clamp_view(hist, view_date, utc_today())
    listings: list[str] = []
    for row in universe:
        listing = str(row.get("quote_listing") or row.get("ticker") or "").strip().upper()
        if listing:
            listings.append(listing)
    histories = load_histories(svc, listings, start=hist.fork_date, end=view)
    out: list[BuyCandidate] = []
    for row in universe:
        ticker = str(row.get("ticker") or "").strip().upper()
        listing = str(row.get("quote_listing") or ticker).strip().upper()
        ccy = str(row.get("currency") or hist.seed.base_currency or "").strip().upper()
        series = histories.get(listing)
        mark = mark_on(series, view) if series is not None else _missing_mark(listing, view)
        fx = hist.seed.fx_for(ccy)
        pickable = mark.status == "quoted" and mark.close is not None and fx is not None
        out.append(
            BuyCandidate(
                ticker=ticker,
                listing=listing,
                mark=mark,
                audit_verdict=row.get("audit_verdict"),
                margin_of_safety_pct=row.get("margin_of_safety_pct"),
                session_date=row.get("session_date"),
                currency=ccy,
                pickable=pickable,
            )
        )
    return tuple(out)


def ticket_on(
    hist: History,
    svc: HistoryService,
    *,
    view_date: str | None,
    side: str,
    listing: str,
    ticker: str | None = None,
    quantity: float | None = None,
    currency: str | None = None,
) -> dict[str, Any]:
    """Preview a buy or sell at the shown close. POST still re-resolves."""
    asof = account_on(hist, svc, view_date=view_date)
    day = asof.view_date
    kind = (side or "").strip().lower()
    key = (listing or ticker or "").strip().upper()
    mark = mark_listing(hist, svc, key, view_date=day)
    qty = 0.0 if quantity is None else float(quantity)
    held = next((lot for lot in asof.held if lot.listing == key), None)
    ccy = ""
    fx: float | None = None
    if held is not None:
        ccy = (held.currency or "").strip().upper()
        fx = held.stmt_fx
        if fx is None:
            fx = hist.seed.fx_for(ccy)
    else:
        ccy = (currency or "").strip().upper()
        if not ccy:
            ccy = (hist.seed.base_currency or "").strip().upper()
        fx = hist.seed.fx_for(ccy)
    cost: float | None = None
    if mark.status == "quoted" and mark.close is not None and fx is not None and qty > 0:
        cost = qty * float(mark.close) * float(fx)
    after: PaperAccount | None = None
    if cost is not None:
        if kind == "buy":
            after = preview_buy(asof.account, cost)
        elif kind == "sell":
            after = preview_sell(asof.account, cost)
    return {
        "view_date": day,
        "side": kind,
        "listing": key,
        "ticker": (ticker or "").strip().upper() or None,
        "quantity": qty,
        "mark": mark.as_json(),
        "cost_base": cost,
        "currency": ccy,
        "account": asof.account.as_json(),
        "after": None if after is None else after.as_json(),
        "held_qty": None if held is None else held.qty,
    }


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
    svc: HistoryService,
    *,
    until: str | None = None,
) -> PathView:
    """NAV walk from fork. Last point is header Δ. No holdings table."""
    end = until or utc_today()
    listings = listings_for_path(hist)
    bars = load_bars(svc, listings, start=hist.fork_date, end=end)
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
