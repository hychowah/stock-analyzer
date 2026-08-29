"""Research-oriented tools that extend the base yfinance MCP server.

These tools support the adaptive stock-research framework by adding sector
classification, latest-quarter snapshots, sector-aware valuation, chart
generation, and peer comparison.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any

from .utils import df_to_records, safe_value, series_to_dict


# Sectors supported by the research framework.
SECTOR_MODULES = {
    "banking": "harness/modules/sector_banking.md",
    "insurance": "harness/modules/sector_insurance.md",
    "growth": "harness/modules/sector_growth.md",
    "reit": "harness/modules/sector_reit.md",
    "utility": "harness/modules/sector_utility.md",
    "cyclical": "harness/modules/sector_cyclical.md",
    "standard": None,
}


def _latest_column(df: Any) -> Any:
    """Return the most recent column of a financial statement DataFrame.

    yfinance statement columns are ordered newest-first, so the latest
    period is at index 0.
    """
    if df is None or df.empty:
        return None
    df = df.T if hasattr(df, "T") else df
    return df.iloc[0] if len(df) > 0 else None


def _get_item(series: Any, keys: list[str], default: float | None = None) -> float | None:
    """Fetch the first available key from a Series/dict."""
    if series is None:
        return default
    if hasattr(series, "get"):
        for key in keys:
            val = series.get(key)
            if val is not None:
                return float(val) if isinstance(val, (int, float)) else val
    return default


def _safe_float(value: Any, default: float | None = None) -> float | None:
    """Convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _info_to_text(info: dict) -> str:
    """Build a single lower-case text blob from info fields for keyword matching."""
    parts = [
        info.get("sector", ""),
        info.get("industry", ""),
        info.get("longBusinessSummary", ""),
        info.get("shortName", ""),
        info.get("longName", ""),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def _keyword_score(text: str, keywords: list[str]) -> int:
    """Count keyword occurrences in text."""
    return sum(1 for kw in keywords if kw in text)


# ── Sector Classification ────────────────────────────────────────────────────


def classify_sector(ticker: str) -> dict:
    """Classify a ticker into a research sector using yfinance metadata.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with primary_sector, confidence (0-1), is_also_growth,
        trigger_reasons, and suggested_module_file.
    """
    import yfinance as yf

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        text = _info_to_text(info)

        # Gather financial statement hints.
        inc = None
        bs = None
        cf = None
        try:
            inc = _latest_column(t.quarterly_income_stmt)
        except Exception:
            pass
        try:
            bs = _latest_column(t.quarterly_balance_sheet)
        except Exception:
            pass
        try:
            cf = _latest_column(t.quarterly_cashflow)
        except Exception:
            pass

        # Extract useful ratios.
        revenue = _safe_float(_get_item(inc, ["Total Revenue", "TotalRevenue", "Revenue"]))
        net_income = _safe_float(_get_item(inc, ["Net Income", "NetIncome"]))
        fcf = _safe_float(_get_item(cf, ["Free Cash Flow", "FreeCashFlow"]))
        sbc = _safe_float(_get_item(cf, ["Stock Based Compensation", "StockBasedCompensation"]))
        total_assets = _safe_float(_get_item(bs, ["Total Assets", "TotalAssets"]))
        total_debt = _safe_float(_get_item(bs, ["Total Debt", "TotalDebt"]))
        book_value = _safe_float(_get_item(bs, ["Stockholders Equity", "StockholdersEquity", "Total Stockholder Equity"]))
        dividend_yield = _safe_float(info.get("dividendYield"))
        beta = _safe_float(info.get("beta"))
        trailing_pe = _safe_float(info.get("trailingPE"))
        price_to_book = _safe_float(info.get("priceToBook"))

        # Revenue growth (try multiple keys).
        revenue_growth = _safe_float(
            info.get("revenueGrowth")
            or info.get("revenueQuarterlyGrowth")
            or info.get("earningsGrowth")
        )

        scores: dict[str, float] = {
            "banking": 0.0,
            "insurance": 0.0,
            "reit": 0.0,
            "utility": 0.0,
            "cyclical": 0.0,
            "growth": 0.0,
            "standard": 0.0,
        }
        triggers: dict[str, list[str]] = {k: [] for k in scores}

        # Banking keywords.
        bank_kws = [
            "bank", "banking", "commercial bank", "investment bank",
            "savings", "credit union", "thrift", "mortgage", "lending",
            "net interest income", "deposit", "loan", "cel1", "tier 1",
        ]
        bank_score = _keyword_score(text, bank_kws)
        if bank_score > 0:
            scores["banking"] += bank_score * 0.3
            triggers["banking"].append(f"banking keywords ({bank_score})")
        if "financial services" in text and (bank_score > 0 or "asset management" in text):
            scores["banking"] += 0.4
            triggers["banking"].append("financial-services sector")
        # Strong GICS sector confirmation.
        if info.get("sector", "").lower() == "financial services" and "bank" in info.get("industry", "").lower():
            scores["banking"] += 2.0
            triggers["banking"].append("Financial Services + bank industry")
        if total_assets and book_value and total_assets > 0 and (book_value / total_assets) > 0.08:
            scores["banking"] += 0.2
            triggers["banking"].append("high equity/assets ratio")

        # Insurance keywords.
        ins_kws = [
            "insurance", "insurer", "underwriting", "premium", "claims",
            "combined ratio", "float", "life insurance", "property & casualty",
        ]
        ins_score = _keyword_score(text, ins_kws)
        if ins_score > 0:
            scores["insurance"] += ins_score * 0.4
            triggers["insurance"].append(f"insurance keywords ({ins_score})")

        # REIT keywords.
        reit_kws = [
            "reit", "real estate investment trust", "net operating income",
            "noi", "occupancy", "lease", "property portfolio", "real estate",
        ]
        reit_score = _keyword_score(text, reit_kws)
        if reit_score > 0:
            scores["reit"] += reit_score * 0.45
            triggers["reit"].append(f"REIT keywords ({reit_score})")
        # Strong GICS sector confirmation.
        if info.get("sector", "").lower() == "real estate":
            scores["reit"] += 1.5
            triggers["reit"].append("Real Estate sector")
        # yfinance returns dividendYield as a percentage number (e.g. 4.5 for 4.5%).
        if dividend_yield and dividend_yield > 3.0:
            scores["reit"] += 0.15
            triggers["reit"].append(f"high dividend yield ({dividend_yield:.2f}%)")

        # Utility keywords.
        util_kws = [
            "utility", "utilities", "electric", "gas distribution",
            "water utility", "rate base", "regulated utility", "transmission",
        ]
        util_score = _keyword_score(text, util_kws)
        if util_score > 0:
            scores["utility"] += util_score * 0.4
            triggers["utility"].append(f"utility keywords ({util_score})")
        # Strong GICS sector confirmation.
        if info.get("sector", "").lower() == "utilities":
            scores["utility"] += 1.5
            triggers["utility"].append("Utilities sector")
        if dividend_yield and dividend_yield > 2.5:
            scores["utility"] += 0.15
            triggers["utility"].append(f"dividend yield ({dividend_yield:.2f}%)")

        # Cyclical keywords / metrics.
        cyc_kws = [
            "mining", "oil", "gas", "steel", "aluminum", "copper",
            "commodity", "airline", "automotive", "semiconductor",
            "construction", "shipping", "chemical", "materials",
        ]
        cyc_score = _keyword_score(text, cyc_kws)
        if cyc_score > 0:
            scores["cyclical"] += cyc_score * 0.3
            triggers["cyclical"].append(f"cyclical keywords ({cyc_score})")
        if beta and beta > 1.15:
            scores["cyclical"] += 0.2
            triggers["cyclical"].append(f"high beta ({beta:.2f})")
        cyclical_sectors = {"energy", "materials", "industrials"}
        if info.get("sector", "").lower() in cyclical_sectors:
            scores["cyclical"] += 1.0
            triggers["cyclical"].append(f"cyclical GICS sector ({info.get('sector')})")

        # Growth keywords / metrics.
        growth_kws = [
            "software", "saas", "cloud", "platform", "fintech",
            "biotech", "biotechnology", "artificial intelligence", "ai ",
            "subscription", "recurring revenue", "network effect",
        ]
        growth_score = _keyword_score(text, growth_kws)
        if growth_score > 0:
            scores["growth"] += growth_score * 0.25
            triggers["growth"].append(f"growth keywords ({growth_score})")
        if revenue_growth and revenue_growth > 0.20:
            scores["growth"] += 0.35
            triggers["growth"].append(f"high revenue growth ({revenue_growth:.1%})")
        if revenue and sbc and revenue > 0 and (sbc / revenue) > 0.05:
            scores["growth"] += 0.25
            triggers["growth"].append(f"high SBC/revenue ({sbc / revenue:.1%})")
        if fcf is not None and revenue and revenue > 0 and fcf / revenue < 0.02:
            scores["growth"] += 0.15
            triggers["growth"].append("low/negative FCF margin")
        if trailing_pe and trailing_pe > 40:
            scores["growth"] += 0.1
            triggers["growth"].append(f"high P/E ({trailing_pe:.1f})")

        # Standard base score.
        scores["standard"] = 0.25

        primary = max(scores, key=scores.get)
        primary_score = scores[primary]
        second_score = sorted(scores.values(), reverse=True)[1]

        # Confidence = primary score / sum of scores, with a floor adjustment.
        total = sum(scores.values()) or 1.0
        confidence = round(primary_score / total, 3)
        if confidence < 0.5:
            confidence = round(max(confidence, 0.35), 3)

        # Determine if the company also has growth characteristics.
        is_also_growth = (
            primary in {"banking", "utility", "reit", "insurance"}
            and scores["growth"] > 0.5
        )
        if primary == "growth":
            is_also_growth = False

        manual_review = confidence < 0.70
        if primary_score < 0.5 or confidence < 0.70:
            if primary != "standard":
                triggers["standard"].append(
                    f"confidence {confidence} below 0.70; fallback to standard"
                )
            primary = "standard"
            confidence = round(min(confidence, 0.65), 3)
            manual_review = True

        module_file = SECTOR_MODULES.get(primary)

        return {
            "ticker": ticker,
            "primary_sector": primary,
            "confidence": confidence,
            "is_also_growth": is_also_growth,
            "manual_review_recommended": manual_review,
            "trigger_reasons": {k: v for k, v in triggers.items() if v},
            "suggested_module_file": module_file,
            "all_scores": {k: round(v, 3) for k, v in scores.items()},
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ── Latest Quarter Snapshot ──────────────────────────────────────────────────


def _extract_guidance(info: dict) -> dict:
    """Attempt to surface any guidance-like fields from yfinance info."""
    guidance = {}
    for key in [
        "revenueGrowth",
        "earningsGrowth",
        "targetHighPrice",
        "targetLowPrice",
        "targetMeanPrice",
        "targetMedianPrice",
        "recommendationKey",
        "numberOfAnalystOpinions",
    ]:
        val = info.get(key)
        if val is not None:
            guidance[key] = safe_value(val)
    return guidance


def _statement_records(df: Any) -> list[dict]:
    """Convert a statement DataFrame to records, newest first."""
    if df is None or df.empty:
        return []
    return df_to_records(df.T.reset_index().rename(columns={"index": "period"}))


def get_latest_quarter_snapshot(ticker: str) -> dict:
    """Fetch the most recent quarterly snapshot for a ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Structured dict matching the latest_quarter.json schema.
    """
    import yfinance as yf

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        fi = t.fast_info

        # Income statement.
        inc_latest = _latest_column(t.quarterly_income_stmt)
        revenue = _safe_float(_get_item(inc_latest, ["Total Revenue", "TotalRevenue", "Revenue"]))
        ebit = _safe_float(_get_item(inc_latest, ["EBIT", "Operating Income", "OperatingIncome"]))
        ebitda = _safe_float(_get_item(inc_latest, ["EBITDA"]))
        net_income = _safe_float(_get_item(inc_latest, ["Net Income", "NetIncome"]))
        gross_profit = _safe_float(_get_item(inc_latest, ["Gross Profit", "GrossProfit"]))

        # Balance sheet.
        bs_latest = _latest_column(t.quarterly_balance_sheet)
        total_assets = _safe_float(_get_item(bs_latest, ["Total Assets", "TotalAssets"]))
        total_debt = _safe_float(_get_item(bs_latest, ["Total Debt", "TotalDebt"]))
        book_value = _safe_float(_get_item(bs_latest, ["Stockholders Equity", "StockholdersEquity", "Total Stockholder Equity"]))
        cash = _safe_float(_get_item(bs_latest, ["Cash And Cash Equivalents", "CashAndCashEquivalents", "Cash"]))

        # Cash flow.
        cf_latest = _latest_column(t.quarterly_cashflow)
        operating_cash_flow = _safe_float(_get_item(cf_latest, ["Operating Cash Flow", "OperatingCashFlow", "Total Cash From Operating Activities"]))
        capex = _safe_float(_get_item(cf_latest, ["Capital Expenditure", "CapitalExpenditure", "Capital Expenditures"]))
        free_cash_flow = _safe_float(_get_item(cf_latest, ["Free Cash Flow", "FreeCashFlow"]))
        dividends_paid = _safe_float(_get_item(cf_latest, ["Dividends Paid", "DividendsPaid", "Common Stock Dividend Paid"]))
        buybacks = _safe_float(_get_item(cf_latest, ["Repurchase Of Capital Stock", "RepurchaseOfCapitalStock", "Buybacks"]))
        sbc = _safe_float(_get_item(cf_latest, ["Stock Based Compensation", "StockBasedCompensation"]))

        if free_cash_flow is None and operating_cash_flow is not None and capex is not None:
            free_cash_flow = operating_cash_flow - capex

        # Margins.
        margins = {}
        if revenue and revenue != 0:
            margins["gross_margin"] = safe_value(gross_profit / revenue) if gross_profit is not None else None
            margins["operating_margin"] = safe_value(ebit / revenue) if ebit is not None else None
            margins["net_margin"] = safe_value(net_income / revenue) if net_income is not None else None
            margins["sbc_over_revenue"] = safe_value(sbc / revenue) if sbc is not None else None

        # Analyst estimates (DataFrames in yfinance 1.5+).
        earnings_est = []
        revenue_est = []
        try:
            ee = t.earnings_estimate
            if ee is not None and not (hasattr(ee, "empty") and ee.empty):
                earnings_est = df_to_records(ee)
        except Exception:
            pass
        try:
            re_ = t.revenue_estimate
            if re_ is not None and not (hasattr(re_, "empty") and re_.empty):
                revenue_est = df_to_records(re_)
        except Exception:
            pass

        # Period label (best effort).
        period = None
        try:
            stmt = t.quarterly_income_stmt
            if stmt is not None and not stmt.empty:
                period = str(stmt.columns[-1])
        except Exception:
            pass

        snapshot = {
            "ticker": ticker,
            "period": period,
            "as_of": datetime.now().isoformat(),
            "revenue": {
                "total_revenue": safe_value(revenue),
                "gross_profit": safe_value(gross_profit),
                "ebit": safe_value(ebit),
                "ebitda": safe_value(ebitda),
                "net_income": safe_value(net_income),
            },
            "margins": margins,
            "balance_sheet": {
                "total_assets": safe_value(total_assets),
                "total_debt": safe_value(total_debt),
                "stockholders_equity": safe_value(book_value),
                "cash": safe_value(cash),
            },
            "cash_flow": {
                "operating_cash_flow": safe_value(operating_cash_flow),
                "capex": safe_value(capex),
                "free_cash_flow": safe_value(free_cash_flow),
                "stock_based_compensation": safe_value(sbc),
            },
            "capital_returns": {
                "dividends_paid": safe_value(dividends_paid),
                "buybacks": safe_value(buybacks),
            },
            "guidance": _extract_guidance(info),
            "estimates": {
                "earnings": earnings_est,
                "revenue": revenue_est,
            },
            "sector_kpis": {},
            "source": "yfinance",
        }

        # Add latest price context.
        price_data = {}
        for attr in ["last_price", "market_cap", "shares", "year_high", "year_low", "fifty_day_average", "two_hundred_day_average"]:
            try:
                price_data[attr] = safe_value(getattr(fi, attr, None))
            except Exception:
                pass
        snapshot["price"] = price_data

        return snapshot
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ── Valuation Model ──────────────────────────────────────────────────────────


def _weighted_average_cost_of_equity(info: dict, beta: float | None = None) -> float:
    """Estimate cost of equity using CAPM with conservative defaults."""
    if beta is None:
        beta = _safe_float(info.get("beta"), 1.0)
    beta = max(0.5, min(beta, 2.0))
    risk_free = 0.045  # 10-year treasury proxy
    market_premium = 0.05
    return risk_free + beta * market_premium


def compute_valuation_model(
    ticker: str,
    sector: str = "standard",
    scenario: str = "base",
) -> dict:
    """Compute a sector-aware valuation model for a ticker.

    Args:
        ticker: Stock ticker symbol.
        sector: One of banking, insurance, growth, reit, utility, cyclical, standard.
        scenario: One of base, bull, bear (sensitivity tag).

    Returns:
        dict with model inputs, per-share fair value, and base/bull/bear sensitivities.
    """
    import yfinance as yf

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        fi = t.fast_info
        price = _safe_float(
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or getattr(fi, "last_price", None)
        )
        shares = _safe_float(
            info.get("sharesOutstanding")
            or getattr(fi, "shares", None)
        )
        market_cap = _safe_float(
            info.get("marketCap")
            or getattr(fi, "market_cap", None)
        )

        # Latest annual/TTM financials.
        inc = _latest_column(t.income_stmt)
        if inc is None:
            inc = _latest_column(t.quarterly_income_stmt)
        bs = _latest_column(t.balance_sheet)
        if bs is None:
            bs = _latest_column(t.quarterly_balance_sheet)
        cf = _latest_column(t.cashflow)
        if cf is None:
            cf = _latest_column(t.quarterly_cashflow)

        revenue = _safe_float(_get_item(inc, ["Total Revenue", "TotalRevenue", "Revenue"]))
        net_income = _safe_float(_get_item(inc, ["Net Income", "NetIncome"]))
        operating_cash_flow = _safe_float(_get_item(cf, ["Operating Cash Flow", "OperatingCashFlow"]))
        capex = _safe_float(_get_item(cf, ["Capital Expenditure", "CapitalExpenditure"]))
        fcf = _safe_float(_get_item(cf, ["Free Cash Flow", "FreeCashFlow"]))
        if fcf is None and operating_cash_flow is not None and capex is not None:
            fcf = operating_cash_flow - capex

        book_value = _safe_float(_get_item(bs, ["Stockholders Equity", "StockholdersEquity", "Total Stockholder Equity"]))
        total_debt = _safe_float(_get_item(bs, ["Total Debt", "TotalDebt"]))
        cash = _safe_float(_get_item(bs, ["Cash And Cash Equivalents", "CashAndCashEquivalents", "Cash"]))

        beta = _safe_float(info.get("beta"), 1.0)
        ke = _weighted_average_cost_of_equity(info, beta)
        roe = _safe_float(info.get("returnOnEquity"))
        if roe is None and net_income and book_value and book_value > 0:
            roe = net_income / book_value

        dividend_yield = _safe_float(info.get("dividendYield"))
        price_to_book = _safe_float(info.get("priceToBook"))
        trailing_eps = _safe_float(info.get("trailingEps"))

        sector = sector.lower()
        if sector not in SECTOR_MODULES:
            sector = "standard"

        def gordon_growth_dcf(fcf_per_share: float, growth: float, discount: float) -> float | None:
            if fcf_per_share is None or fcf_per_share <= 0 or discount <= growth:
                return None
            return fcf_per_share * (1 + growth) / (discount - growth)

        def excess_return_model(bv: float, roe_val: float, ke_val: float, g: float) -> float | None:
            if bv is None or bv <= 0 or roe_val is None or ke_val <= g:
                return None
            # Simplified single-stage ERM: BV + (ROE - k) * BV / (k - g)
            return bv + (roe_val - ke_val) * bv / (ke_val - g)

        def dividend_discount(div_yield: float, price_val: float, g: float, ke_val: float) -> float | None:
            # yfinance dividendYield is a percentage number (e.g. 4.5 for 4.5%).
            if div_yield is None or div_yield <= 0 or price_val is None or ke_val <= g:
                return None
            d1 = (div_yield / 100) * price_val * (1 + g)
            return d1 / (ke_val - g)

        def nav_per_share(book_val: float, shares_val: float, price_to_book_val: float) -> float | None:
            if price_to_book_val and price_to_book_val > 0 and shares_val and shares_val > 0:
                return (book_val / price_to_book_val) / shares_val
            return None

        def ev_revenue_sanity(rev: float, shares_val: float, ev_multiple: float = 8.0) -> float | None:
            if rev and shares_val and shares_val > 0:
                return rev * ev_multiple / shares_val
            return None

        # Scenario assumptions.
        assumptions = {
            "standard": {"g_base": 0.03, "g_bull": 0.05, "g_bear": 0.01, "model": "gordon_growth"},
            "growth": {"g_base": 0.12, "g_bull": 0.18, "g_bear": 0.06, "model": "extended_dcf"},
            "banking": {"g_base": 0.03, "g_bull": 0.045, "g_bear": 0.015, "model": "excess_return"},
            "insurance": {"g_base": 0.025, "g_bull": 0.04, "g_bear": 0.01, "model": "dividend_discount"},
            "reit": {"g_base": 0.025, "g_bull": 0.035, "g_bear": 0.01, "model": "nav"},
            "utility": {"g_base": 0.025, "g_bull": 0.035, "g_bear": 0.015, "model": "dividend_discount"},
            "cyclical": {"g_base": 0.02, "g_bull": 0.03, "g_bear": 0.0, "model": "ttc_earnings"},
        }
        sa = assumptions[sector]

        result = {
            "ticker": ticker,
            "sector": sector,
            "scenario_focus": scenario,
            "inputs": {
                "price": safe_value(price),
                "shares": safe_value(shares),
                "market_cap": safe_value(market_cap),
                "revenue": safe_value(revenue),
                "net_income": safe_value(net_income),
                "fcf": safe_value(fcf),
                "book_value": safe_value(book_value),
                "beta": safe_value(beta),
                "cost_of_equity": safe_value(ke),
                "roe": safe_value(roe),
                "dividend_yield": safe_value(dividend_yield),
                "price_to_book": safe_value(price_to_book),
                "trailing_eps": safe_value(trailing_eps),
            },
        }

        sensitivities = {}

        if sector == "banking":
            for label, g in [("base", sa["g_base"]), ("bull", sa["g_bull"]), ("bear", sa["g_bear"])]:
                val = excess_return_model(book_value, roe or 0.10, ke, g)
                if shares and shares > 0 and val:
                    val = val / shares
                sensitivities[label] = safe_value(val)
        elif sector in {"utility", "insurance"}:
            for label, g in [("base", sa["g_base"]), ("bull", sa["g_bull"]), ("bear", sa["g_bear"])]:
                val = dividend_discount(dividend_yield, price, g, ke)
                sensitivities[label] = safe_value(val)
        elif sector == "reit":
            for label, g in [("base", sa["g_base"]), ("bull", sa["g_bull"]), ("bear", sa["g_bear"])]:
                val = nav_per_share(book_value, shares, price_to_book)
                if val:
                    # Apply a small growth premium/discount.
                    val = val * (1 + g)
                sensitivities[label] = safe_value(val)
        # Per-share free cash flow used for DCF-based sectors.
        fcf_per_share = (fcf / shares) if (fcf and shares and shares > 0) else None

        if sector == "growth":
            for label, g in [("base", sa["g_base"]), ("bull", sa["g_bull"]), ("bear", sa["g_bear"])]:
                dcf_val = gordon_growth_dcf(fcf_per_share or 0, g, ke) if (fcf_per_share and fcf_per_share > 0) else None
                ev_val = ev_revenue_sanity(revenue, shares)
                if dcf_val and ev_val:
                    val = (dcf_val + ev_val) / 2
                elif ev_val:
                    val = ev_val
                else:
                    val = dcf_val
                sensitivities[label] = safe_value(val)
        elif sector == "cyclical":
            for label, g in [("base", sa["g_base"]), ("bull", sa["g_bull"]), ("bear", sa["g_bear"])]:
                if trailing_eps and price:
                    # Through-the-cycle P/E of 12-16x depending on scenario.
                    pe = 12 + (g * 100)
                    val = trailing_eps * pe
                else:
                    val = gordon_growth_dcf(fcf_per_share or 0, g, ke)
                sensitivities[label] = safe_value(val)
        else:  # standard
            for label, g in [("base", sa["g_base"]), ("bull", sa["g_bull"]), ("bear", sa["g_bear"])]:
                sensitivities[label] = safe_value(gordon_growth_dcf(fcf_per_share or 0, g, ke))

        result["fair_value"] = sensitivities.get(scenario)
        result["sensitivities"] = sensitivities
        result["model_name"] = sa["model"]
        result["upside_downside"] = None
        if price and result["fair_value"]:
            result["upside_downside"] = safe_value((result["fair_value"] - price) / price)

        return result
    except Exception as e:
        return {"error": str(e), "ticker": ticker, "sector": sector}


# ── Chart Generation ─────────────────────────────────────────────────────────


def generate_charts(ticker: str, output_dir: str) -> dict:
    """Generate research charts for a ticker and save them to output_dir.

    Args:
        ticker: Stock ticker symbol.
        output_dir: Directory where PNG files will be written.

    Returns:
        dict with paths to generated chart files.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import yfinance as yf

        os.makedirs(output_dir, exist_ok=True)
        ticker_upper = ticker.upper()
        t = yf.Ticker(ticker)
        price_path = os.path.join(output_dir, "price_trend.png")
        val_path = os.path.join(output_dir, "valuation_sensitivity.png")

        # --- price_trend.png ---
        hist = t.history(period="2y")
        if hist is not None and not hist.empty:
            fig, axes = plt.subplots(
                nrows=2,
                ncols=1,
                figsize=(10, 8),
                gridspec_kw={"height_ratios": [3, 1]},
                sharex=True,
            )
            ax_price, ax_vol = axes

            closes = hist["Close"]
            ma50 = closes.rolling(window=50, min_periods=1).mean()
            ma200 = closes.rolling(window=200, min_periods=1).mean()

            ax_price.plot(hist.index, closes, label="Close", linewidth=1.2)
            ax_price.plot(hist.index, ma50, label="50 MA", linewidth=1, alpha=0.8)
            ax_price.plot(hist.index, ma200, label="200 MA", linewidth=1, alpha=0.8)
            ax_price.set_title(f"{ticker_upper} Price Trend & Moving Averages")
            ax_price.set_ylabel("Price")
            ax_price.legend(loc="upper left")
            ax_price.grid(True, alpha=0.3)

            ax_vol.bar(hist.index, hist["Volume"], width=1.5, color="gray", alpha=0.6)
            ax_vol.set_ylabel("Volume")
            ax_vol.set_xlabel("Date")
            ax_vol.grid(True, alpha=0.3)

            plt.tight_layout()
            fig.savefig(price_path, dpi=150)
            plt.close(fig)

        # --- valuation_sensitivity.png ---
        fig, ax = plt.subplots(figsize=(8, 6))

        # Build a simple WACC vs terminal-growth fair-value grid for the standard model.
        cf = _latest_column(t.cashflow)
        if cf is None:
            cf = _latest_column(t.quarterly_cashflow)
        fcf = _safe_float(_get_item(cf, ["Free Cash Flow", "FreeCashFlow"]))
        if fcf is None:
            operating_cash_flow = _safe_float(_get_item(cf, ["Operating Cash Flow", "OperatingCashFlow"]))
            capex = _safe_float(_get_item(cf, ["Capital Expenditure", "CapitalExpenditure"]))
            if operating_cash_flow is not None and capex is not None:
                fcf = operating_cash_flow - capex

        shares = _safe_float(
            (t.info or {}).get("sharesOutstanding")
            or getattr(t.fast_info, "shares", None)
        )
        fcf_per_share = None
        if fcf and shares and shares > 0:
            fcf_per_share = fcf / shares

        waccs = [0.06, 0.08, 0.10, 0.12, 0.14]
        growths = [0.01, 0.02, 0.03, 0.04, 0.05]
        grid = []
        for g in growths:
            row = []
            for w in waccs:
                if fcf_per_share and w > g:
                    row.append(fcf_per_share * (1 + g) / (w - g))
                else:
                    row.append(None)
            grid.append(row)

        im = ax.imshow(grid, cmap="RdYlGn", aspect="auto")
        ax.set_xticks(range(len(waccs)))
        ax.set_yticks(range(len(growths)))
        ax.set_xticklabels([f"{w:.0%}" for w in waccs])
        ax.set_yticklabels([f"{g:.0%}" for g in growths])
        ax.set_xlabel("Discount Rate (WACC)")
        ax.set_ylabel("Terminal Growth")
        ax.set_title(f"{ticker_upper} Fair Value Sensitivity (USD per share)")

        # Annotate cells.
        for i in range(len(growths)):
            for j in range(len(waccs)):
                val = grid[i][j]
                if val is not None:
                    ax.text(
                        j,
                        i,
                        f"{val:.1f}",
                        ha="center",
                        va="center",
                        color="black",
                        fontsize=8,
                    )

        fig.colorbar(im, ax=ax, label="Fair value per share")
        plt.tight_layout()
        fig.savefig(val_path, dpi=150)
        plt.close(fig)

        return {
            "ticker": ticker,
            "output_dir": output_dir,
            "charts": [
                {"name": "price_trend", "path": price_path},
                {"name": "valuation_sensitivity", "path": val_path},
            ],
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker, "output_dir": output_dir}


# ── Peer Snapshot ────────────────────────────────────────────────────────────


def _ticker_snapshot(ticker: str) -> dict:
    """Collect a small set of key metrics for one ticker."""
    import yfinance as yf

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        fi = t.fast_info
        price = _safe_float(
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or getattr(fi, "last_price", None)
        )
        market_cap = _safe_float(
            info.get("marketCap")
            or getattr(fi, "market_cap", None)
        )
        pe = _safe_float(info.get("trailingPE"))
        pb = _safe_float(info.get("priceToBook"))
        div_yield = _safe_float(info.get("dividendYield"))
        revenue_growth = _safe_float(
            info.get("revenueGrowth")
            or info.get("revenueQuarterlyGrowth")
        )
        profit_margin = _safe_float(info.get("profitMargins"))
        beta = _safe_float(info.get("beta"))
        sector = info.get("sector")
        industry = info.get("industry")
        name = info.get("shortName") or info.get("longName")
        return {
            "ticker": ticker,
            "name": safe_value(name),
            "sector": safe_value(sector),
            "industry": safe_value(industry),
            "price": safe_value(price),
            "market_cap": safe_value(market_cap),
            "trailing_pe": safe_value(pe),
            "price_to_book": safe_value(pb),
            "dividend_yield": safe_value(div_yield),
            "revenue_growth": safe_value(revenue_growth),
            "profit_margin": safe_value(profit_margin),
            "beta": safe_value(beta),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def get_peer_snapshot(ticker: str, peers: list[str]) -> dict:
    """Return combined key metrics for a ticker and a list of peers.

    Args:
        ticker: Primary stock ticker symbol.
        peers: List of peer ticker symbols.

    Returns:
        dict with combined metrics for ticker + peers.
    """
    import yfinance as yf

    try:
        all_tickers = [ticker] + list(peers)
        snapshots = [_ticker_snapshot(t) for t in all_tickers]
        return {
            "ticker": ticker,
            "peers": peers,
            "count": len(snapshots),
            "data": snapshots,
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker, "peers": peers}
