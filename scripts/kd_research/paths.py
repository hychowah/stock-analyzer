"""Path helpers for the kimi-datasource research harness."""

from __future__ import annotations

from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def project_root() -> Path:
    """Return the project root (/workspace-stock-research)."""
    return PROJECT_ROOT


def session_root(ticker: str, session_date: str, output_dir: Path | str | None = None) -> Path:
    """Return <output_dir>/<TICKER>/<SESSION_DATE>/."""
    root = Path(output_dir).expanduser().resolve() if output_dir else PROJECT_ROOT
    return root / ticker.upper() / session_date


def session_dirs(ticker: str, session_date: str, output_dir: Path | str | None = None) -> dict[str, Path]:
    """Return and create reports/data/charts/registry paths for a session."""
    root = session_root(ticker, session_date, output_dir)
    dirs = {
        "root": root,
        "reports": root / "reports",
        "data": root / "data",
        "charts": root / "charts",
        "registry": root / "registry",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def safe_path(*parts: Any) -> Path:
    """Build a Path from stringifiable parts."""
    return Path(*(str(p) for p in parts))
