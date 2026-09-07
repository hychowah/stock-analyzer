"""HTML page routes (server-rendered)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from packages.catalog_api.client import (
    ArtifactDenied,
    CatalogApi,
    DbMissing,
    RunNotFound,
    RunQuery,
    SchemaStale,
    TickerNotFound,
)

from apps.analysis_web.deps import get_api
from apps.analysis_web.services.runs_query import (
    RUN_QUERY_KEYS,
    query_public_map,
    runs_list_q,
)
from apps.analysis_web.services.running import running_analyzes
from apps.analysis_web.templating import fmt_num, render_fragment, render_page

router = APIRouter(tags=["pages"])

_NUMERIC_SORT = frozenset(
    {
        "session_date",
        "asof_price",
        "fv_base",
        "margin_of_safety_pct",
        "harness_version",
        "asof_downside_pct",
    }
)
_SORT_HEADERS = (
    "ticker",
    "session_date",
    "harness_version",
    "primary_sector",
    "region",
    "asof_price",
    "fv_base",
    "margin_of_safety_pct",
    "asof_downside_pct",
    "audit_verdict",
    "tech_signal",
)


_HEALTH_LABELS: tuple[tuple[str, str], ...] = (
    ("archive_root", "Archive root"),
    ("db_path", "Database path"),
    ("db_exists", "Database exists"),
    ("research_exists", "Research folder"),
    ("library_exists", "Library folder"),
    ("comparisons_exists", "Comparisons folder"),
    ("schema_version", "Schema version"),
    ("run_count", "Completed runs"),
    ("max_exported_at", "Last catalog export"),
    ("error", "Error"),
)


def _health_rows(health: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, label in _HEALTH_LABELS:
        val = health.get(key)
        href = "/" if key == "run_count" and val is not None else None
        rows.append({"key": key, "label": label, "value": val, "href": href})
    return rows


def _first_dir(col: str) -> str:
    return "desc" if col in _NUMERIC_SORT else "asc"


def _next_dir(col: str, current_sort: str | None, current_dir: str | None) -> str:
    if current_sort == col:
        return "asc" if (current_dir or "asc") == "desc" else "desc"
    return _first_dir(col)


def _filter_href(q: RunQuery, **overrides: Any) -> str:
    merged = query_public_map(q)
    merged.update(overrides)
    params: dict[str, str] = {}
    for key in RUN_QUERY_KEYS:
        val = merged.get(key)
        if val in (None, ""):
            continue
        if key == "limit" and val in (None, 50):
            continue
        if key == "latest":
            if not val or str(val).strip().lower() in ("0", "false", "off", "no"):
                continue
            params[key] = "1"
            continue
        params[key] = str(val)
    if not params:
        return "/"
    return "/?" + urlencode(params)


def _sort_links(q: RunQuery) -> dict[str, str]:
    return {
        col: _filter_href(
            q, sort=col, dir=_next_dir(col, q.sort, q.dir)
        )
        for col in _SORT_HEADERS
    }


def _load_facets(api: CatalogApi) -> dict[str, list[str]]:
    empty = {"sector": [], "region": [], "tech_signal": [], "harness_version": []}
    try:
        return api.list_run_facets()
    except DbMissing:
        return empty


def _runs_context(api: CatalogApi, q: RunQuery) -> tuple[dict[str, Any], int]:
    error = None
    error_kind = None
    ticker_query = None
    runs: list[dict[str, Any]] = []
    total: int | None = None
    status = 200
    query = replace(q, comparable_only=False, offset=0)
    try:
        api.require_ticker(ticker=q.ticker, ticker_prefix=q.ticker_prefix)
        runs = api.list_runs(query)
        total = api.count_runs(query)
    except TickerNotFound as e:
        error = str(e)
        error_kind = "ticker_not_found"
        ticker_query = e.query
        status = 404
    except ValueError as e:
        error = str(e)
        status = 400
    except DbMissing as e:
        error = f"Database missing: {e}"
    except SchemaStale as e:
        error = str(e)
    ctx = {
        **query_public_map(q),
        "runs": runs,
        "total": total,
        "sort_links": _sort_links(q),
        "filter_href": lambda **overrides: _filter_href(q, **overrides),
        "facets": _load_facets(api),
        "error": error,
        "error_kind": error_kind,
        "ticker_query": ticker_query,
    }
    return ctx, status


@router.get("/", response_class=HTMLResponse)
def page_runs(
    request: Request,
    q: RunQuery = Depends(runs_list_q),
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    ctx, status = _runs_context(api, q)
    live, extra = running_analyzes()
    ctx["running_analyzes"] = live
    ctx["running_more"] = extra
    return render_page(request, "runs.html", status_code=status, **ctx)


@router.get("/runs", response_class=HTMLResponse)
def page_runs_alias(
    request: Request,
    q: RunQuery = Depends(runs_list_q),
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    return page_runs(request, q=q, api=api)


@router.get("/fragments/runs", response_class=HTMLResponse)
def fragment_runs(
    request: Request,
    q: RunQuery = Depends(runs_list_q),
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    ctx, status = _runs_context(api, q)
    return render_fragment(
        request, "partials/runs_table.html", status_code=status, **ctx
    )


@router.get("/runs/{run_id:path}", response_class=HTMLResponse)
def page_run(
    request: Request,
    run_id: str,
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    run_id = run_id.strip()
    try:
        run = api.get_run(run_id)
        paths = api.get_report_paths(run_id)
    except RunNotFound:
        return render_page(
            request,
            "error.html",
            status_code=404,
            title="Run",
            message=f"Run not found: {run_id}",
        )
    except DbMissing as e:
        return render_page(
            request,
            "error.html",
            status_code=503,
            title="Run",
            message=f"DB missing: {e}",
        )

    def _artifact_href(rel: str) -> str:
        return f"/artifact?run_id={quote(run_id, safe='')}&path={quote(rel, safe='')}"

    cio_href = None
    readme = paths.get("readme")
    if readme:
        try:
            from pathlib import Path

            root = Path(str(paths["session_root"]))
            rel = Path(str(readme)).resolve().relative_to(root.resolve()).as_posix()
        except Exception:
            rel = None
        if rel:
            cio_href = _artifact_href(rel)

    artifact_index: list[dict[str, Any]] = []
    try:
        listed = api.list_artifacts(run_id, prefix="reports/")
    except (RunNotFound, ArtifactDenied, DbMissing):
        listed = []
    for item in listed:
        rel = item["relpath"]
        artifact_index.append(
            {
                "name": item["name"],
                "relpath": rel,
                "size_bytes": item.get("size_bytes"),
                "href": _artifact_href(rel),
            }
        )

    football_href = None
    try:
        charts = api.list_artifacts(run_id, prefix="charts/")
    except (RunNotFound, ArtifactDenied, DbMissing):
        charts = []
    for item in charts:
        if item.get("name") == "valuation_football_field.png":
            football_href = _artifact_href(item["relpath"])
            break

    sibling_links: list[dict[str, Any]] = []
    comparable_siblings: list[dict[str, Any]] = []
    ticker = str(run.get("ticker") or "").strip()
    if ticker:
        try:
            for row in api.list_runs(ticker=ticker, limit=50, comparable_only=False):
                if row.get("run_id") != run_id:
                    rid = str(row.get("run_id") or "")
                    sibling_links.append(
                        {
                            "run_id": rid,
                            "session_key": row.get("session_key"),
                            "href": f"/runs/{rid}",
                        }
                    )
            for row in api.list_runs(ticker=ticker, limit=50, comparable_only=True):
                if row.get("run_id") != run_id:
                    comparable_siblings.append(row)
        except (DbMissing, ValueError):
            sibling_links = []
            comparable_siblings = []

    return render_page(
        request,
        "run_detail.html",
        run=run,
        artifact_index=artifact_index,
        football_href=football_href,
        cio_href=cio_href,
        sibling_links=sibling_links,
        comparable_siblings=comparable_siblings,
        chart_overlay=_chart_overlay(run, comparable_siblings),
    )


def _chart_num(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _chart_overlay(run: dict[str, Any], siblings: list[dict[str, Any]]) -> dict[str, Any]:
    """Catalog fields the chart may overlay. No Mode B FV."""
    return {
        "ticker": run.get("ticker"),
        "session_key": run.get("session_key"),
        "asof_date": run.get("session_date"),
        "asof_price": _chart_num(run.get("asof_price")),
        "fv_bear": _chart_num(run.get("fv_bear")),
        "fv_base": _chart_num(run.get("fv_base")),
        "fv_bull": _chart_num(run.get("fv_bull")),
        "fv_weighted": _chart_num(run.get("fv_weighted")),
        "currency": run.get("currency") or None,
        "siblings": [
            {
                "run_id": s.get("run_id"),
                "session_key": s.get("session_key"),
                "asof_date": s.get("session_date"),
                "asof_price": _chart_num(s.get("asof_price")),
                "fv_bear": _chart_num(s.get("fv_bear")),
                "fv_base": _chart_num(s.get("fv_base")),
                "fv_bull": _chart_num(s.get("fv_bull")),
            }
            for s in siblings
        ],
    }


@router.get("/run")
def legacy_run_redirect(run_id: str = "") -> RedirectResponse:
    """Bookmark compatibility: /run?run_id=… → /runs/…"""
    rid = (run_id or "").strip()
    if not rid:
        return RedirectResponse("/", status_code=302)
    return RedirectResponse(f"/runs/{rid}", status_code=302)


@router.get("/health", response_class=HTMLResponse)
def page_health(
    request: Request,
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    git_sha = getattr(request.app.state, "git_sha", None)
    if not isinstance(git_sha, str) or not git_sha.strip():
        git_sha = None
    health = api.health()
    return render_page(
        request,
        "health.html",
        health=health,
        git_sha=git_sha,
        health_rows=_health_rows(health),
    )


@router.get("/calibration", response_class=HTMLResponse)
def page_calibration(
    request: Request,
    horizon: str = "1m",
    pass_only: str = "0",
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    horizon = (horizon or "1m").strip() or "1m"
    po = pass_only not in ("", "0", "false", "False")
    try:
        report = api.calibration(horizon=horizon, pass_only=po)
    except DbMissing as e:
        return render_page(
            request,
            "error.html",
            title="Calibration",
            message=str(e),
        )
    overall = report.get("overall") or {}
    o_rate = overall.get("direction_hit_rate")
    overall_hit = f"{100 * o_rate:.1f}%" if isinstance(o_rate, float) else "—"
    overall_mean = fmt_num(overall.get("mean_return_pct"), 2)
    buckets = []
    for name, st in (report.get("by_mos_bucket") or {}).items():
        rate = st.get("direction_hit_rate")
        rate_s = f"{100 * rate:.1f}%" if isinstance(rate, float) else "—"
        buckets.append(
            {
                "name": name,
                "n": st.get("n"),
                "n_scored": st.get("n_scored"),
                "rate_s": rate_s,
                "mean_s": fmt_num(st.get("mean_return_pct"), 2),
            }
        )
    return render_page(
        request,
        "calibration.html",
        report=report,
        horizon=horizon,
        pass_only=po,
        overall_hit=overall_hit,
        overall_mean=overall_mean,
        buckets=buckets,
    )


@router.get("/experiments", response_class=HTMLResponse)
def page_experiments(
    request: Request,
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    try:
        runs = api.list_runs(limit=500)
    except (DbMissing, SchemaStale) as e:
        return render_page(
            request,
            "error.html",
            title="Experiments",
            message=str(e),
        )
    if not any(r.get("experiment_id") for r in runs):
        return render_page(request, "experiments.html", sections=[])
    by_exp: dict[str, list[dict[str, Any]]] = {}
    for r in runs:
        eid = r.get("experiment_id") or "(none)"
        by_exp.setdefault(str(eid), []).append(r)

    sections: list[dict[str, Any]] = []
    for eid, group in sorted(by_exp.items(), key=lambda x: (-len(x[1]), x[0])):
        if eid == "(none)":
            sections.append({"kind": "none", "count": len(group)})
            continue
        sections.append(
            {
                "kind": "group",
                "eid": eid,
                "count": len(group),
                "runs": group,
            }
        )
    return render_page(request, "experiments.html", sections=sections)


@router.get("/portfolio", response_class=HTMLResponse)
def page_portfolio(
    request: Request,
    pass_only: str = "0",
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    from apps.analysis_web.services.portfolio import active_portfolio_view

    po = pass_only not in ("", "0", "false", "False")
    view = active_portfolio_view(api, pass_only=po)
    return render_page(
        request,
        "portfolio.html",
        view=view,
        pass_only=po,
    )
