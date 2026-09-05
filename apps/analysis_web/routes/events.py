"""SSE + poll endpoints for catalog/portfolio change notifications."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from apps.analysis_web.services.change_feed import (
    classify_change,
    dump_fingerprint,
    fingerprint,
)

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/fingerprint")
def api_fingerprint() -> dict[str, Any]:
    """Poll fallback: current catalog/portfolio fingerprint token."""
    fp = fingerprint()
    return {
        "token": fp["token"],
        "catalog_db_exists": fp["catalog_db_exists"],
        "portfolio_exists": fp["portfolio_exists"],
    }


def _sse_data(fp: dict[str, Any], git_sha: str | None = None) -> str:
    """Catalog fingerprint plus process identity (git_sha is not in the token)."""
    payload = json.loads(dump_fingerprint(fp))
    payload["git_sha"] = git_sha
    return json.dumps(payload, separators=(",", ":"))


async def _event_stream(
    *,
    interval_s: float = 1.5,
    once: bool = False,
    max_events: int | None = None,
    git_sha: str | None = None,
) -> AsyncIterator[str]:
    """Yield SSE frames when fingerprint changes.

    Always emits an initial ``hello`` event so clients can sync tokens
    and the UI boot SHA.
    """
    prev: dict[str, Any] | None = None
    emitted = 0
    while True:
        cur = fingerprint()
        if prev is None:
            yield f"event: hello\ndata: {_sse_data(cur, git_sha)}\n\n"
            prev = cur
            emitted += 1
            if once or (max_events is not None and emitted >= max_events):
                return
        else:
            events = classify_change(prev, cur)
            if events:
                data = _sse_data(cur, git_sha)
                for name in events:
                    yield f"event: {name}\ndata: {data}\n\n"
                    emitted += 1
                    if max_events is not None and emitted >= max_events:
                        return
                prev = cur
                if once:
                    return
        await asyncio.sleep(interval_s)


@router.get("/events")
async def api_events(
    request: Request,
    once: int = Query(0, ge=0, le=1, description="Emit hello then close (tests)"),
    max_events: int | None = Query(
        None, ge=1, le=50, description="Cap events then close (tests)"
    ),
    interval_ms: int = Query(1500, ge=200, le=30_000),
) -> StreamingResponse:
    """Server-Sent Events: hello | catalog_changed | portfolio_changed."""
    git_sha = getattr(request.app.state, "git_sha", None)
    gen = _event_stream(
        interval_s=interval_ms / 1000.0,
        once=bool(once),
        max_events=max_events,
        git_sha=git_sha if isinstance(git_sha, str) else None,
    )
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
