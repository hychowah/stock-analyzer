"""JSON API routes for the analysis UI and other catalog clients."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from packages.catalog_api.client import (
    CatalogApi,
    CompareNotFound,
    DbMissing,
    RunNotFound,
    TickerNotFound,
)
from packages.compare_jobs.jobs import (
    CompareBusy,
    CompareError,
    CompareNotFound as JobNotFound,
    CompareValidationError,
    GrokMissing,
    cancel_compare,
    get_compare,
    list_compares,
    start_compare,
)

from apps.analysis_web.config import archive_root
from apps.analysis_web.deps import get_api
from apps.analysis_web.services.runs_query import catalog_filters, runs_list_q

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
def api_health(api: CatalogApi = Depends(get_api)) -> dict[str, Any]:
    return api.health()


@router.get("/runs")
def api_list_runs(
    q: dict[str, Any] = Depends(runs_list_q),
    offset: int = Query(0, ge=0),
    api: CatalogApi = Depends(get_api),
) -> dict[str, Any]:
    filters = catalog_filters(q)
    try:
        api.require_ticker(ticker=q.get("ticker"), ticker_prefix=q.get("ticker_prefix"))
        rows = api.list_runs(
            sort=q["sort"],
            dir=q["dir"],
            limit=q["limit"],
            offset=offset,
            **filters,
        )
        total = api.count_runs(**filters)
    except TickerNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except DbMissing as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {
        "runs": rows,
        "limit": q["limit"],
        "offset": offset,
        "count": len(rows),
        "total": total,
        "sort": q["sort"],
        "dir": q["dir"],
    }


@router.get("/runs/{run_id:path}")
def api_get_run(run_id: str, api: CatalogApi = Depends(get_api)) -> dict[str, Any]:
    try:
        return api.get_run(run_id.strip())
    except RunNotFound as e:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from e
    except DbMissing as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/portfolio")
def api_portfolio(
    pass_only: str = "0",
    api: CatalogApi = Depends(get_api),
) -> dict[str, Any]:
    """JSON portfolio view: local book joined to latest catalog runs."""
    from apps.analysis_web.services.portfolio import build_portfolio_view, load_book

    po = pass_only not in ("", "0", "false", "False")
    book = load_book()
    return build_portfolio_view(api, book, pass_only=po)


class CompareStartBody(BaseModel):
    run_id_a: str = Field(..., min_length=1)
    run_id_b: str = Field(..., min_length=1)
    force: bool = False


@router.get("/compares")
def api_list_compares(
    ticker: str | None = None,
    api: CatalogApi = Depends(get_api),  # noqa: ARG001
) -> dict[str, Any]:
    rows = list_compares(archive_root(), ticker=ticker)
    return {"compares": rows, "count": len(rows)}


@router.post("/compares", status_code=202)
def api_start_compare(body: CompareStartBody) -> dict[str, Any]:
    try:
        job = start_compare(
            archive_root(),
            body.run_id_a,
            body.run_id_b,
            force=body.force,
        )
    except CompareValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except CompareBusy as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except GrokMissing as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except CompareError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return job


@router.get("/compares/{compare_id:path}")
def api_get_compare(compare_id: str) -> dict[str, Any]:
    try:
        return get_compare(archive_root(), compare_id.strip())
    except (CompareNotFound, JobNotFound, ValueError) as e:
        raise HTTPException(status_code=404, detail=f"Compare not found: {compare_id}") from e


@router.post("/compares/{compare_id:path}/cancel")
def api_cancel_compare(compare_id: str) -> dict[str, Any]:
    cid = compare_id.strip()
    if cid.endswith("/cancel"):
        cid = cid[: -len("/cancel")]
    try:
        return cancel_compare(archive_root(), cid)
    except (CompareNotFound, JobNotFound, ValueError) as e:
        raise HTTPException(status_code=404, detail=f"Compare not found: {compare_id}") from e
