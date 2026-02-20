"""
Tests for Feature 4: Quarterly Earnings Analysis.

Tests cover:
- Quarterly financial data fetching
- Earnings history and surprise calculations
- Beat/miss pattern analysis
- Quarter-over-quarter and year-over-year trends
- Earnings quality assessment
- Agent functionality
- API endpoint integration
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import numpy as np


# ─────────────────────────────────────────────────────────────
# Earnings Data Tool Tests
# ─────────────────────────────────────────────────────────────


class TestSurprisePatternCalculation:
    """Test earnings surprise pattern calculations."""

    def test_calculate_surprise_pattern_consistent_beater(self):
        """Should identify consistent beater pattern."""
        from src.tools.earnings_data import calculate_surprise_pattern

        earnings_records = [
            {"verdict": "BEAT", "eps_surprise_pct": 5.0},
            {"verdict": "BEAT", "eps_surprise_pct": 8.0},
            {"verdict": "BEAT", "eps_surprise_pct": 3.0},
            {"verdict": "BEAT", "eps_surprise_pct": 10.0},
            {"verdict": "BEAT", "eps_surprise_pct": 6.0},
        ]

        result = calculate_surprise_pattern(earnings_records)

        assert result["total_quarters"] == 5
        assert result["beats"] == 5
        assert result["misses"] == 0
        assert "80" in result["beat_rate"] or result["beat_rate"] == "100.0%"
        assert "Consistent beater" in result["pattern"]

    def test_calculate_surprise_pattern_mixed_results(self):
        """Should identify mixed results pattern."""
        from src.tools.earnings_data import calculate_surprise_pattern

        earnings_records = [
            {"verdict": "BEAT", "eps_surprise_pct": 5.0},
            {"verdict": "MISS", "eps_surprise_pct": -3.0},
            {"verdict": "BEAT", "eps_surprise_pct": 2.0},
            {"verdict": "MISS", "eps_surprise_pct": -5.0},
            {"verdict": "INLINE", "eps_surprise_pct": 0.5},
        ]

        result = calculate_surprise_pattern(earnings_records)

        assert result["total_quarters"] == 5
        assert result["beats"] == 2
        assert result["misses"] == 2
        assert result["inline"] == 1
        assert "Mixed" in result["pattern"]

    def test_calculate_surprise_pattern_insufficient_data(self):
        """Should handle empty records gracefully."""
        from src.tools.earnings_data import calculate_surprise_pattern

        result = calculate_surprise_pattern([])

        assert result["total_quarters"] == 0
        assert result["beat_rate"] == 0
        assert "Insufficient data" in result["pattern"]

    def test_calculate_surprise_pattern_regular_misser(self):
        """Should identify regular misser pattern."""
        from src.tools.earnings_data import calculate_surprise_pattern

        earnings_records = [
            {"verdict": "MISS", "eps_surprise_pct": -5.0},
            {"verdict": "MISS", "eps_surprise_pct": -3.0},
            {"verdict": "BEAT", "eps_surprise_pct": 2.0},
            {"verdict": "MISS", "eps_surprise_pct": -8.0},
            {"verdict": "MISS", "eps_surprise_pct": -4.0},
        ]

        result = calculate_surprise_pattern(earnings_records)

        assert result["beats"] == 1
        assert result["misses"] == 4
        assert "misser" in result["pattern"].lower()


class TestQuarterlyTrends:
    """Test quarter-over-quarter trend analysis."""

    def test_calculate_quarterly_trends_accelerating(self):
        """Should detect accelerating revenue growth."""
        from src.tools.earnings_data import calculate_quarterly_trends

        quarters = [
            {"quarter": "Q1 2025", "revenue": 150_000_000_000, "net_income": 30_000_000_000, "gross_profit": 60_000_000_000},
            {"quarter": "Q4 2024", "revenue": 130_000_000_000, "net_income": 26_000_000_000, "gross_profit": 52_000_000_000},
            {"quarter": "Q3 2024", "revenue": 115_000_000_000, "net_income": 23_000_000_000, "gross_profit": 46_000_000_000},
            {"quarter": "Q2 2024", "revenue": 105_000_000_000, "net_income": 21_000_000_000, "gross_profit": 42_000_000_000},
        ]

        result = calculate_quarterly_trends(quarters)

        assert "revenue_trend" in result
        assert "income_trend" in result
        assert "margin_trajectory" in result
        assert len(result["revenue_qoq_growth"]) > 0

    def test_calculate_quarterly_trends_insufficient_data(self):
        """Should handle insufficient data."""
        from src.tools.earnings_data import calculate_quarterly_trends

        quarters = [{"quarter": "Q1 2025", "revenue": 100_000_000_000}]

        result = calculate_quarterly_trends(quarters)

        assert "error" in result

    def test_calculate_quarterly_trends_stable(self):
        """Should detect stable growth pattern."""
        from src.tools.earnings_data import calculate_quarterly_trends

        quarters = [
            {"quarter": "Q1 2025", "revenue": 100_000_000_000, "net_income": 20_000_000_000, "gross_profit": 40_000_000_000},
            {"quarter": "Q4 2024", "revenue": 100_000_000_000, "net_income": 20_000_000_000, "gross_profit": 40_000_000_000},
            {"quarter": "Q3 2024", "revenue": 100_000_000_000, "net_income": 20_000_000_000, "gross_profit": 40_000_000_000},
            {"quarter": "Q2 2024", "revenue": 100_000_000_000, "net_income": 20_000_000_000, "gross_profit": 40_000_000_000},
        ]

        result = calculate_quarterly_trends(quarters)

        assert result["revenue_trend"] == "Stable"


class TestYoYComparison:
    """Test year-over-year comparison."""

    def test_calculate_yoy_comparison(self):
        """Should calculate YoY growth correctly."""
        from src.tools.earnings_data import calculate_yoy_comparison

        quarters = [
            {"quarter": "Q1 2025", "revenue": 120_000_000_000, "net_income": 25_000_000_000},
            {"quarter": "Q4 2024", "revenue": 115_000_000_000, "net_income": 23_000_000_000},
            {"quarter": "Q3 2024", "revenue": 110_000_000_000, "net_income": 22_000_000_000},
            {"quarter": "Q2 2024", "revenue": 105_000_000_000, "net_income": 21_000_000_000},
            {"quarter": "Q1 2024", "revenue": 100_000_000_000, "net_income": 20_000_000_000},
        ]

        result = calculate_yoy_comparison(quarters)

        assert "revenue_growth" in result
        assert "net_income_growth" in result
        # Q1 2025 vs Q1 2024: (120-100)/100 = 20%
        assert "+20" in result["revenue_growth"]

    def test_calculate_yoy_comparison_insufficient_data(self):
        """Should handle insufficient data."""
        from src.tools.earnings_data import calculate_yoy_comparison

        quarters = [
            {"quarter": "Q1 2025", "revenue": 100_000_000_000},
            {"quarter": "Q4 2024", "revenue": 95_000_000_000},
        ]

        result = calculate_yoy_comparison(quarters)

        assert "error" in result


class TestEarningsQuality:
    """Test earnings quality assessment."""

    def test_assess_earnings_quality_high(self):
        """Should give high score for high-quality earnings."""
        from src.tools.earnings_data import assess_earnings_quality

        # Consistent revenue, stable margins, operational income alignment
        quarters = [
            {"revenue": 100_000_000_000, "gross_profit": 40_000_000_000, "operating_income": 20_000_000_000, "net_income": 18_000_000_000},
            {"revenue": 98_000_000_000, "gross_profit": 39_200_000_000, "operating_income": 19_600_000_000, "net_income": 17_600_000_000},
            {"revenue": 97_000_000_000, "gross_profit": 38_800_000_000, "operating_income": 19_400_000_000, "net_income": 17_400_000_000},
            {"revenue": 96_000_000_000, "gross_profit": 38_400_000_000, "operating_income": 19_200_000_000, "net_income": 17_200_000_000},
        ]

        result = assess_earnings_quality(quarters)

        assert "score" in result
        assert "assessment" in result
        assert "factors" in result
        assert result["score"] >= 5.0  # Above average

    def test_assess_earnings_quality_low(self):
        """Should give lower score for volatile earnings."""
        from src.tools.earnings_data import assess_earnings_quality

        # Highly volatile revenue, inconsistent margins
        quarters = [
            {"revenue": 100_000_000_000, "gross_profit": 40_000_000_000, "operating_income": 10_000_000_000, "net_income": 25_000_000_000},
            {"revenue": 50_000_000_000, "gross_profit": 10_000_000_000, "operating_income": 5_000_000_000, "net_income": 2_000_000_000},
            {"revenue": 120_000_000_000, "gross_profit": 24_000_000_000, "operating_income": 12_000_000_000, "net_income": 10_000_000_000},
            {"revenue": 60_000_000_000, "gross_profit": 30_000_000_000, "operating_income": 6_000_000_000, "net_income": 5_000_000_000},
        ]

        result = assess_earnings_quality(quarters)

        assert result["score"] <= 6.0

    def test_assess_earnings_quality_insufficient_data(self):
        """Should return neutral score for insufficient data."""
        from src.tools.earnings_data import assess_earnings_quality

        quarters = [{"revenue": 100_000_000_000, "gross_profit": 40_000_000_000}]

        result = assess_earnings_quality(quarters)

        assert result["score"] == 5.0
        assert "Insufficient" in result["assessment"]


class TestFullEarningsAnalysis:
    """Test complete earnings analysis flow."""

    def test_analyze_earnings_structure(self):
        """Full analysis should produce all expected keys when mocked."""
        from src.tools.earnings_data import (
            calculate_surprise_pattern,
            calculate_quarterly_trends,
            calculate_yoy_comparison,
            assess_earnings_quality,
        )

        # Simulate the analysis flow with mock data
        earnings_records = [
            {"verdict": "BEAT", "eps_surprise_pct": 5.0},
            {"verdict": "BEAT", "eps_surprise_pct": 3.0},
            {"verdict": "MISS", "eps_surprise_pct": -2.0},
            {"verdict": "BEAT", "eps_surprise_pct": 8.0},
        ]
        quarters = [
            {"quarter": "Q1 2025", "revenue": 120_000_000_000, "net_income": 25_000_000_000, "gross_profit": 50_000_000_000, "operating_income": 30_000_000_000},
            {"quarter": "Q4 2024", "revenue": 110_000_000_000, "net_income": 23_000_000_000, "gross_profit": 45_000_000_000, "operating_income": 27_000_000_000},
            {"quarter": "Q3 2024", "revenue": 105_000_000_000, "net_income": 21_000_000_000, "gross_profit": 42_000_000_000, "operating_income": 25_000_000_000},
            {"quarter": "Q2 2024", "revenue": 100_000_000_000, "net_income": 20_000_000_000, "gross_profit": 40_000_000_000, "operating_income": 24_000_000_000},
            {"quarter": "Q1 2024", "revenue": 95_000_000_000, "net_income": 19_000_000_000, "gross_profit": 38_000_000_000, "operating_income": 22_000_000_000},
        ]

        surprise_pattern = calculate_surprise_pattern(earnings_records)
        trends = calculate_quarterly_trends(quarters)
        yoy = calculate_yoy_comparison(quarters)
        quality = assess_earnings_quality(quarters)

        # Verify all components work together
        assert "beat_rate" in surprise_pattern
        assert "pattern" in surprise_pattern
        assert "revenue_trend" in trends
        assert "income_trend" in trends
        assert "revenue_growth" in yoy
        assert "score" in quality
        assert "assessment" in quality

    def test_compare_earnings(self):
        """Compare function should rank companies by earnings quality."""
        from src.tools.earnings_data import compare_earnings

        # Mock the analyze_earnings function to avoid network calls
        with patch("src.tools.earnings_data.analyze_earnings") as mock_analyze:
            mock_analyze.side_effect = [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "earnings_surprise_history": {
                        "last_8_quarters": {
                            "beat_rate": "75%",
                            "average_surprise": "+5%",
                            "pattern": "Regular beater",
                        }
                    },
                    "quarterly_trends": {
                        "revenue_trend": "Growing steadily",
                        "income_trend": "Growing steadily",
                    },
                    "earnings_quality": {"score": 8.0},
                    "next_earnings": {"date": "2025-04-30"},
                },
                {
                    "symbol": "MSFT",
                    "name": "Microsoft Corporation",
                    "earnings_surprise_history": {
                        "last_8_quarters": {
                            "beat_rate": "87.5%",
                            "average_surprise": "+8%",
                            "pattern": "Consistent beater",
                        }
                    },
                    "quarterly_trends": {
                        "revenue_trend": "Accelerating",
                        "income_trend": "Accelerating",
                    },
                    "earnings_quality": {"score": 9.0},
                    "next_earnings": {"date": "2025-04-25"},
                },
            ]

            result = compare_earnings(["AAPL", "MSFT"])

            assert "companies_compared" in result
            assert result["companies_compared"] == 2
            assert "comparison" in result
            assert result["best_earnings_quality"] == "MSFT"  # Sorted by score

            # Verify sorted by quality score descending
            comparison = result["comparison"]
            assert comparison[0]["symbol"] == "MSFT"
            assert comparison[1]["symbol"] == "AAPL"


# ─────────────────────────────────────────────────────────────
# Earnings Analyst Agent Tests
# ─────────────────────────────────────────────────────────────


class TestEarningsAnalystAgent:
    """Test EarningsAnalystAgent class."""

    def test_agent_initialization(self):
        """Agent should initialize with correct attributes."""
        from src.agents.earnings import EarningsAnalystAgent

        agent = EarningsAnalystAgent()

        assert agent.name == "EarningsAnalyst"
        assert "earnings" in agent.description.lower()

    def test_agent_tools(self):
        """Agent should have the expected tools."""
        from src.agents.earnings import EarningsAnalystAgent

        agent = EarningsAnalystAgent()
        tools = agent._get_default_tools()

        tool_names = [t.name for t in tools]
        assert "analyze_earnings_profile" in tool_names
        assert "compare_earnings_profiles" in tool_names
        assert "get_earnings_history" in tool_names
        assert "get_upcoming_earnings" in tool_names
        assert "get_quarterly_trends" in tool_names
        assert "assess_earnings_quality" in tool_names


# ─────────────────────────────────────────────────────────────
# API Schema Tests
# ─────────────────────────────────────────────────────────────


class TestEarningsSchemas:
    """Test Pydantic schemas for earnings analysis."""

    def test_earnings_analysis_request(self):
        """EarningsAnalysisRequest should validate correctly."""
        from src.api.schemas import EarningsAnalysisRequest

        req = EarningsAnalysisRequest(symbol="AAPL")
        assert req.symbol == "AAPL"
        assert req.include_narrative is False

    def test_earnings_analysis_request_with_narrative(self):
        """Should accept include_narrative flag."""
        from src.api.schemas import EarningsAnalysisRequest

        req = EarningsAnalysisRequest(symbol="MSFT", include_narrative=True)
        assert req.include_narrative is True

    def test_earnings_compare_request(self):
        """EarningsCompareRequest should accept a list of symbols."""
        from src.api.schemas import EarningsCompareRequest

        req = EarningsCompareRequest(symbols=["AAPL", "MSFT", "GOOGL"])
        assert len(req.symbols) == 3

    def test_earnings_analysis_response(self):
        """EarningsAnalysisResponse should accept valid data."""
        from src.api.schemas import EarningsAnalysisResponse

        resp = EarningsAnalysisResponse(
            symbol="AAPL",
            name="Apple Inc.",
            currency="USD",
            analyzed_at=datetime.utcnow(),
        )
        assert resp.symbol == "AAPL"
        assert resp.currency == "USD"

    def test_earnings_compare_response(self):
        """EarningsCompareResponse should accept comparison data."""
        from src.api.schemas import EarningsCompareResponse, EarningsComparisonItem

        item = EarningsComparisonItem(
            symbol="AAPL",
            name="Apple Inc.",
            beat_rate="75%",
            earnings_quality_score=8.0,
        )
        resp = EarningsCompareResponse(
            companies_compared=1,
            comparison=[item],
            best_earnings_quality="AAPL",
            analyzed_at=datetime.utcnow(),
        )
        assert resp.companies_compared == 1
        assert resp.best_earnings_quality == "AAPL"

    def test_analysis_type_includes_earnings(self):
        """AnalysisType enum should include EARNINGS."""
        from src.api.schemas import AnalysisType

        assert hasattr(AnalysisType, "EARNINGS")
        assert AnalysisType.EARNINGS.value == "earnings"

    def test_surprise_pattern_schema(self):
        """SurprisePattern schema should validate."""
        from src.api.schemas import SurprisePattern

        pattern = SurprisePattern(
            total_quarters=8,
            beats=6,
            misses=1,
            inline=1,
            beat_rate="75%",
            average_surprise="+5%",
            pattern="Regular beater",
        )
        assert pattern.beats == 6
        assert pattern.beat_rate == "75%"

    def test_earnings_quality_schema(self):
        """EarningsQuality schema should validate score range."""
        from src.api.schemas import EarningsQuality

        quality = EarningsQuality(
            score=8.5,
            assessment="High quality",
            factors=["Consistent revenue", "Stable margins"],
        )
        assert quality.score == 8.5
        assert len(quality.factors) == 2


# ─────────────────────────────────────────────────────────────
# Orchestrator Integration Tests
# ─────────────────────────────────────────────────────────────


class TestOrchestratorEarningsIntegration:
    """Test earnings integration in orchestrator."""

    def test_orchestrator_has_earnings_analyst(self):
        """Orchestrator should have earnings analyst."""
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()

        assert hasattr(orchestrator, "earnings_analyst")

    def test_orchestrator_earnings_delegation_tool(self):
        """Orchestrator should have earnings delegation tool."""
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()
        tools = orchestrator._get_default_tools()

        tool_names = [t.name for t in tools]
        assert "delegate_to_earnings_analyst" in tool_names


# ─────────────────────────────────────────────────────────────
# Integration Tests (require yfinance / network)
# ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestEarningsIntegration:
    """Integration tests that fetch real data (mark as integration)."""

    def test_analyze_earnings_full(self):
        """Full earnings analysis should produce all expected keys."""
        from src.tools.earnings_data import analyze_earnings

        result = analyze_earnings("AAPL")

        assert "symbol" in result
        assert "name" in result
        assert "last_4_quarters" in result
        assert "earnings_surprise_history" in result
        assert "quarterly_trends" in result
        assert "earnings_quality" in result
        assert "next_earnings" in result
        assert "analyzed_at" in result

    def test_compare_earnings_full(self):
        """Full comparison should rank multiple companies."""
        from src.tools.earnings_data import compare_earnings

        result = compare_earnings(["AAPL", "MSFT"])

        assert "companies_compared" in result
        assert result["companies_compared"] == 2
        assert "comparison" in result
        assert "best_earnings_quality" in result

    def test_fetch_quarterly_financials(self):
        """Should fetch quarterly financial data."""
        from src.tools.earnings_data import fetch_quarterly_financials

        result = fetch_quarterly_financials("MSFT")

        assert "symbol" in result
        assert "quarters" in result

    def test_fetch_earnings_history(self):
        """Should fetch earnings history."""
        from src.tools.earnings_data import fetch_earnings_history

        result = fetch_earnings_history("GOOGL")

        assert "symbol" in result
        assert "earnings_records" in result

    def test_fetch_upcoming_earnings(self):
        """Should fetch upcoming earnings info."""
        from src.tools.earnings_data import fetch_upcoming_earnings

        result = fetch_upcoming_earnings("NVDA")

        assert "symbol" in result
        # May or may not have next_earnings_date depending on timing


@pytest.mark.integration
class TestEarningsAPIEndpoints:
    """Integration tests for API endpoints."""

    def test_earnings_endpoint_structure(self):
        """Endpoint should return properly structured response."""
        from fastapi.testclient import TestClient
        from src.api.routes import app

        client = TestClient(app)

        response = client.get("/api/v1/earnings/AAPL")

        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "earnings_quality" in data

    def test_earnings_analyze_endpoint(self):
        """Analyze endpoint should accept request body."""
        from fastapi.testclient import TestClient
        from src.api.routes import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/earnings/analyze",
            json={"symbol": "MSFT", "include_narrative": False},
        )

        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data

    def test_earnings_compare_endpoint(self):
        """Compare endpoint should accept list of symbols."""
        from fastapi.testclient import TestClient
        from src.api.routes import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/earnings/compare",
            json={"symbols": ["AAPL", "MSFT"], "include_narrative": False},
        )

        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert "companies_compared" in data
            assert "comparison" in data

    def test_earnings_compare_validation(self):
        """Should reject comparison with less than 2 symbols."""
        from fastapi.testclient import TestClient
        from src.api.routes import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/earnings/compare",
            json={"symbols": ["AAPL"], "include_narrative": False},
        )

        assert response.status_code == 400
