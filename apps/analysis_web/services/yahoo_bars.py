"""Yahoo OHLCV helpers. Listing symbols only. No catalog, FV, or MoS."""

from __future__ import annotations

from typing import Any


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


def split_download(data: Any, symbols: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {s: None for s in symbols}
    if data is None:
        return out
    empty = getattr(data, "empty", True)
    if empty:
        return out
    cols = getattr(data, "columns", None)
    if cols is not None and getattr(cols, "nlevels", 1) > 1:
        for sym in symbols:
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
) -> dict[str, list[tuple[float, str | None]]]:
    """symbol -> [(close, as_of), ...] from yf.download. Missing symbols are []."""
    empty: dict[str, list[tuple[float, str | None]]] = {s: [] for s in symbols}
    if not symbols:
        return empty
    try:
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
    out: dict[str, list[tuple[float, str | None]]] = {}
    for sym in symbols:
        out[sym] = close_series(frames.get(sym))
    return out
