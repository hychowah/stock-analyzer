#!/usr/bin/env python3
"""Agent 2: Fetch market and financial API data and write api_data.json.

Outputs:
    <session>/registry/api_data.json

Usage:
    yfinance-market-mcp/.venv/bin/python scripts/agent2_api_data.py \
        --ticker ADBE --date 2026-07-20 --output-dir /workspace-stock-research
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yfinance as yf


def _safe(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _df_to_dict(df) -> dict[str, Any] | None:
    if df is None or df.empty:
        return None
    return {str(idx): {str(col): _safe(val) for col, val in row.items()} for idx, row in df.iterrows()}


def main():
    parser = argparse.ArgumentParser(description="Agent 2: fetch market and financial API data")
    parser.add_argument("--ticker", required=True, help="Ticker symbol")
    parser.add_argument("--date", required=True, help="Session date YYYY-MM-DD")
    parser.add_argument("--output-dir", default="/workspace-stock-research", help="Project root")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    session_date = args.date
    output_dir = Path(args.output_dir).expanduser().resolve()
    registry_dir = output_dir / ticker / session_date / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    out_path = registry_dir / "api_data.json"

    print(f"Fetching API data for {ticker}...")
    t = yf.Ticker(ticker)
    info = t.info or {}

    result = {
        "ticker": ticker,
        "session_date": session_date,
        "fetch_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "yfinance direct library",
        "info": info,
        "income_statement_yearly": _df_to_dict(t.income_stmt),
        "income_statement_quarterly": _df_to_dict(t.quarterly_income_stmt),
        "balance_sheet_yearly": _df_to_dict(t.balance_sheet),
        "balance_sheet_quarterly": _df_to_dict(t.quarterly_balance_sheet),
        "cashflow_yearly": _df_to_dict(t.cashflow),
        "cashflow_quarterly": _df_to_dict(t.quarterly_cashflow),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Saved {out_path}")
    print(f"  currentPrice: {info.get('currentPrice')}")
    print(f"  marketCap: {info.get('marketCap')}")
    print(f"  enterpriseValue: {info.get('enterpriseValue')}")


if __name__ == "__main__":
    main()
