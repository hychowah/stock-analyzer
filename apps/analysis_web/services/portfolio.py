"""Portfolio book loader + catalog join (display only; no FV invention)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from packages.catalog_api.client import CatalogApi, DbMissing

from apps.analysis_web.config import local_dir


DEFAULT_BOOK_NAME = "portfolio.json"


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


def load_book(path: Path | None = None) -> PortfolioBook:
    """Load portfolio JSON from app .local/ (never from archive/research)."""
    p = path or book_path()
    if not p.is_file():
        return PortfolioBook(
            path=p,
            error=f"No book at {p}. Copy portfolio.example.json → .local/portfolio.json",
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


def build_portfolio_view(
    api: CatalogApi,
    book: PortfolioBook,
    *,
    pass_only: bool = False,
) -> dict[str, Any]:
    """Join book positions to latest catalog runs; compute display aggregates."""
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
        covered = run is not None
        if covered:
            n_covered += 1
        audit = (run or {}).get("audit_verdict")
        if str(audit or "").upper() == "PASS":
            n_pass += 1
        mos = (run or {}).get("margin_of_safety_pct")
        mos_f: float | None
        try:
            mos_f = float(mos) if mos is not None else None
        except (TypeError, ValueError):
            mos_f = None
        if mos_f is not None and covered:
            mos_vals.append(mos_f)
            mos_w_sum += mos_f * w
            mos_w_tot += w

        rows.append(
            {
                "ticker": pos.ticker,
                "weight": w,
                "shares": pos.shares,
                "notes": pos.notes,
                "covered": covered,
                "run_id": (run or {}).get("run_id"),
                "session_key": (run or {}).get("session_key"),
                "asof_price": (run or {}).get("asof_price"),
                "fv_base": (run or {}).get("fv_base"),
                "margin_of_safety_pct": mos_f,
                "audit_verdict": audit,
                "tech_signal": (run or {}).get("tech_signal"),
                "primary_sector": (run or {}).get("primary_sector"),
                "region": (run or {}).get("region"),
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
        "note": (
            "asof_price/FV/MoS come from catalog research as-of snapshots, "
            "not live market marks."
        ),
    }


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
