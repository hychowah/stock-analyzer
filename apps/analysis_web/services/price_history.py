"""Daily closes for the analysis UI.

Callers pass one catalog ``quote_listing`` and the earliest calendar day they
must mark or plot. One successful series per listing lives in process RAM.
Yahoo period is how we fetched, not who we are. Chart-name repair lives in
yahoo_bars. This module does not know catalog identity, FV, or MoS.
"""

from __future__ import annotations

import os
import threading
import time
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


DEFAULT_TTL_SEC = 900
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
_PERIOD_ORDER = ("1m", "3m", "6m", "1y", "2y", "5y", "max")
_PERIOD_RANK = {key: i for i, key in enumerate(_PERIOD_ORDER)}


def history_ttl_sec() -> int:
    raw = (os.environ.get("HISTORY_TTL_SEC") or "").strip()
    if not raw:
        return DEFAULT_TTL_SEC
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_TTL_SEC
    return n if n >= 1 else DEFAULT_TTL_SEC


def _utc_today() -> str:
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
        self, symbols: list[str], *, since: str
    ) -> dict[str, PriceHistory]:
        """One round of daily closes covering ``since`` through now.

        Fake series are complete. Yahoo maps ``since`` to a trailing period.
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
        self, symbols: list[str], *, since: str
    ) -> dict[str, PriceHistory]:
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
    now = _parse_day(today) or _parse_day(_utc_today())
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


def _wider_period(left: str, right: str) -> str:
    return left if _PERIOD_RANK[left] >= _PERIOD_RANK[right] else right


def since_for_period(period_key: str, *, today: str | None = None) -> str:
    """A cover date that period_covering maps back to ``period_key`` (inside the bucket)."""
    key = period_key if period_key in RANGE_SPAN_DAYS else "max"
    days = RANGE_SPAN_DAYS[key]
    if days is None:
        return COVERED_ALL
    now = _parse_day(today) or _parse_day(_utc_today())
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
    now = _parse_day(today) or _parse_day(_utc_today())
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

    def history(self, symbol: str, *, since: str) -> PriceHistory:
        return _one_or_unavailable(
            self.history_many([symbol], since=since),
            symbol,
            source=self.source,
        )

    def history_many(
        self, symbols: list[str], *, since: str
    ) -> dict[str, PriceHistory]:
        unique = _unique_listings(symbols)
        period_key = period_covering(since, today=self._today)
        period = RANGES[period_key]
        if not unique:
            return {}
        try:
            yf = self._yf if self._yf is not None else import_yfinance()
        except RuntimeError as e:
            return {
                s: PriceHistory(symbol=s, source=self.source, error=str(e))
                for s in unique
            }
        resolved = resolve_close_series(
            yf,
            unique,
            period=period,
            interval="1d",
            download=self._download,
            search=self._search,
        )
        out: dict[str, PriceHistory] = {}
        for sym in unique:
            _yahoo, rows = resolved.get(sym, (sym, []))
            bars = bars_from_closes(rows)
            if not bars:
                out[sym] = PriceHistory(
                    symbol=sym,
                    source=self.source,
                    error="unavailable",
                )
            else:
                out[sym] = PriceHistory(
                    symbol=sym, source=self.source, bars=bars
                )
        return out


class HistoryService:
    """In-process daily-close map + single-flight in front of a HistoryBackend.

    Store key is listing. Cache only error is None. A blip must not freeze as
    unavailable. Coverage is the Yahoo period we asked for, not the first bar
    (a 2-year IPO and a truncated 1y fetch can look the same).
    On miss, fetch max(needed period, period already stored) so a short poll
    cannot shrink a long series. Single-flight is one in-process batch, like
    QuoteService; it is not yahoo_bars's yfinance lock.
    """

    def __init__(
        self,
        backend: HistoryBackend,
        *,
        ttl_sec: int = DEFAULT_TTL_SEC,
        today: str | None = None,
    ):
        self._backend = backend
        self._ttl = max(1, int(ttl_sec))
        self._today = today
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._store: dict[str, tuple[float, PriceHistory, str]] = {}
        self._batch_fetching = False

    @property
    def ttl_sec(self) -> int:
        return self._ttl

    @property
    def today(self) -> str:
        return self._today or _utc_today()

    def get(self, symbol: str, *, since: str) -> PriceHistory:
        return _one_or_unavailable(
            self.get_many([symbol], since=since), symbol
        )

    def get_many(
        self, symbols: list[str], *, since: str
    ) -> dict[str, PriceHistory]:
        """One row per unique listing, covering since through the latest stored bar."""
        unique = _unique_listings(symbols)
        need = normalize_since(since)
        out: dict[str, PriceHistory] = {}
        if not unique:
            return out
        now = time.monotonic()
        with self._cv:
            while self._batch_fetching:
                self._cv.wait(timeout=30)
            missing: list[str] = []
            today = self.today
            need_period = period_covering(need, today=today)
            fetch_period = need_period
            for s in unique:
                hit = self._store.get(s)
                stored_period = hit[2] if hit is not None else None
                if (
                    hit is not None
                    and hit[0] > now
                    and _PERIOD_RANK[stored_period] >= _PERIOD_RANK[need_period]
                ):
                    out[s] = hit[1]
                else:
                    missing.append(s)
                    if stored_period is not None:
                        fetch_period = _wider_period(fetch_period, stored_period)
            fetch_since = (
                need
                if fetch_period == need_period
                else since_for_period(fetch_period, today=today)
            )
            if not missing:
                return out
            self._batch_fetching = True
        try:
            fetched = dict(self._backend.history_many(missing, since=fetch_since))
            expires = time.monotonic() + self._ttl
            with self._cv:
                for s in missing:
                    hist = fetched.get(s) or PriceHistory(
                        symbol=s, error="unavailable"
                    )
                    if hist.error is None:
                        self._store[s] = (expires, hist, fetch_period)
                    out[s] = hist
            return out
        finally:
            with self._cv:
                self._batch_fetching = False
                self._cv.notify_all()
