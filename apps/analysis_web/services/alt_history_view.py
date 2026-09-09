"""Assemble what-if page payloads. Three views; do not call Live NAV.

PaperView      — lots and cash as of D. Replay only; no Yahoo, no path, no editor.
HoldingsView   — lots + closes + cash as of D. Never path, never cash-today.
PathView       — one NAV walk from fork; last point is header Δ.
EditorPage     — HTML: paper + cash today + universe + fills + error.
HistoryDocument — GET /{id}: identity + hyp fills. No lots, no path.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from html import escape
from typing import Any, Callable

from apps.analysis_web.services.alt_history import (
    History,
    actual_state,
    compare_path,
    listings_for_path,
    mark_alt,
    prices_on,
    state_on,
    utc_today,
)
from apps.analysis_web.services.book_state import earliest_stock_date
from apps.analysis_web.services.mark_book import MarkedNav
from apps.analysis_web.services.price_history import (
    HistoryService,
    PriceBar,
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


def load_bars(
    svc: HistoryService,
    listings: list[str],
    *,
    start: str,
    end: str,
) -> dict[str, tuple[PriceBar, ...]]:
    range_key = range_for_span(start, end)
    keys: list[str] = []
    seen: set[str] = set()
    for raw in listings:
        listing = (raw or "").strip().upper()
        if not listing or listing in seen:
            continue
        seen.add(listing)
        keys.append(listing)
    out: dict[str, tuple[PriceBar, ...]] = {}
    if not keys:
        return out

    def _one(listing: str) -> tuple[str, tuple[PriceBar, ...]]:
        hist = svc.get(listing, range_key)
        return listing, hist.bars

    workers = min(8, len(keys))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for listing, bars in pool.map(_one, keys):
            out[listing] = bars
    return out


def _span(hist: History) -> str:
    hyp = hist.hyp_fills()
    if not hyp:
        return hist.fork_date
    days = [f.as_of for f in hyp]
    return f"{min(days)} → {max(days)}"


@dataclass(frozen=True)
class PaperLot:
    """Lot on the paper book as of D. No close, no value."""

    listing: str
    qty: float
    ib_symbol: str | None = None
    catalog_ticker: str | None = None
    currency: str = ""
    deceased: bool = False


@dataclass(frozen=True)
class HoldingsLot:
    """Paper lot plus that day's mark. close is None when unquoted."""

    listing: str
    qty: float
    close: float | None
    value_base: float | None
    ib_symbol: str | None = None
    catalog_ticker: str | None = None
    currency: str = ""
    deceased: bool = False

    def as_json(self) -> dict[str, Any]:
        return {
            "listing": self.listing,
            "qty": self.qty,
            "ib_symbol": self.ib_symbol,
            "catalog_ticker": self.catalog_ticker,
            "currency": self.currency,
            "deceased": self.deceased,
            "close": self.close,
            "value_base": self.value_base,
        }


@dataclass(frozen=True)
class PaperView:
    """Paper book as of D. No path, no Δ, no Yahoo, no editor extras."""

    history: History
    view_date: str
    fork_date: str
    held: tuple[PaperLot, ...]
    cash: float | None
    caveats: tuple[str, ...]
    base_currency: str


@dataclass(frozen=True)
class HoldingsView:
    """Lots + marks + cash as of D. Not cash-today. Not the path."""

    view_date: str
    fork_date: str
    held: tuple[HoldingsLot, ...]
    cash: float | None
    base_currency: str

    def as_json(self) -> dict[str, Any]:
        return {
            "view_date": self.view_date,
            "fork_date": self.fork_date,
            "held": [lot.as_json() for lot in self.held],
            "cash": self.cash,
            "base_currency": self.base_currency,
        }


