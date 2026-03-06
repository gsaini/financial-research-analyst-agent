"""
Tests for Feature 11: Key Observations & Insights.

Tests cover:
- Individual detector functions (technical, valuation, earnings, performance)
- Confluence detection
- Anomaly detection
- Ranking / scoring
- Full generate_observations() pipeline
- ObservationsResponse schema validation
- Orchestrator integration
"""

import pytest

from src.tools.insight_engine import (
    generate_observations,
    _detect_technical_signals,
    _detect_valuation_signals,
    _detect_earnings_signals,
    _detect_performance_signals,
    _detect_confluences,
    _detect_anomalies,
    _rank_observations,
    _obs,
    CATEGORY_BULLISH,
    CATEGORY_BEARISH,
    CATEGORY_RISK,
    CATEGORY_OPPORTUNITY,
    CATEGORY_WATCH,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
)


# ─────────────────────────────────────────────────────────────
# Helpers: sample analysis dicts
# ─────────────────────────────────────────────────────────────


def _tech_oversold():
    return {
        "rsi": {"value": 25.0},
        "macd": {"crossover": "bullish", "histogram": 0.5},
        "moving_averages": {"trend": "bullish", "sma_50": 160, "sma_200": 150},
        "bollinger_bands": {"position": "below_lower", "lower_band": 140},
    }


def _tech_overbought():
    return {
        "rsi": {"value": 78.0},
        "macd": {"crossover": "bearish", "histogram": -0.3},
        "moving_averages": {"trend": "bearish", "sma_50": 145, "sma_200": 155},
        "bollinger_bands": {"position": "above_upper", "upper_band": 170},
    }


def _peers_discount():
    return {
        "target": "AAPL",
        "comparison_table": {
            "pe_ratio": {"AAPL": 18.0, "MSFT": 35.0, "GOOGL": 25.0, "peer_median": 25.0},
        },
    }


def _peers_premium():
    return {
        "target": "TSLA",
        "comparison_table": {
            "pe_ratio": {"TSLA": 65.0, "F": 8.0, "GM": 6.0, "peer_median": 7.0},
        },
    }


def _earnings_beater():
    return {
        "earnings_surprise_history": {
            "beats": 7, "misses": 0, "inline": 1,
            "average_surprise": "+3.2%", "pattern": "Consistent beater",
        },
        "quarterly_trends": {
            "revenue_trend": "Accelerating",
            "revenue_qoq_growth": ["+2.1%", "+3.4%", "+4.1%"],
        },
        "earnings_quality": {"score": 9, "assessment": "High quality"},
    }


def _earnings_weak():
    return {
        "earnings_surprise_history": {
            "beats": 1, "misses": 5, "inline": 2,
            "average_surprise": "-2.1%", "pattern": "Frequent misser",
        },
        "quarterly_trends": {
            "revenue_trend": "Decelerating",
            "revenue_qoq_growth": ["+15%", "+12%", "+8%"],
        },
        "earnings_quality": {"score": 3, "assessment": "Low quality"},
    }


def _performance_strong():
    return {
        "benchmark_comparison": {
            "vs_spy": {"1_year_alpha": "+15.2%", "assessment": "Outperforming"},
        },
        "drawdown_analysis": {"max_drawdown": "-8%"},
        "risk_adjusted_metrics": {"sharpe_ratio": {"value": 1.5}},
    }


def _performance_weak():
    return {
        "benchmark_comparison": {
            "vs_spy": {"1_year_alpha": "-12.5%", "assessment": "Underperforming"},
        },
        "drawdown_analysis": {"max_drawdown": "-32%", "max_drawdown_date": "2025-06-15",
                              "recovery_days": 55},
        "risk_adjusted_metrics": {"sharpe_ratio": {"value": -0.3}},
    }


# ─────────────────────────────────────────────────────────────
# Technical Detector Tests
# ─────────────────────────────────────────────────────────────


