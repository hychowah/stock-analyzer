"""Paper Reg-T on a marked cash book. Not IB house margin."""

from __future__ import annotations

import unittest

from apps.analysis_web.services.book_state import BookState, Lot
from apps.analysis_web.services.mark_book import mark_book
from apps.analysis_web.services.paper_account import (
    FundingError,
    assert_buyable,
    paper_account,
    preview_buy,
)


def _marked(cash: float = 1000.0, stock_px: float = 40.0) -> object:
    state = BookState(
        lots=(Lot("META", "USD", 100, 1.0, ib_symbol="META"),),
        cash_base=cash,
        as_of="2026-03-31",
        caveats=(),
        base_currency="USD",
    )
    return mark_book(state, {"META": stock_px})


class PaperAccountTests(unittest.TestCase):
    def test_identities(self):
        marked = _marked(cash=1000.0, stock_px=40.0)
        acct = paper_account(marked, base_currency="USD")
        self.assertAlmostEqual(acct.stock, 4000.0, places=5)
        self.assertAlmostEqual(acct.nav, 5000.0, places=5)
        self.assertAlmostEqual(acct.loan, 0.0, places=5)
        self.assertAlmostEqual(acct.maintenance, 1000.0, places=5)
        self.assertAlmostEqual(acct.excess, 4000.0, places=5)
        self.assertAlmostEqual(acct.buying_power, 8000.0, places=5)

    def test_negative_cash_is_the_loan(self):
        marked = _marked(cash=-200.0, stock_px=40.0)
        acct = paper_account(marked, base_currency="USD")
        self.assertAlmostEqual(acct.loan, 200.0, places=5)
        self.assertAlmostEqual(acct.nav, 3800.0, places=5)

    def test_preview_buy_at_mark_keeps_nav(self):
        acct = paper_account(_marked(), base_currency="USD")
        after = preview_buy(acct, 2000.0)
        self.assertAlmostEqual(after.nav, acct.nav, places=5)
        self.assertAlmostEqual(after.cash or 0, -1000.0, places=5)
        self.assertAlmostEqual(after.loan, 1000.0, places=5)
        self.assertAlmostEqual(after.stock, 6000.0, places=5)

    def test_assert_buyable_uses_buying_power_not_cash(self):
        acct = paper_account(_marked(cash=500.0, stock_px=40.0), base_currency="USD")
        self.assertLess(acct.cash or 0, 1600.0)
        assert_buyable(acct, 1600.0)
        with self.assertRaises(FundingError) as ctx:
            assert_buyable(acct, 50_000.0)
        self.assertEqual(ctx.exception.code, "insufficient_buying_power")
