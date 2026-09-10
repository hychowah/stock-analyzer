"""Price history service + /api/price-history (FakeHistoryBackend; no network)."""

from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from apps.analysis_web.services.price_history import (
    COVERED_ALL,
    DEFAULT_RANGE,
    FakeHistoryBackend,
    HistoryService,
    PriceBar,
    RANGES,
    bars_from_closes,
    bars_in_window,
    parse_history_symbol,
    parse_range,
    period_covering,
    since_for_period,
    since_for_range,
)
from apps.analysis_web.services.yahoo_bars import bar_date, close_series


TODAY = "2026-09-10"
SINCE_1M = "2026-08-20"
SINCE_1Y = "2025-10-01"
SINCE_5Y = "2022-01-01"
SINCE_MAX = "2018-01-01"


def _bars() -> list[PriceBar]:
    return [
        PriceBar("2026-01-02", 100.0),
        PriceBar("2026-01-05", 110.0),
        PriceBar("2026-08-03", 400.0),
        PriceBar("2026-09-08", 410.0),
    ]


def _svc(be: FakeHistoryBackend, *, ttl_sec: int = 60) -> HistoryService:
    return HistoryService(be, ttl_sec=ttl_sec, today=TODAY)


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

    def test_bars_from_closes_sorts_by_day(self):
        bars = bars_from_closes(
            [(30.0, "2026-03-03"), (10.0, "2026-03-01"), (20.0, "2026-03-02")]
        )
        self.assertEqual([b.t for b in bars], ["2026-03-01", "2026-03-02", "2026-03-03"])


class PeriodCoveringTests(unittest.TestCase):
    def test_trailing_from_today_not_end(self):
        self.assertEqual(period_covering("2026-01-10", today="2026-09-08"), "1y")
        self.assertEqual(period_covering("2024-10-01", today="2026-09-08"), "2y")
        self.assertEqual(period_covering("2022-01-01", today="2026-09-08"), "5y")
        self.assertEqual(period_covering("2018-01-01", today="2026-09-10"), "max")
        self.assertEqual(period_covering("2018-01-01", today="2018-06-01"), "6m")

    def test_old_since_with_today_needs_max(self):
        self.assertEqual(period_covering("2018-01-01", today="2026-09-10"), "max")

    def test_one_week_plans_one_month(self):
        self.assertEqual(period_covering("2026-09-03", today="2026-09-10"), "1m")

    def test_since_for_period_stays_in_bucket(self):
        for key in ("1m", "3m", "6m", "1y", "2y", "5y", "max"):
            since = since_for_period(key, today=TODAY)
            self.assertEqual(period_covering(since, today=TODAY), key)

    def test_invalid_since_is_max(self):
        self.assertEqual(period_covering("", today=TODAY), "max")
        self.assertEqual(period_covering("nope", today=TODAY), "max")

    def test_since_for_range_and_slice(self):
        self.assertEqual(since_for_range("1y", today=TODAY), "2025-09-10")
        self.assertEqual(since_for_range("max", today=TODAY), COVERED_ALL)
        bars = tuple(_bars())
        sliced = bars_in_window(bars, "1m", today=TODAY)
        self.assertEqual([b.t for b in sliced], ["2026-09-08"])
        self.assertEqual(len(bars_in_window(bars, "1y", today=TODAY)), 4)
        self.assertEqual(len(bars_in_window(bars, "max", today=TODAY)), 4)


