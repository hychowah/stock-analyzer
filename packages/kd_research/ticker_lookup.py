"""Mode A market-ticker check: abort unknown symbols with no obvious match.

Does not auto-remap. If the typed symbol is not a real quote:
- one obvious match → abort and print it (user re-runs with that symbol)
- no obvious match → abort unknown
Real quote → ok (use the typed symbol, uppercased).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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
# Yahoo placeholder types for junk symbols.
JUNK_QUOTE_TYPES = frozenset({"NONE", "N/A", ""})
MAX_EDIT_DISTANCE = 1
HK_DOT = re.compile(r"^0+(\d+)\.HK$", re.IGNORECASE)
DOT_CLASS = re.compile(r"^([A-Z]{1,5})\.([A-Z])$")


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
    status: str  # ok | abort_unknown | abort_match | abort_reserved | abort_syntax
    canonical: str | None = None
    matches: list[str] = field(default_factory=list)
    reason: str = ""
    quote_type: str | None = None
    name: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


class LookupBackend(Protocol):
    def quote(self, symbol: str) -> Quote | None: ...

    def search(self, query: str, limit: int = 8) -> list[Quote]: ...


def normalize_typed(raw: str) -> str:
    return (raw or "").strip().upper()


def syntax_ok(symbol: str) -> bool:
    return bool(symbol) and TICKER_RE.match(symbol) is not None


def is_reserved(symbol: str) -> bool:
    return symbol.lower() in {n.lower() for n in TICKER_BLOCKLIST}


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


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


def alias_candidates(symbol: str) -> list[str]:
    """Deterministic venue/punctuation rewrites (not fuzzy search)."""
    out: list[str] = []
    s = symbol.upper()
    m = DOT_CLASS.match(s)
    if m:
        out.append(f"{m.group(1)}-{m.group(2)}")
    if "-" in s and s.count("-") == 1:
        a, b = s.split("-", 1)
        if b.isalpha() and len(b) == 1:
            out.append(f"{a}.{b}")
    hk = HK_DOT.match(s)
    if hk:
        out.append(f"{hk.group(1)}.HK")
        out.append(f"{hk.group(1).zfill(4)}.HK")
    if s.endswith(".HK") and s[0] != "0":
        stem = s[: -len(".HK")]
        if stem.isdigit() and len(stem) < 4:
            out.append(f"{stem.zfill(4)}.HK")
    if s.isdigit() and 1 <= len(s) <= 5:
        out.append(f"{s.zfill(4)}.HK")
    seen = {s}
    uniq: list[str] = []
    for cand in out:
        if cand not in seen:
            seen.add(cand)
            uniq.append(cand)
    return uniq


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
            status="ok",
            canonical=typed,
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

    matches: list[str] = []
    for alias in alias_candidates(typed):
        q = be.quote(alias)
        if quote_is_usable(q) and q is not None:
            if q.symbol not in matches:
                matches.append(q.symbol)

    for hit in be.search(typed, limit=8):
        if not quote_is_usable(hit):
            continue
        if levenshtein(typed, hit.symbol) <= MAX_EDIT_DISTANCE:
            if hit.symbol != typed and hit.symbol not in matches:
                matches.append(hit.symbol)

    if len(matches) == 1:
        m = matches[0]
        return TickerCheck(
            typed=typed,
            status="abort_match",
            matches=matches,
            reason=(
                f"{typed} is not a real market ticker. Obvious match: {m}. "
                f"Re-run with --ticker {m}. Do not research {typed}."
            ),
        )
    if matches:
        listed = ", ".join(matches)
        return TickerCheck(
            typed=typed,
            status="abort_match",
            matches=matches,
            reason=(
                f"{typed} is not a real market ticker. Possible matches: {listed}. "
                "Re-run with one of those symbols. Do not research the typed symbol."
            ),
        )
    return TickerCheck(
        typed=typed,
        status="abort_unknown",
        reason=(
            f"{typed} is not a real market ticker and there is no obvious match. "
            "Aborted — do not scaffold or invent research."
        ),
    )


def require_market_ticker(raw: str, *, backend: LookupBackend | None = None) -> str:
    """Return canonical ticker or raise ValueError (abort)."""
    result = check_ticker(raw, backend=backend)
    if result.ok and result.canonical:
        return result.canonical
    raise ValueError(result.reason or f"ticker {raw!r} rejected")
