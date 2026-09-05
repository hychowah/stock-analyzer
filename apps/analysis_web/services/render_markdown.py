"""Safe markdown → HTML for research reports."""

from __future__ import annotations

import html
import json
import re
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

_HEADING_RE = re.compile(r"<h([1-6])>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)


def _visible_text(inner: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", inner))


def github_heading_id(text: str) -> str:
    """GitHub-style slug so in-doc #anchors match ARCHITECTURE.md links."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def _with_heading_ids(fragment: str) -> str:
    """Inject heading ids after sanitizing. Never copy an id from source HTML."""
    seen: dict[str, int] = {}

    def repl(match: re.Match[str]) -> str:
        level, inner = match.group(1), match.group(2)
        slug = github_heading_id(_visible_text(inner)) or "heading"
        n = seen.get(slug, 0)
        seen[slug] = n + 1
        if n:
            slug = f"{slug}-{n}"
        return f'<h{level} id="{slug}">{inner}</h{level}>'

    return _HEADING_RE.sub(repl, fragment)


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
    cleaned = bleach.clean(
        cleaned,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
    return _with_heading_ids(cleaned)


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
