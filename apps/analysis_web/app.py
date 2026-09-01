#!/usr/bin/env python3
"""Archive Analysis UI — catalog over packages.catalog_api plus Grok job scheduling.

Does not author research phases, fair values, or MoS. Schedules Mode A
(Analyze → new archive/research sessions) and Mode B Compare
(archive/comparisons/). Reads archive catalog only for completed runs.

Usage:
    python3 -m apps.analysis_web
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
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from apps.analysis_web.config import archive_root, static_dir
from apps.analysis_web.routes import analyze, api, artifacts, compares, events, harness, pages
from apps.analysis_web.templating import create_templates


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

    static_path = static_dir()
    static_path.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    app.include_router(pages.router)
    app.include_router(analyze.router)
    app.include_router(harness.router)
    app.include_router(compares.router)
    app.include_router(api.router)
    app.include_router(events.router)
    app.include_router(artifacts.router)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> HTMLResponse:  # noqa: ARG001
        import traceback

        tb = traceback.format_exc()
        html = app.state.templates.get_template("error.html").render(
            title="Error",
            message="Internal server error",
            detail=tb,
        )
        return HTMLResponse(html, status_code=500)

    return app


# ASGI entry for uvicorn / tests
app = create_app()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    root = archive_root()
    print("Archive Analysis UI")
    print(f"  ARCHIVE_ROOT={root}")
    print(f"  http://{args.host}:{args.port}/")
    try:
        import uvicorn
    except ImportError:
        print(
            "uvicorn is required. Install: pip install -r apps/analysis_web/requirements.txt",
            file=sys.stderr,
        )
        return 1
    uvicorn.run(
        "apps.analysis_web.app:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
