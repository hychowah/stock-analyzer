"""Daily-close value types and Yahoo/fake fetch backends.

Durable storage is DailyCloses. Yahoo writes through CloseRefresh, not a
GET. Callers pass one catalog ``quote_listing`` and the earliest calendar
day they must mark or plot. Yahoo period is how we fetched, not who we
are. Chart-name repair lives in yahoo_bars. This module does not know
catalog identity, FV, or MoS.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol

from apps.analysis_web.services.yahoo_bars import (
    bar_date,
    download_close_series,
    import_yfinance,
    resolve_close_series,
    search_yahoo_quotes,
)


DEFAULT_RANGE = "1y"
# HTTP chart vocabulary and yfinance period tokens. Not a store key.
RANGES: dict[str, str] = {
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1y": "1y",
    "2y": "2y",
    "5y": "5y",
    "max": "max",
}
# Trailing calendar span for HTTP ?range= (display slice, not Yahoo pad).
RANGE_SPAN_DAYS: dict[str, int | None] = {
    "1m": 31,
    "3m": 93,
    "6m": 186,
    "1y": 365,
    "2y": 365 * 2,
    "5y": 365 * 5,
    "max": None,
}
# Stored coverage for a max fetch: earlier than any real caller since.
COVERED_ALL = "0001-01-01"


def utc_today() -> str:
    """UTC calendar day YYYY-MM-DD. HTTP range slice clock."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_day(raw: str | None) -> date | None:
    s = (raw or "").strip()[:10]
    if len(s) < 10:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def normalize_since(raw: str | None) -> str:
    """YYYY-MM-DD cover date, or COVERED_ALL when missing/invalid (need max)."""
    day = _parse_day(raw)
    return day.isoformat() if day is not None else COVERED_ALL


@dataclass(frozen=True)
class PriceBar:
    t: str
    close: float

    def as_json(self) -> dict[str, Any]:
        return {"t": self.t, "close": self.close}


def close_on(bars: tuple[PriceBar, ...] | list[PriceBar], date: str) -> PriceBar | None:
    """Last bar on or before ``date`` (YYYY-MM-DD). None if every bar is later.

    ``bars`` must be sorted by ``t``. Callers that ingest Yahoo or a fake
    series sort once (``bars_from_closes`` / ``FakeHistoryBackend``).
    """
    day = (date or "").strip()[:10]
    if len(day) < 10 or not bars:
        return None
    lo = 0
    hi = len(bars)
    while lo < hi:
        mid = (lo + hi) // 2
        t = (bars[mid].t or "")[:10]
        if t and t <= day:
            lo = mid + 1
        else:
            hi = mid
    if lo == 0:
        return None
    return bars[lo - 1]


@dataclass(frozen=True)
class PriceHistory:
    """One listing's daily closes. error set ⇒ bars may be empty. No range field."""

    symbol: str
    interval: str = "1d"
    source: str = "yahoo"
    bars: tuple[PriceBar, ...] = ()
    error: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "source": self.source,
            "bars": [b.as_json() for b in self.bars],
            "count": len(self.bars),
            "error": self.error,
        }


