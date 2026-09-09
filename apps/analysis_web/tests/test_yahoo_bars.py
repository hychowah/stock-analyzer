"""Yahoo bar helpers: HK padding, search pick, resolve, split_download (no network)."""

from __future__ import annotations

import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from apps.analysis_web.services.price_history import YahooHistoryBackend
from apps.analysis_web.services.quotes import YahooPrintBackend
from apps.analysis_web.services.yahoo_bars import (
    download_close_series,
    listing_candidates,
    pick_search_listing,
    reset_yfinance_cache,
    resolve_close_series,
    search_yahoo_quotes,
    split_download,
    sqlite_file_ok,
    yfinance_cache_malformed,
)


def _rows(*closes: float) -> list[tuple[float, str | None]]:
    return [(px, f"t{i}") for i, px in enumerate(closes)]


class ListingCandidateTests(unittest.TestCase):
    def test_hk_five_digit_strips_one_zero(self):
        self.assertEqual(listing_candidates("01378.HK"), ["01378.HK", "1378.HK"])
        self.assertEqual(listing_candidates("02318.hk"), ["02318.HK", "2318.HK"])
        self.assertEqual(listing_candidates("00700.HK"), ["00700.HK", "0700.HK"])

    def test_hk_four_digit_unchanged(self):
        self.assertEqual(listing_candidates("0700.HK"), ["0700.HK"])
        self.assertEqual(listing_candidates("2209.HK"), ["2209.HK"])

    def test_non_hk_unchanged(self):
        self.assertEqual(listing_candidates("000660.KS"), ["000660.KS"])
        self.assertEqual(listing_candidates("ADYEN"), ["ADYEN"])
        self.assertEqual(listing_candidates("ADYEN.AS"), ["ADYEN.AS"])
        self.assertEqual(listing_candidates(""), [])


class PickSearchListingTests(unittest.TestCase):
    def test_suffix_hit(self):
        hits = [
            {"symbol": "ADYEN.AS", "quoteType": "EQUITY"},
            {"symbol": "ADYEY", "quoteType": "EQUITY"},
            {"symbol": "1N8.F", "quoteType": "EQUITY"},
        ]
        self.assertEqual(pick_search_listing("ADYEN", hits), "ADYEN.AS")

    def test_exact_hit_means_search_cannot_help(self):
        hits = [
            {"symbol": "GT", "quoteType": "EQUITY"},
            {"symbol": "GTQUSD=X", "quoteType": "CURRENCY"},
        ]
        self.assertIsNone(pick_search_listing("GT", hits))

    def test_dotted_query_skipped(self):
        hits = [{"symbol": "1378.HK", "quoteType": "EQUITY"}]
        self.assertIsNone(pick_search_listing("01378.HK", hits))

    def test_currency_suffix_ignored(self):
        hits = [{"symbol": "FOO=X", "quoteType": "CURRENCY"}]
        self.assertIsNone(pick_search_listing("FOO", hits))


class SplitDownloadTests(unittest.TestCase):
    def test_multiindex_partial(self):
        arrays = [
            ["META", "META", "AAPL", "AAPL"],
            ["Open", "Close", "Open", "Close"],
        ]
        cols = pd.MultiIndex.from_arrays(arrays)
        idx = pd.date_range("2026-09-01", periods=2)
        data = pd.DataFrame(
            [[1.0, 10.0, 2.0, 20.0], [1.1, 11.0, 2.2, 22.0]],
            index=idx,
            columns=cols,
        )
        frames = split_download(data, ["META", "AAPL", "NOPE"])
        self.assertIsNotNone(frames["META"])
        self.assertIsNotNone(frames["AAPL"])
        self.assertIsNone(frames["NOPE"])

    def test_single_requested_ohlcv(self):
        data = pd.DataFrame(
            {"Open": [1.0], "Close": [10.0]},
            index=pd.date_range("2026-09-01", periods=1),
        )
        frames = split_download(data, ["META"])
        self.assertIsNotNone(frames["META"])

    def test_single_frame_many_requested_stays_unattributed(self):
        data = pd.DataFrame(
            {"Open": [1.0], "Close": [10.0]},
            index=pd.date_range("2026-09-01", periods=1),
        )
        frames = split_download(data, ["META", "AAPL"])
        self.assertIsNone(frames["META"])
        self.assertIsNone(frames["AAPL"])


