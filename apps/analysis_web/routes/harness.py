"""Harness visualization — page model over Pin.workflow_spec / agent_prompt."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from packages.harness_pin.pin import PinError, UnknownVersion, list_versions, resolve
from apps.analysis_web.services.harness_view import harness_page_model, structure_prompt_payload

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


def _conventions_text(pin) -> str:
    """Shared preamble via Pin.agent_prompt so a published pin uses its own tree.

    Extra subprocess on GET /harness until workflow_spec carries the conventions
    body (Mode A / W1 follow-up).
    """
    try:
        payload = pin.agent_prompt("orchestrator")
    except PinError:
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("conventions") or "")


@router.get("/harness", response_class=HTMLResponse)
def page_harness(
    request: Request,
    version: str = "live",
    agent: str = "",
    phase: str = "",
) -> HTMLResponse:
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
    model = harness_page_model(spec, conventions=_conventions_text(pin))
    return _render(
        request,
        "harness.html",
        version=pin.version,
        label=pin.label,
        versions=versions,
        model=model,
        agent=agent.strip(),
        phase=phase.strip(),
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
    out = structure_prompt_payload(payload)
    out["href"] = f"/api/harness/prompt?agent={quote(agent)}&version={quote(version)}"
    return JSONResponse(out)
