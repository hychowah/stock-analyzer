"""Fallback research tools used by orchestrator.py.

These functions mirror the MCP tools that will eventually live in
yfinance_mcp.server (see the extend-yfinance-mcp-research-tools scope).
They are implemented here so the orchestrator can run end-to-end before
those tools are added to the MCP server.  When the server-side tools are
available, orchestrator.py will import them instead.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yfinance as yf

# Matplotlib is imported lazily so the module can be imported in environments
# where only data retrieval is needed.
try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - chart generation will fail gracefully
    matplotlib = None
    plt = None


# ── Helpers ─────────────────────────────────────────────────────────────────


def _safe(value: Any) -> Any:
    """Convert numpy/pandas scalars to JSON-safe Python natives."""
    if value is None:
        return None
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if hasattr(value, "item"):
        return value.item()
    return value


def _first(keys: list[str], mapping: dict[str, Any]) -> Any:
    """Return the first matching key value or None."""
    for k in keys:
        if k in mapping and mapping[k] is not None:
            return mapping[k]
    return None


def _pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / abs(previous)


def _latest(df) -> dict[str, Any] | None:
    """Return the latest column of a financial statement DataFrame as a dict."""
    if df is None or df.empty:
        return None
    col = df.columns[-1]
    return {str(k): _safe(v) for k, v in df[col].items()}


def _column_at(df, offset: int = 0) -> dict[str, Any] | None:
    """Return a financial statement column by offset (0 = latest)."""
    if df is None or df.empty or len(df.columns) <= offset:
        return None
    col = df.columns[-(offset + 1)]
    return {str(k): _safe(v) for k, v in df[col].items()}


def _find_row(rows: dict[str, Any] | None, *candidates: str) -> Any:
    if not rows:
        return None
    for c in candidates:
        for k, v in rows.items():
            if c.lower() in k.lower():
                return v
    return None


def _info_field(t: yf.Ticker, *candidates: str) -> Any:
    info = t.info or {}
    for c in candidates:
        if c in info and info[c] is not None:
            return _safe(info[c])
    return None


def _extract_statement_item(df, *candidates: str, offset: int = 0) -> float | None:
    col = _column_at(df, offset)
    if not col:
        return None
    return _find_row(col, *candidates)


# ── Sector Classification ───────────────────────────────────────────────────


def classify_sector(ticker: str) -> dict:
    """Classify a ticker into a research sector.

    Returns a dict matching sector_config.schema.json fields needed by the
    orchestrator.  The scoring is a pragmatic, yfinance-data-driven
    approximation of the algorithm in prompt_adaptive_v2.md.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}

    sector = (info.get("sector") or "").lower()
    industry = (info.get("industry") or "").lower()
    summary = (info.get("longBusinessSummary") or "").lower()
    name = (info.get("shortName") or info.get("longName") or "").lower()

    scores = {
        "banking": 0.0,
        "insurance": 0.0,
        "growth": 0.0,
        "reit": 0.0,
        "utility": 0.0,
        "cyclical": 0.0,
        "standard": 10.0,  # small default score
    }
    reasons: list[str] = []

    # Banking signals
    if "bank" in industry or "bank" in name or "financial services" in industry:
        scores["banking"] += 50
        reasons.append(f"Industry/name indicates banking ({info.get('industry')})")
    if any(k in summary for k in ("deposit", "lending", "loan portfolio", "net interest income")):
        scores["banking"] += 20

    # Insurance signals
    if "insurance" in industry or "insurance" in name:
        scores["insurance"] += 60
        reasons.append(f"Industry indicates insurance ({info.get('industry')})")

    # REIT signals
    if "reit" in name or "real estate" in sector or "reit" in industry:
        scores["reit"] += 55
        reasons.append(f"Name/sector indicates REIT ({info.get('sector')})")
    if any(k in summary for k in ("real estate investment trust", "property portfolio", "rental income")):
        scores["reit"] += 15

    # Utility signals
    if "utilities" in sector or "utility" in industry:
        scores["utility"] += 55
        reasons.append(f"Sector indicates utility ({info.get('sector')})")
    if any(k in summary for k in ("regulated", "rate base", "rate case", "electric utility")):
        scores["utility"] += 15

    # Cyclical signals
    cyclical_sectors = {"energy", "materials", "industrials", "consumer cyclical"}
    if sector in cyclical_sectors:
        scores["cyclical"] += 30
        reasons.append(f"Sector is cyclical ({info.get('sector')})")
    if any(k in industry for k in ("oil", "gas", "mining", "steel", "auto", "airlines", "semiconductor")):
        scores["cyclical"] += 20
    if any(k in summary for k in ("commodity", "cycle", "capacity utilization")):
        scores["cyclical"] += 10

    # Growth signals (can coexist)
    revenue_growth = _safe(info.get("revenueGrowth"))
    earnings_growth = _safe(info.get("earningsGrowth"))
    fcf = _info_field(t, "freeCashflow")
    revenue = _info_field(t, "totalRevenue")
    sbc = _extract_statement_item(t.cashflow, "Stock Based Compensation")
    rd = _extract_statement_item(t.income_stmt, "Research Development")

    if isinstance(revenue_growth, (int, float)) and revenue_growth > 0.25:
        scores["growth"] += 20
    if isinstance(earnings_growth, (int, float)) and earnings_growth > 0.25:
        scores["growth"] += 10
    if isinstance(fcf, (int, float)) and isinstance(revenue, (int, float)) and revenue > 0:
        if fcf < 0 < revenue:
            scores["growth"] += 20
    if isinstance(sbc, (int, float)) and isinstance(revenue, (int, float)) and revenue > 0:
        if sbc / revenue > 0.05:
            scores["growth"] += 15
            reasons.append("High stock-based compensation relative to revenue")
    if isinstance(rd, (int, float)) and isinstance(revenue, (int, float)) and revenue > 0:
        if rd / revenue > 0.15:
            scores["growth"] += 15

    primary = max(scores, key=scores.get)
    confidence = round(scores[primary] / 100.0, 3)
    is_also_growth = scores["growth"] >= 50 and primary != "growth"
    requires_manual_review = confidence < 0.70

    if requires_manual_review:
        primary = "standard"
        confidence = round(max(confidence, 0.55), 3)

    module_file = f"/workspace-stock-research/sector_{primary}.md"
    secondary_module = (
        "/workspace-stock-research/sector_growth.md" if is_also_growth else None
    )

    substitutions = _build_substitutions(primary, is_also_growth)

    return {
        "ticker": ticker.upper(),
        "primary_sector": primary,
        "confidence": confidence,
        "is_also_growth": is_also_growth,
        "module_file": module_file,
        "secondary_module_file": secondary_module,
        "trigger_reasons": reasons or [f"Defaulted to {primary} based on highest score"],
        "all_scores": {k: round(v, 2) for k, v in scores.items()},
        "substitutions": substitutions,
        "agents_modified": ["agent_0", "agent_2", "agent_5", "agent_12", "agent_13"],
        "agents_unchanged": ["agent_1", "agent_3", "agent_4", "agent_6", "agent_8", "agent_11"],
        "requires_manual_review": requires_manual_review,
        "review_notes": (
            "Sector confidence below 0.70; fell back to standard framework. Human review recommended."
            if requires_manual_review
            else None
        ),
        "classification_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sources": ["yfinance Ticker.info"],
    }


