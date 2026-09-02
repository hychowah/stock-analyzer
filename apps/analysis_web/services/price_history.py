"""Daily close history for the analysis UI.

Callers pass one Yahoo listing symbol (run.quote_listing). This module does
not know catalog tickers, FV, or MoS. Overlay those on the client from
catalog fields already on the run page.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Protocol

from apps.analysis_web.services.yahoo_bars import (
    bar_date,
    download_close_series,
    import_yfinance,
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


class HistoryBackend(Protocol):
    def history(self, symbol: str, range_key: str) -> PriceHistory:
        """Daily closes for one Yahoo listing and an allowlisted range key."""
        ...


class FakeHistoryBackend:
    """In-memory series for tests. Missing symbols get error=unavailable."""

    def __init__(self, series: dict[str, list[PriceBar]] | None = None):
        self._series = {k.upper(): list(v) for k, v in (series or {}).items()}
        self.calls: list[tuple[str, str]] = []

    def history(self, symbol: str, range_key: str) -> PriceHistory:
        sym = symbol.strip().upper()
        self.calls.append((sym, range_key))
        bars = self._series.get(sym)
        if bars is None:
            return PriceHistory(
                symbol=sym, range=range_key, source="fake", error="unavailable"
            )
        return PriceHistory(
            symbol=sym, range=range_key, source="fake", bars=tuple(bars)
        )


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
    return tuple(out)


class YahooHistoryBackend:
    """Daily adjusted close via yfinance. Listing symbols only."""

    source = "yahoo"

    def history(self, symbol: str, range_key: str) -> PriceHistory:
        sym = symbol.strip().upper()
        period = RANGES[range_key]
        try:
            yf = import_yfinance()
        except RuntimeError as e:
            return PriceHistory(
                symbol=sym, range=range_key, source=self.source, error=str(e)
            )
        series = download_close_series(yf, [sym], period=period, interval="1d")
        bars = bars_from_closes(series.get(sym) or [])
        if not bars:
            return PriceHistory(
                symbol=sym, range=range_key, source=self.source, error="unavailable"
            )
        return PriceHistory(
            symbol=sym, range=range_key, source=self.source, bars=bars
        )


class HistoryService:
    """In-process TTL cache + single-flight in front of a HistoryBackend.

    Cache only successful series (error is None) for ttl_sec. Failures are
    not stored: a Yahoo blip must not freeze as unavailable.
    """

    def __init__(self, backend: HistoryBackend, *, ttl_sec: int = DEFAULT_TTL_SEC):
        self._backend = backend
        self._ttl = max(1, int(ttl_sec))
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._store: dict[tuple[str, str], tuple[float, PriceHistory]] = {}
        self._fetching: set[tuple[str, str]] = set()

    @property
    def ttl_sec(self) -> int:
        return self._ttl

    def get(self, symbol: str, range_key: str) -> PriceHistory:
        key = (symbol.strip().upper(), range_key)
        now = time.monotonic()
        with self._cv:
            while key in self._fetching:
                self._cv.wait(timeout=30)
            hit = self._store.get(key)
            if hit is not None and hit[0] > now:
                return hit[1]
            self._fetching.add(key)
        try:
            hist = self._backend.history(key[0], key[1])
            # Successful series only. Do not cache error rows.
            if hist.error is None:
                expires = time.monotonic() + self._ttl
                with self._cv:
                    self._store[key] = (expires, hist)
            return hist
        finally:
            with self._cv:
                self._fetching.discard(key)
                self._cv.notify_all()
