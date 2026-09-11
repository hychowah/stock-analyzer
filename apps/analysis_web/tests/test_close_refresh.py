"""CloseRefresh writes DailyCloses. GET paths must not call the backend."""

from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from apps.analysis_web.services.close_refresh import CloseRefresh
from apps.analysis_web.services.daily_closes import DailyCloses
from apps.analysis_web.services.price_history import FakeHistoryBackend, PriceBar
from apps.analysis_web.tests.closes_util import seed_app_closes
from apps.analysis_web.tests.test_book_state import FIXTURE
from apps.analysis_web.tests.test_portfolio import _mini_archive


TODAY = "2026-09-10"


def _bars() -> list[PriceBar]:
    return [
        PriceBar("2026-01-02", 100.0),
        PriceBar("2026-09-08", 410.0),
    ]


class CloseRefreshTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.store = DailyCloses(Path(self._td.name) / "daily_closes.sqlite")
        self.backend = FakeHistoryBackend({"META": _bars()})
        self.refresh = CloseRefresh(
            self.store, self.backend, today=TODAY, min_refetch_sec=60
        )

    def tearDown(self):
        self._td.cleanup()

    def test_ensure_writes_series(self):
        self.refresh.ensure(["META", "NOPE"], since="2026-01-01")
        self.assertEqual(len(self.backend.many_calls), 1)
        hit = self.store.series(["META"])["META"]
        self.assertEqual(hit.bars[-1].close, 410.0)
        miss = self.store.series(["NOPE"])["NOPE"]
        self.assertEqual(miss.error, "unavailable")

    def test_errors_do_not_erase_or_store(self):
        self.refresh.ensure(["NOPE"], since="2026-01-01")
        self.assertEqual(len(self.backend.calls), 1)
        self.assertEqual(
            self.store.series(["NOPE"])["NOPE"].error,
            "unavailable",
        )
        self.refresh.ensure(["NOPE"], since="2026-01-01")
        self.assertEqual(len(self.backend.calls), 1)

    def test_skip_when_last_bar_is_today(self):
        self.store.replace_window(
            "META",
            [PriceBar("2026-01-02", 100.0), PriceBar("2026-09-10", 420.0)],
            since="2026-01-01",
            yahoo_chart="META",
            fetched_at="2026-09-09T00:00:00Z",
        )
        self.refresh.ensure(["META"], since="2026-01-01")
        self.assertEqual(len(self.backend.many_calls), 0)

    def test_second_ensure_skips_fresh_cover(self):
        self.refresh.ensure(["META"], since="2026-01-01")
        self.refresh.ensure(["META"], since="2026-01-01")
        self.assertEqual(len(self.backend.many_calls), 1)

    def test_wider_since_refetches(self):
        self.refresh.ensure(["META"], since="2026-08-01")
        self.assertEqual(len(self.backend.many_calls), 1)
        self.refresh.ensure(["META"], since="2025-01-01")
        self.assertEqual(len(self.backend.many_calls), 2)
        self.assertEqual(self.backend.many_calls[1][1], "2025-01-01")

    def test_single_flight(self):
        started = threading.Event()
        release = threading.Event()

        class Slow(FakeHistoryBackend):
            def history_many(self, symbols, *, since, preferred_charts=None):  # type: ignore[override]
                started.set()
                release.wait(timeout=2)
                return super().history_many(
                    symbols, since=since, preferred_charts=preferred_charts
                )

        be = Slow({"META": _bars()})
        refresh = CloseRefresh(self.store, be, today=TODAY, min_refetch_sec=60)

        def worker():
            refresh.ensure(["META"], since="2026-01-01")

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        self.assertTrue(started.wait(timeout=2))
        t2.start()
        time.sleep(0.05)
        release.set()
        t1.join(timeout=2)
        t2.join(timeout=2)
        self.assertEqual(len(be.many_calls), 1)


class MtmIntervalDoesNotFetchTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        base = Path(self._td.name)
        self.archive = _mini_archive(base)
        os.environ["ARCHIVE_ROOT"] = str(self.archive)
        self._local = base / "local"
        self._local.mkdir()

        import apps.analysis_web.config as cfg
        from apps.analysis_web.services.ib_statement import parse_activity_csv
        from apps.analysis_web.services.portfolio_store import ingest_statement

        self._orig_local = cfg.local_dir
        cfg.local_dir = lambda: self._local  # type: ignore[assignment]
        ingest_statement(
            parse_activity_csv(FIXTURE), path=self._local / "portfolio.sqlite"
        )

        import importlib
        import apps.analysis_web.app as app_mod
        import apps.analysis_web.config as cfg2
        import apps.analysis_web.services.portfolio as port

        importlib.reload(app_mod)
        cfg2.local_dir = lambda: self._local  # type: ignore[assignment]
        port.local_dir = cfg2.local_dir  # type: ignore[assignment]

        self._app = app_mod.create_app(history_backend=FakeHistoryBackend())
        series = {
            "META": [
                PriceBar("2026-01-02", 40.0),
                PriceBar("2026-03-20", 50.0),
                PriceBar("2026-03-31", 52.0),
            ],
            "0700.HK": [
                PriceBar("2026-01-02", 9.0),
                PriceBar("2026-03-20", 10.0),
                PriceBar("2026-03-31", 10.5),
            ],
        }
        self._store, self._backend = seed_app_closes(
            self._app, self._local / "daily_closes.sqlite", series
        )
        from fastapi.testclient import TestClient

        self.client = TestClient(self._app)

    def tearDown(self):
        import apps.analysis_web.config as cfg

        cfg.local_dir = self._orig_local  # type: ignore[assignment]
        self.client.close()
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_interval_get_does_not_hit_backend(self):
        before = len(self._backend.many_calls)
        r = self.client.get("/api/portfolio/mtm-interval?period=statement")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("rows"))
        self.assertEqual(len(self._backend.many_calls), before)

    def test_empty_store_get_still_no_backend(self):
        empty = DailyCloses(self._local / "empty_closes.sqlite")
        be = FakeHistoryBackend(
            {"META": [PriceBar("2026-03-31", 52.0)]}
        )
        self._app.state.daily_closes = empty
        self._app.state.close_refresh = CloseRefresh(empty, be, today=TODAY)
        r = self.client.get("/api/portfolio/mtm-interval?period=statement")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(be.many_calls), 0)
        rows = r.json().get("rows") or []
        unquoted = [row for row in rows if row.get("pl") is None]
        self.assertTrue(unquoted or r.json().get("error"))