@dataclass(frozen=True)
class EditorPage:
    """HTML editor: paper book plus cash today, buy list, fills, error."""

    paper: PaperView
    cash_today: float | None
    universe: tuple[dict[str, Any], ...]
    decisions: tuple[dict[str, Any], ...]
    error: str | None
    min_date: str
    max_date: str

    @property
    def history(self) -> History:
        return self.paper.history

    @property
    def fork_date(self) -> str:
        return self.paper.fork_date

    @property
    def view_date(self) -> str:
        return self.paper.view_date

    @property
    def held(self) -> tuple[PaperLot, ...]:
        return self.paper.held

    @property
    def caveats(self) -> tuple[str, ...]:
        return self.paper.caveats

    @property
    def base_currency(self) -> str:
        return self.paper.base_currency

    @property
    def until(self) -> str:
        return self.max_date


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


def _paper_lots(hist: History, view: str, until: str) -> tuple[PaperLot, ...]:
    held = state_on(hist, view)
    today_actual_lots = {lot.listing for lot in actual_state(hist, until).lots}
    rows: list[PaperLot] = []
    for lot in held.lots:
        rows.append(
            PaperLot(
                listing=lot.listing,
                qty=lot.qty,
                ib_symbol=lot.ib_symbol,
                catalog_ticker=lot.catalog_ticker,
                currency=lot.currency,
                deceased=lot.listing not in today_actual_lots,
            )
        )
    return tuple(rows)


def _holdings_lots(
    hist: History,
    view: str,
    until: str,
    marked: MarkedNav,
) -> tuple[HoldingsLot, ...]:
    by_listing = {r.listing: r for r in marked.rows}
    rows: list[HoldingsLot] = []
    for lot in _paper_lots(hist, view, until):
        row = by_listing.get(lot.listing)
        rows.append(
            HoldingsLot(
                listing=lot.listing,
                qty=lot.qty,
                close=None if row is None else row.close,
                value_base=None if row is None else row.value_base,
                ib_symbol=lot.ib_symbol,
                catalog_ticker=lot.catalog_ticker,
                currency=lot.currency,
                deceased=lot.deceased,
            )
        )
    return tuple(rows)


def paper_on(
    hist: History,
    *,
    view_date: str | None = None,
) -> PaperView:
    """Paper book as of D. Replay only — no Yahoo, no path, no editor extras."""
    end = utc_today()
    view = _clamp_view(hist, view_date, end)
    as_of = state_on(hist, view)
    return PaperView(
        history=hist,
        view_date=view,
        fork_date=hist.fork_date,
        held=_paper_lots(hist, view, end),
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
    """HTML adapter: PaperView plus cash today. Header NAV is absent."""
    paper = paper_on(hist, view_date=view_date)
    today = utc_today()
    return EditorPage(
        paper=paper,
        cash_today=state_on(hist, today).cash_base,
        universe=tuple(universe or []),
        decisions=tuple(f.as_json() for f in hist.hyp_fills()),
        error=error,
        min_date=paper.fork_date,
        max_date=today,
    )


def holdings_on(
    hist: History,
    svc: HistoryService,
    *,
    view_date: str | None = None,
    until: str | None = None,
) -> HoldingsView:
    """Lots + closes + cash as of D. Never the NAV path. Never cash-today."""
    end = until or utc_today()
    view = _clamp_view(hist, view_date, end)
    as_of = state_on(hist, view)
    listings = [lot.listing for lot in as_of.lots if lot.listing]
    bars = load_bars(svc, listings, start=hist.fork_date, end=view)
    marked = mark_alt(hist, view, prices_on(bars, view))
    return HoldingsView(
        view_date=view,
        fork_date=hist.fork_date,
        held=_holdings_lots(hist, view, end, marked),
        cash=as_of.cash_base,
        base_currency=hist.seed.base_currency,
    )


def path_on_bars(
    hist: History,
    bars: dict[str, tuple[PriceBar, ...]],
    *,
    until: str,
) -> PathView:
    path = compare_path(hist, bars, until=until)
    last = path[-1] if path else None
    return PathView(
        fork_date=hist.fork_date,
        until=until,
        path=path,
        svg=nav_path_svg(path),
        actual_nav=None if last is None else last["actual_nav"],
        alt_nav=None if last is None else last["alt_nav"],
        delta=None if last is None else last["delta"],
        base_currency=hist.seed.base_currency,
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


