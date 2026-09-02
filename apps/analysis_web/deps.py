"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from packages.catalog_api.client import CatalogApi

from apps.analysis_web.config import archive_root
from apps.analysis_web.services.quotes import QuoteService


def get_api() -> CatalogApi:
    return CatalogApi(archive_root=archive_root(), readonly=True)


def get_quote_service(request: Request) -> QuoteService:
    svc = getattr(request.app.state, "quote_service", None)
    if svc is None:
        raise RuntimeError("quote_service not configured on app.state")
    return svc