def _build_substitutions(primary: str, is_also_growth: bool) -> dict:
    """Return sector-specific metric substitutions."""
    base = {
        "banking": {
            "valuation_model_primary": "Excess Return Model: BV + (ROE - k) * BV / (k - g)",
            "valuation_model_secondary": "P/B-ROE Regression",
            "roic_equivalent": "ROE / RAROC",
            "pe_equivalent": "P/B",
            "fcf_yield_equivalent": "Div Yield + Buyback Yield",
            "revenue_growth_equivalent": "NII + Fee Income Growth",
            "operating_leverage_equivalent": "Fin. Leverage x NIM Sensitivity",
            "gross_margin_equivalent": "NIM",
            "sbc_analysis_intensity": "low",
            "moat_indicator": "Deposit Franchise",
            "capital_structure_focus": "CET1 / Tier 1",
            "peer_comparison_metrics": ["P/B", "ROE", "NIM", "CET1"],
            "stress_test_scenarios": [
                "Credit downturn: NPL +500bp",
                "Rate shock: +300bp parallel",
                "Liquidity crisis: deposit flight -30%",
                "Regulatory: CET1 req +300bp",
            ],
            "reverse_engineering_target": "Implied ROE from current P/B",
        },
        "insurance": {
            "valuation_model_primary": "Float Valuation / MCEV",
            "valuation_model_secondary": "P/B-ROE Regression",
            "roic_equivalent": "ROE / ROEV",
            "pe_equivalent": "P/B (P&C) or P/EV (Life)",
            "fcf_yield_equivalent": "Inv. Yield on Float + Div",
            "revenue_growth_equivalent": "Premium / Float Growth",
            "operating_leverage_equivalent": "Float Leverage x Inv. Yield",
            "gross_margin_equivalent": "Combined Ratio",
            "sbc_analysis_intensity": "low",
            "moat_indicator": "Float Duration / CR Discipline",
            "capital_structure_focus": "Solvency II / RBC",
            "peer_comparison_metrics": ["P/B", "Combined Ratio", "ROE", "Float"],
            "stress_test_scenarios": [
                "Reserve deficiency: +8% adverse dev",
                "Cat super-year: $250B losses",
                "Rate shock: +300bp ALM",
                "Pricing cycle: soft market CR +10pp",
            ],
            "reverse_engineering_target": "Implied Combined Ratio from P/B",
        },
        "growth": {
            "valuation_model_primary": "Extended DCF (7-10yr) + EV/Revenue sanity check",
            "valuation_model_secondary": "Unit Economics (LTV/CAC)",
            "roic_equivalent": "Unit Economics (LTV/CAC, Burn Multiple)",
            "pe_equivalent": "EV/Revenue",
            "fcf_yield_equivalent": "Burn Multiple / Rule of 40",
            "revenue_growth_equivalent": "ARR Growth / NRR",
            "operating_leverage_equivalent": "Fixed Cost / Lease Spreads",
            "gross_margin_equivalent": "Gross Margin",
            "sbc_analysis_intensity": "critical",
            "moat_indicator": "NRR / Switching Costs",
            "capital_structure_focus": "Cash Runway / Burn",
            "peer_comparison_metrics": ["EV/Rev", "NRR", "Rule of 40", "Gross Margin"],
            "stress_test_scenarios": [
                "Funding winter: cannot raise capital",
                "Growth halves: 30% -> 15%",
                "Churn shock: NRR drops to 90%",
                "SBC cliff: cut 50%, talent leaves",
            ],
            "reverse_engineering_target": "Implied revenue CAGR and FCF margin from EV/Revenue",
        },
        "reit": {
            "valuation_model_primary": "NAV = NOI / Cap Rate - Debt",
            "valuation_model_secondary": "FFO/AFFO Multiple",
            "roic_equivalent": "FFO Yield",
            "pe_equivalent": "P/FFO or P/AFFO",
            "fcf_yield_equivalent": "FFO Yield",
            "revenue_growth_equivalent": "Same-Store NOI Growth",
            "operating_leverage_equivalent": "Regulatory Lag",
            "gross_margin_equivalent": "NOI Margin",
            "sbc_analysis_intensity": "medium",
            "moat_indicator": "Location / WALT",
            "capital_structure_focus": "LTV / Debt Maturity",
            "peer_comparison_metrics": ["P/FFO", "Cap Rate", "WALT", "Occupancy"],
            "stress_test_scenarios": [
                "Cap rate expansion: +200bp",
                "Occupancy shock: -10%",
                "Refinancing crisis: +300bp rates",
                "Rent decline: -10% market rents",
            ],
            "reverse_engineering_target": "Implied cap rate from Price/NAV",
        },
        "utility": {
            "valuation_model_primary": "Rate-Base DCF",
            "valuation_model_secondary": "Dividend Discount Model",
            "roic_equivalent": "Earned vs Allowed ROE",
            "pe_equivalent": "Dividend Yield",
            "fcf_yield_equivalent": "Div Yield + Rate Base Growth",
            "revenue_growth_equivalent": "Rate Base CAGR",
            "operating_leverage_equivalent": "Regulatory Lag",
            "gross_margin_equivalent": "Allowed ROE Spread",
            "sbc_analysis_intensity": "low",
            "moat_indicator": "Regulatory Compact",
            "capital_structure_focus": "Debt/Total Capital",
            "peer_comparison_metrics": ["Div Yield", "Allowed ROE", "Rate Base CAGR"],
            "stress_test_scenarios": [
                "Allowed ROE cut: -200bp",
                "Interest rate spike: +300bp",
                "$5B wildfire liability",
                "Demand destruction: -15%",
            ],
            "reverse_engineering_target": "Implied rate base growth from dividend yield",
        },
        "cyclical": {
            "valuation_model_primary": "TTC Earnings x Normalized EV/EBITDA",
            "valuation_model_secondary": "Replacement Cost Check",
            "roic_equivalent": "Cost Curve Position",
            "pe_equivalent": "TTC EV/EBITDA",
            "fcf_yield_equivalent": "FCF Breakeven Price",
            "revenue_growth_equivalent": "Volume Growth (ex-price)",
            "operating_leverage_equivalent": "Operating Leverage",
            "gross_margin_equivalent": "Cash Cost Margin",
            "sbc_analysis_intensity": "low",
            "moat_indicator": "Cost Curve Position",
            "capital_structure_focus": "Net Debt / TTC EBITDA",
            "peer_comparison_metrics": ["TTC EV/EBITDA", "AISC", "Net Debt/EBITDA"],
            "stress_test_scenarios": [
                "Commodity crash: -40%",
                "Recession: demand -20%",
                "China demand shock: -10%",
                "Overcapacity: +20% new supply",
            ],
            "reverse_engineering_target": "Implied commodity price from current stock price",
        },
        "standard": {
            "valuation_model_primary": "Gordon Growth DCF using FCF",
            "valuation_model_secondary": "EV/EBITDA Multiple Sanity Check",
            "roic_equivalent": "ROIC",
            "pe_equivalent": "P/E",
            "fcf_yield_equivalent": "FCF Yield",
            "revenue_growth_equivalent": "Revenue Growth",
            "operating_leverage_equivalent": "Operating Leverage",
            "gross_margin_equivalent": "Gross Margin",
            "sbc_analysis_intensity": "medium",
            "moat_indicator": "ROIC vs WACC",
            "capital_structure_focus": "Net Debt / EBITDA",
            "peer_comparison_metrics": ["P/E", "EV/EBITDA", "ROIC", "FCF Yield"],
            "stress_test_scenarios": [
                "Recession: revenue -15%",
                "Rate shock: WACC +200bp",
                "Margin compression: -300bp",
                "Competitive disruption: growth -50%",
            ],
            "reverse_engineering_target": "Implied revenue CAGR and FCF margin from P/E",
        },
    }

    sub = base.get(primary, base["standard"]).copy()
    sub["forecast_years"] = 10 if primary == "growth" or is_also_growth else 5
    return sub


