"""
Tests for Feature 5: Historical Stock Performance Tracking.

Tests cover:
- Multi-horizon return calculations
- Benchmark comparison logic
- Risk-adjusted metrics (Sharpe, Sortino, Beta)
- Drawdown analysis
- Rolling return computation
- PerformanceResponse schema validation
- Risk Agent tool availability
"""

import pytest
import math
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _make_price_series(start: float, end: float, n: int = 300):
    """Generate a synthetic price Series with a realistic index."""
    dates = pd.bdate_range(end=datetime.now(), periods=n)
    prices = np.linspace(start, end, n)
    # Add slight noise so returns are non-zero
    noise = np.random.default_rng(42).normal(0, 0.5, n)
    prices = prices + noise
    prices = np.maximum(prices, 1.0)  # Prevent zero/negative prices
    return pd.Series(prices, index=dates)


# ─────────────────────────────────────────────────────────────
# Return Computation Tests
# ─────────────────────────────────────────────────────────────


class TestReturnComputation:
    """Test the internal return computation helpers."""

    def test_compute_return_positive(self):
        """Should compute positive return correctly."""
        from src.tools.performance_tracker import _compute_return

        prices = _make_price_series(100, 120, 30)
        ret = _compute_return(prices, days=20)

        assert ret is not None
        assert isinstance(ret, float)

    def test_compute_return_ytd(self):
        """Should compute YTD return."""
        from src.tools.performance_tracker import _compute_return

        prices = _make_price_series(100, 110, 60)
        ret = _compute_return(prices, ytd=True)

        # May be None if all dates are in the same year boundary
        # but should not raise
        assert ret is None or isinstance(ret, float)

    def test_compute_return_none_on_empty(self):
        """Should return None for empty input."""
        from src.tools.performance_tracker import _compute_return

        assert _compute_return(None) is None
        assert _compute_return(pd.Series(dtype=float)) is None

    def test_compute_rolling_returns(self):
        """Should compute rolling N-day returns."""
        from src.tools.performance_tracker import _compute_rolling_returns

        prices = _make_price_series(100, 120, 60)
        rolling = _compute_rolling_returns(prices, window=5)

        assert len(rolling) > 0
        assert all(isinstance(r, float) for r in rolling)

    def test_compute_rolling_returns_insufficient_data(self):
        """Should return empty list when data is shorter than window."""
        from src.tools.performance_tracker import _compute_rolling_returns

        prices = _make_price_series(100, 110, 3)
        rolling = _compute_rolling_returns(prices, window=30)

        assert rolling == []


# ─────────────────────────────────────────────────────────────
# Risk Metrics Tests
# ─────────────────────────────────────────────────────────────


class TestRiskMetrics:
    """Test risk-adjusted metric calculations."""

    def test_compute_risk_metrics_structure(self):
        """Should return Sharpe, Sortino, and volatility."""
        from src.tools.performance_tracker import _compute_risk_metrics

        prices = _make_price_series(100, 130, 300)
        metrics = _compute_risk_metrics(prices)

        assert "sharpe_ratio" in metrics
        assert "sortino_ratio" in metrics
        assert "annual_volatility" in metrics
        assert "sharpe_rating" in metrics
        assert "sortino_rating" in metrics

    def test_compute_risk_metrics_with_benchmark(self):
        """Should compute Beta when benchmark is provided."""
        from src.tools.performance_tracker import _compute_risk_metrics

        stock = _make_price_series(100, 140, 300)
        bench = _make_price_series(100, 120, 300)
        metrics = _compute_risk_metrics(stock, bench)

        assert "beta" in metrics
        assert "beta_interpretation" in metrics
        assert isinstance(metrics["beta"], float)

    def test_compute_risk_metrics_insufficient(self):
        """Should return empty dict for insufficient data."""
        from src.tools.performance_tracker import _compute_risk_metrics

        short = _make_price_series(100, 105, 5)
        metrics = _compute_risk_metrics(short)

        assert metrics == {}


# ─────────────────────────────────────────────────────────────
# Drawdown Tests
# ─────────────────────────────────────────────────────────────


class TestDrawdownAnalysis:
    """Test drawdown computation."""

    def test_compute_drawdowns_structure(self):
        """Should return max drawdown, date, and current drawdown."""
        from src.tools.performance_tracker import _compute_drawdowns

        prices = _make_price_series(100, 110, 100)
        result = _compute_drawdowns(prices)

        assert "max_drawdown" in result
        assert "max_drawdown_date" in result
        assert "current_drawdown" in result
        assert result["max_drawdown"] <= 0  # Drawdown is always negative or zero

    def test_compute_drawdowns_empty(self):
        """Should return empty dict for insufficient data."""
        from src.tools.performance_tracker import _compute_drawdowns

        assert _compute_drawdowns(None) == {}
        assert _compute_drawdowns(pd.Series([100.0])) == {}


# ─────────────────────────────────────────────────────────────
# Full track_performance() Tests (mocked)
# ─────────────────────────────────────────────────────────────


