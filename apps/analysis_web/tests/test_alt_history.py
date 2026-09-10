"""Replay, POST policy, overlay store. Does not write the IB book."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from packages.catalog_api.client import CatalogApi

from datetime import date, timedelta

from apps.analysis_web.services.alt_history import (
    CatalogSnap,
    PricedFill,
    ReplayError,
    catalog_snaps,
    compare_at,
    compare_path,
    drop_hyp_fill,
    missing_fx_message,
    walk_compare,
    trial_replay,
    history_from_ib,
    overlay_fills,
    path_dates,
    persist_ticket,
    prices_on,
    replay,
    state_on,
    ticket_block,
    with_hyp_fill,
)
from apps.analysis_web.services.alt_history_view import build_ticket
from apps.analysis_web.services.mark_book import AsOfMark, MarkedLot
from apps.analysis_web.services.paper_account import PaperAccount
from apps.analysis_web.services.alt_history_store import (
    copy_history,
    create_from_ib,
    create_history,
    db_path,
    delete_history,
    get_history,
    list_histories,
    save,
)
from apps.analysis_web.services.book_state import BookState, as_of_book

from apps.analysis_web.services.ib_statement import IbBook, parse_activity_csv
from apps.analysis_web.services.price_history import PriceBar
from apps.analysis_web.tests.test_book_state import FIXTURE
from apps.analysis_web.tests.test_portfolio import _mini_archive


def _ib() -> IbBook:
    stmt = parse_activity_csv(FIXTURE)
    return IbBook(snapshot=stmt, trades=list(stmt.trades))


def _fill(
    *,
    as_of: str = "2026-03-31",
    side: str = "sell",
    listing: str = "META",
    quantity: float = 10,
    fill_price: float = 50,
    currency: str = "USD",
    stmt_fx: float = 8.0,
    catalog_ticker: str | None = None,
    ib_symbol: str | None = "META",
    price_mode: str = "close",
    id: int | None = 1,
    source: str = "hyp",
) -> PricedFill:
    return PricedFill(
        as_of=as_of,
        side=side,
        listing=listing,
        quantity=quantity,
        fill_price=fill_price,
        currency=currency,
        stmt_fx=stmt_fx,
        catalog_ticker=catalog_ticker,
        ib_symbol=ib_symbol,
        price_mode=price_mode,
        id=id,
        source=source,
    )


def _closes() -> dict[str, tuple[PriceBar, ...]]:
    return {
        "META": (
            PriceBar("2026-03-31", 50.0),
            PriceBar("2026-04-01", 55.0),
        ),
        "0700.HK": (
            PriceBar("2026-03-31", 10.0),
            PriceBar("2026-04-01", 10.0),
        ),
        "AAPL": (
            PriceBar("2026-03-31", 200.0),
            PriceBar("2026-04-01", 210.0),
        ),
    }


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.ib = _ib()
        self.fork = as_of_book(self.ib, "2026-03-31")

    def test_sell_meta_frees_cash(self):
        out = replay(self.fork, [_fill()])
        self.assertIsNone(out.lot_by_listing("META"))
        self.assertAlmostEqual(out.lot_by_listing("0700.HK").qty, 100.0, places=5)  # type: ignore[union-attr]
        self.assertAlmostEqual((out.cash_base or 0) - 500.0, 10 * 50 * 8, places=5)

    def test_oversell_rejected(self):
        with self.assertRaises(ReplayError) as ctx:
            replay(self.fork, [_fill(quantity=11)])
        self.assertEqual(ctx.exception.code, "oversell")

    def test_buy_may_run_cash_negative(self):
        buy = _fill(
            side="buy",
            listing="AAPL",
            quantity=1,
            fill_price=200,
            currency="USD",
            catalog_ticker="AAPL",
            ib_symbol=None,
            id=2,
        )
        # 1 * 200 * 8 = 1600; cash 500 → loan 1100
        out = replay(self.fork, [buy])
        self.assertAlmostEqual(out.cash_base or 0, 500.0 - 1600.0, places=5)
        self.assertAlmostEqual(out.lot_by_listing("AAPL").qty, 1.0, places=5)  # type: ignore[union-attr]
        self.assertEqual(out.lot_by_listing("AAPL").catalog_ticker, "AAPL")
        sold = replay(self.fork, [_fill()])
        funded = replay(sold, [buy])
        self.assertAlmostEqual(funded.lot_by_listing("AAPL").qty, 1.0, places=5)  # type: ignore[union-attr]

    def test_unwind_hypothetical_buy(self):
        sold = replay(self.fork, [_fill()])
        bought = replay(
            sold,
            [
                _fill(
                    side="buy",
                    listing="AAPL",
                    quantity=1,
                    fill_price=200,
                    catalog_ticker="AAPL",
                    ib_symbol=None,
                    id=2,
                )
            ],
        )
        flat = replay(
            bought,
            [
                _fill(
                    side="sell",
                    listing="AAPL",
                    quantity=1,
                    fill_price=200,
                    catalog_ticker="AAPL",
                    ib_symbol=None,
                    id=3,
                )
            ],
        )
        self.assertIsNone(flat.lot_by_listing("AAPL"))

    def test_before_fork_rejected(self):
        with self.assertRaises(ReplayError) as ctx:
            replay(self.fork, [_fill(as_of="2026-01-01")])
        self.assertEqual(ctx.exception.code, "before_fork")

    def test_zero_qty_rejected(self):
        with self.assertRaises(ReplayError) as ctx:
            replay(self.fork, [_fill(quantity=0)])
        self.assertEqual(ctx.exception.code, "zero_qty")

    def test_replay_does_not_need_catalog(self):
        # Unknown listing is fine once priced; catalog is POST-only.
        sold = replay(self.fork, [_fill()])
        out = replay(
            sold,
            [
                _fill(
                    side="buy",
                    listing="ZZZZ",
                    quantity=1,
                    fill_price=10,
                    currency="HKD",
                    stmt_fx=1.0,
                    catalog_ticker="ZZZZ",
                    ib_symbol=None,
                    id=2,
                )
            ],
        )
        self.assertAlmostEqual(out.lot_by_listing("ZZZZ").qty, 1.0, places=5)  # type: ignore[union-attr]


def _rich_account() -> PaperAccount:
    return PaperAccount(
        as_of="2026-03-31",
        cash=1_000_000.0,
        stock=0.0,
        nav=1_000_000.0,
        loan=0.0,
        maintenance=0.0,
        excess=1_000_000.0,
        buying_power=2_000_000.0,
        n_unquoted=0,
        n_unavailable=0,
        base_currency="HKD",
    )


def _mark(listing: str, close: float | None, *, status: str | None = None) -> AsOfMark:
    if status is None:
        status = "quoted" if close is not None else "unquoted"
    return AsOfMark(listing=listing, as_of="2026-03-31", status=status, close=close)


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.archive = _mini_archive(Path(self._td.name))
        self.api = CatalogApi(archive_root=self.archive, readonly=True)
        self.ib = _ib()
        self.hist = history_from_ib(self.ib, name="copy")
        self.snaps = catalog_snaps(self.api)

    def tearDown(self):
        del self.api
        self._td.cleanup()

    def _buy(self, ticker: str, *, hist=None, close=200.0, quantity=1.0, **kwargs):
        listing = ticker
        return persist_ticket(
            build_ticket(
                hist or self.hist,
                account=_rich_account(),
                held=(),
                side="buy",
                view_date="2026-03-31",
                mark=_mark(listing, close),
                snaps=self.snaps,
                listing=listing,
                ticker=ticker,
                quantity=quantity,
                **kwargs,
            )
        )

    def test_buy_unknown_ticker_rejected(self):
        with self.assertRaises(ReplayError) as ctx:
            self._buy("ZZZZ")
        self.assertEqual(ctx.exception.code, "not_in_catalog")

    def test_buy_resolves_listing_and_close(self):
        fill = self._buy("AAPL")
        self.assertEqual(fill.listing, "AAPL")
        self.assertEqual(fill.catalog_ticker, "AAPL")
        self.assertEqual(fill.price_mode, "close")
        self.assertAlmostEqual(fill.fill_price, 200.0, places=5)
        self.assertEqual(fill.currency, "USD")

    def test_override_fill(self):
        fill = self._buy("AAPL", override_price=180.0)
        self.assertEqual(fill.price_mode, "override")
        self.assertAlmostEqual(fill.fill_price, 180.0, places=5)

    def test_no_close_rejected(self):
        with self.assertRaises(ReplayError) as ctx:
            self._buy("AAPL", close=None)
        self.assertEqual(ctx.exception.code, "no_close")
        block = ticket_block(
            self.hist,
            side="buy",
            mark_status="unquoted",
            close=None,
            currency="USD",
            fx=self.hist.seed.fx_for("USD"),
            listing="AAPL",
            view_date="2026-03-31",
        )
        self.assertIsNotNone(block)
        assert block is not None
        self.assertEqual(ctx.exception.message, block.message)

    def test_sell_from_alt_state(self):
        lot = MarkedLot(
            listing="META",
            qty=10.0,
            close=50.0,
            value_base=4000.0,
            error=None,
            ib_symbol="META",
            currency="USD",
            stmt_fx=8.0,
        )
        fill = persist_ticket(
            build_ticket(
                self.hist,
                account=_rich_account(),
                held=(lot,),
                side="sell",
                view_date="2026-03-31",
                mark=_mark("META", 50.0),
                snaps=self.snaps,
                listing="META",
                ticker="META",
                quantity=2,
            )
        )
        self.assertEqual(fill.side, "sell")
        self.assertEqual(fill.ib_symbol, "META")
        self.assertAlmostEqual(fill.fill_price, 50.0, places=5)

    def test_ticket_buy_ignores_live_fx_after_copy(self):
        fill = self._buy("AAPL")
        self.assertAlmostEqual(
            fill.stmt_fx or 0,
            self.hist.seed.fx_for(fill.currency) or 0,
            places=5,
        )
        for ccy, _rate in self.hist.seed.fx_by_ccy:
            self.ib.snapshot.forex_closes[ccy] = 99.0
        again = self._buy("AAPL")
        self.assertAlmostEqual(again.stmt_fx or 0, fill.stmt_fx or 0, places=5)

    def test_catalog_snaps_latest(self):
        snaps = catalog_snaps(self.api)
        self.assertEqual({s.ticker for s in snaps}, {"META", "AAPL", "ORCL"})
        meta = next(s for s in snaps if s.ticker == "META")
        self.assertAlmostEqual(meta.fv_bear or 0, 350.0, places=5)
        self.assertEqual(meta.listing, "META")
        self.assertNotIn("quote_listing", meta.as_json())
        self.assertEqual(meta.currency, "USD")

    def test_missing_fx_message_names_currency(self):
        msg = missing_fx_message("USD", "HKD")
        self.assertIn("USD", msg)
        self.assertIn("HKD", msg)
        self.assertIn("frozen at copy", msg)
        self.assertNotIn("No statement FX", msg)
        block = ticket_block(
            self.hist,
            side="buy",
            mark_status="quoted",
            close=10.0,
            currency="EUR",
            fx=None,
        )
        self.assertIsNotNone(block)
        assert block is not None
        self.assertEqual(block.code, "missing_fx")
        self.assertIn("EUR", block.message)

    def test_ticket_buy_missing_fx_when_no_frozen_rate(self):
        from dataclasses import replace

        lots = tuple(
            lot
            for lot in self.hist.seed.lots
            if (lot.currency or "").strip().upper() != "USD"
        )
        hist = replace(self.hist, seed=replace(self.hist.seed, fx_by_ccy=(), lots=lots))
        self.assertIsNone(hist.seed.fx_for("USD"))
        with self.assertRaises(ReplayError) as ctx:
            self._buy("AAPL", hist=hist)
        self.assertEqual(ctx.exception.code, "missing_fx")
        self.assertIn("USD", ctx.exception.message)
        self.assertIn("frozen at copy", ctx.exception.message)
        self.assertNotIn("No statement FX", ctx.exception.message)

    def test_ticket_buy_uses_lot_fx_when_map_empty(self):
        from dataclasses import replace

        from apps.analysis_web.services.book_state import Lot

        usd_lot = Lot(
            listing="VSNT",
            currency="USD",
            qty=1.0,
            stmt_fx=7.8397,
            ib_symbol="VSNT",
        )
        hist = replace(
            self.hist,
            seed=replace(self.hist.seed, fx_by_ccy=(), lots=self.hist.seed.lots + (usd_lot,)),
        )
        usd = hist.seed.fx_for("USD")
        self.assertIsNotNone(usd)
        fill = self._buy("AAPL", hist=hist)
        self.assertEqual(fill.currency, "USD")
        self.assertAlmostEqual(fill.stmt_fx or 0, usd or 0, places=5)

    def test_empty_snap_currency_is_a_block(self):
        snaps = (
            CatalogSnap(ticker="AAPL", listing="AAPL", currency=""),
        )
        ticket = build_ticket(
            self.hist,
            account=_rich_account(),
            held=(),
            side="buy",
            view_date="2026-03-31",
            mark=_mark("AAPL", 200.0),
            snaps=snaps,
            listing="AAPL",
            ticker="AAPL",
            quantity=1,
        )
        self.assertIsNotNone(ticket.block)
        assert ticket.block is not None
        self.assertEqual(ticket.block.code, "missing_currency")
        with self.assertRaises(ReplayError) as ctx:
            persist_ticket(ticket)
        self.assertEqual(ctx.exception.code, "missing_currency")
        self.assertEqual(ctx.exception.message, ticket.block.message)


class CopyLedgerTests(unittest.TestCase):
    def setUp(self):
        self.ib = _ib()

    def test_empty_whatif_lots_match_as_of(self):
        hist = history_from_ib(self.ib, name="copy")
        alt = state_on(hist, "2026-03-31")
        actual = as_of_book(self.ib, "2026-03-31")
        self.assertAlmostEqual(alt.lot_by_listing("META").qty, 10.0, places=5)  # type: ignore[union-attr]
        self.assertAlmostEqual(actual.lot_by_listing("META").qty, 10.0, places=5)  # type: ignore[union-attr]
        self.assertAlmostEqual(alt.lot_by_listing("0700.HK").qty, 100.0, places=5)  # type: ignore[union-attr]
        self.assertAlmostEqual(alt.cash_base or 0, actual.cash_base or 0, places=5)

    def test_past_date_shows_later_sold_lot(self):
        hist = history_from_ib(self.ib, name="copy")
        held = state_on(hist, "2026-02-01")
        self.assertAlmostEqual(held.lot_by_listing("META").qty, 12.0, places=5)  # type: ignore[union-attr]
        end = as_of_book(self.ib, "2026-03-31")
        self.assertAlmostEqual(end.lot_by_listing("META").qty, 10.0, places=5)  # type: ignore[union-attr]

    def test_hyp_sell_clips_later_real_sell(self):
        hist = history_from_ib(self.ib, name="copy")
        extra = PricedFill(
            as_of="2026-04-10",
            side="sell",
            listing="META",
            quantity=10,
            fill_price=50,
            currency="USD",
            stmt_fx=8.0,
            source="real",
            ib_symbol="META",
            price_mode="ib",
        )
        from dataclasses import replace

        hist = replace(hist, fills=hist.fills + (extra,))
        sold = with_hyp_fill(hist, _fill())
        later = state_on(sold, "2026-04-10")
        self.assertIsNone(later.lot_by_listing("META"))

    def test_overlay_clips_strict_replay_does_not(self):
        hist = history_from_ib(self.ib, name="copy")
        extra = PricedFill(
            as_of="2026-04-10",
            side="sell",
            listing="META",
            quantity=10,
            fill_price=50,
            currency="USD",
            stmt_fx=8.0,
            source="real",
            ib_symbol="META",
            price_mode="ib",
        )
        from dataclasses import replace

        raw = hist.fills + (replace(_fill(), source="hyp"), extra)
        with self.assertRaises(ReplayError) as ctx:
            replay(hist.seed, raw)
        self.assertEqual(ctx.exception.code, "oversell")
        later = replay(hist.seed, overlay_fills(hist.seed, raw))
        self.assertIsNone(later.lot_by_listing("META"))

    def test_compare_uses_frozen_seed_not_live_ib(self):
        hist = history_from_ib(self.ib, name="copy")
        from dataclasses import replace

        empty = BookState(
            lots=(),
            cash_base=0.0,
            as_of=hist.seed.as_of,
            caveats=(),
            base_currency=hist.seed.base_currency,
        )
        mutated = replace(hist, seed=empty, fills=())
        row = compare_at(mutated, "2026-03-31", {"META": 50.0, "0700.HK": 10.0})
        self.assertAlmostEqual(row["actual_nav"], 0.0, places=5)
        live = as_of_book(self.ib, "2026-03-31")
        self.assertGreater(len(live.lots), 0)

    def test_drop_hyp_sell_leaves_buy_on_loan(self):
        hist = history_from_ib(self.ib, name="copy")
        sold = with_hyp_fill(hist, _fill())
        bought = with_hyp_fill(
            sold,
            _fill(
                side="buy",
                listing="AAPL",
                quantity=1,
                fill_price=200,
                catalog_ticker="AAPL",
                ib_symbol=None,
                id=2,
            ),
        )
        td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            persist = create_history(
                name="x",
                fork_date=bought.fork_date,
                seed=bought.seed,
                fills=bought.fills,
                path=Path(td.name) / "alt.sqlite",
            )
            hyp = persist.hyp_fills()
            sell_id = next(f.id for f in hyp if f.side == "sell")
            out = drop_hyp_fill(persist, int(sell_id))
            self.assertTrue(any(f.side == "buy" for f in out.hyp_fills()))
            self.assertFalse(
                any(f.side == "sell" and f.listing == "META" for f in out.hyp_fills())
            )
            book = trial_replay(out)
            self.assertLess(book.cash_base or 0, 0.0)
        finally:
            td.cleanup()


def _naive_path(hist, bars, until):
    points = []
    for day in path_dates(bars, hist.fork_date, until):
        row = compare_at(hist, day, prices_on(bars, day))
        points.append(
            {
                "t": day,
                "actual_nav": row["actual_nav"],
                "alt_nav": row["alt_nav"],
                "delta": row["delta"],
            }
        )
    return points


def _daily_bars(start: str, end: str, px: float) -> tuple[PriceBar, ...]:
    d = date.fromisoformat(start)
    last = date.fromisoformat(end)
    out: list[PriceBar] = []
    while d <= last:
        if d.weekday() < 5:
            out.append(PriceBar(d.isoformat(), px))
        d += timedelta(days=1)
    return tuple(out)


class ComparePathTests(unittest.TestCase):
    def setUp(self):
        self.ib = _ib()
        self.bars = _closes()

    def test_delta_today_equals_last_path_point(self):
        hist = with_hyp_fill(history_from_ib(self.ib, name="t"), _fill())
        path = compare_path(hist, self.bars, until="2026-04-01")
        self.assertGreaterEqual(len(path), 2)
        last = path[-1]
        today = compare_at(
            hist,
            "2026-04-01",
            {"META": 55.0, "0700.HK": 10.0, "AAPL": 210.0},
        )
        self.assertAlmostEqual(last["delta"], today["delta"], places=5)
        self.assertAlmostEqual(last["alt_nav"], today["alt_nav"], places=5)
        self.assertAlmostEqual(last["actual_nav"], today["actual_nav"], places=5)
        self.assertNotAlmostEqual(today["alt_nav"], today["actual_nav"], places=5)

    def test_walk_matches_per_day_restart_and_prefix_overlay(self):
        hist = with_hyp_fill(history_from_ib(self.ib, name="t"), _fill())
        bars = {
            "META": _daily_bars("2026-01-10", "2026-04-01", 50.0),
            "0700.HK": _daily_bars("2026-01-10", "2026-04-01", 10.0),
            "AAPL": _daily_bars("2026-01-10", "2026-04-01", 200.0),
        }
        until = "2026-04-01"
        walked = compare_path(hist, bars, until=until)
        naive = _naive_path(hist, bars, until)
        self.assertEqual(len(walked), len(naive))
        self.assertGreater(len(walked), 20)
        for got, want in zip(walked, naive):
            self.assertEqual(got["t"], want["t"])
            self.assertAlmostEqual(got["actual_nav"], want["actual_nav"], places=5)
            self.assertAlmostEqual(got["alt_nav"], want["alt_nav"], places=5)
            self.assertAlmostEqual(got["delta"], want["delta"], places=5)
        for day in (hist.fork_date, "2026-03-31", until):
            point = next(p for p in walked if p["t"] == day)
            row = compare_at(hist, day, prices_on(bars, day))
            self.assertAlmostEqual(point["alt_nav"], row["alt_nav"], places=5)
            self.assertAlmostEqual(point["actual_nav"], row["actual_nav"], places=5)

    def test_path_starts_at_fork_and_has_no_since(self):
        import inspect

        hist = history_from_ib(self.ib, name="t")
        path = compare_path(hist, self.bars, until="2026-04-01")
        self.assertEqual(path[0]["t"], hist.fork_date)
        self.assertNotIn("since", inspect.signature(compare_path).parameters)

    def test_walk_last_marks_match_compare_at(self):
        from apps.analysis_web.services.mark_book import nav_delta_rows

        hist = with_hyp_fill(history_from_ib(self.ib, name="t"), _fill())
        walked = walk_compare(hist, self.bars, until="2026-04-01")
        self.assertEqual(list(walked.points), compare_path(hist, self.bars, until="2026-04-01"))
        self.assertIsNotNone(walked.actual)
        self.assertIsNotNone(walked.alt)
        today = compare_at(
            hist,
            "2026-04-01",
            {"META": 55.0, "0700.HK": 10.0, "AAPL": 210.0},
        )
        self.assertAlmostEqual(walked.alt.nav, today["alt_nav"], places=5)
        self.assertAlmostEqual(walked.actual.nav, today["actual_nav"], places=5)
        rows = nav_delta_rows(walked.actual, walked.alt)
        self.assertAlmostEqual(
            sum(pl for _, pl in rows), walked.alt.nav - walked.actual.nav, places=5
        )

    def test_overlay_joins_walks_on_date(self):
        from apps.analysis_web.services.alt_history_view import overlay_svg_from_cards

        cards = [
            {
                "name": "early",
                "path": [
                    {"t": "2026-01-01", "actual_nav": 10.0, "alt_nav": 10.0},
                    {"t": "2026-01-02", "actual_nav": 11.0, "alt_nav": 12.0},
                ],
            },
            {
                "name": "late",
                "path": [
                    {"t": "2026-01-02", "actual_nav": 11.0, "alt_nav": 9.0},
                ],
            },
        ]
        svg = overlay_svg_from_cards(cards, "2026-01-01", "2026-01-02")
        self.assertIn("nav-chart-svg", svg)
        self.assertIn("early", svg)
        self.assertIn("late", svg)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.local = Path(self._td.name) / "local"
        self.local.mkdir()
        import apps.analysis_web.config as cfg
        from apps.analysis_web.services.ib_statement import parse_activity_csv
        from apps.analysis_web.services.portfolio_store import ingest_statement

        self._orig = cfg.local_dir
        cfg.local_dir = lambda: self.local  # type: ignore[assignment]
        ingest_statement(
            parse_activity_csv(FIXTURE), path=self.local / "portfolio.sqlite"
        )
        self.ib_sqlite = self.local / "portfolio.sqlite"
        self.ib_mtime = self.ib_sqlite.stat().st_mtime
        self.ib_trades = self._trade_count()

    def tearDown(self):
        import apps.analysis_web.config as cfg

        cfg.local_dir = self._orig  # type: ignore[assignment]
        self._td.cleanup()

    def _trade_count(self) -> int:
        import sqlite3

        conn = sqlite3.connect(str(self.ib_sqlite))
        n = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        conn.close()
        return int(n)

    def test_crud_copy_and_no_ib_writes(self):
        from apps.analysis_web.services.ib_statement import parse_activity_csv
        from apps.analysis_web.services.portfolio_store import load as load_sql

        ib = load_sql(path=self.ib_sqlite)
        assert ib is not None
        hist = create_from_ib(ib, name="Missed AAPL")
        self.assertTrue(hist.fork_date)
        self.assertGreater(len(hist.real_fills()), 0)
        self.assertEqual(hist.seed.as_of, "2025-12-31")
        snapped = state_on(hist, "2026-03-31")
        self.assertEqual(snapped.as_of, "2026-03-31")
        self.assertNotEqual(snapped.as_of, hist.seed.as_of)
        from dataclasses import replace as _replace

        from apps.analysis_web.services.alt_history_view import (
            editor_page,
            sold_later_listings,
        )

        later = save(
            _replace(
                hist,
                fills=hist.fills
                + (
                    _fill(
                        as_of="2026-04-10",
                        side="sell",
                        listing="META",
                        quantity=10,
                        source="real",
                        id=9001,
                    ),
                ),
            )
        )
        self.assertIn("META", sold_later_listings(later, "2026-03-31"))
        page = editor_page(later, view_date="2026-03-31")
        self.assertIn("META", page.sold_later)
        self.assertFalse(hasattr(page.paper.held[0], "deceased"))
        self.assertAlmostEqual(hist.seed.cash_base or 0, 4427.0, places=5)
        self.assertAlmostEqual(hist.seed.fx_for("USD") or 0, 8.0, places=5)
        added = save(with_hyp_fill(hist, _fill()))
        self.assertEqual(len(added.hyp_fills()), 1)
        self.assertIsNotNone(added.hyp_fills()[0].id)
        listed = list_histories()
        self.assertEqual(len(listed), 1)
        self.assertEqual(len(listed[0].hyp_fills()), 1)
        self.assertAlmostEqual(
            listed[0].seed.cash_base or 0, hist.seed.cash_base or 0, places=5
        )
        copied = copy_history(int(hist.id))
        self.assertEqual(copied.fork_date, hist.fork_date)
        self.assertEqual(copied.name, "Missed AAPL copy")
        self.assertEqual(len(copied.hyp_fills()), 1)
        self.assertNotEqual(copied.id, hist.id)
        self.assertAlmostEqual(
            copied.seed.cash_base or 0, hist.seed.cash_base or 0, places=5
        )
        hyp_id = added.hyp_fills()[0].id
        cleared = save(drop_hyp_fill(added, int(hyp_id)))
        self.assertEqual(len(cleared.hyp_fills()), 0)
        self.assertEqual(len(get_history(int(hist.id)).hyp_fills()), 0)
        delete_history(int(copied.id))
        self.assertEqual(len(list_histories()), 1)
        self.assertEqual(self._trade_count(), self.ib_trades)
        self.assertEqual(self.ib_sqlite.stat().st_mtime, self.ib_mtime)
        self.assertTrue(db_path().is_file())
        self.assertNotEqual(db_path(), self.ib_sqlite)
