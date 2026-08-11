"""FastAPI dependencies."""

from __future__ import annotations

from packages.catalog_api.client import CatalogApi

from apps.analysis_web.config import archive_root


def get_api() -> CatalogApi:
    return CatalogApi(archive_root=archive_root(), readonly=True)
