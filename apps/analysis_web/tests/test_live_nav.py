"""Live NAV marker + /api/portfolio/live-nav (FakeQuoteBackend; no network)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from apps.analysis_web.services.live_nav import (
    MarkLot,
    fetch_prints,
    lots_from_view,
    mark_live_nav,
)
from apps.analysis_web.services.quotes import (
    MAX_SYMBOLS,
    FakeQuoteBackend,
    QuotePrint,
    QuoteService,
)
from apps.analysis_web.tests.test_ib_statement import FIXTURE
from apps.analysis_web.tests.test_portfolio import _mini_archive
from apps.analysis_web.tests.test_quotes import _q


def _lot(
    symbol: str,
    *,
    listing: str | None = None,
    qty: float = 10,
    value: float = 4000,
    fx: float | None = 8.0,
) -> MarkLot:
    return MarkLot(
        ib_symbol=symbol,
        listing=listing if listing is not None else symbol,
        quantity=qty,
        stmt_value_base=value,
        stmt_fx=fx,
    )


def _quotes(*prints: QuotePrint) -> dict[str, QuotePrint]:
    return {q.symbol.upper(): q for q in prints}


class MarkLiveNavTests(unittest.TestCase):
    def test_meta_print_move_identity(self):
        lots = [
            _lot("700", listing="0700.HK", qty=100, value=1000, fx=1.0),
            _lot("META", qty=10, value=4000, fx=8.0),
        ]
        quotes = _quotes(
            _q("0700.HK", 10.0, prev=10.0),
            _q("META", 55.0, prev=50.0),
        )
        out = mark_live_nav(lots, quotes, ending_nav=5500.0, cash=500.0)
        self.assertAlmostEqual(out["live_nav"], 5900.0, places=5)
        self.assertAlmostEqual(out["delta"], 400.0, places=5)
        self.assertAlmostEqual(out["delta_pct"], (5900 / 5500 - 1) * 100, places=5)
        self.assertAlmostEqual(out["day_pl"], 10 * (55 - 50) * 8, places=5)
        self.assertEqual(out["vintage"], "live")
        self.assertEqual(out["fx_vintage"], "statement")
        self.assertEqual(out["n_positions"], 2)
        self.assertEqual(out["n_repriced"], 2)
        self.assertEqual(out["n_unquoted"], 0)
        self.assertAlmostEqual(out["cash_statement"], 500.0, places=5)
        by = {r["ib_symbol"]: r for r in out["rows"]}
        self.assertAlmostEqual(by["META"]["live_value_base"], 4400.0, places=5)
        self.assertAlmostEqual(by["700"]["live_value_base"], 1000.0, places=5)
        self.assertAlmostEqual(by["META"]["day_pl"], 10 * (55 - 50) * 8, places=5)
        self.assertAlmostEqual(by["700"]["day_pl"], 0.0, places=5)
        self.assertAlmostEqual(
            sum(r["day_pl"] or 0 for r in out["rows"]), out["day_pl"], places=5
        )
        qsyms = {q["symbol"] for q in out["quotes"]}
        self.assertEqual(qsyms, {"0700.HK", "META"})

    def test_row_day_pl_none_without_prev_close(self):
        lots = [_lot("META", qty=10, value=4000, fx=8.0)]
        q = QuotePrint(symbol="META", price=55.0, prev_close=None, change_pct=None)
        out = mark_live_nav(lots, _quotes(q), ending_nav=5500.0)
        self.assertIsNone(out["rows"][0]["day_pl"])
        self.assertIsNone(out["day_pl"])

    def test_missing_quote_keeps_statement(self):
        lots = [
            _lot("700", listing="0700.HK", qty=100, value=1000, fx=1.0),
            _lot("META", qty=10, value=4000, fx=8.0),
        ]
        quotes = _quotes(_q("META", 55.0, prev=50.0))
        out = mark_live_nav(lots, quotes, ending_nav=5500.0)
        self.assertAlmostEqual(out["live_nav"], 5900.0, places=5)
        self.assertEqual(out["vintage"], "partial")
        self.assertEqual(out["n_repriced"], 1)
        self.assertEqual(out["n_unquoted"], 1)
        by = {r["ib_symbol"]: r for r in out["rows"]}
        self.assertIsNone(by["700"]["live_value_base"])
        self.assertEqual(by["700"]["error"], "unavailable")

    def test_missing_fx_not_repriced(self):
        lots = [_lot("META", qty=10, value=4000, fx=None)]
        quotes = _quotes(_q("META", 55.0))
        out = mark_live_nav(lots, quotes, ending_nav=5500.0)
        self.assertAlmostEqual(out["live_nav"], 5500.0, places=5)
        self.assertEqual(out["vintage"], "statement")
        self.assertEqual(out["n_repriced"], 0)
        self.assertEqual(out["rows"][0]["error"], "missing_fx")

    def test_all_quotes_fail_keeps_statement(self):
        lots = [_lot("META"), _lot("700", listing="0700.HK", qty=100, value=1000, fx=1)]
        out = mark_live_nav(lots, {}, ending_nav=5500.0)
        self.assertAlmostEqual(out["live_nav"], 5500.0, places=5)
        self.assertEqual(out["vintage"], "statement")
        self.assertEqual(out["n_repriced"], 0)
        self.assertEqual(out["n_unquoted"], 2)

    def test_json_shares_sum_no_delta(self):
        lots = [
            MarkLot("META", "META", 2.0, None, 1.0),
            MarkLot("AAPL", "AAPL", 3.0, None, 1.0),
        ]
        quotes = _quotes(_q("META", 10.0), _q("AAPL", 20.0))
        out = mark_live_nav(lots, quotes, ending_nav=None)
        self.assertAlmostEqual(out["live_nav"], 2 * 10 + 3 * 20, places=5)
        self.assertIsNone(out["delta"])
        self.assertIsNone(out["delta_pct"])
        self.assertEqual(out["vintage"], "live")

    def test_empty_lots_no_live_nav(self):
        out = mark_live_nav([], {}, ending_nav=None)
        self.assertIsNone(out["live_nav"])
        self.assertIsNone(out["vintage"])
        self.assertEqual(out["n_positions"], 0)

    def test_empty_lots_with_ending_keeps_statement(self):
        out = mark_live_nav([], {}, ending_nav=5500.0)
        self.assertAlmostEqual(out["live_nav"], 5500.0, places=5)
        self.assertEqual(out["vintage"], "statement")

    def test_marker_takes_lots_only(self):
        lots = [_lot("META", qty=10, value=4000, fx=8.0)]
        quotes = _quotes(_q("META", 55.0, prev=50.0))
        out = mark_live_nav(lots, quotes, ending_nav=5500.0)
        self.assertNotIn("margin_of_safety_pct", out)
        self.assertNotIn("fv_base", out)
        self.assertEqual(out["rows"][0]["ib_symbol"], "META")


class LotsFromViewTests(unittest.TestCase):
    def test_weights_only_json_empty(self):
        view = {
            "ib": None,
            "positions": [{"ticker": "META", "shares": None, "print_listing": "META"}],
        }
        self.assertEqual(lots_from_view(view), [])

    def test_json_shares_become_lots(self):
        view = {
            "ib": None,
            "positions": [
                {
                    "ib_symbol": "META",
                    "shares": 2,
                    "print_listing": "META",
                    "stmt_fx": 1.0,
                }
            ],
        }
        lots = lots_from_view(view)
        self.assertEqual(len(lots), 1)
        self.assertEqual(lots[0].quantity, 2.0)
        self.assertEqual(lots[0].listing, "META")


class FetchPrintsChunkTests(unittest.TestCase):
    def test_chunks_over_cap(self):
        n = MAX_SYMBOLS + 1
        listings = [f"T{i}" for i in range(n)]
        quotes = {s: _q(s, 1.0) for s in listings}
        be = FakeQuoteBackend(quotes)
        rows = fetch_prints(be.quote_many, listings, chunk_size=MAX_SYMBOLS)
        self.assertEqual(len(rows), n)
        self.assertEqual(len(be.calls), 2)
        self.assertEqual(len(be.calls[0]), MAX_SYMBOLS)
        self.assertEqual(len(be.calls[1]), 1)


class LiveNavHttpTests(unittest.TestCase):
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
        be = FakeQuoteBackend(
            {
                "META": _q("META", 55.0, prev=50.0),
                "0700.HK": _q("0700.HK", 10.0, prev=10.0),
            }
        )
        self._app.state.quote_service = QuoteService(be, ttl_sec=120)
        self._backend = be
        from fastapi.testclient import TestClient

        self.client = TestClient(self._app)

    def tearDown(self):
        import apps.analysis_web.config as cfg

        cfg.local_dir = self._orig_local  # type: ignore[assignment]
        self.client.close()
        os.environ.pop("ARCHIVE_ROOT", None)
        self._td.cleanup()

    def test_api_live_nav_identity(self):
        r = self.client.get("/api/portfolio/live-nav")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertAlmostEqual(body["statement_nav"], 5500.0, places=5)
        self.assertAlmostEqual(body["live_nav"], 5900.0, places=5)
        self.assertAlmostEqual(body["delta"], 400.0, places=5)
        self.assertEqual(body["vintage"], "live")
        self.assertEqual(body["fx_vintage"], "statement")
        self.assertEqual(body["period_to"], "2026-03-31")
        self.assertEqual(body["ttl_sec"], 120)
        self.assertEqual(body["n_positions"], 2)
        self.assertEqual(body["n_repriced"], 2)
        qsyms = {q["symbol"] for q in body["quotes"]}
        self.assertEqual(qsyms, {"META", "0700.HK"})
        by = {row["ib_symbol"]: row for row in body["rows"]}
        self.assertAlmostEqual(by["META"]["live_value_base"], 4400.0, places=5)
        self.assertAlmostEqual(by["META"]["day_pl"], 10 * (55 - 50) * 8, places=5)
        self.assertEqual(by["700"]["listing"], "0700.HK")

    def test_page_hooks(self):
        r = self.client.get("/portfolio")
        self.assertEqual(r.status_code, 200)
        html = r.content
        self.assertIn(b'data-quote-poll="0"', html)
        self.assertIn(b'id="live-nav"', html)
        self.assertIn(b'id="quote-status"', html)
        self.assertNotIn(b'id="live-nav-delta"', html)
        self.assertIn(b'id="live-nav-day"', html)
        self.assertNotIn(b">Ending NAV<", html)
        self.assertNotIn(b">Period<", html)
        self.assertIn(b'data-quote-symbol="0700.HK"', html)
        self.assertIn(b'data-quote-symbol="META"', html)
        self.assertIn(b"data-live-value", html)
        self.assertIn(b"/static/live_nav.js", html)
        self.assertIn(b'id="heatmap"', html)
        self.assertIn(b"/static/heatmap.js", html)
        self.assertIn(b"Tile area is the |day change|", html)
        self.assertNotIn(b"quote_listing or yahoo_listing", html)

    def test_chunked_http_51_listings(self):
        n = MAX_SYMBOLS + 1
        quotes = {f"T{i}": _q(f"T{i}", 1.0) for i in range(n)}
        be = FakeQuoteBackend(quotes)
        svc = QuoteService(be, ttl_sec=120)
        from apps.analysis_web.services.live_nav import fetch_prints

        rows = fetch_prints(svc.get_many, list(quotes), chunk_size=MAX_SYMBOLS)
        self.assertEqual(len(rows), n)
        self.assertGreaterEqual(len(be.calls), 2)


class PrintListingJoinTests(unittest.TestCase):
    def test_uncovered_ib_uses_overlay(self):
        from packages.catalog_api.client import CatalogApi
        from apps.analysis_web.services.ib_statement import IbBook, parse_activity_csv
        from apps.analysis_web.services.portfolio import build_portfolio_view

        td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            archive = _mini_archive(Path(td.name))
            api = CatalogApi(archive_root=archive, readonly=True)
            stmt = parse_activity_csv(FIXTURE)
            view = build_portfolio_view(
                api, ib_book=IbBook(snapshot=stmt, trades=list(stmt.trades))
            )
            by = {p["ib_symbol"]: p for p in view["positions"]}
            self.assertEqual(by["700"]["print_listing"], "0700.HK")
            self.assertIsNone(by["700"]["quote_listing"])
            self.assertAlmostEqual(by["700"]["stmt_fx"], 1.0, places=5)
            self.assertEqual(by["META"]["print_listing"], "META")
            self.assertEqual(by["META"]["quote_listing"], "META")
            self.assertAlmostEqual(by["META"]["stmt_fx"], 8.0, places=5)
            del api
        finally:
            td.cleanup()

    def test_gds_print_listing_stays_on_the_holding(self):
        from apps.analysis_web.services.portfolio import (
            holding_print_listing,
            map_catalog_ticker,
        )

        self.assertEqual(holding_print_listing("HY9H", "BATS"), "HY9H")
        self.assertEqual(holding_print_listing("HY9H", "FWB"), "HY9H")
        self.assertEqual(map_catalog_ticker("HY9H", "FWB"), "000660.KS")
        self.assertEqual(holding_print_listing("MC", None), "MC.PA")
        self.assertEqual(holding_print_listing("700", "SEHK"), "0700.HK")


class QuotesJsOptOutTests(unittest.TestCase):
    def test_quotes_js_opt_out_and_event(self):
        qjs = (
            Path(__file__).resolve().parents[1] / "static" / "quotes.js"
        ).read_text(encoding="utf-8")
        self.assertIn('data-quote-poll', qjs)
        self.assertIn("pollOptedOut", qjs)
        self.assertIn("quotes-applied", qjs)
        self.assertIn('slice(0, MAX_SYMBOLS)', qjs)

    def test_live_nav_js_does_not_hit_quotes_api(self):
        navjs = (
            Path(__file__).resolve().parents[1] / "static" / "live_nav.js"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/portfolio/live-nav", navjs)
        self.assertIn("quotes-applied", navjs)
        self.assertIn("live-nav-applied", navjs)
        self.assertNotIn('fetch("/api/quotes"', navjs)
        self.assertIn("Does not call /api/quotes", navjs)

    def test_heatmap_js_is_a_projection(self):
        hjs = (
            Path(__file__).resolve().parents[1] / "static" / "heatmap.js"
        ).read_text(encoding="utf-8")
        self.assertIn("live-nav-applied", hjs)
        self.assertIn("day_pl > 0", hjs)
        self.assertIn("Gainers", hjs)
        self.assertIn("losers", hjs)
        self.assertIn("max-width: 1100px", hjs)
        self.assertNotIn("fetch(", hjs)

    def test_runs_page_still_polls(self):
        runs = (
            Path(__file__).resolve().parents[1] / "templates" / "runs.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn('data-quote-poll="0"', runs)


if __name__ == "__main__":
    unittest.main()
