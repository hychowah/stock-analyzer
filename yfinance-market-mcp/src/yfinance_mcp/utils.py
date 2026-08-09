"""Serialization helpers for converting pandas/numpy types to JSON-safe Python natives."""

import math
from datetime import datetime


def safe_value(v):
    """Convert a single value to a JSON-serializable Python native type.

    Args:
        v: Any value (numpy, pandas, or native Python type).

    Returns:
        JSON-safe Python native (str, int, float, None, or original).
    """
    import numpy as np
    import pandas as pd

    if v is None:
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        val = float(v)
        return None if math.isnan(val) else val
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, float) and math.isnan(val):
        return None
    if isinstance(v, (np.ndarray,)):
        return v.tolist()
    return v


def series_to_dict(s):
    """Convert a pandas Series to a dict with JSON-safe values.

    Args:
        s: pandas Series or dict-like object.

    Returns:
        dict with string keys and JSON-safe values.
    """
    import pandas as pd

    if s is None:
        return {}
    if isinstance(s, pd.Series):
        s = s.to_dict()
    return {str(k): safe_value(v) for k, v in s.items()}


def df_to_records(df, max_rows=500):
    """Convert a DataFrame to a list of dicts with JSON-safe values.

    Args:
        df: pandas DataFrame.
        max_rows: Maximum number of rows to return (default 500).

    Returns:
        list[dict] with string keys and JSON-safe values.
    """
    import pandas as pd

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return []
    df = df.head(max_rows)
    # Reset index to include it in records if it's meaningful (e.g. Date)
    if df.index.name or not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index()
    records = []
    for _, row in df.iterrows():
        records.append({str(k): safe_value(v) for k, v in row.items()})
    return records
