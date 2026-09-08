"""Assemble what-if page payloads. Fetch closes; do not call Live NAV."""

from __future__ import annotations

from html import escape
from typing import Any, Callable

from apps.analysis_web.services.alt_history import (
    History,
    actual_state,
    compare_path,
    listings_for_path,
    mark_actual,
    mark_alt,
    path_dates,
    prices_on,
    state_on,
    utc_today,
)
from apps.analysis_web.services.book_state import earliest_stock_date
from apps.analysis_web.services.price_history import HistoryService, PriceBar, close_on


def close_getter(svc: HistoryService) -> Callable[[str, str], float | None]:
    def get_close(listing: str, date: str) -> float | None:
        hist = svc.get(listing, "max")
        bar = close_on(hist.bars, date)
        return None if bar is None else bar.close

    return get_close


def load_bars(svc: HistoryService, listings: list[str]) -> dict[str, tuple[PriceBar, ...]]:
    out: dict[str, tuple[PriceBar, ...]] = {}
    for raw in listings:
        listing = (raw or "").strip().upper()
        if not listing:
            continue
        hist = svc.get(listing, "max")
        out[listing] = hist.bars
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
) -> dict[str, Any]:
    fork = hist.fork_date
    path = compare_path(hist, bars, until=until)
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
    bars = load_bars(svc, sorted(listings))
    cards = [card_for(hist, bars, until=end) for hist in histories]
    overlay = None
    if len(cards) >= 2:
        start = min(forks) if forks else end
        overlay = overlay_svg(histories, bars, start, end)
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


def editor_payload(
    hist: History,
    svc: HistoryService,
    *,
    view_date: str | None = None,
    until: str | None = None,
    universe: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    end = until or utc_today()
    fork = hist.fork_date
    view = (view_date or end).strip()[:10] or end
    if view < fork:
        view = fork
    if view > end:
        view = end
    listings = listings_for_path(hist)
    bars = load_bars(svc, listings)
    path = compare_path(hist, bars, until=end)
    last = path[-1] if path else None
    prices_view = prices_on(bars, view)
    held = state_on(hist, view)
    marked_held = mark_alt(hist, view, prices_view)
    today_book = state_on(hist, end)
    today_actual_lots = {lot.listing for lot in actual_state(hist, end).lots}
    by_listing = {r.listing: r for r in marked_held.rows}
    held_rows = []
    for lot in held.lots:
        row = by_listing.get(lot.listing)
        held_rows.append(
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
    return {
        "history": hist,
        "fork_date": fork,
        "view_date": view,
        "until": end,
        "min_date": hist.fork_date,
        "max_date": end,
        "base_currency": hist.seed.base_currency,
        "caveats": today_book.caveats,
        "cash": today_book.cash_base,
        "held": held_rows,
        "universe": universe or [],
        "decisions": [f.as_json() for f in hist.hyp_fills()],
        "actual_nav": None if last is None else last["actual_nav"],
        "alt_nav": None if last is None else last["alt_nav"],
        "delta": None if last is None else last["delta"],
        "path": path,
        "svg": nav_path_svg(path),
        "error": error,
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
        f'<svg class="nav-chart-svg" viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" role="img" '
        f'aria-label="Actual versus this history, daily close">'
        f'<polyline class="nav-path-actual" fill="none" points="{actual}"/>'
        f'<polyline class="nav-path-alt" fill="none" points="{alt}"/>'
        f"</svg>"
    )


def overlay_svg(
    histories: list[History],
    bars: dict[str, tuple[PriceBar, ...]],
    start: str,
    end: str,
    *,
    width: int = 640,
    height: int = 180,
) -> str:
    days = path_dates(bars, start, end)
    if len(days) < 2:
        return ""
    actual_pts: list[float] = []
    series: list[list[float]] = []
    baseline = histories[0]
    for day in days:
        prices = prices_on(bars, day)
        actual_pts.append(mark_actual(baseline, day, prices).nav)
    for hist in histories:
        fork = hist.fork_date
        line: list[float] = []
        for day in days:
            prices = prices_on(bars, day)
            if day < fork:
                line.append(mark_actual(hist, day, prices).nav)
            else:
                line.append(mark_alt(hist, day, prices).nav)
        series.append(line)
    vals = actual_pts + [v for line in series for v in line]
    ymin, ymax = _domain(vals)
    pad_l, pad_r, pad_t, pad_b = 8, 8, 8, 8
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)
    n = len(days)

    def xy(i: int, value: float) -> str:
        x = pad_l + (inner_w * i / (n - 1))
        y = pad_t + inner_h * (1 - (value - ymin) / (ymax - ymin))
        return f"{x:.1f},{y:.1f}"

    actual = " ".join(xy(i, v) for i, v in enumerate(actual_pts))
    parts = [
        f'<svg class="nav-chart-svg" viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" role="img" '
        f'aria-label="Actual versus alternative histories, daily close">',
        f'<polyline class="nav-path-actual" fill="none" points="{actual}"/>',
    ]
    for i, line in enumerate(series):
        pts = " ".join(xy(j, v) for j, v in enumerate(line))
        cls = f"nav-path-alt nav-path-h{i % 6}"
        name = escape(str(histories[i].name or f"History {i + 1}"))
        parts.append(
            f'<polyline class="{cls}" fill="none" points="{pts}">'
            f"<title>{name}</title></polyline>"
        )
    parts.append("</svg>")
    return "".join(parts)


