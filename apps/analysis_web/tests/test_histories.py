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
        self._backend = FakeHistoryBackend(_bars())
        self._app.state.history_service = HistoryService(
            self._backend, ttl_sec=60
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
        self._backend.calls.clear()
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
        self.assertIn(b'<label>Qty', r.content)
        self.assertNotIn(b'sr-only', r.content)
        self.assertEqual(self._backend.calls, [])

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

        api = self.client.get(f"/api/portfolio/histories/{hid}/path")
        self.assertEqual(api.status_code, 200)
        body = api.json()
        self.assertIsNotNone(body["delta"])
        self.assertGreaterEqual(len(body["path"]), 2)
        last = body["path"][-1]
        self.assertAlmostEqual(body["delta"], last["delta"], places=5)
        self.assertAlmostEqual(body["alt_nav"], last["alt_nav"], places=5)
        self.assertAlmostEqual(body["actual_nav"], last["actual_nav"], places=5)
        self.assertNotIn("held", body)

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
        api = self.client.get(f"/api/portfolio/histories/{hid}/path")
        self.assertEqual(api.status_code, 200)
        self.assertIsNotNone(api.json()["delta"])

    def test_views_are_split_and_date_skips_path(self):
        created = self.client.post(
            "/portfolio/histories/new",
            data={"name": "Split"},
            follow_redirects=False,
        )
        hid = created.headers["location"].rsplit("/", 1)[-1].split("?")[0]
        self._backend.calls.clear()
        html = self.client.get(f"/portfolio/histories/{hid}?date=2026-03-31")
        self.assertEqual(html.status_code, 200)
        self.assertIn(b"Holdings on this day", html.content)
        self.assertEqual(self._backend.calls, [])

        held = self.client.get(
            f"/api/portfolio/histories/{hid}/holdings?date=2026-03-31"
        )
        self.assertEqual(held.status_code, 200)
        body = held.json()
        self.assertIn("held", body)
        self.assertNotIn("path", body)
        self.assertEqual(body["view_date"], "2026-03-31")
        self.assertTrue(any(row["listing"] == "META" for row in body["held"]))
        ranges = {key for _sym, key in self._backend.calls}
        self.assertNotIn("max", ranges)

        doc = self.client.get(f"/api/portfolio/histories/{hid}")
        self.assertEqual(doc.status_code, 200)
        one_body = doc.json()
        self.assertEqual(one_body["name"], "Split")
        self.assertIn("decisions", one_body)
        self.assertIn("fork_date", one_body)
        self.assertNotIn("held", one_body)
        self.assertNotIn("path", one_body)
        self.assertNotIn("delta", one_body)
        self.assertNotIn("view_date", one_body)

        path = self.client.get(f"/api/portfolio/histories/{hid}/path")
        self.assertEqual(path.status_code, 200)
        pbody = path.json()
        self.assertIn("path", pbody)
        self.assertNotIn("held", pbody)
        self.assertIsNotNone(pbody["delta"])
        svg = self.client.get(f"/api/portfolio/histories/{hid}/path.svg")
        self.assertEqual(svg.status_code, 200)
        self.assertIn("image/svg+xml", svg.headers.get("content-type", ""))

    def test_partial_sell_leaves_remainder(self):
        created = self.client.post(
            "/portfolio/histories/new",
            data={"name": "Partial"},
            follow_redirects=False,
        )
        hid = created.headers["location"].rsplit("/", 1)[-1].split("?")[0]
        before = self.client.get(
            f"/api/portfolio/histories/{hid}/holdings?date=2026-03-31"
        ).json()
        meta = next(row for row in before["held"] if row["listing"] == "META")
        self.assertGreater(meta["qty"], 1)
        sell = self.client.post(
            f"/portfolio/histories/{hid}/decisions",
            data={
                "side": "sell",
                "listing": "META",
                "as_of": "2026-03-31",
                "quantity": "1",
            },
            follow_redirects=True,
        )
        self.assertEqual(sell.status_code, 200)
        self.assertIn(b"sell META", sell.content)
        after = self.client.get(
            f"/api/portfolio/histories/{hid}/holdings?date=2026-03-31"
        ).json()
        meta_after = next(row for row in after["held"] if row["listing"] == "META")
        self.assertAlmostEqual(meta_after["qty"], meta["qty"] - 1, places=5)

    def test_holdings_cash_is_as_of_view_date(self):
        created = self.client.post(
            "/portfolio/histories/new",
            data={"name": "Cash D"},
            follow_redirects=False,
        )
        hid = created.headers["location"].rsplit("/", 1)[-1].split("?")[0]
        from apps.analysis_web.services.alt_history import state_on
        from apps.analysis_web.services.alt_history_store import get_history

        hist = get_history(int(hid))
        fork_held = self.client.get(
            f"/api/portfolio/histories/{hid}/holdings?date={hist.fork_date}"
        ).json()
        late_held = self.client.get(
            f"/api/portfolio/histories/{hid}/holdings?date=2026-03-31"
        ).json()
        self.assertAlmostEqual(
            fork_held["cash"], state_on(hist, hist.fork_date).cash_base or 0, places=5
        )
        self.assertAlmostEqual(
            late_held["cash"], state_on(hist, "2026-03-31").cash_base or 0, places=5
        )
        self.assertNotAlmostEqual(fork_held["cash"], late_held["cash"], places=5)
        html = self.client.get(f"/portfolio/histories/{hid}?date=2026-03-31")
        self.assertIn(b"Cash (today)", html.content)
        self.assertIn(b"Cash on 2026-03-31", html.content)
        self.assertNotIn(b'"path"', html.content)
        self.assertNotIn(b"live_nav.js", html.content)
        late_row = late_held["held"][0]
        self.assertNotIn("deceased", late_row)

    def test_paper_view_has_no_path_fields(self):
        created = self.client.post(
            "/portfolio/histories/new",
            data={"name": "Types"},
            follow_redirects=False,
        )
        hid = created.headers["location"].rsplit("/", 1)[-1].split("?")[0]
        from apps.analysis_web.services.alt_history_store import get_history
        from apps.analysis_web.services.alt_history_view import (
            EditorPage,
            HoldingsLot,
            PaperLot,
            PaperView,
            editor_page,
            holdings_on,
            paper_on,
        )

        hist = get_history(int(hid))
        paper = paper_on(hist, view_date="2026-03-31")
        self.assertIsInstance(paper, PaperView)
        self.assertFalse(hasattr(paper, "path"))
        self.assertFalse(hasattr(paper, "delta"))
        self.assertFalse(hasattr(paper, "svg"))
        self.assertFalse(hasattr(paper, "actual_nav"))
        self.assertFalse(hasattr(paper, "universe"))
        self.assertFalse(hasattr(paper, "decisions"))
        self.assertFalse(hasattr(paper, "error"))
        self.assertFalse(hasattr(paper, "until"))
        self.assertFalse(hasattr(paper, "history"))
        self.assertTrue(paper.held)
        self.assertIsInstance(paper.held[0], PaperLot)
        self.assertFalse(hasattr(paper.held[0], "close"))
        self.assertFalse(hasattr(paper.held[0], "value_base"))
        self.assertFalse(hasattr(paper.held[0], "deceased"))

        page = editor_page(hist, view_date="2026-03-31")
        self.assertIsInstance(page, EditorPage)
        self.assertNotIsInstance(page, dict)
        self.assertIsInstance(page.paper, PaperView)
        self.assertEqual(page.history.id, hist.id)
        self.assertFalse(hasattr(page, "held"))
        self.assertFalse(hasattr(page, "until"))
        self.assertIsInstance(page.sold_later, frozenset)

        captured: list[tuple[str, str]] = []

        def fake_load(svc, listings, *, start, end):
            captured.append((start, end))
            return {}

        from unittest.mock import patch

        with patch(
            "apps.analysis_web.services.alt_history_view.load_bars", fake_load
        ):
            held = holdings_on(
                hist, self._app.state.history_service, view_date="2026-03-31"
            )
        self.assertEqual(captured[0][1], "2026-03-31")
        self.assertTrue(held.held)
        self.assertIsInstance(held.held[0], HoldingsLot)
        self.assertTrue(hasattr(held.held[0], "close"))
        self.assertNotIn("deceased", held.held[0].as_json())
        self.assertEqual(held.view_date, "2026-03-31")

        frag = self.client.get(
            f"/fragments/portfolio/histories/{hid}/held?date=2026-03-31"
        )
        self.assertEqual(frag.status_code, 200)
        self.assertIn(b'name="quantity"', frag.content)
        self.assertIn(b"data-view-date", frag.content)
        self.assertIn(b"META", frag.content)
        self.assertIn(b"Cash on 2026-03-31", frag.content)
        self.assertNotIn(b"Cash (today)", frag.content)
        html = self.client.get(f"/portfolio/histories/{hid}")
        self.assertIn(b"data-held-url", html.content)
        self.assertNotIn(b"data-holdings-url", html.content)
        js = Path("apps/analysis_web/static/alt_history.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("renderHeld", js)
        self.assertNotIn("<table>", js)

    def test_sold_later_is_page_badge_not_holdings_json(self):
        from dataclasses import replace

        from apps.analysis_web.services.alt_history import PricedFill
        from apps.analysis_web.services.alt_history_store import get_history, save

        created = self.client.post(
            "/portfolio/histories/new",
            data={"name": "Sold later"},
            follow_redirects=False,
        )
        hid = created.headers["location"].rsplit("/", 1)[-1].split("?")[0]
        hist = get_history(int(hid))
        save(
            replace(
                hist,
                fills=hist.fills
                + (
                    PricedFill(
                        as_of="2026-04-10",
                        side="sell",
                        listing="META",
                        quantity=10,
                        fill_price=50,
                        currency="USD",
                        stmt_fx=8.0,
                        ib_symbol="META",
                        source="real",
                    ),
                ),
            )
        )
        html = self.client.get(f"/portfolio/histories/{hid}?date=2026-03-31")
        self.assertEqual(html.status_code, 200)
        self.assertIn(b"sold later", html.content)
        self.assertIn(b"META", html.content)
        frag = self.client.get(
            f"/fragments/portfolio/histories/{hid}/held?date=2026-03-31"
        )
        self.assertEqual(frag.status_code, 200)
        self.assertIn(b"sold later", frag.content)
        held = self.client.get(
            f"/api/portfolio/histories/{hid}/holdings?date=2026-03-31"
        ).json()
        meta = next(row for row in held["held"] if row["listing"] == "META")
        self.assertNotIn("deceased", meta)
