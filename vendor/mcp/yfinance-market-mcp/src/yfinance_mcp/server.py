"""FastMCP server exposing Yahoo Finance market data tools."""

from datetime import datetime, timedelta
import importlib.util
from mcp.server.fastmcp import FastMCP
import sys

from .utils import df_to_records, series_to_dict, safe_value
from . import research


def _lazy_import(name: str):
    """Lazy-load a module so heavy imports don't block MCP server startup."""
    spec = importlib.util.find_spec(name)
    if spec is None:
        raise ImportError(f"cannot find spec for {name}")
    loader = importlib.util.LazyLoader(spec.loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


yf = _lazy_import("yfinance")

mcp = FastMCP("yfinance")


def _parse_news_article(article: dict) -> dict:
    """Extract news fields from yfinance 1.2+ nested structure.

    Args:
        article: Raw news article dict from yfinance.

    Returns:
        Flattened dict with title, publisher, link, date, summary.
    """
    content = article.get("content", article)
    provider = content.get("provider", {})
    canonical = content.get("canonicalUrl", {})
    click_through = content.get("clickThroughUrl", {})
    return {
        "title": content.get("title", ""),
        "publisher": provider.get("displayName", ""),
        "link": canonical.get("url", "") or click_through.get("url", ""),
        "date": content.get("pubDate", ""),
        "summary": content.get("summary", ""),
    }


# ── Price Tools ──────────────────────────────────────────────────────────────


@mcp.tool()
def get_price_history(
    ticker: str,
    period: str = "1mo",
    interval: str = "1d",
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """Get OHLCV price history for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL").
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max).
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo).
        start: Start date string (YYYY-MM-DD). Overrides period if set.
        end: End date string (YYYY-MM-DD).

    Returns:
        dict with ticker and list of OHLCV records.
    """
    try:
        t = yf.Ticker(ticker)
        kwargs = {"interval": interval}
        if start:
            kwargs["start"] = start
            if end:
                kwargs["end"] = end
        else:
            kwargs["period"] = period
        df = t.history(**kwargs)
        return {"ticker": ticker, "data": df_to_records(df)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_dividends(ticker: str) -> dict:
    """Get dividend history for a ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and list of dividend records.
    """
    try:
        t = yf.Ticker(ticker)
        divs = t.dividends
        return {
            "ticker": ticker,
            "data": df_to_records(
                divs.reset_index().rename(columns={0: "Dividend"})
                if not divs.empty
                else divs
            ),
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_splits(ticker: str) -> dict:
    """Get stock split history for a ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and list of split records.
    """
    try:
        t = yf.Ticker(ticker)
        splits = t.splits
        return {
            "ticker": ticker,
            "data": df_to_records(
                splits.reset_index().rename(columns={0: "Split"})
                if not splits.empty
                else splits
            ),
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ── Info Tools ───────────────────────────────────────────────────────────────


@mcp.tool()
def get_ticker_info(ticker: str) -> dict:
    """Get full company info for a ticker (sector, industry, description, financials, etc.).

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with all available company information.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {"ticker": ticker, "data": {k: safe_value(v) for k, v in info.items()}}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_fast_info(ticker: str) -> dict:
    """Get quick price snapshot (price, volume, market cap, 52w range).

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with key price metrics.
    """
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        data = {}
        for attr in [
            "currency",
            "day_high",
            "day_low",
            "exchange",
            "fifty_day_average",
            "last_price",
            "last_volume",
            "market_cap",
            "open",
            "previous_close",
            "quote_type",
            "regular_market_previous_close",
            "shares",
            "ten_day_average_volume",
            "three_month_average_volume",
            "timezone",
            "two_hundred_day_average",
            "year_change",
            "year_high",
            "year_low",
        ]:
            try:
                data[attr] = safe_value(getattr(fi, attr, None))
            except Exception:
                pass
        return {"ticker": ticker, "data": data}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_ticker_summary(ticker: str) -> dict:
    """Get composite summary: fast info + key fundamentals + last 5 news + analyst targets.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with price, fundamentals, news, and analyst target sections.
    """
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        price_data = {}
        for attr in [
            "last_price",
            "market_cap",
            "previous_close",
            "open",
            "day_high",
            "day_low",
            "year_high",
            "year_low",
            "fifty_day_average",
            "two_hundred_day_average",
        ]:
            try:
                price_data[attr] = safe_value(getattr(fi, attr, None))
            except Exception:
                pass

        info = t.info
        fundamentals = {
            k: safe_value(info.get(k))
            for k in [
                "trailingPE",
                "forwardPE",
                "trailingEps",
                "forwardEps",
                "dividendYield",
                "beta",
                "sector",
                "industry",
                "fullTimeEmployees",
                "shortName",
            ]
            if info.get(k) is not None
        }

        news = []
        try:
            raw_news = t.news[:5] if t.news else []
            for article in raw_news:
                news.append(_parse_news_article(article))
        except Exception:
            pass

        analyst = {}
        try:
            targets = t.analyst_price_targets
            if targets is not None:
                analyst = (
                    series_to_dict(targets)
                    if hasattr(targets, "to_dict")
                    else {k: safe_value(v) for k, v in targets.items()}
                    if isinstance(targets, dict)
                    else {}
                )
        except Exception:
            pass

        return {
            "ticker": ticker,
            "price": price_data,
            "fundamentals": fundamentals,
            "news": news,
            "analyst_targets": analyst,
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ── News Tools ───────────────────────────────────────────────────────────────


@mcp.tool()
def get_ticker_news(ticker: str, count: int = 10) -> dict:
    """Get recent news articles for a ticker.

    Args:
        ticker: Stock ticker symbol.
        count: Number of articles to return (default 10).

    Returns:
        dict with ticker and list of news articles.
    """
    try:
        t = yf.Ticker(ticker)
        raw_news = t.news[:count] if t.news else []
        articles = []
        for article in raw_news:
            articles.append(_parse_news_article(article))
        return {"ticker": ticker, "count": len(articles), "articles": articles}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def search_news(query: str, count: int = 8) -> dict:
    """Search for general market news by keyword.

    Args:
        query: Search query string.
        count: Number of results to return (default 8).

    Returns:
        dict with query and list of news articles.
    """
    try:
        search = yf.Search(query, news_count=count)
        articles = []
        for article in search.news or []:
            articles.append(_parse_news_article(article))
        return {"query": query, "count": len(articles), "articles": articles}
    except Exception as e:
        return {"error": str(e), "query": query}


# ── Options Tools ────────────────────────────────────────────────────────────


@mcp.tool()
def get_options_expirations(ticker: str) -> dict:
    """Get available options expiration dates for a ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and list of expiration date strings.
    """
    try:
        t = yf.Ticker(ticker)
        return {"ticker": ticker, "expirations": list(t.options)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_options_chain(
    ticker: str,
    expiration: str | None = None,
    option_type: str = "both",
) -> dict:
    """Get options chain data (calls, puts, or both) for a ticker and expiration.

    Args:
        ticker: Stock ticker symbol.
        expiration: Expiration date string (YYYY-MM-DD). Uses nearest if None.
        option_type: "calls", "puts", or "both" (default "both").

    Returns:
        dict with ticker, expiration, and calls/puts data.
    """
    try:
        t = yf.Ticker(ticker)
        if expiration:
            chain = t.option_chain(expiration)
        else:
            exps = t.options
            if not exps:
                return {"error": "No options available", "ticker": ticker}
            chain = t.option_chain(exps[0])
            expiration = exps[0]

        result = {"ticker": ticker, "expiration": expiration}
        if option_type in ("calls", "both"):
            result["calls"] = df_to_records(chain.calls)
        if option_type in ("puts", "both"):
            result["puts"] = df_to_records(chain.puts)
        return result
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ── Financial Statements ─────────────────────────────────────────────────────


@mcp.tool()
def get_income_statement(ticker: str, freq: str = "yearly") -> dict:
    """Get income statement for a ticker.

    Args:
        ticker: Stock ticker symbol.
        freq: "yearly", "quarterly", or "trailing".

    Returns:
        dict with ticker and income statement records.
    """
    try:
        t = yf.Ticker(ticker)
        if freq == "quarterly":
            df = t.quarterly_income_stmt
        elif freq == "trailing":
            df = getattr(t, "trailing_income_stmt", t.income_stmt)
        else:
            df = t.income_stmt
        return {
            "ticker": ticker,
            "freq": freq,
            "data": df_to_records(df.T if df is not None else df),
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_balance_sheet(ticker: str, freq: str = "yearly") -> dict:
    """Get balance sheet for a ticker.

    Args:
        ticker: Stock ticker symbol.
        freq: "yearly" or "quarterly".

    Returns:
        dict with ticker and balance sheet records.
    """
    try:
        t = yf.Ticker(ticker)
        df = t.quarterly_balance_sheet if freq == "quarterly" else t.balance_sheet
        return {
            "ticker": ticker,
            "freq": freq,
            "data": df_to_records(df.T if df is not None else df),
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_cash_flow(ticker: str, freq: str = "yearly") -> dict:
    """Get cash flow statement for a ticker.

    Args:
        ticker: Stock ticker symbol.
        freq: "yearly" or "quarterly".

    Returns:
        dict with ticker and cash flow records.
    """
    try:
        t = yf.Ticker(ticker)
        df = t.quarterly_cashflow if freq == "quarterly" else t.cashflow
        return {
            "ticker": ticker,
            "freq": freq,
            "data": df_to_records(df.T if df is not None else df),
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ── Analysis & Estimates ─────────────────────────────────────────────────────


@mcp.tool()
def get_analyst_price_targets(ticker: str) -> dict:
    """Get analyst price targets (low, high, mean, median, current).

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and price target data.
    """
    try:
        t = yf.Ticker(ticker)
        targets = t.analyst_price_targets
        if targets is None:
            return {"ticker": ticker, "data": {}}
        if isinstance(targets, dict):
            return {
                "ticker": ticker,
                "data": {k: safe_value(v) for k, v in targets.items()},
            }
        return {"ticker": ticker, "data": series_to_dict(targets)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_recommendations(ticker: str) -> dict:
    """Get analyst buy/sell/hold recommendations over time.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and recommendation records.
    """
    try:
        t = yf.Ticker(ticker)
        recs = t.recommendations
        return {"ticker": ticker, "data": df_to_records(recs)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_upgrades_downgrades(ticker: str) -> dict:
    """Get analyst upgrades and downgrades history.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and upgrade/downgrade records.
    """
    try:
        t = yf.Ticker(ticker)
        ud = t.upgrades_downgrades
        return {"ticker": ticker, "data": df_to_records(ud)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_earnings_estimate(ticker: str) -> dict:
    """Get EPS estimates by period.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and earnings estimate records.
    """
    try:
        t = yf.Ticker(ticker)
        ee = t.earnings_estimate
        return {"ticker": ticker, "data": df_to_records(ee)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_revenue_estimate(ticker: str) -> dict:
    """Get revenue estimates by period.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and revenue estimate records.
    """
    try:
        t = yf.Ticker(ticker)
        re_ = t.revenue_estimate
        return {"ticker": ticker, "data": df_to_records(re_)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_growth_estimates(ticker: str) -> dict:
    """Get growth rate estimates for a ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and growth estimate records.
    """
    try:
        t = yf.Ticker(ticker)
        ge = t.growth_estimates
        return {"ticker": ticker, "data": df_to_records(ge)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_eps_trend(ticker: str) -> dict:
    """Get EPS trend data showing estimate revisions over time.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and EPS trend records.
    """
    try:
        t = yf.Ticker(ticker)
        et = t.eps_trend
        return {"ticker": ticker, "data": df_to_records(et)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ── Holders ──────────────────────────────────────────────────────────────────


@mcp.tool()
def get_institutional_holders(ticker: str) -> dict:
    """Get top institutional holders for a ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and institutional holder records.
    """
    try:
        t = yf.Ticker(ticker)
        ih = t.institutional_holders
        return {"ticker": ticker, "data": df_to_records(ih)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_insider_transactions(ticker: str) -> dict:
    """Get recent insider buy/sell transactions.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and insider transaction records.
    """
    try:
        t = yf.Ticker(ticker)
        it = t.insider_transactions
        return {"ticker": ticker, "data": df_to_records(it)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_major_holders(ticker: str) -> dict:
    """Get major holder breakdown (insiders, institutions, etc.).

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and major holder data.
    """
    try:
        t = yf.Ticker(ticker)
        mh = t.major_holders
        return {"ticker": ticker, "data": df_to_records(mh)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ── Events & Search ──────────────────────────────────────────────────────────


@mcp.tool()
def get_earnings_dates(ticker: str, limit: int = 12) -> dict:
    """Get upcoming and past earnings dates.

    Args:
        ticker: Stock ticker symbol.
        limit: Number of dates to return (default 12).

    Returns:
        dict with ticker and earnings date records.
    """
    try:
        t = yf.Ticker(ticker)
        ed = t.get_earnings_dates(limit=limit)
        return {"ticker": ticker, "data": df_to_records(ed)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def get_calendar(ticker: str) -> dict:
    """Get upcoming events calendar (dividends, earnings, etc.).

    Args:
        ticker: Stock ticker symbol.

    Returns:
        dict with ticker and calendar event data.
    """
    try:
        t = yf.Ticker(ticker)
        cal = t.calendar
        if cal is None:
            return {"ticker": ticker, "data": {}}
        if isinstance(cal, dict):
            return {
                "ticker": ticker,
                "data": {k: safe_value(v) for k, v in cal.items()},
            }
        return {"ticker": ticker, "data": series_to_dict(cal)}
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


@mcp.tool()
def search_tickers(query: str, max_results: int = 8) -> dict:
    """Search for tickers by company name or keyword.

    Args:
        query: Search query string.
        max_results: Maximum results to return (default 8).

    Returns:
        dict with query and list of matching ticker results.
    """
    try:
        search = yf.Search(query, max_results=max_results)
        quotes = []
        for q in search.quotes or []:
            quotes.append(
                {
                    "symbol": q.get("symbol", ""),
                    "shortname": q.get("shortname", ""),
                    "longname": q.get("longname", ""),
                    "exchange": q.get("exchange", ""),
                    "quoteType": q.get("quoteType", ""),
                }
            )
        return {"query": query, "count": len(quotes), "results": quotes}
    except Exception as e:
        return {"error": str(e), "query": query}


# ── Sector & Industry ────────────────────────────────────────────────────────


@mcp.tool()
def get_sector_data(sector: str) -> dict:
    """Get sector overview, top companies, top ETFs, and industry breakdown.

    Args:
        sector: Sector key (e.g. "technology", "healthcare", "financial-services",
                "consumer-cyclical", "energy", "industrials", "utilities",
                "basic-materials", "communication-services", "consumer-defensive",
                "real-estate").

    Returns:
        dict with sector overview, top companies, and industries list.
    """
    try:
        s = yf.Sector(sector)
        result = {"sector": sector, "overview": s.overview or {}}
        tc = s.top_companies
        if tc is not None and not tc.empty:
            result["top_companies"] = df_to_records(tc)
        ind = s.industries
        if ind is not None and not ind.empty:
            result["industries"] = df_to_records(ind)
        return result
    except Exception as e:
        return {"error": str(e), "sector": sector}


@mcp.tool()
def get_industry_data(industry: str) -> dict:
    """Get industry overview, top companies, and top growth companies.

    Args:
        industry: Industry key (e.g. "semiconductors", "software-infrastructure",
                  "software-application", "consumer-electronics", "auto-manufacturers").

    Returns:
        dict with industry overview, top companies, and top growth companies.
    """
    try:
        i = yf.Industry(industry)
        result = {
            "industry": industry,
            "overview": i.overview or {},
            "sector": {"key": i.sector_key, "name": i.sector_name},
        }
        tc = i.top_companies
        if tc is not None and not tc.empty:
            result["top_companies"] = df_to_records(tc)
        tg = i.top_growth_companies
        if tg is not None and not tg.empty:
            result["top_growth_companies"] = df_to_records(tg)
        return result
    except Exception as e:
        return {"error": str(e), "industry": industry}


# ── Screener ─────────────────────────────────────────────────────────────────


@mcp.tool()
def screen_stocks(
    query: str = "most_actives",
    count: int = 25,
) -> dict:
    """Screen stocks using predefined Yahoo Finance screeners.

    Args:
        query: Predefined screener name. Options: "most_actives", "day_gainers",
               "day_losers", "most_shorted_stocks", "undervalued_growth_stocks",
               "undervalued_large_caps", "growth_technology_stocks",
               "aggressive_small_caps", "small_cap_gainers",
               "top_mutual_funds", "portfolio_anchors", "high_yield_bond".
        count: Number of results (default 25, max 250).

    Returns:
        dict with screener title, description, total matches, and stock quotes.
    """
    try:
        result = yf.screen(query, count=count)
        quotes = []
        for q in result.get("quotes") or []:
            quotes.append(
                {
                    "symbol": q.get("symbol", ""),
                    "shortName": q.get("shortName", ""),
                    "regularMarketPrice": safe_value(q.get("regularMarketPrice")),
                    "regularMarketChange": safe_value(q.get("regularMarketChange")),
                    "regularMarketChangePercent": safe_value(
                        q.get("regularMarketChangePercent")
                    ),
                    "regularMarketVolume": safe_value(q.get("regularMarketVolume")),
                    "marketCap": safe_value(q.get("marketCap")),
                    "trailingPE": safe_value(q.get("trailingPE")),
                    "exchange": q.get("exchange", ""),
                }
            )
        return {
            "query": query,
            "title": result.get("title", ""),
            "description": result.get("description", ""),
            "total": result.get("total", 0),
            "count": len(quotes),
            "quotes": quotes,
        }
    except Exception as e:
        return {"error": str(e), "query": query}


# ── Trade Advisor Tools ─────────────────────────────────────────────────────


# FOMC Meeting Dates 2025-2026 (announcement days)
_FOMC_DATES = [
    # 2025
    "2025-01-29",
    "2025-03-19",
    "2025-05-07",
    "2025-06-18",
    "2025-07-30",
    "2025-09-17",
    "2025-11-05",
    "2025-12-17",
    # 2026
    "2026-01-28",
    "2026-03-18",
    "2026-04-29",
    "2026-06-17",
    "2026-07-29",
    "2026-09-16",
    "2026-10-28",
    "2026-12-16",
]
_FOMC_PARSED = [datetime.strptime(d, "%Y-%m-%d").date() for d in _FOMC_DATES]


@mcp.tool()
def check_fed_earnings(ticker: str) -> dict:
    """Check proximity to Fed meetings and earnings reports for safe trading.

    Critical pre-trade check: Never open options positions on the day of or
    day before a Fed meeting or earnings report.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL").

    Returns:
        dict with next Fed meeting, next earnings date, days until each,
        safety assessment, and warnings.
    """
    today = datetime.now().date()
    result = {"ticker": ticker, "date": today.isoformat()}

    # --- Fed meeting ---
    future_fomc = [d for d in _FOMC_PARSED if d >= today]
    if future_fomc:
        next_fomc = future_fomc[0]
        days_to_fed = (next_fomc - today).days
        result["next_fed_meeting"] = next_fomc.isoformat()
        result["days_to_fed"] = days_to_fed
        if days_to_fed == 0:
            result["fed_status"] = "PELIGRO - Reunion Fed HOY"
        elif days_to_fed == 1:
            result["fed_status"] = "PELIGRO - Reunion Fed MANANA"
        elif days_to_fed <= 3:
            result["fed_status"] = "PRECAUCION"
        else:
            result["fed_status"] = "OK"
    else:
        result["next_fed_meeting"] = None
        result["days_to_fed"] = None
        result["fed_status"] = "Sin fechas FOMC programadas"

    # --- Earnings ---
    earnings_date = None
    days_to_earnings = None
    try:
        t = yf.Ticker(ticker)
        cal = t.calendar
        if cal is not None:
            if isinstance(cal, dict):
                for key in ["Earnings Date", "earnings_date"]:
                    if key in cal:
                        val = cal[key]
                        if isinstance(val, list) and len(val) > 0:
                            ed = val[0]
                        else:
                            ed = val
                        if hasattr(ed, "date"):
                            earnings_date = ed.date()
                        else:
                            earnings_date = datetime.strptime(
                                str(ed)[:10], "%Y-%m-%d"
                            ).date()
                        break
            elif hasattr(cal, "index"):
                for idx in cal.index:
                    if "earning" in str(idx).lower():
                        val = cal[idx]
                        if isinstance(val, list):
                            val = val[0]
                        if hasattr(val, "date"):
                            earnings_date = val.date()
                        else:
                            earnings_date = datetime.strptime(
                                str(val)[:10], "%Y-%m-%d"
                            ).date()
                        break
    except Exception:
        pass

    if earnings_date is None:
        try:
            t = yf.Ticker(ticker)
            ed = t.earnings_dates
            if ed is not None and len(ed) > 0:
                future_dates = [
                    d.date() if hasattr(d, "date") else d
                    for d in ed.index
                    if (d.date() if hasattr(d, "date") else d) >= today
                ]
                if future_dates:
                    earnings_date = min(future_dates)
        except Exception:
            pass

    if earnings_date:
        days_to_earnings = (earnings_date - today).days
        result["next_earnings"] = earnings_date.isoformat()
        result["days_to_earnings"] = days_to_earnings
        if days_to_earnings == 0:
            result["earnings_status"] = "PELIGRO - Earnings HOY"
        elif days_to_earnings == 1:
            result["earnings_status"] = "PELIGRO - Earnings MANANA"
        elif days_to_earnings <= 3:
            result["earnings_status"] = "PRECAUCION - Prima inflada"
        elif days_to_earnings <= 7:
            result["earnings_status"] = "ATENCION - Verificar expiracion del contrato"
        else:
            result["earnings_status"] = "OK"
    else:
        result["next_earnings"] = None
        result["days_to_earnings"] = None
        result["earnings_status"] = "No se encontro fecha - verificar manualmente"

    # --- Safety assessment ---
    warnings = []
    safe = True
    days_fed = result.get("days_to_fed")
    if days_fed is not None:
        if days_fed <= 1:
            warnings.append(f"CRITICO: Reunion Fed en {days_fed} dia(s) - NO operar")
            safe = False
        elif days_fed <= 3:
            warnings.append(f"PRECAUCION: Reunion Fed en {days_fed} dias")
    if days_to_earnings is not None:
        if days_to_earnings <= 1:
            warnings.append(
                f"CRITICO: Earnings en {days_to_earnings} dia(s) - NO operar este ticker"
            )
            safe = False
        elif days_to_earnings <= 3:
            warnings.append(
                f"PRECAUCION: Earnings en {days_to_earnings} dias - Prima inflada"
            )
        elif days_to_earnings <= 7:
            warnings.append(
                f"NOTA: Earnings en {days_to_earnings} dias - Verificar expiracion"
            )
    if not warnings:
        warnings.append("Sin eventos criticos proximos - Zona segura para operar")

    result["safe_to_trade"] = safe
    result["warnings"] = warnings
    return result


def _round_to_5(value):
    """Round to nearest 5 (e.g., 18->20, 83->85, 42->40)."""
    return max(5, round(value / 5) * 5)


def _get_contract_day_range(contract_symbol):
    """Fetch the Day's Range (High/Low) for an options contract."""
    try:
        ticker = yf.Ticker(contract_symbol)
        info = ticker.info
        # Try regularMarket fields first, then fall back to standard fields
        day_low = info.get("regularMarketDayLow") or info.get("dayLow")
        day_high = info.get("regularMarketDayHigh") or info.get("dayHigh")
        if (
            day_low is not None
            and day_high is not None
            and day_low > 0
            and day_high > 0
        ):
            return float(day_low), float(day_high)
        return None, None
    except Exception:
        return None, None


@mcp.tool()
def calculate_range(
    ticker: str,
    direction: str | None = None,
    expiration: str | None = None,
    strikes: int = 5,
) -> dict:
    """Calculate the RANGO (operating price range) for options contracts.

    Uses the exact methodology from the options trading course:
    1. Takes 5 strikes from the nearest expiration (usually this Friday)
    2. Gets Day's Range (High/Low) for each contract
    3. Calculates: % = (Day High - Day Low) / Day Low * 100
    4. Top 2 by % = the contracts that valorize the most
    5. Their Ask prices (x100, rounded to 5) define the RANGO
    6. Divides into 3 zones by day of week (Mon-Tue: low, Wed: mid, Thu-Fri: high)

    TIPS:
    - Best days to calculate: Tuesday, Wednesday, Thursday
    - Auto-selects the nearest expiration (closest Friday) for best results
    - Monday has limited Day's Range data, Friday contracts expire same day

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL").
        direction: "CALL", "PUT", or None for both.
        expiration: Specific expiration date (YYYY-MM-DD). Auto-selects nearest if None.
        strikes: Number of strikes to analyze (default 5).

    Returns:
        dict with price, expiration, and per-direction range analysis including
        recommended contracts for today.
    """
    ticker = ticker.upper()
    today = datetime.now()
    n_strikes = strikes

    try:
        t = yf.Ticker(ticker)
        price = t.fast_info.get("lastPrice", None) or t.fast_info.get(
            "last_price", None
        )
        if price is None:
            hist = t.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        if not price:
            return {"error": f"No se pudo obtener el precio de {ticker}"}
    except Exception as e:
        return {"error": f"Error obteniendo precio: {e}"}

    # Select expiration
    try:
        expirations = list(t.options) if hasattr(t, "options") else []
    except Exception:
        expirations = []
    if not expirations:
        return {"error": "No hay expiraciones de opciones disponibles"}

    target_exp = expiration
    if not target_exp:
        # Prefer the nearest expiration (usually this Friday)
        nearest_exp = None
        for exp in expirations:
            exp_date = datetime.strptime(exp, "%Y-%m-%d")
            dte = (exp_date - today).days
            if dte >= 1:
                nearest_exp = exp
                break
        target_exp = nearest_exp or expirations[0]

    exp_date = datetime.strptime(target_exp, "%Y-%m-%d")
    dte = (exp_date - today).days

    # Tip: best days to calculate the range
    weekday = today.weekday()
    day_names = {
        0: "Lunes",
        1: "Martes",
        2: "Miercoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sabado",
        6: "Domingo",
    }
    tips = []
    if weekday == 0:
        tips.append(
            "TIP: El lunes no es ideal para calcular el rango. Los mejores dias son martes, miercoles y jueves cuando hay mas datos de Day's Range disponibles."
        )
    elif weekday == 4:
        tips.append(
            "TIP: El viernes no es ideal para calcular el rango ya que los contratos semanales expiran hoy. Mejor calcular martes a jueves."
        )
    elif weekday >= 5:
        tips.append(
            "TIP: El mercado esta cerrado. Calcula el rango entre martes y jueves para mejores resultados."
        )

    try:
        chain = t.option_chain(target_exp)
    except Exception as e:
        return {"error": f"Error al obtener cadena de opciones: {e}"}

    directions = [direction.upper()] if direction else ["CALL", "PUT"]
    results_summary = {}

    for dir_ in directions:
        df = chain.calls if dir_ == "CALL" else chain.puts

        # Select strikes: primarily OTM, Ask > 0.15
        filtered = df[df["ask"] > 0.15].copy()
        if filtered.empty:
            results_summary[dir_] = {
                "error": "No se encontraron contratos validos (Ask > $0.15)"
            }
            continue

        if dir_ == "CALL":
            otm = filtered[filtered["strike"] > price].sort_values("strike")
            itm = filtered[filtered["strike"] <= price].sort_values(
                "strike", ascending=False
            )
        else:
            otm = filtered[filtered["strike"] < price].sort_values(
                "strike", ascending=False
            )
            itm = filtered[filtered["strike"] >= price].sort_values("strike")

        selected = []
        for _, row in otm.head(n_strikes).iterrows():
            selected.append(row)
        remaining = n_strikes - len(selected)
        if remaining > 0:
            for _, row in itm.head(remaining).iterrows():
                selected.append(row)

        if not selected:
            results_summary[dir_] = {"error": "No hay suficientes contratos"}
            continue

        # Get Day's Range for each selected strike
        strike_data = []
        for row in selected:
            strike_val = float(row["strike"])
            ask = float(row["ask"])
            bid = float(row.get("bid", 0) or 0)
            vol = int(row.get("volume", 0) or 0)
            oi = int(row.get("openInterest", 0) or 0)
            is_itm = bool(row.get("inTheMoney", False))
            symbol = row.get("contractSymbol", "")

            day_low, day_high = _get_contract_day_range(symbol)
            pct = None
            if day_low and day_high and day_low > 0:
                pct = (day_high - day_low) / day_low * 100

            strike_data.append(
                {
                    "strike": strike_val,
                    "ask": ask,
                    "ask_x100": round(ask * 100),
                    "bid": bid,
                    "day_low_x100": round(day_low * 100) if day_low else None,
                    "day_high_x100": round(day_high * 100) if day_high else None,
                    "pct": round(pct, 1) if pct else None,
                    "volume": vol,
                    "open_interest": oi,
                    "itm": is_itm,
                    "symbol": symbol,
                }
            )

        # Find top 2 by percentage
        valid = [s for s in strike_data if s["pct"] is not None and s["pct"] > 0]
        if len(valid) < 2:
            results_summary[dir_] = {
                "strikes_analyzed": strike_data,
                "error": "No se pudo calcular rango (se necesitan al menos 2 contratos con Day's Range)",
            }
            continue

        valid.sort(key=lambda x: x["pct"], reverse=True)
        top_2 = valid[:2]
        ask_prices = sorted([s["ask_x100"] for s in top_2])
        range_low = _round_to_5(ask_prices[0])
        range_high = _round_to_5(ask_prices[1])
        if range_low >= range_high:
            range_high = range_low + 5

        # Day-of-week zone
        spread = range_high - range_low
        third = spread / 3

        if weekday <= 1:
            zone_name = "BAJA"
            zone_low = range_low
            zone_high = _round_to_5(range_low + third)
        elif weekday == 2:
            zone_name = "MEDIA"
            zone_low = _round_to_5(range_low + third)
            zone_high = _round_to_5(range_low + 2 * third)
        else:
            zone_name = "ALTA"
            zone_low = _round_to_5(range_low + 2 * third)
            zone_high = range_high

        # Find ALL OTM contracts in the chain within the RANGO
        all_otm = df.copy()
        if dir_ == "CALL":
            all_otm = all_otm[
                (all_otm["strike"] > price) & (all_otm["strike"] <= price * 1.15)
            ]
        else:
            all_otm = all_otm[
                (all_otm["strike"] < price) & (all_otm["strike"] >= price * 0.85)
            ]

        contracts_in_range = []
        for _, c in all_otm.iterrows():
            c_ask = float(c.get("ask", 0) or 0)
            c_bid = float(c.get("bid", 0) or 0)
            if c_ask <= 0:
                continue
            c_ask_x100 = round(c_ask * 100)
            spread_pct = ((c_ask - c_bid) / c_ask * 100) if c_ask > 0 else 100
            in_range = range_low <= c_ask_x100 <= range_high
            in_zone = zone_low <= c_ask_x100 <= zone_high

            if in_range:
                contracts_in_range.append(
                    {
                        "strike": float(c["strike"]),
                        "bid": round(c_bid, 2),
                        "ask": round(c_ask, 2),
                        "ask_x100": c_ask_x100,
                        "spread_pct": round(spread_pct, 1),
                        "volume": int(c.get("volume", 0) or 0),
                        "open_interest": int(c.get("openInterest", 0) or 0),
                        "in_zone_today": in_zone,
                        "valid_spread": spread_pct <= 10,
                    }
                )

        # Find best contract for today
        valid_today = [
            c for c in contracts_in_range if c["in_zone_today"] and c["valid_spread"]
        ]
        recommended = None
        if valid_today:
            recommended = max(valid_today, key=lambda x: x["volume"])

        results_summary[dir_] = {
            "range_low": range_low,
            "range_high": range_high,
            "top_2_strikes": [
                {"strike": s["strike"], "ask_x100": s["ask_x100"], "pct": s["pct"]}
                for s in top_2
            ],
            "day_of_week": day_names.get(weekday, "?"),
            "zone": zone_name,
            "zone_range": [zone_low, zone_high],
            "strikes_analyzed": strike_data,
            "contracts_in_range": contracts_in_range,
            "recommended_contract": recommended,
        }

    result = {
        "ticker": ticker,
        "price": round(price, 2),
        "expiration": target_exp,
        "days_to_expiry": dte,
        "ranges": results_summary,
    }
    if tips:
        result["tips"] = tips
    return result


# ── Batch Download ───────────────────────────────────────────────────────────


@mcp.tool()
def batch_download(
    tickers: list[str],
    period: str = "1mo",
    interval: str = "1d",
) -> dict:
    """Download OHLCV price history for multiple tickers at once.

    Args:
        tickers: List of ticker symbols (e.g. ["AAPL", "MSFT", "GOOGL"]).
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max).
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo).

    Returns:
        dict with per-ticker OHLCV records.
    """
    try:
        df = yf.download(tickers, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return {"tickers": tickers, "data": {}}
        result = {"tickers": tickers, "data": {}}
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    ticker_df = df.copy()
                else:
                    ticker_df = df.xs(ticker, level="Ticker", axis=1)
                result["data"][ticker] = df_to_records(ticker_df)
            except Exception:
                result["data"][ticker] = []
        return result
    except Exception as e:
        return {"error": str(e), "tickers": tickers}


# ── Research Tools (sector classification, valuation, charts, peers) ───────────


mcp.add_tool(research.classify_sector)
mcp.add_tool(research.get_latest_quarter_snapshot)
mcp.add_tool(research.compute_valuation_model)
mcp.add_tool(research.generate_charts)
mcp.add_tool(research.get_peer_snapshot)


def main():
    """Entry point for the yfinance-mcp command."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
