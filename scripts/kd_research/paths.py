"""Path helpers for the research harness and archive layout.

Canonical research sessions live under::

    <project>/archive/research/<TICKER>/<SESSION_KEY>/

where ``SESSION_KEY`` is ``YYYY-MM-DD`` (first run for that as-of day),
``YYYY-MM-DD__rN`` (same-day production re-run), or
``YYYY-MM-DD__<slug>`` (named / experiment runs).

Legacy sessions (pre-migration) may still exist at::

    <project>/<TICKER>/<YYYY-MM-DD>/

``resolve_session`` prefers the archive path, then falls back to legacy.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Names that are harness/code at the repo root — never treat as tickers.
# Keep in sync when adding top-level product dirs (eng/, packages/, apps/, …).
ROOT_RESERVED_NAMES = frozenset(
    {
        "archive",
        "harness",
        "scripts",
        "templates",
        "sec-edgar-mcp",
        "web-fetch-mcp",
        "yfinance-market-mcp",
        "_archive",
        ".git",
        ".grok",
        "node_modules",
        # Mode B / product platform (dual-mode plan)
        "eng",
        "packages",
        "apps",
        "programs",
        "docs",
        "build",  # setuptools output; also gitignored
        "dist",
        "tests",
        "meta",
        "research",  # reserved if research law moves to top-level folder
    }
)

# Production calendar folders.
DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Production or experiment: 2026-08-10 or 2026-08-10__model-grok45_r1
SESSION_KEY_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})(?:__(?P<slug>[A-Za-z0-9][A-Za-z0-9._-]{0,80}))?$"
)
SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")


def project_root() -> Path:
    """Return the project root (/workspace-stock-research)."""
    return PROJECT_ROOT


def archive_root(output_dir: Path | str | None = None) -> Path:
    """Return <root>/archive/."""
    root = Path(output_dir).expanduser().resolve() if output_dir else PROJECT_ROOT
    # If caller passes archive/research as output_dir, don't double-nest.
    if root.name == "archive":
        return root
    if root.name == "research" and root.parent.name == "archive":
        return root.parent
    return root / "archive"


def research_root(output_dir: Path | str | None = None) -> Path:
    """Return canonical parent of all research sessions: archive/research/."""
    root = Path(output_dir).expanduser().resolve() if output_dir else PROJECT_ROOT
    if root.name == "research" and root.parent.name == "archive":
        return root
    if root.name == "archive":
        return root / "research"
    return root / "archive" / "research"


def catalog_root(output_dir: Path | str | None = None) -> Path:
    return archive_root(output_dir) / "catalog"


def outcomes_root(output_dir: Path | str | None = None) -> Path:
    return archive_root(output_dir) / "outcomes"


def parse_session_key(session_key: str) -> tuple[str, str | None]:
    """Return (session_date, slug|None) from a folder name or run suffix."""
    m = SESSION_KEY_RE.match(session_key)
    if not m:
        # Best-effort: date prefix before __ even if slug is odd
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


# Same-day production re-runs: YYYY-MM-DD__r2, __r3, … or __run02
_PRODUCTION_SLUG_RE = re.compile(r"^(?:r|run)\d+$", re.IGNORECASE)


def is_production_session_key(session_key: str) -> bool:
    """True for plain YYYY-MM-DD or same-day re-run slugs (rN / runN).

    Named experiment slugs (e.g. model-grok45) are non-production for catalog
    “latest production” preference; they remain full research sessions.
    """
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
    prefer: str = "archive",
    auto_replicate: bool = True,
) -> str:
    """Choose a free session_key for a new scaffold.

    - Explicit ``slug`` → ``YYYY-MM-DD__slug`` (caller still refuses if taken).
    - No slug: prefer plain ``YYYY-MM-DD``; if that folder is non-empty and
      ``auto_replicate``, allocate ``YYYY-MM-DD__r2``, ``__r3``, … 
    """
    if not DATE_DIR_RE.match(session_date):
        # Allow full key passed as date (date__slug already parsed upstream)
        if "__" in session_date and slug is None:
            session_date, slug = parse_session_key(session_date)
        else:
            raise ValueError(f"session_date must be YYYY-MM-DD, got {session_date!r}")

    if slug:
        return make_session_key(session_date, slug)

    plain = make_session_key(session_date, None)
    plain_root = session_root(ticker, plain, output_dir, prefer=prefer)
    if not session_dir_nonempty(plain_root):
        return plain

    if not auto_replicate:
        return plain

    for n in range(2, 1000):
        candidate = make_session_key(session_date, f"r{n}")
        cand_root = session_root(ticker, candidate, output_dir, prefer=prefer)
        if not session_dir_nonempty(cand_root):
            return candidate
    raise RuntimeError(
        f"Could not allocate session_key for {ticker.upper()} {session_date}: "
        "r2..r999 all occupied"
    )


def run_id(ticker: str, session_key: str) -> str:
    """Stable run identifier: research:TICKER:SESSION_KEY."""
    return f"research:{ticker.upper()}:{session_key}"


def session_root(
    ticker: str,
    session_key: str,
    output_dir: Path | str | None = None,
    *,
    prefer: str = "archive",
) -> Path:
    """Return the *default write path* for a new session (archive by default).

    ``session_key`` is ``YYYY-MM-DD`` or ``YYYY-MM-DD__slug``.
    ``prefer`` is ``\"archive\"`` (default) or ``\"legacy\"`` (root/<T>/<key>).
    Does not check existence — use ``resolve_session`` to find an existing run.
    """
    t = ticker.upper()
    if prefer == "legacy":
        root = Path(output_dir).expanduser().resolve() if output_dir else PROJECT_ROOT
        if root.name == "research" and root.parent.name == "archive":
            root = PROJECT_ROOT
        elif root.name == "archive":
            root = PROJECT_ROOT
        return root / t / session_key
    return research_root(output_dir) / t / session_key


def legacy_session_root(
    ticker: str,
    session_key: str,
    output_dir: Path | str | None = None,
) -> Path:
    root = Path(output_dir).expanduser().resolve() if output_dir else PROJECT_ROOT
    # Strip archive/research if someone passed it as output_dir.
    if root.name == "research" and root.parent.name == "archive":
        root = root.parent.parent
    elif root.name == "archive":
        root = root.parent
    return root / ticker.upper() / session_key


def resolve_session(
    ticker: str,
    session_key: str,
    output_dir: Path | str | None = None,
) -> Path | None:
    """Locate an existing session: archive first, then legacy root.

    ``session_key`` may be a plain date or ``date__slug``.
    Returns None if neither path exists as a directory.
    """
    archive_path = research_root(output_dir) / ticker.upper() / session_key
    if archive_path.is_dir():
        return archive_path
    legacy_path = legacy_session_root(ticker, session_key, output_dir)
    if legacy_path.is_dir():
        return legacy_path
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
            f"{research_root(output_dir)} or legacy root"
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
    *,
    include_legacy: bool = True,
) -> list[tuple[str, str, Path]]:
    """Yield (ticker, session_key, path) for all discovered research sessions.

    Archive sessions first; legacy only if not already present in archive.
    ``session_key`` is the folder name (date or date__slug).
    """
    found: dict[tuple[str, str], Path] = {}

    def _scan_ticker_parent(parent: Path) -> None:
        if not parent.is_dir():
            return
        for ticker_dir in sorted(parent.iterdir()):
            if not ticker_dir.is_dir():
                continue
            name = ticker_dir.name
            if name in ROOT_RESERVED_NAMES or name.startswith("."):
                continue
            for key_dir in sorted(ticker_dir.iterdir()):
                if not key_dir.is_dir() or not SESSION_KEY_RE.match(key_dir.name):
                    continue
                # Heuristic: must look like a session (has registry or reports).
                if not ((key_dir / "registry").is_dir() or (key_dir / "reports").is_dir()):
                    continue
                key = (name.upper(), key_dir.name)
                if key not in found:
                    found[key] = key_dir

    _scan_ticker_parent(research_root(output_dir))
    if include_legacy:
        root = Path(output_dir).expanduser().resolve() if output_dir else PROJECT_ROOT
        if root.name == "research" and root.parent.name == "archive":
            root = root.parent.parent
        elif root.name == "archive":
            root = root.parent
        _scan_ticker_parent(root)

    return [(t, d, p) for (t, d), p in sorted(found.items())]


def safe_path(*parts: Any) -> Path:
    """Build a Path from stringifiable parts."""
    return Path(*(str(p) for p in parts))


def ensure_archive_tree(output_dir: Path | str | None = None) -> dict[str, Path]:
    """Create archive/{research,catalog,outcomes} if missing."""
    ar = archive_root(output_dir)
    dirs = {
        "archive": ar,
        "research": ar / "research",
        "catalog": ar / "catalog",
        "outcomes": ar / "outcomes",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs
