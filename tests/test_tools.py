"""
Tests for the tools module.
"""

import pytest
import numpy as np
from src.tools.technical_indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_bollinger_bands,
    identify_support_resistance,
    detect_patterns,
)
from src.tools.financial_metrics import (
    calculate_valuation_ratios,
    calculate_profitability_ratios,
    calculate_liquidity_ratios,
    analyze_financial_health,
)


class TestTechnicalIndicators:
    """Tests for technical indicator calculations."""
    
    def setup_method(self):
        """Set up test data."""
        np.random.seed(42)
        self.prices = list(100 + np.cumsum(np.random.randn(100)))
    
    def test_calculate_rsi(self):
        """Test RSI calculation."""
        result = calculate_rsi(self.prices, period=14)
        
        assert "value" in result
        assert "signal" in result
        assert 0 <= result["value"] <= 100
    
    def test_calculate_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        result = calculate_rsi([100, 101, 102], period=14)
        
        assert "error" in result
    
    def test_calculate_macd(self):
        """Test MACD calculation."""
        result = calculate_macd(self.prices)
        
        assert "macd_line" in result
        assert "signal_line" in result
        assert "histogram" in result
        assert "trend" in result
    
    def test_calculate_moving_averages(self):
        """Test moving average calculations."""
        result = calculate_moving_averages(self.prices, periods=[20, 50])
        
        assert "sma_20" in result
        assert "sma_50" in result
        assert "ema_20" in result
        assert "ema_50" in result
        assert "current_price" in result
    
    def test_calculate_bollinger_bands(self):
        """Test Bollinger Bands calculation."""
        result = calculate_bollinger_bands(self.prices, period=20)
        
        assert "upper_band" in result
        assert "middle_band" in result
        assert "lower_band" in result
        assert "bandwidth" in result
        assert result["upper_band"] > result["middle_band"] > result["lower_band"]
    
    def test_identify_support_resistance(self):
        """Test support/resistance identification."""
        price_data = {
            "highs": self.prices,
            "lows": [p * 0.98 for p in self.prices],
            "closes": self.prices,
        }
        
        result = identify_support_resistance(price_data, window=5)
        
        assert "resistance_levels" in result
        assert "support_levels" in result
        assert "current_price" in result
    
    def test_detect_patterns(self):
        """Test pattern detection."""
        price_data = {"closes": self.prices}
        
        result = detect_patterns(price_data)
        
        assert "patterns_detected" in result
        assert isinstance(result["patterns_detected"], list)


class TestFinancialMetrics:
    """Tests for financial metric calculations."""
    
    def test_calculate_valuation_ratios(self):
        """Test valuation ratio calculations."""
        data = {
            "price": 150,
            "eps": 6,
            "book_value_per_share": 50,
            "revenue_per_share": 30,
            "enterprise_value": 2500000000,
            "ebitda": 200000000,
        }
        
        result = calculate_valuation_ratios(data)
        
        assert "pe_ratio" in result
        assert result["pe_ratio"] == 25  # 150 / 6
        assert "pb_ratio" in result
        assert result["pb_ratio"] == 3  # 150 / 50
    
    def test_calculate_profitability_ratios(self):
        """Test profitability ratio calculations."""
        data = {
            "revenue": 1000000,
            "gross_profit": 400000,
            "operating_income": 200000,
            "net_income": 150000,
            "total_assets": 2000000,
            "total_equity": 1000000,
        }
        
        result = calculate_profitability_ratios(data)
        
        assert "gross_margin" in result
        assert result["gross_margin"] == 40  # 400k/1M * 100
        assert "net_margin" in result
        assert result["net_margin"] == 15  # 150k/1M * 100
        assert "roe" in result
    
    def test_calculate_liquidity_ratios(self):
        """Test liquidity ratio calculations."""
        data = {
            "current_assets": 500000,
            "current_liabilities": 250000,
            "cash": 100000,
            "inventory": 100000,
            "total_debt": 300000,
            "total_equity": 400000,
        }
        
        result = calculate_liquidity_ratios(data)
        
        assert "current_ratio" in result
        assert result["current_ratio"] == 2.0  # 500k/250k
        assert "quick_ratio" in result
        assert "debt_to_equity" in result
    
    def test_analyze_financial_health(self):
        """Test comprehensive financial health analysis."""
        data = {
            "price": 100,
            "eps": 5,
            "revenue": 1000000,
            "net_income": 150000,
            "total_equity": 800000,
            "current_assets": 400000,
            "current_liabilities": 200000,
        }
        
        result = analyze_financial_health(data)
        
        assert "health_score" in result
        assert "strengths" in result
        assert "weaknesses" in result
        assert "overall_assessment" in result


class TestRSIEdgeCases:
    """Edge case tests for RSI calculation."""
    
    def test_rsi_all_gains(self):
        """Test RSI when all prices increase."""
        prices = list(range(100, 120))
        result = calculate_rsi(prices, period=14)
        
        assert result["value"] > 90  # Should be very high
    
    def test_rsi_all_losses(self):
        """Test RSI when all prices decrease."""
        prices = list(range(120, 100, -1))
        result = calculate_rsi(prices, period=14)
        
        assert result["value"] < 10  # Should be very low


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
