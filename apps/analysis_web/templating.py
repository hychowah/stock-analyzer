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
    return env
