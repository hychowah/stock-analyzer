#!/usr/bin/env python3
"""Archive Analysis UI — catalog over packages.catalog_api plus Grok job scheduling.

Does not author research phases, fair values, or MoS. Schedules Mode A
(Analyze → new archive/research sessions) and Mode B Compare
(archive/comparisons/). Reads archive catalog only for completed runs.

Usage:
    python3 -m apps.analysis_web
    python3 -m apps.analysis_web --no-auto-restart
    ARCHIVE_ROOT=/path/to/archive python3 -m apps.analysis_web --port 8765
"""

from __future__ import annotations

import argparse
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Project root on path (same pattern as packages / scripts)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope

from apps.analysis_web.config import archive_root, static_dir
from apps.analysis_web.identity import boot_git_sha
from apps.analysis_web.routes import analyze, api, architecture, artifacts, compares, events, harness, histories, pages
from apps.analysis_web.services.price_history import (
    HistoryService,
    YahooHistoryBackend,
    history_ttl_sec,
)
from apps.analysis_web.services.quotes import QuoteService, YahooPrintBackend, quote_ttl_sec
from apps.analysis_web.templating import create_templates, render_page


def _prefers_html(request: Request) -> bool:
    """True when Accept ranks text/html at least as high as application/json."""
    raw = request.headers.get("accept") or ""
    html_q = -1.0
    json_q = -1.0
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        bits = [b.strip() for b in token.split(";")]
        media = bits[0].lower()
        q = 1.0
        for param in bits[1:]:
            if param.startswith("q="):
                try:
                    q = float(param[2:].strip())
                except ValueError:
                    q = 0.0
        if q <= 0:
            continue
        if media in ("text/html", "application/xhtml+xml"):
            html_q = max(html_q, q)
        elif media == "application/json":
            json_q = max(json_q, q)
    return html_q >= 0 and html_q >= json_q


class StaticFilesNoCache(StaticFiles):
    """Revalidate on every request so JS/CSS cannot stick after a file change."""

    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    try:
        from packages.research_jobs.jobs import reconcile_analyze_jobs

        reconcile_analyze_jobs(archive_root())
    except Exception:
        pass
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Archive Analysis",
        description="Catalog UI plus job scheduler: Analyze starts Mode A; Compare appends archive/comparisons/. Does not author phases or FV.",
        version="2.3.0",
        lifespan=_lifespan,
    )
    app.state.templates = create_templates()
    app.state.git_sha = boot_git_sha()
    app.state.quote_service = QuoteService(YahooPrintBackend(), ttl_sec=quote_ttl_sec())
    app.state.history_service = HistoryService(
        YahooHistoryBackend(), ttl_sec=history_ttl_sec()
    )

    static_path = static_dir()
    static_path.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFilesNoCache(directory=str(static_path)), name="static")

    @app.get("/favicon.ico")
    def favicon() -> Response:
        return Response(status_code=204)

    app.include_router(pages.router)
    app.include_router(architecture.router)
    app.include_router(analyze.router)
    app.include_router(harness.router)
    app.include_router(compares.router)
    app.include_router(histories.router)
    app.include_router(api.router)
    app.include_router(events.router)
    app.include_router(artifacts.router)

    @app.exception_handler(StarletteHTTPException)
    async def negotiate_http_exception(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404 and _prefers_html(request):
            message = exc.detail if isinstance(exc.detail, str) else "Not Found"
            return render_page(
                request,
                "error.html",
                status_code=404,
                title="Not Found",
                message=message,
            )
        return await http_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> HTMLResponse:  # noqa: ARG001
        import traceback

        tb = traceback.format_exc()
        return render_page(
            request,
            "error.html",
            status_code=500,
            title="Error",
            message="Internal server error",
            detail=tb,
        )

    return app


# ASGI entry for uvicorn / tests
app = create_app()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument(
        "--no-auto-restart",
        action="store_true",
        help="One-shot server: do not replace this process when git HEAD moves.",
    )
    args = ap.parse_args(argv)
    root = archive_root()
    print("Archive Analysis UI")
    print(f"  ARCHIVE_ROOT={root}")
    print(f"  http://{args.host}:{args.port}/")
    from apps.analysis_web.supervise import serve

    return serve(args.host, args.port, auto_restart=not args.no_auto_restart)


if __name__ == "__main__":
    raise SystemExit(main())
