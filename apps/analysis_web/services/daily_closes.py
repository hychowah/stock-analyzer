"""Durable daily closes for a requested listing. No network.

``series()`` is the close on each stored bar date through the latest bar.
A missing listing is PriceHistory(error="unavailable"), same row contract
as the old in-process cache. Yahoo lives in CloseRefresh, not here.

File: local_dir() / daily_closes.sqlite — same home as the IB book.
Not portfolio.sqlite, not archive/, not last prints.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from apps.analysis_web.services.price_history import (
    COVERED_ALL,
    PriceBar,
    PriceHistory,
    _unique_listings,
    normalize_since,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS listing_meta (
  listing TEXT PRIMARY KEY,
  yahoo_chart TEXT,
  cover_since TEXT,
  last_bar_date TEXT,
  fetched_at TEXT,
  attempted_at TEXT
);
CREATE TABLE IF NOT EXISTS closes (
  listing TEXT NOT NULL,
  bar_date TEXT NOT NULL,
  close REAL NOT NULL,
  PRIMARY KEY (listing, bar_date)
);
"""


def db_path() -> Path:
    from apps.analysis_web.config import local_dir

    return local_dir() / "daily_closes.sqlite"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class ListingMeta:
    """Per-listing cover watermark. Not a price series."""

    listing: str
    yahoo_chart: str | None = None
    cover_since: str | None = None
    last_bar_date: str | None = None
    fetched_at: str | None = None
    attempted_at: str | None = None