class TestTechnicalDetector:

    def test_oversold_signals(self):
        obs = _detect_technical_signals(_tech_oversold())
        categories = [o["category"] for o in obs]
        assert CATEGORY_BULLISH in categories
        titles = [o["title"] for o in obs]
        assert any("RSI Oversold" in t for t in titles)

    def test_overbought_signals(self):
        obs = _detect_technical_signals(_tech_overbought())
        categories = [o["category"] for o in obs]
        assert CATEGORY_BEARISH in categories
        titles = [o["title"] for o in obs]
        assert any("RSI Overbought" in t for t in titles)

    def test_macd_bullish(self):
        obs = _detect_technical_signals({"macd": {"crossover": "bullish", "histogram": 1}})
        assert any("MACD Bullish" in o["title"] for o in obs)

    def test_macd_bearish(self):
        obs = _detect_technical_signals({"macd": {"crossover": "bearish", "histogram": -1}})
        assert any("MACD Bearish" in o["title"] for o in obs)

    def test_bollinger_below_lower(self):
        obs = _detect_technical_signals({"bollinger_bands": {"position": "below_lower", "lower_band": 100}})
        assert any("Below Lower Bollinger" in o["title"] for o in obs)

    def test_bollinger_above_upper(self):
        obs = _detect_technical_signals({"bollinger_bands": {"position": "above_upper", "upper_band": 200}})
        assert any("Above Upper Bollinger" in o["title"] for o in obs)

    def test_empty_returns_nothing(self):
        assert _detect_technical_signals({}) == []
        assert _detect_technical_signals(None) == []

    def test_moving_average_bullish_trend(self):
        obs = _detect_technical_signals({"moving_averages": {"trend": "bullish", "sma_50": 160, "sma_200": 150}})
        assert any("Bullish Moving Average" in o["title"] for o in obs)


# ─────────────────────────────────────────────────────────────
# Valuation Detector Tests
# ─────────────────────────────────────────────────────────────


class TestValuationDetector:

    def test_pe_discount(self):
        obs = _detect_valuation_signals({}, _peers_discount())
        assert any(o["category"] == CATEGORY_OPPORTUNITY for o in obs)
        assert any("Discount" in o["title"] for o in obs)

    def test_pe_premium(self):
        obs = _detect_valuation_signals({}, _peers_premium())
        assert any(o["category"] == CATEGORY_RISK for o in obs)
        assert any("Premium" in o["title"] for o in obs)

    def test_weak_financial_health(self):
        obs = _detect_valuation_signals({"financial_health": {"overall_score": 30}}, {})
        assert any("Weak Financial Health" in o["title"] for o in obs)

    def test_empty_returns_nothing(self):
        assert _detect_valuation_signals({}, {}) == []


# ─────────────────────────────────────────────────────────────
# Earnings Detector Tests
# ─────────────────────────────────────────────────────────────


class TestEarningsDetector:

    def test_consistent_beater(self):
        obs = _detect_earnings_signals(_earnings_beater())
        titles = [o["title"] for o in obs]
        assert any("Consistent Earnings Beater" in t for t in titles)

    def test_frequent_misser(self):
        obs = _detect_earnings_signals(_earnings_weak())
        titles = [o["title"] for o in obs]
        assert any("Frequent Earnings Misses" in t for t in titles)

    def test_revenue_decelerating(self):
        obs = _detect_earnings_signals(_earnings_weak())
        titles = [o["title"] for o in obs]
        assert any("Revenue Growth Decelerating" in t for t in titles)

    def test_revenue_accelerating(self):
        obs = _detect_earnings_signals(_earnings_beater())
        titles = [o["title"] for o in obs]
        assert any("Revenue Growth Accelerating" in t for t in titles)

    def test_high_earnings_quality(self):
        obs = _detect_earnings_signals(_earnings_beater())
        titles = [o["title"] for o in obs]
        assert any("High Earnings Quality" in t for t in titles)

    def test_low_earnings_quality(self):
        obs = _detect_earnings_signals(_earnings_weak())
        titles = [o["title"] for o in obs]
        assert any("Low Earnings Quality" in t for t in titles)

    def test_empty_returns_nothing(self):
        assert _detect_earnings_signals({}) == []


