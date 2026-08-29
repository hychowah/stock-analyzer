"""Path helpers for the research harness and archive layout.

Canonical research sessions live under::

    <project>/archive/research/<TICKER>/<SESSION_KEY>/

where ``SESSION_KEY`` is ``YYYY-MM-DD`` (first run for that as-of day),
``YYYY-MM-DD__rN`` (same-day production re-run), or
``YYYY-MM-DD__<slug>`` (named / experiment runs).

``archive_root`` honors an explicit output dir, then env ``ARCHIVE_ROOT``,
then ``<project>/archive``. Repo root is never a session parent.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Symbols that must not be used as Mode A tickers (product / vendor dir names).
# Not a filesystem firewall — sessions are only discovered under archive/research/.
TICKER_BLOCKLIST = frozenset(
    {
        "archive",
        "harness",
        "scripts",
        "vendor",
        "eng",
        "packages",
        "apps",
        "programs",
        "docs",
        "build",
        "dist",
        "tests",
        "library",
        "research",
    }
)

DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SESSION_KEY_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})(?:__(?P<slug>[A-Za-z0-9][A-Za-z0-9._-]{0,80}))?$"
)
SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")

RUN_ID_RE = re.compile(
    r"^research:(?P<ticker>[^:]+):(?P<session_key>.+)$", re.IGNORECASE
)
COMPARE_ID_RE = re.compile(
    r"^compare:(?P<ticker>[^:]+):(?P<packet_key>.+)$", re.IGNORECASE
)
ANALYZE_ID_RE = re.compile(
    r"^analyze:(?P<ticker>[^:]+):(?P<session_key>.+)$", re.IGNORECASE
)


def project_root() -> Path:
    """Return the project root."""
    return PROJECT_ROOT


def _unwrap_archive_dir(root: Path) -> Path:
    """If caller passed archive/, archive/research, or a session path, don't double-nest."""
    for p in (root, *root.parents):
        if p.name == "archive":
            return p
    return root / "archive"


def archive_root(output_dir: Path | str | None = None) -> Path:
    """Return the archive directory.

    Explicit ``output_dir`` wins, then env ``ARCHIVE_ROOT``, then
    ``<project>/archive``.
    """
    if output_dir is not None and str(output_dir).strip():
        return _unwrap_archive_dir(Path(output_dir).expanduser().resolve())
    raw = os.environ.get("ARCHIVE_ROOT")
    if raw and str(raw).strip():
        return _unwrap_archive_dir(Path(raw).expanduser().resolve())
    return PROJECT_ROOT / "archive"


def research_root(output_dir: Path | str | None = None) -> Path:
    """Return canonical parent of all research sessions: archive/research/."""
    return archive_root(output_dir) / "research"


def catalog_root(output_dir: Path | str | None = None) -> Path:
    return archive_root(output_dir) / "catalog"


def outcomes_root(output_dir: Path | str | None = None) -> Path:
    return archive_root(output_dir) / "outcomes"


def library_root(output_dir: Path | str | None = None) -> Path:
    """Return archive/library/ — reusable primary documents, not research runs."""
    return archive_root(output_dir) / "library"


def ticker_library(ticker: str, output_dir: Path | str | None = None) -> Path:
    """Return archive/library/<TICKER>/."""
    return library_root(output_dir) / str(ticker).strip().upper()


def parse_session_key(session_key: str) -> tuple[str, str | None]:
    """Return (session_date, slug|None) from a folder name or run suffix."""
    m = SESSION_KEY_RE.match(session_key)
    if not m:
        if "__" in session_key:
            date_part, slug = session_key.split("__", 1)
            return date_part, slug or None
        return session_key, None
    return m.group("date"), m.group("slug")


def make_session_key(session_date: str, slug: str | None = None) -> str:
    """Build session folder name from as-of date + optional experiment slug."""
    if not DATE_DIR_RE.match(session_date):
        raise ValueError(f"session_date must be YYYY-MM-DD, got {session_date!r}")
    if not slug:
        return session_date
    if not SLUG_RE.match(slug):
        raise ValueError(
            f"slug must match {SLUG_RE.pattern} (no path separators), got {slug!r}"
        )
    return f"{session_date}__{slug}"


_PRODUCTION_SLUG_RE = re.compile(r"^(?:r|run)\d+$", re.IGNORECASE)


def is_production_session_key(session_key: str) -> bool:
    """True for plain YYYY-MM-DD or same-day re-run slugs (rN / runN)."""
    if DATE_DIR_RE.match(session_key):
        return True
    _date, slug = parse_session_key(session_key)
    if slug and _PRODUCTION_SLUG_RE.match(slug):
        return True
    return False


def session_dir_nonempty(path: Path) -> bool:
    """True if path exists and contains any entry (scaffold refuses these)."""
    try:
        return path.is_dir() and any(path.iterdir())
    except OSError:
        return path.exists()


