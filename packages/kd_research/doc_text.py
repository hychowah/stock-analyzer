"""Convert HTML/PDF originals to cleaned .txt sidecars.

Year-readers and excerpt-in-source must never be fed HTML/PDF. Conversion is
code (not a session-local agent script). PDF uses pypdf when installed.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class _HtmlStrip(HTMLParser):
    _BLOCK = frozenset(
        {"p", "br", "div", "tr", "h1", "h2", "h3", "h4", "li", "table", "pre", "blockquote"}
    )
    _SKIP = frozenset({"script", "style", "noscript"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            self._skip += 1
        if tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip:
            self._skip -= 1
        if tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = raw.replace("\r\n", "\n").replace("\r", "\n")
        raw = re.sub(r"[ \t]+\n", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip() + "\n"


def html_to_text(src: str | bytes) -> str:
    if isinstance(src, bytes):
        src = src.decode("utf-8", errors="replace")
    parser = _HtmlStrip()
    parser.feed(src)
    parser.close()
    return parser.text()


def pdf_to_text(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised via importorskip tests
        raise RuntimeError(
            "pypdf is not installed; cannot convert PDF. pip install pypdf"
        ) from exc
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            t = ""
        if t.strip():
            parts.append(t)
    body = "\n\n".join(parts).strip()
    if not body:
        raise RuntimeError(f"PDF extract produced empty text: {path}")
    return body + "\n"


def convert_path(src: Path, dest: Path | None = None) -> dict[str, Any]:
    """Write a .txt sidecar. Returns {status, text_path, detail}."""
    src = Path(src)
    suffix = src.suffix.lower()
    out = dest if dest is not None else src.with_suffix(".txt")
    out = Path(out)
    try:
        if suffix == ".txt":
            if src.resolve() != out.resolve():
                out.write_bytes(src.read_bytes())
            return {"status": "ok", "text_path": str(out), "detail": "already text"}
        if suffix in {".htm", ".html"}:
            text = html_to_text(src.read_bytes())
            out.write_text(text, encoding="utf-8")
            return {"status": "ok", "text_path": str(out), "detail": "html"}
        if suffix == ".pdf":
            text = pdf_to_text(src)
            out.write_text(text, encoding="utf-8")
            return {"status": "ok", "text_path": str(out), "detail": "pdf"}
        return {
            "status": "failed",
            "text_path": None,
            "detail": f"unsupported suffix {suffix}",
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "text_path": None, "detail": str(exc)}
