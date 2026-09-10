"""as_of_book ledger walk on the mini IB fixture."""

from __future__ import annotations

import unittest
from pathlib import Path

from apps.analysis_web.services.book_state import BookState, Lot, as_of_book
from apps.analysis_web.services.ib_statement import IbBook, Trade, parse_activity_csv


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ib_activity_mini.csv"


def _book() -> IbBook:
    stmt = parse_activity_csv(FIXTURE)
    return IbBook(snapshot=stmt, trades=list(stmt.trades))


def _by_listing(state) -> dict[str, float]:
    return {lot.listing: lot.qty for lot in state.lots}


class AsOfBookFixtureTests(unittest.TestCase):
    def setUp(self):
        self.book = _book()

    def test_jan_5_no_stock_lots(self):
        state = as_of_book(self.book, "2026-01-05")
        self.assertEqual(_by_listing(state), {})
        self.assertEqual(state.as_of, "2026-01-05")
        self.assertEqual(state.base_currency, "HKD")
        self.assertTrue(any("ledger" in c.lower() for c in state.caveats))

    def test_jan_12_tencent_only(self):
        state = as_of_book(self.book, "2026-01-12")
        by = _by_listing(state)
        self.assertAlmostEqual(by["0700.HK"], 100.0, places=5)
        self.assertNotIn("META", by)
        lot = state.lot_by_listing("0700.HK")
        self.assertIsNotNone(lot)
        assert lot is not None
        self.assertEqual(lot.ib_symbol, "700")
        self.assertEqual(lot.currency, "HKD")
        self.assertAlmostEqual(lot.stmt_fx or 0, 1.0, places=5)

    def test_feb_1_meta_twelve(self):
        state = as_of_book(self.book, "2026-02-01")
        by = _by_listing(state)
        self.assertAlmostEqual(by["0700.HK"], 100.0, places=5)
        self.assertAlmostEqual(by["META"], 12.0, places=5)
        meta = state.lot_by_listing("META")
        self.assertIsNotNone(meta)
        assert meta is not None
        self.assertEqual(meta.ib_symbol, "META")
        self.assertAlmostEqual(meta.stmt_fx or 0, 8.0, places=5)

    def test_period_to_is_snapshot(self):
        state = as_of_book(self.book, "2026-03-31")
        by = _by_listing(state)
        self.assertAlmostEqual(by["0700.HK"], 100.0, places=5)
        self.assertAlmostEqual(by["META"], 10.0, places=5)
        self.assertAlmostEqual(state.cash_base or 0, 500.0, places=5)

    def test_after_period_to_no_extra_fills_is_snapshot(self):
        state = as_of_book(self.book, "2026-04-15")
        by = _by_listing(state)
        self.assertAlmostEqual(by["0700.HK"], 100.0, places=5)
        self.assertAlmostEqual(by["META"], 10.0, places=5)
        self.assertAlmostEqual(state.cash_base or 0, 500.0, places=5)

    def test_forex_trades_ignored(self):
        forex = [
            t for t in self.book.trades if (t.asset_category or "").lower() == "forex"
        ]
        self.assertEqual(len(forex), 1)
        state = as_of_book(self.book, "2026-03-31")
        self.assertEqual(len(state.lots), 2)

    def test_cash_walks_stock_proceeds(self):
        at_end = as_of_book(self.book, "2026-03-31")
        before_meta_sell = as_of_book(self.book, "2026-02-01")
        # Reverse META sell +110 proceeds, -1 commission, USD × 8.
        self.assertAlmostEqual(
            (before_meta_sell.cash_base or 0) - (at_end.cash_base or 0),
            -109.0 * 8.0,
            places=5,
        )

    def test_after_period_to_applies_fill(self):
        extra = Trade(
            row_index=99,
            discriminator="Order",
            asset_category="Stocks",
            currency="USD",
            ib_symbol="META",
            traded_at="2026-04-10T10:00:00",
            quantity=-3.0,
            proceeds=180.0,
            commission=-1.0,
        )
        book = IbBook(
            snapshot=self.book.snapshot,
            trades=list(self.book.trades) + [extra],
        )
        state = as_of_book(book, "2026-04-10")
        self.assertAlmostEqual(state.lot_by_listing("META").qty, 7.0, places=5)  # type: ignore[union-attr]
        self.assertAlmostEqual(
            (state.cash_base or 0) - 500.0,
            179.0 * 8.0,
            places=5,
        )

    def test_fx_for_uses_lot_when_map_empty(self):
        seed = BookState(
            lots=(
                Lot(
                    listing="VSNT",
                    currency="USD",
                    qty=1.0,
                    stmt_fx=7.8397,
                    ib_symbol="VSNT",
                ),
            ),
            cash_base=0.0,
            as_of="2026-01-01",
            caveats=(),
            base_currency="HKD",
            fx_by_ccy=(),
        )
        self.assertAlmostEqual(seed.fx_for("USD") or 0, 7.8397, places=4)
        self.assertIsNone(seed.fx_for("EUR"))
        self.assertAlmostEqual(seed.fx_for("HKD") or 0, 1.0, places=5)
        mapped = BookState(
            lots=seed.lots,
            cash_base=0.0,
            as_of="2026-01-01",
            caveats=(),
            base_currency="HKD",
            fx_by_ccy=(("USD", 8.0),),
        )
        self.assertAlmostEqual(mapped.fx_for("USD") or 0, 8.0, places=5)

    def test_bad_date_raises(self):
        with self.assertRaises(ValueError):
            as_of_book(self.book, "not-a-date")

    def test_before_period_from_flags_cash(self):
        state = as_of_book(self.book, "2025-12-01")
        self.assertTrue(any("before the statement" in c for c in state.caveats))

    def test_seed_json_roundtrip(self):
        state = as_of_book(self.book, "2026-03-31")
        loaded = type(state).from_json(state.as_json())
        self.assertEqual(loaded.as_of, state.as_of)
        self.assertAlmostEqual(loaded.cash_base or 0, state.cash_base or 0, places=5)
        self.assertEqual(len(loaded.lots), len(state.lots))
        self.assertAlmostEqual(
            loaded.lot_by_listing("META").qty, 10.0, places=5  # type: ignore[union-attr]
        )
        self.assertAlmostEqual(state.fx_for("USD") or 0, 8.0, places=5)
        self.assertAlmostEqual(loaded.fx_for("USD") or 0, 8.0, places=5)
        self.assertAlmostEqual(loaded.fx_for("HKD") or 0, 1.0, places=5)
