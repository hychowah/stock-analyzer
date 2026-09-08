"""Yahoo bar helpers: HK padding, search pick, resolve, split_download (no network)."""

from __future__ import annotations

import unittest

import pandas as pd

from apps.analysis_web.services.price_history import YahooHistoryBackend
from apps.analysis_web.services.quotes import YahooPrintBackend
from apps.analysis_web.services.yahoo_bars import (
    listing_candidates,
    pick_search_listing,
    resolve_close_series,
    split_download,
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