# ─────────────────────────────────────────────────────────────
# Performance Detector Tests
# ─────────────────────────────────────────────────────────────


class TestPerformanceDetector:

    def test_outperformance(self):
        obs = _detect_performance_signals(_performance_strong())
        assert any("Outperformance" in o["title"] for o in obs)

    def test_underperformance(self):
        obs = _detect_performance_signals(_performance_weak())
        assert any("Underperformance" in o["title"] for o in obs)

    def test_significant_drawdown(self):
        obs = _detect_performance_signals(_performance_weak())
        assert any("Drawdown" in o["title"] for o in obs)

    def test_negative_sharpe(self):
        obs = _detect_performance_signals(_performance_weak())
        assert any("Negative Risk-Adjusted" in o["title"] for o in obs)

    def test_empty_returns_nothing(self):
        assert _detect_performance_signals({}) == []


# ─────────────────────────────────────────────────────────────
# Confluence Tests
# ─────────────────────────────────────────────────────────────


class TestConfluence:

    def test_bullish_confluence(self):
        obs = [
            _obs(CATEGORY_BULLISH, SEVERITY_HIGH, "A", "a", [], direction="bullish"),
            _obs(CATEGORY_BULLISH, SEVERITY_MEDIUM, "B", "b", [], direction="bullish"),
            _obs(CATEGORY_BULLISH, SEVERITY_LOW, "C", "c", [], direction="bullish"),
        ]
        conf = _detect_confluences(obs)
        assert len(conf) == 1
        assert conf[0]["direction"] == "Bullish"
        assert conf[0]["signal_count"] == 3

    def test_bearish_confluence(self):
        obs = [
            _obs(CATEGORY_BEARISH, SEVERITY_HIGH, "X", "x", [], direction="bearish"),
            _obs(CATEGORY_BEARISH, SEVERITY_MEDIUM, "Y", "y", [], direction="bearish"),
            _obs(CATEGORY_BEARISH, SEVERITY_LOW, "Z", "z", [], direction="bearish"),
        ]
        conf = _detect_confluences(obs)
        assert len(conf) == 1
        assert conf[0]["direction"] == "Bearish"

    def test_no_confluence_below_three(self):
        obs = [
            _obs(CATEGORY_BULLISH, SEVERITY_LOW, "A", "a", [], direction="bullish"),
            _obs(CATEGORY_BULLISH, SEVERITY_LOW, "B", "b", [], direction="bullish"),
        ]
        assert _detect_confluences(obs) == []

    def test_strength_labels(self):
        obs = [_obs(CATEGORY_BULLISH, SEVERITY_LOW, f"S{i}", "", [], direction="bullish")
               for i in range(5)]
        conf = _detect_confluences(obs)
        assert conf[0]["combined_strength"] == "Very Strong"


# ─────────────────────────────────────────────────────────────
# Anomaly Tests
# ─────────────────────────────────────────────────────────────


class TestAnomaly:

    def test_oversold_but_decelerating(self):
        analyses = {
            "technical": {"rsi": {"value": 25}},
            "earnings": {"quarterly_trends": {"revenue_trend": "Decelerating"}},
        }
        anomalies = _detect_anomalies(analyses)
        assert len(anomalies) >= 1
        assert "oversold" in anomalies[0]["description"].lower()

    def test_no_anomalies_clean_data(self):
        analyses = {"technical": {}, "earnings": {}, "performance": {}}
        assert _detect_anomalies(analyses) == []


# ─────────────────────────────────────────────────────────────
# Ranking Tests
# ─────────────────────────────────────────────────────────────


