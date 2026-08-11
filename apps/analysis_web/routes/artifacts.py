"""Artifact / report serving (allowlisted via CatalogApi)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment

from packages.catalog_api.client import (
    ArtifactDenied,
    CatalogApi,
    DbMissing,
    RunNotFound,
)

from apps.analysis_web.deps import get_api
from apps.analysis_web.services.render_markdown import (
    is_json_path,
    is_markdown_path,
    is_text_path,
    render_json_pretty,
    render_markdown,
)

router = APIRouter(tags=["artifacts"])


def _templates(request: Request) -> Environment:
    return request.app.state.templates


def _error(request: Request, message: str, status: int) -> HTMLResponse:
    html = _templates(request).get_template("error.html").render(
        title="Artifact",
        message=message,
    )
    return HTMLResponse(html, status_code=status)


@router.get("/artifact")
def page_artifact(
    request: Request,
    run_id: str = Query(""),
    path: str = Query(""),
    raw: str = Query("0"),
    api: CatalogApi = Depends(get_api),
) -> Response:
    """Serve allowlisted session artifact.

    Markdown → sanitized HTML by default; pass raw=1 for source in <pre>.
    """
    rid = (run_id or "").strip()
    rel = (path or "").strip()
    want_raw = raw not in ("", "0", "false", "False")
    if not rid or not rel:
        return _error(request, "Missing run_id or path", 400)

    try:
        data = api.open_artifact(rid, rel)
    except ArtifactDenied as e:
        return _error(request, f"Denied: {e}", 403)
    except (RunNotFound, FileNotFoundError, DbMissing) as e:
        return _error(request, f"Not found: {e}", 404)

    # Markdown: rendered HTML (default) or raw source
    if is_markdown_path(rel):
        text = data.decode("utf-8", errors="replace")
        if want_raw:
            html = _templates(request).get_template("artifact.html").render(
                run_id=rid, relpath=rel, text=text
            )
            return HTMLResponse(html)
        body_html = render_markdown(text)
        html = _templates(request).get_template("report.html").render(
            run_id=rid,
            relpath=rel,
            mode="markdown",
            body_html=body_html,
            body_text="",
        )
        return HTMLResponse(html)

    # JSON: pretty-printed in <pre>
    if is_json_path(rel):
        pretty = render_json_pretty(data)
        html = _templates(request).get_template("report.html").render(
            run_id=rid,
            relpath=rel,
            mode="text",
            body_html="",
            body_text=pretty,
        )
        return HTMLResponse(html)

    # Plain text
    if is_text_path(rel):
        text = data.decode("utf-8", errors="replace")
        html = _templates(request).get_template("report.html").render(
            run_id=rid,
            relpath=rel,
            mode="text",
            body_html="",
            body_text=text,
        )
        return HTMLResponse(html)

    lower = rel.lower()
    if lower.endswith(".png"):
        return Response(content=data, media_type="image/png")
    if lower.endswith((".jpg", ".jpeg")):
        return Response(content=data, media_type="image/jpeg")
    return Response(content=data, media_type="application/octet-stream")
