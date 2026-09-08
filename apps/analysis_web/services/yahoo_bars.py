"""Yahoo OHLCV for catalog `quote_listing` strings.

Callers pass the requested listing (stamp, else snapshot, else folder ticker).
This module resolves the Yahoo chart name and returns series keyed by the
request. No catalog identity, FV, or MoS.
"""

from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from typing import Any, Callable, Iterator

CloseRow = tuple[float, str | None]
CloseSeries = list[CloseRow]
DownloadFn = Callable[..., dict[str, CloseSeries]]
SearchFn = Callable[..., list[dict[str, Any]]]

# Yahoo HK listings are 4 digits (0700.HK). Folder names sometimes keep the
# HKEX 5-digit padded form (01378.HK). Strip one leading zero — not a ticker map.
_HK_PADDED = re.compile(r"^0(\d{4}\.HK)$")
_SEARCH_QUOTE_TYPES = frozenset({"EQUITY", "ETF", "INDEX"})


def as_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n != n:  # NaN
        return None
    return n


def ts_iso(ts: Any) -> str | None:
    if ts is None:
        return None
    iso = getattr(ts, "isoformat", None)
    if callable(iso):
        try:
            return str(iso())
        except Exception:  # noqa: BLE001
            pass
    s = str(ts).strip()
    return s or None


def bar_date(ts: str | None) -> str | None:
    """YYYY-MM-DD from an isoformat / pandas timestamp string."""
    if not ts:
        return None
    s = ts.strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s or None


def import_yfinance() -> Any:
    try:
        import yfinance as yf  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "yfinance not installed. pip install -r apps/analysis_web/requirements.txt"
        ) from e
    return yf


def listing_candidates(symbol: str) -> list[str]:
    """Requested listing plus mechanical Yahoo forms. No per-issuer map."""
    s = str(symbol or "").strip().upper()
    if not s:
        return []
    out = [s]
    m = _HK_PADDED.match(s)
    if m:
        alt = m.group(1)
        if alt not in out:
            out.append(alt)
    return out


def pick_search_listing(query: str, hits: list[dict[str, Any]]) -> str | None:
    """If QUERY is not itself a Yahoo symbol, take QUERY.<exchange> from search.

    Exact QUERY in the hits means search cannot help (already tried as-is).
    Query with a dot is left alone — HK padding handles those.
    """
    q = str(query or "").strip().upper()
    if not q or "." in q:
        return None
    suffix_hits: list[str] = []
    for row in hits:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or "").strip().upper()
        if not sym:
            continue
        qt = str(row.get("quoteType") or row.get("quote_type") or "").upper()
        if qt and qt not in _SEARCH_QUOTE_TYPES:
            continue
        if sym == q:
            return None
        if sym.startswith(q + ".") and sym.count(".") == 1:
            suffix_hits.append(sym)
    if not suffix_hits:
        return None
    return suffix_hits[0]


