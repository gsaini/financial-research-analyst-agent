"""
News impact analysis - volume tracking, sentiment trends, source diversity,
and news-price correlation for a given stock symbol.
"""

from typing import Any, Dict, List
from datetime import datetime, timedelta
from collections import Counter

from src.utils.logger import get_logger

logger = get_logger(__name__)


def analyze_news_impact(symbol: str) -> Dict[str, Any]:
    """
    Comprehensive news & sentiment impact analysis for a stock.

    Fetches news, runs sentiment scoring, computes volume metrics,
    sentiment trends, source diversity, and news-price correlation.
    """
    symbol = symbol.upper()

    # 1. Fetch news articles
    from src.tools.news_fetcher import fetch_company_news
    articles = fetch_company_news(symbol)

    if not articles:
        return {"symbol": symbol, "error": "No news articles found"}

    # 2. Run sentiment analysis on all articles
    from src.tools.sentiment_engine import analyze_articles
    sentiment_result = analyze_articles(articles)

    # 3. Compute news volume metrics
    volume = _compute_volume_metrics(articles)

    # 4. Compute source diversity
    sources = _compute_source_diversity(articles)

    # 5. Compute sentiment trend (bucket by day)
    trend = _compute_sentiment_trend(sentiment_result.get("scored_articles", []))

    # 6. Topic extraction (simple keyword-based)
    topics = _extract_topics(articles)

    # 7. News-price correlation (basic)
    correlation = _compute_price_correlation(symbol)

    return {
        "symbol": symbol,
        "engine": sentiment_result.get("engine", "unknown"),
        "articles_analyzed": sentiment_result.get("articles_analyzed", 0),
        "aggregate_sentiment": sentiment_result.get("aggregate_sentiment", {}),
        "distribution": sentiment_result.get("distribution", {}),
        "volume": volume,
        "source_diversity": sources,
        "sentiment_trend": trend,
        "topics": topics,
        "news_price_correlation": correlation,
        "top_positive": _slim_articles(sentiment_result.get("top_positive", [])),
        "top_negative": _slim_articles(sentiment_result.get("top_negative", [])),
        "scored_articles": _slim_articles(sentiment_result.get("scored_articles", [])),
    }


def _slim_articles(articles: List[Dict]) -> List[Dict]:
    """Return articles with only essential fields for frontend display."""
    slim = []
    for a in articles:
        slim.append({
            "title": a.get("title", ""),
            "source": a.get("source", ""),
            "published_at": a.get("published_at", ""),
            "url": a.get("url", ""),
            "type": a.get("type", "STORY"),
            "thumbnail": a.get("thumbnail", ""),
            "description": a.get("description", ""),
            "sentiment": a.get("sentiment", {}),
        })
    return slim


def _compute_volume_metrics(articles: List[Dict]) -> Dict[str, Any]:
    """Compute news volume metrics."""
    now = datetime.now()
    count_24h = 0
    count_48h = 0
    count_7d = 0

    for article in articles:
        pub_str = article.get("published_at", "")
        try:
            if isinstance(pub_str, str) and pub_str:
                pub = datetime.fromisoformat(
                    pub_str.replace("Z", "+00:00").replace("+00:00", "")
                )
            else:
                pub = now - timedelta(days=3)
        except (ValueError, TypeError):
            pub = now - timedelta(days=3)

        age = now - pub
        if age <= timedelta(hours=24):
            count_24h += 1
        if age <= timedelta(hours=48):
            count_48h += 1
        if age <= timedelta(days=7):
            count_7d += 1

    total = len(articles)
    avg_daily = round(count_7d / 7, 1) if count_7d > 0 else 0

    # Spike detection
    spike = False
    spike_assessment = "Normal news flow"
    if avg_daily > 0 and count_24h >= avg_daily * 2.5:
        spike = True
        multiplier = round(count_24h / avg_daily, 1)
        spike_assessment = f"{multiplier}x normal volume — significant event coverage"
    elif avg_daily > 0 and count_24h >= avg_daily * 1.5:
        spike = True
        multiplier = round(count_24h / avg_daily, 1)
        spike_assessment = f"{multiplier}x normal volume — elevated interest"

    return {
        "total_articles": total,
        "last_24h": count_24h,
        "last_48h": count_48h,
        "last_7d": count_7d,
        "avg_daily": avg_daily,
        "spike_detected": spike,
        "spike_assessment": spike_assessment,
    }


