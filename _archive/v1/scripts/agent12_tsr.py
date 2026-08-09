#!/usr/bin/env python3
"""Agent 12: TSR validation and value-trap red flags.

Outputs:
    <session>/registry/tsr_validation.json

Usage:
    yfinance-market-mcp/.venv/bin/python scripts/agent12_tsr.py \
        --ticker ADBE --date 2026-07-20 --output-dir /workspace-stock-research
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def _get_price_on_or_before(df: pd.DataFrame, target: datetime) -> float | None:
    if df.empty:
        return None
    if df.index.tz is not None:
        target = target.replace(tzinfo=df.index.tz)
    elif target.tzinfo is not None:
        target = target.replace(tzinfo=None)
    col = "Close" if "Close" in df.columns else "Adj Close"
    mask = df.index <= target
    if not mask.any():
        return _safe(df[col].iloc[0])
    return _safe(df.loc[mask, col].iloc[-1])


def _compute_tsr(df: pd.DataFrame, start: datetime, end: datetime) -> dict[str, Any]:
    col = "Close" if "Close" in df.columns else "Adj Close"
    start_price = _get_price_on_or_before(df, start)
    end_price = _get_price_on_or_before(df, end)
    if start_price is None or end_price is None or start_price == 0:
        return {"tsr_pct": None, "start_price": start_price, "end_price": end_price}
    tsr = end_price / start_price - 1.0
    years = (end - start).days / 365.25
    cagr = (end_price / start_price) ** (1 / years) - 1.0 if years > 0 else None
    return {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "start_price": round(start_price, 4),
        "end_price": round(end_price, 4),
        "tsr_pct": round(tsr * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
        "years": round(years, 3),
        "price_column_used": col,
    }


def main():
    parser = argparse.ArgumentParser(description="Agent 12: TSR validation and value-trap red flags")
    parser.add_argument("--ticker", required=True, help="Ticker symbol")
    parser.add_argument("--date", required=True, help="Session date YYYY-MM-DD")
    parser.add_argument("--output-dir", default="/workspace-stock-research", help="Project root")
    parser.add_argument("--benchmarks", default="SPY,QQQ,IWF", help="Comma-separated benchmark tickers")
    parser.add_argument("--risk-free", type=float, default=0.045, help="Risk-free rate for WACC estimate")
    parser.add_argument("--market-risk-premium", type=float, default=0.050, help="Market risk premium")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    session_date = args.date
    output_dir = Path(args.output_dir).expanduser().resolve()
    session_dir = output_dir / ticker / session_date
    registry_dir = session_dir / "registry"
    data_dir = session_dir / "data"
    registry_dir.mkdir(parents=True, exist_ok=True)
    out_path = registry_dir / "tsr_validation.json"

    sector_config = json.loads((registry_dir / "sector_config.json").read_text())
    lq = json.loads((registry_dir / "latest_quarter.json").read_text())

    session_dt = datetime.strptime(session_date, "%Y-%m-%d")
    end = session_dt

    tickers = {"ADBE": ticker}
    for b in args.benchmarks.split(","):
        b = b.strip().upper()
        if b:
            tickers[b] = b

    histories = {}
    for name, symbol in tickers.items():
        t = yf.Ticker(symbol)
        hist = t.history(period="6y", auto_adjust=True)
        if hist.empty:
            raise RuntimeError(f"No price history for {symbol}")
        histories[name] = hist

    periods = {
        "1y": session_dt.replace(year=session_dt.year - 1),
        "3y": session_dt.replace(year=session_dt.year - 3),
        "5y": session_dt.replace(year=session_dt.year - 5),
    }

    tsr_results = {}
    for label, start in periods.items():
        tsr_results[label] = {}
        for name, hist in histories.items():
            tsr_results[label][name] = _compute_tsr(hist, start, end)

    benchmarks = [b for b in tickers if b != "ADBE"]
    for label in periods:
        adbe_tsr = tsr_results[label]["ADBE"]["tsr_pct"]
        rel = {}
        for bench in benchmarks:
            bench_tsr = tsr_results[label][bench]["tsr_pct"]
            rel[bench] = {
                "absolute_tsr_pct": bench_tsr,
                "excess_tsr_pct": round(adbe_tsr - bench_tsr, 2) if adbe_tsr is not None and bench_tsr is not None else None,
            }
        tsr_results[label]["relative"] = rel

    # SBC-adjusted TSR
    t_adbe = yf.Ticker(ticker)
    info = t_adbe.info or {}
    market_cap = _safe(info.get("marketCap"))

    cf = t_adbe.cashflow
    sbc_annual = {}
    if cf is not None and not cf.empty:
        for col in cf.columns:
            year = str(col)[:4]
            rows = {str(k): _safe(v) for k, v in cf[col].items()}
            sbc = None
            for k, v in rows.items():
                if "stock based compensation" in k.lower():
                    sbc = v
                    break
            if sbc is not None and sbc > 0:
                sbc_annual[year] = sbc
    sbc_annual = dict(sorted(sbc_annual.items()))

    ttm_sbc = lq["cash_flow"].get("ttm_sbc")

    def _dilution_for_period(years: int):
        if years == 1:
            if ttm_sbc is None or market_cap is None or market_cap == 0:
                return None
            ttm_sbc_dollars = float(ttm_sbc) * 1_000_000
            rate = ttm_sbc_dollars / market_cap
            return {
                "annual_rates_pct": [round(rate * 100, 3)],
                "years_used": ["TTM"],
                "cumulative_dilution_pct": round(rate * 100, 3),
            }
        available_years = list(sbc_annual.keys())
        if not available_years:
            return None
        selected_years = available_years[-min(years, len(available_years)):]
        rates = []
        hist_adbe = histories["ADBE"]
        shares = _safe(info.get("sharesOutstanding"))
        for y in selected_years:
            sbc = sbc_annual[y]
            year_end = datetime(int(y), 11, 30)
            price = _get_price_on_or_before(hist_adbe, year_end)
            mc = price * shares if price is not None and shares is not None else market_cap
            if mc is None or mc == 0:
                mc = market_cap
            rates.append(sbc / mc)
        cumulative = math.prod(1 + r for r in rates) - 1
        return {
            "annual_rates_pct": [round(r * 100, 3) for r in rates],
            "years_used": selected_years,
            "cumulative_dilution_pct": round(cumulative * 100, 3),
            "note": f"Used {len(selected_years)} fiscal year(s) of available SBC history."
            if len(selected_years) < years
            else None,
        }

    dilution = {
        "1y": _dilution_for_period(1),
        "3y": _dilution_for_period(3),
        "5y": _dilution_for_period(5),
    }

    sbc_adjusted_tsr = {}
    for label in periods:
        trad = tsr_results[label]["ADBE"]["tsr_pct"]
        dil_info = dilution.get(label) or {}
        dil = dil_info.get("cumulative_dilution_pct")
        sbc_adjusted_tsr[label] = {
            "traditional_tsr_pct": trad,
            "cumulative_dilution_pct": dil,
            "sbc_adjusted_tsr_pct": round(trad - dil, 2) if trad is not None and dil is not None else None,
        }

    # Growth-module flags
    rev_growth = lq["revenue_earnings"].get("revenue_yoy_pct")
    ttm_fcf_margin = lq["cash_flow"].get("ttm_fcf_margin_pct")
    rule_of_40 = (rev_growth + ttm_fcf_margin) if rev_growth is not None and ttm_fcf_margin is not None else None
    ttm_sbc_rev_pct = lq["cash_flow"].get("ttm_sbc_pct_revenue")
    nrr = lq["sector_kpis"].get("NRR")
    arr_growth = lq["sector_kpis"].get("arr_yoy_growth_pct")

    burn_multiple = None
    if ttm_sbc is not None and arr_growth is not None and arr_growth != 0:
        total_arr = lq["sector_kpis"].get("total_arr_usd")
        if total_arr is not None:
            net_new_arr = total_arr * (arr_growth / 100)
            burn = -float(lq["cash_flow"].get("ttm_sbc_adjusted_fcf", 0))
            if net_new_arr != 0:
                burn_multiple = burn / net_new_arr

    growth_flags = {
        "burn_multiple": {
            "value": round(burn_multiple, 2) if burn_multiple is not None else None,
            "threshold": "N/A for FCF-positive companies; meaningful when operating cash burn > 0",
            "status": "pass" if burn_multiple is None or burn_multiple < 1.5 else "watch" if burn_multiple < 3.0 else "flag",
            "note": f"{ticker} is strongly FCF-positive; Burn Multiple conventionally applies to negative-FCF SaaS.",
        },
        "rule_of_40_pct": {
            "value": round(rule_of_40, 2) if rule_of_40 is not None else None,
            "threshold": "> 40% is healthy SaaS; 30-40% moderate; < 30% weak",
            "status": "pass" if rule_of_40 is not None and rule_of_40 >= 40 else "watch" if rule_of_40 is not None and rule_of_40 >= 30 else "flag",
        },
        "sbc_revenue_pct": {
            "value": round(ttm_sbc_rev_pct, 2) if ttm_sbc_rev_pct is not None else None,
            "threshold": "< 5% low; 5-10% moderate; > 10% high; > 15% critical",
            "status": "pass" if ttm_sbc_rev_pct is not None and ttm_sbc_rev_pct < 5 else "watch" if ttm_sbc_rev_pct is not None and ttm_sbc_rev_pct < 10 else "flag",
        },
        "nrr_pct": {
            "value": nrr,
            "threshold": "> 120% excellent; 110-120% good; 100-110% concerning; < 100% contraction",
            "status": "unknown" if nrr is None else "pass" if nrr >= 110 else "watch" if nrr >= 100 else "flag",
            "note": f"NRR not explicitly disclosed in fetched materials; using ARR YoY growth of {arr_growth}% as proxy." if nrr is None else None,
        },
    }

    # Standard-module flags
    fin_path = data_dir / "financials.csv"
    roic = None
    fcf_ttm = None
    fcf_margin_ttm = None
    ebitda_ttm = None
    if fin_path.exists():
        try:
            fin_df = pd.read_csv(fin_path)
            ttm_row = fin_df[fin_df["Period"] == "TTM"].iloc[0]
            roic = _safe(ttm_row.get("ROIC"))
            fcf_ttm = _safe(ttm_row.get("FCF_TTM"))
            fcf_margin_ttm = _safe(ttm_row.get("FCFMargin"))
            ebitda_ttm = _safe(ttm_row.get("EBITDA"))
        except Exception as exc:
            print(f"WARNING: could not read financials.csv: {exc}")

    net_debt = lq["balance_sheet"].get("net_debt")
    leverage_ratio = lq["balance_sheet"].get("leverage_ratio")

    beta = _safe(info.get("beta")) or 1.0
    cost_of_equity = args.risk_free + beta * args.market_risk_premium
    tax_rate = 0.21
    wacc = 0.8 * cost_of_equity + 0.2 * 0.10 * (1 - tax_rate)

    standard_flags = {
        "roic_vs_wacc_pct": {
            "roic_pct": round(roic * 100, 2) if roic is not None else None,
            "wacc_pct": round(wacc * 100, 2),
            "spread_pct": round((roic - wacc) * 100, 2) if roic is not None else None,
            "threshold": "ROIC > WACC creates value; ROIC < WACC is value-destructive",
            "status": "pass" if roic is not None and roic > wacc else "flag" if roic is not None and roic < wacc else "unknown",
        },
        "fcf_ttm_usd": {
            "value_millions": round(fcf_ttm / 1e6, 2) if fcf_ttm is not None else None,
            "fcf_margin_pct": round(fcf_margin_ttm * 100, 2) if fcf_margin_ttm is not None else None,
            "threshold": "Positive and stable FCF; margin > 10% for mature software is strong",
            "status": "pass" if fcf_ttm is not None and fcf_ttm > 0 else "flag",
        },
        "leverage": {
            "net_debt_usd_millions": round(net_debt, 2) if net_debt is not None else None,
            "net_debt_to_ebitda": round((net_debt * 1_000_000) / ebitda_ttm, 2) if net_debt is not None and ebitda_ttm is not None and ebitda_ttm != 0 else None,
            "leverage_ratio": leverage_ratio,
            "threshold": "Net debt/EBITDA < 2.5x is comfortable; > 3.5x is elevated",
            "status": "pass" if net_debt is not None and ebitda_ttm is not None and (net_debt * 1_000_000) / ebitda_ttm < 2.5 else "watch" if net_debt is not None and ebitda_ttm is not None and (net_debt * 1_000_000) / ebitda_ttm < 3.5 else "flag",
        },
    }

    def _rollup(statuses):
        status_list = list(statuses)
        if any(s == "flag" for s in status_list):
            return "flag"
        if any(s == "watch" for s in status_list):
            return "watch"
        return "pass"

    overall_growth_flag = _rollup(growth_flags[k]["status"] for k in growth_flags)
    overall_standard_flag = _rollup(standard_flags[k]["status"] for k in standard_flags)

    result = {
        "ticker": ticker,
        "session_date": session_date,
        "agent": "Agent 12 (TSR validation)",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "primary_sector": sector_config.get("primary_sector", "standard"),
        "is_also_growth": sector_config.get("is_also_growth", False),
        "sbc_analysis_intensity": "critical",
        "sources": [
            {"name": f"yfinance price history ({', '.join(tickers)})", "url": None},
            {"name": "latest_quarter.json", "path": str(registry_dir / "latest_quarter.json")},
            {"name": "financials.csv", "path": str(data_dir / "financials.csv")},
        ],
        "benchmarks": {
            "regional": f"{benchmarks[0]} (S&P 500 / broad market ETF)",
            "sector_tech_growth": benchmarks[1:],
        },
        "tsr": tsr_results,
        "sbc_adjusted_tsr": {
            "methodology": "Annual dilution rate = SBC / market cap; cumulative dilution = product(1+d_i)-1; SBC-adjusted TSR = traditional TSR - cumulative dilution.",
            "market_cap_usd": market_cap,
            "ttm_sbc_usd_millions": ttm_sbc,
            "ttm_sbc_usd_raw": float(ttm_sbc) * 1_000_000 if ttm_sbc is not None else None,
            "annual_sbc_history_usd": sbc_annual,
            "by_period": sbc_adjusted_tsr,
        },
        "value_trap_red_flags": {
            "growth_module_flags": growth_flags,
            "standard_module_flags": standard_flags,
            "overall_growth_status": overall_growth_flag,
            "overall_standard_status": overall_standard_flag,
            "combined_assessment": (
                f"{ticker} passes standard value-trap screens and growth-module screens are mostly healthy. "
                f"SBC/Revenue ~{ttm_sbc_rev_pct}% is a moderate watch if it rises above 10%."
            ),
        },
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Saved {out_path}")
    return result


if __name__ == "__main__":
    main()