def search_yahoo_quotes(yf: Any, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    try:
        found = yf.Search(query, max_results=limit)
        rows = getattr(found, "quotes", None) or []
    except Exception:  # noqa: BLE001
        return []
    return [row for row in rows if isinstance(row, dict)]


@contextmanager
def _quiet_yfinance() -> Iterator[None]:
    """Empty 1m/chart is not a delisting. Hide yfinance's 'possibly delisted' error log."""
    log = logging.getLogger("yfinance")
    prev = log.level
    log.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        log.setLevel(prev)


def split_download(data: Any, symbols: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {s: None for s in symbols}
    if data is None:
        return out
    empty = getattr(data, "empty", True)
    if empty:
        return out
    cols = getattr(data, "columns", None)
    if cols is not None and getattr(cols, "nlevels", 1) > 1:
        by_upper: dict[str, Any] = {}
        try:
            level0 = list(cols.get_level_values(0))
            for name in level0:
                key = str(name).upper()
                if key not in by_upper:
                    try:
                        by_upper[key] = data[name]
                    except Exception:  # noqa: BLE001
                        continue
        except Exception:  # noqa: BLE001
            by_upper = {}
        for sym in symbols:
            frame = by_upper.get(sym)
            if frame is None:
                try:
                    frame = data[sym]
                except Exception:  # noqa: BLE001
                    continue
            out[sym] = frame
        return out
    if len(symbols) == 1:
        out[symbols[0]] = data
    return out


def close_series(df: Any) -> list[tuple[float, str | None]]:
    if df is None:
        return []
    try:
        series = df["Close"]
    except Exception:  # noqa: BLE001
        return []
    rows: list[tuple[float, str | None]] = []
    try:
        items = list(series.items())
    except Exception:  # noqa: BLE001
        return []
    for ts, val in items:
        px = as_float(val)
        if px is None:
            continue
        rows.append((px, ts_iso(ts)))
    return rows


def download_close_series(
    yf: Any, symbols: list[str], *, period: str, interval: str
) -> dict[str, CloseSeries]:
    """symbol -> [(close, as_of), ...] from yf.download. Missing symbols are []."""
    empty: dict[str, CloseSeries] = {s: [] for s in symbols}
    if not symbols:
        return empty
    try:
        with _quiet_yfinance():
            data = yf.download(
                tickers=symbols,
                period=period,
                interval=interval,
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
                timeout=20,
            )
    except Exception:  # noqa: BLE001
        return empty
    frames = split_download(data, symbols)
    out: dict[str, CloseSeries] = {}
    for sym in symbols:
        out[sym] = close_series(frames.get(sym))
    return out


def resolve_close_series(
    yf: Any,
    symbols: list[str],
    *,
    period: str,
    interval: str,
    download: DownloadFn | None = None,
    search: SearchFn | None = None,
) -> dict[str, tuple[str, CloseSeries]]:
    """Closes keyed by the requested listing. Yahoo chart name is internal."""
    dl = download or download_close_series
    srch = search or search_yahoo_quotes
    unique: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        s = str(raw or "").strip().upper()
        if not s or s in seen:
            continue
        seen.add(s)
        unique.append(s)
    out: dict[str, tuple[str, CloseSeries]] = {s: (s, []) for s in unique}
    if not unique:
        return out

    pool: dict[str, CloseSeries] = dict(dl(yf, unique, period=period, interval=interval))

    def take(requested: str, yahoo: str, rows: CloseSeries) -> None:
        if rows:
            out[requested] = (yahoo, rows)

    for s in unique:
        take(s, s, pool.get(s) or [])

    misses = [s for s in unique if not out[s][1]]
    alias_plan: list[tuple[str, str]] = []
    alias_fetch: list[str] = []
    for s in misses:
        for cand in listing_candidates(s)[1:]:
            rows = pool.get(cand) or []
            if rows:
                take(s, cand, rows)
                break
            alias_plan.append((s, cand))
            if cand not in pool and cand not in alias_fetch:
                alias_fetch.append(cand)
    if alias_fetch:
        extra = dl(yf, alias_fetch, period=period, interval=interval)
        pool.update(extra)
        for s, cand in alias_plan:
            if out[s][1]:
                continue
            take(s, cand, pool.get(cand) or [])

    misses = [s for s in unique if not out[s][1]]
    search_plan: list[tuple[str, str]] = []
    search_fetch: list[str] = []
    for s in misses:
        if "." in s:
            continue
        picked = pick_search_listing(s, srch(yf, s))
        if not picked:
            continue
        rows = pool.get(picked) or []
        if rows:
            take(s, picked, rows)
            continue
        search_plan.append((s, picked))
        if picked not in search_fetch:
            search_fetch.append(picked)
    if search_fetch:
        extra = dl(yf, search_fetch, period=period, interval=interval)
        pool.update(extra)
        for s, picked in search_plan:
            if out[s][1]:
                continue
            take(s, picked, pool.get(picked) or [])
    return out
