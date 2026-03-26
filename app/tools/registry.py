"""
Tool Registry — wraps financial metric functions as LangChain tools.

Key concept (why wrap as tools?):
    LangChain tools are the bridge between an LLM and Python functions.
    The LLM sees the tool name + docstring and decides WHEN to call it
    and WHAT arguments to pass.

    Without tools:  LLM guesses the CAGR → may hallucinate
    With tools:     LLM calls calculate_cagr(100, 150, 3) → guaranteed correct

    The @tool decorator:
    - Generates a JSON schema from the function signature
    - That schema is sent to the LLM so it knows what inputs to provide
    - LangGraph's ToolNode handles the actual execution
"""

from langchain_core.tools import tool
from app.tools.financial_metrics import (
    calculate_pe_ratio,
    calculate_cagr,
    calculate_ebitda,
    calculate_debt_to_equity,
    calculate_profit_margin,
)


@tool
def pe_ratio_tool(stock_price: float, earnings_per_share: float) -> str:
    """
    Calculate Price-to-Earnings (P/E) ratio.
    Use when the user asks about stock valuation or P/E ratio.
    Requires: current stock price and earnings per share (EPS).
    """
    try:
        result = calculate_pe_ratio(stock_price, earnings_per_share)
        return f"{result.formatted} | Formula: {result.formula} | Inputs: {result.inputs}"
    except ValueError as e:
        return f"Error: {str(e)}"


@tool
def cagr_tool(start_value: float, end_value: float, years: float) -> str:
    """
    Calculate Compound Annual Growth Rate (CAGR).
    Use when the user asks about growth rate over multiple years.
    Requires: starting value, ending value, and number of years.
    """
    try:
        result = calculate_cagr(start_value, end_value, years)
        return f"{result.formatted} | Formula: {result.formula} | Inputs: {result.inputs}"
    except ValueError as e:
        return f"Error: {str(e)}"


@tool
def ebitda_tool(
    net_income: float,
    interest: float,
    taxes: float,
    depreciation: float,
    amortization: float,
) -> str:
    """
    Calculate EBITDA (Earnings Before Interest, Taxes, Depreciation, Amortization).
    Use when the user asks about operating profitability or EBITDA.
    Requires: net income, interest expense, tax expense, depreciation, amortization.
    """
    try:
        result = calculate_ebitda(net_income, interest, taxes, depreciation, amortization)
        return f"{result.formatted} | Formula: {result.formula} | Inputs: {result.inputs}"
    except ValueError as e:
        return f"Error: {str(e)}"


@tool
def debt_to_equity_tool(total_debt: float, shareholders_equity: float) -> str:
    """
    Calculate Debt-to-Equity (D/E) ratio.
    Use when the user asks about financial leverage or debt levels.
    Requires: total debt and total shareholders equity.
    """
    try:
        result = calculate_debt_to_equity(total_debt, shareholders_equity)
        return f"{result.formatted} | Formula: {result.formula} | Inputs: {result.inputs}"
    except ValueError as e:
        return f"Error: {str(e)}"


@tool
def profit_margin_tool(net_income: float, revenue: float) -> str:
    """
    Calculate Net Profit Margin percentage.
    Use when the user asks about profitability or profit margin.
    Requires: net income and total revenue.
    """
    try:
        result = calculate_profit_margin(net_income, revenue)
        return f"{result.formatted} | Formula: {result.formula} | Inputs: {result.inputs}"
    except ValueError as e:
        return f"Error: {str(e)}"


# All tools in one list — bind this to the LLM in ComputationAgent
FINANCIAL_TOOLS = [
    pe_ratio_tool,
    cagr_tool,
    ebitda_tool,
    debt_to_equity_tool,
    profit_margin_tool,
]
