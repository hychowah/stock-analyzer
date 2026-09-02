"""Price history service + /api/price-history (FakeHistoryBackend; no network)."""

from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from apps.analysis_web.services.price_history import (
    DEFAULT_RANGE,
    FakeHistoryBackend,
    HistoryService,
    PriceBar,
    RANGES,
    bars_from_closes,
    parse_history_symbol,
    parse_range,
)
from apps.analysis_web.services.yahoo_bars import bar_date, close_series


def _bars() -> list[PriceBar]:
    return [
        PriceBar("2026-01-02", 100.0),
        PriceBar("2026-01-05", 110.0),
        PriceBar("2026-08-03", 400.0),
    ]


class ParseAndBarsTests(unittest.TestCase):
    def test_parse_symbol_upper(self):
        self.assertEqual(parse_history_symbol(" meta "), "META")
        self.assertEqual(parse_history_symbol("ADYEN.AS"), "ADYEN.AS")

    def test_parse_symbol_rejects_empty_and_many(self):
        with self.assertRaises(ValueError):
            parse_history_symbol("")
        with self.assertRaises(ValueError):
            parse_history_symbol("META,AAPL")
        with self.assertRaises(ValueError):
            parse_history_symbol("META AAPL")

    def test_parse_range(self):
        self.assertEqual(parse_range(None), DEFAULT_RANGE)
        self.assertEqual(parse_range("1Y"), "1y")
        self.assertEqual(parse_range("max"), "max")
        with self.assertRaises(ValueError) as ctx:
            parse_range("1d")
        self.assertIn("1m", str(ctx.exception))
        self.assertEqual(set(RANGES), {"1m", "3m", "6m", "1y", "2y", "5y", "max"})

    def test_bar_date(self):
        self.assertEqual(bar_date("2026-08-03T15:30:00-04:00"), "2026-08-03")
        self.assertEqual(bar_date("2026-08-03 00:00:00"), "2026-08-03")
        self.assertIsNone(bar_date(None))
        self.assertIsNone(bar_date(""))

    def test_close_series_skips_nan(self):
        class Series:
            def items(self):
                return [
                    ("2026-01-02", 10.5),
                    ("2026-01-03", None),
                    ("2026-01-04", float("nan")),
                    ("2026-01-05", 11.0),
                ]

        rows = close_series({"Close": Series()})
        self.assertEqual(rows, [(10.5, "2026-01-02"), (11.0, "2026-01-05")])
        bars = bars_from_closes(rows)
        self.assertEqual(bars[0].t, "2026-01-02")
        self.assertEqual(bars[0].close, 10.5)


class FakeBackendAndCacheTests(unittest.TestCase):
    def test_missing_symbol_is_error(self):
        be = FakeHistoryBackend({"META": _bars()})
        hit = be.history("META", "1y")
        miss = be.history("NOPE", "1y")
        self.assertEqual(len(hit.bars), 3)
        self.assertEqual(hit.bars[2].close, 400.0)
        self.assertEqual(miss.error, "unavailable")
        self.assertEqual(miss.bars, ())

    def test_cache_hits_second_call(self):
        be = FakeHistoryBackend({"META": _bars()})
        svc = HistoryService(be, ttl_sec=60)
        first = svc.get("META", "1y")
        second = svc.get("meta", "1y")
        self.assertEqual(len(be.calls), 1)
        self.assertEqual(first.bars[0].close, second.bars[0].close)
        svc.get("META", "5y")
        self.assertEqual(len(be.calls), 2)
        self.assertEqual(be.calls[1], ("META", "5y"))

    def test_ttl_expiry_refetches(self):
        be = FakeHistoryBackend({"META": _bars()})
        svc = HistoryService(be, ttl_sec=1)
        svc.get("META", "1y")
        time.sleep(1.1)
        svc.get("META", "1y")
        self.assertEqual(len(be.calls), 2)

    def test_errors_are_not_cached(self):
        be = FakeHistoryBackend({"META": _bars()})
        svc = HistoryService(be, ttl_sec=60)
        miss = svc.get("NOPE", "1y")
        self.assertEqual(miss.error, "unavailable")
        svc.get("NOPE", "1y")
        self.assertEqual(len(be.calls), 2)
        svc.get("META", "1y")
        svc.get("META", "1y")
        self.assertEqual(len(be.calls), 3)

    def test_single_flight(self):
        started = threading.Event()
        release = threading.Event()

        class Slow(FakeHistoryBackend):
            def history(self, symbol, range_key):  # type: ignore[override]
                started.set()
                release.wait(timeout=2)
                return super().history(symbol, range_key)

        be = Slow({"META": _bars()})
        svc = HistoryService(be, ttl_sec=60)
        results: list = []

        def worker():
            results.append(svc.get("META", "1y"))

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        self.assertTrue(started.wait(timeout=2))
        t2.start()
        time.sleep(0.05)
        release.set()
        t1.join(timeout=2)
        t2.join(timeout=2)
        self.assertEqual(len(be.calls), 1)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].bars[-1].close, 400.0)


class PriceHistoryApiTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        archive = Path(self._td.name) / "archive"
        (archive / "catalog").mkdir(parents=True)
        os.environ["ARCHIVE_ROOT"] = str(archive)

        import importlib

        import apps.analysis_web.app as app_mod

        importlib.reload(app_mod)
        self._app = app_mod.create_app()
        be = FakeHistoryBackend({"META": _bars(), "ADYEN.AS": [PriceBar("2026-08-01", 1400.0)]})
        self._app.state.history_service = HistoryService(be, ttl_sec=900)
        self._backend = be
        from fastapi.testclient import TestClient

        self.client = TestClient(self._app)

    def tearDown(self):
        self.client.close()
        self._td.cleanup()

    def test_history_ok(self):
        r = self.client.get("/api/price-history", params={"symbol": "meta", "range": "1y"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["symbol"], "META")
        self.assertEqual(body["range"], "1y")
        self.assertEqual(body["interval"], "1d")
        self.assertEqual(body["count"], 3)
        self.assertEqual(body["ttl_sec"], 900)
        self.assertIsNone(body["error"])
        self.assertEqual(body["bars"][-1], {"t": "2026-08-03", "close": 400.0})

    def test_history_unavailable(self):
        r = self.client.get("/api/price-history", params={"symbol": "NOPE"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["error"], "unavailable")
        self.assertEqual(body["bars"], [])
        self.assertEqual(body["count"], 0)

    def test_history_empty_symbol_400(self):
        r = self.client.get("/api/price-history")
        self.assertEqual(r.status_code, 400)

    def test_history_many_symbols_400(self):
        r = self.client.get("/api/price-history", params={"symbol": "META,AAPL"})
        self.assertEqual(r.status_code, 400)

    def test_history_bad_range_400(self):
        r = self.client.get("/api/price-history", params={"symbol": "META", "range": "1d"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("range", r.json()["detail"])
