"""Analyze job pages (HTML) — schedule Mode A; do not author phases."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from packages.catalog_api.client import ArtifactDenied
from packages.catalog_api.session_files import list_session_artifacts, open_session_artifact
from packages.agent_jobs.capacity import limits
from packages.harness_pin.pin import list_versions
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
from apps.analysis_web.deps import get_api
from apps.analysis_web.services.render_markdown import (
    is_json_path,
    is_markdown_path,
    render_json_pretty,
    render_markdown,
)

router = APIRouter(tags=["analyze"])


def _templates(request: Request):
    return request.app.state.templates


def _render(request: Request, name: str, **ctx: Any) -> HTMLResponse:
    html = _templates(request).get_template(name).render(**ctx)
    return HTMLResponse(html)


def _error(request: Request, message: str, status: int, title: str = "Analyze") -> HTMLResponse:
    html = _templates(request).get_template("error.html").render(
        title=title,
        message=message,
    )
    return HTMLResponse(html, status_code=status)


@router.get("/analyze", response_class=HTMLResponse)
def page_analyzes(
    request: Request,
    ticker: str = "",
) -> HTMLResponse:
    ticker = (ticker or "").strip().upper()
    jobs = list_analyzes(archive_root(), ticker=ticker or None)
    return _render(
        request,
        "analyze.html",
        jobs=jobs,
        ticker=ticker,
        error=None,
        limits=limits(),
    )


@router.get("/analyze/new", response_class=HTMLResponse)
def page_analyze_new(
    request: Request,
    ticker: str = "",
    error: str = "",
) -> HTMLResponse:
    return _render(
        request,
        "analyze_new.html",
        ticker=(ticker or "").strip().upper(),
        error=error,
        limits=limits(),
        harness_versions=list_versions(),
        harness_version="live",
    )


@router.post("/analyze/new")
def post_analyze_new(
    request: Request,
    ticker: str = Form(""),
    session_date: str = Form(""),
    slug: str = Form(""),
    orchestrator_model: str = Form("grok-4.5"),
    subagent_model: str = Form(""),
    notes: str = Form(""),
    ingest_library: str = Form("0"),
    harness_version: str = Form("live"),
) -> Response:
    try:
        job = start_analyze(
            archive_root(),
            ticker,
            session_date=session_date.strip() or None,
            slug=slug.strip() or None,
            orchestrator_model=orchestrator_model.strip() or "grok-4.5",
            subagent_model=subagent_model.strip() or None,
            notes=notes.strip() or None,
            ingest_library=ingest_library not in ("", "0", "false", "False"),
            harness_version=harness_version.strip() or "live",
        )
    except AnalyzeTickerError as e:
        return page_analyze_new(request, ticker=ticker, error=str(e))
    except AnalyzeValidationError as e:
        return page_analyze_new(request, ticker=ticker, error=str(e))
    except AnalyzeBusy as e:
        return _error(request, str(e), 409)
    except (AnalyzeGrokMissing, AnalyzeRunbookMissing) as e:
        return _error(request, str(e), 503)
    except AnalyzeError as e:
        return _error(request, str(e), 500)
    cid = quote(str(job["analyze_id"]), safe=":")
    return RedirectResponse(f"/analyze/{cid}", status_code=303)


@router.get("/analyze/{analyze_id:path}", response_class=HTMLResponse)
def page_analyze_detail(
    request: Request,
    analyze_id: str,
    api=Depends(get_api),  # noqa: ARG001
) -> HTMLResponse:
    cid = analyze_id.strip()
    try:
        job = get_analyze(archive_root(), cid)
    except (AnalyzeNotFound, ValueError):
        return _error(request, f"Analyze not found: {cid}", 404)

    snapshot_ready = bool(job.get("snapshot_ready"))
    raw_root = str(job.get("session_root") or "").strip()
    session = Path(raw_root) if raw_root else None
    listed = []
    if session is not None and session.is_dir():
        try:
            listed = list_session_artifacts(session, snapshot_ready=snapshot_ready)
        except OSError:
            listed = []

    artifact_index = []
    for item in listed:
        rel = item["relpath"]
        href = ""
        if item.get("body_ok"):
            href = f"/analyze-artifact?analyze_id={quote(cid, safe='')}&path={quote(rel, safe='')}"
        artifact_index.append(
            {
                "name": item["name"],
                "relpath": rel,
                "size_bytes": item.get("size_bytes"),
                "href": href,
                "body_ok": item.get("body_ok"),
            }
        )

    return _render(
        request,
        "analyze_detail.html",
        job=job,
        artifact_index=artifact_index,
        complete=job.get("status") == "complete",
        snapshot_ready=snapshot_ready,
    )


@router.post("/analyze-cancel")
def post_analyze_cancel(analyze_id: str = Form("")) -> RedirectResponse:
    cid = analyze_id.strip()
    if not cid:
        return RedirectResponse("/analyze", status_code=303)
    try:
        cancel_analyze(archive_root(), cid)
    except (AnalyzeNotFound, ValueError):
        return RedirectResponse("/analyze", status_code=303)
    return RedirectResponse(f"/analyze/{quote(cid, safe=':')}", status_code=303)


@router.post("/analyze-discard")
def post_analyze_discard(request: Request, analyze_id: str = Form("")) -> Response:
    cid = analyze_id.strip()
    if not cid:
        return RedirectResponse("/analyze", status_code=303)
    try:
        discard_analyze(archive_root(), cid)
    except AnalyzeDiscardRefused as e:
        return _error(request, str(e), 409)
    except (AnalyzeNotFound, ValueError):
        return RedirectResponse("/analyze", status_code=303)
    return RedirectResponse(f"/analyze/{quote(cid, safe=':')}", status_code=303)


@router.post("/analyze/{analyze_id:path}/resume")
def post_analyze_resume(request: Request, analyze_id: str) -> Response:
    cid = analyze_id.strip()
    try:
        resume_analyze(archive_root(), cid)
    except AnalyzeResumeConflict as e:
        return _error(request, str(e), 409)
    except AnalyzeBusy as e:
        return _error(request, str(e), 409)
    except (AnalyzeGrokMissing, AnalyzeRunbookMissing) as e:
        return _error(request, str(e), 503)
    except AnalyzeValidationError as e:
        return _error(request, str(e), 400)
    except (AnalyzeNotFound, ValueError):
        return _error(request, f"Analyze not found: {cid}", 404)
    return RedirectResponse(f"/analyze/{quote(cid, safe=':')}", status_code=303)


@router.get("/analyze-artifact")
def page_analyze_artifact(
    request: Request,
    analyze_id: str = Query(""),
    path: str = Query(""),
) -> Response:
    cid = (analyze_id or "").strip()
    rel = (path or "").strip()
    if not cid or not rel:
        return _error(request, "Missing analyze_id or path", 400)
    try:
        job = get_analyze(archive_root(), cid)
    except (AnalyzeNotFound, ValueError):
        return _error(request, f"Analyze not found: {cid}", 404)
    session = Path(str(job.get("session_root") or ""))
    try:
        data = open_session_artifact(
            session, rel, snapshot_ready=bool(job.get("snapshot_ready"))
        )
    except ArtifactDenied as e:
        return _error(request, f"Denied: {e}", 403)
    except FileNotFoundError as e:
        return _error(request, f"Not found: {e}", 404)

    back = f"/analyze/{quote(cid, safe='')}"
    if is_markdown_path(rel):
        text = data.decode("utf-8", errors="replace")
        body_html = render_markdown(text)
        html = _templates(request).get_template("report.html").render(
            run_id=cid,
            relpath=rel,
            mode="markdown",
            body_html=body_html,
            body_text="",
            back_href=back,
            back_label="Analyze",
        )
        return HTMLResponse(html)
    if is_json_path(rel):
        pretty = render_json_pretty(data)
        html = _templates(request).get_template("report.html").render(
            run_id=cid,
            relpath=rel,
            mode="json",
            body_html="",
            body_text=pretty,
            back_href=back,
            back_label="Analyze",
        )
        return HTMLResponse(html)
    return Response(data, media_type="application/octet-stream")
