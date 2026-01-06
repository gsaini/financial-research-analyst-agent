"""
Tests for the API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.routes import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestAnalyzeEndpoint:
    """Tests for analyze endpoint."""
    
    @patch('src.api.routes.get_stock_price')
    @patch('src.api.routes.get_historical_data')
    def test_analyze_stock(self, mock_hist, mock_price, client):
        """Test stock analysis endpoint."""
        mock_price.return_value = {
            "symbol": "AAPL",
            "current_price": 180.50,
            "change_percent": 1.5,
        }
        mock_hist.return_value = {
            "closes": list(range(150, 200)),
        }
        
        response = client.post(
            "/api/v1/analyze",
            json={"symbol": "AAPL", "analysis_type": "comprehensive"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "recommendation" in data
        assert "confidence" in data
    
    @patch('src.api.routes.get_stock_price')
    def test_analyze_invalid_symbol(self, mock_price, client):
        """Test analysis with invalid symbol."""
        mock_price.return_value = {"error": "Invalid symbol"}
        
        response = client.post(
            "/api/v1/analyze",
            json={"symbol": "INVALID123"}
        )
        
        assert response.status_code == 400


class TestTechnicalEndpoint:
    """Tests for technical analysis endpoint."""
    
    @patch('src.api.routes.get_historical_data')
    def test_get_technical(self, mock_hist, client):
        """Test technical analysis endpoint."""
        mock_hist.return_value = {
            "closes": list(range(100, 200)),
        }
        
        response = client.get("/api/v1/technical/AAPL")
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "rsi" in data
        assert "macd" in data


class TestFundamentalEndpoint:
    """Tests for fundamental analysis endpoint."""
    
    @patch('src.api.routes.get_company_info')
    @patch('src.api.routes.get_stock_price')
    def test_get_fundamental(self, mock_price, mock_company, client):
        """Test fundamental analysis endpoint."""
        mock_price.return_value = {"symbol": "AAPL", "current_price": 180}
        mock_company.return_value = {"name": "Apple Inc.", "sector": "Technology"}
        
        response = client.get("/api/v1/fundamental/AAPL")
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "company" in data


class TestSentimentEndpoint:
    """Tests for sentiment analysis endpoint."""
    
    def test_get_sentiment(self, client):
        """Test sentiment analysis endpoint."""
        response = client.get("/api/v1/sentiment/AAPL")
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "sentiment" in data
        assert "score" in data


class TestPortfolioEndpoint:
    """Tests for portfolio analysis endpoint."""
    
    @patch('src.api.routes.get_stock_price')
    def test_analyze_portfolio(self, mock_price, client):
        """Test portfolio analysis endpoint."""
        mock_price.return_value = {"symbol": "AAPL", "current_price": 180}
        
        response = client.post(
            "/api/v1/portfolio",
            json={"symbols": ["AAPL", "GOOGL", "MSFT"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbols"] == ["AAPL", "GOOGL", "MSFT"]
        assert "individual_analyses" in data
        assert "diversification_score" in data


class TestReportEndpoint:
    """Tests for report generation endpoint."""
    
    def test_generate_report(self, client):
        """Test report generation endpoint."""
        response = client.post(
            "/api/v1/reports",
            json={"symbols": ["AAPL"], "format": "markdown"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert "content" in data


class TestMarketSummaryEndpoint:
    """Tests for market summary endpoint."""
    
    def test_get_market_summary(self, client):
        """Test market summary endpoint."""
        response = client.get("/api/v1/market/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert "market_status" in data
        assert "indices" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