class _TableDownload:
    """period/interval -> yahoo symbol -> rows."""

    def __init__(self, table: dict[tuple[str, str, str], list[tuple[float, str | None]]]):
        self.table = table
        self.calls: list[tuple[tuple[str, ...], str, str]] = []

    def __call__(self, yf, symbols, *, period, interval):  # noqa: ANN001
        self.calls.append((tuple(symbols), period, interval))
        out: dict[str, list[tuple[float, str | None]]] = {}
        for s in symbols:
            out[s] = list(self.table.get((s, period, interval), []))
        return out


class ResolveCloseSeriesTests(unittest.TestCase):
    def test_hk_padding_uses_four_digit_series(self):
        dl = _TableDownload({("1378.HK", "5d", "1d"): _rows(23.0, 23.5)})
        got = resolve_close_series(
            object(),
            ["01378.HK"],
            period="5d",
            interval="1d",
            download=dl,
            search=lambda yf, q: [],
        )
        yahoo, rows = got["01378.HK"]
        self.assertEqual(yahoo, "1378.HK")
        self.assertEqual(rows[-1][0], 23.5)
        self.assertEqual(dl.calls[0][0], ("01378.HK",))
        self.assertEqual(dl.calls[1][0], ("1378.HK",))

    def test_batch_peer_already_has_unpadded_listing(self):
        dl = _TableDownload({("2618.HK", "5d", "1d"): _rows(11.0)})
        got = resolve_close_series(
            object(),
            ["02618.HK", "2618.HK"],
            period="5d",
            interval="1d",
            download=dl,
            search=lambda yf, q: (_ for _ in ()).throw(AssertionError("search")),
        )
        self.assertEqual(got["2618.HK"][0], "2618.HK")
        self.assertEqual(got["02618.HK"], ("2618.HK", _rows(11.0)))
        self.assertEqual(len(dl.calls), 1)

    def test_search_suffix_for_unstamped_european(self):
        dl = _TableDownload({("ADYEN.AS", "5d", "1d"): _rows(1000.0, 1010.0)})
        searches: list[str] = []

        def search(yf, q):  # noqa: ANN001
            searches.append(q)
            return [
                {"symbol": "ADYEN.AS", "quoteType": "EQUITY"},
                {"symbol": "ADYEY", "quoteType": "EQUITY"},
            ]

        got = resolve_close_series(
            object(),
            ["ADYEN", "META"],
            period="5d",
            interval="1d",
            download=dl,
            search=search,
        )
        self.assertEqual(got["ADYEN"][0], "ADYEN.AS")
        self.assertEqual(got["ADYEN"][1][-1][0], 1010.0)
        self.assertEqual(got["META"][1], [])
        self.assertEqual(searches, ["ADYEN", "META"])

    def test_hit_as_is_skips_search(self):
        dl = _TableDownload({("META", "5d", "1d"): _rows(100.0)})

        def search(yf, q):  # noqa: ANN001
            raise AssertionError("search should not run for hits")

        got = resolve_close_series(
            object(), ["META"], period="5d", interval="1d", download=dl, search=search
        )
        self.assertEqual(got["META"][0], "META")
        self.assertEqual(len(dl.calls), 1)

    def test_dotted_miss_does_not_search(self):
        dl = _TableDownload({})
        searches: list[str] = []

        def search(yf, q):  # noqa: ANN001
            searches.append(q)
            return [{"symbol": "1378.HK", "quoteType": "EQUITY"}]

        got = resolve_close_series(
            object(),
            ["01378.HK"],
            period="5d",
            interval="1d",
            download=dl,
            search=search,
        )
        self.assertEqual(got["01378.HK"][1], [])
        self.assertEqual(searches, [])


