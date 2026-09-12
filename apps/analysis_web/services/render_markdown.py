"""Safe markdown → HTML for research reports."""

from __future__ import annotations

import html
import json
import posixpath
import re
from typing import Any
from urllib.parse import quote, urlparse

import bleach
from markdown_it import MarkdownIt

from packages.catalog_api.client import DEFAULT_ALLOW_PREFIXES, DEFAULT_DENY_PREFIXES

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


_MERMAID_FENCE_RE = re.compile(
    r"<pre><code class=\"language-mermaid\">(.*?)</code></pre>",
    re.IGNORECASE | re.DOTALL,
)


def _unwrap_mermaid_fences(fragment: str) -> str:
    """Turn mermaid code fences into <pre class="mermaid"> for client-side draw.

    Leave the source text in the node. mermaid.js reads textContent and
    replaces the node with SVG. If JS does not run, the flowchart text stays.
    """

    def repl(match: re.Match[str]) -> str:
        return f'<pre class="mermaid">{match.group(1)}</pre>'

    return _MERMAID_FENCE_RE.sub(repl, fragment)


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
    return _unwrap_mermaid_fences(_with_heading_ids(cleaned))


_H1_RE = re.compile(r"<h1\b([^>]*)>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_TOC_RE = re.compile(
    r'<h([23])\b[^>]*\sid="([^"]+)"[^>]*>(.*?)</h\1>',
    re.IGNORECASE | re.DOTALL,
)
_A_HREF_RE = re.compile(
    r'(<a\b[^>]*?\s)href="([^"]*)"([^>]*>)',
    re.IGNORECASE,
)
_MD_EXT = (".md", ".markdown")


def _allowlisted_rel(norm: str) -> bool:
    if not any(norm == a.rstrip("/") or norm.startswith(a) for a in DEFAULT_ALLOW_PREFIXES):
        return False
    return not any(norm.startswith(d) for d in DEFAULT_DENY_PREFIXES)


def _rewrite_session_href(
    href: str,
    *,
    run_id: str,
    relpath: str,
    href_base: str,
    id_query: str,
) -> str | None:
    """Rewrite a relative .md href onto href_base, or None to drop the URL.

    Leave #fragments and http(s)/mailto alone. Reject `..` and targets the
    catalog would not serve. Resolve against relpath's directory (not a
    hardcoded reports/ prefix).
    """
    raw = html.unescape((href or "").strip())
    if not raw:
        return raw
    if raw.startswith("#"):
        return raw
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme in ("http", "https", "mailto"):
        return raw
    if scheme:
        return None
    path = parsed.path or ""
    if path.startswith("/"):
        return raw
    if not path.lower().endswith(_MD_EXT):
        return raw
    posix = path.replace("\\", "/")
    if ".." in posix.split("/"):
        return None
    # Paths that already name an allowlisted prefix are session-root relative
    # (`reports/01.md` from `reports/README.md` must not become reports/reports/).
    # Bare siblings (`01.md`, `./01.md`) resolve against relpath's directory.
    candidate = posixpath.normpath(posix)
    if _allowlisted_rel(candidate):
        norm = candidate
    else:
        base_dir = posixpath.dirname((relpath or "").replace("\\", "/"))
        joined = posixpath.join(base_dir, posix) if base_dir else posix
        norm = posixpath.normpath(joined)
    if norm.startswith("..") or norm == "..":
        return None
    if not _allowlisted_rel(norm):
        return None
    out = (
        f"{href_base}?{id_query}={quote(run_id, safe='')}&path={quote(norm, safe='')}"
    )
    if parsed.fragment:
        out += f"#{parsed.fragment}"
    return out


def _rewrite_relative_md_hrefs(
    fragment: str,
    *,
    run_id: str,
    relpath: str,
    href_base: str,
    id_query: str,
) -> str:
    def repl(match: re.Match[str]) -> str:
        rewritten = _rewrite_session_href(
            match.group(2),
            run_id=run_id,
            relpath=relpath,
            href_base=href_base,
            id_query=id_query,
        )
        if rewritten is None:
            prefix = match.group(1).rstrip()
            return f"{prefix}{match.group(3)}"
        escaped = html.escape(rewritten, quote=True)
        return f'{match.group(1)}href="{escaped}"{match.group(3)}'

    return _A_HREF_RE.sub(repl, fragment)


def _extract_title(html_body: str, relpath: str) -> tuple[str, str]:
    """Page title from the first H1; strip that heading from the body."""
    match = _H1_RE.search(html_body)
    if not match:
        return (relpath or "Report"), html_body
    title = _visible_text(match.group(2)).strip() or (relpath or "Report")
    body = html_body[: match.start()] + html_body[match.end() :]
    return title, body.lstrip()


def _toc_from_html(html_body: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for match in _TOC_RE.finditer(html_body):
        text = _visible_text(match.group(3)).strip()
        if not text:
            continue
        out.append(
            {
                "level": int(match.group(1)),
                "id": match.group(2),
                "text": text,
            }
        )
    return out


_FORECAST_TITLES = frozenset(
    {
        "forecast path",
        "forecast used in the model",
        "the forecast used in the model",
        "cash-flow forecast",
        "cash flow forecast",
        "year-by-year forecast",
        "explicit forecast",
    }
)
_MD_H2 = re.compile(r"^(#{2,3})[ \t]+(.+?)[ \t]*#*[ \t]*$")


def strip_forecast_section(text: str) -> str:
    """Drop a named forecast-path H2 so the composed report does not repeat the grid."""
    out: list[str] = []
    skipping = False
    for line in (text or "").splitlines(keepends=True):
        raw = line[:-1] if line.endswith("\n") else line
        match = _MD_H2.match(raw.rstrip())
        if match:
            level = len(match.group(1))
            title = match.group(2).strip().lower()
            if level == 2 and title in _FORECAST_TITLES:
                skipping = True
                continue
            if skipping and level <= 2:
                skipping = False
        if not skipping:
            out.append(line)
    return "".join(out)


def _prefix_heading_ids(html_body: str, prefix: str) -> str:
    if not prefix:
        return html_body
    return re.sub(
        r'\bid="([^"]+)"',
        lambda m: f'id="{prefix}-{m.group(1)}"',
        html_body,
    )


def render_session_report(
    text: str,
    *,
    run_id: str,
    relpath: str,
    href_base: str = "/artifact",
    id_query: str = "run_id",
    id_prefix: str = "",
    strip_forecast: bool = False,
) -> dict[str, Any]:
    """Artifact markdown as a document: title, h2/h3 toc, rewritten sibling links.

    `render_markdown()` stays a plain sanitizer (architecture, harness). This
    helper is the session-report document type. Default href_base is catalog
    `/artifact` with query key `run_id`. Compare/analyze may pass another
    base and id_query (`compare_id` / `analyze_id`).
    """
    source = strip_forecast_section(text) if strip_forecast else text
    html_body = render_markdown(source)
    title, html_body = _extract_title(html_body, relpath)
    html_body = _rewrite_relative_md_hrefs(
        html_body,
        run_id=run_id,
        relpath=relpath,
        href_base=href_base,
        id_query=id_query,
    )
    if id_prefix:
        html_body = _prefix_heading_ids(html_body, id_prefix)
    toc = _toc_from_html(html_body)
    if id_prefix:
        toc = [
            {**item, "id": item["id"] if str(item["id"]).startswith(id_prefix) else f"{id_prefix}-{item['id']}"}
            for item in toc
        ]
    return {
        "title": title,
        "toc": toc,
        "html": html_body,
    }


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
