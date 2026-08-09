#!/usr/bin/env python3
"""Agent 4: Technical analysis and entry-timing.

Outputs:
    <session>/registry/technical.json

Usage:
    yfinance-market-mcp/.venv/bin/python scripts/agent4_technical.py \
        --ticker ADBE --date 2026-07-20 --output-dir /workspace-stock-research
"""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf


def _safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def fetch_history(ticker: str, period: str = "2y", interval: str = "1d", end: datetime | None = None) -> pd.DataFrame:
    kwargs = {"period": period, "interval": interval, "progress": False, "auto_adjust": True}
    if end is not None:
        kwargs["end"] = end.strftime("%Y-%m-%d")
    df = yf.download(ticker, **kwargs)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna().copy()
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"])
    df["date"] = pd.to_datetime(df.index)
    df = df.sort_values("date").reset_index(drop=True)
    return df


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    for window in [20, 50, 100, 200]:
        df[f"ma_{window}"] = df["close"].rolling(window=window, min_periods=window).mean()
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["rsi_14"] = 100 - (100 / (1 + rs))
    return df


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr_14"] = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return df


def add_bollinger(df: pd.DataFrame, window: int = 20, num_std: int = 2) -> pd.DataFrame:
    df["bb_middle"] = df["close"].rolling(window=window, min_periods=window).mean()
    df["bb_std"] = df["close"].rolling(window=window, min_periods=window).std(ddof=0)
    df["bb_upper"] = df["bb_middle"] + num_std * df["bb_std"]
    df["bb_lower"] = df["bb_middle"] - num_std * df["bb_std"]
    df["bb_pct_b"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
    return df


def find_pivots(df: pd.DataFrame, current_price: float, lookback_days: int = 360, min_touches: int = 2, proximity_pct: float = 0.02) -> dict[str, list[float]]:
    recent = df[df["date"] >= df["date"].max() - timedelta(days=lookback_days)].copy()
    if recent.empty:
        return {"support_levels": [], "resistance_levels": []}

    window = 5
    recent["local_min"] = recent["low"].rolling(window=window, center=True).min() == recent["low"]
    recent["local_max"] = recent["high"].rolling(window=window, center=True).max() == recent["high"]

    support_candidates = recent.loc[recent["local_min"], "low"].tolist()
    resistance_candidates = recent.loc[recent["local_max"], "high"].tolist()

    def cluster_levels(levels: list[float]) -> list[float]:
        if not levels:
            return []
        levels = sorted(set(levels))
        clusters = []
        current = [levels[0]]
        for lvl in levels[1:]:
            if lvl - current[0] <= proximity_pct * current[0]:
                current.append(lvl)
            else:
                clusters.append(sum(current) / len(current))
                current = [lvl]
        clusters.append(sum(current) / len(current))
        return clusters

    support = cluster_levels(support_candidates)
    resistance = cluster_levels(resistance_candidates)

    def count_touches(level: float) -> int:
        return int(((recent["low"] <= level * (1 + proximity_pct)) & (recent["high"] >= level * (1 - proximity_pct))).sum())

    support = [lvl for lvl in support if count_touches(lvl) >= min_touches and lvl < current_price]
    resistance = [lvl for lvl in resistance if count_touches(lvl) >= min_touches and lvl > current_price]

    return {
        "support_levels": sorted([_safe(x) for x in support])[-5:],
        "resistance_levels": sorted([_safe(x) for x in resistance])[:5],
    }


def max_drawdown(df: pd.DataFrame) -> dict[str, Any]:
    cummax = df["close"].cummax()
    drawdown = (df["close"] - cummax) / cummax
    max_dd_idx = drawdown.idxmin()
    peak_idx = cummax.loc[:max_dd_idx].idxmax()
    return {
        "max_drawdown_pct": round(drawdown.min() * 100, 2),
        "peak_date": str(df.loc[peak_idx, "date"].date()),
        "trough_date": str(df.loc[max_dd_idx, "date"].date()),
        "peak_price": round(float(df.loc[peak_idx, "close"]), 2),
        "trough_price": round(float(df.loc[max_dd_idx, "close"]), 2),
    }


def relative_strength(df_stock: pd.DataFrame, df_bench: pd.DataFrame) -> dict[str, Any]:
    merged = pd.merge(df_stock[["date", "close"]], df_bench[["date", "close"]], on="date", suffixes=("_stock", "_bench"))
    merged["rs_ratio"] = merged["close_stock"] / merged["close_bench"]
    latest = merged.iloc[-1]
    rs_20d = merged["rs_ratio"].rolling(20, min_periods=20).mean().iloc[-1]
    rs_50d = merged["rs_ratio"].rolling(50, min_periods=50).mean().iloc[-1]
    rs_1m_change = (latest["rs_ratio"] / merged["rs_ratio"].iloc[-22] - 1) * 100 if len(merged) >= 22 else None
    rs_3m_change = (latest["rs_ratio"] / merged["rs_ratio"].iloc[-66] - 1) * 100 if len(merged) >= 66 else None
    return {
        "current_rs_ratio": round(float(latest["rs_ratio"]), 6),
        "rs_20d_ma": round(float(rs_20d), 6) if not pd.isna(rs_20d) else None,
        "rs_50d_ma": round(float(rs_50d), 6) if not pd.isna(rs_50d) else None,
        "rs_1m_change_pct": round(float(rs_1m_change), 2) if rs_1m_change is not None else None,
        "rs_3m_change_pct": round(float(rs_3m_change), 2) if rs_3m_change is not None else None,
        "vs_moving_average": "above" if latest["rs_ratio"] > rs_50d else "below",
    }


def volume_trends(df: pd.DataFrame) -> dict[str, Any]:
    df["volume_ma_20"] = df["volume"].rolling(20, min_periods=20).mean()
    df["volume_ma_50"] = df["volume"].rolling(50, min_periods=50).mean()
    latest = df.iloc[-1]
    recent = df.tail(20)
    return {
        "latest_volume": int(latest["volume"]),
        "volume_20d_avg": int(latest["volume_ma_20"]),
        "volume_50d_avg": int(latest["volume_ma_50"]),
        "volume_vs_20d_avg_pct": round((latest["volume"] / latest["volume_ma_20"] - 1) * 100, 1) if latest["volume_ma_20"] > 0 else None,
        "volume_vs_50d_avg_pct": round((latest["volume"] / latest["volume_ma_50"] - 1) * 100, 1) if latest["volume_ma_50"] > 0 else None,
        "avg_daily_volume_20d": int(recent["volume"].mean()),
        "price_volume_trend_20d": round(np.corrcoef(recent["close"], recent["volume"])[0, 1], 3) if len(recent) >= 2 else None,
    }


def determine_trend(df: pd.DataFrame) -> dict[str, Any]:
    latest = df.iloc[-1]
    price = latest["close"]
    ma20, ma50, ma100, ma200 = latest["ma_20"], latest["ma_50"], latest["ma_100"], latest["ma_200"]

    # Require valid MAs (not NaN)
    if any(pd.isna(v) for v in [ma20, ma50, ma100, ma200]):
        return {"classification": "insufficient_data", "ma_alignment_score": None}

    alignment = int(sum([
        bool(price > ma20),
        bool(ma20 > ma50),
        bool(ma50 > ma100),
        bool(ma100 > ma200),
    ]))

    # Stricter uptrend: price above 50d and 50d above 200d
    if alignment == 4:
        trend = "strong_uptrend"
    elif price > ma50 and ma50 > ma200:
        trend = "uptrend"
    elif alignment == 0:
        trend = "strong_downtrend"
    elif price < ma50 and ma50 < ma200:
        trend = "downtrend"
    else:
        trend = "mixed"

    return {
        "classification": trend,
        "ma_alignment_score": alignment,
        "golden_cross": bool(ma50 > ma200),
        "death_cross": bool(ma50 < ma200),
        "price_above_200d_ma": bool(price > ma200),
        "price_above_50d_ma": bool(price > ma50),
    }


def generate_levels(df: pd.DataFrame, pivots: dict[str, list[float]], latest_atr: float, max_risk_pct: float = 0.05) -> dict[str, Any]:
    """Generate entry, stop-loss, and target levels from the chosen entry price.

    The stop is computed relative to the preferred entry (not last_close) so that
    risk/R/R and position sizing are internally consistent.
    """
    last_close = float(df.iloc[-1]["close"])
    support_levels = pivots.get("support_levels", [])
    resistance_levels = pivots.get("resistance_levels", [])

    ma20 = float(df.iloc[-1]["ma_20"])
    nearest_support = max([s for s in support_levels if s < last_close], default=ma20 * 0.97)

    # Preferred entry: pullback to 20-day MA or nearest support, whichever is lower
    preferred_entry = min(ma20, nearest_support)
    preferred_entry = max(preferred_entry, last_close * 0.90)  # sanity floor: no more than 10% below price
    entry_zone_low = preferred_entry
    entry_zone_high = last_close

    # Stop loss: 2x ATR below preferred entry, capped at max_risk_pct of entry
    atr_stop = preferred_entry - 2 * latest_atr
    max_risk_stop = preferred_entry * (1 - max_risk_pct)
    stop_loss = max(atr_stop, max_risk_stop)

    # Also enforce stop below entry
    stop_loss = min(stop_loss, preferred_entry * 0.995)

    # If the computed stop is above the entry zone, use a 1x ATR stop
    if stop_loss >= entry_zone_low:
        stop_loss = preferred_entry - latest_atr
        stop_loss = min(stop_loss, preferred_entry * 0.995)

    # Final assertion
    if stop_loss >= entry_zone_low:
        raise RuntimeError(f"Internal error: stop_loss {stop_loss:.2f} >= entry_zone_low {entry_zone_low:.2f}")

    risk = preferred_entry - stop_loss
    reward_target_2r = preferred_entry + 2 * risk
    reward_target_3r = preferred_entry + 3 * risk
    nearest_resistance = min([r for r in resistance_levels if r > preferred_entry], default=reward_target_3r)

    take_profit_1 = max(reward_target_2r, preferred_entry * 1.02)
    take_profit_2 = min(nearest_resistance, reward_target_3r) if nearest_resistance > reward_target_2r else reward_target_3r

    return {
        "last_close": round(last_close, 2),
        "entry_zone": {
            "low": round(entry_zone_low, 2),
            "high": round(entry_zone_high, 2),
            "preferred": round(preferred_entry, 2),
            "rationale": "Pullback to 20-day MA or nearest support",
        },
        "stop_loss": round(stop_loss, 2),
        "take_profit_1": round(take_profit_1, 2),
        "take_profit_2": round(take_profit_2, 2),
        "risk_per_share": round(risk, 2),
        "reward_risk_ratio_tp1": round((take_profit_1 - preferred_entry) / risk, 2) if risk > 0 else None,
        "reward_risk_ratio_tp2": round((take_profit_2 - preferred_entry) / risk, 2) if risk > 0 else None,
    }


def atr_position_sizing(actual_entry: float, actual_stop: float, latest_atr: float, account_risk_pct: float = 0.02) -> dict[str, Any]:
    risk_per_share = actual_entry - actual_stop
    risk_per_share_pct = risk_per_share / actual_entry if actual_entry else None
    return {
        "account_risk_pct": account_risk_pct,
        "atr_14": round(latest_atr, 2),
        "entry_price_used": round(actual_entry, 2),
        "stop_loss_used": round(actual_stop, 2),
        "stop_distance_usd": round(risk_per_share, 2),
        "risk_per_share_pct": round(risk_per_share_pct * 100, 2) if risk_per_share_pct else None,
        "position_size_per_10k_account": round((10000 * account_risk_pct) / risk_per_share, 3) if risk_per_share > 0 else None,
        "position_size_per_100k_account": round((100000 * account_risk_pct) / risk_per_share, 3) if risk_per_share > 0 else None,
        "max_position_pct_of_account_at_risk": round(account_risk_pct * 100, 1),
        "note": "Size position so that if stop is hit, loss equals account_risk_pct of capital. Stop distance reflects the actual entry/stop levels in trade_levels.",
    }


def main():
    parser = argparse.ArgumentParser(description="Agent 4: technical analysis")
    parser.add_argument("--ticker", required=True, help="Ticker symbol")
    parser.add_argument("--date", required=True, help="Session date YYYY-MM-DD")
    parser.add_argument("--output-dir", default="/workspace-stock-research", help="Project root")
    parser.add_argument("--period", default="2y", help="Price history period")
    parser.add_argument("--sector-etf", default="IGV", help="Sector ETF ticker for relative strength")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    session_date = args.date
    output_dir = Path(args.output_dir).expanduser().resolve()
    registry_dir = output_dir / ticker / session_date / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    output_path = registry_dir / "technical.json"

    session_dt = datetime.strptime(session_date, "%Y-%m-%d")
    fetch_end = session_dt + timedelta(days=1)  # yfinance end is exclusive

    # Load API price snapshot for consistency with valuation model
    api_path = registry_dir / "api_data.json"
    api_price = None
    if api_path.exists():
        api_data = json.loads(api_path.read_text())
        api_price = api_data.get("info", {}).get("currentPrice")
        api_price = float(api_price) if api_price is not None else None

    print(f"Fetching {ticker} history...")
    stock = fetch_history(ticker, period=args.period, end=fetch_end)
    print(f"{ticker} rows: {len(stock)}")

    # Use API snapshot price as the session close if available; otherwise use fetched close
    if api_price is not None and len(stock) > 0:
        fetched_close = float(stock.iloc[-1]["close"])
        if abs(fetched_close - api_price) / api_price > 0.001:
            print(f"NOTE: replacing fetched close {fetched_close:.2f} with API session price {api_price:.2f}")
        stock.at[stock.index[-1], "close"] = api_price
        stock.at[stock.index[-1], "high"] = max(api_price, float(stock.iloc[-1]["high"]))
        stock.at[stock.index[-1], "low"] = min(api_price, float(stock.iloc[-1]["low"]))

    print("Fetching benchmark histories...")
    gspc = fetch_history("^GSPC", period=args.period, end=fetch_end)
    ndx = fetch_history("^NDX", period=args.period, end=fetch_end)
    sector_etf = fetch_history(args.sector_etf, period=args.period, end=fetch_end)
    print(f"^GSPC rows: {len(gspc)}, ^NDX rows: {len(ndx)}, {args.sector_etf} rows: {len(sector_etf)}")

    stock = add_moving_averages(stock)
    stock = add_rsi(stock)
    stock = add_macd(stock)
    stock = add_atr(stock)
    stock = add_bollinger(stock)

    latest = stock.iloc[-1]
    latest_atr = float(latest["atr_14"])
    last_close = float(latest["close"])

    pivots = find_pivots(stock, current_price=last_close, lookback_days=360, min_touches=2)
    dd = max_drawdown(stock)
    rs_sp500 = relative_strength(stock, gspc)
    rs_ndx = relative_strength(stock, ndx)
    rs_sector = relative_strength(stock, sector_etf)
    vol = volume_trends(stock)
    trend = determine_trend(stock)

    levels = generate_levels(stock, pivots, latest_atr)
    sizing = atr_position_sizing(
        actual_entry=levels["entry_zone"]["preferred"],
        actual_stop=levels["stop_loss"],
        latest_atr=latest_atr,
    )

    latest_snapshot = {
        "date": str(latest["date"].date()),
        "close": round(last_close, 2),
        "open": round(float(latest["open"]), 2),
        "high": round(float(latest["high"]), 2),
        "low": round(float(latest["low"]), 2),
        "volume": int(latest["volume"]),
        "ma_20": round(float(latest["ma_20"]), 2),
        "ma_50": round(float(latest["ma_50"]), 2),
        "ma_100": round(float(latest["ma_100"]), 2),
        "ma_200": round(float(latest["ma_200"]), 2),
        "rsi_14": round(float(latest["rsi_14"]), 2),
        "macd": round(float(latest["macd"]), 3),
        "macd_signal": round(float(latest["macd_signal"]), 3),
        "macd_hist": round(float(latest["macd_hist"]), 3),
        "atr_14": round(latest_atr, 2),
        "bb_upper": round(float(latest["bb_upper"]), 2),
        "bb_middle": round(float(latest["bb_middle"]), 2),
        "bb_lower": round(float(latest["bb_lower"]), 2),
        "bb_pct_b": round(float(latest["bb_pct_b"]), 3),
    }

    one_year = stock[stock["date"] >= stock["date"].max() - timedelta(days=365)]
    yr_high = float(one_year["high"].max())
    yr_low = float(one_year["low"].min())
    pct_of_52w_range = (last_close - yr_low) / (yr_high - yr_low) * 100

    # MACD cross definitions
    macd_bullish_cross = bool(
        latest["macd"] > latest["macd_signal"] and stock.iloc[-2]["macd"] <= stock.iloc[-2]["macd_signal"]
    )
    macd_bearish_cross = bool(
        latest["macd"] < latest["macd_signal"] and stock.iloc[-2]["macd"] >= stock.iloc[-2]["macd_signal"]
    )
    macd_above_signal = bool(latest["macd"] > latest["macd_signal"])

    result = {
        "ticker": ticker,
        "analysis_date": session_date,
        "agent": 4,
        "agent_role": "technical_analysis",
        "data_source": "yfinance",
        "history_period": args.period,
        "interval": "1d",
        "last_price": round(last_close, 2),
        "latest_snapshot": latest_snapshot,
        "trend": trend,
        "moving_averages": {
            "ma_20": round(float(latest["ma_20"]), 2),
            "ma_50": round(float(latest["ma_50"]), 2),
            "ma_100": round(float(latest["ma_100"]), 2),
            "ma_200": round(float(latest["ma_200"]), 2),
            "slope_ma20_pct": round((latest["ma_20"] / stock.iloc[-21]["ma_20"] - 1) * 100, 2) if len(stock) >= 21 and not pd.isna(stock.iloc[-21]["ma_20"]) else None,
            "slope_ma50_pct": round((latest["ma_50"] / stock.iloc[-51]["ma_50"] - 1) * 100, 2) if len(stock) >= 51 and not pd.isna(stock.iloc[-51]["ma_50"]) else None,
        },
        "momentum": {
            "rsi_14": round(float(latest["rsi_14"]), 2),
            "rsi_signal": "oversold" if latest["rsi_14"] < 30 else ("overbought" if latest["rsi_14"] > 70 else "neutral"),
            "macd": round(float(latest["macd"]), 3),
            "macd_signal": round(float(latest["macd_signal"]), 3),
            "macd_hist": round(float(latest["macd_hist"]), 3),
            "macd_above_signal": macd_above_signal,
            "macd_bullish_crossover": macd_bullish_cross,
            "macd_bearish_crossover": macd_bearish_cross,
        },
        "volatility": {
            "atr_14": round(latest_atr, 2),
            "atr_pct_of_price": round(latest_atr / last_close * 100, 2),
            "bollinger_upper": round(float(latest["bb_upper"]), 2),
            "bollinger_lower": round(float(latest["bb_lower"]), 2),
            "bollinger_pct_b": round(float(latest["bb_pct_b"]), 3),
            "bollinger_signal": "near_upper_band" if latest["bb_pct_b"] > 0.9 else ("near_lower_band" if latest["bb_pct_b"] < 0.1 else "mid_range"),
        },
        "support_resistance": pivots,
        "drawdown": dd,
        "relative_strength": {
            "vs_sp500": rs_sp500,
            "vs_nasdaq100": rs_ndx,
            f"vs_{args.sector_etf.lower()}": rs_sector,
        },
        "volume": vol,
        "range": {
            "52w_high": round(yr_high, 2),
            "52w_low": round(yr_low, 2),
            "pct_of_52w_range": round(pct_of_52w_range, 1),
        },
        "trade_levels": levels,
        "position_sizing": sizing,
        "metadata": {
            "rows_analyzed": len(stock),
            "start_date": str(stock.iloc[0]["date"].date()),
            "end_date": str(stock.iloc[-1]["date"].date()),
            "calculation_notes": [
                "Moving averages are simple moving averages with full-window requirements (no partial early values).",
                "RSI(14) uses Wilder's smoothing.",
                "MACD uses EMA(12,26) with signal EMA(9).",
                "ATR(14) uses Wilder's smoothing on true range.",
                "Bollinger Bands use 20-day SMA +/- 2 standard deviations.",
                "Support/resistance pivots identified from 5-day local extrema in last 12 months, clustered within 2%, filtered below/above current price.",
                "Relative strength computed as stock close / benchmark close, then compared to moving averages.",
                "Trade levels use the preferred entry price for stop-loss and risk/R/R calculations; stop_loss is always below the entry zone.",
            ],
        },
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Saved technical analysis to {output_path}")


if __name__ == "__main__":
    main()
