"""
Tests for Feature 7: Event-Driven Performance Analysis.

Tests cover:
- Event calendar extraction
- Price window computation and return calculations
- Pattern aggregation and consistency scoring
- EPS surprise-to-price correlation
- Full analyze_events() pipeline (mocked)
- EventAnalysisResponse schema validation
- Orchestrator integration
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _make_price_series(start: float, end: float, n: int = 60):
    """Generate synthetic daily prices with a realistic DatetimeIndex."""
    dates = pd.bdate_range(end=datetime(2026, 1, 30), periods=n)
    prices = np.linspace(start, end, n)
    noise = np.random.default_rng(42).normal(0, 0.3, n)
    prices = np.maximum(prices + noise, 1.0)
    return pd.Series(prices, index=dates)


def _mock_ticker_factory(
    earnings_records=None,
    dividend_data=None,
    split_data=None,
    prices=None,
    info=None,
):
    """Build a mock yfinance.Ticker with configurable attributes."""

    def factory(symbol):
        m = MagicMock()
        m.info = info or {"longName": f"Mock {symbol}", "sector": "Technology"}

        # earnings_history
        if earnings_records is not None:
            df = pd.DataFrame(earnings_records)
            if not df.empty:
                df.index = pd.to_datetime(df.pop("date"))
            m.earnings_history = df
        else:
            m.earnings_history = pd.DataFrame()

        # earnings_dates (empty by default)
        m.earnings_dates = pd.DataFrame()

        # dividends
        if dividend_data is not None:
            idx = pd.to_datetime([d["date"] for d in dividend_data])
            m.dividends = pd.Series(
                [d["amount"] for d in dividend_data], index=idx
            )
        else:
            m.dividends = pd.Series(dtype=float)

        # splits
        if split_data is not None:
            idx = pd.to_datetime([s["date"] for s in split_data])
            m.splits = pd.Series(
                [s["ratio"] for s in split_data], index=idx
            )
        else:
            m.splits = pd.Series(dtype=float)

        # history() for price data
        if prices is not None:
            m.history.return_value = pd.DataFrame(
                {"Close": prices.values}, index=prices.index
            )
        else:
            m.history.return_value = pd.DataFrame(
                {"Close": _make_price_series(100, 110, 60).values},
                index=_make_price_series(100, 110, 60).index,
            )

        return m

    return factory


# ─────────────────────────────────────────────────────────────
# Event Calendar Tests
# ─────────────────────────────────────────────────────────────


class TestEventCalendar:
    """Test the event calendar extraction."""

    @patch("src.tools.event_analyzer.yf")
    def test_calendar_earnings(self, mock_yf):
        """Should extract earnings dates from earnings_history."""
        from src.tools.event_analyzer import get_event_calendar

        mock_yf.Ticker.side_effect = _mock_ticker_factory(
            earnings_records=[
                {"date": "2025-10-30", "epsActual": 1.50, "epsEstimate": 1.40},
                {"date": "2025-07-31", "epsActual": 1.30, "epsEstimate": 1.25},
            ]
        )

        result = get_event_calendar("AAPL")

        assert result["symbol"] == "AAPL"
        assert len(result["earnings"]) == 2
        assert result["earnings"][0]["eps_actual"] == 1.30  # sorted — earlier date first
        assert result["total_events"] >= 2

    @patch("src.tools.event_analyzer.yf")
    def test_calendar_dividends(self, mock_yf):
        """Should extract dividend ex-dates."""
        from src.tools.event_analyzer import get_event_calendar

        mock_yf.Ticker.side_effect = _mock_ticker_factory(
            dividend_data=[
                {"date": "2025-08-07", "amount": 0.25},
                {"date": "2025-11-06", "amount": 0.26},
            ]
        )

        result = get_event_calendar("AAPL")

        assert len(result["dividends"]) == 2
        assert result["dividends"][0]["amount"] == 0.25

    @patch("src.tools.event_analyzer.yf")
    def test_calendar_empty(self, mock_yf):
        """Should handle no events gracefully."""
        from src.tools.event_analyzer import get_event_calendar

        mock_yf.Ticker.side_effect = _mock_ticker_factory()

        result = get_event_calendar("XYZ")

        assert result["total_events"] == 0
        assert result["earnings"] == []


# ─────────────────────────────────────────────────────────────
# Price Window Tests
# ─────────────────────────────────────────────────────────────


class TestEventWindow:
    """Test price window extraction and return calculations."""

    @patch("src.tools.event_analyzer._fetch_prices")
    def test_window_structure(self, mock_fetch):
        """Should return correct price levels and return segments."""
        from src.tools.event_analyzer import calculate_event_window

        prices = _make_price_series(100, 120, 30)
        mock_fetch.return_value = prices

        # Pick a date near the middle of the series
        event_date = prices.index[15].strftime("%Y-%m-%d")
        result = calculate_event_window("AAPL", event_date, days_before=5, days_after=5)

        assert "price_window" in result
        assert "returns" in result
        assert "5d_before" in result["price_window"]
        assert "event_day" in result["price_window"]
        assert "5d_after" in result["price_window"]

    @patch("src.tools.event_analyzer._fetch_prices")
    def test_returns_format(self, mock_fetch):
        """Returns should be formatted as percentage strings."""
        from src.tools.event_analyzer import calculate_event_window

        prices = _make_price_series(100, 120, 30)
        mock_fetch.return_value = prices

        event_date = prices.index[15].strftime("%Y-%m-%d")
        result = calculate_event_window("AAPL", event_date)

        returns = result["returns"]
        # All return entries should end with "%" or be "N/A"
        for v in returns.values():
            assert v.endswith("%") or v == "N/A"

    @patch("src.tools.event_analyzer._fetch_prices")
    def test_insufficient_data(self, mock_fetch):
        """Should return error for insufficient data."""
        from src.tools.event_analyzer import calculate_event_window

        mock_fetch.return_value = None

        result = calculate_event_window("AAPL", "2025-10-30")
        assert "error" in result

    def test_invalid_date(self):
        """Should return error for invalid date format."""
        from src.tools.event_analyzer import calculate_event_window

        result = calculate_event_window("AAPL", "not-a-date")
        assert "error" in result


# ─────────────────────────────────────────────────────────────
# Pattern Aggregation Tests
# ─────────────────────────────────────────────────────────────


class TestPatternAggregation:
    """Test historical pattern aggregation."""

    def test_aggregate_patterns(self):
        """Should compute averages and consistency across windows."""
        from src.tools.event_analyzer import _aggregate_patterns

        windows = [
            {"_returns_raw": {"pre_event": 1.5, "event_day": 3.0, "post_event_1d": -0.5, "post_event": -1.0, "full_window": 3.0}},
            {"_returns_raw": {"pre_event": 2.0, "event_day": 1.5, "post_event_1d": 0.5, "post_event": 0.0, "full_window": 4.0}},
            {"_returns_raw": {"pre_event": 1.0, "event_day": -1.0, "post_event_1d": -1.0, "post_event": -2.0, "full_window": -2.0}},
            {"_returns_raw": {"pre_event": 2.5, "event_day": 2.0, "post_event_1d": 0.0, "post_event": -0.5, "full_window": 4.0}},
        ]

        result = _aggregate_patterns(windows)

        assert result["events_analyzed"] == 4
        assert "average_pre_event_drift" in result
        assert "average_event_day_move" in result
        assert "consistency" in result
        assert "pattern" in result

    def test_aggregate_empty(self):
        """Should handle empty input."""
        from src.tools.event_analyzer import _aggregate_patterns

        result = _aggregate_patterns([])

        assert result["events_analyzed"] == 0
        assert "error" in result

    def test_consistency_high(self):
        """High consistency when most events have same direction."""
        from src.tools.event_analyzer import _aggregate_patterns

        windows = [
            {"_returns_raw": {"pre_event": r, "event_day": 1.0, "post_event_1d": 0.0, "post_event": 0.0, "full_window": 0.0}}
            for r in [1.0, 2.0, 1.5, 3.0]
        ]

        result = _aggregate_patterns(windows)

        assert "High" in result["consistency"]


# ─────────────────────────────────────────────────────────────
# Surprise Correlation Tests
# ─────────────────────────────────────────────────────────────


class TestSurpriseCorrelation:
    """Test EPS surprise-to-price correlation."""

    def test_positive_correlation(self):
        """Should detect positive correlation."""
        from src.tools.event_analyzer import _surprise_correlation

        earnings = [
            {"date": "2025-01-30", "eps_actual": 1.5, "eps_estimate": 1.3},
            {"date": "2025-04-30", "eps_actual": 1.8, "eps_estimate": 1.4},
            {"date": "2025-07-30", "eps_actual": 2.0, "eps_estimate": 1.5},
            {"date": "2025-10-30", "eps_actual": 1.2, "eps_estimate": 1.3},
        ]

        # event-day returns roughly proportional to surprise
        windows = [
            {"event_date": "2025-01-30", "_returns_raw": {"event_day": 2.0}},
            {"event_date": "2025-04-30", "_returns_raw": {"event_day": 4.0}},
            {"event_date": "2025-07-30", "_returns_raw": {"event_day": 5.0}},
            {"event_date": "2025-10-30", "_returns_raw": {"event_day": -1.0}},
        ]

        result = _surprise_correlation(earnings, windows)

        assert result["data_points"] == 4
        assert "correlation" in result
        assert result["correlation"] > 0  # Should be positive

    def test_insufficient_data(self):
        """Should note insufficient data."""
        from src.tools.event_analyzer import _surprise_correlation

        result = _surprise_correlation(
            [{"date": "2025-01-30", "eps_actual": 1.0, "eps_estimate": 1.0}],
            [{"event_date": "2025-01-30", "_returns_raw": {"event_day": 1.0}}],
        )

        assert "insufficient" in result["insight"].lower() or result["data_points"] < 3


# ─────────────────────────────────────────────────────────────
# Full analyze_events() Tests
# ─────────────────────────────────────────────────────────────


class TestAnalyzeEvents:
    """Test the main analyze_events entry point."""

    @patch("src.tools.event_analyzer._fetch_prices")
    @patch("src.tools.event_analyzer.yf")
    def test_full_analysis_structure(self, mock_yf, mock_fetch):
        """Should return all expected top-level keys."""
        from src.tools.event_analyzer import analyze_events

        prices = _make_price_series(100, 120, 60)
        mock_fetch.return_value = prices

        mock_yf.Ticker.side_effect = _mock_ticker_factory(
            earnings_records=[
                {"date": "2025-10-30", "epsActual": 1.50, "epsEstimate": 1.40},
                {"date": "2025-07-31", "epsActual": 1.30, "epsEstimate": 1.25},
                {"date": "2025-04-30", "epsActual": 1.20, "epsEstimate": 1.15},
            ],
            prices=prices,
        )

        result = analyze_events("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["event_type"] == "earnings"
        assert "events" in result
        assert "historical_patterns" in result
        assert "correlation_with_surprise" in result
        assert "analyzed_at" in result
        assert "execution_time_seconds" in result

    @patch("src.tools.event_analyzer.yf")
    def test_no_events(self, mock_yf):
        """Should handle zero events gracefully."""
        from src.tools.event_analyzer import analyze_events

        mock_yf.Ticker.side_effect = _mock_ticker_factory()

        result = analyze_events("XYZ", event_type="earnings")

        assert result["events_analyzed"] == 0
        assert "error" in result

    @patch("src.tools.event_analyzer.yf")
    def test_unknown_event_type(self, mock_yf):
        """Should return error for unknown event type."""
        from src.tools.event_analyzer import analyze_events

        mock_yf.Ticker.side_effect = _mock_ticker_factory()

        result = analyze_events("AAPL", event_type="unknown")

        assert "error" in result


# ─────────────────────────────────────────────────────────────
# Schema Tests
# ─────────────────────────────────────────────────────────────


class TestEventSchemas:
    """Test Pydantic schemas for event analysis."""

    def test_event_analysis_response_valid(self):
        """EventAnalysisResponse should accept valid data."""
        from src.api.schemas import EventAnalysisResponse

        resp = EventAnalysisResponse(
            symbol="AAPL",
            name="Apple Inc.",
            event_type="earnings",
            events_analyzed=4,
            events=[{"date": "2025-10-30", "returns": {"event_day": "3.5%"}}],
            historical_patterns={"average_event_day_move": "2.5%", "consistency": "High"},
            correlation_with_surprise={"correlation": 0.72, "insight": "Strong positive"},
        )

        assert resp.symbol == "AAPL"
        assert resp.events_analyzed == 4
        assert len(resp.events) == 1

    def test_event_analysis_response_defaults(self):
        """EventAnalysisResponse should have sensible defaults."""
        from src.api.schemas import EventAnalysisResponse

        resp = EventAnalysisResponse(symbol="TEST")

        assert resp.events_analyzed == 0
        assert resp.events == []
        assert resp.historical_patterns == {}
        assert resp.event_type == "earnings"


# ─────────────────────────────────────────────────────────────
# Orchestrator Integration Tests
# ─────────────────────────────────────────────────────────────


class TestOrchestratorEventIntegration:
    """Test that the orchestrator exposes analyze_events."""

    def test_orchestrator_has_analyze_events(self):
        """OrchestratorAgent should have analyze_events method."""
        from src.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent()
        assert hasattr(agent, "analyze_events")
        assert callable(agent.analyze_events)
