"""Paper Reg-T on a marked cash book as of D.

Negative cash is the loan. Maintenance is 25% of quoted stock.
Overnight buying power is max(0, excess / 0.50). Not IB house,
not TIMS, not Live NAV. Stock already excludes unquoted lots.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.analysis_web.services.mark_book import MarkedNav


MAINT_RATE = 0.25
INITIAL_RATE = 0.50
_QTY_EPS = 1e-9


class FundingError(Exception):
    """What-if buy fails paper Reg-T. ``code`` is ``insufficient_buying_power``."""

    def __init__(
        self,
        message: str,
        *,
        need: float,
        buying_power: float,
        excess_after: float,
    ):
        super().__init__(message)
        self.code = "insufficient_buying_power"
        self.message = message
        self.need = need
        self.buying_power = buying_power
        self.excess_after = excess_after

    def as_json(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "need": self.need,
            "buying_power": self.buying_power,
            "excess_after": self.excess_after,
        }


@dataclass(frozen=True)
class PaperAccount:
    """Paper Reg-T on a marked cash book as of D.

    Negative cash is the loan. Maintenance is 25% of quoted stock.
    Overnight buying power is max(0, excess / 0.50). Not IB house,
    not TIMS, not Live NAV. Stock already excludes unquoted lots.
    """

    as_of: str
    cash: float | None
    stock: float
    nav: float
    loan: float
    maintenance: float
    excess: float
    buying_power: float
    n_unquoted: int
    n_unavailable: int
    base_currency: str

    def as_json(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of,
            "cash": self.cash,
            "stock": self.stock,
            "nav": self.nav,
            "loan": self.loan,
            "maintenance": self.maintenance,
            "excess": self.excess,
            "buying_power": self.buying_power,
            "n_unquoted": self.n_unquoted,
            "n_unavailable": self.n_unavailable,
            "base_currency": self.base_currency,
        }


def paper_account(
    marked: MarkedNav,
    *,
    n_unavailable: int | None = None,
    base_currency: str = "",
) -> PaperAccount:
    """loan = max(0, −cash); maint = 0.25×stock; excess = nav−maint;
    buying_power = max(0, excess / 0.50)."""
    cash = marked.cash
    cash_f = 0.0 if cash is None else float(cash)
    loan = max(0.0, -cash_f)
    stock = float(marked.stock)
    nav = float(marked.nav)
    maint = MAINT_RATE * stock
    excess = nav - maint
    buying_power = max(0.0, excess / INITIAL_RATE)
    n_unav = marked.n_unavailable if n_unavailable is None else int(n_unavailable)
    return PaperAccount(
        as_of=marked.as_of,
        cash=cash,
        stock=stock,
        nav=nav,
        loan=loan,
        maintenance=maint,
        excess=excess,
        buying_power=buying_power,
        n_unquoted=marked.n_unquoted,
        n_unavailable=n_unav,
        base_currency=base_currency,
    )


def preview_buy(
    account: PaperAccount,
    cost_base: float,
    *,
    mark_value: float | None = None,
) -> PaperAccount:
    """Long at the mark: cash − cost, stock + cost, NAV unchanged when
    fill equals the mark. Override fills may move NAV (pass mark_value)."""
    cost = float(cost_base)
    add_stock = cost if mark_value is None else float(mark_value)
    cash0 = 0.0 if account.cash is None else float(account.cash)
    cash1 = cash0 - cost
    stock1 = account.stock + add_stock
    nav1 = cash1 + stock1
    loan = max(0.0, -cash1)
    maint = MAINT_RATE * stock1
    excess = nav1 - maint
    buying_power = max(0.0, excess / INITIAL_RATE)
    return PaperAccount(
        as_of=account.as_of,
        cash=cash1,
        stock=stock1,
        nav=nav1,
        loan=loan,
        maintenance=maint,
        excess=excess,
        buying_power=buying_power,
        n_unquoted=account.n_unquoted,
        n_unavailable=account.n_unavailable,
        base_currency=account.base_currency,
    )


def preview_sell(
    account: PaperAccount,
    proceeds_base: float,
    *,
    mark_value: float | None = None,
) -> PaperAccount:
    """Sell at the mark: cash + proceeds, stock − proceeds."""
    proceeds = float(proceeds_base)
    drop_stock = proceeds if mark_value is None else float(mark_value)
    cash0 = 0.0 if account.cash is None else float(account.cash)
    cash1 = cash0 + proceeds
    stock1 = max(0.0, account.stock - drop_stock)
    nav1 = cash1 + stock1
    loan = max(0.0, -cash1)
    maint = MAINT_RATE * stock1
    excess = nav1 - maint
    buying_power = max(0.0, excess / INITIAL_RATE)
    return PaperAccount(
        as_of=account.as_of,
        cash=cash1,
        stock=stock1,
        nav=nav1,
        loan=loan,
        maintenance=maint,
        excess=excess,
        buying_power=buying_power,
        n_unquoted=account.n_unquoted,
        n_unavailable=account.n_unavailable,
        base_currency=account.base_currency,
    )


def assert_buyable(
    account: PaperAccount,
    cost_base: float,
    *,
    mark_value: float | None = None,
) -> None:
    """Raise FundingError if initial (0.50×cost) > BP
    or preview_buy(...).excess < 0. Does not look at raw cash."""
    cost = float(cost_base)
    if cost <= _QTY_EPS:
        return
    initial = INITIAL_RATE * cost
    after = preview_buy(account, cost, mark_value=mark_value)
    if initial > account.buying_power + _QTY_EPS or after.excess < -_QTY_EPS:
        raise FundingError(
            "Not enough buying power for this buy.",
            need=initial,
            buying_power=account.buying_power,
            excess_after=after.excess,
        )
