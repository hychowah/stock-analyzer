"""Portfolio book join + page/API smoke tests."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


def _mini_archive(base: Path) -> Path:
    archive = base / "archive"
    for ticker, session, fv, mos, audit in (
        ("META", "2026-08-03", 500.0, 20.0, "PASS"),
        ("AAPL", "2026-07-25", 200.0, -5.0, "PASS"),
        ("ORCL", "2026-08-03", 100.0, 10.0, "FAIL"),
    ):
        research = archive / "research" / ticker / session
        (research / "reports").mkdir(parents=True, exist_ok=True)
    catalog = archive / "catalog"
    catalog.mkdir(parents=True)
    db = catalog / "research_compare.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT);
        INSERT INTO schema_migrations VALUES (3, '2026-08-10T00:00:00Z');
        CREATE TABLE runs (
          run_id TEXT PRIMARY KEY,
          ticker TEXT, session_date TEXT, session_key TEXT, path TEXT,
          experiment_id TEXT, audit_verdict TEXT, data_quality TEXT, status TEXT,
          asof_price REAL, currency TEXT, primary_sector TEXT, region TEXT, intensity TEXT,
          fv_bear REAL, fv_base REAL, fv_bull REAL, fv_weighted REAL,
          p_bear REAL, p_base REAL, p_bull REAL, margin_of_safety_pct REAL,
          model_name TEXT, tech_signal TEXT, tech_regime TEXT,
          exported_at TEXT, harness_git_sha TEXT, orchestrator_model TEXT,
          quote_symbol TEXT, quote_listing TEXT, quote_listing_source TEXT
        );
        """
    )
    for ticker, session, fv, mos, audit in (
        ("META", "2026-08-03", 500.0, 20.0, "PASS"),
        ("AAPL", "2026-07-25", 200.0, -5.0, "PASS"),
        ("ORCL", "2026-08-03", 100.0, 10.0, "FAIL"),
    ):
        conn.execute(
            """
            INSERT INTO runs (
              run_id, ticker, session_date, session_key, path,
              audit_verdict, fv_base, fv_bear, margin_of_safety_pct, asof_price,
              quote_listing, quote_listing_source, exported_at, currency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"research:{ticker}:{session}",
                ticker,
                session,
                session,
                f"archive/research/{ticker}/{session}",
                audit,
                fv,
                fv * 0.7,
                mos,
                fv * 0.9,
                ticker,
                "stamp",
                "2026-08-10T00:00:00Z",
                "USD",
            ),
        )
    conn.commit()
    conn.close()
    return archive


class PortfolioServiceTests(unittest.TestCase):
    def test_waterfall_rows_mark_totals(self):
        from apps.analysis_web.services.ib_statement import parse_activity_csv
        from apps.analysis_web.services.portfolio import _waterfall_rows

        stmt = parse_activity_csv(
            Path(__file__).resolve().parent / "fixtures" / "ib_activity_mini.csv"
        )
        rows = {r["name"]: r for r in _waterfall_rows(stmt)}
        self.assertEqual(rows["Starting Value"]["kind"], "total")
        self.assertEqual(rows["Ending Value"]["kind"], "total")
        self.assertEqual(rows["Starting Value"]["bar_pct"], 0.0)
        flow = rows["Change in Dividend Accruals"]
        self.assertEqual(flow["kind"], "flow")
        self.assertGreater(flow["bar_pct"], 0)

    def test_mtm_gains_top_losses_bottom(self):
        from apps.analysis_web.services.ib_statement import IbStatement, MtmRow
        from apps.analysis_web.services.portfolio import _performance

        stmt = IbStatement(
            account_id="U1",
            period_from="2026-01-01",
            period_to="2026-03-31",
            mtm=[
                MtmRow("Stocks", "SMALL", pl_total=10.0),
                MtmRow("Stocks", "LOSE", pl_total=-90.0),
                MtmRow("Stocks", "WIN", pl_total=40.0),
            ],
        )
        names = [r["name"] for r in _performance(stmt)["mtm"]]
        self.assertEqual(names, ["WIN", "SMALL", "LOSE"])
        self.assertNotEqual(names, ["LOSE", "WIN", "SMALL"])

    def test_weighted_mos_and_coverage(self):
        from packages.catalog_api.client import CatalogApi
        from apps.analysis_web.services.portfolio import (
            PortfolioBook,
            PositionSpec,
            build_portfolio_view,
        )

        td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            archive = _mini_archive(Path(td.name))
            api = CatalogApi(archive_root=archive, readonly=True)
            book = PortfolioBook(
                name="t",
                positions=[
                    PositionSpec("META", weight=0.5),
                    PositionSpec("AAPL", weight=0.5),
                ],
            )
            view = build_portfolio_view(api, book, pass_only=False)
            self.assertEqual(view["summary"]["n_positions"], 2)
            self.assertEqual(view["summary"]["n_covered"], 2)
            self.assertEqual(view["summary"]["n_missing"], 0)
            # 0.5*20 + 0.5*(-5) = 7.5
            self.assertAlmostEqual(view["summary"]["weighted_mean_mos_pct"], 7.5, places=5)
            self.assertAlmostEqual(view["summary"]["mean_mos_pct"], 7.5, places=5)
            del api
        finally:
            td.cleanup()

    def test_pass_only_hides_fail_as_uncovered_if_no_pass(self):
        from packages.catalog_api.client import CatalogApi
        from apps.analysis_web.services.portfolio import (
            PortfolioBook,
            PositionSpec,
            build_portfolio_view,
        )

        td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            archive = _mini_archive(Path(td.name))
            api = CatalogApi(archive_root=archive, readonly=True)
            book = PortfolioBook(
                positions=[PositionSpec("ORCL", weight=1.0)],
            )
            view = build_portfolio_view(api, book, pass_only=True)
            self.assertEqual(view["summary"]["n_covered"], 0)
            view2 = build_portfolio_view(api, book, pass_only=False)
            self.assertEqual(view2["summary"]["n_covered"], 1)
            self.assertEqual(view2["positions"][0]["audit_verdict"], "FAIL")
            del api
        finally:
            td.cleanup()


class PortfolioHttpTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        base = Path(self._td.name)
        self.archive = _mini_archive(base)
        os.environ["ARCHIVE_ROOT"] = str(self.archive)

        # Point .local via writing book where config.local_dir points — monkeypatch
        import apps.analysis_web.config as cfg
        import apps.analysis_web.services.portfolio as port

        self._local = base / "local"
        self._local.mkdir()
        book = {
            "name": "test-book",
            "currency": "USD",
            "positions": [
                {"ticker": "META", "weight": 0.4},
                {"ticker": "AAPL", "weight": 0.4},
                {"ticker": "ZZZZ", "weight": 0.2},
            ],
        }
        (self._local / "portfolio.json").write_text(
            json.dumps(book), encoding="utf-8"
        )
        self._orig_local = cfg.local_dir
        cfg.local_dir = lambda: self._local  # type: ignore[assignment]
        port.local_dir = cfg.local_dir  # type: ignore[assignment]

        import importlib

        import apps.analysis_web.app as app_mod

        importlib.reload(app_mod)
        # re-apply monkeypatch after reload of modules that may re-import
        import apps.analysis_web.config as cfg2
        import apps.analysis_web.services.portfolio as port2

        cfg2.local_dir = lambda: self._local  # type: ignore[assignment]
        port2.local_dir = cfg2.local_dir  # type: ignore[assignment]

        from fastapi.testclient import TestClient

        self.client = TestClient(app_mod.create_app())

    def tearDown(self):
        import apps.analysis_web.config as cfg

        cfg.local_dir = self._orig_local  # type: ignore[assignment]
        self.client.close()
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_api_portfolio(self):
        r = self.client.get("/api/portfolio")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["name"], "test-book")
        self.assertEqual(data["summary"]["n_positions"], 3)
        self.assertEqual(data["summary"]["n_covered"], 2)
        tickers = {p["ticker"] for p in data["positions"]}
        self.assertEqual(tickers, {"META", "AAPL", "ZZZZ"})

    def test_portfolio_page(self):
        r = self.client.get("/portfolio")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"test-book", r.content)
        self.assertIn(b"META", r.content)
        self.assertIn(b"Weighted mean MoS", r.content)
        self.assertIn(b"data-downside-pct", r.content)
        self.assertIn(b'data-quote-symbol="META"', r.content)
        self.assertIn(b'data-quote-poll="0"', r.content)
        self.assertIn(b'id="live-nav"', r.content)
        self.assertIn(b"/static/live_nav.js", r.content)
        self.assertIn(b'data-fv-bear="350.0"', r.content)
        self.assertIn(b">As-of<", r.content)
        self.assertIn(b">Duration<", r.content)
        self.assertIn(b"/analyze/new?ticker=", r.content)

    def test_portfolio_empty_copy_is_import_statement(self):
        (self._local / "portfolio.json").unlink()
        r = self.client.get("/portfolio")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Import an IB activity statement.", r.content)
        self.assertIn(b"No IB book yet", r.content)
        self.assertNotIn(b"No book at", r.content)
        self.assertNotIn(b"apps/analysis_web/.local", r.content)
        self.assertNotIn(b"python -m apps.analysis_web.import_ib", r.content)


if __name__ == "__main__":
    unittest.main()
