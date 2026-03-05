"""
Sentiment analysis engine for financial news.

Uses FinBERT (ProsusAI/finbert) when transformers is available,
falls back to NLTK VADER with financial-domain lexicon enhancements.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import math

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Financial-domain lexicon additions for VADER
# These capture terms that generic sentiment models often miss
_FINANCIAL_LEXICON = {
    # Positive financial terms
    "beat": 2.0, "beats": 2.0, "exceeded": 2.5, "outperform": 2.5,
    "outperforms": 2.5, "upgrade": 2.0, "upgraded": 2.0, "bullish": 2.5,
    "rally": 2.0, "rallied": 2.0, "surge": 2.5, "surged": 2.5,
    "soar": 2.5, "soared": 2.5, "record": 1.5, "breakout": 2.0,
    "momentum": 1.0, "growth": 1.5, "dividend": 1.0, "buyback": 1.5,
    "rebound": 1.5, "recovery": 1.5, "profitable": 2.0, "earnings": 0.5,
    "revenue": 0.5, "upside": 2.0, "catalyst": 1.5, "innovation": 1.5,
    "tailwind": 1.5, "overweight": 1.5,
    # Negative financial terms
    "miss": -2.0, "missed": -2.0, "misses": -2.0, "downgrade": -2.5,
    "downgraded": -2.5, "bearish": -2.5, "selloff": -2.5, "sell-off": -2.5,
    "crash": -3.0, "plunge": -3.0, "plunged": -3.0, "tank": -2.5,
    "tanked": -2.5, "recession": -2.5, "default": -2.5, "bankruptcy": -3.5,
    "layoff": -2.0, "layoffs": -2.0, "headwind": -1.5, "underperform": -2.0,
    "underweight": -1.5, "overvalued": -1.5, "writedown": -2.0,
    "impairment": -2.0, "shortfall": -2.0, "warning": -1.5,
    "guidance cut": -2.5, "debt": -0.5, "lawsuit": -1.5, "fraud": -3.5,
    "investigation": -2.0, "fine": -1.5, "penalty": -1.5, "recall": -2.0,
}

# Singleton for model caching
_analyzer = None
_analyzer_type = None


def _get_analyzer():
    """Get or initialize the sentiment analyzer (FinBERT or VADER)."""
    global _analyzer, _analyzer_type

    if _analyzer is not None:
        return _analyzer, _analyzer_type

    # Try FinBERT first
    try:
        from transformers import pipeline
        _analyzer = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            top_k=None,
            truncation=True,
            max_length=512,
        )
        _analyzer_type = "finbert"
        logger.info("Sentiment engine initialized with FinBERT")
        return _analyzer, _analyzer_type
    except Exception as e:
        logger.info(f"FinBERT not available ({e}), falling back to VADER")

    # Fallback to VADER with financial lexicon
    try:
        import nltk
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            nltk.download("vader_lexicon", quiet=True)
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        vader = SentimentIntensityAnalyzer()
        # Enhance with financial lexicon
        vader.lexicon.update(_FINANCIAL_LEXICON)
        _analyzer = vader
        _analyzer_type = "vader"
        logger.info("Sentiment engine initialized with VADER (financial-enhanced)")
        return _analyzer, _analyzer_type
    except Exception as e:
        logger.error(f"Failed to initialize any sentiment analyzer: {e}")
        return None, None


def _score_finbert(text: str) -> Dict[str, Any]:
    """Score a single text using FinBERT."""
    analyzer, _ = _get_analyzer()
    results = analyzer(text[:512])

    # FinBERT returns [{'label': 'positive', 'score': 0.92}, ...]
    scores = {r["label"]: r["score"] for r in results[0]}
    pos = scores.get("positive", 0)
    neg = scores.get("negative", 0)
    neu = scores.get("neutral", 0)

    # Composite score: -1 to +1
    composite = pos - neg
    confidence = max(pos, neg, neu)

    if pos > neg and pos > neu:
        label = "Positive"
    elif neg > pos and neg > neu:
        label = "Negative"
    else:
        label = "Neutral"

    return {
        "score": round(composite, 3),
        "label": label,
        "confidence": round(confidence, 3),
        "positive": round(pos, 3),
        "negative": round(neg, 3),
        "neutral": round(neu, 3),
    }


def _score_vader(text: str) -> Dict[str, Any]:
    """Score a single text using VADER with financial enhancements."""
    analyzer, _ = _get_analyzer()
    scores = analyzer.polarity_scores(text)

    compound = scores["compound"]
    pos = scores["pos"]
    neg = scores["neg"]
    neu = scores["neu"]

    if compound >= 0.15:
        label = "Positive"
    elif compound <= -0.15:
        label = "Negative"
    else:
        label = "Neutral"

    # Confidence: how decisive the score is (distance from 0)
    confidence = round(min(abs(compound) * 1.5, 1.0), 3)

    return {
        "score": round(compound, 3),
        "label": label,
        "confidence": confidence,
        "positive": round(pos, 3),
        "negative": round(neg, 3),
        "neutral": round(neu, 3),
    }


def score_text(text: str) -> Dict[str, Any]:
    """Score sentiment of a single text string."""
    if not text or not text.strip():
        return {"score": 0, "label": "Neutral", "confidence": 0}

    _, analyzer_type = _get_analyzer()
    if analyzer_type == "finbert":
        return _score_finbert(text)
    elif analyzer_type == "vader":
        return _score_vader(text)
    else:
        return {"score": 0, "label": "Neutral", "confidence": 0, "engine": "none"}


def analyze_articles(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze sentiment for a list of news articles.

    Each article dict should have at minimum: 'title' and optionally 'description'.
    Returns per-article sentiment and aggregate metrics.
    """
    if not articles:
        return {
            "articles_analyzed": 0,
            "aggregate_sentiment": {"score": 0, "label": "Neutral", "confidence": 0},
            "scored_articles": [],
        }

    _, analyzer_type = _get_analyzer()

    scored = []
    for article in articles:
        title = article.get("title", "")
        desc = article.get("description", "")
        # Combine title + description for richer signal
        text = f"{title}. {desc}".strip() if desc else title

        sentiment = score_text(text)
        scored.append({
            **article,
            "sentiment": sentiment,
        })

    # Compute aggregates
    scores = [a["sentiment"]["score"] for a in scored]
    confidences = [a["sentiment"]["confidence"] for a in scored]

    avg_score = sum(scores) / len(scores)
    avg_confidence = sum(confidences) / len(confidences)

    # Time-weighted score (more recent articles weighted higher)
    tw_score = _time_weighted_score(scored)

    if avg_score >= 0.15:
        agg_label = "Positive"
    elif avg_score <= -0.15:
        agg_label = "Negative"
    else:
        agg_label = "Neutral"

    # Sentiment distribution
    pos_count = sum(1 for s in scores if s >= 0.15)
    neg_count = sum(1 for s in scores if s <= -0.15)
    neu_count = len(scores) - pos_count - neg_count

    # Sort by sentiment for top positive/negative
    sorted_by_sent = sorted(scored, key=lambda x: x["sentiment"]["score"], reverse=True)

    return {
        "engine": analyzer_type or "none",
        "articles_analyzed": len(scored),
        "aggregate_sentiment": {
            "score": round(avg_score, 3),
            "label": agg_label,
            "confidence": round(avg_confidence, 3),
            "time_weighted_score": round(tw_score, 3),
        },
        "distribution": {
            "positive": pos_count,
            "negative": neg_count,
            "neutral": neu_count,
            "positive_pct": round(pos_count / len(scores) * 100, 1),
            "negative_pct": round(neg_count / len(scores) * 100, 1),
            "neutral_pct": round(neu_count / len(scores) * 100, 1),
        },
        "top_positive": sorted_by_sent[:3],
        "top_negative": sorted_by_sent[-3:][::-1] if neg_count > 0 else [],
        "scored_articles": scored,
    }


def _time_weighted_score(scored_articles: List[Dict]) -> float:
    """Compute time-weighted sentiment (recent articles matter more)."""
    now = datetime.now()
    weighted_sum = 0.0
    weight_total = 0.0

    for article in scored_articles:
        pub_str = article.get("published_at", "")
        try:
            if isinstance(pub_str, str) and pub_str:
                pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00").replace("+00:00", ""))
            else:
                pub = now - timedelta(days=3)  # default weight
        except (ValueError, TypeError):
            pub = now - timedelta(days=3)

        hours_ago = max((now - pub).total_seconds() / 3600, 1)
        weight = 1.0 / math.log2(hours_ago + 2)  # logarithmic decay

        weighted_sum += article["sentiment"]["score"] * weight
        weight_total += weight

    return weighted_sum / weight_total if weight_total > 0 else 0
