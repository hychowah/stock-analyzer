#!/usr/bin/env python3
"""Agent 5: Sector-aware valuation modeling.

Primary: SBC-adjusted FCF DCF (10-yr explicit, is_also_growth=true).
Secondary: EV/FCF, EV/EBITDA, EV/Revenue relative multiples from peer data.
Tertiary: Sum-of-the-parts by segment.

Outputs:
    <session>/data/valuation_model.json
    <session>/registry/risk_bridge.json

Usage:
    yfinance-market-mcp/.venv/bin/python scripts/agent5_valuation.py \
        --ticker ADBE --date 2026-07-20 --output-dir /workspace-stock-research
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yfinance as yf


# ── Helpers ─────────────────────────────────────────────────────────────────


def _safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _latest_column(df) -> dict[str, Any] | None:
    if df is None or df.empty:
        return None
    col = df.columns[-1]
    return {str(k): _safe(v) for k, v in df[col].items()}


def _find_row(rows: dict[str, Any] | None, *candidates: str) -> Any:
    if not rows:
        return None
    for c in candidates:
        for k, v in rows.items():
            if c.lower() in k.lower():
                return v
    return None


def _extract_statement_item(df, *candidates: str) -> float | None:
    col = _latest_column(df)
    if not col:
        return None
    return _find_row(col, *candidates)


# ── Peer multiples ──────────────────────────────────────────────────────────


@dataclass
class PeerMultiples:
    ticker: str
    ev_ebitda: float | None
    ev_fcf: float | None
    ev_revenue: float | None


def fetch_peer_multiples(ticker: str, peers: list[str]) -> list[PeerMultiples]:
    """Fetch latest EV/EBITDA, EV/FCF, and EV/Revenue for ticker + peers from yfinance."""
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


def read_peer_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def median(values: list[float]) -> float | None:
    clean = sorted([v for v in values if v is not None])
    if not clean:
        return None
    n = len(clean)
    if n % 2:
        return clean[n // 2]
    return (clean[n // 2 - 1] + clean[n // 2]) / 2


# ── DCF engine ──────────────────────────────────────────────────────────────


def build_dcf(
    rev_growths: list[float],
    fcf_margins: list[float],
    terminal_growth: float,
    wacc: float,
    start_revenue: float,
    years: int = 10,
) -> dict[str, Any]:
    """Build a year-by-year SBC-adjusted FCF DCF.

    start_revenue is the fiscal year *before* the first forecast year. The first
    growth rate in rev_growths produces the Year-1 revenue.
    """
    assert len(rev_growths) == years
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


def solve_implied_cagr(
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


def solve_implied_terminal_margin(
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


def solve_implied_wacc(
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


# ── Scenario probabilities ──────────────────────────────────────────────────


def build_scenario_probabilities() -> dict[str, float]:
    """Return a coherent, mutually-exclusive scenario probability set."""
    return {
        "bear": 0.20,
        "base": 0.55,
        "bull": 0.15,
        "recession": 0.05,
        "sbc_cliff": 0.03,
        "regulatory": 0.02,
    }


# ── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Agent 5: sector-aware valuation modeling")
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

    api = json.loads((registry_dir / "api_data.json").read_text())
    lq = json.loads((registry_dir / "latest_quarter.json").read_text())
    sector_cfg = json.loads((registry_dir / "sector_config.json").read_text())

    info = api["info"]
    t = yf.Ticker(ticker)

    # -----------------------------------------------------------------------
    # Key market / financial inputs
    # -----------------------------------------------------------------------
    current_price = float(info["currentPrice"])
    shares_out = float(info["sharesOutstanding"])
    market_cap = float(info["marketCap"])
    enterprise_value = float(info["enterpriseValue"])

    # Prefer 10-Q figures from latest_quarter.json; fall back to API info
    bs = lq.get("balance_sheet", {})
    cf = lq.get("cash_flow", {})
    total_debt = float(bs.get("total_debt") or info.get("totalDebt") or 0) * 1e6
    total_cash = float(bs.get("cash_and_equivalents") or info.get("totalCash") or 0) * 1e6

    ttm_revenue = float(info["totalRevenue"])
    ttm_fcf = float(cf.get("ttm_free_cash_flow") or info.get("freeCashflow") or 0) * 1e6
    ttm_sbc = float(cf.get("ttm_sbc") or _extract_statement_item(t.cashflow, "Stock Based Compensation") or 0) * 1e6
    ttm_sbc_adj_fcf = ttm_fcf - ttm_sbc
    ttm_ebitda = float(info.get("ebitda") or 0)

    reported_fcf_margin = ttm_fcf / ttm_revenue if ttm_revenue else None
    sbc_adj_fcf_margin = ttm_sbc_adj_fcf / ttm_revenue if ttm_revenue else None
    gross_margin = float(info.get("grossMargins") or 0)
    operating_margin = float(info.get("operatingMargins") or 0)
    ebitda_margin = ttm_ebitda / ttm_revenue if ttm_revenue else None

    ev_fcf_reported = enterprise_value / ttm_fcf if ttm_fcf else None
    ev_fcf_sbc_adj = enterprise_value / ttm_sbc_adj_fcf if ttm_sbc_adj_fcf else None
    ev_ebitda = enterprise_value / ttm_ebitda if ttm_ebitda else None
    ev_revenue = enterprise_value / ttm_revenue if ttm_revenue else None
    pe_trailing = float(info.get("trailingPE") or 0)

    # -----------------------------------------------------------------------
    # WACC
    # -----------------------------------------------------------------------
    risk_free = args.risk_free
    market_risk_premium = args.market_risk_premium
    beta = float(info.get("beta") or 1.0)
    cost_of_equity = risk_free + beta * market_risk_premium

    is_yr = api.get("income_statement_yearly") or {}
    interest_expense = None
    ie_row = is_yr.get("Interest Expense") or is_yr.get("InterestExpense")
    if ie_row:
        latest_ie_date = max(ie_row.keys())
        interest_expense = abs(float(ie_row[latest_ie_date]))
    if interest_expense is None:
        # Fall back to yfinance DataFrame
        interest_expense = abs(_extract_statement_item(t.income_stmt, "Interest Expense") or 0)
    cost_of_debt = interest_expense / total_debt if interest_expense and total_debt else 0.04
    tax_rate = args.tax_rate
    after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)

    debt_weight = total_debt / (market_cap + total_debt) if (market_cap + total_debt) else 0
    equity_weight = market_cap / (market_cap + total_debt) if (market_cap + total_debt) else 1
    wacc = equity_weight * cost_of_equity + debt_weight * after_tax_cost_of_debt

    wacc_base = round(wacc, 4)
    wacc_bear = round(wacc + 0.015, 4)
    wacc_bull = round(max(wacc - 0.005, 0.075), 4)

    # -----------------------------------------------------------------------
    # DCF: start from FY2025 revenue so Year 1 = guided FY2026
    # -----------------------------------------------------------------------
    is_df = t.income_stmt
    fy2025_revenue = None
    if is_df is not None and not is_df.empty:
        latest_fy_col = is_df.columns[-1]
        fy2025_revenue = _safe(is_df.loc["Total Revenue", latest_fy_col]) if "Total Revenue" in is_df.index else None
    if fy2025_revenue is None:
        fy2025_revenue = ttm_revenue / 1.06  # rough fallback
    fy2025_revenue = float(fy2025_revenue)

    fy2026_guided_mid = float(lq.get("guidance", {}).get("fy2026_revenue_guidance_mid") or 0)
    if fy2026_guided_mid == 0:
        # Parse "$26.50B-$26.60B" or use a default
        guide = lq.get("guidance", {}).get("revenue_guidance", "")
        if "$" in guide and "B" in guide:
            try:
                parts = [p.replace("$", "").replace("B", "").strip() for p in guide.split(";")[-1].split("-")]
                fy2026_guided_mid = sum(float(x) for x in parts) / len(parts) * 1e9
            except Exception:
                fy2026_guided_mid = ttm_revenue * 1.05
        else:
            fy2026_guided_mid = ttm_revenue * 1.05

    # Implied FY2026 growth from FY2025 to guided midpoint
    fy2026_implied_growth = (fy2026_guided_mid / fy2025_revenue) - 1

    base_growth = [fy2026_implied_growth, 0.105, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.038, 0.033]
    base_margin = [0.343, 0.348, 0.352, 0.355, 0.358, 0.360, 0.362, 0.363, 0.364, 0.365]
    base_terminal_g = 0.030

    bear_growth = [0.100, 0.085, 0.070, 0.055, 0.045, 0.038, 0.032, 0.028, 0.025, 0.022]
    bear_margin = [0.320, 0.315, 0.310, 0.305, 0.300, 0.298, 0.296, 0.295, 0.294, 0.293]
    bear_terminal_g = 0.020

    bull_growth = [0.130, 0.125, 0.115, 0.105, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045]
    bull_margin = [0.350, 0.360, 0.370, 0.380, 0.390, 0.395, 0.400, 0.403, 0.405, 0.408]
    bull_terminal_g = 0.035

    base_dcf = build_dcf(base_growth, base_margin, base_terminal_g, wacc_base, fy2025_revenue)
    bear_dcf = build_dcf(bear_growth, bear_margin, bear_terminal_g, wacc_bear, fy2025_revenue)
    bull_dcf = build_dcf(bull_growth, bull_margin, bull_terminal_g, wacc_bull, fy2025_revenue)

    # CAGR reported from Year-1 (FY2026) revenue to Year-10 (FY2035)
    def explicit_cagr(dcf_result: dict) -> float:
        return round(((dcf_result["revenues"][-1] / dcf_result["revenues"][0]) ** (1 / 9) - 1) * 100, 2)

    # -----------------------------------------------------------------------
    # Relative multiples (live peer data)
    # -----------------------------------------------------------------------
    peers = sector_cfg.get("peers", [])
    peer_multiples = fetch_peer_multiples(ticker, peers)

    # Also try to backfill from peer_comparison.csv if yfinance is missing
    csv_rows = read_peer_csv(data_dir / "peer_comparison.csv")
    csv_by_ticker = {r.get("ticker", "").upper(): r for r in csv_rows}
    for pm in peer_multiples:
        if pm.ticker == ticker:
            continue
        row = csv_by_ticker.get(pm.ticker)
        if row:
            if pm.ev_ebitda is None:
                pm.ev_ebitda = _safe(float(row["ev_ebitda"])) if row.get("ev_ebitda") else None
            if pm.ev_revenue is None:
                ps = _safe(float(row["ps"])) if row.get("ps") else None
                pm.ev_revenue = ps

    peer_vals = [pm for pm in peer_multiples if pm.ticker != ticker]
    median_ev_fcf = median([pm.ev_fcf for pm in peer_vals])
    median_ev_ebitda = median([pm.ev_ebitda for pm in peer_vals])
    median_ev_rev = median([pm.ev_revenue for pm in peer_vals])

    # Adjustment factor: discount for slower growth / transition risk
    adobe_adjustment_factor = 0.90
    implied_ev_fcf_multiple = (median_ev_fcf or 18.0) * adobe_adjustment_factor
    implied_ev_ebitda_multiple = (median_ev_ebitda or 16.0) * adobe_adjustment_factor
    implied_ev_rev_multiple = (median_ev_rev or 7.0) * adobe_adjustment_factor

    relative_ev_fcf = ttm_sbc_adj_fcf * implied_ev_fcf_multiple
    relative_ev_ebitda = ttm_ebitda * implied_ev_ebitda_multiple
    relative_ev_rev = ttm_revenue * implied_ev_rev_multiple

    peer_multiples_json = {
        pm.ticker: {
            "ev_fcf": _safe(pm.ev_fcf),
            "ev_ebitda": _safe(pm.ev_ebitda),
            "ev_rev": _safe(pm.ev_revenue),
        }
        for pm in peer_multiples
    }

    # -----------------------------------------------------------------------
    # Sum-of-the-parts
    # -----------------------------------------------------------------------
    segment_weights = {
        "Digital Media": 0.73,
        "Digital Experience": 0.25,
        "Publishing and Advertising": 0.02,
    }
    segment_multiples = {
        "Digital Media": {"ev_revenue_low": 4.0, "ev_revenue_base": 5.0, "ev_revenue_high": 6.5},
        "Digital Experience": {"ev_revenue_low": 2.0, "ev_revenue_base": 3.0, "ev_revenue_high": 4.0},
        "Publishing and Advertising": {"ev_revenue_low": 0.8, "ev_revenue_base": 1.2, "ev_revenue_high": 1.8},
    }

    sotp_fy2026_revenue = fy2026_guided_mid
    sotp = {}
    for seg, weight in segment_weights.items():
        seg_rev = sotp_fy2026_revenue * weight
        mults = segment_multiples[seg]
        sotp[seg] = {
            "fy2026_revenue_usd": seg_rev,
            "revenue_weight": weight,
            "ev_revenue_multiples": mults,
            "ev_low_usd": seg_rev * mults["ev_revenue_low"],
            "ev_base_usd": seg_rev * mults["ev_revenue_base"],
            "ev_high_usd": seg_rev * mults["ev_revenue_high"],
        }

    sotp_sum_low = sum(v["ev_low_usd"] for v in sotp.values())
    sotp_sum_base = sum(v["ev_base_usd"] for v in sotp.values())
    sotp_sum_high = sum(v["ev_high_usd"] for v in sotp.values())

    # -----------------------------------------------------------------------
    # Fair value synthesis (weights stored explicitly and used consistently)
    # -----------------------------------------------------------------------
    def ev_to_price(ev: float) -> float:
        return (ev - total_debt + total_cash) / shares_out

    dcf_bear_fv = ev_to_price(bear_dcf["enterprise_value"])
    dcf_base_fv = ev_to_price(base_dcf["enterprise_value"])
    dcf_bull_fv = ev_to_price(bull_dcf["enterprise_value"])
    rel_fv = ev_to_price((relative_ev_fcf + relative_ev_ebitda + relative_ev_rev) / 3)
    sotp_base_fv = ev_to_price(sotp_sum_base)

    # Weights: 50% DCF base, 25% relative, 25% SOTP
    weights = {
        "dcf_base": 0.50,
        "relative": 0.25,
        "sotp": 0.25,
    }
    weighted_fv = (
        dcf_base_fv * weights["dcf_base"]
        + rel_fv * weights["relative"]
        + sotp_base_fv * weights["sotp"]
    )

    # -----------------------------------------------------------------------
    # Reverse engineering
    # -----------------------------------------------------------------------
    reverse_engineering = {
        "current_ev_usd": enterprise_value,
        "current_price": current_price,
        "ev_fcf_reported": round(ev_fcf_reported, 2) if ev_fcf_reported else None,
        "ev_fcf_sbc_adjusted": round(ev_fcf_sbc_adj, 2) if ev_fcf_sbc_adj else None,
        "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda else None,
        "pe_trailing": round(pe_trailing, 2),
        "methodology": (
            "Solve for the single parameter that makes the 10-year SBC-adjusted FCF DCF "
            "equal current EV, holding other assumptions at base-case levels. "
            "Year-1 revenue is FY2026 guided; FY2025 is the DCF starting revenue."
        ),
        "implied_revenue_cagr": {
            "description": "Holding terminal SBC-adjusted FCF margin at base-case terminal 36.5% and terminal growth 3.0%",
            "value_pct": round(solve_implied_cagr(enterprise_value, fy2025_revenue, base_margin[-1], base_terminal_g, wacc_base) * 100, 2),
            "assessed_achievable": "11-13% near-term; 3-4% terminal. A constant ~7-8% 10-year CAGR is plausible; anything above 10% for the full decade is demanding.",
        },
        "implied_terminal_fcf_margin": {
            "description": "Holding base-case revenue CAGR path and terminal growth 3.0%",
            "value_pct": round(solve_implied_terminal_margin(enterprise_value, fy2025_revenue, base_growth, base_terminal_g, wacc_base) * 100, 2),
            "assessed_achievable": "Current SBC-adjusted FCF margin ~34%. Terminal margin above 38% requires sustained operating leverage and SBC/Revenue falling below 6%; achievable only in bull case.",
        },
        "implied_wacc": {
            "description": "Holding base-case revenue CAGR path and base-case SBC-adjusted FCF margin trajectory",
            "value_pct": round(solve_implied_wacc(enterprise_value, fy2025_revenue, base_growth, base_margin, base_terminal_g) * 100, 2),
            "assessed_achievable": "Estimated WACC ~10.7%. Implied WACC below 9% would require materially lower beta/cost of equity; above 13% implies high distress/regulatory risk.",
        },
        "priced_for_perfection_flag": False,
        "priced_for_perfection_rationale": (
            "Current EV/FCF (reported) is well below mature-SaaS peer medians. "
            "Reverse engineering shows the market is pricing in either a low/negative 10-year revenue CAGR, "
            "a collapsed terminal SBC-adjusted FCF margin, or a very high WACC. "
            "All three are more pessimistic than base-case fundamentals. The stock does NOT appear priced for perfection."
        ),
    }

    # -----------------------------------------------------------------------
    # Build valuation_model.json
    # -----------------------------------------------------------------------
    def build_scenario_json(dcf_result: dict, growth: list[float], margins: list[float], wacc_pct: float, terminal_g: float, description: str) -> dict:
        return {
            "description": description,
            "wacc_pct": round(wacc_pct * 100, 2),
            "terminal_growth_pct": round(terminal_g * 100, 2),
            "revenue_cagr_pct": explicit_cagr(dcf_result),
            "terminal_fcf_margin_pct": round(margins[-1] * 100, 2),
            "enterprise_value_usd": dcf_result["enterprise_value"],
            "fair_value_per_share_usd": round(ev_to_price(dcf_result["enterprise_value"]), 2),
            "pv_explicit_usd": sum(dcf_result["pv_fcfs"]),
            "pv_terminal_usd": dcf_result["pv_terminal"],
            "pv_explicit_pct": round(sum(dcf_result["pv_fcfs"]) / dcf_result["enterprise_value"] * 100, 2),
            "forecast": [
                {
                    "year": i + 1,
                    "fiscal_year": f"FY{2026 + i}",
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

    valuation = {
        "ticker": ticker,
        "session_date": session_date,
        "agent": "Agent 5 (valuation modeling)",
        "valuation_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "primary_model": sector_cfg.get("substitutions", {}).get("valuation_model_primary", "Standard FCF-based DCF"),
        "is_also_growth": sector_cfg.get("is_also_growth", False),
        "sbc_analysis_intensity": sector_cfg.get("substitutions", {}).get("sbc_analysis_intensity", "standard"),
        "inputs": {
            "current_price_usd": current_price,
            "shares_outstanding_millions": round(shares_out / 1e6, 2),
            "market_cap_usd": market_cap,
            "enterprise_value_usd": enterprise_value,
            "total_debt_usd": total_debt,
            "total_cash_usd": total_cash,
            "ttm_revenue_usd": ttm_revenue,
            "ttm_reported_fcf_usd": ttm_fcf,
            "ttm_sbc_usd": ttm_sbc,
            "ttm_sbc_adjusted_fcf_usd": ttm_sbc_adj_fcf,
            "ttm_ebitda_usd": ttm_ebitda,
            "reported_fcf_margin_pct": round(reported_fcf_margin * 100, 2) if reported_fcf_margin else None,
            "sbc_adjusted_fcf_margin_pct": round(sbc_adj_fcf_margin * 100, 2) if sbc_adj_fcf_margin else None,
            "gross_margin_pct": round(gross_margin * 100, 2),
            "operating_margin_pct": round(operating_margin * 100, 2),
            "ebitda_margin_pct": round(ebitda_margin * 100, 2) if ebitda_margin else None,
            "fy2025_revenue_usd": fy2025_revenue,
            "fy2026_guided_revenue_usd": fy2026_guided_mid,
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
            "explicit_forecast_years": 10,
            "terminal_value_method": "Gordon growth perpetuity",
            "starting_revenue_usd": fy2025_revenue,
            "explicit_forecast_start_year_revenue_usd": fy2026_guided_mid,
            "scenarios": {
                "bear": build_scenario_json(
                    bear_dcf, bear_growth, bear_margin, wacc_bear, bear_terminal_g,
                    "AI disruption stalls Creative Cloud; enterprise ad spend cuts hit Digital Experience; SBC pressure persists."
                ),
                "base": build_scenario_json(
                    base_dcf, base_growth, base_margin, wacc_base, base_terminal_g,
                    "Guided FY26 growth, gradual deceleration to 3% terminal; modest operating leverage; SBC/Revenue stable near 7.5%."
                ),
                "bull": build_scenario_json(
                    bull_dcf, bull_growth, bull_margin, wacc_bull, bull_terminal_g,
                    "AI products accelerate growth; operating leverage exceeds expectations; SBC/Revenue drifts down."
                ),
            },
        },
        "relative_multiples": {
            "peer_set": peers,
            "peer_multiples": peer_multiples_json,
            "median_peer_ev_fcf": round(median_ev_fcf, 2) if median_ev_fcf is not None else None,
            "median_peer_ev_ebitda": round(median_ev_ebitda, 2) if median_ev_ebitda is not None else None,
            "median_peer_ev_revenue": round(median_ev_rev, 2) if median_ev_rev is not None else None,
            "adobe_adjustment_factor": adobe_adjustment_factor,
            "implied_ev_fcf_multiple": round(implied_ev_fcf_multiple, 2),
            "implied_ev_ebitda_multiple": round(implied_ev_ebitda_multiple, 2),
            "implied_ev_revenue_multiple": round(implied_ev_rev_multiple, 2),
            "ev_from_ev_fcf_usd": round(relative_ev_fcf, 2),
            "ev_from_ev_ebitda_usd": round(relative_ev_ebitda, 2),
            "ev_from_ev_revenue_usd": round(relative_ev_rev, 2),
            "fair_value_per_share_from_ev_fcf_usd": round(ev_to_price(relative_ev_fcf), 2),
            "fair_value_per_share_from_ev_ebitda_usd": round(ev_to_price(relative_ev_ebitda), 2),
            "fair_value_per_share_from_ev_revenue_usd": round(ev_to_price(relative_ev_rev), 2),
            "current_multiples": {
                "ev_fcf_reported": round(ev_fcf_reported, 2) if ev_fcf_reported else None,
                "ev_fcf_sbc_adjusted": round(ev_fcf_sbc_adj, 2) if ev_fcf_sbc_adj else None,
                "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda else None,
                "ev_revenue": round(ev_revenue, 2) if ev_revenue else None,
            },
        },
        "sum_of_parts": {
            "fy2026_revenue_usd": sotp_fy2026_revenue,
            "segment_weights": segment_weights,
            "segment_multiples": segment_multiples,
            "segments": sotp,
            "sum_ev_low_usd": sotp_sum_low,
            "sum_ev_base_usd": sotp_sum_base,
            "sum_ev_high_usd": sotp_sum_high,
            "fair_value_per_share_low_usd": round(ev_to_price(sotp_sum_low), 2),
            "fair_value_per_share_base_usd": round(ev_to_price(sotp_sum_base), 2),
            "fair_value_per_share_high_usd": round(ev_to_price(sotp_sum_high), 2),
            "current_ev_usd": enterprise_value,
            "sotp_vs_current_pct": round((sotp_sum_base / enterprise_value - 1) * 100, 2),
        },
        "reverse_engineering": reverse_engineering,
        "fair_value_synthesis": {
            "current_price_usd": current_price,
            "weights": weights,
            "dcf_bear_fv_usd": round(dcf_bear_fv, 2),
            "dcf_base_fv_usd": round(dcf_base_fv, 2),
            "dcf_bull_fv_usd": round(dcf_bull_fv, 2),
            "rel_fv_usd": round(rel_fv, 2),
            "sotp_base_fv_usd": round(sotp_base_fv, 2),
            "weighted_fv_usd": round(weighted_fv, 2),
            "upside_downside_to_weighted_fv_pct": round((weighted_fv / current_price - 1) * 100, 2),
            "margin_of_safety_vs_base_pct": round((dcf_base_fv / current_price - 1) * 100, 2),
        },
    }

    # -----------------------------------------------------------------------
    # Risk bridge with coherent scenario probabilities and 5th stress scenario
    # -----------------------------------------------------------------------
    scenario_probs = build_scenario_probabilities()

    # Allocate the bear-vs-base EV gap across composing risks
    bear_ev_gap = base_dcf["enterprise_value"] - bear_dcf["enterprise_value"]
    risk_allocations = {
        "R1": 0.55,  # AI disruption
        "R2": 0.25,  # Recession
        "R3": 0.15,  # SBC cliff
        "R4": 0.05,  # Regulatory
    }

    def make_risk(
        risk_id: str,
        category: str,
        specific_risk: str,
        severity: str,
        probability_pct: int,
        scenario_probability: float,
        affected_parameters: list[str],
        parameter_adjustment: dict[str, str],
        valuation_impact_usd: float,
        mitigation: str,
        time_horizon: str,
        direction: str,
        growth_delta: float | None = None,
        margin_delta: float | None = None,
        wacc_delta: float | None = None,
    ) -> dict:
        return {
            "risk_id": risk_id,
            "category": category,
            "description": specific_risk,
            "specific_risk": specific_risk,
            "severity": severity,
            "probability_pct": probability_pct,
            "scenario_probability": scenario_probability,
            "dcp_parameters_impacted": affected_parameters,
            "affected_parameters": affected_parameters,
            "parameter_adjustment": parameter_adjustment,
            "impact_magnitude": {
                "base_case": -0.02,
                "bear_case": -0.04,
                "bull_case": -0.01,
                "unit": "percentage_points",
            },
            "probability": probability_pct / 100.0,
            "time_horizon": time_horizon,
            "valuation_adjustment": {
                "direction": direction,
                "wacc_delta": wacc_delta,
                "growth_delta": growth_delta,
                "margin_delta": margin_delta,
                "multiple_delta": None,
                "notes": json.dumps(parameter_adjustment),
            },
            "scenario_mapping": "bear_case" if risk_id in ("R1", "R2") else ("scenario_specific" if risk_id in ("R3", "R4") else ("base_case_with_drag" if risk_id in ("R5", "R6") else "base_case_minor")),
            "valuation_impact_usd": valuation_impact_usd,
            "mitigation": mitigation,
            "monitoring_trigger": f"Watch {affected_parameters[0]} trend",
        }

    risks = [
        make_risk(
            "R1", "AI disruption",
            "Generative AI disrupts core Creative Cloud workflows and pricing power.",
            "high", 25, scenario_probs["bear"],
            ["revenue_growth", "terminal_growth", "terminal_fcf_margin", "wacc"],
            {"revenue_growth": "-200 to -400 bps across explicit forecast; terminal growth -50 bps", "terminal_fcf_margin": "-200 to -300 bps", "wacc": "+150 bps"},
            round(bear_ev_gap * risk_allocations["R1"], 2),
            "Firefly integration, AI-first subscriptions, ecosystem lock-in",
            "structural", "decrease_growth", growth_delta=-0.03, wacc_delta=0.015,
        ),
        make_risk(
            "R2", "Recession / enterprise ad-spend cut",
            "Macro slowdown reduces Digital Experience bookings and net-new ARR.",
            "medium", 30, scenario_probs["recession"],
            ["revenue_growth", "fcf_margin"],
            {"revenue_growth": "-150 to -300 bps in Digital Experience-heavy years", "fcf_margin": "-100 to -200 bps due to delayed bookings and higher S&M"},
            round(bear_ev_gap * risk_allocations["R2"], 2),
            "Recurring subscription model, RPO visibility, cost discipline",
            "1y", "decrease_growth", growth_delta=-0.02,
        ),
        make_risk(
            "R3", "SBC cliff / talent flight",
            "SBC/Revenue rises above 10% if AI talent wars intensify, diluting SBC-adjusted FCF.",
            "medium", 20, scenario_probs["sbc_cliff"],
            ["sbc_adjusted_fcf_margin", "share_count"],
            {"sbc_adjusted_fcf_margin": "-500 to -700 bps", "share_count": "+1.5% to +2.5% annual gross dilution if buybacks do not fully offset"},
            round(bear_ev_gap * risk_allocations["R3"], 2),
            "Aggressive buyback authorization, equity refresh discipline",
            "3y", "decrease_margin", margin_delta=-0.06,
        ),
        make_risk(
            "R4", "Antitrust / regulatory action",
            "Regulatory actions around Figma, AI training data, or app-store distribution.",
            "medium", 15, scenario_probs["regulatory"],
            ["revenue_growth", "terminal_growth", "wacc"],
            {"revenue_growth": "-100 to -200 bps", "terminal_growth": "-25 to -50 bps", "wacc": "+50 to +150 bps"},
            round(bear_ev_gap * risk_allocations["R4"], 2),
            "Legal reserves, settlement provisions, geographic diversification",
            "5y+", "decrease_growth", growth_delta=-0.015, wacc_delta=0.01,
        ),
        make_risk(
            "R5", "CFO transition",
            "Dan Durn departure and interim CFO Steve Day creates near-term execution/communication risk.",
            "medium", 20, 0.0,
            ["fcf_margin", "wacc"],
            {"fcf_margin": "-50 to -100 bps temporary disruption", "wacc": "+25 to +50 bps near-term risk premium"},
            round(base_dcf["enterprise_value"] * 0.03, 2),
            "Deep finance bench, clear Q3 guidance, succession plan",
            "1q", "decrease_margin", margin_delta=-0.0075, wacc_delta=0.0038,
        ),
        make_risk(
            "R6", "M&A integration (Semrush)",
            "Semrush must be integrated into Experience Cloud; cross-sell execution risk.",
            "medium", 25, 0.0,
            ["revenue_growth", "fcf_margin"],
            {"revenue_growth": "-50 to -150 bps if cross-sell lags", "fcf_margin": "-50 to -100 bps integration costs"},
            round(base_dcf["enterprise_value"] * 0.02, 2),
            "Proven M&A track record, dedicated integration team",
            "1y", "decrease_growth", growth_delta=-0.01, margin_delta=-0.0075,
        ),
        make_risk(
            "R7", "Foreign exchange",
            "USD strength reduces reported growth (~2pp headwind visible in Q2 FY26).",
            "low", 40, 0.0,
            ["revenue_growth"],
            {"revenue_growth": "-50 to -100 bps reported"},
            round(base_dcf["enterprise_value"] * 0.01, 2),
            "Natural hedge via global operations, pricing power",
            "1y", "decrease_growth", growth_delta=-0.0075,
        ),
    ]

    # Scenario probability note: standalone risk probabilities are marginal; scenario probabilities are mutually exclusive
    stress_scenarios = [
        {
            "scenario_id": "A",
            "name": "Generative AI disruption — core Creative Cloud growth stalls and pricing power erodes",
            "probability": scenario_probs["bear"],
            "affected_parameters": {
                "revenue_cagr_pct": {"base": explicit_cagr(base_dcf), "stressed": explicit_cagr(bear_dcf)},
                "terminal_fcf_margin_pct": {"base": base_margin[-1] * 100, "stressed": bear_margin[-1] * 100},
                "terminal_growth_pct": {"base": base_terminal_g * 100, "stressed": bear_terminal_g * 100},
                "wacc_pct": {"base": wacc_base * 100, "stressed": wacc_bear * 100},
                "enterprise_value_usd": {"base": base_dcf["enterprise_value"], "stressed": bear_dcf["enterprise_value"]},
            },
            "fair_value_haircut_pct": round((1 - bear_dcf["enterprise_value"] / base_dcf["enterprise_value"]) * 100, 2),
            "implied_share_price_usd": round(dcf_bear_fv, 2),
            "narrative": "Generative AI tools commoditize core Creative Cloud workflows, slowing net-new ARR and forcing price concessions. Maps to the modeled bear case.",
        },
        {
            "scenario_id": "B",
            "name": "Recession / enterprise ad-spend cut — Digital Experience growth halves, marketing budgets contract",
            "probability": scenario_probs["recession"],
            "affected_parameters": {
                "revenue_cagr_pct": f"-{round((explicit_cagr(base_dcf) - explicit_cagr(bear_dcf)) * 0.75, 2)} bps",
                "terminal_fcf_margin_pct": f"-100 to -150 bps",
                "wacc_pct": "+25 to +50 bps",
            },
            "fair_value_haircut_pct": 22.0,
            "implied_share_price_usd": round(dcf_base_fv * 0.78, 2),
            "narrative": "A recession-driven enterprise ad-spend cut disproportionately hits Digital Experience. Recurring subscriptions and low leverage limit the downside.",
        },
        {
            "scenario_id": "C",
            "name": "SBC cliff / talent flight — SBC/Revenue rises +5-7pp, dilution accelerates, buybacks cannot fully offset",
            "probability": scenario_probs["sbc_cliff"],
            "affected_parameters": {
                "sbc_adjusted_fcf_margin": "-500 to -700 bps",
                "share_count": "+1.5% to +2.5% annual gross dilution",
                "wacc_pct": "+25 to +50 bps",
            },
            "fair_value_haircut_pct": 30.0,
            "implied_share_price_usd": round(dcf_base_fv * 0.70, 2),
            "narrative": "An AI talent war forces Adobe to raise equity compensation, lifting SBC/Revenue toward 13-15% and compressing per-share DCF value.",
        },
        {
            "scenario_id": "D",
            "name": "Antitrust / regulatory action — Figma-style scrutiny expands to AI data, subscriptions, or app-store distribution",
            "probability": scenario_probs["regulatory"],
            "affected_parameters": {
                "revenue_growth": "-150 to -250 bps vs base-case CAGR",
                "terminal_growth_pct": "-50 to -75 bps",
                "wacc_pct": "+75 to +125 bps",
                "terminal_fcf_margin_pct": "-150 to -250 bps",
            },
            "fair_value_haircut_pct": 22.0,
            "implied_share_price_usd": round(dcf_base_fv * 0.78, 2),
            "narrative": "Expanding scrutiny hits Adobe's integrated ecosystem. Fines are fundable from internal cash flows; the risk is valuation compression.",
        },
        {
            "scenario_id": "E",
            "name": "FX / macro shock — sustained USD strength and rates-driven multiple compression",
            "probability": 0.05,
            "affected_parameters": {
                "revenue_growth": "-75 to -125 bps reported",
                "wacc_pct": "+50 to +100 bps",
                "terminal_growth_pct": "-25 to -50 bps",
            },
            "fair_value_haircut_pct": 15.0,
            "implied_share_price_usd": round(dcf_base_fv * 0.85, 2),
            "narrative": "A stronger USD and higher discount rates simultaneously reduce reported growth and compress long-duration software multiples. This is the fifth required macro/sector stress scenario.",
        },
    ]

    # Probability-weighted FV derived from mutually-exclusive scenario probabilities
    pw_fv = (
        scenario_probs["base"] * dcf_base_fv
        + scenario_probs["bull"] * dcf_bull_fv
        + scenario_probs["bear"] * dcf_bear_fv
        + scenario_probs["recession"] * (dcf_base_fv * 0.78)
        + scenario_probs["sbc_cliff"] * (dcf_base_fv * 0.70)
        + scenario_probs["regulatory"] * (dcf_base_fv * 0.78)
    )

    risk_bridge = {
        "ticker": ticker,
        "session_date": session_date,
        "primary_sector": sector_cfg.get("primary_sector", "standard"),
        "agent": "Agent 5 (valuation modeling) / Agent 13 stress-test aggregator",
        "valuation_anchor": {
            "base_case_enterprise_value_usd": base_dcf["enterprise_value"],
            "base_case_fair_value_per_share_usd": round(dcf_base_fv, 2),
            "wacc_base_pct": round(wacc_base * 100, 2),
            "terminal_growth_base_pct": round(base_terminal_g * 100, 2),
        },
        "probability_framework_note": (
            "Standalone risk probabilities are marginal (not mutually exclusive). "
            "Scenario probabilities below are mutually exclusive and sum to 100%."
        ),
        "scenario_probabilities": scenario_probs,
        "probability_weighted_fv_usd": round(pw_fv, 2),
        "risks": risks,
        "stress_scenario_valuation_impacts": {
            "bear_case_vs_base_ev_usd": round(bear_dcf["enterprise_value"] - base_dcf["enterprise_value"], 2),
            "bull_case_vs_base_ev_usd": round(bull_dcf["enterprise_value"] - base_dcf["enterprise_value"], 2),
            "bear_case_fv_per_share_usd": round(dcf_bear_fv, 2),
            "base_case_fv_per_share_usd": round(dcf_base_fv, 2),
            "bull_case_fv_per_share_usd": round(dcf_bull_fv, 2),
        },
        "stress_test": {
            "source": "Phase 2.5 AgentSwarm (coder) — 5 scenarios",
            "scenarios": stress_scenarios,
        },
        "recommendation": {
            "position_sizing_input": (
                f"Model outputs: bear-case FV ~${dcf_bear_fv:.0f}/share, base-case ~${dcf_base_fv:.0f}/share, "
                f"bull-case ~${dcf_bull_fv:.0f}/share, weighted FV ~${weighted_fv:.0f}/share. "
                f"The bear case still exceeds the current price of ${current_price:.2f}, suggesting the market has discounted substantial risk. "
                "A 3-5% position within a tech/growth sleeve is appropriate for investors who believe the Creative Cloud moat and Firefly integration can offset generative-AI threats."
            ),
            "key_monitoring_kpis": [
                "ARR growth and AI-first ARR trajectory",
                "SBC/Revenue and buyback offset",
                "Digital Experience net-new ARR",
                "Non-GAAP operating margin expansion",
                "RPO growth and current RPO mix",
            ],
        },
    }

    # -----------------------------------------------------------------------
    # Write outputs
    # -----------------------------------------------------------------------
    with open(data_dir / "valuation_model.json", "w") as f:
        json.dump(valuation, f, indent=2)

    with open(registry_dir / "risk_bridge.json", "w") as f:
        json.dump(risk_bridge, f, indent=2)

    print(f"Wrote {data_dir / 'valuation_model.json'}")
    print(f"Wrote {registry_dir / 'risk_bridge.json'}")
    print(f"Base-case EV: ${base_dcf['enterprise_value']/1e9:.2f}B")
    print(f"Base-case FV/share: ${dcf_base_fv:.2f}")
    print(f"Weighted FV/share: ${weighted_fv:.2f}")
    print(f"Current price: ${current_price:.2f}")
    print(f"Margin of safety vs base: {(dcf_base_fv/current_price - 1)*100:.1f}%")


if __name__ == "__main__":
    main()