class TestRanking:

    def test_observations_ranked_by_importance(self):
        obs = [
            _obs(CATEGORY_BULLISH, SEVERITY_LOW, "Low", "", [], confidence=0.5),
            _obs(CATEGORY_BEARISH, SEVERITY_HIGH, "High", "", [], confidence=0.9),
            _obs(CATEGORY_WATCH, SEVERITY_MEDIUM, "Med", "", [], confidence=0.7),
        ]
        ranked = _rank_observations(obs)
        assert ranked[0]["title"] == "High"
        assert ranked[0]["rank"] == 1
        assert ranked[-1]["title"] == "Low"

    def test_rank_numbers_sequential(self):
        obs = [_obs(CATEGORY_BULLISH, SEVERITY_LOW, f"O{i}", "", []) for i in range(5)]
        ranked = _rank_observations(obs)
        assert [o["rank"] for o in ranked] == [1, 2, 3, 4, 5]


# ─────────────────────────────────────────────────────────────
# Full Pipeline Tests
# ─────────────────────────────────────────────────────────────


class TestGenerateObservations:

    def test_bullish_pipeline(self):
        analyses = {
            "technical": _tech_oversold(),
            "earnings": _earnings_beater(),
            "performance": _performance_strong(),
            "peers": _peers_discount(),
        }
        result = generate_observations("AAPL", analyses)

        assert result["symbol"] == "AAPL"
        assert result["total_observations"] > 0
        assert result["overall_bias"] == "Bullish"
        assert result["bullish_signals"] > result["bearish_signals"]
        assert len(result["observations"]) == result["total_observations"]
        assert "confluences" in result
        assert "anomalies" in result
        assert "execution_time_seconds" in result

    def test_bearish_pipeline(self):
        analyses = {
            "technical": _tech_overbought(),
            "earnings": _earnings_weak(),
            "performance": _performance_weak(),
            "peers": _peers_premium(),
        }
        result = generate_observations("TSLA", analyses)

        assert result["overall_bias"] == "Bearish"
        assert result["bearish_signals"] > result["bullish_signals"]

    def test_empty_analyses(self):
        result = generate_observations("EMPTY", {})
        assert result["total_observations"] == 0
        assert result["overall_bias"] == "Mixed / Neutral"
        assert result["observations"] == []

    def test_partial_analyses(self):
        result = generate_observations("PART", {"technical": _tech_oversold()})
        assert result["total_observations"] > 0

    def test_observations_have_required_keys(self):
        result = generate_observations("AAPL", {"technical": _tech_oversold()})
        for obs in result["observations"]:
            assert "rank" in obs
            assert "category" in obs
            assert "severity" in obs
            assert "title" in obs
            assert "observation" in obs
            assert "supporting_evidence" in obs
            assert "confidence" in obs

    def test_confluence_boosts_severity(self):
        """With 4+ bullish signals, top observation should become Critical."""
        analyses = {
            "technical": _tech_oversold(),
            "earnings": _earnings_beater(),
            "performance": _performance_strong(),
            "peers": _peers_discount(),
        }
        result = generate_observations("AAPL", analyses)
        # If we have >= 4 bullish confluent signals, top should be Critical
        if result["bullish_signals"] >= 4:
            assert result["observations"][0]["severity"] == "Critical"


# ─────────────────────────────────────────────────────────────
# Schema Tests
# ─────────────────────────────────────────────────────────────


class TestObservationsSchema:

    def test_schema_valid(self):
        from src.api.schemas import ObservationsResponse

        resp = ObservationsResponse(
            symbol="AAPL",
            total_observations=3,
            overall_bias="Bullish",
            bullish_signals=2,
            bearish_signals=1,
            observations=[{"rank": 1, "title": "Test"}],
        )
        assert resp.symbol == "AAPL"
        assert resp.total_observations == 3

    def test_schema_defaults(self):
        from src.api.schemas import ObservationsResponse

        resp = ObservationsResponse(symbol="TEST")
        assert resp.total_observations == 0
        assert resp.overall_bias == "Mixed / Neutral"
        assert resp.observations == []
        assert resp.confluences == []
        assert resp.anomalies == []


# ─────────────────────────────────────────────────────────────
# Orchestrator Integration Tests
# ─────────────────────────────────────────────────────────────


class TestOrchestratorObservationsIntegration:

    def test_orchestrator_has_get_observations(self):
        from src.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent()
        assert hasattr(agent, "get_observations")
        assert callable(agent.get_observations)
