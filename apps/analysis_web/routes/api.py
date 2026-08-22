"""JSON API routes for the analysis UI and other catalog clients."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.catalog_api.client import CatalogApi, DbMissing, RunNotFound

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
        rows = api.list_runs(
            sort=q["sort"],
            dir=q["dir"],
            limit=q["limit"],
            offset=offset,
            **filters,
        )
        total = api.count_runs(**filters)
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
