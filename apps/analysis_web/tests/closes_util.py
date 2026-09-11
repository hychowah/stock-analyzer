"""Seed DailyCloses on a test app. No Yahoo."""

from __future__ import annotations

from pathlib import Path

from apps.analysis_web.services.close_refresh import CloseRefresh
from apps.analysis_web.services.daily_closes import DailyCloses
from apps.analysis_web.services.price_history import (
    COVERED_ALL,
    FakeHistoryBackend,
    PriceBar,
)


def tmp_closes(td: str | Path) -> DailyCloses:
    """DailyCloses under a tmp dir. HTTP tests must not write apps/.local."""
    return DailyCloses(Path(td) / "daily_closes.sqlite")


def seed_app_closes(
    app,
    path: Path,
    series: dict[str, list[PriceBar]],
    *,
    today: str = "2026-09-10",
) -> tuple[DailyCloses, FakeHistoryBackend]:
    store = DailyCloses(path)
    for listing, bars in series.items():
        store.put_series(listing, bars, since=COVERED_ALL)
    backend = FakeHistoryBackend(series)
    app.state.daily_closes = store
    app.state.close_refresh = CloseRefresh(store, backend, today=today)
    return store, backend
