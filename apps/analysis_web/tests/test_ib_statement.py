"""IB activity CSV parser, store, and catalog overlay."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from apps.analysis_web.tests.test_portfolio import _mini_archive


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ib_activity_mini.csv"


def _strings(obj) -> str:
    return json.dumps(asdict(obj), default=str)


class ParseActivityCsvTests(unittest.TestCase):
    def setUp(self):
        from apps.analysis_web.services.ib_statement import parse_activity_csv

        self.stmt = parse_activity_csv(FIXTURE)

    def test_header_nav_twr_deposits(self):
        self.assertEqual(self.stmt.account_id, "U00000001")
        self.assertEqual(self.stmt.period_from, "2026-01-01")
        self.assertEqual(self.stmt.period_to, "2026-03-31")
        self.assertEqual(self.stmt.base_currency, "HKD")
        self.assertAlmostEqual(self.stmt.twr_pct or 0, 12.5, places=5)
        self.assertAlmostEqual(self.stmt.ending_nav or 0, 5500, places=5)
        self.assertAlmostEqual(self.stmt.deposits_total or 0, 5100, places=5)
        self.assertEqual(len(self.stmt.cashflows), 2)

    def test_no_pii_fields(self):
        blob = _strings(self.stmt)
        self.assertNotIn("FIXTURE USER", blob)
        self.assertNotIn("NOWHERE", blob)
        self.assertFalse(hasattr(self.stmt, "name"))
        self.assertFalse(hasattr(self.stmt, "address"))

    def test_positions_skip_totals(self):
        symbols = [p.ib_symbol for p in self.stmt.positions]
        self.assertEqual(symbols, ["700", "META"])
        self.assertEqual(self.stmt.positions[0].listing_exch, "SEHK")
        self.assertEqual(self.stmt.positions[1].listing_exch, "NASDAQ")

    def test_trades_include_forex_skip_subtotal(self):
        self.assertEqual(len(self.stmt.trades), 4)
        cats = {t.asset_category for t in self.stmt.trades}
        self.assertEqual(cats, {"Stocks", "Forex"})
        forex = [t for t in self.stmt.trades if t.asset_category == "Forex"]
        self.assertEqual(len(forex), 1)
        self.assertEqual(forex[0].ib_symbol, "USD.HKD")
        self.assertAlmostEqual(forex[0].quantity or 0, 1000.0, places=5)
        meta_buy = self.stmt.trades[1]
        self.assertEqual(meta_buy.traded_at, "2026-01-15T10:00:00")

    def test_nav_components_include_accrual(self):
        names = [c.name for c in self.stmt.nav_components]
        self.assertIn("Change in Dividend Accruals", names)
        self.assertIn("Starting Value", names)
        self.assertIn("Ending Value", names)
        self.assertEqual(len(names), 7)

    def test_value_base_fx_rule(self):
        by = {p.ib_symbol: p for p in self.stmt.positions}
        hkd = self.stmt.value_base(by["700"].value, by["700"].currency)
        usd = self.stmt.value_base(by["META"].value, by["META"].currency)
        self.assertAlmostEqual(hkd or 0, 1000.0, places=5)
        self.assertAlmostEqual(usd or 0, 4000.0, places=5)
        stock = self.stmt.nav_asset("Stock")
        self.assertIsNotNone(stock)
        self.assertAlmostEqual((hkd or 0) + (usd or 0), stock.current_total or 0, places=5)


class CatalogMapTests(unittest.TestCase):
    def test_sehk_pad_and_overrides(self):
        from apps.analysis_web.services.portfolio import map_catalog_ticker

        self.assertEqual(map_catalog_ticker("700", "SEHK"), "0700.HK")
        self.assertEqual(map_catalog_ticker("2318", "SEHK"), "2318.HK")
        from apps.analysis_web.services.portfolio import catalog_lookup_tickers

        self.assertEqual(catalog_lookup_tickers("2318", "SEHK"), ["2318.HK", "02318.HK"])
        self.assertEqual(catalog_lookup_tickers("700", "SEHK"), ["0700.HK", "00700.HK"])
        self.assertEqual(map_catalog_ticker("HY9H", "BATS"), "000660.KS")
        self.assertEqual(map_catalog_ticker("MC", "SBF"), "MC.PA")
        self.assertEqual(map_catalog_ticker("ADYEN", "AEB"), "ADYEN")
        self.assertEqual(map_catalog_ticker("META", "NASDAQ"), "META")
        self.assertEqual(map_catalog_ticker("4516.T", "TSEJ"), "4516.T")


class StoreTests(unittest.TestCase):
    def test_replace_is_idempotent(self):
        from apps.analysis_web.services.ib_statement import parse_activity_csv
        from apps.analysis_web.services.portfolio_store import load, replace_statement

        stmt = parse_activity_csv(FIXTURE)
        td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            db = Path(td.name) / "portfolio.sqlite"
            replace_statement(stmt, path=db)
            replace_statement(stmt, path=db)
            loaded = load(path=db)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(len(loaded.trades), 4)
            self.assertEqual(len(loaded.positions), 2)
            self.assertEqual(loaded.account_id, "U00000001")
            self.assertAlmostEqual(loaded.twr_pct or 0, 12.5, places=5)
            blob = _strings(loaded)
            self.assertNotIn("FIXTURE USER", blob)
            self.assertNotIn("NOWHERE", blob)
        finally:
            td.cleanup()


class ImportDoesNotWriteJsonTests(unittest.TestCase):
    def test_import_skips_json(self):
        import apps.analysis_web.config as cfg
        from apps.analysis_web.import_ib import import_statement

        td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        orig = cfg.local_dir
        try:
            local = Path(td.name) / "local"
            local.mkdir()
            cfg.local_dir = lambda: local  # type: ignore[assignment]
            result = import_statement(FIXTURE)
            self.assertEqual(result["trades_imported"], 4)
            self.assertFalse(result["json_rewritten"])
            self.assertFalse((local / "portfolio.json").exists())
            self.assertTrue((local / "portfolio.sqlite").is_file())
            self.assertTrue((local / "ib" / "statements" / FIXTURE.name).is_file())
        finally:
            cfg.local_dir = orig  # type: ignore[assignment]
            td.cleanup()


class IbPortfolioViewTests(unittest.TestCase):
    def test_ib_identity_and_weights(self):
        from packages.catalog_api.client import CatalogApi
        from apps.analysis_web.services.ib_statement import parse_activity_csv
        from apps.analysis_web.services.portfolio import build_portfolio_view

        td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            api = CatalogApi(archive_root=_mini_archive(Path(td.name)), readonly=True)
            stmt = parse_activity_csv(FIXTURE)
            view = build_portfolio_view(api, statement=stmt, pass_only=False)
            by = {p["ib_symbol"]: p for p in view["positions"]}
            self.assertEqual(by["700"]["ib_symbol"], "700")
            self.assertEqual(by["700"]["catalog_ticker"], "0700.HK")
            self.assertFalse(by["700"]["covered"])
            self.assertEqual(by["META"]["ib_symbol"], "META")
            self.assertTrue(by["META"]["covered"])
            self.assertAlmostEqual(by["700"]["weight"], 0.2, places=5)
            self.assertAlmostEqual(by["META"]["weight"], 0.8, places=5)
            names = [r["name"] for r in view["performance"]["waterfall"]]
            self.assertIn("Change in Dividend Accruals", names)
            self.assertEqual(view["ib"]["trade_count"], 4)
            self.assertEqual(view["ib"]["account_masked"], "U0000…001")
            mtm_syms = {r["ib_symbol"] for r in view["performance"]["mtm"]}
            self.assertIn("CLOSED", mtm_syms)
            del api
        finally:
            td.cleanup()


class IbPortfolioHttpTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        base = Path(self._td.name)
        self.archive = _mini_archive(base)
        os.environ["ARCHIVE_ROOT"] = str(self.archive)
        self._local = base / "local"
        self._local.mkdir()

        import apps.analysis_web.config as cfg
        from apps.analysis_web.services.ib_statement import parse_activity_csv
        from apps.analysis_web.services.portfolio_store import replace_statement

        self._orig_local = cfg.local_dir
        cfg.local_dir = lambda: self._local  # type: ignore[assignment]
        stmt = parse_activity_csv(FIXTURE)
        replace_statement(stmt, path=self._local / "portfolio.sqlite")
        # JSON book must not win
        (self._local / "portfolio.json").write_text(
            json.dumps(
                {
                    "name": "should-not-appear",
                    "currency": "USD",
                    "positions": [{"ticker": "AAPL", "weight": 1}],
                }
            ),
            encoding="utf-8",
        )

        import importlib
        import apps.analysis_web.app as app_mod
        import apps.analysis_web.config as cfg2
        import apps.analysis_web.services.portfolio as port

        importlib.reload(app_mod)
        cfg2.local_dir = lambda: self._local  # type: ignore[assignment]
        port.local_dir = cfg2.local_dir  # type: ignore[assignment]

        from fastapi.testclient import TestClient

        self.client = TestClient(app_mod.create_app())

    def tearDown(self):
        import apps.analysis_web.config as cfg

        cfg.local_dir = self._orig_local  # type: ignore[assignment]
        self.client.close()
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_api_ib_block(self):
        r = self.client.get("/api/portfolio")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsNotNone(data.get("ib"))
        self.assertEqual(data["ib"]["trade_count"], 4)
        self.assertAlmostEqual(data["ib"]["twr_pct"], 12.5)
        names = [row["name"] for row in data["performance"]["waterfall"]]
        self.assertIn("Change in Dividend Accruals", names)
        self.assertIn("Ending Value", names)
        tickers = {p["ib_symbol"] for p in data["positions"]}
        self.assertEqual(tickers, {"700", "META"})
        self.assertNotIn("AAPL", tickers)
        self.assertNotIn("should-not-appear", data.get("name") or "")

    def test_page_waterfall_html(self):
        r = self.client.get("/portfolio")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Change in NAV", r.content)
        self.assertIn(b"Change in Dividend Accruals", r.content)
        self.assertIn(b"<strong>Starting Value</strong>", r.content)
        self.assertIn(b"<strong>Ending Value</strong>", r.content)
        self.assertIn(b"left:50%", r.content)
        self.assertIn(b"right:50%", r.content)
        self.assertIn(b"Mark-to-market P/L", r.content)
        self.assertIn(b"12.50%", r.content)
        self.assertIn(b">700<", r.content)
        self.assertNotIn(b"should-not-appear", r.content)
        self.assertNotIn(b"portfolio_chart.js", r.content)


class CorruptSqliteHttpTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        base = Path(self._td.name)
        self.archive = _mini_archive(base)
        os.environ["ARCHIVE_ROOT"] = str(self.archive)
        self._local = base / "local"
        self._local.mkdir()
        (self._local / "portfolio.sqlite").write_bytes(b"not a sqlite database")
        (self._local / "portfolio.json").write_text(
            json.dumps(
                {
                    "name": "json-fallback-must-not-run",
                    "positions": [{"ticker": "META", "weight": 1}],
                }
            ),
            encoding="utf-8",
        )
        import apps.analysis_web.config as cfg

        self._orig_local = cfg.local_dir
        cfg.local_dir = lambda: self._local  # type: ignore[assignment]
        import importlib
        import apps.analysis_web.app as app_mod
        import apps.analysis_web.config as cfg2
        import apps.analysis_web.services.portfolio as port

        importlib.reload(app_mod)
        cfg2.local_dir = lambda: self._local  # type: ignore[assignment]
        port.local_dir = cfg2.local_dir  # type: ignore[assignment]
        from fastapi.testclient import TestClient

        self.client = TestClient(app_mod.create_app())

    def tearDown(self):
        import apps.analysis_web.config as cfg

        cfg.local_dir = self._orig_local  # type: ignore[assignment]
        self.client.close()
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_corrupt_sqlite_does_not_use_json(self):
        r = self.client.get("/portfolio")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"json-fallback-must-not-run", r.content)
        self.assertTrue(
            b"unreadable" in r.content.lower() or b"not a database" in r.content.lower() or b"IB book" in r.content,
            msg=r.content[:500],
        )


class ChangeFeedSqliteTests(unittest.TestCase):
    def test_sqlite_change_is_portfolio_changed(self):
        from apps.analysis_web.services import change_feed as cf

        with tempfile.TemporaryDirectory() as td:
            ar = Path(td) / "archive"
            (ar / "catalog").mkdir(parents=True)
            local = Path(td) / "local"
            local.mkdir()
            (local / "portfolio.json").write_text("{}", encoding="utf-8")
            orig_local = cf.local_dir
            orig_archive = cf.archive_root
            try:
                cf.local_dir = lambda: local  # type: ignore[assignment]
                cf.archive_root = lambda: ar  # type: ignore[assignment]
                fp1 = cf.fingerprint(root=ar)
                (local / "portfolio.sqlite").write_bytes(b"x")
                fp2 = cf.fingerprint(root=ar)
                self.assertNotEqual(fp1["token"], fp2["token"])
                self.assertIn("portfolio_changed", cf.classify_change(fp1, fp2))
            finally:
                cf.local_dir = orig_local  # type: ignore[assignment]
                cf.archive_root = orig_archive  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
