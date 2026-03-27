"""
Stock search API — live company data via yfinance (no API key needed).

Endpoints:
  GET /stock/search?q=Apple     ← search by company name or ticker
  GET /stock/{ticker}           ← full data for a specific ticker
"""

import yfinance as yf
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/stock/search")
async def search_stocks(q: str) -> list[dict]:
    """
    Search for stocks by company name or ticker.
    Returns a list of matching tickers with basic info.
    """
    if not q or len(q.strip()) < 1:
        return []

    try:
        search = yf.Search(q.strip(), max_results=8)
        results = []
        for quote in search.quotes:
            results.append({
                "symbol":    quote.get("symbol", ""),
                "name":      quote.get("longname") or quote.get("shortname", ""),
                "exchange":  quote.get("exchange", ""),
                "type":      quote.get("quoteType", ""),
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{ticker}")
async def get_stock(ticker: str) -> dict:
    """
    Fetch full live stock data for a ticker symbol.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        if not info or info.get("quoteType") is None:
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")

        def safe(val):
            return val if val is not None else None

        return {
            "symbol":           ticker.upper(),
            "name":             safe(info.get("longName") or info.get("shortName")),
            "sector":           safe(info.get("sector")),
            "industry":         safe(info.get("industry")),
            "country":          safe(info.get("country")),
            "website":          safe(info.get("website")),
            "description":      safe(info.get("longBusinessSummary")),
            # Price
            "price":            safe(info.get("currentPrice") or info.get("regularMarketPrice")),
            "prev_close":       safe(info.get("previousClose")),
            "open":             safe(info.get("open")),
            "day_low":          safe(info.get("dayLow")),
            "day_high":         safe(info.get("dayHigh")),
            "week_52_low":      safe(info.get("fiftyTwoWeekLow")),
            "week_52_high":     safe(info.get("fiftyTwoWeekHigh")),
            # Valuation
            "market_cap":       safe(info.get("marketCap")),
            "pe_ratio":         safe(info.get("trailingPE")),
            "forward_pe":       safe(info.get("forwardPE")),
            "eps":              safe(info.get("trailingEps")),
            "price_to_book":    safe(info.get("priceToBook")),
            # Financials
            "revenue":          safe(info.get("totalRevenue")),
            "net_income":       safe(info.get("netIncomeToCommon")),
            "total_debt":       safe(info.get("totalDebt")),
            "total_cash":       safe(info.get("totalCash")),
            "ebitda":           safe(info.get("ebitda")),
            "gross_margins":    safe(info.get("grossMargins")),
            "profit_margins":   safe(info.get("profitMargins")),
            # Dividends
            "dividend_yield":   safe(info.get("dividendYield")),
            "dividend_rate":    safe(info.get("dividendRate")),
            # Other
            "beta":             safe(info.get("beta")),
            "shares_outstanding": safe(info.get("sharesOutstanding")),
            "float_shares":     safe(info.get("floatShares")),
            "avg_volume":       safe(info.get("averageVolume")),
            "volume":           safe(info.get("volume")),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
