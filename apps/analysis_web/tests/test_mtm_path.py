"""Reconstructed period MTM (FakeHistoryBackend; no network)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from apps.analysis_web.services.ib_statement import (
    IbBook,
    IbStatement,
    NavAsset,
    Position,
    Trade,
    parse_activity_csv,
)
from apps.analysis_web.services.mtm_path import (
    PeriodError,
    build_mtm_path,
    choose_path_args,
    parse_window_dates,
    resolve_period,
    trade_cash_by_listing,
    window_listings,
)
from apps.analysis_web.services.price_history import (
    FakeHistoryBackend,
    HistoryService,
    PriceBar,
    PriceHistory,
)
from apps.analysis_web.tests.test_ib_statement import FIXTURE
from apps.analysis_web.tests.test_portfolio import _mini_archive


def _book() -> IbBook:
    stmt = parse_activity_csv(FIXTURE)
    return IbBook(snapshot=stmt, trades=list(stmt.trades))


def _hist(symbol: str, bars: list[PriceBar]) -> PriceHistory:
    return PriceHistory(
        symbol=symbol,
        source="fake",
        bars=tuple(bars),
    )


class ResolvePeriodTests(unittest.TestCase):
    def test_allowlist_and_statement(self):
        stmt = parse_activity_csv(FIXTURE)
        self.assertEqual(
            resolve_period("statement", stmt),
            ("2026-01-01", "2026-03-31"),
        )
        self.assertEqual(
            resolve_period("1w", stmt, today="2026-09-10"),
            ("2026-09-03", "2026-09-10"),
        )
        self.assertEqual(
            resolve_period("1m", stmt, today="2026-09-10"),
            ("2026-08-11", "2026-09-10"),
        )
        self.assertEqual(
            resolve_period("ytd", stmt, today="2026-09-10"),
            ("2026-01-01", "2026-09-10"),
        )
        with self.assertRaises(PeriodError):
            resolve_period("1d", stmt, today="2026-09-10")
        with self.assertRaises(PeriodError):
            resolve_period("live", stmt, today="2026-09-10")


class ChoosePathArgsTests(unittest.TestCase):
    def test_period_xor_window(self):
        self.assertEqual(choose_path_args("1w", None, None), ("period", "1w", ""))
        self.assertEqual(
            choose_path_args(None, "2026-01-01", "2026-03-31"),
            ("window", "2026-01-01", "2026-03-31"),
        )
        with self.assertRaises(PeriodError):
            choose_path_args(None, None, None)
        with self.assertRaises(PeriodError):
            choose_path_args("1w", "2026-01-01", "2026-03-31")
        with self.assertRaises(PeriodError):
            choose_path_args(None, "2026-01-01", None)
        with self.assertRaises(PeriodError):
            parse_window_dates("2026-03-31", "2026-01-01")
        with self.assertRaises(PeriodError):
            parse_window_dates("nope", "2026-01-01")
        self.assertEqual(
            parse_window_dates("2026-01-01", "2026-03-31"),
            ("2026-01-01", "2026-03-31"),
        )


class BuildMtmPathTests(unittest.TestCase):
    def test_hold_through_is_price_move(self):
        book = _book()
        histories = {
            "META": _hist(
                "META",
                [PriceBar("2026-03-20", 50.0), PriceBar("2026-03-21", 55.0)],
            ),
            "0700.HK": _hist(
                "0700.HK",
                [PriceBar("2026-03-20", 10.0), PriceBar("2026-03-21", 10.0)],
            ),
        }
        out = build_mtm_path(
            book, histories, start="2026-03-20", end="2026-03-21"
        )
        self.assertIsNone(out["error"])
        self.assertEqual([fr["t"] for fr in out["frames"]], ["2026-03-20", "2026-03-21"])
        start_nav = out["start_nav"]
        self.assertAlmostEqual(start_nav, 500.0 + 10 * 50 * 8 + 100 * 10, places=5)
        first = {r["ib_symbol"]: r for r in out["frames"][0]["rows"]}
        self.assertAlmostEqual(first["META"]["pl"], 0.0, places=5)
        last = {r["ib_symbol"]: r for r in out["frames"][1]["rows"]}
        self.assertAlmostEqual(last["META"]["pl"], 10 * (55 - 50) * 8, places=5)
        self.assertAlmostEqual(last["700"]["pl"], 0.0, places=5)
        self.assertAlmostEqual(last["META"]["change_pct"], (55 / 50 - 1) * 100, places=5)
        self.assertAlmostEqual(
            last["META"]["contrib_pct"],
            last["META"]["pl"] / start_nav * 100,
            places=5,
        )
        names = [r["name"] for r in out["frames"][1]["bars"]]
        self.assertEqual(names, ["META"])

    def test_buy_mid_window_is_mark_minus_fill_not_full_value(self):
        book = _book()
        histories = {
            "META": _hist(
                "META",
                [
                    PriceBar("2026-01-14", 40.0),
                    PriceBar("2026-01-15", 42.0),
                    PriceBar("2026-01-16", 44.0),
                ],
            ),
            "0700.HK": _hist(
                "0700.HK",
                [
                    PriceBar("2026-01-14", 9.5),
                    PriceBar("2026-01-16", 10.0),
                ],
            ),
        }
        out = build_mtm_path(
            book, histories, start="2026-01-14", end="2026-01-16"
        )
        last = {r["ib_symbol"]: r for r in out["frames"][-1]["rows"]}
        self.assertIn("META", last)
        self.assertIsNotNone(last["META"]["pl"])
        # 12 bought @ 40, comm -1 USD, fx 8; still held 12 @ 44.
        value_t = 12 * 44 * 8
        fill_cash = (-480.0 + -1.0) * 8
        self.assertAlmostEqual(last["META"]["pl"], value_t + fill_cash, places=5)
        self.assertLess(last["META"]["pl"], value_t)

    def test_sold_name_is_fill_minus_start_not_minus_value(self):
        stmt = IbStatement(
            account_id="U1",
            period_from="2026-03-01",
            period_to="2026-03-10",
            base_currency="USD",
            forex_closes={"USD": 1.0},
            nav_assets=[NavAsset(asset_class="Cash", current_total=0.0)],
            positions=[
                Position(
                    ib_symbol="GONE",
                    asset_category="Stocks",
                    currency="USD",
                    quantity=0.0,
                    listing_exch="NASDAQ",
                )
            ],
        )
        sell = Trade(
            row_index=0,
            discriminator="Order",
            asset_category="Stocks",
            currency="USD",
            ib_symbol="GONE",
            traded_at="2026-03-05T10:00:00",
            quantity=-10.0,
            proceeds=500.0,
            commission=0.0,
        )
        book = IbBook(snapshot=stmt, trades=[sell])
        histories = {
            "GONE": _hist(
                "GONE",
                [PriceBar("2026-03-04", 50.0), PriceBar("2026-03-06", 40.0)],
            )
        }
        out = build_mtm_path(
            book, histories, start="2026-03-04", end="2026-03-06"
        )
        last = {r["ib_symbol"]: r for r in out["frames"][-1]["rows"]}
        self.assertIn("GONE", last)
        # Sold at the start mark: MTM is 0, not −start value.
        self.assertAlmostEqual(last["GONE"]["pl"], 0.0, places=5)

    def test_round_trip_keeps_realized_without_end_lot(self):
        stmt = IbStatement(
            account_id="U1",
            period_from="2026-03-01",
            period_to="2026-03-10",
            base_currency="USD",
            forex_closes={"USD": 1.0},
            nav_assets=[NavAsset(asset_class="Cash", current_total=0.0)],
            positions=[
                Position(
                    ib_symbol="FLIP",
                    asset_category="Stocks",
                    currency="USD",
                    quantity=0.0,
                    listing_exch="NASDAQ",
                )
            ],
        )
        buy = Trade(
            row_index=0,
            discriminator="Order",
            asset_category="Stocks",
            currency="USD",
            ib_symbol="FLIP",
            traded_at="2026-03-04T10:00:00",
            quantity=10.0,
            proceeds=-500.0,
            commission=0.0,
        )
        sell = Trade(
            row_index=1,
            discriminator="Order",
            asset_category="Stocks",
            currency="USD",
            ib_symbol="FLIP",
            traded_at="2026-03-06T10:00:00",
            quantity=-10.0,
            proceeds=550.0,
            commission=0.0,
        )
        book = IbBook(snapshot=stmt, trades=[buy, sell])
        out = build_mtm_path(
            book, {}, start="2026-03-03", end="2026-03-07"
        )
        last = {r["ib_symbol"]: r for r in out["frames"][-1]["rows"]}
        self.assertIn("FLIP", last)
        self.assertAlmostEqual(last["FLIP"]["pl"], 50.0, places=5)

    def test_held_unquoted_pl_is_none(self):
        book = _book()
        histories = {
            "0700.HK": _hist("0700.HK", [PriceBar("2026-03-20", 10.0)]),
        }
        out = build_mtm_path(
            book, histories, start="2026-03-20", end="2026-03-20"
        )
        by = {r["ib_symbol"]: r for r in out["frames"][0]["rows"]}
        self.assertIn("META", by)
        self.assertIsNone(by["META"]["pl"])
        self.assertAlmostEqual(by["700"]["pl"], 0.0, places=5)

    def test_window_listings_include_end_lots(self):
        book = _book()
        keys = window_listings(book, "2026-01-01", "2026-03-31")
        self.assertIn("META", keys)
        self.assertIn("0700.HK", keys)

    def test_trade_cash_excludes_start_day_includes_sell(self):
        book = _book()
        cash, unknown = trade_cash_by_listing(
            book, after="2026-01-15", through="2026-02-20"
        )
        self.assertEqual(unknown, set())
        self.assertNotIn("0700.HK", cash)
        self.assertAlmostEqual(cash["META"], (110.0 - 1.0) * 8, places=5)


class MtmPathHttpTests(unittest.TestCase):
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
        stmt = parse_activity_csv(FIXTURE)
        ingest_statement(stmt, path=self._local / "portfolio.sqlite")

        import importlib
        import apps.analysis_web.app as app_mod
        import apps.analysis_web.config as cfg2
        import apps.analysis_web.services.portfolio as port

        importlib.reload(app_mod)
        cfg2.local_dir = lambda: self._local  # type: ignore[assignment]
        port.local_dir = cfg2.local_dir  # type: ignore[assignment]

        self._app = app_mod.create_app()
        be = FakeHistoryBackend(
            {
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
        )
        self._app.state.history_service = HistoryService(be, ttl_sec=60)
        from fastapi.testclient import TestClient

        self.client = TestClient(self._app)

    def tearDown(self):
        import apps.analysis_web.config as cfg

        cfg.local_dir = self._orig_local  # type: ignore[assignment]
        self.client.close()
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_statement_path_has_frames(self):
        r = self.client.get("/api/portfolio/mtm-path?period=statement")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["period"], "statement")
        self.assertEqual(body["start"], "2026-01-01")
        self.assertEqual(body["end"], "2026-03-31")
        self.assertTrue(body["frames"])
        last = body["frames"][-1]
        self.assertEqual(last["t"], "2026-03-31")
        by = {row["ib_symbol"]: row for row in last["rows"]}
        self.assertIn("META", by)
        self.assertIn("pl", by["META"])
        self.assertIn("contrib_pct", by["META"])
        self.assertTrue(last["bars"])

    def test_bad_period_is_400(self):
        r = self.client.get("/api/portfolio/mtm-path?period=1d")
        self.assertEqual(r.status_code, 400)

    def test_start_end_path_has_frames(self):
        r = self.client.get(
            "/api/portfolio/mtm-path?start=2026-01-01&end=2026-03-31"
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["period"], "")
        self.assertEqual(body["start"], "2026-01-01")
        self.assertEqual(body["end"], "2026-03-31")
        self.assertTrue(body["frames"])
        last = body["frames"][-1]
        self.assertEqual(last["t"], "2026-03-31")
        by = {row["ib_symbol"]: row for row in last["rows"]}
        self.assertIn("META", by)
        self.assertIn("pl", by["META"])
        self.assertIn("contrib_pct", by["META"])

    def test_period_and_dates_is_400(self):
        r = self.client.get(
            "/api/portfolio/mtm-path?period=statement&start=2026-01-01&end=2026-03-31"
        )
        self.assertEqual(r.status_code, 400)

    def test_start_after_end_is_400(self):
        r = self.client.get(
            "/api/portfolio/mtm-path?start=2026-03-31&end=2026-01-01"
        )
        self.assertEqual(r.status_code, 400)

    def test_missing_args_is_400(self):
        r = self.client.get("/api/portfolio/mtm-path")
        self.assertEqual(r.status_code, 400)

    def test_player_js_fetches_path_not_quotes(self):
        js = (
            Path(__file__).resolve().parents[1] / "static" / "mtm_play.js"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/portfolio/mtm-path", js)
        self.assertIn("mtm-tbody", js)
        self.assertIn("data-period", js)
        self.assertNotIn("holding-pl-applied", js)
        self.assertNotIn("book-pl-mode-changed", js)
        self.assertNotIn("/api/quotes", js)
        self.assertNotIn('getElementById("quote-status")', js)

    def test_heatmap_js_fetches_path_not_bars(self):
        js = (
            Path(__file__).resolve().parents[1] / "static" / "heatmap.js"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/portfolio/mtm-path?period=", js)
        self.assertIn("start=", js)
        self.assertIn("holding-pl-applied", js)
        self.assertNotIn("heatmap-range-applied", js)
        self.assertNotIn("heatmap-live", js)
        self.assertNotIn("mtm-tbody", js)


if __name__ == "__main__":
    unittest.main()
