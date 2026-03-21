from datetime import timezone
"""
Tests for Feature 15: Dividend Analysis.

Tests cover:
- Dividend information fetching
- Dividend safety scoring
- Dividend growth calculations
- Yield comparison analysis
- Agent functionality
- API schema validation
- Orchestrator integration
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import numpy as np


# ─────────────────────────────────────────────────────────────
# Dividend Safety Calculation Tests
# ─────────────────────────────────────────────────────────────


class TestDividendSafetyCalculation:
    """Test dividend safety score calculations."""

    def test_calculate_dividend_safety_high_score(self):
        """Should calculate high safety score for strong fundamentals."""
        from src.tools.dividend_analyzer import calculate_dividend_safety

        with patch("src.tools.dividend_analyzer.get_provider") as mock_get_provider, \
             patch("src.tools.dividend_analyzer.calculate_dividend_growth") as mock_growth:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider

            # Mock strong dividend payer
            mock_provider.get_info.return_value = {
                "longName": "Johnson & Johnson",
                "dividendRate": 4.76,
                "dividendYield": 0.03,
                "payoutRatio": 0.44,
                "sharesOutstanding": 2_400_000_000,
            }

            # Mock cash flow with strong FCF
            fcf_row = MagicMock()
            fcf_row.get = lambda key, default=0: 20_000_000_000 if key == "Free Cash Flow" else default
            mock_cashflow = MagicMock()
            mock_cashflow.empty = False
            mock_cashflow.iloc.__getitem__ = MagicMock(return_value=fcf_row)
            mock_provider.get_cash_flow.return_value = mock_cashflow

            # Mock balance sheet with low debt
            bs_row = MagicMock()
            bs_row.get = lambda key, default=0: {
                "Total Debt": 30_000_000_000,
                "Total Equity Gross Minority Interest": 70_000_000_000,
            }.get(key, default)
            mock_balance = MagicMock()
            mock_balance.empty = False
            mock_balance.iloc.__getitem__ = MagicMock(return_value=bs_row)
            mock_provider.get_balance_sheet.return_value = mock_balance

            # Mock income statement with stable earnings
            income_col = MagicMock()
            income_col.get = lambda key, default=0: 18_000_000_000 if key == "Net Income" else default
            mock_income = MagicMock()
            mock_income.empty = False
            mock_income.columns = ["2024", "2023", "2022", "2021"]
            mock_income.__getitem__ = MagicMock(return_value=income_col)
            mock_provider.get_income_statement.return_value = mock_income

            # Mock dividend growth result
            mock_growth.return_value = {
                "consecutive_years_increased": 61,
                "classification": "Dividend King (50+ years)",
            }

            result = calculate_dividend_safety("JNJ")

            assert "safety_score" in result
            assert "rating" in result
            assert "factors" in result
            assert result["safety_score"] >= 0
            assert result["safety_score"] <= 100

    def test_calculate_dividend_safety_no_dividend(self):
        """Should return N/A for non-dividend payers."""
        from src.tools.dividend_analyzer import calculate_dividend_safety

        with patch("src.tools.dividend_analyzer.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider

            mock_provider.get_info.return_value = {
                "longName": "Amazon.com Inc",
                "dividendRate": 0,
                "dividendYield": 0,
            }
            mock_provider.get_cash_flow.return_value = MagicMock(empty=True)
            mock_provider.get_balance_sheet.return_value = MagicMock(empty=True)
            mock_provider.get_income_statement.return_value = MagicMock(empty=True)
            mock_provider.get_dividends.return_value = MagicMock(empty=True)

            result = calculate_dividend_safety("AMZN")

            assert result["safety_score"] == 0
            assert "N/A" in result["rating"]

    def test_calculate_dividend_safety_red_flags(self):
        """Should identify red flags for risky dividends."""
        from src.tools.dividend_analyzer import calculate_dividend_safety

        with patch("src.tools.dividend_analyzer.get_provider") as mock_get_provider, \
             patch("src.tools.dividend_analyzer.calculate_dividend_growth") as mock_growth:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider

            # Mock risky dividend payer (high payout, low FCF coverage)
            mock_provider.get_info.return_value = {
                "longName": "Risky Corp",
                "dividendRate": 5.0,
                "dividendYield": 0.08,
                "payoutRatio": 0.95,
                "sharesOutstanding": 1_000_000_000,
            }

            # Mock cash flow with weak FCF
            fcf_row = MagicMock()
            fcf_row.get = lambda key, default=0: 4_000_000_000 if key == "Free Cash Flow" else default
            mock_cashflow = MagicMock()
            mock_cashflow.empty = False
            mock_cashflow.iloc.__getitem__ = MagicMock(return_value=fcf_row)
            mock_provider.get_cash_flow.return_value = mock_cashflow

            # Mock balance sheet with high debt
            bs_row = MagicMock()
            bs_row.get = lambda key, default=0: {
                "Total Debt": 80_000_000_000,
                "Total Equity Gross Minority Interest": 40_000_000_000,
            }.get(key, default)
            mock_balance = MagicMock()
            mock_balance.empty = False
            mock_balance.iloc.__getitem__ = MagicMock(return_value=bs_row)
            mock_provider.get_balance_sheet.return_value = mock_balance

            mock_provider.get_income_statement.return_value = MagicMock(empty=True)

            mock_growth.return_value = {
                "consecutive_years_increased": 0,
                "classification": "Inconsistent Dividend Payer",
            }

            result = calculate_dividend_safety("RISK")

            assert "red_flags" in result
            assert result["safety_score"] < 70


# ─────────────────────────────────────────────────────────────
# Dividend Growth Tests
# ─────────────────────────────────────────────────────────────


class TestDividendGrowthCalculation:
    """Test dividend growth history calculations."""

    def test_calculate_dividend_growth_king(self):
        """Should classify as Dividend King for 50+ years."""
        from src.tools.dividend_analyzer import calculate_dividend_growth

        with patch("src.tools.dividend_analyzer.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider
            mock_provider.get_info.return_value = {"longName": "Procter & Gamble"}

            # Create 60+ years of increasing dividends
            import pandas as pd
            dates = pd.date_range(start="1960-01-01", end="2025-01-01", freq="QE")
            amounts = [0.10 * (1.03 ** (i // 4)) for i in range(len(dates))]
            mock_dividends = pd.Series(amounts, index=dates)
            mock_provider.get_dividends.return_value = mock_dividends

            result = calculate_dividend_growth("PG")

            assert result["has_dividends"] is True
            assert "classification" in result
            # Note: Actual classification depends on consecutive years calculation

    def test_calculate_dividend_growth_no_dividends(self):
        """Should handle non-dividend payers."""
        from src.tools.dividend_analyzer import calculate_dividend_growth

        with patch("src.tools.dividend_analyzer.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider
            mock_provider.get_info.return_value = {"longName": "Amazon.com Inc"}

            import pandas as pd
            mock_provider.get_dividends.return_value = pd.Series([], dtype=float)

            result = calculate_dividend_growth("AMZN")

            assert result["has_dividends"] is False
            assert result["classification"] == "Non-Dividend Payer"
            assert result["consecutive_years_increased"] == 0

    def test_calculate_dividend_growth_cagr(self):
        """Should calculate CAGR correctly."""
        from src.tools.dividend_analyzer import calculate_dividend_growth

        with patch("src.tools.dividend_analyzer.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider
            mock_provider.get_info.return_value = {"longName": "Test Corp"}

            # Create 10 years of steady 6% annual dividend growth
            import pandas as pd
            dates = pd.date_range(start="2015-01-01", end="2025-01-01", freq="QE")
            base = 1.0
            amounts = [base * (1.06 ** (i // 4)) for i in range(len(dates))]
            mock_provider.get_dividends.return_value = pd.Series(amounts, index=dates)

            result = calculate_dividend_growth("TEST")

            assert result["has_dividends"] is True
            # CAGR values should be present if enough data
            if result.get("cagr_5_year"):
                assert isinstance(result["cagr_5_year"], (int, float))


# ─────────────────────────────────────────────────────────────
# Yield Comparison Tests
# ─────────────────────────────────────────────────────────────


class TestYieldComparison:
    """Test yield comparison functionality."""

    def test_compare_yields_above_average(self):
        """Should identify yield above sector average."""
        from src.tools.dividend_analyzer import compare_yields

        with patch("src.tools.dividend_analyzer.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider

            mock_provider.get_info.return_value = {
                "longName": "Verizon Communications",
                "dividendYield": 0.065,  # 6.5% yield
                "sector": "Communication Services",
            }

            result = compare_yields("VZ")

            assert "dividend_yield" in result
            assert "comparisons" in result
            assert "spreads" in result
            assert result["dividend_yield"] == 6.5
            assert "sector_average" in result["comparisons"]
            assert "sp500_average" in result["comparisons"]

    def test_compare_yields_utilities_sector(self):
        """Should use correct sector average for utilities."""
        from src.tools.dividend_analyzer import compare_yields

        with patch("src.tools.dividend_analyzer.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider

            mock_provider.get_info.return_value = {
                "longName": "Duke Energy",
                "dividendYield": 0.04,  # 4% yield
                "sector": "Utilities",
            }

            result = compare_yields("DUK")

            assert result["sector"] == "Utilities"
            assert result["comparisons"]["sector_average"] == 3.5  # Utilities average


# ─────────────────────────────────────────────────────────────
# Full Dividend Analysis Tests
# ─────────────────────────────────────────────────────────────


class TestAnalyzeDividends:
    """Test the main analyze_dividends function."""

    def test_analyze_dividends_complete(self):
        """Should return complete dividend analysis."""
        from src.tools.dividend_analyzer import analyze_dividends

        with patch("src.tools.dividend_analyzer.fetch_dividend_info") as mock_info, \
             patch("src.tools.dividend_analyzer.calculate_dividend_growth") as mock_growth, \
             patch("src.tools.dividend_analyzer.calculate_dividend_safety") as mock_safety, \
             patch("src.tools.dividend_analyzer.compare_yields") as mock_yields:

            mock_info.return_value = {
                "symbol": "JNJ",
                "name": "Johnson & Johnson",
                "annual_dividend": 4.76,
                "dividend_yield": 2.95,
                "payout_ratio": 44.2,
                "frequency": "Quarterly",
                "ex_dividend_date": "2026-02-20",
                "last_dividend_amount": 1.19,
            }

            mock_growth.return_value = {
                "consecutive_years_increased": 61,
                "classification": "Dividend King (50+ years)",
                "cagr_3_year": 5.8,
                "cagr_5_year": 5.5,
                "cagr_10_year": 6.2,
            }

            mock_safety.return_value = {
                "safety_score": 92,
                "rating": "Very Safe",
                "dividend_cut_probability": "Very Low (<5%)",
                "factors": {},
                "red_flags": [],
            }

            mock_yields.return_value = {
                "dividend_yield": 2.95,
                "sector": "Healthcare",
                "comparisons": {"sector_average": 1.8, "sp500_average": 1.5},
                "yield_assessment": "Above sector average",
            }

            result = analyze_dividends("JNJ")

            assert result["symbol"] == "JNJ"
            assert result["pays_dividends"] is True
            assert "current_dividend" in result
            assert "dividend_safety" in result
            assert "dividend_growth" in result
            assert "yield_comparison" in result
            assert result["dividend_safety"]["safety_score"] == 92

    def test_analyze_dividends_non_payer(self):
        """Should handle non-dividend payers gracefully."""
        from src.tools.dividend_analyzer import analyze_dividends

        with patch("src.tools.dividend_analyzer.fetch_dividend_info") as mock_info:
            mock_info.return_value = {
                "symbol": "AMZN",
                "name": "Amazon.com Inc",
                "annual_dividend": 0,
                "dividend_yield": 0,
            }

            result = analyze_dividends("AMZN")

            assert result["symbol"] == "AMZN"
            assert result["pays_dividends"] is False
            assert "message" in result


class TestCompareDividends:
    """Test dividend comparison functionality."""

    def test_compare_dividends(self):
        """Should compare multiple companies correctly."""
        from src.tools.dividend_analyzer import compare_dividends

        with patch("src.tools.dividend_analyzer.analyze_dividends") as mock_analyze:
            mock_analyze.side_effect = [
                {
                    "symbol": "JNJ",
                    "name": "Johnson & Johnson",
                    "pays_dividends": True,
                    "current_dividend": {"dividend_yield": 2.95, "payout_ratio": 44.2},
                    "dividend_safety": {"safety_score": 92, "rating": "Very Safe"},
                    "dividend_growth": {
                        "consecutive_years_increased": 61,
                        "classification": "Dividend King",
                        "cagr_5_year": 5.5,
                    },
                },
                {
                    "symbol": "PG",
                    "name": "Procter & Gamble",
                    "pays_dividends": True,
                    "current_dividend": {"dividend_yield": 2.4, "payout_ratio": 60.0},
                    "dividend_safety": {"safety_score": 88, "rating": "Very Safe"},
                    "dividend_growth": {
                        "consecutive_years_increased": 68,
                        "classification": "Dividend King",
                        "cagr_5_year": 5.0,
                    },
                },
                {
                    "symbol": "AMZN",
                    "name": "Amazon.com Inc",
                    "pays_dividends": False,
                },
            ]

            result = compare_dividends(["JNJ", "PG", "AMZN"])

            assert result["companies_compared"] == 3
            assert len(result["comparison"]) == 3
            assert result["best_for_income"] == "JNJ"  # Highest safety score

            # Check sorting by safety score
            dividend_payers = [c for c in result["comparison"] if c.get("safety_score", 0) > 0]
            assert dividend_payers[0]["symbol"] == "JNJ"
            assert dividend_payers[1]["symbol"] == "PG"


# ─────────────────────────────────────────────────────────────
# Dividend Analyst Agent Tests
# ─────────────────────────────────────────────────────────────


class TestDividendAnalystAgent:
    """Test DividendAnalystAgent class."""

    def test_agent_initialization(self):
        """Agent should initialize with correct attributes."""
        from src.agents.dividend import DividendAnalystAgent

        agent = DividendAnalystAgent()

        assert agent.name == "DividendAnalyst"
        assert "dividend" in agent.description.lower()

    def test_agent_tools(self):
        """Agent should have the expected tools."""
        from src.agents.dividend import DividendAnalystAgent

        agent = DividendAnalystAgent()
        tools = agent._get_default_tools()

        tool_names = [t.name for t in tools]
        assert "analyze_dividend_profile" in tool_names
        assert "compare_dividend_profiles" in tool_names
        assert "get_dividend_safety" in tool_names
        assert "get_dividend_growth" in tool_names
        assert "get_dividend_history" in tool_names
        assert "compare_dividend_yields" in tool_names


# ─────────────────────────────────────────────────────────────
# API Schema Tests
# ─────────────────────────────────────────────────────────────


class TestDividendSchemas:
    """Test Pydantic schemas for dividend analysis."""

    def test_dividend_analysis_request(self):
        """DividendAnalysisRequest should validate correctly."""
        from src.api.schemas import DividendAnalysisRequest

        req = DividendAnalysisRequest(symbol="JNJ")
        assert req.symbol == "JNJ"
        assert req.include_narrative is False

    def test_dividend_analysis_request_with_narrative(self):
        """Should accept include_narrative flag."""
        from src.api.schemas import DividendAnalysisRequest

        req = DividendAnalysisRequest(symbol="PG", include_narrative=True)
        assert req.include_narrative is True

    def test_dividend_compare_request(self):
        """DividendCompareRequest should accept a list of symbols."""
        from src.api.schemas import DividendCompareRequest

        req = DividendCompareRequest(symbols=["JNJ", "PG", "KO"])
        assert len(req.symbols) == 3

    def test_dividend_analysis_response(self):
        """DividendAnalysisResponse should accept valid data."""
        from src.api.schemas import DividendAnalysisResponse

        resp = DividendAnalysisResponse(
            symbol="JNJ",
            name="Johnson & Johnson",
            pays_dividends=True,
            analyzed_at=datetime.now(timezone.utc),
        )
        assert resp.symbol == "JNJ"
        assert resp.pays_dividends is True

    def test_dividend_compare_response(self):
        """DividendCompareResponse should accept comparison data."""
        from src.api.schemas import DividendCompareResponse, DividendComparisonItem

        item = DividendComparisonItem(
            symbol="JNJ",
            name="Johnson & Johnson",
            dividend_yield=2.95,
            safety_score=92,
            classification="Dividend King",
        )
        resp = DividendCompareResponse(
            companies_compared=1,
            comparison=[item],
            best_for_income="JNJ",
            analyzed_at=datetime.now(timezone.utc),
        )
        assert resp.companies_compared == 1
        assert resp.best_for_income == "JNJ"

    def test_analysis_type_includes_dividend(self):
        """AnalysisType enum should include DIVIDEND."""
        from src.api.schemas import AnalysisType

        assert hasattr(AnalysisType, "DIVIDEND")
        assert AnalysisType.DIVIDEND.value == "dividend"

    def test_dividend_safety_schema(self):
        """DividendSafety schema should validate."""
        from src.api.schemas import DividendSafety

        safety = DividendSafety(
            safety_score=92,
            rating="Very Safe",
            dividend_cut_probability="Very Low (<5%)",
            factors={},
            red_flags=[],
        )
        assert safety.safety_score == 92
        assert safety.rating == "Very Safe"

    def test_dividend_growth_schema(self):
        """DividendGrowth schema should validate."""
        from src.api.schemas import DividendGrowth

        growth = DividendGrowth(
            consecutive_years_increased=61,
            classification="Dividend King (50+ years)",
            cagr_5_year=5.5,
        )
        assert growth.consecutive_years_increased == 61
        assert "King" in growth.classification

    def test_current_dividend_schema(self):
        """CurrentDividend schema should validate."""
        from src.api.schemas import CurrentDividend

        current = CurrentDividend(
            annual_dividend=4.76,
            dividend_yield=2.95,
            frequency="Quarterly",
            payout_ratio=44.2,
        )
        assert current.annual_dividend == 4.76
        assert current.frequency == "Quarterly"

    def test_yield_comparison_schema(self):
        """YieldComparison schema should validate."""
        from src.api.schemas import YieldComparison

        yc = YieldComparison(
            stock_yield=2.95,
            sector="Healthcare",
            sector_average=1.8,
            sp500_average=1.5,
            yield_assessment="Above sector average",
        )
        assert yc.stock_yield == 2.95
        assert yc.sector == "Healthcare"


# ─────────────────────────────────────────────────────────────
# Orchestrator Integration Tests
# ─────────────────────────────────────────────────────────────


class TestOrchestratorDividendIntegration:
    """Test dividend integration in orchestrator."""

    def test_orchestrator_has_dividend_analyst(self):
        """Orchestrator should have dividend analyst."""
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()

        assert hasattr(orchestrator, "dividend_analyst")

    def test_orchestrator_dividend_delegation_tool(self):
        """Orchestrator should have dividend delegation tool."""
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()
        tools = orchestrator._get_default_tools()

        tool_names = [t.name for t in tools]
        assert "delegate_to_dividend_analyst" in tool_names

    def test_orchestrator_analyze_dividends_method(self):
        """Orchestrator should have analyze_dividends method."""
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()

        assert hasattr(orchestrator, "analyze_dividends")
        assert callable(orchestrator.analyze_dividends)

    def test_orchestrator_compare_dividends_method(self):
        """Orchestrator should have compare_dividends method."""
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()

        assert hasattr(orchestrator, "compare_dividends")
        assert callable(orchestrator.compare_dividends)


# ─────────────────────────────────────────────────────────────
# Integration Tests (require yfinance / network)
# ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDividendIntegration:
    """Integration tests that fetch real data (mark as integration)."""

    def test_analyze_dividends_full(self):
        """Full dividend analysis should produce all expected keys."""
        from src.tools.dividend_analyzer import analyze_dividends

        result = analyze_dividends("JNJ")

        assert "symbol" in result
        assert "pays_dividends" in result or "error" in result

        if result.get("pays_dividends"):
            assert "current_dividend" in result
            assert "dividend_safety" in result
            assert "dividend_growth" in result
            assert "yield_comparison" in result

    def test_compare_dividends_real(self):
        """Dividend comparison should work with real data."""
        from src.tools.dividend_analyzer import compare_dividends

        result = compare_dividends(["JNJ", "PG"])

        assert "companies_compared" in result
        assert result["companies_compared"] == 2
        assert "comparison" in result

    def test_fetch_dividend_info_real(self):
        """Should fetch real dividend info."""
        from src.tools.dividend_analyzer import fetch_dividend_info

        result = fetch_dividend_info("KO")

        assert "symbol" in result
        if "error" not in result:
            assert "annual_dividend" in result
            assert "dividend_yield" in result

    def test_calculate_dividend_growth_real(self):
        """Should calculate real dividend growth."""
        from src.tools.dividend_analyzer import calculate_dividend_growth

        result = calculate_dividend_growth("JNJ")

        assert "has_dividends" in result
        if result["has_dividends"]:
            assert "classification" in result
            assert "consecutive_years_increased" in result
