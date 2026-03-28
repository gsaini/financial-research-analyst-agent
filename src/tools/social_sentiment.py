"""
Social Media Sentiment Tool (Phase 2.2).

Monitors Reddit for stock sentiment using public JSON endpoints
(no API credentials required). Falls back gracefully when unavailable.

Usage::

    from src.tools.social_sentiment import get_reddit_sentiment
    result = get_reddit_sentiment("AAPL")
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from textblob import TextBlob

from src.utils.logger import get_logger

logger = get_logger(__name__)

_USER_AGENT = "FinancialResearchAgent/1.0 (educational project)"
_REQUEST_TIMEOUT = 10

# Common words that look like tickers but aren't
_TICKER_BLACKLIST = {
    "I", "A", "AM", "PM", "DD", "CEO", "CFO", "COO", "CTO", "IPO", "ETF",
    "SEC", "FDA", "GDP", "CPI", "IMF", "FED", "API", "AI", "ML", "USA",
    "UK", "EU", "NYSE", "THE", "FOR", "AND", "NOT", "ARE", "HAS", "HAD",
    "WAS", "ALL", "CAN", "HER", "HIS", "NEW", "OLD", "OUR", "OUT", "OWN",
    "SAY", "SHE", "TOO", "USE", "WAY", "WHO", "BOY", "DID", "GET", "HIM",
    "HOW", "MAN", "ITS", "LET", "MAY", "SAY", "TRY", "ASK", "BIG", "EOD",
    "ATH", "ATL", "EPS", "PE", "PB", "PS", "ROE", "ROA", "EV", "EBITDA",
    "YOLO", "HODL", "FOMO", "FUD", "IMO", "TLDR", "LOL", "OMG", "WTF",
    "RIP", "TIL", "PSA", "EDIT", "LMAO", "PUMP", "DUMP", "BEAR", "BULL",
    "CALL", "PUT", "LONG", "SHORT", "BUY", "SELL", "HOLD", "OPEN", "HIGH",
    "LOW", "CLOSE", "GAIN", "LOSS", "MOON", "DIP", "RUN", "RED", "GREEN",
}


# ── Reddit Public JSON API ──────────────────────────────────


def _reddit_search(
    subreddit: str, query: str, limit: int = 25
) -> List[Dict[str, Any]]:
    """Search a subreddit using public JSON API."""
    try:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            "q": query,
            "sort": "new",
            "limit": limit,
            "restrict_sr": "on",
            "t": "week",
        }
        headers = {"User-Agent": _USER_AGENT}
        resp = requests.get(url, params=params, headers=headers, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            posts.append({
                "title": post.get("title", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "created_utc": post.get("created_utc", 0),
                "subreddit": subreddit,
                "upvote_ratio": post.get("upvote_ratio", 0.5),
                "selftext": (post.get("selftext", "") or "")[:200],
            })
        return posts

    except Exception as e:
        logger.debug(f"Reddit search failed for r/{subreddit} q={query}: {e}")
        return []


def _reddit_hot(subreddit: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch hot posts from a subreddit."""
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        params = {"limit": limit}
        headers = {"User-Agent": _USER_AGENT}
        resp = requests.get(url, params=params, headers=headers, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            posts.append({
                "title": post.get("title", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "created_utc": post.get("created_utc", 0),
                "selftext": (post.get("selftext", "") or "")[:200],
            })
        return posts

    except Exception as e:
        logger.debug(f"Reddit hot fetch failed for r/{subreddit}: {e}")
        return []


# ── Sentiment scoring ────────────────────────────────────────


def _score_text(text: str) -> float:
    """Score sentiment of text using TextBlob. Returns polarity -1 to 1."""
    if not text:
        return 0.0
    try:
        return TextBlob(text).sentiment.polarity
    except Exception:
        return 0.0


def _sentiment_label(polarity: float) -> str:
    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    return "neutral"


# ── Public API ───────────────────────────────────────────────


def get_reddit_sentiment(
    symbol: str,
    subreddits: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Get Reddit sentiment for a stock symbol.

    Args:
        symbol: Stock ticker (e.g. "AAPL").
        subreddits: List of subreddits to search. Defaults to WSB, stocks, investing.

    Returns:
        Dict with post_count, avg_sentiment, sentiment_label, top_posts,
        subreddit_breakdown, and metadata.
    """
    if subreddits is None:
        subreddits = ["wallstreetbets", "stocks", "investing"]

    all_posts: List[Dict[str, Any]] = []
    sub_breakdown: Dict[str, Any] = {}

    for sub in subreddits:
        posts = _reddit_search(sub, symbol)
        if posts:
            sentiments = [_score_text(p["title"]) for p in posts]
            avg = sum(sentiments) / len(sentiments) if sentiments else 0
            sub_breakdown[sub] = {
                "post_count": len(posts),
                "avg_sentiment": round(avg, 3),
                "sentiment_label": _sentiment_label(avg),
            }
            for p, s in zip(posts, sentiments):
                p["sentiment"] = round(s, 3)
            all_posts.extend(posts)
        else:
            sub_breakdown[sub] = {"post_count": 0, "avg_sentiment": 0, "sentiment_label": "neutral"}
        # Rate limit courtesy
        time.sleep(1)

    if not all_posts:
        return {
            "symbol": symbol,
            "source": "unavailable",
            "message": "No Reddit data available — rate limited or no posts found.",
            "post_count": 0,
            "avg_sentiment": 0,
            "sentiment_label": "neutral",
        }

    # Aggregate
    sentiments = [p.get("sentiment", 0) for p in all_posts]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

    # Top posts by engagement (score + comments)
    sorted_posts = sorted(all_posts, key=lambda p: p["score"] + p["num_comments"], reverse=True)
    top_posts = [
        {
            "title": p["title"][:120],
            "subreddit": p.get("subreddit", ""),
            "score": p["score"],
            "comments": p["num_comments"],
            "sentiment": p.get("sentiment", 0),
        }
        for p in sorted_posts[:10]
    ]

    return {
        "symbol": symbol,
        "source": "reddit",
        "post_count": len(all_posts),
        "avg_sentiment": round(avg_sentiment, 3),
        "sentiment_label": _sentiment_label(avg_sentiment),
        "top_posts": top_posts,
        "subreddit_breakdown": sub_breakdown,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def get_trending_tickers(subreddit: str = "wallstreetbets") -> Dict[str, Any]:
    """
    Detect trending stock tickers from a subreddit's hot posts.

    Args:
        subreddit: Subreddit to scan.

    Returns:
        Dict with trending tickers sorted by mention count.
    """
    posts = _reddit_hot(subreddit)
    if not posts:
        return {
            "subreddit": subreddit,
            "source": "unavailable",
            "message": "Could not fetch Reddit data.",
            "tickers": [],
        }

    # Extract tickers from titles
    ticker_counts: Dict[str, int] = {}
    # Match $TICKER or standalone 2-5 uppercase words
    pattern = re.compile(r'\$([A-Z]{1,5})\b|(?<!\w)([A-Z]{2,5})(?!\w)')

    for post in posts:
        text = post["title"]
        matches = pattern.findall(text)
        seen_in_post: set = set()
        for dollar_match, plain_match in matches:
            ticker = dollar_match or plain_match
            if ticker in _TICKER_BLACKLIST or ticker in seen_in_post:
                continue
            seen_in_post.add(ticker)
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

    # Sort by frequency
    sorted_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "subreddit": subreddit,
        "source": "reddit",
        "posts_scanned": len(posts),
        "tickers": [
            {"symbol": t, "mentions": c}
            for t, c in sorted_tickers[:20]
        ],
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def get_social_sentiment_composite(symbol: str) -> Dict[str, Any]:
    """
    Composite sentiment combining Reddit + news sentiment.

    Weights: Reddit 0.3, News 0.7 (news is more reliable).

    Args:
        symbol: Stock ticker.

    Returns:
        Dict with composite_score, composite_label, and component breakdowns.
    """
    # Reddit component
    reddit = get_reddit_sentiment(symbol)
    reddit_score = reddit.get("avg_sentiment", 0)
    reddit_available = reddit.get("source") != "unavailable"

    # News component
    news_score = 0.0
    news_available = False
    try:
        from src.tools.news_fetcher import fetch_company_news
        articles = fetch_company_news(symbol)
        if articles:
            # Filter out sample data
            real_articles = [a for a in articles if not a.get("_is_sample")]
            if real_articles:
                news_sentiments = [_score_text(f"{a.get('title', '')} {a.get('description', '')}") for a in real_articles]
                news_score = sum(news_sentiments) / len(news_sentiments)
                news_available = True
    except Exception as e:
        logger.debug(f"News sentiment fetch failed for {symbol}: {e}")

    # Composite calculation
    if reddit_available and news_available:
        composite = 0.3 * reddit_score + 0.7 * news_score
    elif news_available:
        composite = news_score
    elif reddit_available:
        composite = reddit_score
    else:
        composite = 0.0

    return {
        "symbol": symbol,
        "composite_score": round(composite, 3),
        "composite_label": _sentiment_label(composite),
        "reddit": {
            "available": reddit_available,
            "score": round(reddit_score, 3),
            "label": _sentiment_label(reddit_score),
            "post_count": reddit.get("post_count", 0),
            "weight": 0.3,
        },
        "news": {
            "available": news_available,
            "score": round(news_score, 3),
            "label": _sentiment_label(news_score),
            "weight": 0.7,
        },
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
