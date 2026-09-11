"""Write DailyCloses from Yahoo. Not a GET collaborator.

Call from HTML prime, IB ingest, and the app idle loop. GET handlers
must not call this. Failures do not erase stored bars.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Sequence

from apps.analysis_web.services.daily_closes import DailyCloses, ListingMeta
from apps.analysis_web.services.price_history import (
    HistoryBackend,
    PriceHistory,
    _unique_listings,
    normalize_since,
)


DEFAULT_MIN_REFETCH_SEC = 900


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_iso(raw: str | None) -> datetime | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _epoch(raw: str | None) -> float | None:
    dt = _parse_iso(raw)
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


class CloseRefresh:
    """Write DailyCloses from a HistoryBackend (Yahoo in production).

    ensure() is one in-process batch. GET handlers must not call it.
    At most one successful fetch per listing per last completed session
    (skip when last_bar_date is today, or a recent attempt already ran).
    Does not know the IB book.
    """

    def __init__(
        self,
        store: DailyCloses,
        backend: HistoryBackend,
        *,
        today: str | None = None,
        min_refetch_sec: int = DEFAULT_MIN_REFETCH_SEC,
    ):
        self._store = store
        self._backend = backend
        self._today = today
        self._min_refetch = max(1, int(min_refetch_sec))
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._fetching = False

    @property
    def store(self) -> DailyCloses:
        return self._store

    @property
    def today(self) -> str:
        return self._today or _utc_today()

    def prime(self, listings: list[str], *, since: str) -> None:
        """Start ensure on a daemon thread. Return immediately. HTML must not wait."""
        unique = _unique_listings(listings)
        if not unique:
            return

        def _run() -> None:
            try:
                self.ensure(unique, since=since)
            except Exception:
                logging.getLogger(__name__).exception("close refresh prime failed")

        threading.Thread(target=_run, name="close-refresh-prime", daemon=True).start()

    def ensure(self, listings: Sequence[str], *, since: str) -> None:
        """Fetch missing/stale listings into DailyCloses. No-op when fresh."""
        unique = _unique_listings(list(listings))
        need = normalize_since(since)
        if not unique:
            return
        with self._cv:
            while self._fetching:
                self._cv.wait(timeout=60)
            to_fetch, fetch_since, charts = self._missing(unique, need)
            if not to_fetch:
                return
            self._fetching = True
        try:
            fetched = dict(
                self._backend.history_many(
                    to_fetch,
                    since=fetch_since,
                    preferred_charts=charts or None,
                )
            )
            charts_got = getattr(self._backend, "last_charts", {}) or {}
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            self._store.mark_attempted(to_fetch, at=now)
            for listing in to_fetch:
                hist = fetched.get(listing) or PriceHistory(
                    symbol=listing, error="unavailable"
                )
                if hist.error is not None or not hist.bars:
                    continue
                yahoo = str(charts_got.get(listing) or listing).strip().upper()
                self._store.replace_window(
                    listing,
                    hist.bars,
                    since=fetch_since,
                    yahoo_chart=yahoo,
                    fetched_at=now,
                )
        finally:
            with self._cv:
                self._fetching = False
                self._cv.notify_all()

    def _missing(
        self, unique: list[str], need: str
    ) -> tuple[list[str], str, dict[str, str]]:
        today = self.today
        now = datetime.now(timezone.utc).timestamp()
        to_fetch: list[str] = []
        fetch_since = need
        charts = self._store.preferred_charts(unique)
        for listing in unique:
            meta = self._store.listing_meta(listing)
            if self._skip(meta, need=need, today=today, now=now):
                continue
            to_fetch.append(listing)
            if meta and meta.cover_since:
                if meta.cover_since < fetch_since:
                    fetch_since = meta.cover_since
        return to_fetch, fetch_since, charts

    def _skip(
        self,
        meta: ListingMeta | None,
        *,
        need: str,
        today: str,
        now: float,
    ) -> bool:
        if meta is None:
            return False
        attempted = _epoch(meta.attempted_at) or _epoch(meta.fetched_at)
        recent = attempted is not None and (now - attempted) < self._min_refetch
        if not meta.cover_since:
            return recent
        if meta.cover_since > need:
            return False
        if meta.last_bar_date and meta.last_bar_date[:10] >= today:
            return True
        return recent
