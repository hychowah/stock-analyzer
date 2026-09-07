"""Portfolio book loader + catalog join (display only; no FV invention).

When ``.local/portfolio.sqlite`` exists it is the only book (IB statement).
``portfolio.json`` is the fallback if sqlite is missing. An unreadable sqlite
fails the page; it does not fall back to JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from packages.catalog_api.client import CatalogApi, DbMissing

from apps.analysis_web.config import local_dir
from apps.analysis_web.services.ib_statement import IbStatement


DEFAULT_BOOK_NAME = "portfolio.json"

# Overlay only. The book always shows ib_symbol.
_CATALOG_OVERRIDES = {
    "HY9H": "000660.KS",
    "MC": "MC.PA",
    "ADYEN": "ADYEN",
}
_US_EXCHANGES = frozenset({"NYSE", "NASDAQ", "ARCA", "AMEX", "BATS", "NYSEARCA"})


@dataclass
class PositionSpec:
    ticker: str
    weight: float | None = None
    shares: float | None = None
    notes: str = ""


@dataclass
class PortfolioBook:
    name: str = "default"
    currency: str = "USD"
    positions: list[PositionSpec] = field(default_factory=list)
    path: Path | None = None
    error: str | None = None


def book_path(*, filename: str = DEFAULT_BOOK_NAME) -> Path:
    return local_dir() / filename


def map_catalog_ticker(ib_symbol: str, listing_exch: str | None = None) -> str | None:
    """View-time overlay: IB symbol + listing → catalog ticker. Not stored."""
    sym = (ib_symbol or "").strip().upper()
    if not sym:
        return None
    if sym in _CATALOG_OVERRIDES:
        return _CATALOG_OVERRIDES[sym]
    exch = (listing_exch or "").strip().upper()
    if exch == "SEHK":
        digits = sym.split(".")[0]
        if digits.isdigit():
            return f"{int(digits):04d}.HK"
        return f"{sym}.HK"
    if exch in {"TSEJ", "TSE"}:
        return sym if sym.endswith(".T") else f"{sym}.T"
    if exch in _US_EXCHANGES:
        return sym
    if "." in sym:
        return sym
    return None


def catalog_lookup_tickers(ib_symbol: str, listing_exch: str | None = None) -> list[str]:
    """Primary overlay plus a 5-digit HK variant (02318.HK vs 2318.HK)."""
    primary = map_catalog_ticker(ib_symbol, listing_exch)
    if not primary:
        return []
    out = [primary]
    if primary.endswith(".HK"):
        num = primary[:-3]
        if num.isdigit() and len(num) == 4:
            padded = f"0{num}.HK"
            if padded not in out:
                out.append(padded)
    return out


def mask_account(account_id: str) -> str:
    s = (account_id or "").strip()
    if len(s) <= 8:
        return s
    return f"{s[:5]}…{s[-3:]}"


def load_ib_statement() -> tuple[IbStatement | None, str | None]:
    """Return (statement, error). error set ⇒ sqlite present but unusable."""
    from apps.analysis_web.services.portfolio_store import StoreError, db_path, load as load_stmt

    p = db_path()
    if not p.is_file():
        return None, None
    try:
        stmt = load_stmt()
    except StoreError as e:
        return None, str(e)
    except OSError as e:
        return None, f"Failed to read IB book: {e}"
    if stmt is None:
        return None, "IB book has no statement"
    return stmt, None


def load_book(path: Path | None = None) -> PortfolioBook:
    """Load the JSON fallback book from app .local/ (never from archive/research)."""
    p = path or book_path()
    if not p.is_file():
        return PortfolioBook(
            path=p,
            error="No IB book yet. Import an activity statement or copy portfolio.example.json to .local/.",
        )
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return PortfolioBook(path=p, error=f"Failed to read book: {e}")

    if not isinstance(raw, dict):
        return PortfolioBook(path=p, error="portfolio root must be a JSON object")

    positions: list[PositionSpec] = []
    for i, item in enumerate(raw.get("positions") or []):
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        w = item.get("weight")
        s = item.get("shares")
        try:
            weight = float(w) if w is not None else None
        except (TypeError, ValueError):
            weight = None
        try:
            shares = float(s) if s is not None else None
        except (TypeError, ValueError):
            shares = None
        positions.append(
            PositionSpec(
                ticker=ticker,
                weight=weight,
                shares=shares,
                notes=str(item.get("notes") or ""),
            )
        )

    return PortfolioBook(
        name=str(raw.get("name") or "default"),
        currency=str(raw.get("currency") or "USD"),
        positions=positions,
        path=p,
        error=None if positions else "Book has no positions",
    )


def _resolve_weights(positions: list[PositionSpec]) -> list[float]:
    """Return non-negative weights that sum to 1 (or empty)."""
    if not positions:
        return []
    if all(p.weight is not None and p.weight >= 0 for p in positions):
        total = sum(float(p.weight or 0) for p in positions)
        if total > 0:
            return [float(p.weight or 0) / total for p in positions]
    if all(p.shares is not None and p.shares >= 0 for p in positions):
        total = sum(float(p.shares or 0) for p in positions)
        if total > 0:
            return [float(p.shares or 0) / total for p in positions]
    # equal weight
    n = len(positions)
    return [1.0 / n] * n


def latest_run(
    api: CatalogApi,
    ticker: str,
    *,
    pass_only: bool = False,
) -> dict[str, Any] | None:
    try:
        rows = api.list_runs(
            ticker=ticker,
            audit_verdict="PASS" if pass_only else None,
            comparable_only=False,
            limit=1,
            offset=0,
        )
    except DbMissing:
        return None
    return rows[0] if rows else None


def _empty_performance() -> dict[str, Any]:
    return {"waterfall": [], "mtm": []}


def _bar_rows(items: list[dict[str, Any]], value_key: str) -> list[dict[str, Any]]:
    peak = max((abs(float(r[value_key] or 0)) for r in items), default=0.0)
    out: list[dict[str, Any]] = []
    for r in items:
        val = r[value_key]
        try:
            n = float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            n = 0.0
        sign = "pos" if n > 0 else ("neg" if n < 0 else "zero")
        row = dict(r)
        row["bar_pct"] = (100.0 * abs(n) / peak) if peak > 0 else 0.0
        row["sign"] = sign
        out.append(row)
    return out


_WATERFALL_TOTALS = frozenset(
    {"Starting Value", "Ending Value", "Starting NAV", "Ending NAV"}
)


def _waterfall_rows(stmt: IbStatement) -> list[dict[str, Any]]:
    """Starting/Ending as total rows; signed flows from a zero gutter."""
    items = [{"name": c.name, "value": c.value} for c in stmt.nav_components]
    flows = [r for r in items if r["name"] not in _WATERFALL_TOTALS]
    peak = max((abs(float(r["value"] or 0)) for r in flows), default=0.0)
    out: list[dict[str, Any]] = []
    for r in items:
        try:
            n = float(r["value"]) if r["value"] is not None else 0.0
        except (TypeError, ValueError):
            n = 0.0
        is_total = r["name"] in _WATERFALL_TOTALS
        sign = "pos" if n > 0 else ("neg" if n < 0 else "zero")
        out.append(
            {
                "name": r["name"],
                "value": r["value"],
                "kind": "total" if is_total else "flow",
                "sign": sign,
                "bar_pct": (50.0 * abs(n) / peak) if (not is_total and peak > 0) else 0.0,
            }
        )
    return out


def _performance(stmt: IbStatement) -> dict[str, Any]:
    waterfall = _waterfall_rows(stmt)
    stocks = [m for m in stmt.mtm if (m.asset_category or "").lower() == "stocks"]
    ranked = sorted(stocks, key=lambda m: abs(m.pl_total or 0.0), reverse=True)
    top, rest = ranked[:20], ranked[20:]
    mtm_items: list[dict[str, Any]] = [
        {"ib_symbol": m.ib_symbol, "pl": m.pl_total} for m in top
    ]
    if rest:
        mtm_items.append(
            {"ib_symbol": "other", "pl": sum(m.pl_total or 0.0 for m in rest)}
        )
    return {"waterfall": waterfall, "mtm": _bar_rows(mtm_items, "pl")}


def _catalog_fields(run: dict[str, Any] | None) -> dict[str, Any]:
    mos = (run or {}).get("margin_of_safety_pct")
    try:
        mos_f = float(mos) if mos is not None else None
    except (TypeError, ValueError):
        mos_f = None
    return {
        "covered": run is not None,
        "run_id": (run or {}).get("run_id"),
        "session_key": (run or {}).get("session_key"),
        "session_date": (run or {}).get("session_date"),
        "asof_price": (run or {}).get("asof_price"),
        "fv_bear": (run or {}).get("fv_bear"),
        "fv_base": (run or {}).get("fv_base"),
        "margin_of_safety_pct": mos_f,
        "audit_verdict": (run or {}).get("audit_verdict"),
        "decision_action": (run or {}).get("decision_action"),
        "quote_listing": (run or {}).get("quote_listing"),
        "quote_listing_source": (run or {}).get("quote_listing_source"),
        "tech_signal": (run or {}).get("tech_signal"),
        "primary_sector": (run or {}).get("primary_sector"),
        "region": (run or {}).get("region"),
    }


def _view_from_statement(
    api: CatalogApi,
    stmt: IbStatement,
    *,
    pass_only: bool = False,
) -> dict[str, Any]:
    stocks = [
        p
        for p in stmt.positions
        if (p.asset_category or "Stocks").lower() == "stocks"
    ]
    bases: list[float | None] = [stmt.value_base(p.value, p.currency) for p in stocks]
    known = [b for b in bases if b is not None and b >= 0]
    total_base = sum(known)
    rows: list[dict[str, Any]] = []
    mos_w_sum = 0.0
    mos_w_tot = 0.0
    mos_vals: list[float] = []
    n_pass = 0
    n_covered = 0

    for i, pos in enumerate(stocks):
        vb = bases[i]
        w = (vb / total_base) if (vb is not None and total_base > 0) else 0.0
        candidates = catalog_lookup_tickers(pos.ib_symbol, pos.listing_exch)
        catalog_ticker = candidates[0] if candidates else None
        run = None
        for cand in candidates:
            run = latest_run(api, cand, pass_only=pass_only)
            if run is not None:
                catalog_ticker = cand
                break
        fields = _catalog_fields(run)
        if fields["covered"]:
            n_covered += 1
        if str(fields["audit_verdict"] or "").upper() == "PASS":
            n_pass += 1
        mos_f = fields["margin_of_safety_pct"]
        if mos_f is not None and fields["covered"]:
            mos_vals.append(mos_f)
            mos_w_sum += mos_f * w
            mos_w_tot += w
        rows.append(
            {
                "ticker": pos.ib_symbol,
                "ib_symbol": pos.ib_symbol,
                "listing_exch": pos.listing_exch,
                "catalog_ticker": catalog_ticker,
                "yahoo_listing": catalog_ticker,
                "weight": w,
                "shares": pos.quantity,
                "quantity": pos.quantity,
                "notes": pos.description,
                "currency": pos.currency,
                "close_price": pos.close_price,
                "value_native": pos.value,
                "value_base": vb,
                "unrealized_pl": pos.unrealized_pl,
                **fields,
            }
        )

    n = len(stocks)
    cash = stmt.nav_asset("Cash")
    stock_nav = stmt.nav_asset("Stock")
    ib = {
        "account_id": stmt.account_id,
        "account_masked": mask_account(stmt.account_id),
        "broker": stmt.broker,
        "period_from": stmt.period_from,
        "period_to": stmt.period_to,
        "base_currency": stmt.base_currency,
        "starting_nav": stmt.starting_nav,
        "ending_nav": stmt.ending_nav,
        "twr_pct": stmt.twr_pct,
        "deposits_total": stmt.deposits_total,
        "trade_count": len(stmt.trades),
        "stock_value": stock_nav.current_total if stock_nav else total_base,
        "cash_value": cash.current_total if cash else None,
        "source_csv": stmt.source_csv,
    }
    summary = {
        "n_positions": n,
        "n_covered": n_covered,
        "n_missing": max(0, n - n_covered),
        "n_pass": n_pass,
        "coverage_pct": (100.0 * n_covered / n) if n else None,
        "pass_coverage_pct": (100.0 * n_pass / n) if n else None,
        "mean_mos_pct": (sum(mos_vals) / len(mos_vals)) if mos_vals else None,
        "weighted_mean_mos_pct": (mos_w_sum / mos_w_tot) if mos_w_tot > 0 else None,
        "pass_only": pass_only,
        "weight_mode": "value_base",
        "trade_count": len(stmt.trades),
    }
    return {
        "name": f"IB · {mask_account(stmt.account_id)}",
        "currency": stmt.base_currency,
        "path": stmt.source_csv,
        "error": None,
        "summary": summary,
        "positions": rows,
        "ib": ib,
        "performance": _performance(stmt),
        "note": (
            "Holdings, NAV, and TWR are from the IB activity statement. "
            "asof_price/FV/MoS come from catalog research as-of snapshots, "
            "not live market marks. TWR is IB-reported for the statement period."
        ),
    }


def build_portfolio_view(
    api: CatalogApi,
    book: PortfolioBook | None = None,
    *,
    statement: IbStatement | None = None,
    pass_only: bool = False,
) -> dict[str, Any]:
    """Join holdings to latest catalog runs. ``statement`` wins over JSON book."""
    if statement is not None:
        return _view_from_statement(api, statement, pass_only=pass_only)

    if book is None:
        book = load_book()
    weights = _resolve_weights(book.positions)
    rows: list[dict[str, Any]] = []
    mos_w_sum = 0.0
    mos_w_tot = 0.0
    mos_vals: list[float] = []
    n_pass = 0
    n_covered = 0

    for i, pos in enumerate(book.positions):
        w = weights[i] if i < len(weights) else 0.0
        run = latest_run(api, pos.ticker, pass_only=pass_only)
        fields = _catalog_fields(run)
        if fields["covered"]:
            n_covered += 1
        if str(fields["audit_verdict"] or "").upper() == "PASS":
            n_pass += 1
        mos_f = fields["margin_of_safety_pct"]
        if mos_f is not None and fields["covered"]:
            mos_vals.append(mos_f)
            mos_w_sum += mos_f * w
            mos_w_tot += w

        rows.append(
            {
                "ticker": pos.ticker,
                "ib_symbol": pos.ticker,
                "listing_exch": None,
                "catalog_ticker": pos.ticker,
                "yahoo_listing": pos.ticker,
                "weight": w,
                "shares": pos.shares,
                "notes": pos.notes,
                **fields,
            }
        )

    n = len(book.positions)
    summary = {
        "n_positions": n,
        "n_covered": n_covered,
        "n_missing": max(0, n - n_covered),
        "n_pass": n_pass,
        "coverage_pct": (100.0 * n_covered / n) if n else None,
        "pass_coverage_pct": (100.0 * n_pass / n) if n else None,
        "mean_mos_pct": (sum(mos_vals) / len(mos_vals)) if mos_vals else None,
        "weighted_mean_mos_pct": (mos_w_sum / mos_w_tot) if mos_w_tot > 0 else None,
        "pass_only": pass_only,
        "weight_mode": _weight_mode(book.positions),
    }
    return {
        "name": book.name,
        "currency": book.currency,
        "path": str(book.path) if book.path else None,
        "error": book.error,
        "summary": summary,
        "positions": rows,
        "ib": None,
        "performance": _empty_performance(),
        "note": (
            "asof_price/FV/MoS come from catalog research as-of snapshots, "
            "not live market marks."
        ),
    }


def active_portfolio_view(
    api: CatalogApi,
    *,
    pass_only: bool = False,
) -> dict[str, Any]:
    """Sqlite book if present; JSON fallback only when sqlite is missing."""
    stmt, err = load_ib_statement()
    if err:
        return {
            "name": "IB book",
            "currency": "",
            "path": None,
            "error": err,
            "summary": None,
            "positions": [],
            "ib": None,
            "performance": _empty_performance(),
            "note": "",
        }
    if stmt is not None:
        return build_portfolio_view(api, statement=stmt, pass_only=pass_only)
    return build_portfolio_view(api, load_book(), pass_only=pass_only)


def _weight_mode(positions: list[PositionSpec]) -> str:
    if not positions:
        return "empty"
    if all(p.weight is not None and p.weight >= 0 for p in positions):
        if sum(float(p.weight or 0) for p in positions) > 0:
            return "weight"
    if all(p.shares is not None and p.shares >= 0 for p in positions):
        if sum(float(p.shares or 0) for p in positions) > 0:
            return "shares"
    return "equal"
