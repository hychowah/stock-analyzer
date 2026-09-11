"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from packages.catalog_api.client import CatalogApi

from apps.analysis_web.config import archive_root
from apps.analysis_web.services.close_refresh import CloseRefresh
from apps.analysis_web.services.daily_closes import DailyCloses
from apps.analysis_web.services.quotes import QuoteService


def get_api() -> CatalogApi:
    return CatalogApi(archive_root=archive_root(), readonly=True)


def get_quote_service(request: Request) -> QuoteService:
    svc = getattr(request.app.state, "quote_service", None)
    if svc is None:
        raise RuntimeError("quote_service not configured on app.state")
    return svc


def get_daily_closes(request: Request) -> DailyCloses:
    svc = getattr(request.app.state, "daily_closes", None)
    if svc is None:
        raise RuntimeError("daily_closes not configured on app.state")
    return svc


def get_close_refresh(request: Request) -> CloseRefresh:
    svc = getattr(request.app.state, "close_refresh", None)
    if svc is None:
        raise RuntimeError("close_refresh not configured on app.state")
    return svc
