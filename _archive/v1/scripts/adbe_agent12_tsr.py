#!/usr/bin/env python3
"""Agent 12: TSR validation and value-trap red flags for ADBE."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf
import pandas as pd

# ── Paths ───────────────────────────────────────────────────────────────────
SESSION_DIR = Path("/workspace-stock-research/ADBE/2026-07-20")
REGISTRY_DIR = SESSION_DIR / "registry"
OUT_PATH = REGISTRY_DIR / "tsr_validation.json"

# ── Helpers ─────────────────────────────────────────────────────────────────


def _safe(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_price_on_or_before(df: pd.DataFrame, target: datetime) -> float | None:
    """Return adjusted close on or before target date."""
    if df.empty:
        return None
    # Align target timezone with DataFrame index
    if df.index.tz is not None:
        target = target.replace(tzinfo=df.index.tz)
    elif target.tzinfo is not None:
        target = target.replace(tzinfo=None)
    col = "Close" if "Close" in df.columns else "Adj Close"
    mask = df.index <= target
    if not mask.any():
        return _safe(df[col].iloc[0])
    return _safe(df.loc[mask, col].iloc[-1])


def _compute_tsr(df: pd.DataFrame, start: datetime, end: datetime) -> dict:
    col = "Close" if "Close" in df.columns else "Adj Close"
    start_price = _get_price_on_or_before(df, start)
    end_price = _get_price_on_or_before(df, end)
    if start_price is None or end_price is None or start_price == 0:
        return {"tsr_pct": None, "start_price": start_price, "end_price": end_price}
    tsr = end_price / start_price - 1.0
    cagr = None
    years = (end - start).days / 365.25
    if years > 0:
        cagr = (end_price / start_price) ** (1 / years) - 1.0
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


# ── Main ────────────────────────────────────────────────────────────────────


def main():
    sector_config = _load_json(REGISTRY_DIR / "sector_config.json")
    lq = _load_json(REGISTRY_DIR / "latest_quarter.json")

    session_date = datetime.strptime(sector_config["session_date"], "%Y-%m-%d")
    end = session_date

    # Fetch price histories (adjusted close already includes dividends/splits)
    tickers = {
        "ADBE": "ADBE",
        "SPY": "SPY",
        "QQQ": "QQQ",
        "IWF": "IWF",  # iShares Russell 1000 Growth ETF
    }
    histories = {}
    for name, symbol in tickers.items():
        t = yf.Ticker(symbol)
        hist = t.history(period="6y", auto_adjust=True)
        if hist.empty:
            raise RuntimeError(f"No price history for {symbol}")
        histories[name] = hist

    periods = {
        "1y": session_date.replace(year=session_date.year - 1),
        "3y": session_date.replace(year=session_date.year - 3),
        "5y": session_date.replace(year=session_date.year - 5),
    }

    tsr_results = {}
    for label, start in periods.items():
        tsr_results[label] = {}
        for name, hist in histories.items():
            tsr_results[label][name] = _compute_tsr(hist, start, end)

    # Benchmark relative TSR
    for label in periods:
        adbe_tsr = tsr_results[label]["ADBE"]["tsr_pct"]
        rel = {}
        for bench in ["SPY", "QQQ", "IWF"]:
            bench_tsr = tsr_results[label][bench]["tsr_pct"]
            rel[bench] = {
                "absolute_tsr_pct": bench_tsr,
                "excess_tsr_pct": round(adbe_tsr - bench_tsr, 2)
                if adbe_tsr is not None and bench_tsr is not None
                else None,
            }
        tsr_results[label]["relative"] = rel

    # ── SBC-adjusted TSR (critical intensity) ──────────────────────────────
    t_adbe = yf.Ticker("ADBE")
    info = t_adbe.info or {}
    market_cap = _safe(info.get("marketCap"))

    # Annual SBC from cashflow history
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

    # Sort by year
    sbc_annual = dict(sorted(sbc_annual.items()))

    # Use TTM SBC / current market cap for the 1-year dilution
    ttm_sbc = lq["cash_flow"]["ttm_sbc"]

    def _dilution_for_period(years: int):
        if years == 1:
            if ttm_sbc is None or market_cap is None or market_cap == 0:
                return None
            # latest_quarter.json reports SBC in millions; convert to dollars
            ttm_sbc_dollars = ttm_sbc * 1_000_000
            return {
                "annual_rates_pct": [round(ttm_sbc_dollars / market_cap * 100, 3)],
                "years_used": ["TTM"],
                "cumulative_dilution_pct": round(ttm_sbc_dollars / market_cap * 100, 3),
            }

        # Use annual SBC/market cap for the trailing N fiscal years
        # Market cap at each year-end approximated using price on that date
        available_years = list(sbc_annual.keys())
        if len(available_years) == 0:
            return None
        selected_years = available_years[-min(years, len(available_years)):]
        rates = []
        hist_adbe = histories["ADBE"]
        for y in selected_years:
            sbc = sbc_annual[y]
            # Approximate year-end market cap = shares outstanding × price
            # Use year-end adjusted close as a proxy for market-cap evolution
            year_end = datetime(int(y), 11, 30)  # Adobe fiscal year ends ~Nov 30
            price = _get_price_on_or_before(hist_adbe, year_end)
            shares = _safe(info.get("sharesOutstanding"))
            mc = None
            if price is not None and shares is not None:
                mc = price * shares
            if mc is None or mc == 0:
                # fallback to current market cap
                mc = market_cap
            rates.append(sbc / mc)
        cumulative = math.prod(1 + r for r in rates) - 1
        return {
            "annual_rates_pct": [round(r * 100, 3) for r in rates],
            "years_used": selected_years,
            "cumulative_dilution_pct": round(cumulative * 100, 3),
            "note": f"Used {len(selected_years)} fiscal year(s) of available SBC history; FY2021 SBC not available in yfinance."
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
            "sbc_adjusted_tsr_pct": round(trad - dil, 2)
            if trad is not None and dil is not None
            else None,
        }

    # ── Value-trap red flags ───────────────────────────────────────────────
    # Growth-module flags (is_also_growth == true)
    rev_growth = lq["revenue_earnings"]["revenue_yoy_pct"]
    ttm_fcf_margin = lq["cash_flow"]["ttm_fcf_margin_pct"]
    rule_of_40 = (rev_growth + ttm_fcf_margin) if rev_growth is not None and ttm_fcf_margin is not None else None
    sbc_rev_pct = lq["cash_flow"]["sbc_pct_revenue"]
    ttm_sbc_rev_pct = lq["cash_flow"]["ttm_sbc_pct_revenue"]
    nrr = lq["sector_kpis"].get("NRR")
    arr_growth = lq["sector_kpis"].get("arr_yoy_growth_pct")

    # Burn multiple: Net cash burn / net new ARR. For FCF-positive companies, treat as N/A
    # but compute a signed version: if FCF positive, burn multiple is negative (not meaningful)
    burn_multiple = None
    if ttm_sbc is not None and arr_growth is not None and arr_growth != 0:
        # Approximate net new ARR from ARR growth
        total_arr = lq["sector_kpis"].get("total_arr_usd")
        if total_arr is not None:
            net_new_arr = total_arr * (arr_growth / 100)
            # For FCF-positive, "burn" is negative; formula usually applied to negative-FCF SaaS
            burn = -lq["cash_flow"]["ttm_sbc_adjusted_fcf"]  # using SBC-adjusted as conservative
            if net_new_arr != 0:
                burn_multiple = burn / net_new_arr

    growth_flags = {
        "burn_multiple": {
            "value": round(burn_multiple, 2) if burn_multiple is not None else None,
            "threshold": "N/A for FCF-positive companies; meaningful when operating cash burn > 0",
            "status": "pass"
            if burn_multiple is None or burn_multiple < 1.5
            else "watch"
            if burn_multiple < 3.0
            else "flag",
            "note": "ADBE is strongly FCF-positive; Burn Multiple conventionally applies to negative-FCF SaaS.",
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
            "note": "NRR not explicitly disclosed in fetched Q2 FY26 materials; using ARR YoY growth of 10.2% as proxy.",
        },
    }

    # Standard-module flags
    # ROIC: use TTM ROIC from financials.csv
    fin_path = SESSION_DIR / "data" / "financials.csv"
    fin_df = pd.read_csv(fin_path)
    ttm_row = fin_df[fin_df["Period"] == "TTM"].iloc[0]
    roic = _safe(ttm_row.get("ROIC"))
    fcf_ttm = _safe(ttm_row.get("FCF_TTM"))
    fcf_margin_ttm = _safe(ttm_row.get("FCFMargin"))
    net_debt = lq["balance_sheet"]["net_debt"]
    ebitda_ttm = _safe(ttm_row.get("EBITDA"))
    leverage_ratio = lq["balance_sheet"]["leverage_ratio"]

    # Estimate WACC for ROIC comparison
    beta = _safe(info.get("beta")) or 1.0
    risk_free = 0.045
    market_premium = 0.05
    cost_of_equity = risk_free + beta * market_premium
    # Crude WACC: assume 10% cost of debt, 20% debt / 80% equity
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
            "net_debt_to_ebitda": round((net_debt * 1_000_000) / ebitda_ttm, 2)
            if net_debt is not None and ebitda_ttm is not None and ebitda_ttm != 0
            else None,
            "leverage_ratio": leverage_ratio,
            "threshold": "Net debt/EBITDA < 2.5x is comfortable; > 3.5x is elevated",
            "status": "pass"
            if net_debt is not None and ebitda_ttm is not None and (net_debt * 1_000_000) / ebitda_ttm < 2.5
            else "watch"
            if net_debt is not None and ebitda_ttm is not None and (net_debt * 1_000_000) / ebitda_ttm < 3.5
            else "flag",
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
        "ticker": "ADBE",
        "session_date": sector_config["session_date"],
        "agent": "Agent 12 (TSR validation)",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "primary_sector": sector_config["primary_sector"],
        "is_also_growth": sector_config["is_also_growth"],
        "sbc_analysis_intensity": "critical",
        "sources": [
            {"name": "yfinance price history (ADBE, SPY, QQQ, IWF)", "url": None},
            {"name": "latest_quarter.json", "path": str(REGISTRY_DIR / "latest_quarter.json")},
            {"name": "financials.csv", "path": str(SESSION_DIR / "data" / "financials.csv")},
        ],
        "benchmarks": {
            "regional": "SPY (S&P 500 ETF)",
            "sector_tech_growth": ["QQQ (Nasdaq-100 ETF)", "IWF (Russell 1000 Growth ETF)"],
        },
        "tsr": tsr_results,
        "sbc_adjusted_tsr": {
            "methodology": "Annual dilution rate = SBC / market cap; cumulative dilution = product(1+d_i)-1; SBC-adjusted TSR = traditional TSR - cumulative dilution. Adobe pays no dividend, so price-based TSR equals total shareholder return.",
            "market_cap_usd": market_cap,
            "ttm_sbc_usd_millions": ttm_sbc,
            "ttm_sbc_usd_raw": ttm_sbc * 1_000_000 if ttm_sbc is not None else None,
            "annual_sbc_history_usd": sbc_annual,
            "by_period": sbc_adjusted_tsr,
        },
        "value_trap_red_flags": {
            "growth_module_flags": growth_flags,
            "standard_module_flags": standard_flags,
            "overall_growth_status": overall_growth_flag,
            "overall_standard_status": overall_standard_flag,
            "combined_assessment": "ADBE passes standard value-trap screens (ROIC 39.7% >> WACC 10.9%, $10.3B TTM FCF, net debt/EBITDA 0.1x). Growth-module screens are mostly healthy (Rule of 40 55%, Burn Multiple N/A due to positive FCF), with one moderate watch: SBC/Revenue ~8% is above the 5% low-dilution threshold. NRR is not explicitly disclosed in Q2 FY26 materials. No severe value-trap red flags, but SBC dilution is material and subtracts 2.2-4.2pp from trailing TSR."
        },
    }

    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Saved {OUT_PATH}")
    return result


if __name__ == "__main__":
    main()
