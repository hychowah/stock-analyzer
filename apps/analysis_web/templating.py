"""Jinja environment helpers and filters."""

from __future__ import annotations

import json
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from apps.analysis_web.config import templates_dir


def fmt_num(v: Any, digits: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.{int(digits)}f}"
    except (TypeError, ValueError):
        return str(v)


HEADLINE_LABELS: dict[str, str] = {
    "asof_price": "As-of",
    "fv_base": "FV base",
    "fv_bear": "FV bear",
    "fv_bull": "FV bull",
    "margin_of_safety_pct": "MoS %",
    "audit_verdict": "Audit",
    "primary_sector": "Sector",
    "region": "Region",
    "verdict_line": "Verdict",
}


def headline_view(packet: dict[str, Any] | None) -> dict[str, Any] | None:
    """Project headline.json into {sessions, rows: [{label, cells}]}.

    The template iterates label/cells only. On-disk field key remains "values".
    """
    if not packet:
        return None
    sessions = [str(s) for s in (packet.get("sessions") or [])]
    rows: list[dict[str, Any]] = []
    for field in packet.get("fields") or []:
        if not isinstance(field, dict):
            continue
        name = str(field.get("field") or "")
        raw = field.get("values")
        cells_src = raw if isinstance(raw, dict) else {}
        label = HEADLINE_LABELS.get(name) or name.replace("_", " ").strip() or name
        rows.append({"label": label, "cells": [fmt_num(cells_src.get(key)) for key in sessions]})
    return {"sessions": sessions, "rows": rows}


def _as_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if n != n or n in (float("inf"), float("-inf")):
        return None
    return n


def downside_pct(price: Any, fv_bear: Any) -> float | None:
    """Percent drop from price to bear FV: (price - fv_bear) / price * 100."""
    p = _as_float(price)
    b = _as_float(fv_bear)
    if p is None or b is None or p == 0:
        return None
    return (p - b) / p * 100.0


def downside_title(price: Any, fv_bear: Any, vintage: str = "as-of") -> str:
    """Tooltip 'as-of · 400.00 → bear 350.00'. Empty when the value is missing."""
    if downside_pct(price, fv_bear) is None:
        return ""
    label = (vintage or "as-of").strip() or "as-of"
    return f"{label} · {fmt_num(price)} → bear {fmt_num(fv_bear)}"


def verdict_badge(v: Any) -> Markup:
    s = str(v or "")
    cls = "pass" if s.upper() == "PASS" else ("fail" if s.upper() == "FAIL" else "")
    return Markup(f'<span class="badge {cls}">{escape(s or "—")}</span>')


def create_templates() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir())),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["fmt_num"] = fmt_num
    env.filters["verdict_badge"] = verdict_badge
    env.filters["tojson"] = lambda v: Markup(json.dumps(v))
    env.globals["downside_pct"] = downside_pct
    env.globals["downside_title"] = downside_title
    return env
