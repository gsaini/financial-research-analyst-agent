"""
Tests for Feature 2: Peer Group Comparison.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.tools.peer_comparison import discover_peers, compare_peers
from src.api.schemas import PeerComparisonResponse

# Mock data
MOCK_AAPL_INFO = {
    "symbol": "AAPL",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "marketCap": 3000000000000,
    "currentPrice": 180.0,
    "trailingPE": 30.0,
    "priceToBook": 45.0,
    "returnOnEquity": 1.5
}

MOCK_MSFT_INFO = {
    "symbol": "MSFT",
    "sector": "Technology",
    "industry": "Software - Infrastructure",
    "marketCap": 3100000000000,
    "currentPrice": 400.0,
    "trailingPE": 35.0,
    "priceToBook": 12.0,
    "returnOnEquity": 0.4
}

MOCK_NVDA_INFO = {
    "symbol": "NVDA",
    "sector": "Technology",
    "industry": "Semiconductors",
    "marketCap": 2000000000000,
    "currentPrice": 800.0,
    "trailingPE": 60.0,
    "priceToBook": 50.0,
    "returnOnEquity": 0.8
}

MOCK_TSLA_INFO = {
    "symbol": "TSLA", # Tech but diff industry
    "sector": "Consumer Cyclical", # Note: yfinance often puts TSLA in Consumer Cyclical
    "industry": "Auto Manufacturers",
    "marketCap": 600000000000,
    "currentPrice": 175.0,
    "trailingPE": 45.0,
}


@pytest.mark.asyncio
async def test_discover_peers():
    """Test peer discovery logic."""
    # We mock _fetch_info_cached to avoid network calls
    with patch("src.tools.peer_comparison._fetch_info_cached") as mock_fetch:
        
        def side_effect(symbol):
            if symbol == "AAPL": return MOCK_AAPL_INFO
            if symbol == "MSFT": return MOCK_MSFT_INFO
            if symbol == "NVDA": return MOCK_NVDA_INFO
            if symbol == "TSLA": return MOCK_TSLA_INFO
            return None # Others
            
        mock_fetch.side_effect = side_effect
        
        # We also need to mock DEFAULT_UNIVERSE to be small for test speed
        with patch("src.tools.peer_comparison.DEFAULT_UNIVERSE", ["MSFT", "NVDA", "TSLA"]):
            result = await discover_peers("AAPL", limit=5)
            
            assert result["symbol"] == "AAPL"
            assert result["target_sector"] == "Technology"
            peers = result["peers"]
            
            # MSFT is Tech (score 5) + Market Cap close (score 5) -> 10
            # NVDA is Tech (score 5) + Market Cap close (score 5) -> 10
            # TSLA is Consumer Cyclical -> Score 0? No, sector different.
            
            assert "MSFT" in peers
            assert "NVDA" in peers
            assert "TSLA" not in peers # Should filter out completely irrelevant ones
            assert len(peers) == 2


@pytest.mark.asyncio
async def test_compare_peers():
    """Test peer comparison logic."""
    with patch("src.tools.peer_comparison._fetch_info_cached") as mock_fetch:
        def side_effect(symbol):
            if symbol == "AAPL": return MOCK_AAPL_INFO
            if symbol == "MSFT": return MOCK_MSFT_INFO
            return {}
            
        mock_fetch.side_effect = side_effect
        
        result = await compare_peers("AAPL", ["MSFT"])
        
        assert result["target"] == "AAPL"
        assert "MSFT" in result["peer_group"]
        assert "pe_ratio" in result["peer_aggregates"]
        
        # Test math
        pe_median = result["peer_aggregates"]["pe_ratio"]["median"]
        # Values: AAPL(30), MSFT(35). Median = 32.5? 
        # Wait, metrics loop includes only VALID values.
        # Function computes aggregates over VALID values.
        # valid_symbols = AAPL, MSFT.
        # pe_values = [30, 35]. Median = 32.5.
        
        assert pe_median == 32.5
        
        # Test relative valuation
        # AAPL (30) vs Median (32.5) -> Discount
        # Diff = (30 - 32.5)/32.5 = -0.0769 -> -7.7%
        assert "pe_ratio" in result["relative_valuation"]
        assert "Discount" in result["relative_valuation"]["pe_ratio"]


@pytest.mark.asyncio
async def test_compare_peers_auto_discovery():
    """Test comparison with auto-discovery."""
    with patch("src.tools.peer_comparison.discover_peers") as mock_discover:
        mock_discover.return_value = {
            "symbol": "AAPL",
            "peers": ["MSFT"]
        }
        
        with patch("src.tools.peer_comparison._fetch_info_cached") as mock_fetch:
            mock_fetch.side_effect = lambda s: MOCK_AAPL_INFO if s == "AAPL" else MOCK_MSFT_INFO
            
            result = await compare_peers("AAPL")
            
            mock_discover.assert_called_once()
            assert "MSFT" in result["peer_group"]


def test_peer_schemas():
    """Test Pydantic schemas."""
    # Just verify they import and instantiate
    from src.api.schemas import PeerComparisonResponse
    from datetime import datetime
    
    resp = PeerComparisonResponse(
        target="AAPL",
        peer_group=["MSFT"],
        metrics={"AAPL": {}, "MSFT": {}},
        peer_aggregates={},
        percentile_rankings={},
        relative_valuation={},
        strengths=[],
        weaknesses=[],
        generated_at=datetime.utcnow()
    )
    assert resp.target == "AAPL"
