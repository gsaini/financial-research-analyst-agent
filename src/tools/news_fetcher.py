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

        if not news:
            return _get_sample_news(symbol)

        articles = []
        for item in news[:20]:
            # Newer yfinance wraps data under a "content" key
            content = item.get("content", item)

            title = (
                content.get("title")
                or item.get("title")
                or ""
            )
            summary = (
                content.get("summary")
                or content.get("description")
                or item.get("title")
                or ""
            )
            # Strip any residual HTML tags from description
            if "<" in summary:
                import re
                summary = re.sub(r"<[^>]+>", "", summary)

            provider = content.get("provider") or {}
            source = (
                provider.get("displayName")
                if isinstance(provider, dict)
                else item.get("publisher", "")
            )

            # URL: try canonical, then clickThrough, then legacy "link"
            url = ""
            for url_key in ("canonicalUrl", "clickThroughUrl"):
                url_obj = content.get(url_key)
                if isinstance(url_obj, dict) and url_obj.get("url"):
                    url = url_obj["url"]
                    break
                elif isinstance(url_obj, str) and url_obj:
                    url = url_obj
                    break
            if not url:
                url = content.get("previewUrl") or item.get("link", "")

            # Published date
            pub_date = content.get("pubDate") or content.get("displayTime") or ""
            if not pub_date and item.get("providerPublishTime"):
                pub_date = datetime.fromtimestamp(
                    item["providerPublishTime"]
                ).isoformat()

            # Thumbnail
            thumbnail = ""
            thumb_obj = content.get("thumbnail")
            if isinstance(thumb_obj, dict):
                resolutions = thumb_obj.get("resolutions", [])
                if resolutions:
                    thumbnail = resolutions[0].get("url", "")
                elif thumb_obj.get("originalUrl"):
                    thumbnail = thumb_obj["originalUrl"]

            content_type = content.get("contentType", item.get("type", "STORY"))

            articles.append({
                "title": title,
                "description": summary,
                "source": source,
                "url": url,
                "published_at": pub_date,
                "type": content_type,
                "thumbnail": thumbnail,
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