def allocate_session_key(
    ticker: str,
    session_date: str,
    slug: str | None = None,
    *,
    output_dir: Path | str | None = None,
    auto_replicate: bool = True,
) -> str:
    """Choose a free session_key for a new scaffold under archive/research/."""
    if not DATE_DIR_RE.match(session_date):
        if "__" in session_date and slug is None:
            session_date, slug = parse_session_key(session_date)
        else:
            raise ValueError(f"session_date must be YYYY-MM-DD, got {session_date!r}")

    if slug:
        return make_session_key(session_date, slug)

    plain = make_session_key(session_date, None)
    plain_root = session_root(ticker, plain, output_dir)
    if not session_dir_nonempty(plain_root):
        return plain

    if not auto_replicate:
        return plain

    for n in range(2, 1000):
        candidate = make_session_key(session_date, f"r{n}")
        cand_root = session_root(ticker, candidate, output_dir)
        if not session_dir_nonempty(cand_root):
            return candidate
    raise RuntimeError(
        f"Could not allocate session_key for {ticker.upper()} {session_date}: "
        "r2..r999 all occupied"
    )


def run_id(ticker: str, session_key: str) -> str:
    """Stable run identifier: research:TICKER:SESSION_KEY."""
    return f"research:{ticker.upper()}:{session_key}"


def parse_run_id(value: str) -> tuple[str, str]:
    m = RUN_ID_RE.match((value or "").strip())
    if not m:
        raise ValueError(f"invalid run_id: {value!r}")
    return m.group("ticker").upper(), m.group("session_key")


def parse_compare_id(value: str) -> tuple[str, str]:
    m = COMPARE_ID_RE.match((value or "").strip())
    if not m:
        raise ValueError(f"invalid compare_id: {value!r}")
    return m.group("ticker").upper(), m.group("packet_key")


def parse_analyze_id(value: str) -> tuple[str, str]:
    m = ANALYZE_ID_RE.match((value or "").strip())
    if not m:
        raise ValueError(f"invalid analyze_id: {value!r}")
    return m.group("ticker").upper(), m.group("session_key")


def session_root(
    ticker: str,
    session_key: str,
    output_dir: Path | str | None = None,
) -> Path:
    """Return the write path for a session under archive/research/."""
    return research_root(output_dir) / ticker.upper() / session_key


def resolve_session(
    ticker: str,
    session_key: str,
    output_dir: Path | str | None = None,
) -> Path | None:
    """Locate an existing session under archive/research/. None if missing."""
    archive_path = research_root(output_dir) / ticker.upper() / session_key
    if archive_path.is_dir():
        return archive_path
    return None


def require_session(
    ticker: str,
    session_key: str,
    output_dir: Path | str | None = None,
) -> Path:
    """Like resolve_session but raises FileNotFoundError if missing."""
    found = resolve_session(ticker, session_key, output_dir)
    if found is None:
        raise FileNotFoundError(
            f"No session for {ticker.upper()} {session_key} under "
            f"{research_root(output_dir)}"
        )
    return found


def session_dirs(
    ticker: str,
    session_key: str,
    output_dir: Path | str | None = None,
) -> dict[str, Path]:
    """Return and create reports/data/charts/registry/meta paths for a session."""
    root = session_root(ticker, session_key, output_dir)
    dirs = {
        "root": root,
        "reports": root / "reports",
        "data": root / "data",
        "charts": root / "charts",
        "registry": root / "registry",
        "meta": root / "meta",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def rel_to_project(path: Path, root: Path | None = None) -> str:
    """POSIX-style path relative to project root when possible."""
    base = root or PROJECT_ROOT
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def iter_research_sessions(
    output_dir: Path | str | None = None,
) -> list[tuple[str, str, Path]]:
    """Yield (ticker, session_key, path) for sessions under archive/research/."""
    found: dict[tuple[str, str], Path] = {}
    parent = research_root(output_dir)
    if not parent.is_dir():
        return []
    for ticker_dir in sorted(parent.iterdir()):
        if not ticker_dir.is_dir() or ticker_dir.name.startswith("."):
            continue
        for key_dir in sorted(ticker_dir.iterdir()):
            if not key_dir.is_dir() or not SESSION_KEY_RE.match(key_dir.name):
                continue
            if not ((key_dir / "registry").is_dir() or (key_dir / "reports").is_dir()):
                continue
            key = (ticker_dir.name.upper(), key_dir.name)
            if key not in found:
                found[key] = key_dir
    return [(t, d, p) for (t, d), p in sorted(found.items())]


def safe_path(*parts: Any) -> Path:
    """Build a Path from stringifiable parts."""
    return Path(*(str(p) for p in parts))


def ensure_archive_tree(output_dir: Path | str | None = None) -> dict[str, Path]:
    """Create archive planes if missing."""
    ar = archive_root(output_dir)
    dirs = {
        "archive": ar,
        "research": ar / "research",
        "catalog": ar / "catalog",
        "outcomes": ar / "outcomes",
        "library": ar / "library",
        "comparisons": ar / "comparisons",
        "research_jobs": ar / "research_jobs",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs
