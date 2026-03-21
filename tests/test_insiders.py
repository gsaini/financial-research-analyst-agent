"""
Tests for Feature 12: Insider & Institutional Activity.

Tests cover:
- Insider transaction parsing and classification
- Net activity computation
- Cluster buying detection
- Institutional holdings parsing
- Smart money scoring
- Full analyze_smart_money() pipeline (mocked yfinance)
- SmartMoneyResponse schema validation
- Orchestrator integration
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, PropertyMock

import pandas as pd
import numpy as np

from src.tools.insider_activity import (
    get_insider_activity,
    get_institutional_holdings,
    analyze_smart_money,
    _classify_transaction,
    _compute_net_activity,
    _detect_cluster_buying,
    _compute_smart_money_score,
    _extract_insider_ownership,
    _extract_institutional_ownership,
    _parse_transactions,
    _to_float,
    _empty_net,
)


# ─────────────────────────────────────────────────────────────
# Helpers: synthetic data
# ─────────────────────────────────────────────────────────────


def _make_insider_txn_df(transactions: list) -> pd.DataFrame:
    """Build a synthetic insider_transactions DataFrame."""
    return pd.DataFrame(transactions)


def _recent_date(days_ago: int = 5) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _sample_insider_buys():
    return _make_insider_txn_df([
        {
            "Insider": "John Smith",
            "Position": "CEO",
            "Transaction": "Purchase",
            "Start Date": _recent_date(5),
            "Shares": 50000,
            "Value": 7250000,
        },
        {
            "Insider": "Jane Doe",
            "Position": "CFO",
            "Transaction": "Purchase",
            "Start Date": _recent_date(8),
            "Shares": 10000,
            "Value": 1465000,
        },
        {
            "Insider": "Bob Lee",
            "Position": "Director",
            "Transaction": "Sale",
            "Start Date": _recent_date(10),
            "Shares": -5000,
            "Value": 740000,
        },
    ])


def _sample_major_holders():
    return pd.DataFrame([
        ["0.07%", "% of Shares Held by All Insider"],
        ["60.50%", "% of Shares Held by Institutions"],
        ["72.30%", "% of Float Held by Institutions"],
        ["5423", "Number of Institutions Holding Shares"],
    ])


def _sample_institutional_holders():
    return pd.DataFrame([
        {"Holder": "Vanguard Group", "Shares": 1280000000, "% Out": 0.078, "Value": 2.5e11, "Date Reported": "2026-01-15"},
        {"Holder": "BlackRock", "Shares": 1050000000, "% Out": 0.064, "Value": 2.0e11, "Date Reported": "2026-01-15"},
        {"Holder": "Berkshire Hathaway", "Shares": 915000000, "% Out": 0.056, "Value": 1.7e11, "Date Reported": "2026-01-15"},
    ])


def _sample_mf_holders():
    return pd.DataFrame([
        {"Holder": "Vanguard Total Stock Market", "Shares": 400000000, "% Out": 0.024, "Value": 7.5e10, "Date Reported": "2026-01-15"},
    ])


# ─────────────────────────────────────────────────────────────
# Transaction Classification Tests
# ─────────────────────────────────────────────────────────────


class TestTransactionClassification:

    def test_purchase(self):
        assert _classify_transaction("Purchase", 1000) == "Buy"

    def test_buy_keyword(self):
        assert _classify_transaction("buy shares", 500) == "Buy"

    def test_acquisition(self):
        assert _classify_transaction("Acquisition (Non Open Market)", 200) == "Buy"

    def test_sale(self):
        assert _classify_transaction("Sale", -1000) == "Sale"

    def test_sell_keyword(self):
        assert _classify_transaction("sell shares", -500) == "Sale"

    def test_disposition(self):
        assert _classify_transaction("Disposition (Non Open Market)", -200) == "Sale"

    def test_fallback_negative_shares(self):
        assert _classify_transaction("Other", -100) == "Sale"

    def test_fallback_positive_shares(self):
        assert _classify_transaction("Other", 100) == "Buy"

    def test_unknown(self):
        assert _classify_transaction("Grant", 0) == "Other"


# ─────────────────────────────────────────────────────────────
# Net Activity Tests
# ─────────────────────────────────────────────────────────────


class TestNetActivity:

    def test_net_buying(self):
        txns = [
            {"transaction_type": "Buy", "shares": 50000, "value": 7250000},
            {"transaction_type": "Buy", "shares": 10000, "value": 1465000},
        ]
        result = _compute_net_activity(txns)
        assert result["net_shares"] == 60000
        assert result["net_value"] > 0
        assert result["total_buys"] == 2
        assert "buying" in result["assessment"].lower()

    def test_net_selling(self):
        txns = [
            {"transaction_type": "Sale", "shares": 50000, "value": 7250000},
        ]
        result = _compute_net_activity(txns)
        assert result["net_shares"] == -50000
        assert result["total_sales"] == 1
        assert "selling" in result["assessment"].lower()

    def test_mixed_activity(self):
        txns = [
            {"transaction_type": "Buy", "shares": 10000, "value": 1000000},
            {"transaction_type": "Sale", "shares": 50000, "value": 7000000},
        ]
        result = _compute_net_activity(txns)
        assert "mixed" in result["assessment"].lower()

    def test_empty(self):
        result = _compute_net_activity([])
        assert result["net_shares"] == 0
        assert result["total_buys"] == 0

    def test_empty_net_helper(self):
        result = _empty_net()
        assert result["total_buys"] == 0
        assert "No insider" in result["assessment"]


# ─────────────────────────────────────────────────────────────
# Cluster Buying Tests
# ─────────────────────────────────────────────────────────────


class TestClusterBuying:

    def test_cluster_detected(self):
        txns = [
            {"transaction_type": "Buy", "shares": 50000, "value": 7250000,
             "name": "John Smith", "date": _recent_date(5)},
            {"transaction_type": "Buy", "shares": 10000, "value": 1465000,
             "name": "Jane Doe", "date": _recent_date(8)},
        ]
        result = _detect_cluster_buying(txns, window_days=14, min_buyers=2)
        assert result["detected"] is True
        assert result["buyer_count"] >= 2
        assert "strong bullish" in result["details"].lower()

    def test_no_cluster_single_buyer(self):
        txns = [
            {"transaction_type": "Buy", "shares": 50000, "value": 7250000,
             "name": "John Smith", "date": _recent_date(5)},
        ]
        result = _detect_cluster_buying(txns, min_buyers=2)
        assert result["detected"] is False

    def test_no_cluster_no_buys(self):
        txns = [
            {"transaction_type": "Sale", "shares": 5000, "value": 740000,
             "name": "Bob Lee", "date": _recent_date(10)},
        ]
        result = _detect_cluster_buying(txns, min_buyers=2)
        assert result["detected"] is False


# ─────────────────────────────────────────────────────────────
# Ownership Extraction Tests
# ─────────────────────────────────────────────────────────────


class TestOwnershipExtraction:

    def test_insider_ownership(self):
        pct = _extract_insider_ownership(_sample_major_holders())
        assert pct is not None
        assert pct == 0.07

    def test_institutional_ownership(self):
        pct = _extract_institutional_ownership(_sample_major_holders())
        assert pct is not None
        assert pct == 60.5

    def test_none_on_empty(self):
        assert _extract_insider_ownership(None) is None
        assert _extract_institutional_ownership(None) is None


# ─────────────────────────────────────────────────────────────
# Smart Money Score Tests
# ─────────────────────────────────────────────────────────────


class TestSmartMoneyScore:

    def test_bullish_score(self):
        insider = {
            "net_activity": {"total_buys": 3, "total_sales": 0, "net_value": 10000000},
            "cluster_buying": {"detected": True},
        }
        institutional = {"institutional_ownership_pct": 75}
        result = _compute_smart_money_score(insider, institutional)
        assert result["score"] >= 75
        assert "bullish" in result["assessment"].lower()

    def test_bearish_score(self):
        insider = {
            "net_activity": {"total_buys": 0, "total_sales": 5, "net_value": -10000000},
            "cluster_buying": {"detected": False},
        }
        institutional = {"institutional_ownership_pct": 15}
        result = _compute_smart_money_score(insider, institutional)
        assert result["score"] < 40
        assert "bearish" in result["assessment"].lower()

    def test_neutral_score(self):
        insider = {
            "net_activity": {"total_buys": 0, "total_sales": 0, "net_value": 0},
            "cluster_buying": {"detected": False},
        }
        institutional = {"institutional_ownership_pct": 55}
        result = _compute_smart_money_score(insider, institutional)
        assert 40 <= result["score"] <= 60
        assert "neutral" in result["assessment"].lower()

    def test_score_clamped(self):
        """Score should never exceed 0-100 range."""
        insider = {
            "net_activity": {"total_buys": 20, "total_sales": 0, "net_value": 100000000},
            "cluster_buying": {"detected": True},
        }
        institutional = {"institutional_ownership_pct": 90}
        result = _compute_smart_money_score(insider, institutional)
        assert 0 <= result["score"] <= 100


# ─────────────────────────────────────────────────────────────
# Parse Transactions Tests
# ─────────────────────────────────────────────────────────────


class TestParseTransactions:

    def test_parses_recent_transactions(self):
        df = _sample_insider_buys()
        txns = _parse_transactions(df, days=90)
        assert len(txns) == 3

    def test_filters_old_transactions(self):
        df = _make_insider_txn_df([
            {"Insider": "Old Timer", "Transaction": "Purchase",
             "Start Date": "2020-01-01", "Shares": 100, "Value": 10000},
        ])
        txns = _parse_transactions(df, days=90)
        assert len(txns) == 0

    def test_handles_none(self):
        assert _parse_transactions(None, 90) == []


# ─────────────────────────────────────────────────────────────
# Full Pipeline Tests (mocked yfinance)
# ─────────────────────────────────────────────────────────────


class TestAnalyzeSmartMoney:

    @patch("src.tools.insider_activity.get_provider")
    def test_full_pipeline(self, mock_provider_func):
        mock_provider = MagicMock()
        mock_provider_func.return_value = mock_provider

        mock_provider.get_insider_transactions.return_value = _sample_insider_buys()
        mock_provider.get_insider_purchases.return_value = pd.DataFrame()
        mock_provider.get_major_holders.return_value = _sample_major_holders()
        mock_provider.get_institutional_holders.return_value = _sample_institutional_holders()
        mock_provider.get_mutualfund_holders.return_value = _sample_mf_holders()

        result = analyze_smart_money("AAPL")

        assert result["symbol"] == "AAPL"
        assert "insider_activity" in result
        assert "institutional_activity" in result
        assert "smart_money_signal" in result
        assert "score" in result["smart_money_signal"]
        assert "execution_time_seconds" in result

    @patch("src.tools.insider_activity.get_provider")
    def test_handles_empty_data(self, mock_provider_func):
        mock_provider = MagicMock()
        mock_provider_func.return_value = mock_provider

        mock_provider.get_insider_transactions.return_value = pd.DataFrame()
        mock_provider.get_insider_purchases.return_value = pd.DataFrame()
        mock_provider.get_major_holders.return_value = pd.DataFrame()
        mock_provider.get_institutional_holders.return_value = pd.DataFrame()
        mock_provider.get_mutualfund_holders.return_value = pd.DataFrame()

        result = analyze_smart_money("UNKNOWN")

        assert result["symbol"] == "UNKNOWN"
        assert result["insider_activity"]["transaction_count"] == 0
        assert result["institutional_activity"]["total_institutional_holders"] == 0

    @patch("src.tools.insider_activity.get_provider")
    def test_custom_days(self, mock_provider_func):
        mock_provider = MagicMock()
        mock_provider_func.return_value = mock_provider

        mock_provider.get_insider_transactions.return_value = _sample_insider_buys()
        mock_provider.get_insider_purchases.return_value = pd.DataFrame()
        mock_provider.get_major_holders.return_value = _sample_major_holders()
        mock_provider.get_institutional_holders.return_value = _sample_institutional_holders()
        mock_provider.get_mutualfund_holders.return_value = pd.DataFrame()

        result = analyze_smart_money("AAPL", days=30)
        assert result["period_days"] == 30


# ─────────────────────────────────────────────────────────────
# Utility Tests
# ─────────────────────────────────────────────────────────────


class TestUtilities:

    def test_to_float_valid(self):
        assert _to_float(42) == 42.0
        assert _to_float("3.14") == 3.14

    def test_to_float_invalid(self):
        assert _to_float(None) == 0.0
        assert _to_float("abc") == 0.0


# ─────────────────────────────────────────────────────────────
# Schema Tests
# ─────────────────────────────────────────────────────────────


class TestSmartMoneySchema:

    def test_schema_valid(self):
        from src.api.schemas import SmartMoneyResponse

        resp = SmartMoneyResponse(
            symbol="AAPL",
            smart_money_signal={"score": 72, "assessment": "Moderately bullish"},
        )
        assert resp.symbol == "AAPL"
        assert resp.period_days == 90

    def test_schema_defaults(self):
        from src.api.schemas import SmartMoneyResponse

        resp = SmartMoneyResponse(symbol="TEST")
        assert resp.insider_activity == {}
        assert resp.institutional_activity == {}
        assert resp.smart_money_signal == {}


# ─────────────────────────────────────────────────────────────
# Orchestrator Integration Tests
# ─────────────────────────────────────────────────────────────


class TestOrchestratorInsiderIntegration:

    def test_orchestrator_has_method(self):
        from src.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent()
        assert hasattr(agent, "analyze_insider_activity")
        assert callable(agent.analyze_insider_activity)
