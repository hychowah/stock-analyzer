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

router = APIRouter(tags=["artifacts"])


def _templates(request: Request) -> Environment:
    return request.app.state.templates


@router.get("/artifact")
def page_artifact(
    request: Request,
    run_id: str = Query(""),
    path: str = Query(""),
    api: CatalogApi = Depends(get_api),
) -> Response:
    """Serve allowlisted session artifact (parity with WSGI MVP).

    Markdown/text/json are shown as escaped pre text in Phase 1.
    Phase 2 upgrades markdown to sanitized HTML.
    """
    rid = (run_id or "").strip()
    rel = (path or "").strip()
    if not rid or not rel:
        html = _templates(request).get_template("error.html").render(
            title="Artifact",
            message="Missing run_id or path",
        )
        return HTMLResponse(html, status_code=400)

    try:
        data = api.open_artifact(rid, rel)
    except ArtifactDenied as e:
        html = _templates(request).get_template("error.html").render(
            title="Artifact",
            message=f"Denied: {e}",
        )
        return HTMLResponse(html, status_code=403)
    except (RunNotFound, FileNotFoundError, DbMissing) as e:
        html = _templates(request).get_template("error.html").render(
            title="Artifact",
            message=f"Not found: {e}",
        )
        return HTMLResponse(html, status_code=404)

    lower = rel.lower()
    if lower.endswith((".md", ".txt", ".json")):
        text = data.decode("utf-8", errors="replace")
        html = _templates(request).get_template("artifact.html").render(
            run_id=rid,
            relpath=rel,
            text=text,
        )
        return HTMLResponse(html)

    ctype = "application/octet-stream"
    if lower.endswith(".png"):
        ctype = "image/png"
    elif lower.endswith((".jpg", ".jpeg")):
        ctype = "image/jpeg"
    return Response(content=data, media_type=ctype)
