"""What-if pages: no live_nav.js; POST composer; Δ equals chart end."""

from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

from apps.analysis_web.services.price_history import (
    FakeHistoryBackend,
    HistoryService,
    PriceBar,
)
from apps.analysis_web.tests.test_book_state import FIXTURE
from apps.analysis_web.tests.test_portfolio import _mini_archive


def _bars() -> dict[str, list[PriceBar]]:
    return {
        "META": [PriceBar("2026-03-31", 50.0), PriceBar("2026-04-01", 55.0)],
        "0700.HK": [PriceBar("2026-03-31", 10.0), PriceBar("2026-04-01", 10.0)],
        "AAPL": [PriceBar("2026-03-31", 200.0), PriceBar("2026-04-01", 210.0)],
        "ORCL": [PriceBar("2026-03-31", 100.0), PriceBar("2026-04-01", 101.0)],
    }


class HistoryHttpTests(unittest.TestCase):
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

        self._app = app_mod.create_app()
        self._app.state.history_service = HistoryService(
            FakeHistoryBackend(_bars()), ttl_sec=60
        )
        from fastapi.testclient import TestClient

        self.client = TestClient(self._app)

    def tearDown(self):
        import apps.analysis_web.config as cfg

        cfg.local_dir = self._orig_local  # type: ignore[assignment]
        self.client.close()
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_list_empty_state(self):
        r = self.client.get("/portfolio/histories")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Copy your IB trades", r.content)
        self.assertIn(b"Copy my trades", r.content)
        self.assertNotIn(b"live_nav.js", r.content)
        self.assertIn(b"What-if", r.content)
        self.assertIn(b'href="/portfolio"', r.content)

    def test_portfolio_keeps_live_nav_and_subnav(self):
        r = self.client.get("/portfolio")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"/static/live_nav.js", r.content)
        self.assertIn(b"/portfolio/histories", r.content)
        self.assertIn(b'data-quote-poll="0"', r.content)

    def test_get_new_form(self):
        r = self.client.get("/portfolio/histories/new")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Copy my trades", r.content)
        self.assertIn(b"Copy trades", r.content)
        self.assertNotIn(b"live_nav.js", r.content)

    def test_new_stores_fork_and_editor(self):
        r = self.client.post(
            "/portfolio/histories/new",
            data={"name": "Missed AAPL"},
            follow_redirects=True,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Missed AAPL", r.content)
        self.assertIn(b"Holdings on this day", r.content)
        self.assertNotIn(b"live_nav.js", r.content)
        self.assertIn(b"alt_history.js", r.content)
        self.assertIn(b"META", r.content)

    def test_unknown_id_404(self):
        r = self.client.get("/portfolio/histories/9999")
        self.assertEqual(r.status_code, 404)

    def test_buy_and_sell_and_delta_matches_path(self):
        created = self.client.post(
            "/portfolio/histories/new",
            data={"name": "Path"},
            follow_redirects=False,
        )
        self.assertEqual(created.status_code, 303)
        loc = created.headers["location"]
        hid = loc.rsplit("/", 1)[-1].split("?")[0]

        sell = self.client.post(
            f"/portfolio/histories/{hid}/decisions",
            data={
                "side": "sell",
                "listing": "META",
                "as_of": "2026-03-31",
                "quantity": "10",
            },
            follow_redirects=True,
        )
        self.assertEqual(sell.status_code, 200)
        self.assertIn(b"sell META", sell.content)

        buy = self.client.post(
            f"/portfolio/histories/{hid}/decisions",
            data={
                "side": "buy",
                "ticker": "AAPL",
                "as_of": "2026-03-31",
                "quantity": "1",
            },
            follow_redirects=True,
        )
        self.assertEqual(buy.status_code, 200)
        self.assertIn(b"buy AAPL", buy.content)
        self.assertNotIn(b"live_nav.js", buy.content)

        api = self.client.get(f"/api/portfolio/histories/{hid}")
        self.assertEqual(api.status_code, 200)
        body = api.json()
        self.assertIsNotNone(body["delta"])
        self.assertGreaterEqual(len(body["path"]), 2)
        last = body["path"][-1]
        self.assertAlmostEqual(body["delta"], last["delta"], places=5)
        self.assertAlmostEqual(body["alt_nav"], last["alt_nav"], places=5)
        self.assertAlmostEqual(body["actual_nav"], last["actual_nav"], places=5)

        html = buy.text
        m = re.search(r'id="hist-delta"[^>]*>([^<]+)', html)
        self.assertIsNotNone(m)
        listed = self.client.get("/api/portfolio/histories")
        rows = listed.json()["histories"]
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["delta"], last["delta"], places=5)

    def test_buy_unknown_stays_on_editor(self):
        created = self.client.post(
            "/portfolio/histories/new",
            data={"name": "Bad"},
            follow_redirects=False,
        )
        hid = created.headers["location"].rsplit("/", 1)[-1].split("?")[0]
        r = self.client.post(
            f"/portfolio/histories/{hid}/decisions",
            data={
                "side": "buy",
                "ticker": "ZZZZ",
                "as_of": "2026-03-31",
                "quantity": "1",
            },
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn(b"not on the researched list", r.content)

    def test_copy(self):
        created = self.client.post(
            "/portfolio/histories/new",
            data={"name": "Orig"},
            follow_redirects=False,
        )
        hid = created.headers["location"].rsplit("/", 1)[-1].split("?")[0]
        copied = self.client.post(
            f"/portfolio/histories/{hid}/copy", follow_redirects=True
        )
        self.assertEqual(copied.status_code, 200)
        self.assertIn(b"Orig copy", copied.content)
        listed = self.client.get("/api/portfolio/histories").json()["histories"]
        self.assertEqual(len(listed), 2)
        overlay = self.client.get("/portfolio/histories")
        self.assertEqual(overlay.status_code, 200)
        self.assertIn(b"All histories vs actual", overlay.content)
        self.assertIn(b"nav-chart-svg", overlay.content)

    def test_list_without_ib_file_is_empty_ok(self):
        (self._local / "portfolio.sqlite").unlink()
        r = self.client.get("/portfolio/histories")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Copy my trades", r.content)
        self.assertNotIn(b"live_nav.js", r.content)
        new = self.client.get("/portfolio/histories/new")
        self.assertEqual(new.status_code, 200)
        self.assertIn(b"Import an IB activity statement first.", new.content)

    def test_editor_and_sell_without_ib_file(self):
        created = self.client.post(
            "/portfolio/histories/new",
            data={"name": "No IB"},
            follow_redirects=False,
        )
        self.assertEqual(created.status_code, 303)
        hid = created.headers["location"].rsplit("/", 1)[-1].split("?")[0]
        (self._local / "portfolio.sqlite").unlink()
        listed = self.client.get("/portfolio/histories")
        self.assertEqual(listed.status_code, 200)
        self.assertIn(b"No IB", listed.content)
        editor = self.client.get(f"/portfolio/histories/{hid}")
        self.assertEqual(editor.status_code, 200)
        self.assertIn(b"Holdings on this day", editor.content)
        self.assertNotIn(b"live_nav.js", editor.content)
        sell = self.client.post(
            f"/portfolio/histories/{hid}/decisions",
            data={
                "side": "sell",
                "listing": "META",
                "as_of": "2026-03-31",
                "quantity": "10",
            },
            follow_redirects=True,
        )
        self.assertEqual(sell.status_code, 200)
        self.assertIn(b"sell META", sell.content)
        api = self.client.get(f"/api/portfolio/histories/{hid}")
        self.assertEqual(api.status_code, 200)
        self.assertIsNotNone(api.json()["delta"])
