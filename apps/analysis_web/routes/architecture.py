"""Live ARCHITECTURE.md page — repo document, not a catalog artifact."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from packages.kd_research.paths import PROJECT_ROOT
from apps.analysis_web.services.render_markdown import render_markdown
from apps.analysis_web.templating import render_page

router = APIRouter(tags=["architecture"])


def architecture_md_path() -> Path:
    """Working-tree map. Not under ARCHIVE_ROOT; not a pin."""
    return PROJECT_ROOT / "ARCHITECTURE.md"


@router.get("/architecture", response_class=HTMLResponse)
def page_architecture(request: Request) -> HTMLResponse:
    path = architecture_md_path()
    if not path.is_file():
        return render_page(
            request,
            "error.html",
            status_code=404,
            title="Architecture",
            message="ARCHITECTURE.md is missing from the working tree.",
        )
    text = path.read_text(encoding="utf-8")
    return render_page(
        request,
        "architecture.html",
        body_html=render_markdown(text),
        source_path="ARCHITECTURE.md",
    )
