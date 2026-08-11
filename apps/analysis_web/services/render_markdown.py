"""Safe markdown → HTML for research reports."""

from __future__ import annotations

import json
from typing import Any

import bleach
from markdown_it import MarkdownIt

# Keep tight: research reports need structure, not scripts.
_ALLOWED_TAGS = frozenset(
    {
        "a",
        "abbr",
        "b",
        "blockquote",
        "br",
        "code",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "img",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "ul",
    }
)
_ALLOWED_ATTRS: dict[str, list[str]] = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title"],
    "th": ["align", "colspan", "rowspan"],
    "td": ["align", "colspan", "rowspan"],
    "code": ["class"],
    "pre": ["class"],
    "div": ["class"],
    "span": ["class"],
}
_ALLOWED_PROTOCOLS = frozenset({"http", "https", "mailto"})


def _md_engine() -> MarkdownIt:
    # html=False: do not pass through raw HTML from markdown source
    md = MarkdownIt("commonmark", {"breaks": True, "html": False})
    md.enable("table")
    md.enable("strikethrough")
    return md


_MD = _md_engine()


def render_markdown(text: str) -> str:
    """Convert markdown to sanitized HTML (safe for untrusted research notes)."""
    raw_html = _MD.render(text or "")
    cleaned = bleach.clean(
        raw_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
    # Defense in depth: drop any remaining javascript: / data: href/src
    return bleach.clean(
        cleaned,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )


def render_json_pretty(data: bytes | str | Any) -> str:
    """Pretty-print JSON as escaped text (caller wraps in <pre>)."""
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="replace")
    elif isinstance(data, str):
        text = data
    else:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    try:
        obj = json.loads(text)
        return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    except json.JSONDecodeError:
        return text


def is_markdown_path(relpath: str) -> bool:
    lower = relpath.lower()
    return lower.endswith(".md") or lower.endswith(".markdown")


def is_text_path(relpath: str) -> bool:
    lower = relpath.lower()
    return lower.endswith(".txt")


def is_json_path(relpath: str) -> bool:
    return relpath.lower().endswith(".json")
