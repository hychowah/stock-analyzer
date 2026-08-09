#!/usr/bin/env python3
"""Agent 5 (kimi-datasource edition): Sector-aware valuation modeling.

Reads fundamentals from S&P Capital IQ via data/sp_financials.csv and the latest
quarter snapshot, computes a sector-appropriate valuation, and writes the
valuation model plus the base risk bridge.

Usage:
    /workspace-stock-research/yfinance-market-mcp/.venv/bin/python \
        scripts/agent5_kd_valuation.py --ticker AAPL --date 2026-07-25 \
        --output-dir /workspace-stock-research
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yfinance as yf

# Ensure project root is on sys.path so `scripts` package imports work.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kd_research import load_json, save_json


# ── Helpers ─────────────────────────────────────────────────────────────────


def _safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _read_sp_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _sp_series(rows: list[dict[str, Any]], item_key: str, period_type: str = "Quarterly") -> list[tuple[str, str, float]]:
    """Return (fiscal_year, fiscal_quarter, value) for an item, sorted ascending."""
    out: list[tuple[str, str, float]] = []
    for r in rows:
        if r.get("item_key") != item_key:
            continue
        if r.get("period_type") != period_type:
            continue
        v = _to_float(r.get("item_value"))
        if v is None:
            continue
        fy = r.get("fiscal_year", "")
        fq = r.get("fiscal_quarter", "")
        out.append((fy, fq, v))
    # Sort by year then quarter (treat empty quarter as 0)
    out.sort(key=lambda x: (int(x[0]) if x[0].isdigit() else 0, int(x[1]) if x[1].isdigit() else 0))
    return out


def _sp_annual(rows: list[dict[str, Any]], item_key: str) -> list[tuple[str, float]]:
    """Return (fiscal_year, value) for annual rows."""
    out: list[tuple[str, float]] = []
    for r in rows:
        if r.get("item_key") != item_key:
            continue
        if r.get("period_type") != "Annual":
            continue
        v = _to_float(r.get("item_value"))
        if v is None:
            continue
        out.append((r.get("fiscal_year", ""), v))
    out.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)
    return out


def _ttm(rows: list[dict[str, Any]], item_key: str, n: int = 4) -> float | None:
    """Sum the latest N quarterly values for an item (TTM)."""
    series = _sp_series(rows, item_key, "Quarterly")
    if len(series) < n:
        return None
    return sum(v for _, _, v in series[-n:])


def _latest_quarter_value(rows: list[dict[str, Any]], item_key: str) -> float | None:
    series = _sp_series(rows, item_key, "Quarterly")
    if not series:
        return None
    return series[-1][2]


def _latest_annual_value(rows: list[dict[str, Any]], item_key: str) -> float | None:
    series = _sp_annual(rows, item_key)
    if not series:
        return None
    return series[-1][1]


def _median(values: list[float]) -> float | None:
    clean = sorted([v for v in values if v is not None])
    if not clean:
        return None
    n = len(clean)
    if n % 2:
        return clean[n // 2]
    return (clean[n // 2 - 1] + clean[n // 2]) / 2


# ── Peer multiples ──────────────────────────────────────────────────────────


@dataclass
class PeerMultiples:
    ticker: str
    ev_ebitda: float | None
    ev_fcf: float | None
    ev_revenue: float | None


def _fetch_peer_multiples(ticker: str, peers: list[str]) -> list[PeerMultiples]:
    results: list[PeerMultiples] = []
    for sym in [ticker] + peers:
        sym = sym.upper()
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            ev = _safe(info.get("enterpriseValue"))
            ebitda = _safe(info.get("ebitda"))
            fcf = _safe(info.get("freeCashflow"))
            revenue = _safe(info.get("totalRevenue"))
            results.append(
                PeerMultiples(
                    ticker=sym,
                    ev_ebitda=(ev / ebitda) if ev and ebitda and ebitda > 0 else None,
                    ev_fcf=(ev / fcf) if ev and fcf and fcf > 0 else None,
                    ev_revenue=(ev / revenue) if ev and revenue and revenue > 0 else None,
                )
            )
        except Exception as exc:
            print(f"WARNING: could not fetch multiples for {sym}: {exc}")
            results.append(PeerMultiples(ticker=sym, ev_ebitda=None, ev_fcf=None, ev_revenue=None))
    return results


# ── DCF engine ──────────────────────────────────────────────────────────────


def _build_dcf(
    rev_growths: list[float],
    fcf_margins: list[float],
    terminal_growth: float,
    wacc: float,
    start_revenue: float,
) -> dict[str, Any]:
    """Build a year-by-year FCF DCF. start_revenue is TTM; Year 1 = start_revenue * (1+g0)."""
    years = len(rev_growths)
    assert len(fcf_margins) == years

    revenues = []
    fcfs = []
    pv_fcfs = []
    for i, (g, m) in enumerate(zip(rev_growths, fcf_margins)):
        rev = start_revenue * (1 + g) if i == 0 else revenues[-1] * (1 + g)
        fcf = rev * m
        pv = fcf / ((1 + wacc) ** (i + 1))
        revenues.append(rev)
        fcfs.append(fcf)
        pv_fcfs.append(pv)

    terminal_fcf = fcfs[-1] * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** years)
    ev = sum(pv_fcfs) + pv_terminal

    return {
        "revenues": revenues,
        "fcfs": fcfs,
        "pv_fcfs": pv_fcfs,
        "terminal_fcf": terminal_fcf,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "enterprise_value": ev,
        "pv_explicit_ratio": sum(pv_fcfs) / ev if ev else None,
    }


def _solve_implied_cagr(
    target_ev: float,
    start_rev: float,
    margin: float,
    terminal_g: float,
    wacc: float,
    years: int = 10,
) -> float:
    lo, hi = -0.10, 0.50
    for _ in range(80):
        mid = (lo + hi) / 2
        revs = [start_rev * ((1 + mid) ** (i + 1)) for i in range(years)]
        fcfs = [r * margin for r in revs]
        pv = sum(f / ((1 + wacc) ** (i + 1)) for i, f in enumerate(fcfs))
        tv = fcfs[-1] * (1 + terminal_g) / (wacc - terminal_g)
        pv_tv = tv / ((1 + wacc) ** years)
        ev = pv + pv_tv
        if ev < target_ev:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 4)


def _solve_implied_terminal_margin(
    target_ev: float,
    start_rev: float,
    cagrs: list[float],
    terminal_g: float,
    wacc: float,
    years: int = 10,
) -> float:
    lo, hi = 0.05, 0.70
    for _ in range(80):
        mid = (lo + hi) / 2
        revs = [start_rev]
        for g in cagrs:
            revs.append(revs[-1] * (1 + g))
        revs = revs[1:]
        fcfs = [r * mid for r in revs]
        pv = sum(f / ((1 + wacc) ** (i + 1)) for i, f in enumerate(fcfs))
        tv = fcfs[-1] * (1 + terminal_g) / (wacc - terminal_g)
        pv_tv = tv / ((1 + wacc) ** years)
        ev = pv + pv_tv
        if ev < target_ev:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 4)


def _solve_implied_wacc(
    target_ev: float,
    start_rev: float,
    cagrs: list[float],
    margins: list[float],
    terminal_g: float,
    years: int = 10,
) -> float:
    lo, hi = 0.03, 0.30
    for _ in range(80):
        mid = (lo + hi) / 2
        revs = [start_rev]
        for g in cagrs:
            revs.append(revs[-1] * (1 + g))
        revs = revs[1:]
        fcfs = [r * m for r, m in zip(revs, margins)]
        pv = sum(f / ((1 + mid) ** (i + 1)) for i, f in enumerate(fcfs))
        tv = fcfs[-1] * (1 + terminal_g) / (mid - terminal_g)
        pv_tv = tv / ((1 + mid) ** years)
        ev = pv + pv_tv
        if ev < target_ev:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2, 4)


# ── Sector-specific model stubs ─────────────────────────────────────────────


def _standard_growth_model(
    ticker: str,
    session_date: str,
    sector_cfg: dict[str, Any],
    lq: dict[str, Any],
    sp_rows: list[dict[str, Any]],
    info: dict[str, Any],
    t: yf.Ticker,
    peers: list[str],
    risk_free: float,
    market_risk_premium: float,
    tax_rate: float,
) -> dict[str, Any]:
    """Standard / growth SBC-adjusted FCF DCF using S&P historicals + yfinance market data."""

    price = _to_float(info.get("currentPrice")) or _to_float(info.get("regularMarketPrice")) or _to_float(info.get("previousClose"))
    shares = _to_float(info.get("sharesOutstanding"))
    market_cap = _to_float(info.get("marketCap"))
    ev = _to_float(info.get("enterpriseValue"))
    beta = _to_float(info.get("beta")) or 1.0

    # TTM figures from S&P where possible. S&P data_item_value is in millions.
    def _mm(v):
        return v * 1e6 if v is not None else None

    ttm_revenue = _mm(_ttm(sp_rows, "revenue", 4)) or _to_float(info.get("totalRevenue"))
    ttm_gross_profit = _mm(_ttm(sp_rows, "gross_profit", 4))
    ttm_operating_income = _mm(_ttm(sp_rows, "operating_income", 4))
    ttm_net_income = _mm(_ttm(sp_rows, "net_income", 4))
    ttm_ocf = _mm(_ttm(sp_rows, "cash_from_operations", 4))
    ttm_dividends = _mm(_ttm(sp_rows, "dividends_paid", 4))

    # Use yfinance for FCF / SBC / EBITDA because S&P capex/SBC items may not be in our canonical set.
    ttm_fcf = _to_float(info.get("freeCashflow"))
    ttm_ebitda = _to_float(info.get("ebitda"))
    ttm_sbc = None
    try:
        ttm_sbc = _to_float(t.cashflow.loc["Stock Based Compensation"].iloc[-1]) if "Stock Based Compensation" in t.cashflow.index else None
    except Exception:
        pass
    sbc_adj_fcf = (ttm_fcf - ttm_sbc) if ttm_fcf is not None and ttm_sbc is not None else ttm_fcf

    latest_q = lq.get("revenue_earnings", {})
    latest_margin = lq.get("margins_costs", {})

    # Margins
    gross_margin = ttm_gross_profit / ttm_revenue if ttm_gross_profit and ttm_revenue else _to_float(info.get("grossMargins"))
    operating_margin = ttm_operating_income / ttm_revenue if ttm_operating_income and ttm_revenue else _to_float(info.get("operatingMargins"))
    net_margin = ttm_net_income / ttm_revenue if ttm_net_income and ttm_revenue else _to_float(info.get("profitMargins"))
    fcf_margin = sbc_adj_fcf / ttm_revenue if sbc_adj_fcf and ttm_revenue else None

    # Balance sheet / capital structure from yfinance
    total_debt = _to_float(info.get("totalDebt")) or 0
    total_cash = _to_float(info.get("totalCash")) or _to_float(info.get("cashAndCashEquivalents")) or 0

    # WACC
    cost_of_equity = risk_free + beta * market_risk_premium
    interest_expense = None
    try:
        inc = t.income_stmt
        if inc is not None and not inc.empty and "Interest Expense" in inc.index:
            interest_expense = abs(float(inc.loc["Interest Expense"].iloc[-1]))
    except Exception:
        pass
    if interest_expense is None:
        interest_expense = abs(_to_float(info.get("interestExpense")) or 0)
    cost_of_debt = interest_expense / total_debt if interest_expense and total_debt else 0.04
    after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)
    debt_weight = total_debt / (market_cap + total_debt) if (market_cap + total_debt) else 0
    equity_weight = market_cap / (market_cap + total_debt) if (market_cap + total_debt) else 1
    wacc = equity_weight * cost_of_equity + debt_weight * after_tax_cost_of_debt

    wacc_base = round(wacc, 4)
    wacc_bear = round(wacc + 0.015, 4)
    wacc_bull = round(max(wacc - 0.005, 0.075), 4)

    # Historical revenue CAGR from S&P annuals
    annual_revs = _sp_annual(sp_rows, "revenue")
    hist_cagr = None
    if len(annual_revs) >= 2:
        start_rev = annual_revs[0][1]
        end_rev = annual_revs[-1][1]
        n = len(annual_revs) - 1
        if start_rev and start_rev > 0:
            hist_cagr = (end_rev / start_rev) ** (1 / n) - 1

    # Forecast assumptions: start from TTM revenue
    start_revenue = ttm_revenue
    base_growth = [0.06, 0.055, 0.05, 0.045, 0.04, 0.038, 0.036, 0.034, 0.032, 0.030]
    # Override Year 1 if latest-quarter guidance / trajectory suggests otherwise
    if hist_cagr is not None:
        base_growth[0] = max(min(hist_cagr, 0.12), 0.02)

    # Margins: converge from latest operating margin to a terminal margin.
    # latest_quarter.json stores percentages (0-100); yfinance info stores decimals.
    latest_op_margin = latest_margin.get("operating_margin_pct")
    if latest_op_margin is not None and latest_op_margin > 1.0:
        latest_op_margin = latest_op_margin / 100.0
    if latest_op_margin is None and operating_margin is not None:
        latest_op_margin = operating_margin
    if latest_op_margin is None:
        latest_op_margin = 0.25

    base_terminal_margin = max(latest_op_margin * 0.95, 0.18)
    base_margin = [base_terminal_margin] * 10
    # Linear interpolation from current margin to terminal
    for i in range(10):
        weight = i / 9
        base_margin[i] = latest_op_margin * (1 - weight) + base_terminal_margin * weight

    bear_growth = [g - 0.02 for g in base_growth]
    bear_margin = [m * 0.92 for m in base_margin]
    bull_growth = [g + 0.015 for g in base_growth]
    bull_margin = [min(m * 1.06, 0.45) for m in base_margin]

    base_terminal_g = 0.03
    bear_terminal_g = 0.02
    bull_terminal_g = 0.035

    years = 10
    base_dcf = _build_dcf(base_growth, base_margin, base_terminal_g, wacc_base, start_revenue)
    bear_dcf = _build_dcf(bear_growth, bear_margin, bear_terminal_g, wacc_bear, start_revenue)
    bull_dcf = _build_dcf(bull_growth, bull_margin, bull_terminal_g, wacc_bull, start_revenue)

    def ev_to_price(ev: float) -> float:
        return (ev - total_debt + total_cash) / shares if shares else 0.0

    dcf_bear_fv = ev_to_price(bear_dcf["enterprise_value"])
    dcf_base_fv = ev_to_price(base_dcf["enterprise_value"])
    dcf_bull_fv = ev_to_price(bull_dcf["enterprise_value"])

    # Relative multiples
    peer_multiples = _fetch_peer_multiples(ticker, peers)
    peer_vals = [pm for pm in peer_multiples if pm.ticker != ticker.upper()]
    median_ev_fcf = _median([pm.ev_fcf for pm in peer_vals])
    median_ev_ebitda = _median([pm.ev_ebitda for pm in peer_vals])
    median_ev_rev = _median([pm.ev_revenue for pm in peer_vals])

    # Conservative adjustments: target usually trades at a slight premium/discount vs peers
    adj_factor = 1.0
    implied_ev_fcf_multiple = (median_ev_fcf or 20.0) * adj_factor
    implied_ev_ebitda_multiple = (median_ev_ebitda or 16.0) * adj_factor
    implied_ev_rev_multiple = (median_ev_rev or 6.0) * adj_factor

    relative_ev_fcf = (sbc_adj_fcf or 0) * implied_ev_fcf_multiple
    relative_ev_ebitda = (ttm_ebitda or 0) * implied_ev_ebitda_multiple
    relative_ev_rev = (ttm_revenue or 0) * implied_ev_rev_multiple
    rel_fv = ev_to_price((relative_ev_fcf + relative_ev_ebitda + relative_ev_rev) / 3)

    # SOTP placeholder (generic; real SOTP needs segment disclosures)
    sotp = {"note": "Generic SOTP placeholder; populate from segment disclosures if material."}
    sotp_base_fv = dcf_base_fv  # fallback

    weights = {"dcf_base": 0.60, "relative": 0.30, "sotp": 0.10}
    weighted_fv = (
        dcf_base_fv * weights["dcf_base"]
        + rel_fv * weights["relative"]
        + sotp_base_fv * weights["sotp"]
    )

    # Reverse engineering
    reverse_engineering = {
        "current_ev_usd": ev,
        "current_price": price,
        "ev_fcf_sbc_adjusted": round(ev / sbc_adj_fcf, 2) if sbc_adj_fcf else None,
        "ev_ebitda": round(ev / ttm_ebitda, 2) if ttm_ebitda else None,
        "ev_revenue": round(ev / ttm_revenue, 2) if ttm_revenue else None,
        "pe_trailing": round(_to_float(info.get("trailingPE")), 2) if info.get("trailingPE") else None,
        "methodology": (
            "Solve for the single parameter that makes the 10-year SBC-adjusted FCF DCF "
            "equal current EV, holding other assumptions at base-case levels. "
            "Starting revenue is TTM revenue from S&P or yfinance."
        ),
        "implied_revenue_cagr_pct": round(
            _solve_implied_cagr(ev, start_revenue, base_margin[-1], base_terminal_g, wacc_base) * 100, 2
        ) if ev and start_revenue else None,
        "implied_terminal_fcf_margin_pct": round(
            _solve_implied_terminal_margin(ev, start_revenue, base_growth, base_terminal_g, wacc_base) * 100, 2
        ) if ev and start_revenue else None,
        "implied_wacc_pct": round(
            _solve_implied_wacc(ev, start_revenue, base_growth, base_margin, base_terminal_g) * 100, 2
        ) if ev and start_revenue else None,
        "priced_for_perfection_flag": False,
        "priced_for_perfection_rationale": "To be assessed by Agent 5 reasoning based on trajectory and peer context.",
    }

    def build_scenario_json(dcf_result: dict, growth: list[float], margins: list[float], wacc_pct: float, terminal_g: float, description: str) -> dict:
        revenues = dcf_result["revenues"]
        cagr = round(((revenues[-1] / revenues[0]) ** (1 / (years - 1)) - 1) * 100, 2) if revenues[0] else None
        return {
            "description": description,
            "wacc_pct": round(wacc_pct * 100, 2),
            "terminal_growth_pct": round(terminal_g * 100, 2),
            "revenue_cagr_pct": cagr,
            "terminal_fcf_margin_pct": round(margins[-1] * 100, 2),
            "enterprise_value_usd": dcf_result["enterprise_value"],
            "fair_value_per_share_usd": round(ev_to_price(dcf_result["enterprise_value"]), 2),
            "pv_explicit_usd": sum(dcf_result["pv_fcfs"]),
            "pv_terminal_usd": dcf_result["pv_terminal"],
            "pv_explicit_pct": round(sum(dcf_result["pv_fcfs"]) / dcf_result["enterprise_value"] * 100, 2) if dcf_result["enterprise_value"] else None,
            "forecast": [
                {
                    "year": i + 1,
                    "fiscal_year": f"FY{datetime.now().year + i}",
                    "revenue_usd": rev,
                    "sbc_adjusted_fcf_margin_pct": round(m * 100, 2),
                    "sbc_adjusted_fcf_usd": fcf,
                    "pv_fcf_usd": pv,
                }
                for i, (rev, m, fcf, pv) in enumerate(zip(
                    dcf_result["revenues"], margins, dcf_result["fcfs"], dcf_result["pv_fcfs"]
                ))
            ],
        }

    peer_multiples_json = {
        pm.ticker: {"ev_fcf": _safe(pm.ev_fcf), "ev_ebitda": _safe(pm.ev_ebitda), "ev_rev": _safe(pm.ev_revenue)}
        for pm in peer_multiples
    }

    valuation = {
        "ticker": ticker.upper(),
        "session_date": session_date,
        "agent": "Agent 5 (kimi-datasource valuation)",
        "valuation_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "primary_model": sector_cfg.get("substitutions", {}).get("valuation_model_primary", "Standard FCF-based DCF"),
        "primary_sector": sector_cfg.get("primary_sector", "standard"),
        "is_also_growth": sector_cfg.get("is_also_growth", False),
        "sbc_analysis_intensity": sector_cfg.get("substitutions", {}).get("sbc_analysis_intensity", "medium"),
        "inputs": {
            "current_price_usd": price,
            "shares_outstanding_millions": round(shares / 1e6, 2) if shares else None,
            "market_cap_usd": market_cap,
            "enterprise_value_usd": ev,
            "total_debt_usd": total_debt,
            "total_cash_usd": total_cash,
            "ttm_revenue_usd": ttm_revenue,
            "ttm_reported_fcf_usd": ttm_fcf,
            "ttm_sbc_usd": ttm_sbc,
            "ttm_sbc_adjusted_fcf_usd": sbc_adj_fcf,
            "ttm_ebitda_usd": ttm_ebitda,
            "ttm_gross_profit_usd": ttm_gross_profit,
            "ttm_operating_income_usd": ttm_operating_income,
            "ttm_net_income_usd": ttm_net_income,
            "gross_margin_pct": round(gross_margin * 100, 2) if gross_margin else None,
            "operating_margin_pct": round(operating_margin * 100, 2) if operating_margin else None,
            "net_margin_pct": round(net_margin * 100, 2) if net_margin else None,
            "sbc_adjusted_fcf_margin_pct": round(fcf_margin * 100, 2) if fcf_margin else None,
            "historical_revenue_cagr_pct": round(hist_cagr * 100, 2) if hist_cagr else None,
            "starting_revenue_usd": start_revenue,
        },
        "wacc": {
            "risk_free_rate_pct": round(risk_free * 100, 2),
            "market_risk_premium_pct": round(market_risk_premium * 100, 2),
            "beta": beta,
            "cost_of_equity_pct": round(cost_of_equity * 100, 2),
            "cost_of_debt_pct": round(cost_of_debt * 100, 2),
            "tax_rate_pct": round(tax_rate * 100, 2),
            "after_tax_cost_of_debt_pct": round(after_tax_cost_of_debt * 100, 2),
            "debt_weight_pct": round(debt_weight * 100, 2),
            "equity_weight_pct": round(equity_weight * 100, 2),
            "wacc_base_pct": round(wacc_base * 100, 2),
            "wacc_bear_pct": round(wacc_bear * 100, 2),
            "wacc_bull_pct": round(wacc_bull * 100, 2),
        },
        "dcf_model": {
            "model_type": "SBC-adjusted free cash flow DCF",
            "explicit_forecast_years": years,
            "terminal_value_method": "Gordon growth perpetuity",
            "starting_revenue_usd": start_revenue,
            "scenarios": {
                "bear": build_scenario_json(
                    bear_dcf, bear_growth, bear_margin, wacc_bear, bear_terminal_g,
                    "Macro slowdown, margin compression, and elevated SBC pressure."
                ),
                "base": build_scenario_json(
                    base_dcf, base_growth, base_margin, wacc_base, base_terminal_g,
                    "Stable execution, modest deceleration to terminal growth, steady margins."
                ),
                "bull": build_scenario_json(
                    bull_dcf, bull_growth, bull_margin, wacc_bull, bull_terminal_g,
                    "Stronger-than-expected demand, operating leverage, and capital returns."
                ),
            },
        },
        "relative_multiples": {
            "peer_set": peers,
            "peer_multiples": peer_multiples_json,
            "median_peer_ev_fcf": round(median_ev_fcf, 2) if median_ev_fcf is not None else None,
            "median_peer_ev_ebitda": round(median_ev_ebitda, 2) if median_ev_ebitda is not None else None,
            "median_peer_ev_revenue": round(median_ev_rev, 2) if median_ev_rev is not None else None,
            "implied_ev_fcf_multiple": round(implied_ev_fcf_multiple, 2),
            "implied_ev_ebitda_multiple": round(implied_ev_ebitda_multiple, 2),
            "implied_ev_revenue_multiple": round(implied_ev_rev_multiple, 2),
            "ev_from_ev_fcf_usd": round(relative_ev_fcf, 2),
            "ev_from_ev_ebitda_usd": round(relative_ev_ebitda, 2),
            "ev_from_ev_revenue_usd": round(relative_ev_rev, 2),
            "fair_value_per_share_from_ev_fcf_usd": round(ev_to_price(relative_ev_fcf), 2),
            "fair_value_per_share_from_ev_ebitda_usd": round(ev_to_price(relative_ev_ebitda), 2),
            "fair_value_per_share_from_ev_revenue_usd": round(ev_to_price(relative_ev_rev), 2),
        },
        "sum_of_parts": sotp,
        "reverse_engineering": reverse_engineering,
        "fair_value_synthesis": {
            "current_price_usd": price,
            "weights": weights,
            "dcf_bear_fv_usd": round(dcf_bear_fv, 2),
            "dcf_base_fv_usd": round(dcf_base_fv, 2),
            "dcf_bull_fv_usd": round(dcf_bull_fv, 2),
            "rel_fv_usd": round(rel_fv, 2),
            "sotp_base_fv_usd": round(sotp_base_fv, 2),
            "weighted_fv_usd": round(weighted_fv, 2),
            "upside_downside_to_weighted_fv_pct": round((weighted_fv / price - 1) * 100, 2) if price else None,
            "margin_of_safety_vs_base_pct": round((dcf_base_fv / price - 1) * 100, 2) if price else None,
        },
    }

    return valuation


# ── Risk bridge ─────────────────────────────────────────────────────────────


def _build_risk_bridge(
    ticker: str,
    session_date: str,
    sector_cfg: dict[str, Any],
    valuation: dict[str, Any],
    lq: dict[str, Any],
) -> dict[str, Any]:
    """Build a base risk_bridge.json from the valuation output and latest-quarter overrides."""

    dcf = valuation.get("dcf_model", {})
    base = dcf.get("scenarios", {}).get("base", {})
    bear = dcf.get("scenarios", {}).get("bear", {})
    bull = dcf.get("scenarios", {}).get("bull", {})

    base_fv = base.get("fair_value_per_share_usd")
    bear_fv = bear.get("fair_value_per_share_usd")
    bull_fv = bull.get("fair_value_per_share_usd")
    base_ev = base.get("enterprise_value_usd")
    bear_ev = bear.get("enterprise_value_usd")

    scenario_probs = {
        "bear": 0.20,
        "base": 0.55,
        "bull": 0.15,
        "recession": 0.05,
        "sbc_cliff": 0.03,
        "regulatory": 0.02,
    }

    def make_risk(
        risk_id: str,
        category: str,
        specific_risk: str,
        affected_parameters: list[str],
        probability_pct: float,
        time_horizon: str,
        direction: str,
        impact_base: float,
        growth_delta: float | None = None,
        margin_delta: float | None = None,
        wacc_delta: float | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        return {
            "risk_id": risk_id,
            "category": category,
            "specific_risk": specific_risk,
            "affected_parameters": affected_parameters,
            "impact_magnitude": {
                "base_case": impact_base,
                "bear_case": impact_base * 1.5,
                "bull_case": impact_base * 0.5,
                "unit": "percentage_points",
            },
            "probability": round(probability_pct / 100.0, 4),
            "time_horizon": time_horizon,
            "valuation_adjustment": {
                "direction": direction,
                "growth_delta": growth_delta,
                "margin_delta": margin_delta,
                "wacc_delta": wacc_delta,
                "notes": notes,
            },
        }

    risks: list[dict[str, Any]] = []

    # Pull override-triggered risks from latest_quarter.json
    for override in lq.get("override_log", []):
        param = override.get("parameter", "")
        reason = override.get("reason", "")
        risks.append(make_risk(
            risk_id=f"OVERRIDE_{len(risks)+1}",
            category="Latest-quarter override",
            specific_risk=f"{param}: {reason}",
            affected_parameters=[param],
            probability_pct=30.0,
            time_horizon="1y",
            direction="decrease_growth" if "growth" in param.lower() else "decrease_margin",
            impact_base=-0.02,
            notes=reason,
        ))

    # Generic structural risks
    risks.extend([
        make_risk(
            "R1", "Macro / demand",
            "Consumer/enterprise demand softens, compressing revenue growth and margins.",
            ["revenue_growth", "terminal_growth", "fcf_margin"],
            25.0, "1y", "decrease_growth", -0.02,
            growth_delta=-0.02, margin_delta=-0.015,
            notes="Revenue growth -150 to -300 bps; FCF margin -100 to -200 bps",
        ),
        make_risk(
            "R2", "Competition / disruption",
            "New products or platform shifts erode pricing power.",
            ["revenue_growth", "terminal_growth", "wacc"],
            20.0, "3y", "decrease_growth", -0.015,
            growth_delta=-0.015, wacc_delta=0.01,
            notes="Revenue growth -100 to -250 bps; WACC +50 to +150 bps",
        ),
        make_risk(
            "R3", "SBC / dilution",
            "Stock-based compensation rises faster than revenue, diluting per-share FCF.",
            ["sbc_adjusted_fcf_margin", "share_count"],
            15.0, "3y", "decrease_margin", -0.03,
            margin_delta=-0.03,
            notes="SBC-adjusted FCF margin -200 to -400 bps",
        ),
    ])

    # Use sector-specific stress scenarios from sector_config
    stress_names = sector_cfg.get("substitutions", {}).get("stress_test_scenarios", [])
    stress_scenarios = []
    for i, name in enumerate(stress_names[:4], start=1):
        stress_scenarios.append({
            "scenario_id": chr(64 + i),
            "name": name,
            "probability": 0.10 if i == 1 else 0.05,
            "affected_parameters": {"note": "To be modeled by Agent 13 stress-test swarm"},
            "fair_value_haircut_pct": None,
            "implied_share_price_usd": None,
            "narrative": "Sector-specific stress scenario; Agent 13 will quantify.",
        })
    stress_scenarios.append({
        "scenario_id": "E",
        "name": "Global recession / macro shock",
        "probability": 0.05,
        "affected_parameters": {"revenue_growth": "-200 to -400 bps", "wacc": "+75 to +150 bps"},
        "fair_value_haircut_pct": 20.0,
        "implied_share_price_usd": round(base_fv * 0.80, 2) if base_fv else None,
        "narrative": "Broad demand shock and higher discount rates simultaneously compress growth and multiples.",
    })

    pw_fv = (
        scenario_probs["base"] * (base_fv or 0)
        + scenario_probs["bull"] * (bull_fv or 0)
        + scenario_probs["bear"] * (bear_fv or 0)
        + scenario_probs["recession"] * (base_fv * 0.80 if base_fv else 0)
        + scenario_probs["sbc_cliff"] * (base_fv * 0.70 if base_fv else 0)
        + scenario_probs["regulatory"] * (base_fv * 0.85 if base_fv else 0)
    )

    risk_bridge = {
        "ticker": ticker.upper(),
        "session_date": session_date,
        "primary_sector": sector_cfg.get("primary_sector", "standard"),
        "agent": "Agent 5 (kimi-datasource valuation) base risk bridge",
        "valuation_anchor": {
            "base_case_enterprise_value_usd": base_ev,
            "base_case_fair_value_per_share_usd": base_fv,
            "wacc_base_pct": valuation.get("wacc", {}).get("wacc_base_pct"),
            "terminal_growth_base_pct": base.get("terminal_growth_pct"),
        },
        "probability_framework_note": (
            "Standalone risk probabilities are marginal (not mutually exclusive). "
            "Scenario probabilities below are mutually exclusive and sum to 100%."
        ),
        "scenario_probabilities": scenario_probs,
        "probability_weighted_fv_usd": round(pw_fv, 2) if pw_fv else None,
        "risks": risks,
        "stress_scenario_valuation_impacts": {
            "bear_case_vs_base_ev_usd": round((bear_ev or 0) - (base_ev or 0), 2),
            "bull_case_vs_base_ev_usd": None,
            "bear_case_fv_per_share_usd": bear_fv,
            "base_case_fv_per_share_usd": base_fv,
            "bull_case_fv_per_share_usd": bull_fv,
        },
        "stress_test": {
            "source": "Phase 2.5 AgentSwarm (coder) — 5 scenarios",
            "scenarios": stress_scenarios,
        },
        "recommendation": {
            "position_sizing_input": (
                f"Model outputs: bear-case FV ~${bear_fv:.0f}/share, base-case ~${base_fv:.0f}/share, "
                f"bull-case ~${bull_fv:.0f}/share, weighted FV ~${pw_fv:.0f}/share. "
                "Review trajectory_review.json and valuation_judgment.json before sizing."
            ),
            "key_monitoring_kpis": [
                "Revenue growth trajectory vs historical CAGR",
                "Gross/operating margin expansion or compression",
                "SBC/Revenue and buyback offset",
                "Capital return program updates",
                "Tariff/supply-chain and FX commentary",
            ],
        },
    }
    return risk_bridge


# ── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Agent 5 (kimi-datasource): valuation modeling")
    parser.add_argument("--ticker", required=True, help="Ticker symbol")
    parser.add_argument("--date", required=True, help="Session date YYYY-MM-DD")
    parser.add_argument("--output-dir", default="/workspace-stock-research", help="Project root")
    parser.add_argument("--risk-free", type=float, default=0.042, help="Risk-free rate")
    parser.add_argument("--market-risk-premium", type=float, default=0.050, help="Market risk premium")
    parser.add_argument("--tax-rate", type=float, default=0.18, help="Marginal tax rate")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    session_date = args.date
    output_dir = Path(args.output_dir).expanduser().resolve()
    session_root = output_dir / ticker / session_date
    data_dir = session_root / "data"
    registry_dir = session_root / "registry"
    data_dir.mkdir(parents=True, exist_ok=True)
    registry_dir.mkdir(parents=True, exist_ok=True)

    sector_cfg = load_json(registry_dir / "sector_config.json") or {}
    lq = load_json(registry_dir / "latest_quarter.json") or {}
    sp_rows = _read_sp_rows(data_dir / "sp_financials.csv")

    # Market data from yfinance (retained for price, beta, shares)
    t = yf.Ticker(ticker)
    info = t.info or {}

    # Peer set: prefer sector_config, then S&P competitors, then a sensible default
    peers = sector_cfg.get("peers", [])
    if not peers:
        sp_comp = load_json(registry_dir / "sp_competitors.json") or {}
        peers = [r.get("competitor_ticker") for r in sp_comp.get("competitors", []) if r.get("competitor_ticker")]
        peers = peers[:6]
    if not peers and ticker == "AAPL":
        peers = ["MSFT", "GOOGL", "AMZN", "META", "HPQ", "DELL"]

    primary_sector = sector_cfg.get("primary_sector", "standard")
    if primary_sector in ("standard", "growth"):
        valuation = _standard_growth_model(
            ticker, session_date, sector_cfg, lq, sp_rows, info, t, peers,
            args.risk_free, args.market_risk_premium, args.tax_rate,
        )
    else:
        # TODO: implement sector-specific models for banking, insurance, reit, utility, cyclical
        valuation = {
            "ticker": ticker,
            "session_date": session_date,
            "primary_sector": primary_sector,
            "error": f"Sector '{primary_sector}' model not yet implemented in kimi-datasource harness.",
            "note": "Use standard/growth for now or extend agent5_kd_valuation.py.",
        }

    save_json(data_dir / "valuation_model.json", valuation)
    print(f"Wrote {data_dir / 'valuation_model.json'}")

    if "error" not in valuation:
        risk_bridge = _build_risk_bridge(ticker, session_date, sector_cfg, valuation, lq)
        save_json(registry_dir / "risk_bridge.json", risk_bridge)
        print(f"Wrote {registry_dir / 'risk_bridge.json'}")
        print(f"Base-case FV/share: ${valuation['fair_value_synthesis']['dcf_base_fv_usd']}")
        print(f"Weighted FV/share: ${valuation['fair_value_synthesis']['weighted_fv_usd']}")


if __name__ == "__main__":
    main()
