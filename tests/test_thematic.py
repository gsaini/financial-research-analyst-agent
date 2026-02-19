"""
Tests for Feature 1: Thematic Investing Analysis.

Tests cover:
- Theme configuration loading
- Theme discovery and lookup
- Performance calculations
- Correlation and risk metrics
- Momentum scoring
- Health score computation
- API endpoint integration
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import numpy as np

# ─────────────────────────────────────────────────────────────
# Theme Mapper Tool Tests
# ─────────────────────────────────────────────────────────────


class TestThemeConfig:
    """Test theme configuration loading."""

    def test_load_themes_config(self):
        """Themes config should load successfully from YAML."""
        from src.tools.theme_mapper import _load_themes_config, reload_themes_config

        reload_themes_config()  # Force fresh load
        config = _load_themes_config()

        assert "themes" in config
        assert "benchmarks" in config
        assert "performance_periods" in config
        assert len(config["themes"]) >= 10  # We defined 10 themes

    def test_list_available_themes(self):
        """Should return a list of theme summaries."""
        from src.tools.theme_mapper import list_available_themes

        themes = list_available_themes()

        assert isinstance(themes, list)
        assert len(themes) >= 10

        # Check structure of each theme
        for theme in themes:
            assert "theme_id" in theme
            assert "name" in theme
            assert "description" in theme
            assert "constituent_count" in theme
            assert "constituents" in theme
            assert "risk_level" in theme
            assert "growth_stage" in theme
            assert theme["constituent_count"] > 0

    def test_get_theme_definition_by_id(self):
        """Should return theme definition for a valid ID."""
        from src.tools.theme_mapper import get_theme_definition

        theme = get_theme_definition("ai_machine_learning")

        assert theme is not None
        assert theme["name"] == "AI & Machine Learning"
        assert "NVDA" in theme["constituents"]
        assert "MSFT" in theme["constituents"]
        assert len(theme["reference_etfs"]) > 0

    def test_get_theme_definition_by_name(self):
        """Should find theme by name (case-insensitive)."""
        from src.tools.theme_mapper import get_theme_definition

        theme = get_theme_definition("Cybersecurity")

        assert theme is not None
        assert "CRWD" in theme["constituents"]

    def test_get_theme_definition_not_found(self):
        """Should return None for invalid theme ID."""
        from src.tools.theme_mapper import get_theme_definition

        assert get_theme_definition("nonexistent_theme") is None

    def test_get_theme_constituents(self):
        """Should return ticker list for a theme."""
        from src.tools.theme_mapper import get_theme_constituents

        tickers = get_theme_constituents("electric_vehicles")

        assert isinstance(tickers, list)
        assert "TSLA" in tickers
        assert len(tickers) >= 5


class TestPerformanceCalculations:
    """Test performance computation functions."""

    def test_calculate_period_return(self):
        """Should compute return correctly."""
        from src.tools.theme_mapper import _calculate_period_return

        # 10% return over 5 days
        closes = [100] * 50 + [110]
        ret = _calculate_period_return(closes, 5)
        assert ret is not None
        assert ret == 10.0

    def test_calculate_period_return_insufficient_data(self):
        """Should return None when data is insufficient."""
        from src.tools.theme_mapper import _calculate_period_return

        closes = [100, 110]
        ret = _calculate_period_return(closes, 100)
        assert ret is None


class TestCorrelation:
    """Test correlation and risk calculations."""

    def test_calculate_theme_correlation(self):
        """Should compute correlation matrix for valid stock data."""
        from src.tools.theme_mapper import calculate_theme_correlation

        # Create synthetic stock data
        np.random.seed(42)
        stock_data = {
            "AAPL": {"returns": np.random.normal(0.001, 0.02, 100).tolist()},
            "MSFT": {"returns": np.random.normal(0.001, 0.02, 100).tolist()},
            "GOOGL": {"returns": np.random.normal(0.001, 0.02, 100).tolist()},
        }

        result = calculate_theme_correlation(stock_data)

        assert "intra_correlation" in result
        assert "diversification_score" in result
        assert "correlation_matrix" in result
        assert result["intra_correlation"] is not None
        assert -1 <= result["intra_correlation"] <= 1

    def test_calculate_theme_correlation_insufficient(self):
        """Should handle insufficient data gracefully."""
        from src.tools.theme_mapper import calculate_theme_correlation

        stock_data = {"AAPL": {"returns": [0.01, 0.02]}}  # Only 1 stock

        result = calculate_theme_correlation(stock_data)
        assert result["diversification_score"] == "Insufficient data"


class TestSectorOverlap:
    """Test sector overlap calculations."""

    def test_calculate_sector_overlap(self):
        """Should compute sector percentages."""
        from src.tools.theme_mapper import calculate_sector_overlap

        stock_data = {
            "AAPL": {"sector": "Technology"},
            "MSFT": {"sector": "Technology"},
            "GOOGL": {"sector": "Communication Services"},
            "AMZN": {"sector": "Consumer Discretionary"},
        }

        result = calculate_sector_overlap(stock_data)

        assert "Technology" in result
        assert result["Technology"] == "50%"


class TestMomentumScoring:
    """Test momentum score calculations."""

    def test_calculate_momentum_score(self):
        """Should return a score between 0 and 100."""
        from src.tools.theme_mapper import calculate_momentum_score

        # Create synthetic bullish stock data
        closes = list(range(100, 200))  # Steadily rising
        stock_data = {
            "AAPL": {"closes": closes},
            "MSFT": {"closes": closes},
        }

        score = calculate_momentum_score(stock_data)

        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_calculate_momentum_score_empty(self):
        """Should return 0 for empty data."""
        from src.tools.theme_mapper import calculate_momentum_score

        assert calculate_momentum_score({}) == 0


class TestHealthScore:
    """Test theme health score computation."""

    def test_calculate_theme_health_score(self):
        """Should compute health score with component breakdown."""
        from src.tools.theme_mapper import calculate_theme_health_score

        performance = {
            "theme_performance": {"1y": "+25.5%"},
        }
        correlation = {
            "intra_correlation": 0.65,
        }
        momentum = 70

        result = calculate_theme_health_score(performance, correlation, momentum)

        assert "health_score" in result
        assert "components" in result
        assert "weights" in result
        assert 0 <= result["health_score"] <= 100
        assert "performance_score" in result["components"]
        assert "momentum_score" in result["components"]


# ─────────────────────────────────────────────────────────────
# Thematic Analyst Agent Tests
# ─────────────────────────────────────────────────────────────


class TestThematicAnalystAgent:
    """Test ThematicAnalystAgent class."""

    def test_agent_initialization(self):
        """Agent should initialize with correct attributes."""
        from src.agents.thematic import ThematicAnalystAgent

        agent = ThematicAnalystAgent()

        assert agent.name == "ThematicAnalyst"
        assert "thematic" in agent.description.lower() or "theme" in agent.description.lower()

    def test_agent_tools(self):
        """Agent should have the expected tools."""
        from src.agents.thematic import ThematicAnalystAgent

        agent = ThematicAnalystAgent()
        tools = agent._get_default_tools()

        tool_names = [t.name for t in tools]
        assert "list_themes" in tool_names
        assert "get_theme_info" in tool_names
        assert "analyze_investment_theme" in tool_names
        assert "compare_themes" in tool_names


# ─────────────────────────────────────────────────────────────
# API Schema Tests
# ─────────────────────────────────────────────────────────────


class TestThemeSchemas:
    """Test Pydantic schemas for thematic analysis."""

    def test_theme_analysis_request(self):
        """ThemeAnalysisRequest should validate correctly."""
        from src.api.schemas import ThemeAnalysisRequest

        req = ThemeAnalysisRequest(theme_id="ai_machine_learning")
        assert req.theme_id == "ai_machine_learning"
        assert req.include_narrative is False

    def test_theme_compare_request(self):
        """ThemeCompareRequest should accept a list of IDs."""
        from src.api.schemas import ThemeCompareRequest

        req = ThemeCompareRequest(
            theme_ids=["ai_machine_learning", "cybersecurity"]
        )
        assert len(req.theme_ids) == 2

    def test_theme_analysis_response(self):
        """ThemeAnalysisResponse should accept valid data."""
        from src.api.schemas import ThemeAnalysisResponse

        resp = ThemeAnalysisResponse(
            theme="AI & Machine Learning",
            theme_id="ai_machine_learning",
            constituents=["NVDA", "MSFT"],
            analyzed_at=datetime.utcnow(),
        )
        assert resp.theme == "AI & Machine Learning"
        assert resp.momentum_score == 0  # default

    def test_theme_list_response(self):
        """ThemeListResponse should accept list of theme summaries."""
        from src.api.schemas import ThemeListResponse, ThemeSummary

        summary = ThemeSummary(
            theme_id="ai_machine_learning",
            name="AI & Machine Learning",
            constituent_count=10,
        )
        resp = ThemeListResponse(
            themes=[summary],
            total_themes=1,
            timestamp=datetime.utcnow(),
        )
        assert resp.total_themes == 1

    def test_analysis_type_includes_thematic(self):
        """AnalysisType enum should include THEMATIC."""
        from src.api.schemas import AnalysisType

        assert hasattr(AnalysisType, "THEMATIC")
        assert AnalysisType.THEMATIC.value == "thematic"


# ─────────────────────────────────────────────────────────────
# Integration Tests (require yfinance / network)
# ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestThematicIntegration:
    """Integration tests that fetch real data (mark as integration)."""

    def test_analyze_theme_full(self):
        """Full theme analysis should produce all expected keys."""
        from src.tools.theme_mapper import analyze_theme

        result = analyze_theme("cybersecurity")

        assert "theme" in result
        assert "constituents" in result
        assert "theme_performance" in result
        assert "momentum_score" in result
        assert "top_performers" in result
        assert "laggards" in result
        assert "sector_overlap" in result
        assert "theme_risk" in result
        assert "theme_health_score" in result
        assert "analyzed_at" in result
