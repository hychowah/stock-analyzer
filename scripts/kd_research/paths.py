"""Path helpers for the research harness and archive layout.

Canonical research sessions live under::

    <project>/archive/research/<TICKER>/<YYYY-MM-DD>/

Legacy sessions (pre-migration) may still exist at::

    <project>/<TICKER>/<YYYY-MM-DD>/

``resolve_session`` prefers the archive path, then falls back to legacy.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Names that are harness/code at the repo root — never treat as tickers.
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
    }
)

DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def run_id(ticker: str, session_date: str) -> str:
    """Stable run identifier: research:TICKER:YYYY-MM-DD."""
    return f"research:{ticker.upper()}:{session_date}"


def session_root(
    ticker: str,
    session_date: str,
    output_dir: Path | str | None = None,
    *,
    prefer: str = "archive",
) -> Path:
    """Return the *default write path* for a new session (archive by default).

    ``prefer`` is ``\"archive\"`` (default) or ``\"legacy\"`` (root/<T>/<D>).
    Does not check existence — use ``resolve_session`` to find an existing run.
    """
    t = ticker.upper()
    if prefer == "legacy":
        root = Path(output_dir).expanduser().resolve() if output_dir else PROJECT_ROOT
        if root.name == "research" and root.parent.name == "archive":
            root = PROJECT_ROOT
        elif root.name == "archive":
            root = PROJECT_ROOT
        return root / t / session_date
    return research_root(output_dir) / t / session_date


def legacy_session_root(
    ticker: str,
    session_date: str,
    output_dir: Path | str | None = None,
) -> Path:
    root = Path(output_dir).expanduser().resolve() if output_dir else PROJECT_ROOT
    # Strip archive/research if someone passed it as output_dir.
    if root.name == "research" and root.parent.name == "archive":
        root = root.parent.parent
    elif root.name == "archive":
        root = root.parent
    return root / ticker.upper() / session_date


def resolve_session(
    ticker: str,
    session_date: str,
    output_dir: Path | str | None = None,
) -> Path | None:
    """Locate an existing session: archive first, then legacy root.

    Returns None if neither path exists as a directory.
    """
    archive_path = research_root(output_dir) / ticker.upper() / session_date
    if archive_path.is_dir():
        return archive_path
    legacy_path = legacy_session_root(ticker, session_date, output_dir)
    if legacy_path.is_dir():
        return legacy_path
    return None


def require_session(
    ticker: str,
    session_date: str,
    output_dir: Path | str | None = None,
) -> Path:
    """Like resolve_session but raises FileNotFoundError if missing."""
    found = resolve_session(ticker, session_date, output_dir)
    if found is None:
        raise FileNotFoundError(
            f"No session for {ticker.upper()} {session_date} under "
            f"{research_root(output_dir)} or legacy root"
        )
    return found


def session_dirs(
    ticker: str,
    session_date: str,
    output_dir: Path | str | None = None,
) -> dict[str, Path]:
    """Return and create reports/data/charts/registry/meta paths for a session."""
    root = session_root(ticker, session_date, output_dir)
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
    """Yield (ticker, session_date, path) for all discovered research sessions.

    Archive sessions first; legacy only if not already present in archive.
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
            for date_dir in sorted(ticker_dir.iterdir()):
                if not date_dir.is_dir() or not DATE_DIR_RE.match(date_dir.name):
                    continue
                # Heuristic: must look like a session (has registry or reports).
                if not ((date_dir / "registry").is_dir() or (date_dir / "reports").is_dir()):
                    continue
                key = (name.upper(), date_dir.name)
                if key not in found:
                    found[key] = date_dir

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
