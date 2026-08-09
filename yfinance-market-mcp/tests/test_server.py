"""Basic tests for yfinance MCP server tools."""

from yfinance_mcp.utils import safe_value, series_to_dict, df_to_records
import pandas as pd
import numpy as np


def test_safe_value_none():
    assert safe_value(None) is None


def test_safe_value_nan():
    assert safe_value(float("nan")) is None


def test_safe_value_numpy_int():
    assert safe_value(np.int64(42)) == 42
    assert isinstance(safe_value(np.int64(42)), int)


def test_safe_value_numpy_float():
    assert safe_value(np.float64(3.14)) == 3.14
    assert isinstance(safe_value(np.float64(3.14)), float)


def test_safe_value_timestamp():
    ts = pd.Timestamp("2024-01-15 10:30:00")
    assert safe_value(ts) == "2024-01-15T10:30:00"


def test_series_to_dict():
    s = pd.Series({"a": 1, "b": np.float64(2.5), "c": None})
    result = series_to_dict(s)
    assert result == {"a": 1, "b": 2.5, "c": None}


def test_df_to_records_empty():
    assert df_to_records(pd.DataFrame()) == []
    assert df_to_records(None) == []


def test_df_to_records():
    df = pd.DataFrame({"price": [100.0, 101.5], "volume": [1000, 2000]})
    records = df_to_records(df)
    assert len(records) == 2
    assert records[0]["price"] == 100.0
    assert records[1]["volume"] == 2000
