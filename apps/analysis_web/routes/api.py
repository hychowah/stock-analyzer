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
from packages.research_jobs.jobs import (
    AnalyzeBusy,
    AnalyzeDiscardRefused,
    AnalyzeError,
    AnalyzeGrokMissing,
    AnalyzeNotFound,
    AnalyzeResumeConflict,
    AnalyzeRunbookMissing,
    AnalyzeTickerError,
    AnalyzeValidationError,
    cancel_analyze,
    discard_analyze,
    get_analyze,
    list_analyzes,
    resume_analyze,
    start_analyze,
)

from apps.analysis_web.config import archive_root
from apps.analysis_web.deps import get_api, get_quote_service
from apps.analysis_web.services.quotes import QuoteService, parse_symbol_query
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


@router.get("/quotes")
def api_quotes(
    symbols: str = Query("", description="Comma-separated Yahoo listing symbols"),
    svc: QuoteService = Depends(get_quote_service),
) -> dict[str, Any]:
    """Last print for listing symbols. Does not accept typed catalog tickers."""
    try:
        listings = parse_symbol_query(symbols)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    quotes = svc.get_many(listings)
    return {
        "quotes": [q.as_json() for q in quotes],
        "ttl_sec": svc.ttl_sec,
        "count": len(quotes),
    }


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


class AnalyzeStartBody(BaseModel):
    ticker: str = Field(..., min_length=1)
    session_date: str | None = None
    slug: str | None = None
    orchestrator_model: str | None = "grok-4.5"
    subagent_model: str | None = None
    notes: str | None = None
    ingest_library: bool = False
    harness_version: str | None = "live"


@router.get("/analyze")
def api_list_analyze(ticker: str | None = None) -> dict[str, Any]:
    rows = list_analyzes(archive_root(), ticker=ticker)
    return {"jobs": rows, "count": len(rows)}


@router.post("/analyze", status_code=202)
def api_start_analyze(body: AnalyzeStartBody) -> dict[str, Any]:
    try:
        return start_analyze(
            archive_root(),
            body.ticker,
            session_date=body.session_date,
            slug=body.slug,
            orchestrator_model=body.orchestrator_model or "grok-4.5",
            subagent_model=body.subagent_model,
            notes=body.notes,
            ingest_library=body.ingest_library,
            harness_version=body.harness_version or "live",
        )
    except AnalyzeTickerError as e:
        raise HTTPException(
            status_code=400,
            detail={"status": e.status, "reason": e.reason},
        ) from e
    except AnalyzeValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AnalyzeBusy as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (AnalyzeGrokMissing, AnalyzeRunbookMissing) as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except AnalyzeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/analyze/{analyze_id:path}")
def api_get_analyze(analyze_id: str) -> dict[str, Any]:
    try:
        return get_analyze(archive_root(), analyze_id.strip())
    except (AnalyzeNotFound, ValueError) as e:
        raise HTTPException(status_code=404, detail=f"Analyze not found: {analyze_id}") from e


@router.post("/analyze/{analyze_id:path}/cancel")
def api_cancel_analyze(analyze_id: str) -> dict[str, Any]:
    cid = analyze_id.strip()
    if cid.endswith("/cancel"):
        cid = cid[: -len("/cancel")]
    try:
        return cancel_analyze(archive_root(), cid)
    except (AnalyzeNotFound, ValueError) as e:
        raise HTTPException(status_code=404, detail=f"Analyze not found: {analyze_id}") from e


@router.post("/analyze/{analyze_id:path}/discard")
def api_discard_analyze(analyze_id: str) -> dict[str, Any]:
    cid = analyze_id.strip()
    if cid.endswith("/discard"):
        cid = cid[: -len("/discard")]
    try:
        return discard_analyze(archive_root(), cid)
    except AnalyzeDiscardRefused as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (AnalyzeNotFound, ValueError) as e:
        raise HTTPException(status_code=404, detail=f"Analyze not found: {analyze_id}") from e


@router.post("/analyze/{analyze_id:path}/resume")
def api_resume_analyze(analyze_id: str) -> dict[str, Any]:
    cid = analyze_id.strip()
    if cid.endswith("/resume"):
        cid = cid[: -len("/resume")]
    try:
        return resume_analyze(archive_root(), cid)
    except AnalyzeResumeConflict as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except AnalyzeBusy as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except AnalyzeValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (AnalyzeGrokMissing, AnalyzeRunbookMissing) as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except (AnalyzeNotFound, ValueError) as e:
        raise HTTPException(status_code=404, detail=f"Analyze not found: {analyze_id}") from e


@router.post("/compares/{compare_id:path}/cancel")
def api_cancel_compare(compare_id: str) -> dict[str, Any]:
    cid = compare_id.strip()
    if cid.endswith("/cancel"):
        cid = cid[: -len("/cancel")]
    try:
        return cancel_compare(archive_root(), cid)
    except (CompareNotFound, JobNotFound, ValueError) as e:
        raise HTTPException(status_code=404, detail=f"Compare not found: {compare_id}") from e
