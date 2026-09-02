"""Quote service + /api/quotes (FakeQuoteBackend; no network)."""

from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from apps.analysis_web.services.quotes import (
    FakeQuoteBackend,
    MAX_SYMBOLS,
    QuotePrint,
    QuoteService,
    build_quote,
    parse_symbol_query,
)


def _q(sym: str, price: float, *, prev: float | None = None) -> QuotePrint:
    prev = prev if prev is not None else price * 0.99
    return QuotePrint(
        symbol=sym,
        price=price,
        prev_close=prev,
        change_pct=(price / prev - 1.0) * 100.0 if prev else None,
        currency="USD",
        as_of="2026-09-02T15:00:00",
        market_state="regular",
        print_kind="intraday",
        source="fake",
        error=None,
    )


class ParseAndBuildTests(unittest.TestCase):
    def test_parse_unique_upper(self):
        self.assertEqual(parse_symbol_query("meta, ADYEN.AS, META"), ["META", "ADYEN.AS"])

    def test_parse_empty(self):
        with self.assertRaises(ValueError):
            parse_symbol_query("")
        with self.assertRaises(ValueError):
            parse_symbol_query(" , ")

    def test_parse_cap(self):
        too_many = ",".join(f"T{i}" for i in range(MAX_SYMBOLS + 1))
        with self.assertRaises(ValueError) as ctx:
            parse_symbol_query(too_many)
        self.assertIn(str(MAX_SYMBOLS), str(ctx.exception))

    def test_build_prefers_intraday(self):
        q = build_quote(
            "aapl",
            last_intraday=10.5,
            last_daily=10.0,
            prev_daily=9.0,
            as_of_intraday="intra",
            as_of_daily="day",
        )
        self.assertEqual(q.symbol, "AAPL")
        self.assertEqual(q.price, 10.5)
        self.assertEqual(q.print_kind, "intraday")
        self.assertEqual(q.market_state, "regular")
        self.assertEqual(q.as_of, "intra")
        self.assertAlmostEqual(q.change_pct or 0, (10.5 / 9.0 - 1) * 100.0)

    def test_build_daily_close_when_no_intraday(self):
        q = build_quote("foo", last_intraday=None, last_daily=20.0, prev_daily=25.0)
        self.assertEqual(q.print_kind, "daily_close")
        self.assertEqual(q.market_state, "closed")
        self.assertEqual(q.price, 20.0)

    def test_build_unavailable(self):
        q = build_quote("zzz", last_intraday=None, last_daily=None, prev_daily=None)
        self.assertEqual(q.error, "unavailable")
        self.assertIsNone(q.price)


class FakeBackendAndCacheTests(unittest.TestCase):
    def test_missing_symbol_is_error_row(self):
        be = FakeQuoteBackend({"META": _q("META", 100.0)})
        rows = be.quote_many(["META", "NOPE"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].price, 100.0)
        self.assertEqual(rows[1].symbol, "NOPE")
        self.assertEqual(rows[1].error, "unavailable")

    def test_cache_hits_second_call(self):
        be = FakeQuoteBackend({"META": _q("META", 100.0)})
        svc = QuoteService(be, ttl_sec=60)
        first = svc.get_many(["META"])
        second = svc.get_many(["meta"])
        self.assertEqual(len(be.calls), 1)
        self.assertEqual(first[0].price, second[0].price)

    def test_ttl_expiry_refetches(self):
        be = FakeQuoteBackend({"META": _q("META", 100.0)})
        svc = QuoteService(be, ttl_sec=1)
        svc.get_many(["META"])
        time.sleep(1.1)
        svc.get_many(["META"])
        self.assertEqual(len(be.calls), 2)

    def test_single_flight(self):
        started = threading.Event()
        release = threading.Event()

        class Slow(FakeQuoteBackend):
            def quote_many(self, symbols):  # type: ignore[override]
                started.set()
                release.wait(timeout=2)
                return super().quote_many(symbols)

        be = Slow({"META": _q("META", 1.0)})
        svc = QuoteService(be, ttl_sec=60)
        results: list[list] = []

        def worker():
            results.append(svc.get_many(["META"]))

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
        self.assertEqual(results[0][0].price, 1.0)


class QuotesApiTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        archive = Path(self._td.name) / "archive"
        (archive / "catalog").mkdir(parents=True)
        os.environ["ARCHIVE_ROOT"] = str(archive)

        import importlib

        import apps.analysis_web.app as app_mod

        importlib.reload(app_mod)
        self._app = app_mod.create_app()
        be = FakeQuoteBackend(
            {
                "META": _q("META", 580.0),
                "ADYEN.AS": _q("ADYEN.AS", 1400.0, prev=1390.0),
            }
        )
        self._app.state.quote_service = QuoteService(be, ttl_sec=120)
        self._backend = be
        from fastapi.testclient import TestClient

        self.client = TestClient(self._app)

    def tearDown(self):
        self.client.close()
        self._td.cleanup()

    def test_quotes_ok(self):
        r = self.client.get("/api/quotes", params={"symbols": "META,ADYEN.AS"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(body["ttl_sec"], 120)
        by = {q["symbol"]: q for q in body["quotes"]}
        self.assertEqual(by["META"]["price"], 580.0)
        self.assertEqual(by["ADYEN.AS"]["price"], 1400.0)
        self.assertEqual(by["META"]["print_kind"], "intraday")

    def test_quotes_one_row_per_symbol_including_miss(self):
        r = self.client.get("/api/quotes", params={"symbols": "META,NOPE"})
        self.assertEqual(r.status_code, 200)
        quotes = r.json()["quotes"]
        self.assertEqual(len(quotes), 2)
        self.assertEqual(quotes[1]["symbol"], "NOPE")
        self.assertEqual(quotes[1]["error"], "unavailable")

    def test_quotes_empty_400(self):
        r = self.client.get("/api/quotes")
        self.assertEqual(r.status_code, 400)

    def test_quotes_over_cap_400(self):
        symbols = ",".join(f"T{i}" for i in range(MAX_SYMBOLS + 1))
        r = self.client.get("/api/quotes", params={"symbols": symbols})
        self.assertEqual(r.status_code, 400)
        self.assertIn(str(MAX_SYMBOLS), r.json()["detail"])
