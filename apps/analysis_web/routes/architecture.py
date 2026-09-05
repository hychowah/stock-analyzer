"""Live ARCHITECTURE.md page — repo document, not a catalog artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from packages.kd_research.paths import PROJECT_ROOT
from apps.analysis_web.services.render_markdown import render_markdown

router = APIRouter(tags=["architecture"])


def architecture_md_path() -> Path:
    """Working-tree map. Not under ARCHIVE_ROOT; not a pin."""
    return PROJECT_ROOT / "ARCHITECTURE.md"


def _templates(request: Request):
    return request.app.state.templates


def _render(request: Request, name: str, **ctx: Any) -> HTMLResponse:
    html = _templates(request).get_template(name).render(**ctx)
    return HTMLResponse(html)


@router.get("/architecture", response_class=HTMLResponse)
def page_architecture(request: Request) -> HTMLResponse:
    path = architecture_md_path()
    if not path.is_file():
        html = _templates(request).get_template("error.html").render(
            title="Architecture",
            message="ARCHITECTURE.md is missing from the working tree.",
        )
        return HTMLResponse(html, status_code=404)
    text = path.read_text(encoding="utf-8")
    return _render(
        request,
        "architecture.html",
        body_html=render_markdown(text),
        source_path="ARCHITECTURE.md",
    )
