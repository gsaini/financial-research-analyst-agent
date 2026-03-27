"""
News fetcher tools for gathering financial news.

Supports multiple sources with automatic fallback:
1. Yahoo Finance (via data provider) — free, no API key
2. NewsAPI — requires API key, higher quality
3. Sample data — last resort fallback for demo/dev
"""

from typing import Any, Dict, List
from datetime import datetime, timedelta
import os

import requests
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Configurable fallback behavior
FALLBACK_TO_SAMPLE = os.getenv("NEWS_FALLBACK_SAMPLE", "true").lower() == "true"


def fetch_news(query: str, days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch news articles related to a query.

    Tries multiple sources in order:
    1. NewsAPI (if API key configured)
    2. Yahoo Finance (via provider)
    3. Sample data (if FALLBACK_TO_SAMPLE=true)

    Args:
        query: Search query
        days_back: Number of days to look back

    Returns:
        List of news articles
    """
    # Source 1: NewsAPI
    articles = _fetch_from_newsapi(query, days_back)
    if articles:
        return articles

    # Source 2: Yahoo Finance via provider
    articles = _fetch_from_provider(query)
    if articles:
        return articles

    # Source 3: Sample fallback
    if FALLBACK_TO_SAMPLE:
        logger.warning(
            f"All news sources failed for '{query}' — falling back to sample data. "
            "Set NEWS_FALLBACK_SAMPLE=false to disable."
        )
        return _get_sample_news(query)

    logger.warning(f"All news sources failed for '{query}' and sample fallback is disabled.")
    return []


def fetch_company_news(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetch news specifically about a company.

    Tries provider first (Yahoo Finance), then NewsAPI, then sample.

    Args:
        symbol: Stock ticker symbol

    Returns:
        List of company-specific news
    """
    # Source 1: Yahoo Finance via provider (best for company-specific)
    articles = _fetch_from_provider(symbol)
    if articles:
        return articles

    # Source 2: NewsAPI
    articles = _fetch_from_newsapi(symbol, days_back=7)
    if articles:
        return articles

    # Source 3: Sample fallback
    if FALLBACK_TO_SAMPLE:
        logger.warning(
            f"All news sources failed for {symbol} — falling back to sample data. "
            "Set NEWS_FALLBACK_SAMPLE=false to disable."
        )
        return _get_sample_news(symbol)

    logger.warning(f"All news sources failed for {symbol} and sample fallback is disabled.")
    return []


# ── Source: NewsAPI ──────────────────────────────────────────────


def _fetch_from_newsapi(query: str, days_back: int = 7) -> List[Dict[str, Any]]:
    """Fetch from NewsAPI. Returns empty list if unavailable."""
    try:
        api_key = settings.data_api.news_api_key
        if not api_key or api_key == "your_news_api_key":
            return []

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

        if articles:
            logger.info(f"NewsAPI: fetched {len(articles)} articles for '{query}'")
        return articles

    except Exception as e:
        logger.debug(f"NewsAPI failed for '{query}': {e}")
        return []


# ── Source: Yahoo Finance via provider ───────────────────────────


def _fetch_from_provider(symbol: str) -> List[Dict[str, Any]]:
    """Fetch from Yahoo Finance provider. Returns empty list if unavailable."""
    try:
        from src.data import get_provider

        provider = get_provider()
        news = provider.get_news(symbol)

        if not news:
            return []

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

            prov = content.get("provider") or {}
            source = (
                prov.get("displayName")
                if isinstance(prov, dict)
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

        if articles:
            logger.info(f"Provider: fetched {len(articles)} news items for {symbol}")
        return articles

    except Exception as e:
        logger.debug(f"Provider news failed for {symbol}: {e}")
        return []


# ── Sample data fallback ─────────────────────────────────────────


def _get_sample_news(query: str) -> List[Dict[str, Any]]:
    """Return sample news data for demonstration/development."""
    return [
        {
            "title": f"{query} Reports Strong Quarterly Earnings",
            "description": f"{query} exceeded analyst expectations with record revenue growth.",
            "source": "Financial Times (Sample)",
            "url": "",
            "published_at": datetime.now().isoformat(),
            "_is_sample": True,
        },
        {
            "title": f"Analysts Upgrade {query} to Buy Rating",
            "description": f"Multiple Wall Street analysts have upgraded {query} citing strong fundamentals.",
            "source": "Bloomberg (Sample)",
            "url": "",
            "published_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "_is_sample": True,
        },
        {
            "title": f"{query} Announces New Product Launch",
            "description": f"{query} unveiled its latest product innovation at an industry conference.",
            "source": "Reuters (Sample)",
            "url": "",
            "published_at": (datetime.now() - timedelta(days=2)).isoformat(),
            "_is_sample": True,
        },
    ]