class FakeBackendAndCacheTests(unittest.TestCase):
    def test_missing_symbol_is_error(self):
        be = FakeHistoryBackend({"META": _bars()})
        hit = be.history("META", since=SINCE_1Y)
        miss = be.history("NOPE", since=SINCE_1Y)
        self.assertEqual(len(hit.bars), 4)
        self.assertEqual(hit.bars[-1].close, 410.0)
        self.assertEqual(miss.error, "unavailable")
        self.assertEqual(miss.bars, ())

    def test_longer_series_covers_shorter_since(self):
        be = FakeHistoryBackend({"META": _bars()})
        svc = _svc(be)
        first = svc.get("META", since=SINCE_1Y)
        second = svc.get("meta", since=SINCE_1Y)
        self.assertEqual(len(be.calls), 1)
        self.assertEqual(first.bars[0].close, second.bars[0].close)
        svc.get("META", since=SINCE_5Y)
        self.assertEqual(len(be.calls), 2)
        self.assertEqual(be.calls[1], ("META", SINCE_5Y))
        svc.get("META", since=SINCE_1Y)
        self.assertEqual(len(be.calls), 2)

    def test_five_year_then_one_year_is_one_round(self):
        be = FakeHistoryBackend({"META": _bars()})
        svc = _svc(be)
        svc.get("META", since=SINCE_5Y)
        svc.get("META", since=SINCE_1Y)
        self.assertEqual(len(be.many_calls), 1)

    def test_coverage_is_fetched_period_not_first_bar(self):
        be = FakeHistoryBackend({"META": _bars()})
        svc = _svc(be)
        svc.get("META", since=SINCE_1Y)
        self.assertEqual(len(be.many_calls), 1)
        svc.get("META", since=SINCE_5Y)
        self.assertEqual(len(be.many_calls), 2)
        svc.get("META", since=SINCE_MAX)
        self.assertEqual(len(be.many_calls), 3)
        svc.get("META", since=SINCE_5Y)
        self.assertEqual(len(be.many_calls), 3)

    def test_expired_long_series_does_not_shrink(self):
        be = FakeHistoryBackend({"META": _bars()})
        svc = _svc(be, ttl_sec=1)
        svc.get("META", since=SINCE_5Y)
        time.sleep(1.1)
        svc.get("META", since=SINCE_1M)
        self.assertEqual(len(be.many_calls), 2)
        self.assertEqual(period_covering(be.many_calls[1][1], today=TODAY), "5y")

    def test_ttl_expiry_refetches(self):
        be = FakeHistoryBackend({"META": _bars()})
        svc = _svc(be, ttl_sec=1)
        svc.get("META", since=SINCE_1Y)
        time.sleep(1.1)
        svc.get("META", since=SINCE_1Y)
        self.assertEqual(len(be.calls), 2)

    def test_errors_are_not_cached(self):
        be = FakeHistoryBackend({"META": _bars()})
        svc = _svc(be)
        miss = svc.get("NOPE", since=SINCE_1Y)
        self.assertEqual(miss.error, "unavailable")
        svc.get("NOPE", since=SINCE_1Y)
        self.assertEqual(len(be.calls), 2)
        svc.get("META", since=SINCE_1Y)
        svc.get("META", since=SINCE_1Y)
        self.assertEqual(len(be.calls), 3)

    def test_single_flight(self):
        started = threading.Event()
        release = threading.Event()

        class Slow(FakeHistoryBackend):
            def history_many(self, symbols, *, since):  # type: ignore[override]
                started.set()
                release.wait(timeout=2)
                return super().history_many(symbols, since=since)

        be = Slow({"META": _bars()})
        svc = _svc(be)
        results: list = []

        def worker():
            results.append(svc.get("META", since=SINCE_1Y))

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
        self.assertEqual(results[0].bars[-1].close, 410.0)

    def test_waiter_rechecks_coverage(self):
        started = threading.Event()
        release = threading.Event()

        class Slow(FakeHistoryBackend):
            def history_many(self, symbols, *, since):  # type: ignore[override]
                started.set()
                release.wait(timeout=2)
                return super().history_many(symbols, since=since)

        be = Slow({"META": _bars()})
        svc = _svc(be)
        short: list = []
        long: list = []

        def short_worker():
            short.append(svc.get("META", since=SINCE_1Y))

        def long_worker():
            long.append(svc.get("META", since=SINCE_5Y))

        t1 = threading.Thread(target=short_worker)
        t2 = threading.Thread(target=long_worker)
        t1.start()
        self.assertTrue(started.wait(timeout=2))
        t2.start()
        time.sleep(0.05)
        release.set()
        t1.join(timeout=2)
        t2.join(timeout=2)
        self.assertEqual(len(be.many_calls), 2)
        self.assertEqual(be.many_calls[0][1], SINCE_1Y)
        self.assertEqual(be.many_calls[1][1], SINCE_5Y)
        self.assertEqual(len(short), 1)
        self.assertEqual(len(long), 1)

    def test_get_many_one_backend_round(self):
        be = FakeHistoryBackend({"META": _bars(), "AAPL": [PriceBar("2026-01-02", 50.0)]})
        svc = _svc(be)
        got = svc.get_many(["meta", "AAPL", "NOPE"], since=SINCE_1Y)
        self.assertEqual(len(be.many_calls), 1)
        self.assertEqual(be.many_calls[0][0], ("META", "AAPL", "NOPE"))
        self.assertEqual(got["META"].bars[-1].close, 410.0)
        self.assertEqual(got["AAPL"].bars[0].close, 50.0)
        self.assertEqual(got["NOPE"].error, "unavailable")
        svc.get_many(["META", "AAPL"], since=SINCE_1Y)
        self.assertEqual(len(be.many_calls), 1)

    def test_get_blank_symbol_is_unavailable(self):
        be = FakeHistoryBackend({"META": _bars()})
        svc = _svc(be)
        miss = svc.get("  ", since=SINCE_1Y)
        self.assertEqual(miss.error, "unavailable")
        self.assertEqual(miss.bars, ())
        self.assertEqual(len(be.many_calls), 0)


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
        be = FakeHistoryBackend(
            {"META": _bars(), "ADYEN.AS": [PriceBar("2026-08-01", 1400.0)]}
        )
        self._app.state.history_service = HistoryService(
            be, ttl_sec=900, today=TODAY
        )
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
        self.assertEqual(body["count"], 4)
        self.assertEqual(body["ttl_sec"], 900)
        self.assertIsNone(body["error"])
        self.assertEqual(body["bars"][-1], {"t": "2026-09-08", "close": 410.0})

    def test_range_is_a_view_not_the_store(self):
        self.client.get("/api/price-history", params={"symbol": "META", "range": "5y"})
        self.assertEqual(len(self._backend.many_calls), 1)
        r = self.client.get("/api/price-history", params={"symbol": "META", "range": "1m"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["range"], "1m")
        self.assertEqual(body["bars"], [{"t": "2026-09-08", "close": 410.0}])
        self.assertEqual(len(self._backend.many_calls), 1)

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
