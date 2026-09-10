"""Cash-book mark: cash + Σ qty × close × fx. Unquoted contributes 0."""

from __future__ import annotations

import unittest

from apps.analysis_web.services.book_state import BookState, Lot
from apps.analysis_web.services.mark_book import (
    mark_book,
    mark_lots,
    mark_on,
    nav_delta_rows,
)
from apps.analysis_web.services.price_history import (
    FakeHistoryBackend,
    PriceBar,
    PriceHistory,
    close_on,
)


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


class NavDeltaRowsTests(unittest.TestCase):
    def test_rows_sum_to_nav_delta_including_cash(self):
        actual = mark_book(
            _state(
                Lot("META", "USD", 10, 8.0, ib_symbol="META"),
                Lot("0700.HK", "HKD", 100, 1.0, ib_symbol="700"),
            ),
            {"META": 55.0, "0700.HK": 10.0},
        )
        alt = mark_book(
            _state(
                Lot("0700.HK", "HKD", 100, 1.0, ib_symbol="700"),
                Lot("AAPL", "USD", 1, 8.0, ib_symbol="AAPL"),
                cash=500 + 10 * 50 * 8 - 1 * 210 * 8,
            ),
            {"0700.HK": 10.0, "AAPL": 210.0},
        )
        rows = nav_delta_rows(actual, alt)
        by = {name: pl for name, pl in rows}
        self.assertIn("META", by)
        self.assertIn("AAPL", by)
        self.assertIn("Cash", by)
        self.assertNotIn("0700.HK", by)
        self.assertAlmostEqual(sum(pl for _, pl in rows), alt.nav - actual.nav, places=5)
        self.assertLess(by["META"], 0)
        self.assertGreater(by["AAPL"], 0)

    def test_unquoted_is_zero_and_missing_cash_is_zero(self):
        actual = mark_book(
            _state(Lot("META", "USD", 10, 8.0, ib_symbol="META"), cash=100),
            {"META": 50.0},
        )
        alt_state = BookState(
            lots=(Lot("META", "USD", 10, 8.0, ib_symbol="META"),),
            cash_base=None,
            as_of="2026-03-31",
            caveats=(),
            base_currency="HKD",
        )
        alt = mark_book(alt_state, {})
        rows = dict(nav_delta_rows(actual, alt))
        self.assertAlmostEqual(sum(rows.values()), alt.nav - actual.nav, places=5)
        self.assertIn("Cash", rows)
        self.assertAlmostEqual(rows["Cash"], -100.0, places=5)


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
        self.assertAlmostEqual(close_on(bars, "2026-04-02").close, 52.0, places=5)  # type: ignore[union-attr]
        self.assertIsNone(close_on((), "2026-03-31"))


class AsOfMarkTests(unittest.TestCase):
    def test_error_is_unavailable_empty_bars_after_d_is_unquoted(self):
        missing = FakeHistoryBackend({}).history("ZZZZ", since="2025-10-01")
        self.assertEqual(missing.error, "unavailable")
        self.assertEqual(mark_on(missing, "2026-03-31").status, "unavailable")

        later = PriceHistory(
            symbol="META",
            bars=(PriceBar("2026-04-10", 60.0),),
        )
        unquoted = mark_on(later, "2026-03-31")
        self.assertEqual(unquoted.status, "unquoted")
        self.assertIsNone(unquoted.close)

        friday = PriceHistory(
            symbol="META",
            bars=(PriceBar("2026-03-27", 49.0),),
        )
        sat = mark_on(friday, "2026-03-28")
        self.assertEqual(sat.status, "quoted")
        self.assertAlmostEqual(sat.close or 0, 49.0, places=5)
        self.assertEqual(sat.bar_date, "2026-03-27")

    def test_mark_lots_splits_unavailable(self):
        state = _state(
            Lot("META", "USD", 10, 8.0, ib_symbol="META"),
            Lot("0700.HK", "HKD", 100, 1.0, ib_symbol="700"),
        )
        from apps.analysis_web.services.mark_book import AsOfMark

        marks = {
            "META": AsOfMark(
                listing="META",
                as_of="2026-03-31",
                status="quoted",
                close=55.0,
                bar_date="2026-03-31",
            ),
            "0700.HK": AsOfMark(
                listing="0700.HK",
                as_of="2026-03-31",
                status="unavailable",
                error="unavailable",
            ),
        }
        out = mark_lots(state, marks)
        self.assertEqual(out.n_unavailable, 1)
        self.assertEqual(out.n_repriced, 1)
        by = {r.listing: r for r in out.rows}
        self.assertEqual(by["0700.HK"].error, "unavailable")
        self.assertEqual(by["META"].bar_date, "2026-03-31")
