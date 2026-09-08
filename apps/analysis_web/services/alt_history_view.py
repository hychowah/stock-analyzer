"""Assemble what-if page payloads. Three views; do not call Live NAV.

paper_on      — lots / cash / deceased. Replay only; no Yahoo.
holdings_payload — paper plus that day's closes.
path_payload  — one NAV walk; last point is header Δ.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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


def card_for(
    hist: History,
    bars: dict[str, tuple[PriceBar, ...]],
    *,
    until: str,
    since: str | None = None,
) -> dict[str, Any]:
    fork = hist.fork_date
    path = compare_path(hist, bars, until=until, since=since)
    last = path[-1] if path else None
    return {
        "id": hist.id,
        "name": hist.name,
        "notes": hist.notes,
        "fork_date": fork,
        "n_decisions": len(hist.hyp_fills()),
        "date_span": _span(hist),
        "actual_nav": None if last is None else last["actual_nav"],
        "alt_nav": None if last is None else last["alt_nav"],
        "delta": None if last is None else last["delta"],
        "path": path,
        "svg": nav_path_svg(path),
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
    cards = [card_for(hist, bars, until=end, since=start) for hist in histories]
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


def _held_rows(
    hist: History,
    view: str,
    until: str,
    marked: MarkedNav | None = None,
) -> list[dict[str, Any]]:
    held = state_on(hist, view)
    today_actual_lots = {lot.listing for lot in actual_state(hist, until).lots}
    by_listing = {} if marked is None else {r.listing: r for r in marked.rows}
    rows: list[dict[str, Any]] = []
    for lot in held.lots:
        row = by_listing.get(lot.listing)
        rows.append(
            {
                "listing": lot.listing,
                "ib_symbol": lot.ib_symbol,
                "catalog_ticker": lot.catalog_ticker,
                "qty": lot.qty,
                "currency": lot.currency,
                "close": None if row is None else row.close,
                "value_base": None if row is None else row.value_base,
                "deceased": lot.listing not in today_actual_lots,
            }
        )
    return rows


def paper_on(
    hist: History,
    *,
    view_date: str | None = None,
    until: str | None = None,
    universe: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Paper book as of D. Replay only — no Yahoo, no path."""
    end = until or utc_today()
    view = _clamp_view(hist, view_date, end)
    today_book = state_on(hist, end)
    return {
        "history": hist,
        "fork_date": hist.fork_date,
        "view_date": view,
        "until": end,
        "min_date": hist.fork_date,
        "max_date": end,
        "base_currency": hist.seed.base_currency,
        "caveats": today_book.caveats,
        "cash": today_book.cash_base,
        "held": _held_rows(hist, view, end),
        "universe": universe or [],
        "decisions": [f.as_json() for f in hist.hyp_fills()],
        "actual_nav": None,
        "alt_nav": None,
        "delta": None,
        "path": [],
        "svg": "",
        "error": error,
    }


def holdings_payload(
    hist: History,
    svc: HistoryService,
    *,
    view_date: str | None = None,
    until: str | None = None,
) -> dict[str, Any]:
    """Paper as of D plus that day's closes. Never the NAV path."""
    paper = paper_on(hist, view_date=view_date, until=until)
    view = paper["view_date"]
    end = paper["until"]
    listings = [str(row["listing"]) for row in paper["held"] if row.get("listing")]
    bars = load_bars(svc, listings, start=hist.fork_date, end=end)
    marked = mark_alt(hist, view, prices_on(bars, view))
    paper["held"] = _held_rows(hist, view, end, marked)
    return paper


def path_payload(
    hist: History,
    svc: HistoryService,
    *,
    until: str | None = None,
) -> dict[str, Any]:
    """NAV walk. Last point is header Δ. No holdings table."""
    end = until or utc_today()
    listings = listings_for_path(hist)
    bars = load_bars(svc, listings, start=hist.fork_date, end=end)
    path = compare_path(hist, bars, until=end)
    last = path[-1] if path else None
    return {
        "fork_date": hist.fork_date,
        "until": end,
        "base_currency": hist.seed.base_currency,
        "actual_nav": None if last is None else last["actual_nav"],
        "alt_nav": None if last is None else last["alt_nav"],
        "delta": None if last is None else last["delta"],
        "path": path,
        "svg": nav_path_svg(path),
    }


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


