#!/usr/bin/env python3
"""Agent 4: Technical analysis for ADBE. Pure price/volume analysis."""
import json
import math
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

TICKER = "ADBE"
OUTPUT_PATH = "/workspace-stock-research/ADBE/2026-07-20/registry/technical.json"


def fetch_history(ticker, period="2y", interval="1d"):
    """Fetch daily history from yfinance."""
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
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


def add_moving_averages(df):
    for window in [20, 50, 100, 200]:
        df[f"ma_{window}"] = df["close"].rolling(window=window, min_periods=1).mean()
    return df


def add_rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["rsi_14"] = 100 - (100 / (1 + rs))
    return df


def add_macd(df, fast=12, slow=26, signal=9):
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df


def add_atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr_14"] = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return df


def add_bollinger(df, window=20, num_std=2):
    df["bb_middle"] = df["close"].rolling(window=window, min_periods=1).mean()
    df["bb_std"] = df["close"].rolling(window=window, min_periods=1).std(ddof=0)
    df["bb_upper"] = df["bb_middle"] + num_std * df["bb_std"]
    df["bb_lower"] = df["bb_middle"] - num_std * df["bb_std"]
    df["bb_pct_b"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
    return df


def find_pivots(df, current_price, lookback_days=360, min_touches=2, proximity_pct=0.02):
    """Find support/resistance levels from local highs/lows over the last N days.

    Support = clustered local lows below current price.
    Resistance = clustered local highs above current price.
    """
    recent = df[df["date"] >= df["date"].max() - timedelta(days=lookback_days)].copy()
    if recent.empty:
        return {"support_levels": [], "resistance_levels": []}

    # Local minima/maxima using a 5-day centered window
    window = 5
    recent["local_min"] = recent["low"].rolling(window=window, center=True).min() == recent["low"]
    recent["local_max"] = recent["high"].rolling(window=window, center=True).max() == recent["high"]

    support_candidates = recent.loc[recent["local_min"], "low"].tolist()
    resistance_candidates = recent.loc[recent["local_max"], "high"].tolist()

    def cluster_levels(levels):
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

    # Filter to levels with at least min_touches (count close approach)
    def count_touches(level):
        return ((recent["low"] <= level * (1 + proximity_pct)) &
                (recent["high"] >= level * (1 - proximity_pct))).sum()

    support = [lvl for lvl in support if count_touches(lvl) >= min_touches and lvl < current_price]
    resistance = [lvl for lvl in resistance if count_touches(lvl) >= min_touches and lvl > current_price]

    return {
        "support_levels": sorted([round(float(x), 2) for x in support])[-5:],
        "resistance_levels": sorted([round(float(x), 2) for x in resistance])[:5]
    }


def max_drawdown(df):
    cummax = df["close"].cummax()
    drawdown = (df["close"] - cummax) / cummax
    max_dd_idx = drawdown.idxmin()
    peak_idx = cummax.loc[:max_dd_idx].idxmax()
    return {
        "max_drawdown_pct": round(drawdown.min() * 100, 2),
        "peak_date": str(df.loc[peak_idx, "date"].date()),
        "trough_date": str(df.loc[max_dd_idx, "date"].date()),
        "peak_price": round(float(df.loc[peak_idx, "close"]), 2),
        "trough_price": round(float(df.loc[max_dd_idx, "close"]), 2)
    }


def relative_strength(df_stock, df_bench):
    """Compute relative strength ratio and its trend."""
    merged = pd.merge(df_stock[["date", "close"]], df_bench[["date", "close"]], on="date", suffixes=("_stock", "_bench"))
    merged["rs_ratio"] = merged["close_stock"] / merged["close_bench"]
    latest = merged.iloc[-1]
    rs_20d = merged["rs_ratio"].rolling(20).mean().iloc[-1]
    rs_50d = merged["rs_ratio"].rolling(50).mean().iloc[-1]
    rs_1m_change = (latest["rs_ratio"] / merged["rs_ratio"].iloc[-22] - 1) * 100 if len(merged) >= 22 else None
    rs_3m_change = (latest["rs_ratio"] / merged["rs_ratio"].iloc[-66] - 1) * 100 if len(merged) >= 66 else None
    return {
        "current_rs_ratio": round(float(latest["rs_ratio"]), 6),
        "rs_20d_ma": round(float(rs_20d), 6) if not pd.isna(rs_20d) else None,
        "rs_50d_ma": round(float(rs_50d), 6) if not pd.isna(rs_50d) else None,
        "rs_1m_change_pct": round(float(rs_1m_change), 2) if rs_1m_change is not None else None,
        "rs_3m_change_pct": round(float(rs_3m_change), 2) if rs_3m_change is not None else None,
        "vs_moving_average": "above" if latest["rs_ratio"] > rs_50d else "below"
    }


def volume_trends(df):
    df["volume_ma_20"] = df["volume"].rolling(20).mean()
    df["volume_ma_50"] = df["volume"].rolling(50).mean()
    latest = df.iloc[-1]
    recent = df.tail(20)
    return {
        "latest_volume": int(latest["volume"]),
        "volume_20d_avg": int(latest["volume_ma_20"]),
        "volume_50d_avg": int(latest["volume_ma_50"]),
        "volume_vs_20d_avg_pct": round((latest["volume"] / latest["volume_ma_20"] - 1) * 100, 1) if latest["volume_ma_20"] > 0 else None,
        "volume_vs_50d_avg_pct": round((latest["volume"] / latest["volume_ma_50"] - 1) * 100, 1) if latest["volume_ma_50"] > 0 else None,
        "avg_daily_volume_20d": int(recent["volume"].mean()),
        "price_volume_trend_20d": round(np.corrcoef(recent["close"], recent["volume"])[0, 1], 3) if len(recent) >= 2 else None
    }


def determine_trend(df):
    latest = df.iloc[-1]
    price = latest["close"]
    ma20, ma50, ma100, ma200 = latest["ma_20"], latest["ma_50"], latest["ma_100"], latest["ma_200"]
    
    alignment = int(sum([
        bool(price > ma20),
        bool(ma20 > ma50),
        bool(ma50 > ma100),
        bool(ma100 > ma200)
    ]))
    
    if alignment == 4:
        trend = "strong_uptrend"
    elif alignment >= 2:
        trend = "uptrend"
    elif alignment == 0:
        trend = "strong_downtrend"
    else:
        trend = "downtrend"
    
    golden_cross = bool(ma50 > ma200)
    death_cross = bool(ma50 < ma200)
    
    return {
        "classification": trend,
        "ma_alignment_score": alignment,
        "golden_cross": bool(golden_cross),
        "death_cross": bool(death_cross),
        "price_above_200d_ma": bool(price > ma200),
        "price_above_50d_ma": bool(price > ma50)
    }


def generate_levels(df, pivots, latest_atr):
    """Generate concrete entry, exit, stop-loss, and target levels."""
    last_close = float(df.iloc[-1]["close"])
    support_levels = pivots.get("support_levels", [])
    resistance_levels = pivots.get("resistance_levels", [])

    # Stop loss: 2x ATR below last close, floored at nearest support (or 1% below it)
    atr_stop = last_close - 2 * latest_atr
    nearest_support = max([s for s in support_levels if s < last_close], default=atr_stop)
    stop_loss = max(atr_stop, nearest_support * 0.99)
    stop_loss = min(stop_loss, last_close * 0.95)  # cap stop at no more than 5% below price

    # Entry: prefer pullbacks to 20-day MA or nearest support
    entry_pullback = float(df.iloc[-1]["ma_20"])
    entry_zone_low = min(entry_pullback, nearest_support, last_close * 0.97)
    entry_zone_high = last_close

    # Risk and reward targets
    risk = last_close - stop_loss
    reward_target_2r = last_close + 2 * risk
    reward_target_3r = last_close + 3 * risk
    nearest_resistance = min([r for r in resistance_levels if r > last_close], default=reward_target_3r)

    # Primary target: 2:1 reward/risk. If nearest resistance is beyond 2R, use it as secondary.
    take_profit_1 = reward_target_2r
    take_profit_2 = min(nearest_resistance, reward_target_3r) if nearest_resistance > reward_target_2r else reward_target_3r
    take_profit_1 = max(take_profit_1, last_close * 1.02)  # ensure target is at least 2% above entry

    return {
        "last_close": round(last_close, 2),
        "entry_zone": {
            "low": round(min(entry_zone_low, last_close * 0.98), 2),
            "high": round(entry_zone_high, 2),
            "preferred": round(entry_pullback, 2),
            "rationale": "Pullback to 20-day MA or nearest support"
        },
        "stop_loss": round(stop_loss, 2),
        "take_profit_1": round(take_profit_1, 2),
        "take_profit_2": round(take_profit_2, 2),
        "risk_per_share": round(risk, 2),
        "reward_risk_ratio_tp1": round((take_profit_1 - last_close) / risk, 2) if risk > 0 else None,
        "reward_risk_ratio_tp2": round((take_profit_2 - last_close) / risk, 2) if risk > 0 else None
    }


def atr_position_sizing(actual_stop_distance, actual_risk_per_share, last_close, latest_atr,
                         account_risk_pct=0.02, stop_multiplier=2.0):
    """Return ATR-based position sizing inputs using the actual trade stop."""
    risk_per_share_pct = actual_risk_per_share / last_close
    return {
        "account_risk_pct": account_risk_pct,
        "stop_distance_atr_multiple": stop_multiplier,
        "atr_14": round(latest_atr, 2),
        "stop_distance_usd": round(actual_stop_distance, 2),
        "risk_per_share_pct": round(risk_per_share_pct * 100, 2),
        "position_size_per_10k_account": round((10000 * account_risk_pct) / actual_risk_per_share, 3),
        "position_size_per_100k_account": round((100000 * account_risk_pct) / actual_risk_per_share, 3),
        "max_position_pct_of_account_at_risk": round(account_risk_pct * 100, 1),
        "note": "Size position so that if stop is hit, loss equals account_risk_pct of capital. Stop distance reflects the actual stop_loss level in trade_levels."
    }


def main():
    print("Fetching ADBE history...")
    adbe = fetch_history(TICKER)
    print(f"ADBE rows: {len(adbe)}")
    
    print("Fetching benchmark histories...")
    gspc = fetch_history("^GSPC")
    ndx = fetch_history("^NDX")
    print(f"^GSPC rows: {len(gspc)}, ^NDX rows: {len(ndx)}")
    
    adbe = add_moving_averages(adbe)
    adbe = add_rsi(adbe)
    adbe = add_macd(adbe)
    adbe = add_atr(adbe)
    adbe = add_bollinger(adbe)

    latest = adbe.iloc[-1]
    latest_atr = float(latest["atr_14"])
    last_close = float(latest["close"])

    pivots = find_pivots(adbe, current_price=last_close, lookback_days=360, min_touches=2)
    dd = max_drawdown(adbe)
    rs_sp500 = relative_strength(adbe, gspc)
    rs_ndx = relative_strength(adbe, ndx)
    vol = volume_trends(adbe)
    trend = determine_trend(adbe)
    
    levels = generate_levels(adbe, pivots, latest_atr)
    sizing = atr_position_sizing(
        actual_stop_distance=last_close - levels["stop_loss"],
        actual_risk_per_share=levels["risk_per_share"],
        last_close=last_close,
        latest_atr=latest_atr
    )
    
    # Latest indicator snapshot
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
        "bb_pct_b": round(float(latest["bb_pct_b"]), 3)
    }
    
    # 52-week range
    one_year = adbe[adbe["date"] >= adbe["date"].max() - timedelta(days=365)]
    yr_high = float(one_year["high"].max())
    yr_low = float(one_year["low"].min())
    pct_of_52w_range = (last_close - yr_low) / (yr_high - yr_low) * 100
    
    result = {
        "ticker": TICKER,
        "analysis_date": "2026-07-20",
        "agent": 4,
        "agent_role": "technical_analysis",
        "data_source": "yfinance",
        "history_period": "2y",
        "interval": "1d",
        "last_price": round(last_close, 2),
        "latest_snapshot": latest_snapshot,
        "trend": trend,
        "moving_averages": {
            "ma_20": round(float(latest["ma_20"]), 2),
            "ma_50": round(float(latest["ma_50"]), 2),
            "ma_100": round(float(latest["ma_100"]), 2),
            "ma_200": round(float(latest["ma_200"]), 2),
            "slope_ma20_pct": round((latest["ma_20"] / adbe.iloc[-21]["ma_20"] - 1) * 100, 2) if len(adbe) >= 21 else None,
            "slope_ma50_pct": round((latest["ma_50"] / adbe.iloc[-51]["ma_50"] - 1) * 100, 2) if len(adbe) >= 51 else None
        },
        "momentum": {
            "rsi_14": round(float(latest["rsi_14"]), 2),
            "rsi_signal": "oversold" if latest["rsi_14"] < 30 else ("overbought" if latest["rsi_14"] > 70 else "neutral"),
            "macd": round(float(latest["macd"]), 3),
            "macd_signal": round(float(latest["macd_signal"]), 3),
            "macd_hist": round(float(latest["macd_hist"]), 3),
            "macd_bullish_crossover": bool(latest["macd"] > latest["macd_signal"] and adbe.iloc[-2]["macd"] <= adbe.iloc[-2]["macd_signal"])
        },
        "volatility": {
            "atr_14": round(latest_atr, 2),
            "atr_pct_of_price": round(latest_atr / last_close * 100, 2),
            "bollinger_upper": round(float(latest["bb_upper"]), 2),
            "bollinger_lower": round(float(latest["bb_lower"]), 2),
            "bollinger_pct_b": round(float(latest["bb_pct_b"]), 3),
            "bollinger_signal": "near_upper_band" if latest["bb_pct_b"] > 0.9 else ("near_lower_band" if latest["bb_pct_b"] < 0.1 else "mid_range")
        },
        "support_resistance": pivots,
        "drawdown": dd,
        "relative_strength": {
            "vs_sp500": rs_sp500,
            "vs_nasdaq100": rs_ndx
        },
        "volume": vol,
        "range": {
            "52w_high": round(yr_high, 2),
            "52w_low": round(yr_low, 2),
            "pct_of_52w_range": round(pct_of_52w_range, 1)
        },
        "trade_levels": levels,
        "position_sizing": sizing,
        "metadata": {
            "rows_analyzed": len(adbe),
            "start_date": str(adbe.iloc[0]["date"].date()),
            "end_date": str(adbe.iloc[-1]["date"].date()),
            "calculation_notes": [
                "Moving averages are simple moving averages.",
                "RSI(14) uses Wilder's smoothing.",
                "MACD uses EMA(12,26) with signal EMA(9).",
                "ATR(14) uses Wilder's smoothing on true range.",
                "Bollinger Bands use 20-day SMA +/- 2 standard deviations.",
                "Support/resistance pivots identified from 5-day local extrema in last 12 months, clustered within 2%, filtered below/above current price.",
                "Relative strength computed as stock close / benchmark close, then compared to moving averages."
            ]
        }
    }
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Saved technical analysis to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