class DailyCloses:
    """Durable daily closes for a requested listing. No network.

    series(listings) returns each listing's stored bars in full so
    close_on(start) can use the prior session. Cover dates belong on
    CloseRefresh.ensure / replace_window, not this read. Missing listing
    → error=unavailable. Failures are never stored.
    """

    def __init__(self, path: Path | None = None):
        self._path = Path(path) if path is not None else db_path()
        self._lock = threading.Lock()
        self._ready = False

    @property
    def path(self) -> Path:
        return self._path

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(self._path), timeout=30, check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _ensure(self, conn: sqlite3.Connection) -> None:
        if self._ready:
            return
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', '1')"
        )
        conn.commit()
        self._ready = True

    def series(self, listings: list[str]) -> dict[str, PriceHistory]:
        """One PriceHistory per unique listing. No network."""
        unique = _unique_listings(listings)
        out: dict[str, PriceHistory] = {}
        if not unique:
            return out
        with self._lock:
            conn = self._connect()
            try:
                self._ensure(conn)
                for listing in unique:
                    rows = conn.execute(
                        "SELECT bar_date, close FROM closes "
                        "WHERE listing = ? ORDER BY bar_date",
                        (listing,),
                    ).fetchall()
                    if not rows:
                        out[listing] = PriceHistory(
                            symbol=listing, source="yahoo", error="unavailable"
                        )
                        continue
                    bars = tuple(
                        PriceBar(str(r["bar_date"]), float(r["close"]))
                        for r in rows
                    )
                    out[listing] = PriceHistory(
                        symbol=listing, source="yahoo", bars=bars
                    )
            finally:
                conn.close()
        return out

    def listing_meta(self, listing: str) -> ListingMeta | None:
        key = (listing or "").strip().upper()
        if not key:
            return None
        with self._lock:
            conn = self._connect()
            try:
                self._ensure(conn)
                row = conn.execute(
                    "SELECT listing, yahoo_chart, cover_since, last_bar_date, "
                    "fetched_at, attempted_at FROM listing_meta WHERE listing = ?",
                    (key,),
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            return None
        return ListingMeta(
            listing=str(row["listing"]),
            yahoo_chart=(str(row["yahoo_chart"]) if row["yahoo_chart"] else None),
            cover_since=(str(row["cover_since"]) if row["cover_since"] else None),
            last_bar_date=(
                str(row["last_bar_date"]) if row["last_bar_date"] else None
            ),
            fetched_at=(str(row["fetched_at"]) if row["fetched_at"] else None),
            attempted_at=(
                str(row["attempted_at"]) if row["attempted_at"] else None
            ),
        )

    def listings(self) -> list[str]:
        with self._lock:
            conn = self._connect()
            try:
                self._ensure(conn)
                rows = conn.execute(
                    "SELECT listing FROM listing_meta ORDER BY listing"
                ).fetchall()
            finally:
                conn.close()
        return [str(r["listing"]) for r in rows]

    def preferred_charts(self, listings: Iterable[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for raw in listings:
            meta = self.listing_meta(raw)
            if meta and meta.yahoo_chart:
                out[meta.listing] = meta.yahoo_chart
        return out

    def replace_window(
        self,
        listing: str,
        bars: Sequence[PriceBar],
        *,
        since: str,
        yahoo_chart: str | None = None,
        fetched_at: str | None = None,
    ) -> None:
        """Replace stored bars on or after ``since`` with ``bars``.

        Adjusted closes restated in the fetched window overwrite. Bars
        before ``since`` stay. Empty ``bars`` is a no-op (do not erase).
        """
        key = (listing or "").strip().upper()
        if not key:
            return
        ordered = tuple(
            b for b in bars if (b.t or "").strip()[:10] and b.close == b.close
        )
        if not ordered:
            return
        cover = normalize_since(since)
        cut = cover if cover != COVERED_ALL else "0001-01-01"
        when = fetched_at or _utc_now()
        last = max((b.t or "")[:10] for b in ordered)
        chart = (yahoo_chart or key).strip().upper() or key
        with self._lock:
            conn = self._connect()
            try:
                self._ensure(conn)
                if cover == COVERED_ALL:
                    conn.execute("DELETE FROM closes WHERE listing = ?", (key,))
                else:
                    conn.execute(
                        "DELETE FROM closes WHERE listing = ? AND bar_date >= ?",
                        (key, cut),
                    )
                conn.executemany(
                    "INSERT OR REPLACE INTO closes(listing, bar_date, close) "
                    "VALUES (?, ?, ?)",
                    [(key, (b.t or "")[:10], float(b.close)) for b in ordered],
                )
                prev = conn.execute(
                    "SELECT cover_since FROM listing_meta WHERE listing = ?",
                    (key,),
                ).fetchone()
                prev_cover = str(prev["cover_since"]) if prev and prev["cover_since"] else None
                if prev_cover is None or cover <= prev_cover:
                    new_cover = cover
                else:
                    new_cover = prev_cover
                conn.execute(
                    "INSERT INTO listing_meta("
                    "listing, yahoo_chart, cover_since, last_bar_date, "
                    "fetched_at, attempted_at) VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(listing) DO UPDATE SET "
                    "yahoo_chart = excluded.yahoo_chart, "
                    "cover_since = excluded.cover_since, "
                    "last_bar_date = excluded.last_bar_date, "
                    "fetched_at = excluded.fetched_at, "
                    "attempted_at = excluded.attempted_at",
                    (key, chart, new_cover, last, when, when),
                )
                conn.commit()
            finally:
                conn.close()

    def mark_attempted(self, listings: Sequence[str], *, at: str | None = None) -> None:
        """Record an ensure attempt without changing bars (failures, skips)."""
        when = at or _utc_now()
        keys = _unique_listings(list(listings))
        if not keys:
            return
        with self._lock:
            conn = self._connect()
            try:
                self._ensure(conn)
                for key in keys:
                    conn.execute(
                        "INSERT INTO listing_meta(listing, attempted_at) "
                        "VALUES (?, ?) "
                        "ON CONFLICT(listing) DO UPDATE SET "
                        "attempted_at = excluded.attempted_at",
                        (key, when),
                    )
                conn.commit()
            finally:
                conn.close()

    def put_series(
        self,
        listing: str,
        bars: Sequence[PriceBar],
        *,
        since: str | None = None,
        yahoo_chart: str | None = None,
    ) -> None:
        """Seed helper (tests). Same write as a successful CloseRefresh."""
        ordered = tuple(sorted(bars, key=lambda b: (b.t or "")[:10]))
        cover = since or (
            (ordered[0].t or "")[:10] if ordered else COVERED_ALL
        )
        self.replace_window(
            listing, ordered, since=cover, yahoo_chart=yahoo_chart or listing
        )