class TestTrackPerformance:
    """Test the main track_performance function with mocked yfinance."""

    @patch("src.tools.performance_tracker.yf")
    def test_track_performance_structure(self, mock_yf):
        """Should return all expected top-level keys."""
        from src.tools.performance_tracker import track_performance

        # Mock Ticker.history and Ticker.info
        stock_prices = _make_price_series(100, 150, 300)
        spy_prices = _make_price_series(100, 130, 300)

        def mock_ticker(symbol):
            m = MagicMock()
            if symbol in ("SPY", "QQQ", "XLK"):
                m.history.return_value = pd.DataFrame(
                    {"Close": spy_prices.values},
                    index=spy_prices.index,
                )
            else:
                m.history.return_value = pd.DataFrame(
                    {"Close": stock_prices.values},
                    index=stock_prices.index,
                )
                m.info = {"sector": "Technology"}
            return m

        mock_yf.Ticker.side_effect = mock_ticker

        result = track_performance("AAPL")

        assert result["symbol"] == "AAPL"
        assert "absolute_returns" in result
        assert "benchmark_comparison" in result
        assert "risk_adjusted_metrics" in result
        assert "rolling_returns" in result
        assert "drawdown_analysis" in result
        assert "return_statistics" in result
        assert "current_price" in result
        assert result["data_points"] > 0

    @patch("src.tools.performance_tracker.yf")
    def test_track_performance_no_data(self, mock_yf):
        """Should return error when no data is available."""
        from src.tools.performance_tracker import track_performance

        m = MagicMock()
        m.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = m

        result = track_performance("INVALID")

        assert "error" in result

    @patch("src.tools.performance_tracker.yf")
    def test_absolute_returns_horizons(self, mock_yf):
        """Should compute returns for multiple horizons."""
        from src.tools.performance_tracker import track_performance

        prices = _make_price_series(100, 150, 500)

        def mock_ticker(symbol):
            m = MagicMock()
            m.history.return_value = pd.DataFrame(
                {"Close": prices.values}, index=prices.index
            )
            m.info = {"sector": "Technology"}
            return m

        mock_yf.Ticker.side_effect = mock_ticker

        result = track_performance("MSFT")
        returns = result["absolute_returns"]

        # Should have at least some horizons
        assert len(returns) >= 3
        # All values should be floats
        for v in returns.values():
            assert isinstance(v, float)


# ─────────────────────────────────────────────────────────────
# Schema Tests
# ─────────────────────────────────────────────────────────────


class TestPerformanceSchema:
    """Test Pydantic schema for performance response."""

    def test_performance_response_valid(self):
        """PerformanceResponse should accept valid data."""
        from src.api.schemas import PerformanceResponse

        resp = PerformanceResponse(
            symbol="AAPL",
            sector="Technology",
            sector_etf="XLK",
            data_points=300,
            start_date="2021-01-01",
            end_date="2026-02-28",
            current_price=185.50,
            absolute_returns={"1_month": 5.2, "1_year": 22.3},
            risk_adjusted_metrics={"sharpe_ratio": 1.5, "sortino_ratio": 1.8, "beta": 1.1},
            drawdown_analysis={"max_drawdown": -12.5, "current_drawdown": -3.2},
        )

        assert resp.symbol == "AAPL"
        assert resp.current_price == 185.50
        assert resp.absolute_returns["1_year"] == 22.3
        assert resp.risk_adjusted_metrics["beta"] == 1.1

    def test_performance_response_defaults(self):
        """PerformanceResponse should have sensible defaults."""
        from src.api.schemas import PerformanceResponse

        resp = PerformanceResponse(symbol="TEST")

        assert resp.data_points == 0
        assert resp.absolute_returns == {}
        assert resp.risk_adjusted_metrics == {}


# ─────────────────────────────────────────────────────────────
# Risk Agent Tests
# ─────────────────────────────────────────────────────────────


class TestRiskAgentTools:
    """Test that the Risk Agent includes the new tools."""

    def test_risk_agent_has_sortino_tool(self):
        """Risk Agent should include calculate_sortino_ratio tool."""
        from src.agents.risk import RiskAnalystAgent

        agent = RiskAnalystAgent()
        tool_names = [t.name for t in agent._get_default_tools()]

        assert "calculate_sortino_ratio" in tool_names

    def test_risk_agent_has_beta_tool(self):
        """Risk Agent should include calculate_beta tool."""
        from src.agents.risk import RiskAnalystAgent

        agent = RiskAnalystAgent()
        tool_names = [t.name for t in agent._get_default_tools()]

        assert "calculate_beta" in tool_names

    def test_risk_agent_has_performance_tool(self):
        """Risk Agent should include track_stock_performance tool."""
        from src.agents.risk import RiskAnalystAgent

        agent = RiskAnalystAgent()
        tool_names = [t.name for t in agent._get_default_tools()]

        assert "track_stock_performance" in tool_names

    def test_risk_agent_total_tools(self):
        """Risk Agent should have 7 tools total."""
        from src.agents.risk import RiskAnalystAgent

        agent = RiskAnalystAgent()
        tools = agent._get_default_tools()

        assert len(tools) == 7
