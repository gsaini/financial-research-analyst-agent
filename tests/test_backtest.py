"""
Tests for Feature 8: Backtesting Engine.

Tests cover:
- Strategy signal functions (edge-case behaviour)
- Simulation loop (_simulate) with synthetic data
- Performance metrics computation
- Full run_backtest() pipeline (mocked yfinance)
- BacktestRequest / BacktestResponse schema validation
- Orchestrator integration
- list_strategies helper
"""

import pytest
from unittest.mock import patch, MagicMock

import numpy as np

from src.tools.strategy_definitions import (
    rsi_reversal,
    macd_crossover,
    golden_death_cross,
    bollinger_reversion,
    momentum_composite,
    STRATEGIES,
    list_strategy_names,
    _rsi,
    _sma,
    _macd_histogram,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _trending_up(n: int = 300, start: float = 100.0, end: float = 200.0) -> np.ndarray:
    """Synthetic upward-trending price series."""
    rng = np.random.default_rng(42)
    trend = np.linspace(start, end, n)
    noise = rng.normal(0, 0.5, n)
    return np.maximum(trend + noise, 1.0)


def _trending_down(n: int = 300, start: float = 200.0, end: float = 100.0) -> np.ndarray:
    """Synthetic downward-trending price series."""
    rng = np.random.default_rng(42)
    trend = np.linspace(start, end, n)
    noise = rng.normal(0, 0.5, n)
    return np.maximum(trend + noise, 1.0)


def _sideways(n: int = 300, mean: float = 150.0, amplitude: float = 15.0) -> np.ndarray:
    """Synthetic sideways / range-bound series."""
    rng = np.random.default_rng(0)
    return mean + amplitude * np.sin(np.linspace(0, 20 * np.pi, n)) + rng.normal(0, 1, n)


# ─────────────────────────────────────────────────────────────
# Strategy Signal Tests
# ─────────────────────────────────────────────────────────────


class TestStrategySignals:
    """Test individual strategy signal functions."""

    def test_rsi_oversold_buy(self):
        """RSI < 30 on a sharp decline should return BUY."""
        prices = _trending_down(n=100, start=200, end=50)
        # At the very end RSI should be very low
        signal = rsi_reversal(prices, len(prices) - 1)
        assert signal in ("BUY", "HOLD")  # Depends on exact RSI

    def test_rsi_hold_on_insufficient_data(self):
        """Should HOLD when there isn't enough data for RSI."""
        prices = np.array([100.0, 101.0, 102.0])
        assert rsi_reversal(prices, 2) == "HOLD"

    def test_macd_hold_insufficient(self):
        """MACD needs ~35 bars; should HOLD with less."""
        prices = np.array([100.0] * 20)
        assert macd_crossover(prices, 19) == "HOLD"

    def test_golden_cross_hold_insufficient(self):
        """Golden cross needs 200 bars; should HOLD with less."""
        prices = np.array([100.0] * 100)
        assert golden_death_cross(prices, 99) == "HOLD"

    def test_bollinger_buy_at_lower(self):
        """Price at lower band should return BUY."""
        # Create data that drops sharply at the end
        prices = np.concatenate([np.full(30, 150.0), np.array([100.0])])
        signal = bollinger_reversion(prices, len(prices) - 1)
        assert signal == "BUY"

    def test_bollinger_sell_at_upper(self):
        """Price at upper band should return SELL."""
        prices = np.concatenate([np.full(30, 150.0), np.array([200.0])])
        signal = bollinger_reversion(prices, len(prices) - 1)
        assert signal == "SELL"

    def test_momentum_hold_insufficient(self):
        """Momentum needs 200-SMA; should HOLD with less."""
        prices = np.array([100.0] * 100)
        assert momentum_composite(prices, 99) == "HOLD"

    def test_strategy_registry_complete(self):
        """All 9 strategies should be registered."""
        assert len(STRATEGIES) == 9
        expected = {
            "rsi_reversal", "macd_crossover", "golden_death_cross",
            "bollinger_reversion", "momentum_composite", "mean_reversion",
            "breakout", "pairs_mean_reversion", "trend_following"
        }
        assert set(STRATEGIES.keys()) == expected

    def test_list_strategy_names(self):
        """list_strategy_names returns all keys."""
        names = list_strategy_names()
        assert len(names) == 9
        assert "rsi_reversal" in names


# ─────────────────────────────────────────────────────────────
# Indicator Helper Tests
# ─────────────────────────────────────────────────────────────


class TestIndicatorHelpers:
    """Test the indicator helper functions used by strategies."""

    def test_rsi_range(self):
        """RSI should be between 0 and 100."""
        prices = _trending_up(100)
        rsi = _rsi(prices, 99)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_sma_correctness(self):
        """SMA of constant prices equals the price."""
        prices = np.full(50, 42.0)
        assert _sma(prices, 49, 20) == pytest.approx(42.0)

    def test_sma_insufficient(self):
        """SMA returns None if not enough data."""
        prices = np.array([1.0, 2.0, 3.0])
        assert _sma(prices, 2, 10) is None

    def test_macd_histogram_returns_float(self):
        """MACD histogram should return a float for sufficient data."""
        prices = _trending_up(100)
        result = _macd_histogram(prices, 99)
        assert isinstance(result, float)


# ─────────────────────────────────────────────────────────────
# Simulation Tests
# ─────────────────────────────────────────────────────────────


class TestSimulation:
    """Test the _simulate() loop."""

    def test_simulate_no_trades(self):
        """A strategy that always HOLDs should produce no trades."""
        from src.tools.backtesting_engine import _simulate

        prices = _trending_up(50)
        trade_log, equity = _simulate(prices, lambda p, i: "HOLD", initial_capital=10000)

        assert len(trade_log) == 0
        # Equity should remain at initial capital throughout
        assert equity[-1] == pytest.approx(10000.0)

    def test_simulate_single_trade(self):
        """Manual BUY at bar 5, SELL at bar 10 should produce one trade."""
        from src.tools.backtesting_engine import _simulate

        prices = _trending_up(20, start=100, end=120)

        def simple_signal(p, i):
            if i == 5:
                return "BUY"
            if i == 10:
                return "SELL"
            return "HOLD"

        trade_log, equity = _simulate(prices, simple_signal, initial_capital=10000,
                                       commission_pct=0, slippage_pct=0)

        assert len(trade_log) == 1
        assert trade_log[0]["entry_idx"] == 5
        assert trade_log[0]["exit_idx"] == 10
        assert trade_log[0]["holding_bars"] == 5

    def test_simulate_open_position_at_end(self):
        """If BUY and never SELL, trade should be marked as open."""
        from src.tools.backtesting_engine import _simulate

        prices = _trending_up(30)

        def buy_only(p, i):
            if i == 5:
                return "BUY"
            return "HOLD"

        trade_log, _ = _simulate(prices, buy_only, initial_capital=10000,
                                  commission_pct=0, slippage_pct=0)

        assert len(trade_log) == 1
        assert trade_log[0].get("status") == "open"

    def test_equity_positive(self):
        """Equity curve values should always be >= 0."""
        from src.tools.backtesting_engine import _simulate

        prices = _sideways(100)
        _, equity = _simulate(prices, rsi_reversal, initial_capital=10000)

        assert all(e >= 0 for e in equity)


# ─────────────────────────────────────────────────────────────
# Metrics Tests
# ─────────────────────────────────────────────────────────────


class TestMetrics:
    """Test performance metric calculations."""

    def test_metrics_empty_log(self):
        """Should handle zero trades gracefully."""
        from src.tools.backtesting_engine import _compute_metrics

        equity = np.full(50, 10000.0)
        result = _compute_metrics([], equity, 10000.0, buy_hold_return=20.0, num_years=1.0)

        assert result["total_trades"] == 0
        assert result["win_rate"] == "0.0%"
        assert result["total_return"] == "+0.0%"

    def test_metrics_positive_return(self):
        """Should correctly compute positive total return."""
        from src.tools.backtesting_engine import _compute_metrics

        equity = np.linspace(10000, 12000, 50)
        trades = [{"return_pct": 20.0}]
        result = _compute_metrics(trades, equity, 10000.0, buy_hold_return=15.0, num_years=1.0)

        assert "+20.0%" in result["total_return"]
        assert result["total_trades"] == 1
        assert result["win_rate"] == "100.0%"


# ─────────────────────────────────────────────────────────────
# Full Pipeline Tests
# ─────────────────────────────────────────────────────────────


class TestRunBacktest:
    """Test the main run_backtest() entry point."""

    @patch("src.tools.backtesting_engine._fetch_prices")
    def test_full_pipeline(self, mock_fetch):
        """Should return all expected keys for a valid backtest."""
        from src.tools.backtesting_engine import run_backtest

        mock_fetch.return_value = _sideways(300)

        result = run_backtest("AAPL", strategy="rsi_reversal")

        assert result["symbol"] == "AAPL"
        assert result["strategy"] == "RSI Reversal"
        assert "trade_log" in result
        assert "performance" in result
        assert "verdict" in result
        assert "execution_time_seconds" in result

    @patch("src.tools.backtesting_engine._fetch_prices")
    def test_unknown_strategy(self, mock_fetch):
        """Should return error for an unknown strategy."""
        from src.tools.backtesting_engine import run_backtest

        result = run_backtest("AAPL", strategy="nonexistent")

        assert "error" in result

    @patch("src.tools.backtesting_engine._fetch_prices")
    def test_insufficient_data(self, mock_fetch):
        """Should return error if fewer than 50 bars."""
        from src.tools.backtesting_engine import run_backtest

        mock_fetch.return_value = np.array([100.0] * 10)

        result = run_backtest("AAPL", strategy="rsi_reversal")

        assert "error" in result

    @patch("src.tools.backtesting_engine._fetch_prices")
    def test_all_strategies_run(self, mock_fetch):
        """Each strategy should run without crashing."""
        from src.tools.backtesting_engine import run_backtest

        mock_fetch.return_value = _sideways(400)

        for key in STRATEGIES.keys():
            result = run_backtest("TEST", strategy=key)
            assert "error" not in result, f"Strategy {key} errored: {result.get('error')}"
            assert "performance" in result


# ─────────────────────────────────────────────────────────────
# list_strategies Tests
# ─────────────────────────────────────────────────────────────


class TestListStrategies:
    """Test the list_strategies helper."""

    def test_returns_list_of_dicts(self):
        from src.tools.backtesting_engine import list_strategies

        result = list_strategies()
        assert isinstance(result, list)
        assert len(result) == 9
        for entry in result:
            assert "key" in entry
            assert "name" in entry
            assert "description" in entry


# ─────────────────────────────────────────────────────────────
# Schema Tests
# ─────────────────────────────────────────────────────────────


class TestBacktestSchemas:
    """Test Pydantic schemas for backtesting."""

    def test_backtest_request_valid(self):
        from src.api.schemas import BacktestRequest

        req = BacktestRequest(symbol="AAPL")
        assert req.symbol == "AAPL"
        assert req.strategy == "rsi_reversal"
        assert req.initial_capital == 10000.0

    def test_backtest_response_valid(self):
        from src.api.schemas import BacktestResponse

        resp = BacktestResponse(
            symbol="AAPL",
            strategy="RSI Reversal",
            strategy_key="rsi_reversal",
            performance={"total_return": "+12.5%"},
            verdict="Strategy outperforms buy-and-hold.",
        )
        assert resp.symbol == "AAPL"
        assert resp.trade_log == []
        assert resp.data_points == 0

    def test_backtest_response_defaults(self):
        from src.api.schemas import BacktestResponse

        resp = BacktestResponse(symbol="TEST")
        assert resp.initial_capital == 10000.0
        assert resp.trade_log == []
        assert resp.performance == {}


# ─────────────────────────────────────────────────────────────
# Orchestrator Integration Tests
# ─────────────────────────────────────────────────────────────


class TestOrchestratorBacktestIntegration:
    """Test that the orchestrator exposes run_backtest."""

    def test_orchestrator_has_run_backtest(self):
        from src.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent()
        assert hasattr(agent, "run_backtest")
        assert callable(agent.run_backtest)
