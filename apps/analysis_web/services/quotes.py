"""Last-print quotes for the analysis UI.

Callers pass Yahoo listing strings: catalog ``quote_listing`` on Runs and
``/api/quotes``, holding ``print_listing`` on portfolio live-nav. Chart-name
repair lives in yahoo_bars. This module does not know catalog identity, FV,
or MoS.
LookupBackend stays a Mode A existence check — do not merge the two.

YahooPrintBackend returns a last available print: last 1-minute bar when
present, else last daily close. print_kind is 'intraday' or 'daily_close'.
quote_many always returns one row per requested listing (dropped symbols get
error, they are not omitted).
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from apps.analysis_web.services.yahoo_bars import (
    download_close_series,
    import_yfinance,
    resolve_close_series,
    search_yahoo_quotes,
)


DEFAULT_TTL_SEC = 120
MAX_SYMBOLS = 50


def quote_ttl_sec() -> int:
    raw = (os.environ.get("QUOTE_TTL_SEC") or "").strip()
    if not raw:
        return DEFAULT_TTL_SEC
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_TTL_SEC
    return n if n >= 1 else DEFAULT_TTL_SEC


@dataclass(frozen=True)
class QuotePrint:
    """One listing's last print. error set ⇒ price fields may be null."""

    symbol: str
    price: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None
    currency: str | None = None
    as_of: str | None = None
    market_state: str | None = None
    print_kind: str | None = None
    source: str = "yahoo"
    error: str | None = None

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


class QuoteBackend(Protocol):
    def quote_many(self, symbols: list[str]) -> list[QuotePrint]:
        """Last print for each requested listing (one row per input, unique)."""
        ...


class FakeQuoteBackend:
    """In-memory last-print map for tests. Missing symbols get error=unavailable."""

    def __init__(self, quotes: dict[str, QuotePrint] | None = None):
        self._quotes = {k.upper(): v for k, v in (quotes or {}).items()}
        self.calls: list[tuple[str, ...]] = []

    def quote_many(self, symbols: list[str]) -> list[QuotePrint]:
        unique = _unique_listings(symbols)
        self.calls.append(tuple(unique))
        out: list[QuotePrint] = []
        for sym in unique:
            hit = self._quotes.get(sym)
            if hit is not None:
                out.append(hit)
            else:
                out.append(QuotePrint(symbol=sym, source="fake", error="unavailable"))
        return out


