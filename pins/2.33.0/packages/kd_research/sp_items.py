"""Canonical S&P Capital IQ data items used by the research harness.

The map below translates S&P's `data_item_id` and `data_item_name` into stable,
friendly keys that downstream scripts and agents can rely on. Add new items as
sectors require them (e.g., NIM for banks, FFO for REITs).
"""

from __future__ import annotations

from typing import Any

# fmt: off
CANONICAL_ITEMS: dict[str, dict[str, Any]] = {
    # Income statement
    "revenue":                {"id": 28,    "name": "Total Revenues",            "statement": "income"},
    "gross_profit":           {"id": 10,    "name": "Gross Profit",              "statement": "income"},
    "operating_income":       {"id": 21,    "name": "Operating Income",          "statement": "income"},
    "ebt_excl_unusual":       {"id": 4,     "name": "EBT, Excl. Unusual Items",  "statement": "income"},
    "ebt_incl_unusual":       {"id": 139,   "name": "EBT, Incl. Unusual Items",  "statement": "income"},
    "net_income":             {"id": 15,    "name": "Net Income - (IS)",         "statement": "income"},
    "net_income_to_company":  {"id": 41571, "name": "Net Income to Company",     "statement": "income"},
    "interest_expense":       {"id": 82,    "name": "Interest Expense, Total",   "statement": "income"},
    "other_operating_expenses": {"id": 380, "name": "Other Operating Expenses, Total", "statement": "income"},

    # Supplemental / per-share
    "eps_diluted":            {"id": 8,     "name": "Net EPS - Diluted",         "statement": "supplemental"},
    "eps_basic":              {"id": 9,     "name": "Net EPS - Basic",           "statement": "supplemental"},
    "dividend_per_share":     {"id": 3058,  "name": "Dividend Per Share",        "statement": "supplemental"},
    "ebitdar":                {"id": 21674, "name": "EBITDAR",                   "statement": "supplemental"},
    "ebita":                  {"id": 100689,"name": "EBITA",                     "statement": "supplemental"},

    # Balance sheet
    "total_receivables":      {"id": 1001,  "name": "Total Receivables",                    "statement": "balance"},
    "cash_and_short_term_investments": {"id": 1002, "name": "Total Cash And Short Term Investments", "statement": "balance"},
    "net_ppe":                {"id": 1004,  "name": "Net Property Plant And Equipment",      "statement": "balance"},
    "total_common_equity":    {"id": 1006,  "name": "Total Common Equity",                   "statement": "balance"},
    "total_assets":           {"id": 1007,  "name": "Total Assets",                          "statement": "balance"},
    "total_current_assets":   {"id": 1008,  "name": "Total Current Assets",                  "statement": "balance"},
    "total_current_liabilities": {"id": 1009, "name": "Total Current Liabilities",          "statement": "balance"},
    "total_liabilities_and_equity": {"id": 1013, "name": "Total Liabilities And Equity",     "statement": "balance"},
    "total_equity":           {"id": 1275,  "name": "Total Equity",                          "statement": "balance"},
    "total_liabilities":      {"id": 1276,  "name": "Total Liabilities - (Standard / Utility Template)", "statement": "balance"},

    # Cash flow
    "cash_from_financing":    {"id": 2004,  "name": "Cash from Financing",                   "statement": "cashflow"},
    "cash_from_investing":    {"id": 2005,  "name": "Cash from Investing",                   "statement": "cashflow"},
    "cash_from_operations":   {"id": 2006,  "name": "Cash from Operations",                  "statement": "cashflow"},
    "dividends_paid":         {"id": 2022,  "name": "Common & Preferred Stock Dividends Paid", "statement": "cashflow"},
    "net_change_in_cash":     {"id": 2093,  "name": "Net Change in Cash",                    "statement": "cashflow"},
    "net_income_cashflow":    {"id": 2150,  "name": "Net Income - (CF)",                     "statement": "cashflow"},
    "depreciation_amortization": {"id": 2160, "name": "Depreciation & Amortization, Total - CF", "statement": "cashflow"},
    "total_debt_issued":      {"id": 2161,  "name": "Total Debt Issued",                     "statement": "cashflow"},
    "total_debt_repaid":      {"id": 2166,  "name": "Total Debt Repaid",                     "statement": "cashflow"},
}
# fmt: on


def item_id_to_name(item_id: int) -> str | None:
    """Return the canonical friendly key for a given S&P data_item_id."""
    for key, meta in CANONICAL_ITEMS.items():
        if meta["id"] == item_id:
            return key
    return None


def item_name_to_id(name: str) -> int | None:
    """Return the S&P data_item_id for a canonical friendly key."""
    meta = CANONICAL_ITEMS.get(name)
    return meta["id"] if meta else None


def items_by_statement(statement: str) -> dict[str, dict[str, Any]]:
    """Return canonical items belonging to a statement type (income/balance/cashflow/supplemental)."""
    return {k: v for k, v in CANONICAL_ITEMS.items() if v.get("statement") == statement}


def all_item_ids() -> list[int]:
    """Return all canonical S&P data_item_ids."""
    return [meta["id"] for meta in CANONICAL_ITEMS.values()]
