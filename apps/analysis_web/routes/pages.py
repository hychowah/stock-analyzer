"""HTML page routes (server-rendered)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment

from packages.catalog_api.client import (
    ArtifactDenied,
    CatalogApi,
    DbMissing,
    RunNotFound,
)

from apps.analysis_web.deps import get_api
from apps.analysis_web.templating import fmt_num

router = APIRouter(tags=["pages"])


def _templates(request: Request) -> Environment:
    return request.app.state.templates


def _render(request: Request, name: str, **ctx: Any) -> HTMLResponse:
    html = _templates(request).get_template(name).render(**ctx)
    return HTMLResponse(html)


@router.get("/", response_class=HTMLResponse)
def page_runs(
    request: Request,
    ticker: str | None = None,
    sector: str | None = None,
    region: str | None = None,
    audit_verdict: str | None = None,
    experiment_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    ticker = (ticker or "").strip() or None
    sector = (sector or "").strip() or None
    region = (region or "").strip() or None
    audit = (audit_verdict or "").strip() or None
    experiment_id = (experiment_id or "").strip() or None
    error = None
    runs: list[dict[str, Any]] = []
    try:
        runs = api.list_runs(
            ticker=ticker,
            sector=sector,
            region=region,
            audit_verdict=audit,
            experiment_id=experiment_id,
            limit=limit,
            offset=0,
        )
    except DbMissing as e:
        error = f"Database missing: {e}"
    return _render(
        request,
        "runs.html",
        runs=runs,
        limit=limit,
        ticker=ticker,
        sector=sector,
        region=region,
        audit=audit,
        experiment_id=experiment_id,
        error=error,
    )


@router.get("/runs", response_class=HTMLResponse)
def page_runs_alias(
    request: Request,
    ticker: str | None = None,
    sector: str | None = None,
    region: str | None = None,
    audit_verdict: str | None = None,
    experiment_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    return page_runs(
        request,
        ticker=ticker,
        sector=sector,
        region=region,
        audit_verdict=audit_verdict,
        experiment_id=experiment_id,
        limit=limit,
        api=api,
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
        html = _templates(request).get_template("error.html").render(
            title="Run",
            message=f"Run not found: {run_id}",
        )
        return HTMLResponse(html, status_code=404)
    except DbMissing as e:
        html = _templates(request).get_template("error.html").render(
            title="Run",
            message=f"DB missing: {e}",
        )
        return HTMLResponse(html, status_code=503)

    # Highlighted classic trio (when present) + full allowlisted reports/ index
    report_links: list[dict[str, Any]] = []
    for label, key in (
        ("README", "readme"),
        ("Fundamental", "fundamental"),
        ("Technical", "technical"),
    ):
        p = paths.get(key)
        if p:
            rel = None
            try:
                from pathlib import Path

                root = Path(str(paths["session_root"]))
                rel = Path(str(p)).resolve().relative_to(root.resolve()).as_posix()
            except Exception:
                rel = None
            if rel:
                href = f"/artifact?run_id={quote(run_id, safe='')}&path={quote(rel, safe='')}"
                report_links.append({"label": label, "href": href, "rel": rel})
            else:
                report_links.append({"label": label, "href": None, "rel": None})
        else:
            report_links.append({"label": label, "href": None, "missing": True})

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
                "href": f"/artifact?run_id={quote(run_id, safe='')}&path={quote(rel, safe='')}",
            }
        )

    return _render(
        request,
        "run_detail.html",
        run=run,
        report_links=report_links,
        artifact_index=artifact_index,
    )


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
    return _render(request, "health.html", health=api.health())


@router.get("/calibration", response_class=HTMLResponse)
def page_calibration(
    request: Request,
    horizon: str = "1m",
    pass_only: str = "1",
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    horizon = (horizon or "1m").strip() or "1m"
    po = pass_only != "0"
    try:
        report = api.calibration(horizon=horizon, pass_only=po)
    except DbMissing as e:
        return _render(
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
    return _render(
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
    except DbMissing as e:
        return _render(
            request,
            "error.html",
            title="Experiments",
            message=str(e),
        )
    by_exp: dict[str, list[dict[str, Any]]] = {}
    for r in runs:
        eid = r.get("experiment_id") or "(none)"
        by_exp.setdefault(str(eid), []).append(r)

    sections: list[dict[str, Any]] = []
    for eid, group in sorted(by_exp.items(), key=lambda x: (-len(x[1]), x[0])):
        if eid == "(none)" and len(by_exp) > 1:
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
    return _render(request, "experiments.html", sections=sections)


@router.get("/portfolio", response_class=HTMLResponse)
def page_portfolio(
    request: Request,
    pass_only: str = "0",
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    from apps.analysis_web.services.portfolio import build_portfolio_view, load_book

    po = pass_only not in ("", "0", "false", "False")
    book = load_book()
    view = build_portfolio_view(api, book, pass_only=po)
    return _render(
        request,
        "portfolio.html",
        view=view,
        pass_only=po,
    )