class YahooPrintBackendResolveTests(unittest.TestCase):
    def test_intraday_uses_resolved_yahoo_symbol(self):
        dl = _TableDownload(
            {
                ("1378.HK", "5d", "1d"): _rows(23.0, 23.4),
                ("1378.HK", "1d", "1m"): _rows(23.5),
            }
        )
        be = YahooPrintBackend(
            yf=object(), download=dl, search=lambda yf, q: []
        )
        rows = be.quote_many(["01378.HK"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].symbol, "01378.HK")
        self.assertEqual(rows[0].price, 23.5)
        self.assertEqual(rows[0].print_kind, "intraday")
        self.assertIsNone(rows[0].error)
        intra_calls = [c for c in dl.calls if c[2] == "1m"]
        self.assertEqual(intra_calls[0][0], ("1378.HK",))

    def test_skips_intraday_when_daily_missing(self):
        dl = _TableDownload({})
        be = YahooPrintBackend(
            yf=object(), download=dl, search=lambda yf, q: []
        )
        rows = be.quote_many(["NOPE"])
        self.assertEqual(rows[0].error, "unavailable")
        self.assertFalse(any(c[2] == "1m" for c in dl.calls))


class YahooHistoryBackendResolveTests(unittest.TestCase):
    def test_history_follows_hk_padding(self):
        dl = _TableDownload({("1378.HK", "1y", "1d"): _rows(20.0, 21.0)})
        be = YahooHistoryBackend(
            yf=object(), download=dl, search=lambda yf, q: []
        )
        hist = be.history("01378.HK", "1y")
        self.assertIsNone(hist.error)
        self.assertEqual(hist.symbol, "01378.HK")
        self.assertEqual(hist.bars[-1].close, 21.0)

    def test_history_many_one_download(self):
        dl = _TableDownload(
            {
                ("META", "1y", "1d"): _rows(100.0),
                ("AAPL", "1y", "1d"): _rows(200.0),
            }
        )
        be = YahooHistoryBackend(
            yf=object(), download=dl, search=lambda yf, q: []
        )
        got = be.history_many(["META", "AAPL", "NOPE"], "1y")
        self.assertEqual(len(dl.calls), 1)
        self.assertEqual(dl.calls[0][0], ("META", "AAPL", "NOPE"))
        self.assertEqual(got["META"].bars[-1].close, 100.0)
        self.assertEqual(got["AAPL"].bars[-1].close, 200.0)
        self.assertEqual(got["NOPE"].error, "unavailable")

    def test_history_blank_symbol_is_unavailable(self):
        be = YahooHistoryBackend(
            yf=object(),
            download=lambda *a, **k: (_ for _ in ()).throw(AssertionError("download")),
            search=lambda yf, q: [],
        )
        hist = be.history("  ", "1y")
        self.assertEqual(hist.error, "unavailable")
        self.assertEqual(hist.bars, ())


class YfIoLockTests(unittest.TestCase):
    def setUp(self) -> None:
        p_mal = patch(
            "apps.analysis_web.services.yahoo_bars.yfinance_cache_malformed",
            return_value=False,
        )
        p_reset = patch("apps.analysis_web.services.yahoo_bars.reset_yfinance_cache")
        p_mal.start()
        p_reset.start()
        self.addCleanup(p_mal.stop)
        self.addCleanup(p_reset.stop)

    def _overlap_probe(self):
        active = 0
        overlapped: list[int] = []
        gate = threading.Lock()
        entered = threading.Event()
        release = threading.Event()

        def enter() -> None:
            nonlocal active
            with gate:
                active += 1
                if active > 1:
                    overlapped.append(active)
                entered.set()
            release.wait(timeout=2)
            with gate:
                active -= 1

        return overlapped, entered, release, enter

    def test_download_serializes_across_threads(self):
        overlapped, entered, release, enter = self._overlap_probe()

        class Yf:
            def download(self, **kwargs):  # noqa: ANN003
                enter()
                return pd.DataFrame()

        def worker() -> None:
            download_close_series(Yf(), ["META"], period="1y", interval="1d")

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        self.assertTrue(entered.wait(timeout=2))
        t2.start()
        time.sleep(0.05)
        release.set()
        t1.join(timeout=2)
        t2.join(timeout=2)
        self.assertEqual(overlapped, [])

    def test_search_and_download_do_not_overlap(self):
        overlapped, entered, release, enter = self._overlap_probe()

        class DownYf:
            def download(self, **kwargs):  # noqa: ANN003
                enter()
                return pd.DataFrame()

        class SearchYf:
            def Search(self, query, max_results=8):  # noqa: ANN001
                enter()
                return type("Found", (), {"quotes": []})()

        t1 = threading.Thread(
            target=lambda: download_close_series(
                DownYf(), ["META"], period="1y", interval="1d"
            )
        )
        t2 = threading.Thread(
            target=lambda: search_yahoo_quotes(SearchYf(), "META")
        )
        t1.start()
        self.assertTrue(entered.wait(timeout=2))
        t2.start()
        time.sleep(0.05)
        release.set()
        t1.join(timeout=2)
        t2.join(timeout=2)
        self.assertEqual(overlapped, [])

    def test_nested_search_under_download_does_not_deadlock(self):
        calls: list[str] = []

        class Yf:
            def download(self, **kwargs):  # noqa: ANN003
                calls.append("download")
                search_yahoo_quotes(self, "META")
                return pd.DataFrame()

            def Search(self, query, max_results=8):  # noqa: ANN001
                calls.append("search")
                return type("Found", (), {"quotes": []})()

        download_close_series(Yf(), ["META"], period="1y", interval="1d")
        self.assertEqual(calls, ["download", "search"])


