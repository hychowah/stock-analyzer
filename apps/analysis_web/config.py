"""Runtime config for analysis_web (env-driven)."""

from __future__ import annotations

import os
from pathlib import Path

from packages.catalog_api.client import default_archive_root


def archive_root() -> Path:
    raw = os.environ.get("ARCHIVE_ROOT")
    if raw:
        return Path(raw).expanduser().resolve()
    return default_archive_root()


def app_dir() -> Path:
    return Path(__file__).resolve().parent


def local_dir() -> Path:
    """App-local state (portfolio book). Never under archive/research."""
    return app_dir() / ".local"


def templates_dir() -> Path:
    return app_dir() / "templates"


def static_dir() -> Path:
    return app_dir() / "static"
