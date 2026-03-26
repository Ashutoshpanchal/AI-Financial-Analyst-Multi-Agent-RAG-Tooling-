"""
MCP Server — exposes financial tools and resources via Model Context Protocol.

Two transport modes:
  1. SSE  (Server-Sent Events) — mounted inside FastAPI at /mcp
           Used by: web clients, Cursor, any HTTP-based MCP client
           Run via: docker-compose up (always on)

  2. stdio — communicates over stdin/stdout as a subprocess
           Used by: Claude Desktop, Claude Code CLI
           Run via: python mcp_stdio.py

What is exposed:

  Tools (callable by MCP clients):
    - calculate_pe_ratio
    - calculate_cagr
    - calculate_ebitda
    - calculate_debt_to_equity
    - calculate_profit_margin
    - analyze_query         ← runs the full LangGraph workflow

  Resources (readable context by MCP clients):
    - financial://formulas  ← reference sheet of all formulas
    - financial://metrics   ← metric definitions and interpretations

  Prompts (reusable prompt templates):
    - financial_analysis    ← structured prompt for financial queries
"""

from fastmcp import FastMCP
from app.tools.financial_metrics import (
    calculate_pe_ratio,
    calculate_cagr,
    calculate_ebitda,
    calculate_debt_to_equity,
    calculate_profit_margin,
)

mcp = FastMCP(
    name="AI Financial Analyst",
    instructions="""
You are connected to a financial analysis system.
Use the calculation tools for any quantitative financial questions.
Use the analyze_query tool for complex multi-step financial analysis.
Resources provide reference formulas and metric definitions.
""",
)


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def pe_ratio(stock_price: float, earnings_per_share: float) -> str:
    """
    Calculate Price-to-Earnings (P/E) ratio.
    Measures how much investors pay per dollar of earnings.
    High P/E = growth expectations. Low P/E = value or slow growth.

    Args:
        stock_price: Current stock price in dollars
        earnings_per_share: Annual EPS (earnings per share)
    """
    try:
        result = calculate_pe_ratio(stock_price, earnings_per_share)
        return (
            f"**{result.formatted}**\n"
            f"Formula: {result.formula}\n"
            f"Inputs: Stock Price=${result.inputs['stock_price']}, "
            f"EPS=${result.inputs['earnings_per_share']}"
        )
    except ValueError as e:
        return f"Calculation error: {str(e)}"


@mcp.tool()
def cagr(start_value: float, end_value: float, years: float) -> str:
    """
    Calculate Compound Annual Growth Rate (CAGR).
    Measures smoothed annual growth over a multi-year period.
    More accurate than simple average growth rate.

    Args:
        start_value: Beginning value (revenue, price, etc.)
        end_value: Ending value
        years: Number of years in the period
    """
    try:
        result = calculate_cagr(start_value, end_value, years)
        return (
            f"**{result.formatted}**\n"
            f"Formula: {result.formula}\n"
            f"Inputs: Start={result.inputs['start_value']}, "
            f"End={result.inputs['end_value']}, "
            f"Years={result.inputs['years']}"
        )
    except ValueError as e:
        return f"Calculation error: {str(e)}"


@mcp.tool()
def ebitda(
    net_income: float,
    interest: float,
    taxes: float,
    depreciation: float,
    amortization: float,
) -> str:
    """
    Calculate EBITDA (Earnings Before Interest, Taxes, Depreciation, Amortization).
    Measures core operating profitability, independent of financing and accounting.

    Args:
        net_income: Net income / bottom line profit
        interest: Interest expense
        taxes: Tax expense
        depreciation: Depreciation expense
        amortization: Amortization expense
    """
    try:
        result = calculate_ebitda(net_income, interest, taxes, depreciation, amortization)
        return (
            f"**{result.formatted}**\n"
            f"Formula: {result.formula}\n"
            f"Inputs: {result.inputs}"
        )
    except ValueError as e:
        return f"Calculation error: {str(e)}"


@mcp.tool()
def debt_to_equity(total_debt: float, shareholders_equity: float) -> str:
    """
    Calculate Debt-to-Equity (D/E) ratio.
    Measures financial leverage. High D/E = more risk but potential for higher returns.

    Args:
        total_debt: Total debt (short-term + long-term)
        shareholders_equity: Total shareholders equity
    """
    try:
        result = calculate_debt_to_equity(total_debt, shareholders_equity)
        return (
            f"**{result.formatted}**\n"
            f"Formula: {result.formula}\n"
            f"Inputs: Debt={result.inputs['total_debt']}, "
            f"Equity={result.inputs['shareholders_equity']}"
        )
    except ValueError as e:
        return f"Calculation error: {str(e)}"


@mcp.tool()
def profit_margin(net_income: float, revenue: float) -> str:
    """
    Calculate Net Profit Margin.
    Percentage of revenue that becomes profit after all expenses.

    Args:
        net_income: Net income / bottom line
        revenue: Total revenue
    """
    try:
        result = calculate_profit_margin(net_income, revenue)
        return (
            f"**{result.formatted}**\n"
            f"Formula: {result.formula}\n"
            f"Inputs: Net Income={result.inputs['net_income']}, "
            f"Revenue={result.inputs['revenue']}"
        )
    except ValueError as e:
        return f"Calculation error: {str(e)}"


