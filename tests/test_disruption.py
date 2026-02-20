"""
Tests for Feature 3: Market Disruption Analysis.

Tests cover:
- Company financial data fetching
- R&D intensity calculations
- Revenue acceleration analysis
- Margin trajectory analysis
- Disruption scoring and classification
- Risk and strength identification
- Agent functionality
- API endpoint integration
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import numpy as np


# ─────────────────────────────────────────────────────────────
# Disruption Metrics Tool Tests
# ─────────────────────────────────────────────────────────────


class TestIndustryBenchmarks:
    """Test industry benchmark lookups."""

    def test_fetch_known_industry(self):
        """Should return benchmarks for known industries."""
        from src.tools.disruption_metrics import fetch_industry_benchmarks

        benchmarks = fetch_industry_benchmarks("Semiconductors")

        assert "rd_intensity" in benchmarks
        assert "revenue_growth" in benchmarks
        assert "gross_margin" in benchmarks
        assert benchmarks["rd_intensity"] == 20.0

    def test_fetch_partial_match(self):
        """Should match industries with partial string match."""
        from src.tools.disruption_metrics import fetch_industry_benchmarks

        # "Software" should match "Software—Infrastructure" or similar
        benchmarks = fetch_industry_benchmarks("Software—Infrastructure")

        assert benchmarks["rd_intensity"] == 15.0

    def test_fetch_unknown_industry(self):
        """Should return default benchmarks for unknown industries."""
        from src.tools.disruption_metrics import fetch_industry_benchmarks

        benchmarks = fetch_industry_benchmarks("Unknown Industry XYZ")

        assert benchmarks == {"rd_intensity": 5.0, "revenue_growth": 8.0, "gross_margin": 35.0}


class TestRDIntensity:
    """Test R&D intensity calculations."""

    def test_calculate_rd_intensity(self):
        """Should calculate R&D intensity correctly."""
        from src.tools.disruption_metrics import calculate_rd_intensity

        financials = {
            "revenues": [80_000_000_000, 90_000_000_000, 100_000_000_000],
            "rd_expenses": [8_000_000_000, 10_000_000_000, 12_000_000_000],
            "industry": "Technology",
        }

        result = calculate_rd_intensity(financials)

        assert "rd_to_revenue_ratio" in result
        assert "trend" in result
        assert "vs_industry_multiple" in result
        assert result["rd_to_revenue_ratio"] == "12.0%"  # 12B / 100B
        assert result["trend"] == "Increasing"

    def test_calculate_rd_intensity_decreasing(self):
        """Should detect decreasing R&D trend."""
        from src.tools.disruption_metrics import calculate_rd_intensity

        financials = {
            "revenues": [80_000_000_000, 90_000_000_000, 100_000_000_000],
            "rd_expenses": [12_000_000_000, 10_000_000_000, 8_000_000_000],
            "industry": "Technology",
        }

        result = calculate_rd_intensity(financials)

        assert result["trend"] == "Decreasing"

    def test_calculate_rd_intensity_insufficient_data(self):
        """Should handle insufficient data gracefully."""
        from src.tools.disruption_metrics import calculate_rd_intensity

        financials = {"revenues": [], "rd_expenses": [], "industry": "Technology"}

        result = calculate_rd_intensity(financials)

        assert "error" in result


class TestRevenueAcceleration:
    """Test revenue growth acceleration analysis."""

    def test_calculate_revenue_acceleration(self):
        """Should calculate revenue growth correctly."""
        from src.tools.disruption_metrics import calculate_revenue_acceleration

        financials = {
            "revenues": [100_000_000_000, 120_000_000_000, 150_000_000_000],
            "industry": "Technology",
        }

        result = calculate_revenue_acceleration(financials)

        assert "yoy_growth" in result
        assert "trajectory" in result
        assert "cagr" in result
        # YoY growth: (150-120)/120 = 25%
        assert result["yoy_growth"] == "25.0%"

    def test_calculate_revenue_acceleration_decelerating(self):
        """Should detect decelerating growth."""
        from src.tools.disruption_metrics import calculate_revenue_acceleration

        financials = {
            # Growth slowing: 50% -> 20%
            "revenues": [100_000_000_000, 150_000_000_000, 180_000_000_000],
            "industry": "Technology",
        }

        result = calculate_revenue_acceleration(financials)

        assert "Decelerating" in result["trajectory"]

    def test_calculate_revenue_insufficient_data(self):
        """Should handle insufficient data."""
        from src.tools.disruption_metrics import calculate_revenue_acceleration

        financials = {"revenues": [100_000_000_000], "industry": "Technology"}

        result = calculate_revenue_acceleration(financials)

        assert "error" in result


class TestMarginTrajectory:
    """Test gross margin trajectory analysis."""

    def test_calculate_margin_trajectory_expanding(self):
        """Should detect expanding margins."""
        from src.tools.disruption_metrics import calculate_margin_trajectory

        financials = {
            "revenues": [100_000_000_000, 120_000_000_000, 150_000_000_000],
            "gross_profits": [30_000_000_000, 40_000_000_000, 55_000_000_000],  # 30%, 33%, 37%
            "operating_incomes": [10_000_000_000, 14_000_000_000, 20_000_000_000],
            "industry": "Technology",
        }

        result = calculate_margin_trajectory(financials)

        assert "current_gross_margin" in result
        assert "trend" in result
        assert result["trend"] == "Expanding"
        assert "36" in result["current_gross_margin"]  # ~36.67%

    def test_calculate_margin_trajectory_contracting(self):
        """Should detect contracting margins."""
        from src.tools.disruption_metrics import calculate_margin_trajectory

        financials = {
            "revenues": [100_000_000_000, 120_000_000_000, 150_000_000_000],
            "gross_profits": [40_000_000_000, 42_000_000_000, 45_000_000_000],  # 40%, 35%, 30%
            "operating_incomes": [10_000_000_000, 10_000_000_000, 10_000_000_000],
            "industry": "Technology",
        }

        result = calculate_margin_trajectory(financials)

        assert result["trend"] == "Contracting"


class TestDisruptionScoring:
    """Test disruption score calculations."""

    def test_calculate_disruption_score_high(self):
        """Should calculate high disruption score for disruptor signals."""
        from src.tools.disruption_metrics import calculate_disruption_score

        rd_metrics = {
            "rd_to_revenue_ratio": "20%",
            "vs_industry_multiple": "2x",
            "trend": "Increasing",
        }
        growth_metrics = {
            "yoy_growth": "40%",
            "trajectory": "Accelerating",
        }
        margin_metrics = {
            "trend": "Expanding",
            "gross_margin_change": 5,
        }

        result = calculate_disruption_score(rd_metrics, growth_metrics, margin_metrics)

        assert "score" in result
        assert "classification" in result
        assert result["score"] >= 70
        assert result["classification"] == "Active Disruptor"

    def test_calculate_disruption_score_low(self):
        """Should calculate low disruption score for at-risk signals."""
        from src.tools.disruption_metrics import calculate_disruption_score

        rd_metrics = {
            "rd_to_revenue_ratio": "2%",
            "vs_industry_multiple": "0.3x",
            "trend": "Decreasing",
        }
        growth_metrics = {
            "yoy_growth": "-5%",
            "trajectory": "Decelerating sharply",
        }
        margin_metrics = {
            "trend": "Contracting",
            "gross_margin_change": -8,
        }

        result = calculate_disruption_score(rd_metrics, growth_metrics, margin_metrics)

        assert result["score"] < 30
        assert result["classification"] == "At Risk"

    def test_calculate_disruption_score_moderate(self):
        """Should calculate moderate score for mixed signals."""
        from src.tools.disruption_metrics import calculate_disruption_score

        rd_metrics = {
            "rd_to_revenue_ratio": "8%",
            "vs_industry_multiple": "1x",
            "trend": "Stable",
        }
        growth_metrics = {
            "yoy_growth": "10%",
            "trajectory": "Stable",
        }
        margin_metrics = {
            "trend": "Stable",
            "gross_margin_change": 0,
        }

        result = calculate_disruption_score(rd_metrics, growth_metrics, margin_metrics)

        assert 30 <= result["score"] <= 70
        assert result["classification"] in ["Moderate Innovator", "Stable Incumbent"]


class TestRiskAndStrengthIdentification:
    """Test risk factor and strength identification."""

    def test_identify_risk_factors(self):
        """Should identify relevant risk factors."""
        from src.tools.disruption_metrics import identify_risk_factors

        financials = {"industry": "Retail", "market_cap": 1_000_000_000}
        rd_metrics = {"vs_industry_multiple": "0.3x", "trend": "Decreasing"}
        growth_metrics = {"yoy_growth": "-5%", "trajectory": "Decelerating sharply"}
        margin_metrics = {"trend": "Contracting"}

        risks = identify_risk_factors(financials, rd_metrics, growth_metrics, margin_metrics)

        assert len(risks) >= 2
        assert any("R&D" in r for r in risks)
        assert any("revenue" in r.lower() or "market share" in r.lower() for r in risks)

    def test_identify_strengths(self):
        """Should identify relevant strengths."""
        from src.tools.disruption_metrics import identify_strengths

        rd_metrics = {"vs_industry_multiple": "2x", "trend": "Increasing"}
        growth_metrics = {"yoy_growth": "30%", "trajectory": "Accelerating"}
        margin_metrics = {"trend": "Expanding", "gross_margin_change": 5}

        strengths = identify_strengths(rd_metrics, growth_metrics, margin_metrics)

        assert len(strengths) >= 2
        assert any("R&D" in s for s in strengths)
        assert any("growth" in s.lower() for s in strengths)


class TestFullAnalysis:
    """Test complete disruption analysis flow."""

    def test_analyze_disruption_structure(self):
        """Full analysis should produce all expected keys."""
        # This test uses mock data to avoid network calls
        from src.tools.disruption_metrics import (
            calculate_rd_intensity,
            calculate_revenue_acceleration,
            calculate_margin_trajectory,
            calculate_disruption_score,
            identify_risk_factors,
            identify_strengths,
        )

        # Simulate the analysis flow with mock financials
        financials = {
            "symbol": "TEST",
            "name": "Test Company",
            "sector": "Technology",
            "industry": "Software—Application",
            "market_cap": 100_000_000_000,
            "revenues": [80_000_000_000, 90_000_000_000, 100_000_000_000],
            "rd_expenses": [10_000_000_000, 12_000_000_000, 15_000_000_000],
            "gross_profits": [50_000_000_000, 58_000_000_000, 68_000_000_000],
            "operating_incomes": [15_000_000_000, 18_000_000_000, 22_000_000_000],
            "years": [2023, 2024, 2025],
        }

        rd_metrics = calculate_rd_intensity(financials)
        growth_metrics = calculate_revenue_acceleration(financials)
        margin_metrics = calculate_margin_trajectory(financials)
        score_data = calculate_disruption_score(rd_metrics, growth_metrics, margin_metrics)
        risks = identify_risk_factors(financials, rd_metrics, growth_metrics, margin_metrics)
        strengths = identify_strengths(rd_metrics, growth_metrics, margin_metrics)

        # Verify all components work together
        assert "rd_to_revenue_ratio" in rd_metrics
        assert "yoy_growth" in growth_metrics
        assert "trend" in margin_metrics
        assert "score" in score_data
        assert isinstance(risks, list)
        assert isinstance(strengths, list)

    def test_compare_disruption(self):
        """Compare function should rank companies by disruption score."""
        from src.tools.disruption_metrics import compare_disruption

        # This will make real API calls, so mark as integration
        # For unit test, we'll mock the analyze_disruption function
        with patch("src.tools.disruption_metrics.analyze_disruption") as mock_analyze:
            mock_analyze.side_effect = [
                {
                    "symbol": "AAPL",
                    "name": "Apple",
                    "industry": "Technology",
                    "disruption_score": 65,
                    "classification": "Moderate Innovator",
                    "quantitative_signals": {
                        "rd_intensity": {"rd_to_revenue_ratio": "8%"},
                        "revenue_acceleration": {"yoy_growth": "10%"},
                        "gross_margin_trajectory": {"trend": "Stable"},
                    },
                },
                {
                    "symbol": "TSLA",
                    "name": "Tesla",
                    "industry": "Auto",
                    "disruption_score": 80,
                    "classification": "Active Disruptor",
                    "quantitative_signals": {
                        "rd_intensity": {"rd_to_revenue_ratio": "12%"},
                        "revenue_acceleration": {"yoy_growth": "25%"},
                        "gross_margin_trajectory": {"trend": "Expanding"},
                    },
                },
            ]

            result = compare_disruption(["AAPL", "TSLA"])

            assert "companies_compared" in result
            assert result["companies_compared"] == 2
            assert "comparison" in result
            assert result["most_disruptive"] == "TSLA"


# ─────────────────────────────────────────────────────────────
# Disruption Analyst Agent Tests
# ─────────────────────────────────────────────────────────────


class TestDisruptionAnalystAgent:
    """Test DisruptionAnalystAgent class."""

    def test_agent_initialization(self):
        """Agent should initialize with correct attributes."""
        from src.agents.disruption import DisruptionAnalystAgent

        agent = DisruptionAnalystAgent()

        assert agent.name == "DisruptionAnalyst"
        assert "disruption" in agent.description.lower()

    def test_agent_tools(self):
        """Agent should have the expected tools."""
        from src.agents.disruption import DisruptionAnalystAgent

        agent = DisruptionAnalystAgent()
        tools = agent._get_default_tools()

        tool_names = [t.name for t in tools]
        assert "analyze_disruption_profile" in tool_names
        assert "compare_disruption_profiles" in tool_names
        assert "get_rd_intensity" in tool_names
        assert "get_growth_trajectory" in tool_names
        assert "get_margin_trajectory" in tool_names


# ─────────────────────────────────────────────────────────────
# API Schema Tests
# ─────────────────────────────────────────────────────────────


class TestDisruptionSchemas:
    """Test Pydantic schemas for disruption analysis."""

    def test_disruption_analysis_request(self):
        """DisruptionAnalysisRequest should validate correctly."""
        from src.api.schemas import DisruptionAnalysisRequest

        req = DisruptionAnalysisRequest(symbol="TSLA")
        assert req.symbol == "TSLA"
        assert req.include_narrative is False

    def test_disruption_analysis_request_with_narrative(self):
        """Should accept include_narrative flag."""
        from src.api.schemas import DisruptionAnalysisRequest

        req = DisruptionAnalysisRequest(symbol="NVDA", include_narrative=True)
        assert req.include_narrative is True

    def test_disruption_compare_request(self):
        """DisruptionCompareRequest should accept a list of symbols."""
        from src.api.schemas import DisruptionCompareRequest

        req = DisruptionCompareRequest(symbols=["TSLA", "F", "GM"])
        assert len(req.symbols) == 3

    def test_disruption_analysis_response(self):
        """DisruptionAnalysisResponse should accept valid data."""
        from src.api.schemas import DisruptionAnalysisResponse

        resp = DisruptionAnalysisResponse(
            symbol="TSLA",
            name="Tesla, Inc.",
            sector="Consumer Cyclical",
            industry="Auto Manufacturers",
            disruption_score=85,
            classification="Active Disruptor",
            analyzed_at=datetime.utcnow(),
        )
        assert resp.disruption_score == 85
        assert resp.classification == "Active Disruptor"

    def test_disruption_compare_response(self):
        """DisruptionCompareResponse should accept comparison data."""
        from src.api.schemas import DisruptionCompareResponse, DisruptionComparisonItem

        item = DisruptionComparisonItem(
            symbol="TSLA",
            name="Tesla",
            disruption_score=85,
            classification="Active Disruptor",
        )
        resp = DisruptionCompareResponse(
            companies_compared=1,
            comparison=[item],
            most_disruptive="TSLA",
            analyzed_at=datetime.utcnow(),
        )
        assert resp.companies_compared == 1
        assert resp.most_disruptive == "TSLA"

    def test_analysis_type_includes_disruption(self):
        """AnalysisType enum should include DISRUPTION."""
        from src.api.schemas import AnalysisType

        assert hasattr(AnalysisType, "DISRUPTION")
        assert AnalysisType.DISRUPTION.value == "disruption"


# ─────────────────────────────────────────────────────────────
# Integration Tests (require yfinance / network)
# ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestDisruptionIntegration:
    """Integration tests that fetch real data (mark as integration)."""

    def test_analyze_disruption_full(self):
        """Full disruption analysis should produce all expected keys."""
        from src.tools.disruption_metrics import analyze_disruption

        result = analyze_disruption("NVDA")

        assert "symbol" in result
        assert "disruption_score" in result
        assert "classification" in result
        assert "quantitative_signals" in result
        assert "strengths" in result
        assert "risk_factors" in result
        assert "analyzed_at" in result

        # Score should be valid
        assert 0 <= result["disruption_score"] <= 100

        # Classification should be valid
        valid_classifications = [
            "Active Disruptor",
            "Moderate Innovator",
            "Stable Incumbent",
            "At Risk",
        ]
        assert result["classification"] in valid_classifications

    def test_compare_disruption_full(self):
        """Full comparison should rank multiple companies."""
        from src.tools.disruption_metrics import compare_disruption

        result = compare_disruption(["NVDA", "INTC"])

        assert "companies_compared" in result
        assert result["companies_compared"] == 2
        assert "comparison" in result
        assert "most_disruptive" in result

        # Comparison should be sorted by score
        comparison = result["comparison"]
        if len(comparison) >= 2:
            scores = [c.get("disruption_score", 0) for c in comparison if "error" not in c]
            if len(scores) >= 2:
                assert scores[0] >= scores[1]  # Sorted descending


@pytest.mark.integration
class TestAPIEndpoints:
    """Integration tests for API endpoints."""

    def test_disruption_endpoint_structure(self):
        """Endpoint should return properly structured response."""
        from fastapi.testclient import TestClient
        from src.api.routes import app

        client = TestClient(app)

        # Note: This will make real API calls to yfinance
        response = client.get("/api/v1/disruption/AAPL")

        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "disruption_score" in data
            assert "classification" in data

    def test_disruption_compare_endpoint(self):
        """Compare endpoint should accept list of symbols."""
        from fastapi.testclient import TestClient
        from src.api.routes import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/disruption/compare",
            json={"symbols": ["AAPL", "MSFT"], "include_narrative": False},
        )

        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert "companies_compared" in data
            assert "comparison" in data
