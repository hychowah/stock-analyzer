"""Mark a portfolio book with last prints. Display math, not a valuation.

``mark_live_nav`` is a pure function: lots + quotes in, aggregates out.
No Yahoo, sqlite, or catalog. FX stays on the lot (statement close).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from apps.analysis_web.services.quotes import MAX_SYMBOLS, QuotePrint


@dataclass(frozen=True)
class MarkLot:
    """One stock lot the marker may reprice. No research fields."""

    ib_symbol: str
    listing: str | None
    quantity: float | None
    stmt_value_base: float | None
    stmt_fx: float | None


def _num(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        n = float(raw)
    except (TypeError, ValueError):
        return None
    if n != n or n in (float("inf"), float("-inf")):
        return None
    return n


def _listing(raw: Any) -> str | None:
    s = str(raw or "").strip().upper()
    return s or None


def lots_from_view(view: dict[str, Any]) -> list[MarkLot]:
    """Narrow lots from a portfolio view. Weights-only JSON → empty."""
    if view.get("error"):
        return []
    positions = view.get("positions") or []
    if not positions:
        return []
    if not view.get("ib"):
        if not all(_num(p.get("shares")) is not None for p in positions):
            return []
    out: list[MarkLot] = []
    for p in positions:
        if not isinstance(p, dict):
            continue
        qty = p.get("quantity")
        if qty is None:
            qty = p.get("shares")
        out.append(
            MarkLot(
                ib_symbol=str(p.get("ib_symbol") or p.get("ticker") or "").strip(),
                listing=_listing(p.get("print_listing")),
                quantity=_num(qty),
                stmt_value_base=_num(p.get("value_base")),
                stmt_fx=_num(p.get("stmt_fx")),
            )
        )
    return out


def fetch_prints(
    get_many: Callable[[list[str]], list[QuotePrint]],
    listings: list[str],
    *,
    chunk_size: int = MAX_SYMBOLS,
) -> list[QuotePrint]:
    """Call get_many in chunks. Caller injects QuoteService.get_many."""
    unique: list[str] = []
    seen: set[str] = set()
    for raw in listings:
        s = _listing(raw)
        if not s or s in seen:
            continue
        seen.add(s)
        unique.append(s)
    size = max(1, int(chunk_size))
    out: list[QuotePrint] = []
    for i in range(0, len(unique), size):
        out.extend(list(get_many(unique[i : i + size])))
    return out


def _quote_for(listing: str | None, quotes: dict[str, QuotePrint]) -> QuotePrint | None:
    if not listing:
        return None
    return quotes.get(listing.upper())


def _usable_print(q: QuotePrint | None) -> float | None:
    if q is None or q.error or q.price is None:
        return None
    return _num(q.price)


def mark_live_nav(
    lots: list[MarkLot],
    quotes_by_listing: dict[str, QuotePrint],
    *,
    ending_nav: float | None,
    cash: float | None = None,
) -> dict[str, Any]:
    """Reprice lots that have a last print and statement FX.

    Identity: live_nav = ending_nav + Σ (qty × print × stmt_fx − stmt_value_base).
    Unquoted / missing FX / missing statement value stay at the statement.
    ``ending_nav is None`` (JSON shares): live_nav is the sum of live lots.
    Empty lots and no ending_nav → no live NAV.
    """
    quotes_map = {str(k).upper(): v for k, v in quotes_by_listing.items()}
    n = len(lots)
    n_repriced = 0
    n_unquoted = 0
    delta_sum = 0.0
    live_stock = 0.0
    have_live_stock = False
    day_pl_sum = 0.0
    have_day = False
    as_of: str | None = None
    quote_rows: list[QuotePrint] = []
    seen_q: set[str] = set()
    rows: list[dict[str, Any]] = []

    for lot in lots:
        q = _quote_for(lot.listing, quotes_map)
        if lot.listing and lot.listing not in seen_q:
            seen_q.add(lot.listing)
            if q is not None:
                quote_rows.append(q)
        live_price = _usable_print(q)
        qty = lot.quantity
        fx = lot.stmt_fx
        stmt_val = lot.stmt_value_base
        can_mark = live_price is not None and qty is not None and fx is not None
        if ending_nav is not None:
            can_mark = can_mark and stmt_val is not None
        live_value: float | None = None
        lot_day_pl: float | None = None
        if can_mark:
            live_value = float(qty) * float(live_price) * float(fx)
            n_repriced += 1
            if stmt_val is not None:
                delta_sum += live_value - float(stmt_val)
            if q is not None and q.prev_close is not None:
                lot_day_pl = (
                    float(qty) * (float(live_price) - float(q.prev_close)) * float(fx)
                )
                day_pl_sum += lot_day_pl
                have_day = True
            if q is not None and q.as_of and (as_of is None or str(q.as_of) > as_of):
                as_of = str(q.as_of)
        else:
            n_unquoted += 1
        stock_piece = live_value if live_value is not None else stmt_val
        if stock_piece is not None:
            live_stock += float(stock_piece)
            have_live_stock = True
        err = None
        if q is not None and q.error:
            err = q.error
        elif not can_mark and live_price is None:
            err = (q.error if q is not None else None) or (
                "unquoted" if not lot.listing else "unavailable"
            )
        elif not can_mark and fx is None:
            err = "missing_fx"
        rows.append(
            {
                "ib_symbol": lot.ib_symbol,
                "listing": lot.listing,
                "quantity": qty,
                "live_price": live_price,
                "change_pct": None if q is None else q.change_pct,
                "day_pl": lot_day_pl,
                "stmt_value_base": stmt_val,
                "live_value_base": live_value,
                "print_kind": None if q is None else q.print_kind,
                "error": None if can_mark else err,
            }
        )

    live_nav: float | None
    vintage: str | None
    if n == 0:
        live_nav = ending_nav
        vintage = "statement" if ending_nav is not None else None
    elif ending_nav is not None:
        live_nav = float(ending_nav) + delta_sum
        if n_repriced == 0:
            vintage = "statement"
        elif n_unquoted == 0:
            vintage = "live"
        else:
            vintage = "partial"
    else:
        if n_repriced == 0:
            live_nav = None
            vintage = "statement"
        else:
            live_nav = sum(
                float(r["live_value_base"])
                for r in rows
                if r["live_value_base"] is not None
            )
            vintage = "live" if n_unquoted == 0 else "partial"

    delta: float | None = None
    delta_pct: float | None = None
    if ending_nav is not None and live_nav is not None:
        delta = live_nav - float(ending_nav)
        if float(ending_nav) != 0:
            delta_pct = (live_nav / float(ending_nav) - 1.0) * 100.0

    for row in rows:
        dp = row.get("day_pl")
        if dp is not None and live_nav not in (None, 0):
            row["contrib_pct"] = float(dp) / float(live_nav) * 100.0
        else:
            row["contrib_pct"] = None

    return {
        "statement_nav": ending_nav,
        "live_nav": live_nav,
        "delta": delta,
        "delta_pct": delta_pct,
        "day_pl": day_pl_sum if have_day else None,
        "cash_statement": cash,
        "stock_live": live_stock if have_live_stock else None,
        "vintage": vintage,
        "fx_vintage": "statement",
        "n_positions": n,
        "n_repriced": n_repriced,
        "n_unquoted": n_unquoted,
        "as_of": as_of,
        "quotes": [q.as_json() for q in quote_rows],
        "rows": rows,
    }
