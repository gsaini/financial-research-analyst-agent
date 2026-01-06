"""
News fetcher tools for gathering financial news.
"""

from typing import Any, Dict, List
from datetime import datetime, timedelta
import os

import requests
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def fetch_news(query: str, days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch news articles related to a query.
    
    Args:
        query: Search query
        days_back: Number of days to look back
        
    Returns:
        List of news articles
    """
    try:
        api_key = settings.data_api.news_api_key
        
        if not api_key or api_key == "your_news_api_key":
            # Return sample data if no API key
            return _get_sample_news(query)
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "from": from_date,
            "sortBy": "relevancy",
            "language": "en",
            "apiKey": api_key,
            "pageSize": 20,
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "source": article.get("source", {}).get("name", ""),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
                "author": article.get("author", ""),
            })
        
        return articles
        
    except Exception as e:
        logger.error(f"Error fetching news for {query}: {e}")
        return _get_sample_news(query)


def fetch_company_news(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetch news specifically about a company.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        List of company-specific news
    """
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol)
        news = ticker.news
        
        articles = []
        for item in news[:20]:
            articles.append({
                "title": item.get("title", ""),
                "description": item.get("title", ""),  # Yahoo doesn't provide description
                "source": item.get("publisher", ""),
                "url": item.get("link", ""),
                "published_at": datetime.fromtimestamp(
                    item.get("providerPublishTime", 0)
                ).isoformat() if item.get("providerPublishTime") else "",
                "type": item.get("type", ""),
            })
        
        return articles
        
    except Exception as e:
        logger.error(f"Error fetching company news for {symbol}: {e}")
        return _get_sample_news(symbol)


def _get_sample_news(query: str) -> List[Dict[str, Any]]:
    """Return sample news data for demonstration."""
    return [
        {
            "title": f"{query} Reports Strong Quarterly Earnings",
            "description": f"{query} exceeded analyst expectations with record revenue growth.",
            "source": "Financial Times",
            "url": "https://example.com/news/1",
            "published_at": datetime.now().isoformat(),
        },
        {
            "title": f"Analysts Upgrade {query} to Buy Rating",
            "description": f"Multiple Wall Street analysts have upgraded {query} citing strong fundamentals.",
            "source": "Bloomberg",
            "url": "https://example.com/news/2",
            "published_at": (datetime.now() - timedelta(days=1)).isoformat(),
        },
        {
            "title": f"{query} Announces New Product Launch",
            "description": f"{query} unveiled its latest product innovation at an industry conference.",
            "source": "Reuters",
            "url": "https://example.com/news/3",
            "published_at": (datetime.now() - timedelta(days=2)).isoformat(),
        },
    ]
