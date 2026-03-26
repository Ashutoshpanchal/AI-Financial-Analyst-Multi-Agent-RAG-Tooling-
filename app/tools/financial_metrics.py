"""
Financial Metrics — deterministic calculation functions.

Rules:
- No LLM calls. Ever.
- Every function validates its inputs and raises ValueError on bad data.
- Every function returns a typed dict with result + formula explanation.
  The explanation is injected into the LLM prompt so the agent can
  cite the calculation — not hallucinate it.
"""

from dataclasses import dataclass


@dataclass
class ToolResult:
    """Standard return type for all financial tools."""
    value: float
    formatted: str          # human-readable result
    formula: str            # the formula used (for LLM context)
    inputs: dict            # the inputs used (for auditability)


# ── P/E Ratio ────────────────────────────────────────────────────────────────

def calculate_pe_ratio(
    stock_price: float,
    earnings_per_share: float,
) -> ToolResult:
    """
    Price-to-Earnings ratio = Stock Price / EPS.

    Interpretation:
    - High P/E: market expects high future growth
    - Low P/E: undervalued or slow growth expected
    """
    if earnings_per_share == 0:
        raise ValueError("EPS cannot be zero — division by zero")
    if stock_price < 0:
        raise ValueError(f"Stock price cannot be negative, got {stock_price}")
    if earnings_per_share < 0:
        raise ValueError(
            f"EPS is negative ({earnings_per_share}) — P/E is not meaningful for loss-making companies"
        )

    pe = round(stock_price / earnings_per_share, 2)

    return ToolResult(
        value=pe,
        formatted=f"P/E Ratio: {pe}x",
        formula="P/E = Stock Price / EPS",
        inputs={"stock_price": stock_price, "earnings_per_share": earnings_per_share},
    )


# ── CAGR ─────────────────────────────────────────────────────────────────────

def calculate_cagr(
    start_value: float,
    end_value: float,
    years: float,
) -> ToolResult:
    """
    Compound Annual Growth Rate.
    CAGR = (end_value / start_value) ^ (1 / years) - 1

    Measures the smoothed annual growth rate over a period.
    """
    if start_value <= 0:
        raise ValueError(f"Start value must be positive, got {start_value}")
    if end_value <= 0:
        raise ValueError(f"End value must be positive, got {end_value}")
    if years <= 0:
        raise ValueError(f"Years must be positive, got {years}")

    cagr = ((end_value / start_value) ** (1 / years)) - 1
    cagr_pct = round(cagr * 100, 2)

    return ToolResult(
        value=cagr,
        formatted=f"CAGR: {cagr_pct}%",
        formula="CAGR = (end_value / start_value) ^ (1 / years) - 1",
        inputs={"start_value": start_value, "end_value": end_value, "years": years},
    )


# ── EBITDA ───────────────────────────────────────────────────────────────────

def calculate_ebitda(
    net_income: float,
    interest: float,
    taxes: float,
    depreciation: float,
    amortization: float,
) -> ToolResult:
    """
    EBITDA = Net Income + Interest + Taxes + Depreciation + Amortization

    Used to evaluate operating performance independent of
    financing decisions and accounting choices.
    """
    ebitda = net_income + interest + taxes + depreciation + amortization
    ebitda = round(ebitda, 2)

    return ToolResult(
        value=ebitda,
        formatted=f"EBITDA: ${ebitda:,.2f}",
        formula="EBITDA = Net Income + Interest + Taxes + Depreciation + Amortization",
        inputs={
            "net_income": net_income,
            "interest": interest,
            "taxes": taxes,
            "depreciation": depreciation,
            "amortization": amortization,
        },
    )


# ── Debt-to-Equity ───────────────────────────────────────────────────────────

def calculate_debt_to_equity(
    total_debt: float,
    shareholders_equity: float,
) -> ToolResult:
    """
    D/E Ratio = Total Debt / Shareholders' Equity.
    Measures financial leverage.
    """
    if shareholders_equity == 0:
        raise ValueError("Shareholders equity cannot be zero")

    de = round(total_debt / shareholders_equity, 2)

    return ToolResult(
        value=de,
        formatted=f"Debt-to-Equity: {de}x",
        formula="D/E = Total Debt / Shareholders' Equity",
        inputs={"total_debt": total_debt, "shareholders_equity": shareholders_equity},
    )


# ── Profit Margin ────────────────────────────────────────────────────────────

def calculate_profit_margin(
    net_income: float,
    revenue: float,
) -> ToolResult:
    """
    Net Profit Margin = Net Income / Revenue * 100
    """
    if revenue == 0:
        raise ValueError("Revenue cannot be zero")

    margin = round((net_income / revenue) * 100, 2)

    return ToolResult(
        value=margin,
        formatted=f"Profit Margin: {margin}%",
        formula="Profit Margin = (Net Income / Revenue) × 100",
        inputs={"net_income": net_income, "revenue": revenue},
    )
