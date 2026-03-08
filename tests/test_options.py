"""
Tests for Feature 13: Options Flow Analysis.

Tests cover:
- Put/Call ratio and total volume calculation
- Implied volatility and skew calculation
- Unusual activity detection (volume > 2x OI)
- Max pain calculation
- Options signal generation
- Full analyze_options() pipeline (mocked yfinance)
- OptionsAnalysisResponse schema validation
- Orchestrator integration
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np

from src.tools.options_analyzer import (
    analyze_options,
    _get_current_price,
    _calculate_sentiment,
    _calculate_volatility,
    _detect_unusual_activity,
    _calculate_max_pain,
    _generate_options_signal,
    _empty_options_response,
)


# ─────────────────────────────────────────────────────────────
# Helpers: synthetic data
# ─────────────────────────────────────────────────────────────


def _sample_calls():
    return pd.DataFrame([
        {"strike": 180, "lastPrice": 12.0, "impliedVolatility": 0.25, "volume": 1000, "openInterest": 5000, "expiration": "2026-02-21"},
        {"strike": 190, "lastPrice": 5.0,  "impliedVolatility": 0.28, "volume": 5000, "openInterest": 1500, "expiration": "2026-02-21"},
        {"strike": 200, "lastPrice": 1.5,  "impliedVolatility": 0.35, "volume": 200,  "openInterest": 1000, "expiration": "2026-02-21"}, # low vol
        {"strike": 210, "lastPrice": 0.5,  "impliedVolatility": 0.40, "volume": 0,    "openInterest": 500,  "expiration": "2026-02-21"}, # zero vol
    ])


def _sample_puts():
    return pd.DataFrame([
        {"strike": 170, "lastPrice": 1.0,  "impliedVolatility": 0.32, "volume": 3000, "openInterest": 10000, "expiration": "2026-02-21"},
        {"strike": 180, "lastPrice": 3.5,  "impliedVolatility": 0.30, "volume": 1500, "openInterest": 500,   "expiration": "2026-02-21"},
        {"strike": 190, "lastPrice": 8.0,  "impliedVolatility": 0.29, "volume": 500,  "openInterest": 1000,  "expiration": "2026-02-21"},
    ])


# ─────────────────────────────────────────────────────────────
# Sentiment Tests
# ─────────────────────────────────────────────────────────────


class TestSentimentCalculation:

    def test_sentiment_ratios(self):
        calls = _sample_calls()
        puts = _sample_puts()
        
        result = _calculate_sentiment(calls, puts)
        
        # Call vol: 1000 + 5000 + 200 = 6200
        # Put vol: 3000 + 1500 + 500 = 5000
        assert result["call_volume"] == 6200
        assert result["put_volume"] == 5000
        assert result["total_options_volume"] == 11200
        
        pc_ratio = round(5000 / 6200, 2)
        assert result["put_call_ratio"] == pc_ratio
        
        # 5000/6200 = ~0.8 (Neutral)
        assert result["put_call_assessment"] == "Neutral"

    def test_bullish_sentiment(self):
        calls = pd.DataFrame([{"volume": 10000}])
        puts = pd.DataFrame([{"volume": 2000}])
        result = _calculate_sentiment(calls, puts)
        assert result["put_call_ratio"] == 0.2
        assert "Bullish" in result["put_call_assessment"]

    def test_bearish_sentiment(self):
        calls = pd.DataFrame([{"volume": 2000}])
        puts = pd.DataFrame([{"volume": 10000}])
        result = _calculate_sentiment(calls, puts)
        assert result["put_call_ratio"] == 5.0
        assert "Bearish" in result["put_call_assessment"]

    def test_zero_call_volume(self):
        calls = pd.DataFrame([{"volume": 0}])
        puts = pd.DataFrame([{"volume": 1000}])
        result = _calculate_sentiment(calls, puts)
        assert result["put_call_ratio"] == 0.0
        assert "Indeterminate" in result["put_call_assessment"]
        
    def test_empty_dataframes(self):
        result = _calculate_sentiment(pd.DataFrame(), pd.DataFrame())
        assert result["total_options_volume"] == 0


# ─────────────────────────────────────────────────────────────
# Volatility Tests
# ─────────────────────────────────────────────────────────────


class TestVolatilityCalculation:

    def test_weighted_iv_and_skew(self):
        calls = _sample_calls()
        puts = _sample_puts()
        
        result = _calculate_volatility(calls, puts)
        
        # Test existence of keys
        assert "current_iv" in result
        assert "iv_assessment" in result
        assert "iv_skew" in result
        
        skew = result["iv_skew"]
        assert "put_iv" in skew
        assert "call_iv" in skew
        
        # Put IV generally higher in sample
        assert skew["put_iv"] > 0
        assert skew["call_iv"] > 0
        
    def test_empty_volatility(self):
        result = _calculate_volatility(pd.DataFrame(), pd.DataFrame())
        assert result["current_iv"] == 0.0


# ─────────────────────────────────────────────────────────────
# Unusual Activity Tests
# ─────────────────────────────────────────────────────────────


class TestUnusualActivity:

    def test_detects_high_volume_low_oi(self):
        calls = _sample_calls()
        puts = _sample_puts()
        current_price = 185.0
        
        unusual = _detect_unusual_activity(calls, puts, current_price)
        
        # Should detect:
        # Call 190: vol 5000, OI 1500 (> 2x, > 500)
        # Put 180: vol 1500, OI 500 (> 2x, > 500)
        
        assert len(unusual) == 2
        
        strikes = [u["strike"] for u in unusual]
        assert 190 in strikes
        assert 180 in strikes
        
        for u in unusual:
            assert u["volume"] >= 500
            assert u["vol_oi_ratio"] > 2.0
            assert "est_premium_paid" in u

    def test_directional_assessment(self):
        calls = pd.DataFrame([{"strike": 200, "lastPrice": 1.0, "impliedVolatility": 0.3, "volume": 5000, "openInterest": 1000, "expiration": "2026"}])
        puts = pd.DataFrame([{"strike": 170, "lastPrice": 1.0, "impliedVolatility": 0.3, "volume": 5000, "openInterest": 1000, "expiration": "2026"}])
        current_price = 185.0
        
        unusual = _detect_unusual_activity(calls, puts, current_price)
        
        assert len(unusual) == 2
        call_unusual = next(u for u in unusual if u["type"] == "CALL")
        put_unusual = next(u for u in unusual if u["type"] == "PUT")
        
        assert "Bullish" in call_unusual["assessment"]
        assert "Bearish" in put_unusual["assessment"]

    def test_filters_low_volume(self):
        calls = pd.DataFrame([{"strike": 200, "lastPrice": 1.0, "impliedVolatility": 0.3, "volume": 499, "openInterest": 100, "expiration": "2026"}])
        unusual = _detect_unusual_activity(calls, pd.DataFrame(), 185.0)
        assert len(unusual) == 0


# ─────────────────────────────────────────────────────────────
# Max Pain Tests
# ─────────────────────────────────────────────────────────────


class TestMaxPain:

    def test_max_pain_calculation(self):
        calls = _sample_calls()
        puts = _sample_puts()
        current_price = 185.0
        
        result = _calculate_max_pain(calls, puts, current_price)
        
        assert "price" in result
        assert result["price"] > 0
        assert "distance_from_current_pct" in result
        assert "options writers benefit" in result["interpretation"].lower()
        
    def test_max_pain_empty(self):
        result = _calculate_max_pain(pd.DataFrame(), pd.DataFrame(), 100.0)
        assert result["price"] == 0.0


# ─────────────────────────────────────────────────────────────
# Options Signal Tests
# ─────────────────────────────────────────────────────────────


class TestOptionsSignal:

    def test_bullish_signal(self):
        sentiment = {"put_call_ratio": 0.5}  # Bullish
        volatility = {"iv_skew": {"skew_assessment": "Call skew"}}  # Bullish
        unusual = [{"type": "CALL", "assessment": "Bullish: Buying OTM calls"}] * 3  # High call activity
        
        signal = _generate_options_signal(sentiment, volatility, unusual)
        assert signal["score"] > 70
        assert "Bullish" in signal["direction"]

    def test_bearish_signal(self):
        sentiment = {"put_call_ratio": 1.6}  # Bearish
        volatility = {"iv_skew": {"skew_assessment": "Put skew"}}  # Bearish
        unusual = [{"type": "PUT", "assessment": "Bearish/Hedge: Buying OTM puts"}] * 3  # High put activity
        
        signal = _generate_options_signal(sentiment, volatility, unusual)
        assert signal["score"] < 40
        assert "Bearish" in signal["direction"]

    def test_neutral_signal(self):
        sentiment = {"put_call_ratio": 0.95}
        volatility = {"iv_skew": {"skew_assessment": "Balanced"}}
        unusual = []
        
        signal = _generate_options_signal(sentiment, volatility, unusual)
        assert 40 <= signal["score"] <= 60
        assert "Neutral" in signal["direction"]


# ─────────────────────────────────────────────────────────────
# Full Pipeline Tests (mocked yfinance)
# ─────────────────────────────────────────────────────────────


class TestAnalyzeOptionsPipeline:

    @patch("src.tools.options_analyzer.yf.Ticker")
    def test_full_pipeline(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        # Setup mock ticker properties
        mock_ticker.info = {"currentPrice": 185.0}
        mock_ticker.options = ["2026-02-21", "2026-03-21"]
        
        # Setup mock option chain
        mock_chain = MagicMock()
        mock_chain.calls = _sample_calls()
        mock_chain.puts = _sample_puts()
        mock_ticker.option_chain.return_value = mock_chain

        result = analyze_options("AAPL")

        assert result["symbol"] == "AAPL"
        assert result["current_price"] == 185.0
        assert "options_sentiment" in result
        assert "implied_volatility" in result
        assert "max_pain" in result
        assert "unusual_activity" in result
        assert "options_signal" in result
        assert "score" in result["options_signal"]
        
        assert len(result["expirations_analyzed"]) > 0

    @patch("src.tools.options_analyzer.yf.Ticker")
    def test_handles_missing_options_data(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        mock_ticker.info = {"currentPrice": 185.0}
        mock_ticker.options = []  # No expirations

        result = analyze_options("NOOPT")

        assert result["symbol"] == "NOOPT"
        assert "error" in result
        assert "No options data" in result["error"]
        assert result["current_price"] == 0.0

    @patch("src.tools.options_analyzer.yf.Ticker")
    def test_handles_missing_price(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        mock_ticker.info = {}
        # Make history return empty dataframe
        mock_hist = MagicMock()
        mock_hist.empty = True
        mock_ticker.history.return_value = mock_hist

        result = analyze_options("NOPRICE")

        assert "error" in result
        assert "Could not fetch current price" in result["error"]


# ─────────────────────────────────────────────────────────────
# Schema Validation Tests
# ─────────────────────────────────────────────────────────────


class TestOptionsAnalysisSchema:

    def test_schema_valid(self):
        from src.api.schemas import OptionsAnalysisResponse

        resp = OptionsAnalysisResponse(
            symbol="AAPL",
            current_price=185.0,
            options_sentiment={"put_call_ratio": 0.8},
            implied_volatility={"current_iv": 30.5},
            unusual_activity=[{"type": "CALL", "strike": 200}],
            options_signal={"score": 65, "direction": "Bullish"},
            expirations_analyzed=["2026-02-21"]
        )
        assert resp.symbol == "AAPL"
        assert resp.current_price == 185.0
        assert len(resp.expirations_analyzed) == 1

    def test_schema_defaults(self):
        from src.api.schemas import OptionsAnalysisResponse

        resp = OptionsAnalysisResponse(symbol="TEST")
        assert resp.current_price == 0.0
        assert resp.options_sentiment == {}
        assert resp.unusual_activity == []


# ─────────────────────────────────────────────────────────────
# Orchestrator & Agent Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestOrchestratorOptionsIntegration:

    async def test_orchestrator_has_method(self):
        from src.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent()
        assert hasattr(agent, "analyze_options")
        assert callable(agent.analyze_options)

    @patch("src.agents.options.analyze_options")
    async def test_options_agent(self, mock_analyze_options):
        from src.agents.options import OptionsAnalystAgent
        
        mock_analyze_options.return_value = {"symbol": "AAPL", "options_sentiment": {}}
        
        agent = OptionsAnalystAgent()
        result = await agent.analyze("AAPL")
        
        assert result["symbol"] == "AAPL"
        assert result["agent_name"] == "OptionsAnalyst"
        assert "data" in result
        mock_analyze_options.assert_called_once_with("AAPL")