@mcp.tool()
async def analyze_query(query: str, user_id: str = "mcp_user") -> str:
    """
    Run a full multi-agent financial analysis using the LangGraph workflow.
    Use this for complex questions that require document retrieval, calculations,
    or multi-step reasoning — not just a single metric calculation.

    Examples:
      - "What are the main risk factors in Apple's 10-K?"
      - "Calculate Apple's revenue CAGR from 2020 to 2023 based on the uploaded report"
      - "Compare Tesla and Ford P/E ratios"

    Args:
        query: The financial question to analyze
        user_id: Optional user identifier for tracing
    """
    from app.services.analyst_service import run_analysis

    try:
        result = await run_analysis(query=query, user_id=user_id)
        parts = [f"**Query Type:** {result.get('query_type', 'unknown')}"]

        if result.get("plan"):
            parts.append(f"**Plan:** {result['plan']}")

        if result.get("steps"):
            steps = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(result["steps"]))
            parts.append(f"**Steps:**\n{steps}")

        if result.get("answer"):
            parts.append(f"**Answer:** {result['answer']}")

        if result.get("errors"):
            parts.append(f"**Errors:** {', '.join(result['errors'])}")

        if result.get("trace_id"):
            parts.append(f"**Trace ID:** {result['trace_id']}")

        return "\n\n".join(parts)

    except Exception as e:
        return f"Analysis failed: {str(e)}"


# ── Resources ─────────────────────────────────────────────────────────────────

@mcp.resource("financial://formulas")
def financial_formulas() -> str:
    """
    Reference sheet of all supported financial formulas.
    Read this to understand what calculations are available.
    """
    return """
# Financial Formulas Reference

## P/E Ratio
Formula: P/E = Stock Price / EPS
Use: Valuation — how much investors pay per $1 of earnings
Tool: pe_ratio(stock_price, earnings_per_share)

## CAGR (Compound Annual Growth Rate)
Formula: CAGR = (End Value / Start Value) ^ (1 / Years) - 1
Use: Measure smoothed annual growth over a period
Tool: cagr(start_value, end_value, years)

## EBITDA
Formula: EBITDA = Net Income + Interest + Taxes + Depreciation + Amortization
Use: Operating profitability without financing/accounting effects
Tool: ebitda(net_income, interest, taxes, depreciation, amortization)

## Debt-to-Equity
Formula: D/E = Total Debt / Shareholders Equity
Use: Financial leverage — risk from debt load
Tool: debt_to_equity(total_debt, shareholders_equity)

## Net Profit Margin
Formula: Margin = (Net Income / Revenue) × 100
Use: What % of revenue becomes profit
Tool: profit_margin(net_income, revenue)
"""


@mcp.resource("financial://metrics")
def metric_interpretations() -> str:
    """
    Interpretation guide for financial metrics.
    Explains what good/bad values look like for each metric.
    """
    return """
# Financial Metric Interpretations

## P/E Ratio
- < 10:   Possibly undervalued or declining business
- 10–20:  Fairly valued (mature company)
- 20–40:  Growth company, high expectations
- > 40:   Very high growth expected or potentially overvalued

## CAGR
- < 5%:   Slow growth (utilities, mature markets)
- 5–15%:  Moderate growth (large caps)
- 15–25%: High growth (tech, emerging markets)
- > 25%:  Hypergrowth (startups, small caps)

## EBITDA Margin (EBITDA / Revenue)
- < 10%:  Low profitability
- 10–20%: Average profitability
- 20–40%: Strong profitability
- > 40%:  Exceptional (software, platforms)

## Debt-to-Equity
- < 1:    Conservative, low leverage
- 1–2:    Moderate leverage
- > 2:    High leverage, higher risk

## Net Profit Margin
- < 5%:   Thin margins (retail, grocery)
- 5–15%:  Average
- 15–30%: Strong (tech, pharma)
- > 30%:  Exceptional
"""


# ── Prompts ───────────────────────────────────────────────────────────────────

@mcp.prompt()
def financial_analysis_prompt(company: str, analysis_type: str = "comprehensive") -> str:
    """
    Reusable prompt template for financial analysis.
    Injects the right structure depending on analysis type.

    Args:
        company: Company name or ticker (e.g. "Apple" or "AAPL")
        analysis_type: "valuation", "growth", "profitability", or "comprehensive"
    """
    type_instructions = {
        "valuation": "Focus on P/E ratio, Price-to-Book, and EV/EBITDA valuation multiples.",
        "growth":    "Focus on revenue CAGR, earnings growth, and market expansion.",
        "profitability": "Focus on EBITDA margin, net profit margin, and return on equity.",
        "comprehensive": "Cover valuation, growth rates, profitability, and debt levels.",
    }

    instruction = type_instructions.get(analysis_type, type_instructions["comprehensive"])

    return f"""Perform a {analysis_type} financial analysis for {company}.

{instruction}

Steps:
1. Read financial://formulas to understand available calculations
2. Use the appropriate calculation tools with the correct inputs
3. Interpret each result using financial://metrics as a reference
4. Provide a clear summary with actionable insights

If financial documents have been uploaded, use analyze_query to search them.
Always cite the formula and inputs used for each calculation."""