# ── Latest Quarter Snapshot ─────────────────────────────────────────────────


def get_latest_quarter_snapshot(ticker: str) -> dict:
    """Build a structured latest-quarter snapshot from yfinance data.

    Returns a dict matching latest_quarter.schema.json.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        q_inc = t.quarterly_income_stmt
        q_bal = t.quarterly_balance_sheet
        q_cf = t.quarterly_cashflow
    except Exception as e:
        return {"error": str(e), "ticker": ticker}

    latest_inc = _column_at(q_inc, 0) or {}
    prev_inc = _column_at(q_inc, 1) or {}
    latest_cf = _column_at(q_cf, 0) or {}

    revenue = _find_row(latest_inc, "Total Revenue", "Revenue")
    prev_revenue = _find_row(prev_inc, "Total Revenue", "Revenue")
    revenue_yoy = None
    if revenue is not None and prev_revenue is not None and prev_revenue != 0:
        revenue_yoy = _pct_change(revenue, prev_revenue)

    ebit = _find_row(latest_inc, "Operating Income", "EBIT")
    ebitda = _find_row(latest_inc, "EBITDA")
    net_income = _find_row(latest_inc, "Net Income", "NetIncome")
    eps = _info_field(t, "trailingEps")

    # Margins
    gross_profit = _find_row(latest_inc, "Gross Profit", "GrossProfit")
    gross_margin = None
    if gross_profit is not None and revenue is not None and revenue != 0:
        gross_margin = gross_profit / revenue
    operating_margin = None
    if ebit is not None and revenue is not None and revenue != 0:
        operating_margin = ebit / revenue
    net_margin = None
    if net_income is not None and revenue is not None and revenue != 0:
        net_margin = net_income / revenue

    # Balance sheet
    latest_bal = _column_at(q_bal, 0) or {}
    total_assets = _find_row(latest_bal, "Total Assets", "TotalAssets")
    total_equity = _find_row(latest_bal, "Stockholders Equity", "Total Stockholder Equity")
    total_debt = _find_row(latest_bal, "Total Debt", "TotalDebt")
    cash = _find_row(latest_bal, "Cash And Cash Equivalents", "Cash")
    net_debt = None
    if total_debt is not None and cash is not None:
        net_debt = total_debt - cash

    # Cash flow
    ocf = _find_row(latest_cf, "Operating Cash Flow", "Total Cash From Operating Activities")
    capex = _find_row(latest_cf, "Capital Expenditure", "Capital Expenditures")
    fcf = None
    if ocf is not None and capex is not None:
        fcf = ocf - abs(capex)
    sbc = _find_row(latest_cf, "Stock Based Compensation")
    sbc_pct_rev = None
    if sbc is not None and revenue is not None and revenue != 0:
        sbc_pct_rev = sbc / revenue

    # Capital returns
    div_yield = _info_field(t, "dividendYield")
    if isinstance(div_yield, (int, float)) and div_yield > 1:
        div_yield = div_yield / 100.0

    # Guidance (best effort from info)
    guidance_change = None
    guidance_notes = "Guidance not available via yfinance; populate from earnings release."
    if info.get("revenueGrowth") is not None:
        guidance_change = "unchanged"

    fiscal_period = "latest_fiscal_quarter"
    if q_inc is not None and not q_inc.empty:
        fiscal_period = str(q_inc.columns[-1])[:10]

    snapshot = {
        "ticker": ticker.upper(),
        "session_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "fiscal_period": fiscal_period,
        "filing_date": None,
        "sources": [
            {
                "name": "yfinance quarterly financials",
                "url": None,
                "accessed": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        ],
        "revenue_earnings": {
            "total_revenue": revenue,
            "revenue_yoy_pct": revenue_yoy,
            "revenue_qoq_pct": None,
            "ebit": ebit,
            "ebitda": ebitda,
            "net_income": net_income,
            "eps_reported": eps,
            "eps_consensus": _info_field(t, "epsCurrentYear", "epsForward"),
            "beat_miss_eps": None,
            "currency": info.get("currency"),
            "unit": "units",
        },
        "guidance": {
            "revenue_guidance": None,
            "eps_guidance": _info_field(t, "epsForward"),
            "capex_guidance": None,
            "margin_guidance": None,
            "guidance_change": guidance_change,
            "guidance_notes": guidance_notes,
        },
        "segment_performance": [],
        "sector_kpis": {},
        "margins_costs": {
            "gross_margin_pct": gross_margin,
            "operating_margin_pct": operating_margin,
            "net_margin_pct": net_margin,
            "cost_inflation_notes": None,
            "pricing_power_notes": None,
        },
        "balance_sheet": {
            "total_assets": total_assets,
            "total_equity": total_equity,
            "total_debt": total_debt,
            "net_debt": net_debt,
            "cash_and_equivalents": cash,
            "leverage_ratio": None,
            "capital_ratio": None,
            "reserves": None,
            "inventory": _find_row(latest_bal, "Inventory"),
            "working_capital": None,
        },
        "cash_flow": {
            "operating_cash_flow": ocf,
            "free_cash_flow": fcf,
            "capex": capex,
            "sbc": sbc,
            "sbc_pct_revenue": sbc_pct_rev,
        },
        "capital_returns": {
            "dividend_per_share": _info_field(t, "dividendRate"),
            "dividend_yield_pct": div_yield,
            "buyback_authorization": None,
            "buyback_executed": None,
            "capital_raise": None,
        },
        "management_tone": {
            "demand_commentary": None,
            "pricing_environment": None,
            "supply_chain": None,
            "hiring_backlog": None,
            "overall_assessment": None,
        },
        "risks": [],
        "override_log": [],
    }

    # Add simple sector-specific KPI placeholders
    sector = (info.get("sector") or "").lower()
    industry = (info.get("industry") or "").lower()
    if "bank" in industry or "bank" in info.get("shortName", "").lower():
        snapshot["sector_kpis"] = {
            "NIM": None,
            "CET1": None,
            "NPL": None,
            "loan_growth": None,
        }
    elif "insurance" in industry:
        snapshot["sector_kpis"] = {
            "combined_ratio": None,
            "float": None,
            "reserve_development": None,
        }
    elif "reit" in info.get("shortName", "").lower() or "real estate" in sector:
        snapshot["sector_kpis"] = {
            "same_store_noi_growth": None,
            "occupancy": None,
            "lease_spreads": None,
        }
    elif "utilities" in sector:
        snapshot["sector_kpis"] = {
            "rate_base": None,
            "allowed_roe": None,
            "regulatory_lag": None,
        }
    elif any(k in industry for k in ("oil", "gas", "mining", "steel")):
        snapshot["sector_kpis"] = {
            "AISC": None,
            "volume": None,
            "commodity_price_realization": None,
        }
    else:
        snapshot["sector_kpis"] = {
            "ARR": None,
            "NRR": None,
            "gross_margin": gross_margin,
        }

    return snapshot


# ── Valuation Model ─────────────────────────────────────────────────────────


def compute_valuation_model(ticker: str, sector: str = "standard", scenario: str = "base") -> dict:
    """Compute a sector-appropriate valuation model.

    Returns base/bull/bear sensitivity plus the selected scenario output.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:
        return {"error": str(e), "ticker": ticker, "sector": sector}

    price = _info_field(t, "currentPrice", "regularMarketPrice", "previousClose")
    shares = _info_field(t, "sharesOutstanding")
    market_cap = _info_field(t, "marketCap")
    book_value = _info_field(t, "bookValue")
    total_equity = _info_field(t, "totalStockholderEquity")

    # Income / cash flow items (annual, with info fallbacks)
    inc = _column_at(t.income_stmt, 0) or {}
    cf = _column_at(t.cashflow, 0) or {}
    qcf = _column_at(t.quarterly_cashflow, 0) or {}
    revenue = _info_field(t, "totalRevenue") or _find_row(inc, "Total Revenue", "Revenue")
    net_income = _info_field(t, "netIncome") or _find_row(inc, "Net Income", "NetIncome")

    fcf = _info_field(t, "freeCashflow")
    if fcf is None or (isinstance(fcf, float) and math.isnan(fcf)):
        fcf = _find_row(cf, "Free Cash Flow")
    if fcf is None or (isinstance(fcf, float) and math.isnan(fcf)):
        fcf = _find_row(qcf, "Free Cash Flow")
    if fcf is None or (isinstance(fcf, float) and math.isnan(fcf)):
        ocf = _find_row(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
        capex = _find_row(cf, "Capital Expenditure", "Capital Expenditures")
        if ocf is not None and capex is not None:
            fcf = ocf - abs(capex)

    sbc = _find_row(cf, "Stock Based Compensation") or _find_row(qcf, "Stock Based Compensation")
    if sbc is not None and fcf is not None and not (isinstance(fcf, float) and math.isnan(fcf)):
        fcf = fcf - sbc

    dividend_rate = _info_field(t, "dividendRate")
    beta = _info_field(t, "beta") or 1.0

    # Cost of equity (CAPM proxy)
    risk_free = 0.04
    market_premium = 0.05
    cost_of_equity = risk_free + beta * market_premium

    sector = (sector or "standard").lower()
    scenario = (scenario or "base").lower()

    if sector == "banking":
        model = _valuation_banking(price, shares, book_value, net_income, total_equity, cost_of_equity)
    elif sector == "reit":
        model = _valuation_reit(price, shares, market_cap, book_value, net_income, revenue, cost_of_equity)
    elif sector == "utility":
        model = _valuation_utility(price, shares, dividend_rate, cost_of_equity)
    elif sector == "growth":
        model = _valuation_growth(price, shares, revenue, fcf, cost_of_equity)
    elif sector == "cyclical":
        model = _valuation_cyclical(price, shares, revenue, net_income, cost_of_equity)
    else:
        model = _valuation_standard(price, shares, fcf, cost_of_equity)

    model["ticker"] = ticker.upper()
    model["sector"] = sector
    model["scenario_requested"] = scenario
    model["current_price"] = price
    model["market_cap"] = market_cap
    model["shares_outstanding"] = shares
    model["cost_of_equity_pct"] = round(cost_of_equity * 100, 2)
    model["beta"] = beta

    selected = model.get("scenarios", {}).get(scenario)
    if selected:
        model["selected_scenario"] = selected
    else:
        model["selected_scenario"] = model.get("scenarios", {}).get("base")

    return model


def _valuation_standard(price, shares, fcf, cost_of_equity):
    """Gordon Growth DCF using FCF."""
    if not fcf or not shares or fcf <= 0:
        return {
            "model": "Gordon Growth DCF (FCF)",
            "error": "Positive FCF required for base-case DCF.",
            "scenarios": {},
        }
    fcf_per_share = fcf / shares
    scenarios = {}
    for name, g, ce_adj in (
        ("bear", 0.01, 0.015),
        ("base", 0.025, 0.0),
        ("bull", 0.04, -0.005),
    ):
        k = max(cost_of_equity + ce_adj, g + 0.01)
        fv = fcf_per_share * (1 + g) / (k - g)
        scenarios[name] = {
            "growth_rate_pct": round(g * 100, 2),
            "wacc_pct": round(k * 100, 2),
            "fair_value_per_share": round(fv, 2),
            "upside_pct": round((fv - price) / price * 100, 2) if price else None,
        }
    return {"model": "Gordon Growth DCF (FCF)", "scenarios": scenarios}


def _valuation_banking(price, shares, book_value, net_income, total_equity, cost_of_equity):
    """Excess Return Model: BV + (ROE - k) * BV / (k - g)."""
    if not total_equity or not net_income or total_equity <= 0:
        return {
            "model": "Excess Return Model (Banking)",
            "error": "Book value and net income required.",
            "scenarios": {},
        }
    bv_per_share = (book_value * shares) / shares if book_value and shares else total_equity / shares if shares else None
    roe = net_income / total_equity
    scenarios = {}
    for name, roe_adj, g, ce_adj in (
        ("bear", -0.03, 0.01, 0.01),
        ("base", 0.0, 0.02, 0.0),
        ("bull", 0.02, 0.03, -0.005),
    ):
        k = max(cost_of_equity + ce_adj, 0.06)
        g = min(g, k - 0.005)
        roe_s = max(roe + roe_adj, k + 0.005)
        if bv_per_share:
            fv = bv_per_share + (roe_s - k) * bv_per_share / (k - g)
        else:
            fv = None
        scenarios[name] = {
            "roe_pct": round(roe_s * 100, 2),
            "growth_rate_pct": round(g * 100, 2),
            "cost_of_equity_pct": round(k * 100, 2),
            "fair_value_per_share": round(fv, 2) if fv else None,
            "upside_pct": round((fv - price) / price * 100, 2) if fv and price else None,
        }
    return {
        "model": "Excess Return Model (Banking)",
        "latest_roe_pct": round(roe * 100, 2),
        "book_value_per_share": round(bv_per_share, 2) if bv_per_share else None,
        "scenarios": scenarios,
    }


def _valuation_reit(price, shares, market_cap, book_value, net_income, revenue, cost_of_equity):
    """NAV approximation using price/book or cap rate proxy."""
    if not market_cap or not shares:
        return {
            "model": "NAV Approximation (REIT)",
            "error": "Market cap and shares required.",
            "scenarios": {},
        }
    bv_per_share = book_value if book_value else None
    cap_rates = {"bear": 0.07, "base": 0.055, "bull": 0.045}
    scenarios = {}
    # Use P/B proxy if NOI unavailable
    for name, cr in cap_rates.items():
        if bv_per_share:
            # Assume book value approximates NAV; adjust for cap rate
            implied_nav = bv_per_share * (0.06 / cr)
        else:
            implied_nav = market_cap / shares
        scenarios[name] = {
            "cap_rate_pct": round(cr * 100, 2),
            "fair_value_per_share": round(implied_nav, 2),
            "upside_pct": round((implied_nav - price) / price * 100, 2) if price else None,
        }
    return {
        "model": "NAV Approximation (REIT)",
        "price_to_book": round(price / bv_per_share, 2) if bv_per_share and price else None,
        "scenarios": scenarios,
    }


def _valuation_utility(price, shares, dividend_rate, cost_of_equity):
    """Dividend discount model proxy."""
    if not dividend_rate or not price:
        return {
            "model": "Dividend Discount Model Proxy (Utility)",
            "error": "Dividend rate and price required.",
            "scenarios": {},
        }
    scenarios = {}
    for name, g, ce_adj in (
        ("bear", 0.01, 0.01),
        ("base", 0.03, 0.0),
        ("bull", 0.045, -0.005),
    ):
        k = max(cost_of_equity + ce_adj, g + 0.01)
        d1 = dividend_rate * (1 + g)
        fv = d1 / (k - g)
        scenarios[name] = {
            "growth_rate_pct": round(g * 100, 2),
            "cost_of_equity_pct": round(k * 100, 2),
            "fair_value_per_share": round(fv, 2),
            "upside_pct": round((fv - price) / price * 100, 2),
        }
    return {
        "model": "Dividend Discount Model Proxy (Utility)",
        "current_dividend_rate": dividend_rate,
        "dividend_yield_pct": round(dividend_rate / price * 100, 2),
        "scenarios": scenarios,
    }


def _valuation_growth(price, shares, revenue, fcf, cost_of_equity):
    """Extended DCF / EV/Revenue sanity check."""
    if not revenue or not shares:
        return {
            "model": "Extended DCF / EV/Revenue Sanity Check (Growth)",
            "error": "Revenue and shares required.",
            "scenarios": {},
        }
    rev_per_share = revenue / shares
    scenarios = {}
    for name, ev_rev, growth in (
        ("bear", 3.0, 0.10),
        ("base", 6.0, 0.18),
        ("bull", 10.0, 0.28),
    ):
        fv = rev_per_share * ev_rev
        scenarios[name] = {
            "ev_revenue_multiple": ev_rev,
            "revenue_growth_pct": round(growth * 100, 2),
            "fair_value_per_share": round(fv, 2),
            "upside_pct": round((fv - price) / price * 100, 2) if price else None,
        }
    return {
        "model": "Extended DCF / EV/Revenue Sanity Check (Growth)",
        "revenue_per_share": round(rev_per_share, 2),
        "fcf_per_share": round(fcf / shares, 2) if fcf and shares else None,
        "scenarios": scenarios,
    }


def _valuation_cyclical(price, shares, revenue, net_income, cost_of_equity):
    """TTC earnings proxy using normalized EV/EBITDA."""
    if not revenue or not shares:
        return {
            "model": "TTC Earnings Proxy (Cyclical)",
            "error": "Revenue and shares required.",
            "scenarios": {},
        }
    # Proxy: mid-cycle EBIT ~ 10-15% of revenue
    base_ebit = revenue * 0.12
    scenarios = {}
    for name, margin, multiple in (
        ("bear", 0.08, 5.0),
        ("base", 0.12, 7.0),
        ("bull", 0.16, 9.0),
    ):
        ebit = revenue * margin
        ev = ebit * multiple
        # crude equity value: EV less 1x revenue debt proxy
        equity = ev - revenue * 0.3
        fv = equity / shares if shares else None
        scenarios[name] = {
            "midcycle_ebit_margin_pct": round(margin * 100, 2),
            "ev_ebitda_multiple": multiple,
            "fair_value_per_share": round(fv, 2) if fv else None,
            "upside_pct": round((fv - price) / price * 100, 2) if fv and price else None,
        }
    return {
        "model": "TTC Earnings Proxy (Cyclical)",
        "revenue_per_share": round(revenue / shares, 2),
        "scenarios": scenarios,
    }


# ── Peer Snapshot ───────────────────────────────────────────────────────────


def get_peer_snapshot(ticker: str, peers: list[str]) -> dict:
    """Return combined key metrics for ticker + peers."""
    peers = [p.upper() for p in (peers or [])]
    all_tickers = [ticker.upper()] + peers
    result = {"target": ticker.upper(), "peers": peers, "data": {}}
    for sym in all_tickers:
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            result["data"][sym] = {
                "price": _safe(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")),
                "market_cap": _safe(info.get("marketCap")),
                "pe_trailing": _safe(info.get("trailingPE")),
                "pe_forward": _safe(info.get("forwardPE")),
                "pb": _safe(info.get("priceToBook")),
                "dividend_yield_pct": _safe(info.get("dividendYield")),
                "revenue_growth_pct": _safe(info.get("revenueGrowth")),
                "profit_margin_pct": _safe(info.get("profitMargins")),
                "beta": _safe(info.get("beta")),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
            }
        except Exception as e:
            result["data"][sym] = {"error": str(e)}
    return result


# ── Charts ──────────────────────────────────────────────────────────────────


def generate_charts(ticker: str, output_dir: str) -> dict:
    """Generate price trend and valuation sensitivity PNG charts.

    Returns paths to created files.  Requires matplotlib.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {}

    if plt is None:
        return {
            "ticker": ticker.upper(),
            "error": "matplotlib not installed",
            "output_dir": str(out),
            "paths": paths,
        }

    ticker = ticker.upper()
    t = yf.Ticker(ticker)

    # --- Price trend with MAs and volume ---
    try:
        hist = t.history(period="1y")
        if hist is not None and not hist.empty:
            fig, axes = plt.subplots(2, 1, figsize=(10, 7), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
            ax_price, ax_vol = axes
            ax_price.plot(hist.index, hist["Close"], label="Close", linewidth=1.2)
            hist["MA50"] = hist["Close"].rolling(50).mean()
            hist["MA200"] = hist["Close"].rolling(200).mean()
            ax_price.plot(hist.index, hist["MA50"], label="50 MA", alpha=0.8)
            ax_price.plot(hist.index, hist["MA200"], label="200 MA", alpha=0.8)
            ax_price.set_title(f"{ticker} Price Trend & Moving Averages")
            ax_price.set_ylabel("Price")
            ax_price.legend()
            ax_price.grid(True, alpha=0.3)

            ax_vol.bar(hist.index, hist["Volume"], color="gray", alpha=0.6)
            ax_vol.set_ylabel("Volume")
            ax_vol.set_xlabel("Date")
            ax_vol.grid(True, alpha=0.3)

            price_path = out / "price_trend.png"
            plt.tight_layout()
            plt.savefig(price_path, dpi=120)
            plt.close(fig)
            paths["price_trend"] = str(price_path)
    except Exception as e:
        paths["price_trend_error"] = str(e)

    # --- Valuation sensitivity grid ---
    # Prefer the session's Agent 5 valuation model if available.
    try:
        session_valuation_path = Path(output_dir).parent / "data" / "valuation_model.json"
        if session_valuation_path.exists():
            model = json.loads(session_valuation_path.read_text())
        else:
            model = compute_valuation_model(ticker, sector="standard")
        scenario_names = ["bear", "base", "bull"]
        fair_values = [model.get("dcf_model", {}).get("scenarios", {}).get(s, {}).get("fair_value_per_share_usd") for s in scenario_names]
        current_price = model.get("inputs", {}).get("current_price_usd") or model.get("current_price")
        if any(v is not None for v in fair_values):
            fig, ax = plt.subplots(figsize=(8, 5))
            colors = ["red", "blue", "green"]
            bars = ax.bar(scenario_names, [v if v is not None else 0 for v in fair_values], color=colors, alpha=0.7)
            if current_price:
                ax.axhline(current_price, color="black", linestyle="--", label="Current Price")
            ax.set_title(f"{ticker} Fair Value Sensitivity")
            ax.set_ylabel("Fair Value per Share")
            ax.legend()
            ax.grid(True, alpha=0.3, axis="y")
            for bar, val in zip(bars, fair_values):
                if val is not None:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"${val:.2f}", ha="center", va="bottom")

            sens_path = out / "valuation_sensitivity.png"
            plt.tight_layout()
            plt.savefig(sens_path, dpi=120)
            plt.close(fig)
            paths["valuation_sensitivity"] = str(sens_path)
    except Exception as e:
        paths["valuation_sensitivity_error"] = str(e)

    return {"ticker": ticker, "output_dir": str(out), "paths": paths}
