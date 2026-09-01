"""Harness visualization — projection of Pin.workflow_spec / agent_prompt."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from packages.harness_pin.pin import PinError, UnknownVersion, list_versions, resolve
from apps.analysis_web.services.render_markdown import render_markdown

router = APIRouter(tags=["harness"])


def _templates(request: Request):
    return request.app.state.templates


def _render(request: Request, name: str, **ctx: Any) -> HTMLResponse:
    html = _templates(request).get_template(name).render(**ctx)
    return HTMLResponse(html)


def _pin_or_none(version: str):
    try:
        return resolve(version)
    except UnknownVersion:
        return None


@router.get("/harness", response_class=HTMLResponse)
def page_harness(request: Request, version: str = "live") -> HTMLResponse:
    versions = list_versions()
    pin = _pin_or_none(version)
    if pin is None:
        html = _templates(request).get_template("error.html").render(
            title="Harness",
            message=f"not a folder under pins/ (going-forward pins only): {version}",
        )
        return HTMLResponse(html, status_code=404)
    try:
        spec = pin.workflow_spec()
    except PinError as e:
        return _render(request, "error.html", title="Harness", message=str(e))
    return _render(
        request,
        "harness.html",
        version=pin.version,
        label=pin.label,
        versions=versions,
        spec=spec,
        pin_root=str(pin.root),
    )


@router.get("/api/harness/spec")
def api_harness_spec(version: str = Query("live")) -> JSONResponse:
    pin = _pin_or_none(version)
    if pin is None:
        return JSONResponse(
            {"error": f"not a folder under pins/ (going-forward pins only): {version}"},
            status_code=404,
        )
    try:
        return JSONResponse(pin.workflow_spec())
    except PinError as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/harness/prompt")
def api_harness_prompt(
    agent: str = Query(...),
    version: str = Query("live"),
) -> JSONResponse:
    pin = _pin_or_none(version)
    if pin is None:
        return JSONResponse(
            {"error": f"not a folder under pins/ (going-forward pins only): {version}"},
            status_code=404,
        )
    try:
        payload = pin.agent_prompt(agent)
    except PinError as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    body = str(payload.get("body") or "")
    conventions = str(payload.get("conventions") or "")
    payload = dict(payload)
    payload["body_html"] = render_markdown(body)
    payload["conventions_html"] = render_markdown(conventions)
    payload["href"] = f"/api/harness/prompt?agent={quote(agent)}&version={quote(version)}"
    return JSONResponse(payload)
