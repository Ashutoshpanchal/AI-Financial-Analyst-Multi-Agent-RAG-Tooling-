import pytest

from app.tools.financial_metrics import (
    ToolResult,
    calculate_cagr,
    calculate_debt_to_equity,
    calculate_ebitda,
    calculate_pe_ratio,
    calculate_profit_margin,
)

# ── P/E Ratio ─────────────────────────────────────────────────────────────────


class TestPeRatio:
    def test_basic_calculation(self):
        result = calculate_pe_ratio(stock_price=150.0, earnings_per_share=10.0)
        assert result.value == 15.0
        assert result.formatted == "P/E Ratio: 15.0x"

    def test_returns_tool_result(self):
        result = calculate_pe_ratio(100.0, 5.0)
        assert isinstance(result, ToolResult)
        assert result.inputs == {"stock_price": 100.0, "earnings_per_share": 5.0}

    def test_rounds_to_two_decimals(self):
        result = calculate_pe_ratio(100.0, 3.0)
        assert result.value == 33.33

    def test_zero_eps_raises(self):
        with pytest.raises(ValueError, match="zero"):
            calculate_pe_ratio(100.0, 0.0)

    def test_negative_stock_price_raises(self):
        with pytest.raises(ValueError, match="negative"):
            calculate_pe_ratio(-50.0, 10.0)

    def test_negative_eps_raises(self):
        with pytest.raises(ValueError, match="negative"):
            calculate_pe_ratio(100.0, -5.0)

    def test_formula_present(self):
        result = calculate_pe_ratio(100.0, 5.0)
        assert "EPS" in result.formula


# ── CAGR ──────────────────────────────────────────────────────────────────────


class TestCagr:
    def test_basic_calculation(self):
        # 1000 → 2000 in 10 years = ~7.18% CAGR
        result = calculate_cagr(start_value=1000.0, end_value=2000.0, years=10.0)
        assert abs(result.value - 0.0718) < 0.001
        assert "CAGR" in result.formatted

    def test_zero_growth(self):
        result = calculate_cagr(1000.0, 1000.0, 5.0)
        assert result.value == 0.0

    def test_one_year(self):
        result = calculate_cagr(100.0, 120.0, 1.0)
        assert result.value == pytest.approx(0.20, abs=0.001)

    def test_zero_start_raises(self):
        with pytest.raises(ValueError, match="positive"):
            calculate_cagr(0.0, 1000.0, 5.0)

    def test_negative_start_raises(self):
        with pytest.raises(ValueError, match="positive"):
            calculate_cagr(-100.0, 1000.0, 5.0)

    def test_zero_end_raises(self):
        with pytest.raises(ValueError, match="positive"):
            calculate_cagr(1000.0, 0.0, 5.0)

    def test_zero_years_raises(self):
        with pytest.raises(ValueError, match="positive"):
            calculate_cagr(1000.0, 2000.0, 0.0)

    def test_inputs_recorded(self):
        result = calculate_cagr(1000.0, 2000.0, 10.0)
        assert result.inputs["start_value"] == 1000.0
        assert result.inputs["years"] == 10.0


# ── EBITDA ────────────────────────────────────────────────────────────────────


class TestEbitda:
    def test_basic_calculation(self):
        result = calculate_ebitda(
            net_income=500_000,
            interest=50_000,
            taxes=100_000,
            depreciation=80_000,
            amortization=20_000,
        )
        assert result.value == 750_000.0
        assert "$750,000.00" in result.formatted

    def test_zero_addbacks(self):
        result = calculate_ebitda(1_000_000, 0, 0, 0, 0)
        assert result.value == 1_000_000.0

    def test_negative_net_income(self):
        # Loss-making company can still have positive EBITDA
        result = calculate_ebitda(-200_000, 50_000, 0, 300_000, 50_000)
        assert result.value == 200_000.0

    def test_all_inputs_recorded(self):
        result = calculate_ebitda(100, 10, 20, 30, 40)
        assert result.inputs["net_income"] == 100
        assert result.inputs["amortization"] == 40

    def test_rounding(self):
        result = calculate_ebitda(1.001, 0, 0, 0, 0)
        assert result.value == round(1.001, 2)


# ── Debt-to-Equity ────────────────────────────────────────────────────────────


class TestDebtToEquity:
    def test_basic_calculation(self):
        result = calculate_debt_to_equity(
            total_debt=500_000, shareholders_equity=250_000
        )
        assert result.value == 2.0
        assert result.formatted == "Debt-to-Equity: 2.0x"

    def test_zero_debt(self):
        result = calculate_debt_to_equity(0, 1_000_000)
        assert result.value == 0.0

    def test_negative_equity(self):
        # Technically valid — company with negative equity
        result = calculate_debt_to_equity(500_000, -100_000)
        assert result.value == -5.0

    def test_zero_equity_raises(self):
        with pytest.raises(ValueError, match="zero"):
            calculate_debt_to_equity(500_000, 0)

    def test_rounds_to_two_decimals(self):
        result = calculate_debt_to_equity(1_000_000, 3_000_000)
        assert result.value == 0.33


# ── Profit Margin ─────────────────────────────────────────────────────────────


class TestProfitMargin:
    def test_basic_calculation(self):
        result = calculate_profit_margin(net_income=200_000, revenue=1_000_000)
        assert result.value == 20.0
        assert result.formatted == "Profit Margin: 20.0%"

    def test_loss_margin(self):
        result = calculate_profit_margin(-100_000, 1_000_000)
        assert result.value == -10.0

    def test_100_percent_margin(self):
        result = calculate_profit_margin(500, 500)
        assert result.value == 100.0

    def test_zero_revenue_raises(self):
        with pytest.raises(ValueError, match="zero"):
            calculate_profit_margin(100_000, 0)

    def test_rounds_to_two_decimals(self):
        result = calculate_profit_margin(1, 3)
        assert result.value == 33.33

    def test_inputs_recorded(self):
        result = calculate_profit_margin(200_000, 1_000_000)
        assert result.inputs == {"net_income": 200_000, "revenue": 1_000_000}

    def test_formula_present(self):
        result = calculate_profit_margin(100, 1000)
        assert "Revenue" in result.formula
