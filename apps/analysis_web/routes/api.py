"""JSON API routes for the analysis UI and other catalog clients."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from packages.catalog_api.client import (
    CatalogApi,
    CompareNotFound,
    DbMissing,
    RunNotFound,
    RunQuery,
    SchemaStale,
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
from apps.analysis_web.deps import get_api, get_history_service, get_quote_service
from apps.analysis_web.services.price_history import (
    HistoryService,
    bars_in_window,
    parse_history_symbol,
    parse_range,
    since_for_range,
)
from apps.analysis_web.services.quotes import QuoteService, parse_symbol_query
from apps.analysis_web.services.runs_query import runs_list_q

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
def api_health(api: CatalogApi = Depends(get_api)) -> dict[str, Any]:
    return api.health()


@router.get("/runs")
def api_list_runs(
    q: RunQuery = Depends(runs_list_q),
    offset: int = Query(0, ge=0),
    api: CatalogApi = Depends(get_api),
) -> dict[str, Any]:
    query = replace(q, offset=offset, comparable_only=False)
    try:
        api.require_ticker(ticker=q.ticker, ticker_prefix=q.ticker_prefix)
        rows = api.list_runs(query)
        total = api.count_runs(query)
    except TickerNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (DbMissing, SchemaStale) as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {
        "runs": rows,
        "limit": q.limit,
        "offset": offset,
        "count": len(rows),
        "total": total,
        "sort": q.sort,
        "dir": q.dir,
    }


@router.get("/runs/{run_id:path}")
def api_get_run(run_id: str, api: CatalogApi = Depends(get_api)) -> dict[str, Any]:
    try:
        return api.get_run(run_id.strip())
    except RunNotFound as e:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from e
    except (DbMissing, SchemaStale) as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/quotes")
def api_quotes(
    symbols: str = Query("", description="Comma-separated catalog quote_listing values"),
    svc: QuoteService = Depends(get_quote_service),
) -> dict[str, Any]:
    """Last print for requested listings. Chart-name repair is in yahoo_bars."""
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


@router.get("/price-history")
def api_price_history(
    symbol: str = Query("", description="One catalog quote_listing"),
    range_key: str = Query(
        "1y", alias="range", description="1m, 3m, 6m, 1y, 2y, 5y, or max"
    ),
    svc: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    """Daily closes for one requested listing. Chart-name repair is in yahoo_bars.

    ``?range=`` is the chart vocabulary. It is not the cache key.
    """
    try:
        listing = parse_history_symbol(symbol)
        parsed_range = parse_range(range_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    today = svc.today
    hist = svc.get(listing, since=since_for_range(parsed_range, today=today))
    sliced = bars_in_window(hist.bars, parsed_range, today=today)
    body = hist.as_json()
    body["range"] = parsed_range
    body["bars"] = [b.as_json() for b in sliced]
    body["count"] = len(sliced)
    body["ttl_sec"] = svc.ttl_sec
    return body


@router.get("/portfolio")
def api_portfolio(
    pass_only: str = "0",
    api: CatalogApi = Depends(get_api),
) -> dict[str, Any]:
    """JSON portfolio view: IB sqlite book (or JSON fallback) joined to catalog."""
    from apps.analysis_web.services.portfolio import active_portfolio_view

    po = pass_only not in ("", "0", "false", "False")
    return active_portfolio_view(api, pass_only=po)


def _empty_live_nav(*, ttl_sec: int, error: str | None = None) -> dict[str, Any]:
    return {
        "error": error,
        "base_currency": "",
        "statement_nav": None,
        "live_nav": None,
        "delta": None,
        "delta_pct": None,
        "day_pl": None,
        "cash_statement": None,
        "stock_live": None,
        "vintage": None,
        "fx_vintage": "statement",
        "period_to": None,
        "n_positions": 0,
        "n_repriced": 0,
        "n_unquoted": 0,
        "as_of": None,
        "ttl_sec": ttl_sec,
        "quotes": [],
        "rows": [],
    }


@router.get("/portfolio/live-nav")
def api_portfolio_live_nav(
    svc: QuoteService = Depends(get_quote_service),
) -> dict[str, Any]:
    """Mark current lots with last prints. Not a catalog join. Display math."""
    from apps.analysis_web.services.live_nav import (
        fetch_prints,
        load_live_lots,
        mark_live_nav,
    )

    lots, meta = load_live_lots()
    if meta.get("error") and not lots:
        return _empty_live_nav(ttl_sec=svc.ttl_sec, error=str(meta["error"]))
    listings = [lot.listing for lot in lots if lot.listing]
    prints = fetch_prints(svc.get_many, listings)
    by = {q.symbol.upper(): q for q in prints}
    ending = meta.get("ending_nav")
    try:
        ending_nav = float(ending) if ending is not None else None
    except (TypeError, ValueError):
        ending_nav = None
    cash = meta.get("cash")
    try:
        cash_f = float(cash) if cash is not None else None
    except (TypeError, ValueError):
        cash_f = None
    marked = mark_live_nav(lots, by, ending_nav=ending_nav, cash=cash_f)
    marked["base_currency"] = str(meta.get("base_currency") or "")
    marked["period_to"] = meta.get("period_to")
    marked["ttl_sec"] = svc.ttl_sec
    marked["error"] = None
    return marked


def _empty_mtm_path(*, error: str | None, period: str = "") -> dict[str, Any]:
    return {
        "error": error,
        "period": period,
        "start": None,
        "end": None,
        "start_nav": None,
        "base_currency": "",
        "frames": [],
    }


@router.get("/portfolio/mtm-path")
def api_portfolio_mtm_path(
    period: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
    svc: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    """Daily reconstructed MTM frames for the live IB book. Display math.

    Pass ``period=`` (1w, 1m, ytd, statement) or ``start=`` and ``end=``,
    not both.
    """
    from apps.analysis_web.services.mtm_path import (
        PeriodError,
        choose_path_args,
        mtm_path_for,
        mtm_path_window,
    )
    from apps.analysis_web.services.portfolio import load_ib_book

    try:
        kind, a, b = choose_path_args(period, start, end)
    except PeriodError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    token = a if kind == "period" else ""
    book, err = load_ib_book()
    if err:
        return _empty_mtm_path(error=str(err), period=token)
    if book is None:
        return _empty_mtm_path(error="No IB book yet.", period=token)
    try:
        if kind == "period":
            return mtm_path_for(book, svc, a)
        return mtm_path_window(book, svc, a, b)
    except PeriodError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def _empty_mtm_interval(*, error: str | None, period: str = "") -> dict[str, Any]:
    return {
        "error": error,
        "period": period,
        "start": None,
        "end": None,
        "start_nav": None,
        "base_currency": "",
        "rows": [],
    }


@router.get("/portfolio/mtm-interval")
def api_portfolio_mtm_interval(
    period: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
    svc: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    """One still: value(end) − value(start) + fill cash after start through end.

    Pass ``period=`` (1w, 1m, ytd, statement) or ``start=`` and ``end=``,
    not both. No frames, no bars. Display math.
    """
    from apps.analysis_web.services.mtm_path import (
        PeriodError,
        choose_path_args,
        mtm_interval_for,
        mtm_interval_window,
    )
    from apps.analysis_web.services.portfolio import load_ib_book

    try:
        kind, a, b = choose_path_args(period, start, end)
    except PeriodError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    token = a if kind == "period" else ""
    book, err = load_ib_book()
    if err:
        return _empty_mtm_interval(error=str(err), period=token)
    if book is None:
        return _empty_mtm_interval(error="No IB book yet.", period=token)
    try:
        if kind == "period":
            return mtm_interval_for(book, svc, a)
        return mtm_interval_window(book, svc, a, b)
    except PeriodError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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