def _unique_listings(symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in symbols:
        s = str(raw or "").strip().upper()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def parse_symbol_query(raw: str | None) -> list[str]:
    """Split comma-separated listings. Empty / over cap raise ValueError."""
    unique = _unique_listings((raw or "").split(","))
    if not unique:
        raise ValueError("symbols is required")
    if len(unique) > MAX_SYMBOLS:
        raise ValueError(f"at most {MAX_SYMBOLS} unique listings per request")
    return unique


def _change_pct(price: float | None, prev_close: float | None) -> float | None:
    if price is None or prev_close is None or prev_close == 0:
        return None
    return (price / prev_close - 1.0) * 100.0


def build_quote(
    symbol: str,
    *,
    last_intraday: float | None,
    last_daily: float | None,
    prev_daily: float | None,
    as_of_intraday: str | None = None,
    as_of_daily: str | None = None,
    currency: str | None = None,
    source: str = "yahoo",
) -> QuotePrint:
    """Pick last 1m print when present, else last daily close. Always a row."""
    sym = symbol.strip().upper()
    if last_intraday is not None:
        return QuotePrint(
            symbol=sym,
            price=last_intraday,
            prev_close=prev_daily,
            change_pct=_change_pct(last_intraday, prev_daily),
            currency=currency,
            as_of=as_of_intraday or as_of_daily,
            market_state="regular",
            print_kind="intraday",
            source=source,
            error=None,
        )
    if last_daily is not None:
        return QuotePrint(
            symbol=sym,
            price=last_daily,
            prev_close=prev_daily,
            change_pct=_change_pct(last_daily, prev_daily),
            currency=currency,
            as_of=as_of_daily,
            market_state="closed",
            print_kind="daily_close",
            source=source,
            error=None,
        )
    return QuotePrint(symbol=sym, source=source, error="unavailable")


class YahooPrintBackend:
    """Last print via yahoo_bars for catalog quote_listing strings."""

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

    def quote_many(self, symbols: list[str]) -> list[QuotePrint]:
        unique = _unique_listings(symbols)
        if not unique:
            return []
        try:
            yf = self._yf if self._yf is not None else import_yfinance()
        except RuntimeError as e:
            return [
                QuotePrint(symbol=s, source=self.source, error=str(e)) for s in unique
            ]
        daily_resolved = resolve_close_series(
            yf,
            unique,
            period="5d",
            interval="1d",
            download=self._download,
            search=self._search,
        )
        yahoo_for_intra: list[str] = []
        seen_yahoo: set[str] = set()
        for sym in unique:
            ysym, daily = daily_resolved.get(sym, (sym, []))
            if daily and ysym not in seen_yahoo:
                seen_yahoo.add(ysym)
                yahoo_for_intra.append(ysym)
        intra_map = (
            self._download(yf, yahoo_for_intra, period="1d", interval="1m")
            if yahoo_for_intra
            else {}
        )
        out: list[QuotePrint] = []
        for sym in unique:
            ysym, daily = daily_resolved.get(sym, (sym, []))
            intra = intra_map.get(ysym) or []
            last_intra = intra[-1] if intra else (None, None)
            last_daily = daily[-1] if daily else (None, None)
            prev_daily = daily[-2] if len(daily) >= 2 else (None, None)
            out.append(
                build_quote(
                    sym,
                    last_intraday=last_intra[0],
                    last_daily=last_daily[0],
                    prev_daily=prev_daily[0],
                    as_of_intraday=last_intra[1],
                    as_of_daily=last_daily[1],
                    currency=None,
                    source=self.source,
                )
            )
        return out


class QuoteService:
    """In-process TTL cache + single-flight in front of a QuoteBackend.

    Cache only successful prints (error is None) for ttl_sec. Failures are
    not stored: a Yahoo blip must not freeze as unavailable.
    """

    def __init__(self, backend: QuoteBackend, *, ttl_sec: int = DEFAULT_TTL_SEC):
        self._backend = backend
        self._ttl = max(1, int(ttl_sec))
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._store: dict[str, tuple[float, QuotePrint]] = {}
        self._fetching = False

    @property
    def ttl_sec(self) -> int:
        return self._ttl

    def get_many(self, symbols: list[str]) -> list[QuotePrint]:
        unique = _unique_listings(symbols)
        if not unique:
            return []
        now = time.monotonic()
        with self._cv:
            while self._fetching:
                self._cv.wait(timeout=30)
            cached, missing = self._split_cached(unique, now)
            if not missing:
                return [cached[s] for s in unique]
            self._fetching = True
        try:
            fetched = list(self._backend.quote_many(missing))
            by_sym = {q.symbol.upper(): q for q in fetched}
            expires = time.monotonic() + self._ttl
            with self._cv:
                for sym in missing:
                    q = by_sym.get(sym) or QuotePrint(
                        symbol=sym, source="yahoo", error="unavailable"
                    )
                    if q.error is None:
                        self._store[sym] = (expires, q)
                    cached[sym] = q
        finally:
            with self._cv:
                self._fetching = False
                self._cv.notify_all()
        return [cached[s] for s in unique]

    def _split_cached(
        self, unique: list[str], now: float
    ) -> tuple[dict[str, QuotePrint], list[str]]:
        cached: dict[str, QuotePrint] = {}
        missing: list[str] = []
        for sym in unique:
            hit = self._store.get(sym)
            if hit is not None and hit[0] > now:
                cached[sym] = hit[1]
            else:
                missing.append(sym)
        return cached, missing
