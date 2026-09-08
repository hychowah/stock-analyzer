"""Cash-book mark: cash + Σ qty × close × fx. Unquoted contributes 0."""

from __future__ import annotations

import unittest

from apps.analysis_web.services.book_state import BookState, Lot
from apps.analysis_web.services.mark_book import mark_book
from apps.analysis_web.services.price_history import PriceBar, close_on


def _state(*lots: Lot, cash: float = 500) -> BookState:
    return BookState(
        lots=lots,
        cash_base=cash,
        as_of="2026-03-31",
        caveats=(),
        base_currency="HKD",
    )


class MarkBookTests(unittest.TestCase):
    def test_identity_includes_cash(self):
        state = _state(
            Lot("0700.HK", "HKD", 100, 1.0, ib_symbol="700"),
            Lot("META", "USD", 10, 8.0, ib_symbol="META"),
        )
        out = mark_book(state, {"0700.HK": 10.0, "META": 55.0})
        self.assertAlmostEqual(out.stock, 100 * 10 * 1 + 10 * 55 * 8, places=5)
        self.assertAlmostEqual(out.nav, 500 + out.stock, places=5)
        self.assertAlmostEqual(out.cash or 0, 500.0, places=5)
        self.assertEqual(out.n_repriced, 2)
        self.assertEqual(out.n_unquoted, 0)

    def test_unquoted_contributes_zero_not_statement(self):
        state = _state(
            Lot("0700.HK", "HKD", 100, 1.0, ib_symbol="700"),
            Lot("META", "USD", 10, 8.0, ib_symbol="META"),
        )
        out = mark_book(state, {"META": 55.0})
        self.assertEqual(out.n_unquoted, 1)
        self.assertEqual(out.n_repriced, 1)
        by = {r.listing: r for r in out.rows}
        self.assertIsNone(by["0700.HK"].value_base)
        self.assertEqual(by["0700.HK"].error, "unquoted")
        self.assertAlmostEqual(out.stock, 10 * 55 * 8, places=5)
        self.assertAlmostEqual(out.nav, 500 + 4400, places=5)

    def test_missing_fx_flagged(self):
        state = _state(Lot("META", "USD", 10, None, ib_symbol="META"))
        out = mark_book(state, {"META": 55.0})
        self.assertEqual(out.n_unquoted, 1)
        self.assertEqual(out.rows[0].error, "missing_fx")
        self.assertAlmostEqual(out.nav, 500.0, places=5)

    def test_none_cash_counts_as_zero(self):
        state = BookState(
            lots=(Lot("META", "USD", 10, 8.0, ib_symbol="META"),),
            cash_base=None,
            as_of="2026-03-31",
            caveats=(),
            base_currency="HKD",
        )
        out = mark_book(state, {"META": 50.0})
        self.assertIsNone(out.cash)
        self.assertAlmostEqual(out.nav, 10 * 50 * 8, places=5)


class CloseOnTests(unittest.TestCase):
    def test_picks_on_or_before(self):
        bars = (
            PriceBar("2026-03-30", 49.0),
            PriceBar("2026-03-31", 50.0),
            PriceBar("2026-04-02", 52.0),
        )
        self.assertAlmostEqual(close_on(bars, "2026-03-31").close, 50.0, places=5)  # type: ignore[union-attr]
        self.assertAlmostEqual(close_on(bars, "2026-04-01").close, 50.0, places=5)  # type: ignore[union-attr]
        self.assertIsNone(close_on(bars, "2026-03-01"))
