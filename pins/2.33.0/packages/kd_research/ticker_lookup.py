"""Mode A market-ticker existence check (no LLM, no suffix map).

Python only answers: is there any Yahoo evidence this name exists?
- live quote under the typed symbol → quoted (scaffold typed folder)
- no live quote, Yahoo search has usable listings → search_evidence
  (scaffold typed folder; orchestrator confirms listing with tools)
- no quote and no search hits → abort (do not scaffold)

Does not remap the archive folder. Does not pick a Yahoo listing.
quote_symbol is written only after the orchestrator confirms a live listing
and scripts/verify_listing.py quotes it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from packages.kd_research.paths import TICKER_BLOCKLIST

TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\^/\-]{0,19}$")
VALID_QUOTE_TYPES = frozenset(
    {
        "EQUITY",
        "ETF",
        "INDEX",
        "MUTUALFUND",
        "CRYPTOCURRENCY",
        "FUTURE",
        "CURRENCY",
        "WARRANT",
    }
)
JUNK_QUOTE_TYPES = frozenset({"NONE", "N/A", ""})
EXISTENCE_OK = frozenset({"quoted", "search_evidence"})


@dataclass(frozen=True)
class Quote:
    symbol: str
    quote_type: str | None = None
    name: str | None = None
    n_fields: int = 0
    price: float | None = None


@dataclass
class TickerCheck:
    typed: str
    status: str  # quoted | search_evidence | abort_unknown | abort_reserved | abort_syntax
    reason: str = ""
    quote_type: str | None = None
    name: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in EXISTENCE_OK


@dataclass(frozen=True)
class ListingCheck:
    symbol: str
    ok: bool
    reason: str = ""
    quote_type: str | None = None
    name: str | None = None


class LookupBackend(Protocol):
    def quote(self, symbol: str) -> Quote | None: ...

    def search(self, query: str, limit: int = 8) -> list[Quote]: ...


def normalize_typed(raw: str) -> str:
    return (raw or "").strip().upper()


def syntax_ok(symbol: str) -> bool:
    return bool(symbol) and TICKER_RE.match(symbol) is not None


def is_reserved(symbol: str) -> bool:
    return symbol.lower() in {n.lower() for n in TICKER_BLOCKLIST}


def quote_is_usable(q: Quote | None) -> bool:
    """Reject Yahoo junk shells (no name, NONE type, sparse MUTUALFUND)."""
    if q is None:
        return False
    qt = (q.quote_type or "").upper()
    if qt in JUNK_QUOTE_TYPES or qt not in VALID_QUOTE_TYPES:
        return False
    name = (q.name or "").strip()
    if name:
        return True
    if qt in {"EQUITY", "ETF", "INDEX"} and q.n_fields >= 40 and q.price is not None:
        return True
    return False


class YahooBackend:
    """Live yfinance lookup. Network. Not used in unit tests."""

    def quote(self, symbol: str) -> Quote | None:
        yf = _import_yfinance()
        t = yf.Ticker(symbol)
        info: dict[str, Any] = {}
        try:
            raw = t.info
            if isinstance(raw, dict):
                info = raw
        except Exception:  # noqa: BLE001
            info = {}
        qt = info.get("quoteType") or info.get("quote_type")
        name = info.get("shortName") or info.get("longName")
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        try:
            fi = t.fast_info
            price = price or getattr(fi, "last_price", None)
            qt = qt or getattr(fi, "quote_type", None) or getattr(fi, "quoteType", None)
        except Exception:  # noqa: BLE001
            pass
        if not info and price is None and not qt:
            return None
        return Quote(
            symbol=str(info.get("symbol") or symbol).upper(),
            quote_type=str(qt).upper() if qt else None,
            name=str(name) if name else None,
            n_fields=len(info),
            price=_as_float(price),
        )

    def search(self, query: str, limit: int = 8) -> list[Quote]:
        yf = _import_yfinance()
        try:
            found = yf.Search(query, max_results=limit)
            rows = getattr(found, "quotes", None) or []
        except Exception:  # noqa: BLE001
            return []
        out: list[Quote] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol") or "").upper()
            if not sym:
                continue
            out.append(
                Quote(
                    symbol=sym,
                    quote_type=str(row.get("quoteType") or "").upper() or None,
                    name=str(row.get("shortname") or row.get("longname") or "") or None,
                    n_fields=len(row),
                    price=None,
                )
            )
        return out


class FakeBackend:
    """In-memory backend for tests."""

    def __init__(self, quotes: dict[str, Quote], search_hits: dict[str, list[Quote]] | None = None):
        self._quotes = {k.upper(): v for k, v in quotes.items()}
        self._search = {k.upper(): list(v) for k, v in (search_hits or {}).items()}

    def quote(self, symbol: str) -> Quote | None:
        return self._quotes.get(symbol.upper())

    def search(self, query: str, limit: int = 8) -> list[Quote]:
        return list(self._search.get(query.upper(), []))[:limit]


def _import_yfinance():  # pragma: no cover - exercised live
    try:
        import yfinance as yf  # type: ignore

        return yf
    except ImportError as e:
        raise RuntimeError(
            "yfinance not installed. Use the vendor/mcp/yfinance-market-mcp venv python, "
            "or pass --skip-ticker-check only for harness tests."
        ) from e


def _as_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _has_search_listing(backend: LookupBackend, typed: str) -> bool:
    for hit in backend.search(typed, limit=8):
        if quote_is_usable(hit) and (hit.symbol or "").upper():
            return True
    return False


def check_ticker(raw: str, *, backend: LookupBackend | None = None) -> TickerCheck:
    typed = normalize_typed(raw)
    if not typed:
        return TickerCheck(typed="", status="abort_syntax", reason="empty ticker")
    if not syntax_ok(typed):
        return TickerCheck(
            typed=typed,
            status="abort_syntax",
            reason="ticker must be letters/digits with optional . - ^ /",
        )
    be = backend or YahooBackend()
    direct = be.quote(typed)
    if quote_is_usable(direct):
        assert direct is not None
        return TickerCheck(
            typed=typed,
            status="quoted",
            quote_type=direct.quote_type,
            name=direct.name,
            reason="market quote found",
        )
    if is_reserved(typed):
        return TickerCheck(
            typed=typed,
            status="abort_reserved",
            reason=f"{typed} is a harness reserved name, not a market ticker",
        )
    if not _has_search_listing(be, typed):
        return TickerCheck(
            typed=typed,
            status="abort_unknown",
            reason=(
                f"{typed} is not a real market ticker and Yahoo search found no listing. "
                "Aborted — do not scaffold or invent research."
            ),
        )
    return TickerCheck(
        typed=typed,
        status="search_evidence",
        reason=(
            f"{typed} has no live quote under that exact symbol, but Yahoo search "
            "found at least one listing. Session ticker stays typed. Orchestrator "
            "must confirm the listing with tools and stamp quote_symbol."
        ),
    )


def live_ticker_check(raw: str) -> TickerCheck:
    """Production Yahoo existence check. Tests inject FakeBackend via check_ticker."""
    return check_ticker(raw, backend=YahooBackend())


def confirm_listing(symbol: str, *, backend: LookupBackend | None = None) -> ListingCheck:
    """Yahoo-quote a proposed listing. Does not decide issuer identity."""
    sym = normalize_typed(symbol)
    if not sym or not syntax_ok(sym):
        return ListingCheck(symbol=sym, ok=False, reason="invalid listing symbol")
    be = backend or YahooBackend()
    q = be.quote(sym)
    if quote_is_usable(q) and q is not None:
        return ListingCheck(
            symbol=sym,
            ok=True,
            reason="listing quotes",
            quote_type=q.quote_type,
            name=q.name,
        )
    return ListingCheck(
        symbol=sym,
        ok=False,
        reason=f"{sym} is not a usable Yahoo quote",
    )


def quote_symbol_from_session(session: Path) -> str | None:
    """Confirmed Yahoo listing, or None. No ticker fallback. Does not re-lookup."""
    man_path = session / "meta" / "run_manifest.json"
    if not man_path.is_file():
        return None
    try:
        man = json.loads(man_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(man, dict):
        return None
    val = man.get("quote_symbol")
    if val is None:
        return None
    s = str(val).strip().upper()
    return s or None


def confirm_session_listing(
    session: Path, *, backend: LookupBackend | None = None
) -> ListingCheck:
    stamp = quote_symbol_from_session(session)
    if not stamp:
        return ListingCheck(
            symbol="",
            ok=False,
            reason="quote_symbol not stamped on run_manifest",
        )
    return confirm_listing(stamp, backend=backend)
