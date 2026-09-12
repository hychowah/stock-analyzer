"""Artifact / report serving (allowlisted via CatalogApi)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response

from packages.catalog_api.client import (
    ArtifactDenied,
    CatalogApi,
    DbMissing,
    RunNotFound,
)

from apps.analysis_web.deps import get_api
from apps.analysis_web.templating import render_page
from apps.analysis_web.services.render_markdown import (
    is_json_path,
    is_markdown_path,
    is_text_path,
    render_json_pretty,
    render_session_report,
)

router = APIRouter(tags=["artifacts"])


def _error(request: Request, message: str, status: int) -> HTMLResponse:
    return render_page(
        request,
        "error.html",
        status_code=status,
        title="Artifact",
        message=message,
    )


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
            return render_page(
                request, "artifact.html", run_id=rid, relpath=rel, text=text
            )
        doc = render_session_report(text, run_id=rid, relpath=rel)
        toc = [
            {"id": item["id"], "title": item["text"], "h2": []}
            for item in doc["toc"]
            if int(item.get("level") or 0) == 2
        ]
        return render_page(
            request,
            "report.html",
            run_id=rid,
            relpath=rel,
            mode="markdown",
            title=doc["title"],
            toc=toc,
            body_html=doc["html"],
            body_text="",
            crumb_href=f"/runs/{rid}",
            crumb_label="Run",
            meta_line=rel,
            extra_links=[
                {
                    "href": f"/artifact?run_id={rid}&path={rel}&raw=1",
                    "label": "Raw source",
                }
            ],
            raw_href=f"/artifact?run_id={rid}&path={rel}&raw=1",
        )

    # JSON: pretty-printed in <pre>
    if is_json_path(rel):
        pretty = render_json_pretty(data)
        return render_page(
            request,
            "report.html",
            run_id=rid,
            relpath=rel,
            mode="text",
            title=rel,
            toc=[],
            body_html="",
            body_text=pretty,
            crumb_href=f"/runs/{rid}",
            crumb_label="Run",
            meta_line="",
            extra_links=[],
        )

    # Plain text
    if is_text_path(rel):
        text = data.decode("utf-8", errors="replace")
        return render_page(
            request,
            "report.html",
            run_id=rid,
            relpath=rel,
            mode="text",
            title=rel,
            toc=[],
            body_html="",
            body_text=text,
            crumb_href=f"/runs/{rid}",
            crumb_label="Run",
            meta_line="",
            extra_links=[],
        )

    lower = rel.lower()
    if lower.endswith(".png"):
        return Response(content=data, media_type="image/png")
    if lower.endswith((".jpg", ".jpeg")):
        return Response(content=data, media_type="image/jpeg")
    return Response(content=data, media_type="application/octet-stream")
