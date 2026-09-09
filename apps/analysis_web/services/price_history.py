"""Daily close history for the analysis UI.

Callers pass one catalog `quote_listing`. Chart-name repair lives in
yahoo_bars. This module does not know catalog identity, FV, or MoS. Overlay
those on the client from catalog fields already on the run page.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
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
RANGES: dict[str, str] = {
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1y": "1y",
    "2y": "2y",
    "5y": "5y",
    "max": "max",
}


def history_ttl_sec() -> int:
    raw = (os.environ.get("HISTORY_TTL_SEC") or "").strip()
    if not raw:
        return DEFAULT_TTL_SEC
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_TTL_SEC
    return n if n >= 1 else DEFAULT_TTL_SEC


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
    """One listing's daily closes for a range. error set ⇒ bars may be empty."""

    symbol: str
    range: str
    interval: str = "1d"
    source: str = "yahoo"
    bars: tuple[PriceBar, ...] = ()
    error: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "range": self.range,
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
    range_key: str,
    *,
    source: str = "yahoo",
) -> PriceHistory:
    key = (symbol or "").strip().upper()
    return got.get(key) or PriceHistory(
        symbol=key, range=range_key, source=source, error="unavailable"
    )


class HistoryBackend(Protocol):
    def history_many(
        self, symbols: list[str], range_key: str
    ) -> dict[str, PriceHistory]:
        """Daily closes for many listings. One backend round."""
        ...


class FakeHistoryBackend:
    """In-memory series for tests. Missing symbols get error=unavailable."""

    def __init__(self, series: dict[str, list[PriceBar]] | None = None):
        self._series = {k.upper(): list(v) for k, v in (series or {}).items()}
        self.calls: list[tuple[str, str]] = []
        self.many_calls: list[tuple[tuple[str, ...], str]] = []

    def history(self, symbol: str, range_key: str) -> PriceHistory:
        return _one_or_unavailable(
            self.history_many([symbol], range_key),
            symbol,
            range_key,
            source="fake",
        )

    def history_many(
        self, symbols: list[str], range_key: str
    ) -> dict[str, PriceHistory]:
        unique = _unique_listings(symbols)
        self.many_calls.append((tuple(unique), range_key))
        out: dict[str, PriceHistory] = {}
        for s in unique:
            self.calls.append((s, range_key))
            bars = self._series.get(s)
            if bars is None:
                out[s] = PriceHistory(
                    symbol=s, range=range_key, source="fake", error="unavailable"
                )
            else:
                ordered = tuple(sorted(bars, key=lambda bar: (bar.t or "")[:10]))
                out[s] = PriceHistory(
                    symbol=s, range=range_key, source="fake", bars=ordered
                )
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


def range_for_span(start: str, end: str | None = None) -> str:
    """Smallest allowlisted Yahoo period that still includes ``start``.

    Yahoo periods are trailing from ``end`` (today if omitted), not from
    ``start``. An old fork needs ``max`` even when ``end - start`` is short.
    """
    a = (start or "").strip()[:10]
    b = (end or "").strip()[:10]
    if len(b) < 10:
        b = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if len(a) < 10 or len(b) < 10:
        return "max"
    try:
        da = date.fromisoformat(a)
        db = date.fromisoformat(b)
    except ValueError:
        return "max"
    need = (db - da).days + 7
    if need <= 0:
        return "1y"
    if need <= 365:
        return "1y"
    if need <= 365 * 2:
        return "2y"
    if need <= 365 * 5:
        return "5y"
    return "max"


class YahooHistoryBackend:
    """Daily adjusted close via yahoo_bars for catalog quote_listing strings."""

    source = "yahoo"

    def __init__(
        self,
        *,
        yf: Any = None,
        download: Any = download_close_series,
        search: Any = search_yahoo_quotes,
    ):
        self._yf = yf
        self._download = download
        self._search = search

    def history(self, symbol: str, range_key: str) -> PriceHistory:
        return _one_or_unavailable(
            self.history_many([symbol], range_key),
            symbol,
            range_key,
            source=self.source,
        )

    def history_many(
        self, symbols: list[str], range_key: str
    ) -> dict[str, PriceHistory]:
        unique = _unique_listings(symbols)
        period = RANGES[range_key]
        if not unique:
            return {}
        try:
            yf = self._yf if self._yf is not None else import_yfinance()
        except RuntimeError as e:
            return {
                s: PriceHistory(
                    symbol=s, range=range_key, source=self.source, error=str(e)
                )
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
                    range=range_key,
                    source=self.source,
                    error="unavailable",
                )
            else:
                out[sym] = PriceHistory(
                    symbol=sym, range=range_key, source=self.source, bars=bars
                )
        return out


class HistoryService:
    """In-process TTL cache + single-flight in front of a HistoryBackend.

    Cache only successful series (error is None) for ttl_sec. Failures are
    not stored: a Yahoo blip must not freeze as unavailable.
    ``_batch_fetching`` coalesces in-flight get_many calls; it is not a
    download lock.
    """

    def __init__(self, backend: HistoryBackend, *, ttl_sec: int = DEFAULT_TTL_SEC):
        self._backend = backend
        self._ttl = max(1, int(ttl_sec))
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._store: dict[tuple[str, str], tuple[float, PriceHistory]] = {}
        self._batch_fetching = False

    @property
    def ttl_sec(self) -> int:
        return self._ttl

    def get(self, symbol: str, range_key: str) -> PriceHistory:
        return _one_or_unavailable(self.get_many([symbol], range_key), symbol, range_key)

    def get_many(
        self, symbols: list[str], range_key: str
    ) -> dict[str, PriceHistory]:
        unique = _unique_listings(symbols)
        out: dict[str, PriceHistory] = {}
        if not unique:
            return out
        now = time.monotonic()
        with self._cv:
            while self._batch_fetching:
                self._cv.wait(timeout=30)
            missing: list[str] = []
            for s in unique:
                hit = self._store.get((s, range_key))
                if hit is not None and hit[0] > now:
                    out[s] = hit[1]
                else:
                    missing.append(s)
            if not missing:
                return out
            self._batch_fetching = True
        try:
            fetched = dict(self._backend.history_many(missing, range_key))
            expires = time.monotonic() + self._ttl
            with self._cv:
                for s in missing:
                    hist = fetched.get(s) or PriceHistory(
                        symbol=s, range=range_key, error="unavailable"
                    )
                    if hist.error is None:
                        self._store[(s, range_key)] = (expires, hist)
                    out[s] = hist
            return out
        finally:
            with self._cv:
                self._batch_fetching = False
                self._cv.notify_all()
