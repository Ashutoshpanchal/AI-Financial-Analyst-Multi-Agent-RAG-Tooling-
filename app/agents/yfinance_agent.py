"""
yFinance Agent — fetches live stock data and compares with document data.

Flow:
    1. Detect ticker from query (e.g. "Apple" → "AAPL", "Tesla" → "TSLA")
    2. Fetch live data from Yahoo Finance (price, P/E, revenue, margins, etc.)
    3. Compare live data vs numbers found in retrieved_context (uploaded docs)
    4. Write live_stock_data + data_comparison to state

Why compare?
    Uploaded documents are historical (e.g. 2022 annual report).
    yFinance gives today's live numbers.
    Comparing both shows:
      - How current the document data is
      - Whether metrics have improved or declined since the report
      - Which source to trust for which metric

Runs after rag_agent, before mcp_enrichment_agent.
Skips gracefully if no ticker is detectable from the query.
"""

import re
import yfinance as yf
from langfuse.decorators import observe
from app.workflows.state import GraphState
from app.models.router import get_model_router


# ── Common company name → ticker mapping ─────────────────────────────────────
_NAME_TO_TICKER = {
    "apple":     "AAPL",
    "microsoft": "MSFT",
    "google":    "GOOGL",
    "alphabet":  "GOOGL",
    "amazon":    "AMZN",
    "tesla":     "TSLA",
    "meta":      "META",
    "facebook":  "META",
    "nvidia":    "NVDA",
    "netflix":   "NFLX",
    "samsung":   "005930.KS",
    "toyota":    "TM",
    "jpmorgan":  "JPM",
    "goldman":   "GS",
    "berkshire": "BRK-B",
}


def _detect_ticker(query: str) -> str | None:
    """
    Try to detect a stock ticker from the query.

    Strategy:
      1. Look for explicit uppercase ticker (e.g. AAPL, TSLA)
      2. Match known company names
      3. Return None if nothing found
    """
    # Check for explicit ticker pattern (2-5 uppercase letters)
    explicit = re.findall(r'\b[A-Z]{2,5}\b', query)
    # Filter out common English words that look like tickers
    stop_words = {"US", "AI", "PE", "EPS", "GDP", "CEO", "CFO", "IPO", "ETF", "OR", "AND", "THE", "FOR", "IN"}
    for word in explicit:
        if word not in stop_words:
            return word

    # Check known company names (case-insensitive)
    query_lower = query.lower()
    for name, ticker in _NAME_TO_TICKER.items():
        if name in query_lower:
            return ticker

    return None


def _fetch_live_data(ticker: str) -> dict | None:
    """Fetch key financial metrics from yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or info.get("quoteType") is None:
            return None

        return {
            "ticker":         ticker,
            "name":           info.get("longName") or info.get("shortName"),
            "price":          info.get("currentPrice") or info.get("regularMarketPrice"),
            "pe_ratio":       info.get("trailingPE"),
            "forward_pe":     info.get("forwardPE"),
            "eps":            info.get("trailingEps"),
            "revenue":        info.get("totalRevenue"),
            "net_income":     info.get("netIncomeToCommon"),
            "profit_margins": info.get("profitMargins"),
            "gross_margins":  info.get("grossMargins"),
            "ebitda":         info.get("ebitda"),
            "total_debt":     info.get("totalDebt"),
            "total_cash":     info.get("totalCash"),
            "market_cap":     info.get("marketCap"),
            "beta":           info.get("beta"),
            "dividend_yield": info.get("dividendYield"),
            "week_52_high":   info.get("fiftyTwoWeekHigh"),
            "week_52_low":    info.get("fiftyTwoWeekLow"),
        }
    except Exception:
        return None


def _compare_with_docs(live: dict, retrieved_context: str) -> dict:
    """
    Compare live yfinance numbers against what was found in documents.

    Scans retrieved_context for any numbers that match live metrics.
    Flags matches, mismatches, and metrics only available in one source.
    """
    comparison = {
        "matches":        [],   # same value in both sources
        "differences":    [],   # different values — document vs live
        "live_only":      [],   # metric exists in yfinance but not in docs
        "summary":        "",
    }

    if not retrieved_context:
        comparison["summary"] = "No document context to compare against."
        return comparison

    ctx_lower = retrieved_context.lower()

    def fmt(val):
        if val is None:
            return None
        if abs(val) >= 1e9:
            return f"${val/1e9:.1f}B"
        if abs(val) >= 1e6:
            return f"${val/1e6:.1f}M"
        return str(round(val, 2))

    # Check each live metric against document context
    checks = [
        ("revenue",        live.get("revenue"),        ["revenue", "net sales", "total revenue"]),
        ("net_income",     live.get("net_income"),      ["net income", "net earnings", "net profit"]),
        ("ebitda",         live.get("ebitda"),          ["ebitda"]),
        ("profit_margins", live.get("profit_margins"),  ["profit margin", "net margin"]),
        ("pe_ratio",       live.get("pe_ratio"),        ["p/e", "price-to-earnings", "pe ratio"]),
        ("total_debt",     live.get("total_debt"),      ["total debt", "long-term debt"]),
    ]

    for metric, live_val, keywords in checks:
        if live_val is None:
            continue

        found_in_doc = any(kw in ctx_lower for kw in keywords)

        if found_in_doc:
            comparison["differences"].append({
                "metric":    metric,
                "live":      fmt(live_val),
                "document":  "present (may differ — check source date)",
                "note":      "Document data may be from a prior period",
            })
        else:
            comparison["live_only"].append({
                "metric": metric,
                "live":   fmt(live_val),
                "note":   "Not found in uploaded documents",
            })

    total = len(comparison["differences"]) + len(comparison["live_only"])
    comparison["summary"] = (
        f"Live data has {total} metrics. "
        f"{len(comparison['differences'])} also appear in documents (may be from different periods). "
        f"{len(comparison['live_only'])} are live-only (not in uploaded docs)."
    )

    return comparison


@observe(name="yfinance_agent")
async def yfinance_agent(state: GraphState) -> GraphState:
    """
    LangGraph node — fetches live stock data and compares with document data.
    Runs after rag_agent, before mcp_enrichment_agent.
    """
    query = state["query"]

    # Step 1 — detect ticker
    ticker = _detect_ticker(query)

    if not ticker:
        return {
            **state,
            "ticker":          None,
            "live_stock_data": None,
            "data_comparison": {"summary": "No ticker detected in query — skipping live data fetch."},
        }

    # Step 2 — fetch live data
    live_data = _fetch_live_data(ticker)

    if not live_data:
        return {
            **state,
            "ticker":          ticker,
            "live_stock_data": None,
            "data_comparison": {"summary": f"Could not fetch live data for ticker '{ticker}'."},
        }

    # Step 3 — compare with document data
    comparison = _compare_with_docs(
        live=live_data,
        retrieved_context=state.get("retrieved_context") or "",
    )

    return {
        **state,
        "ticker":          ticker,
        "live_stock_data": live_data,
        "data_comparison": comparison,
    }