def _unique_listings(symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in symbols:
        s = (raw or "").strip().upper()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _one_or_unavailable(
    got: dict[str, PriceHistory],
    symbol: str,
    *,
    source: str = "yahoo",
) -> PriceHistory:
    key = (symbol or "").strip().upper()
    return got.get(key) or PriceHistory(
        symbol=key, source=source, error="unavailable"
    )


class HistoryBackend(Protocol):
    def history_many(
        self,
        symbols: list[str],
        *,
        since: str,
        preferred_charts: dict[str, str] | None = None,
    ) -> dict[str, PriceHistory]:
        """One round of daily closes covering ``since`` through now.

        Fake series are complete. Yahoo maps ``since`` to a trailing period.
        ``preferred_charts`` is listing → last Yahoo chart name (writer only).
        """
        ...


class FakeHistoryBackend:
    """In-memory series for tests. Missing symbols get error=unavailable.

    Canned series are complete. ``since`` is a recorded need, not a second series.
    """

    def __init__(self, series: dict[str, list[PriceBar]] | None = None):
        self._series = {k.upper(): list(v) for k, v in (series or {}).items()}
        self.calls: list[tuple[str, str]] = []
        self.many_calls: list[tuple[tuple[str, ...], str]] = []

    def history(self, symbol: str, *, since: str) -> PriceHistory:
        return _one_or_unavailable(
            self.history_many([symbol], since=since),
            symbol,
            source="fake",
        )

    def history_many(
        self,
        symbols: list[str],
        *,
        since: str,
        preferred_charts: dict[str, str] | None = None,
    ) -> dict[str, PriceHistory]:
        _ = preferred_charts
        unique = _unique_listings(symbols)
        self.many_calls.append((tuple(unique), since))
        out: dict[str, PriceHistory] = {}
        for s in unique:
            self.calls.append((s, since))
            bars = self._series.get(s)
            if bars is None:
                out[s] = PriceHistory(
                    symbol=s, source="fake", error="unavailable"
                )
            else:
                ordered = tuple(sorted(bars, key=lambda bar: (bar.t or "")[:10]))
                out[s] = PriceHistory(symbol=s, source="fake", bars=ordered)
        return out


def parse_history_symbol(raw: str | None) -> str:
    s = str(raw or "").strip().upper()
    if not s:
        raise ValueError("symbol is required")
    if "," in s or any(ch.isspace() for ch in s):
        raise ValueError("exactly one listing symbol")
    return s


def parse_range(raw: str | None) -> str:
    key = (raw or DEFAULT_RANGE).strip().lower() or DEFAULT_RANGE
    if key not in RANGES:
        allowed = ", ".join(RANGES)
        raise ValueError(f"range must be one of {allowed}")
    return key


def bars_from_closes(rows: list[tuple[float, str | None]]) -> tuple[PriceBar, ...]:
    out: list[PriceBar] = []
    for px, ts in rows:
        t = bar_date(ts)
        if t is None:
            continue
        out.append(PriceBar(t=t, close=px))
    out.sort(key=lambda bar: (bar.t or "")[:10])
    return tuple(out)


def period_covering(since: str, *, today: str | None = None) -> str:
    """Smallest allowlisted Yahoo period trailing from today that still includes since.

    Pad a week so close_on(start) can land on the prior session. Invalid since → max.
    """
    start = _parse_day(since)
    now = _parse_day(today) or _parse_day(utc_today())
    if start is None or now is None:
        return "max"
    span = (now - start).days
    if span <= 0:
        return "1m"
    need = span + 7
    if need <= 31:
        return "1m"
    if need <= 93:
        return "3m"
    if need <= 186:
        return "6m"
    if need <= 365:
        return "1y"
    if need <= 365 * 2:
        return "2y"
    if need <= 365 * 5:
        return "5y"
    return "max"


def since_for_period(period_key: str, *, today: str | None = None) -> str:
    """A cover date that period_covering maps back to ``period_key`` (inside the bucket)."""
    key = period_key if period_key in RANGE_SPAN_DAYS else "max"
    days = RANGE_SPAN_DAYS[key]
    if days is None:
        return COVERED_ALL
    now = _parse_day(today) or _parse_day(utc_today())
    if now is None:
        return COVERED_ALL
    inner = max(0, days - 7)
    return (now - timedelta(days=inner)).isoformat()


def since_for_range(range_key: str, *, today: str | None = None) -> str:
    """Earliest day a chart ``?range=`` window must cover. HTTP only."""
    key = parse_range(range_key)
    days = RANGE_SPAN_DAYS[key]
    if days is None:
        return COVERED_ALL
    now = _parse_day(today) or _parse_day(utc_today())
    if now is None:
        return COVERED_ALL
    return (now - timedelta(days=days)).isoformat()


def bars_in_window(
    bars: tuple[PriceBar, ...] | list[PriceBar],
    range_key: str,
    *,
    today: str | None = None,
) -> tuple[PriceBar, ...]:
    """Trailing slice for HTTP ``?range=``. ``max`` returns the full series."""
    start = since_for_range(range_key, today=today)
    if start == COVERED_ALL:
        return tuple(bars)
    return tuple(b for b in bars if (b.t or "")[:10] >= start)


class YahooHistoryBackend:
    """Daily adjusted close via yahoo_bars for catalog quote_listing strings."""

    source = "yahoo"

    def __init__(
        self,
        *,
        yf: Any = None,
        download: Any = download_close_series,
        search: Any = search_yahoo_quotes,
        today: str | None = None,
    ):
        self._yf = yf
        self._download = download
        self._search = search
        self._today = today
        self.last_charts: dict[str, str] = {}

    def history(self, symbol: str, *, since: str) -> PriceHistory:
        return _one_or_unavailable(
            self.history_many([symbol], since=since),
            symbol,
            source=self.source,
        )

    def history_many(
        self,
        symbols: list[str],
        *,
        since: str,
        preferred_charts: dict[str, str] | None = None,
    ) -> dict[str, PriceHistory]:
        unique = _unique_listings(symbols)
        period_key = period_covering(since, today=self._today)
        period = RANGES[period_key]
        self.last_charts = {}
        if not unique:
            return {}
        try:
            yf = self._yf if self._yf is not None else import_yfinance()
        except RuntimeError as e:
            return {
                s: PriceHistory(symbol=s, source=self.source, error=str(e))
                for s in unique
            }
        fetch = list(unique)
        pref: dict[str, str] = {}
        for raw_k, raw_v in (preferred_charts or {}).items():
            k = (raw_k or "").strip().upper()
            v = (raw_v or "").strip().upper()
            if k and v:
                pref[k] = v
                if v not in fetch:
                    fetch.append(v)
        resolved = resolve_close_series(
            yf,
            fetch,
            period=period,
            interval="1d",
            download=self._download,
            search=self._search,
        )
        out: dict[str, PriceHistory] = {}
        for sym in unique:
            yahoo, rows = resolved.get(sym, (sym, []))
            if not rows:
                chart = pref.get(sym)
                if chart:
                    yahoo, rows = resolved.get(chart, (chart, []))
            bars = bars_from_closes(rows)
            if not bars:
                out[sym] = PriceHistory(
                    symbol=sym,
                    source=self.source,
                    error="unavailable",
                )
            else:
                chart_name = str(yahoo or sym).strip().upper() or sym
                self.last_charts[sym] = chart_name
                out[sym] = PriceHistory(
                    symbol=sym, source=self.source, bars=bars
                )
        return out
