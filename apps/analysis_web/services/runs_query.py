"""Shared runs-list query params (HTML, fragment, JSON). One meaning per key."""

from __future__ import annotations

from typing import Any

from fastapi import Query


def blank(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def runs_list_q(
    ticker: str | None = None,
    ticker_prefix: str | None = None,
    sector: str | None = None,
    region: str | None = None,
    audit_verdict: str | None = None,
    experiment_id: str | None = None,
    tech_signal: str | None = None,
    harness_version: str | None = None,
    session_date_from: str | None = None,
    session_date_to: str | None = None,
    mos_min: str | None = None,
    mos_max: str | None = None,
    price_min: str | None = None,
    price_max: str | None = None,
    fv_base_min: str | None = None,
    fv_base_max: str | None = None,
    sort: str | None = None,
    dir: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    return {
        "ticker": blank(ticker),
        "ticker_prefix": blank(ticker_prefix),
        "sector": blank(sector),
        "region": blank(region),
        "audit": blank(audit_verdict),
        "experiment_id": blank(experiment_id),
        "tech_signal": blank(tech_signal),
        "harness_version": blank(harness_version),
        "session_date_from": blank(session_date_from),
        "session_date_to": blank(session_date_to),
        "mos_min": blank(mos_min),
        "mos_max": blank(mos_max),
        "price_min": blank(price_min),
        "price_max": blank(price_max),
        "fv_base_min": blank(fv_base_min),
        "fv_base_max": blank(fv_base_max),
        "limit": limit,
        "sort": blank(sort),
        "dir": blank(dir),
    }


def catalog_filters(q: dict[str, Any]) -> dict[str, Any]:
    """Kwargs for CatalogApi.list_runs / count_runs (no sort/limit/offset)."""
    return {
        "ticker": q.get("ticker"),
        "ticker_prefix": q.get("ticker_prefix"),
        "sector": q.get("sector"),
        "region": q.get("region"),
        "experiment_id": q.get("experiment_id"),
        "audit_verdict": q.get("audit"),
        "tech_signal": q.get("tech_signal"),
        "harness_version": q.get("harness_version"),
        "session_date_from": q.get("session_date_from"),
        "session_date_to": q.get("session_date_to"),
        "mos_min": q.get("mos_min"),
        "mos_max": q.get("mos_max"),
        "price_min": q.get("price_min"),
        "price_max": q.get("price_max"),
        "fv_base_min": q.get("fv_base_min"),
        "fv_base_max": q.get("fv_base_max"),
    }
