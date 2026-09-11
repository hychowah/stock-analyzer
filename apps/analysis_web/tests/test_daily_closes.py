"""DailyCloses sqlite: series is a disk read, no network."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps.analysis_web.services.daily_closes import DailyCloses
from apps.analysis_web.services.price_history import PriceBar


def _bars() -> list[PriceBar]:
    return [
        PriceBar("2026-01-02", 100.0),
        PriceBar("2026-09-08", 410.0),
    ]


class DailyClosesTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.store = DailyCloses(Path(self._td.name) / "daily_closes.sqlite")

    def tearDown(self):
        self._td.cleanup()

    def test_missing_is_unavailable(self):
        got = self.store.series(["META"])
        self.assertEqual(got["META"].error, "unavailable")
        self.assertEqual(got["META"].bars, ())

    def test_put_and_series(self):
        self.store.put_series("meta", _bars())
        got = self.store.series(["META", "NOPE"])
        self.assertIsNone(got["META"].error)
        self.assertEqual(got["META"].bars[-1].close, 410.0)
        self.assertEqual(got["NOPE"].error, "unavailable")

    def test_replace_window_keeps_earlier_bars(self):
        self.store.put_series(
            "META",
            [PriceBar("2025-06-01", 50.0), PriceBar("2026-01-02", 100.0)],
            since="2025-01-01",
        )
        self.store.replace_window(
            "META",
            [PriceBar("2026-09-08", 410.0)],
            since="2026-08-01",
            yahoo_chart="META",
        )
        bars = self.store.series(["META"])["META"].bars
        self.assertEqual(
            [b.t for b in bars], ["2025-06-01", "2026-01-02", "2026-09-08"]
        )
        self.assertEqual(bars[-1].close, 410.0)

    def test_empty_replace_does_not_erase(self):
        self.store.put_series("META", _bars())
        self.store.replace_window("META", [], since="2026-01-01")
        got = self.store.series(["META"])["META"]
        self.assertEqual(len(got.bars), 2)

    def test_meta_records_chart_and_cover(self):
        self.store.replace_window(
            "01378.HK",
            [PriceBar("2026-09-08", 21.0)],
            since="2026-03-01",
            yahoo_chart="1378.HK",
        )
        meta = self.store.listing_meta("01378.HK")
        self.assertIsNotNone(meta)
        self.assertEqual(meta.yahoo_chart, "1378.HK")
        self.assertEqual(meta.cover_since, "2026-03-01")
        self.assertEqual(meta.last_bar_date, "2026-09-08")
        charts = self.store.preferred_charts(["01378.HK"])
        self.assertEqual(charts["01378.HK"], "1378.HK")