def _compute_source_diversity(articles: List[Dict]) -> Dict[str, Any]:
    """Analyze source diversity of news coverage."""
    sources = [a.get("source", "Unknown") for a in articles if a.get("source")]
    source_counts = Counter(sources)
    unique = len(source_counts)

    if unique >= 5:
        assessment = "Broad coverage from multiple independent sources"
    elif unique >= 3:
        assessment = "Moderate source diversity"
    elif unique >= 2:
        assessment = "Limited source coverage"
    else:
        assessment = "Single-source coverage — verify independently"

    return {
        "unique_sources": unique,
        "source_breakdown": dict(source_counts.most_common(10)),
        "assessment": assessment,
    }


def _compute_sentiment_trend(scored_articles: List[Dict]) -> Dict[str, Any]:
    """Bucket scored articles by day and show sentiment trend."""
    now = datetime.now()
    buckets = {}  # date_str -> list of scores

    for article in scored_articles:
        pub_str = article.get("published_at", "")
        try:
            if isinstance(pub_str, str) and pub_str:
                pub = datetime.fromisoformat(
                    pub_str.replace("Z", "+00:00").replace("+00:00", "")
                )
            else:
                continue
        except (ValueError, TypeError):
            continue

        date_key = pub.strftime("%Y-%m-%d")
        score = article.get("sentiment", {}).get("score", 0)
        buckets.setdefault(date_key, []).append(score)

    # Compute daily averages
    daily_scores = {}
    for date, scores in sorted(buckets.items()):
        daily_scores[date] = round(sum(scores) / len(scores), 3)

    dates = list(daily_scores.keys())
    values = list(daily_scores.values())

    # Trend direction
    direction = "Stable"
    momentum = "No clear trend"
    if len(values) >= 2:
        recent = values[-1]
        earlier = values[0]
        diff = recent - earlier
        if diff > 0.15:
            direction = "Improving"
            momentum = "Strong positive shift"
        elif diff > 0.05:
            direction = "Improving"
            momentum = "Moderate positive shift"
        elif diff < -0.15:
            direction = "Deteriorating"
            momentum = "Strong negative shift"
        elif diff < -0.05:
            direction = "Deteriorating"
            momentum = "Moderate negative shift"

    return {
        "dates": dates,
        "values": values,
        "direction": direction,
        "momentum": momentum,
    }


def _extract_topics(articles: List[Dict]) -> List[Dict[str, Any]]:
    """Extract common topics/keywords from articles (simple frequency-based)."""
    # Financial topic keywords to look for
    topic_keywords = {
        "earnings": ["earnings", "eps", "revenue", "profit", "quarter", "quarterly"],
        "analyst": ["analyst", "upgrade", "downgrade", "target", "rating", "price target"],
        "product": ["product", "launch", "innovation", "announce", "release", "unveil"],
        "management": ["ceo", "cfo", "executive", "leadership", "resign", "appoint"],
        "market": ["market", "rally", "selloff", "correction", "bull", "bear"],
        "regulation": ["regulation", "sec", "antitrust", "lawsuit", "fine", "compliance"],
        "acquisition": ["acquisition", "merger", "acquire", "deal", "buyout", "takeover"],
        "dividend": ["dividend", "buyback", "repurchase", "payout", "yield"],
        "growth": ["growth", "expand", "expansion", "scale", "opportunity"],
        "risk": ["risk", "concern", "warning", "threat", "challenge", "headwind"],
    }

    all_text = " ".join(
        f"{a.get('title', '')} {a.get('description', '')}" for a in articles
    ).lower()

    topic_scores = []
    for topic, keywords in topic_keywords.items():
        count = sum(all_text.count(kw) for kw in keywords)
        if count > 0:
            topic_scores.append({"topic": topic, "mentions": count})

    topic_scores.sort(key=lambda x: x["mentions"], reverse=True)
    return topic_scores[:6]


def _compute_price_correlation(symbol: str) -> Dict[str, Any]:
    """Basic news-price correlation using recent price moves."""
    try:
        from src.tools.market_data import get_stock_price
        price_data = get_stock_price(symbol)

        if "error" in price_data:
            return {"available": False}

        change_pct = price_data.get("change_percent", 0)
        current = price_data.get("current_price", 0)

        return {
            "available": True,
            "current_price": current,
            "today_change_pct": change_pct,
            "note": "Positive sentiment + positive price action = confirming signal",
        }
    except Exception:
        return {"available": False}