class DownloadRetryTests(unittest.TestCase):
    def test_retries_after_download_exception(self):
        n = {"dl": 0, "reset": 0}

        class Yf:
            def download(self, **kwargs):  # noqa: ANN003
                n["dl"] += 1
                if n["dl"] == 1:
                    raise RuntimeError("cache")
                idx = pd.date_range("2026-09-01", periods=1)
                return pd.DataFrame({"Close": [123.0]}, index=idx)

        with (
            patch(
                "apps.analysis_web.services.yahoo_bars.yfinance_cache_malformed",
                return_value=False,
            ),
            patch(
                "apps.analysis_web.services.yahoo_bars.reset_yfinance_cache",
                side_effect=lambda *a, **k: n.__setitem__("reset", n["reset"] + 1),
            ),
        ):
            out = download_close_series(Yf(), ["META"], period="1y", interval="1d")
        self.assertEqual(n["dl"], 2)
        self.assertEqual(n["reset"], 1)
        self.assertEqual(out["META"][-1][0], 123.0)

    def test_retries_when_empty_and_cache_malformed(self):
        n = {"dl": 0, "reset": 0}
        malformed = {"v": False}

        class Yf:
            def download(self, **kwargs):  # noqa: ANN003
                n["dl"] += 1
                if n["dl"] == 1:
                    malformed["v"] = True
                    return pd.DataFrame()
                idx = pd.date_range("2026-09-01", periods=1)
                return pd.DataFrame({"Close": [99.0]}, index=idx)

        def is_malformed(cache_dir=None):  # noqa: ANN001
            return malformed["v"]

        def reset(cache_dir=None):  # noqa: ANN001
            n["reset"] += 1
            malformed["v"] = False

        with (
            patch(
                "apps.analysis_web.services.yahoo_bars.yfinance_cache_malformed",
                is_malformed,
            ),
            patch(
                "apps.analysis_web.services.yahoo_bars.reset_yfinance_cache",
                reset,
            ),
        ):
            out = download_close_series(Yf(), ["META"], period="1y", interval="1d")
        self.assertEqual(n["dl"], 2)
        self.assertEqual(n["reset"], 1)
        self.assertEqual(out["META"][-1][0], 99.0)


class YfinanceCacheTests(unittest.TestCase):
    def test_malformed_tz_db_is_detected_and_reset(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            good = sqlite3.connect(d / "cookies.db")
            good.execute("CREATE TABLE t (x INTEGER)")
            good.commit()
            good.close()
            (d / "tkr-tz.db").write_bytes(b"not a sqlite database")
            self.assertTrue(sqlite_file_ok(d / "cookies.db"))
            self.assertFalse(sqlite_file_ok(d / "tkr-tz.db"))
            self.assertTrue(yfinance_cache_malformed(d))
            reset_yfinance_cache(d)
            self.assertFalse((d / "tkr-tz.db").exists())
            self.assertFalse(yfinance_cache_malformed(d))

    def test_missing_cache_is_not_malformed(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            self.assertTrue(sqlite_file_ok(d / "tkr-tz.db"))
            self.assertFalse(yfinance_cache_malformed(d))
