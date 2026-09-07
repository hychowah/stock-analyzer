"""Shared runs-list query params (HTML, fragment, JSON). One meaning per key."""

from __future__ import annotations

from fastapi import HTTPException, Query

from packages.catalog_api.client import RunQuery

# One list for FastAPI hrefs and runs.js. comparable_only is a route flag, not a URL key.
RUN_QUERY_KEYS: tuple[str, ...] = (
    "ticker",
    "ticker_prefix",
    "sector",
    "region",
    "experiment_id",
    "tech_signal",
    "harness_version",
    "session_date_from",
    "session_date_to",
    "mos_min",
    "mos_max",
    "price_min",
    "price_max",
    "fv_base_min",
    "fv_base_max",
    "sort",
    "dir",
    "audit_verdict",
    "latest",
    "limit",
)


def blank(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_latest(value: str | None) -> bool:
    text = blank(value)
    if text is None:
        return False
    lowered = text.lower()
    if lowered in ("1", "true", "yes", "on"):
        return True
    if lowered in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"invalid latest: {value!r}")


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
    latest: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> RunQuery:
    try:
        latest_flag = parse_latest(latest)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RunQuery(
        ticker=blank(ticker),
        ticker_prefix=blank(ticker_prefix),
        sector=blank(sector),
        region=blank(region),
        audit_verdict=blank(audit_verdict),
        experiment_id=blank(experiment_id),
        tech_signal=blank(tech_signal),
        harness_version=blank(harness_version),
        session_date_from=blank(session_date_from),
        session_date_to=blank(session_date_to),
        mos_min=blank(mos_min),
        mos_max=blank(mos_max),
        price_min=blank(price_min),
        price_max=blank(price_max),
        fv_base_min=blank(fv_base_min),
        fv_base_max=blank(fv_base_max),
        sort=blank(sort),
        dir=blank(dir),
        latest=latest_flag,
        limit=limit,
        comparable_only=False,
    )


def query_public_map(q: RunQuery) -> dict[str, object]:
    """URL/template fields from a RunQuery (no comparable_only / offset)."""
    return {key: getattr(q, key) for key in RUN_QUERY_KEYS}
