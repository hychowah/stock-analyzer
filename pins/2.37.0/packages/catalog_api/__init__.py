"""Read-only catalog API over archive/ (or fixture ARCHIVE_ROOT).

Default production root: <project>/archive
Identity: run_id = research:{TICKER}:{session_key}
"""

from __future__ import annotations

from packages.catalog_api.client import (  # noqa: F401
    ArtifactDenied,
    CatalogApi,
    CompareNotFound,
    DbMissing,
    RunNotFound,
    TickerNotFound,
    default_archive_root,
    parse_compare_id,
    parse_run_id,
)

__all__ = [
    "CatalogApi",
    "ArtifactDenied",
    "CompareNotFound",
    "DbMissing",
    "RunNotFound",
    "TickerNotFound",
    "default_archive_root",
    "parse_compare_id",
    "parse_run_id",
]
