"""Compare job pages (HTML) and artifact serving."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment

from packages.catalog_api.client import (
    ArtifactDenied,
    CatalogApi,
    CompareNotFound,
    DbMissing,
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
from apps.analysis_web.services.render_markdown import (
    is_json_path,
    is_markdown_path,
    is_text_path,
    render_json_pretty,
    render_markdown,
)

router = APIRouter(tags=["compares"])


def _templates(request: Request) -> Environment:
    return request.app.state.templates


def _render(request: Request, name: str, **ctx: Any) -> HTMLResponse:
    html = _templates(request).get_template(name).render(**ctx)
    return HTMLResponse(html)


def _error(request: Request, message: str, status: int, title: str = "Compare") -> HTMLResponse:
    html = _templates(request).get_template("error.html").render(
        title=title,
        message=message,
    )
    return HTMLResponse(html, status_code=status)


def _start(
    run_id_a: str,
    run_id_b: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    return start_compare(
        archive_root(),
        run_id_a.strip(),
        run_id_b.strip(),
        force=force,
    )


@router.get("/compares", response_class=HTMLResponse)
def page_compares(
    request: Request,
    ticker: str = "",
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    ticker = (ticker or "").strip().upper()
    jobs = list_compares(archive_root(), ticker=ticker or None)
    return _render(
        request,
        "compares.html",
        jobs=jobs,
        ticker=ticker,
        health=api.health(),
    )


@router.get("/compares/new", response_class=HTMLResponse)
def page_compare_new(
    request: Request,
    run_id_a: str = "",
    run_id_b: str = "",
    error: str = "",
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    runs: list[dict[str, Any]] = []
    try:
        runs = api.list_runs(limit=200, comparable_only=True)
    except DbMissing:
        runs = []
    return _render(
        request,
        "compare_new.html",
        runs=runs,
        run_id_a=run_id_a.strip(),
        run_id_b=run_id_b.strip(),
        error=error,
    )


@router.post("/compares/new")
def post_compare_new(
    request: Request,
    run_id_a: str = Form(""),
    run_id_b: str = Form(""),
    force: str = Form("0"),
    api: CatalogApi = Depends(get_api),  # noqa: ARG001
) -> Response:
    want_force = force not in ("", "0", "false", "False")
    try:
        job = _start(run_id_a, run_id_b, force=want_force)
    except CompareValidationError as e:
        return page_compare_new(
            request,
            run_id_a=run_id_a,
            run_id_b=run_id_b,
            error=str(e),
            api=api,
        )
    except CompareBusy as e:
        return _error(request, str(e), 409)
    except GrokMissing as e:
        return _error(request, str(e), 503)
    except CompareError as e:
        return _error(request, str(e), 500)
    cid = quote(str(job["compare_id"]), safe=":")
    return RedirectResponse(f"/compares/{cid}", status_code=303)


@router.get("/compares/{compare_id:path}", response_class=HTMLResponse)
def page_compare_detail(
    request: Request,
    compare_id: str,
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    cid = compare_id.strip()
    try:
        job = get_compare(archive_root(), cid)
        listed = api.list_compare_artifacts(cid)
    except (CompareNotFound, JobNotFound, ValueError):
        return _error(request, f"Compare not found: {cid}", 404)
    except ArtifactDenied as e:
        return _error(request, str(e), 403)

    headline: dict[str, Any] | None = None
    try:
        raw = api.open_compare_artifact(cid, "headline.json")
        import json

        headline = json.loads(raw.decode("utf-8"))
    except (FileNotFoundError, ArtifactDenied, ValueError, OSError):
        headline = None

    readme_html = ""
    synthesis_html = ""
    if job.get("status") == "complete" or job.get("readme_ready") or job.get("synthesis_ready"):
        try:
            readme = api.open_compare_artifact(cid, "README.md").decode("utf-8", errors="replace")
            readme_html = render_markdown(readme)
        except (FileNotFoundError, ArtifactDenied, OSError):
            readme_html = ""
        try:
            syn = api.open_compare_artifact(cid, "99_synthesis.md").decode(
                "utf-8", errors="replace"
            )
            synthesis_html = render_markdown(syn)
        except (FileNotFoundError, ArtifactDenied, OSError):
            synthesis_html = ""

    artifact_index = []
    for item in listed:
        rel = item["relpath"]
        artifact_index.append(
            {
                "name": item["name"],
                "relpath": rel,
                "size_bytes": item.get("size_bytes"),
                "href": f"/compare-artifact?compare_id={quote(cid, safe='')}&path={quote(rel, safe='')}",
            }
        )

    return _render(
        request,
        "compare_detail.html",
        job=job,
        headline=headline,
        readme_html=readme_html,
        synthesis_html=synthesis_html,
        artifact_index=artifact_index,
        complete=job.get("status") == "complete",
    )


@router.post("/compare-cancel")
def post_compare_cancel(compare_id: str = Form("")) -> RedirectResponse:
    cid = compare_id.strip()
    if not cid:
        return RedirectResponse("/compares", status_code=303)
    try:
        cancel_compare(archive_root(), cid)
    except (CompareNotFound, JobNotFound, ValueError):
        return RedirectResponse("/compares", status_code=303)
    return RedirectResponse(f"/compares/{quote(cid, safe=':')}", status_code=303)


@router.get("/compare-artifact")
def page_compare_artifact(
    request: Request,
    compare_id: str = Query(""),
    path: str = Query(""),
    raw: str = Query("0"),
    api: CatalogApi = Depends(get_api),
) -> Response:
    cid = (compare_id or "").strip()
    rel = (path or "").strip()
    want_raw = raw not in ("", "0", "false", "False")
    if not cid or not rel:
        return _error(request, "Missing compare_id or path", 400)
    try:
        data = api.open_compare_artifact(cid, rel)
    except ArtifactDenied as e:
        return _error(request, f"Denied: {e}", 403)
    except (CompareNotFound, FileNotFoundError) as e:
        return _error(request, f"Not found: {e}", 404)

    back = f"/compares/{quote(cid, safe='')}"
    if is_markdown_path(rel):
        text = data.decode("utf-8", errors="replace")
        if want_raw:
            html = _templates(request).get_template("artifact.html").render(
                run_id=cid, relpath=rel, text=text, back_href=back, back_label="Compare"
            )
            return HTMLResponse(html)
        body_html = render_markdown(text)
        html = _templates(request).get_template("report.html").render(
            run_id=cid,
            relpath=rel,
            mode="markdown",
            body_html=body_html,
            body_text="",
            back_href=back,
            back_label="Compare",
        )
        return HTMLResponse(html)
    if is_json_path(rel):
        pretty = render_json_pretty(data)
        html = _templates(request).get_template("report.html").render(
            run_id=cid,
            relpath=rel,
            mode="text",
            body_html="",
            body_text=pretty,
            back_href=back,
            back_label="Compare",
        )
        return HTMLResponse(html)
    if is_text_path(rel):
        text = data.decode("utf-8", errors="replace")
        html = _templates(request).get_template("report.html").render(
            run_id=cid,
            relpath=rel,
            mode="text",
            body_html="",
            body_text=text,
            back_href=back,
            back_label="Compare",
        )
        return HTMLResponse(html)
    return Response(content=data, media_type="application/octet-stream")
