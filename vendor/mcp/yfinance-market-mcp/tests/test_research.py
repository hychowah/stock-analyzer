"""Tests for research-oriented yfinance MCP tools."""

import pandas as pd
import pytest

from yfinance_mcp.research import (
    _get_item,
    _keyword_score,
    _latest_column,
    _safe_float,
    classify_sector,
)


def test_latest_column_newest_first():
    df = pd.DataFrame(
        {"2025-06-30": [1, 2], "2024-06-30": [3, 4]},
        index=["Revenue", "Net Income"],
    )
    latest = _latest_column(df)
    assert latest["Revenue"] == 1
    assert latest["Net Income"] == 2


def test_latest_column_empty():
    assert _latest_column(None) is None
    assert _latest_column(pd.DataFrame()) is None


def test_get_item_finds_key():
    s = pd.Series({"Total Revenue": 100.0, "Net Income": 20.0})
    assert _get_item(s, ["Total Revenue", "Revenue"]) == 100.0
    assert _get_item(s, ["Missing", "Net Income"]) == 20.0


def test_get_item_default():
    s = pd.Series({"A": 1})
    assert _get_item(s, ["B", "C"], default=5.0) == 5.0


def test_safe_float():
    assert _safe_float("3.14") == 3.14
    assert _safe_float(None, default=0.0) == 0.0
    assert _safe_float("not a number", default=1.0) == 1.0


def test_keyword_score():
    text = "this is a bank holding company with loans and deposits"
    assert _keyword_score(text, ["bank", "loans", "insurance"]) == 2


@pytest.mark.network
@pytest.mark.slow
def test_classify_sector_smoke():
    """Network-dependent smoke test for sector classification."""
    result = classify_sector("JPM")
    assert "error" not in result
    assert result["primary_sector"] == "banking"
    assert result["confidence"] >= 0.70
    assert result["suggested_module_file"].endswith("sector_banking.md")
