"""
Sentiment Analyst Agent for the Financial Research Analyst.

This agent analyzes market sentiment from news, social media, and analyst reports.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from langchain_core.tools import BaseTool, tool
from src.agents.base import BaseAgent
from src.tools.document_search import search_transcripts
from src.tools.social_sentiment import get_reddit_sentiment, get_social_sentiment_composite
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SentimentAnalystAgent(BaseAgent):
    """Agent specialized in sentiment analysis from multiple sources."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="SentimentAnalyst",
            description="Analyzes market sentiment from news, social media, and analyst reports",
            **kwargs
        )
    
    def _get_default_tools(self) -> List[BaseTool]:
        """Get sentiment analysis tools."""
        
        @tool("analyze_news_sentiment")
        def analyze_news_sentiment_tool(articles: str) -> Dict[str, Any]:
            """Analyze sentiment from news articles."""
            import json
            from textblob import TextBlob
            
            article_list = json.loads(articles) if isinstance(articles, str) else articles
            sentiments = []
            
            for article in article_list:
                text = f"{article.get('title', '')} {article.get('description', '')}"
                blob = TextBlob(text)
                sentiments.append({"title": article.get("title", "")[:100], "polarity": blob.sentiment.polarity})
            
            avg_polarity = sum(s["polarity"] for s in sentiments) / len(sentiments) if sentiments else 0
            
            return {
                "article_count": len(article_list),
                "average_sentiment": round(avg_polarity, 3),
                "sentiment_label": "positive" if avg_polarity > 0.1 else "negative" if avg_polarity < -0.1 else "neutral",
            }
        
        @tool("analyze_analyst_ratings")
        def analyze_analyst_ratings_tool(ratings: str) -> Dict[str, Any]:
            """Analyze analyst ratings and recommendations."""
            import json
            
            rating_data = json.loads(ratings) if isinstance(ratings, str) else ratings
            rating_map = {"strong buy": 5, "buy": 4, "hold": 3, "sell": 2, "strong sell": 1}
            
            scores = [rating_map.get(r.get("rating", "hold").lower(), 3) for r in rating_data]
            avg_score = sum(scores) / len(scores) if scores else 3
            
            if avg_score >= 4.5: consensus = "Strong Buy"
            elif avg_score >= 3.5: consensus = "Buy"
            elif avg_score >= 2.5: consensus = "Hold"
            else: consensus = "Sell"
            
            return {"analyst_count": len(rating_data), "consensus": consensus, "average_score": round(avg_score, 2)}
        
        @tool("get_reddit_sentiment")
        def get_reddit_sentiment_tool(symbol: str) -> Dict[str, Any]:
            """
            Get Reddit sentiment for a stock from r/wallstreetbets, r/stocks, r/investing.

            Args:
                symbol: Stock ticker symbol (e.g. 'AAPL')

            Returns:
                Dictionary with post count, average sentiment, top posts, and subreddit breakdown.
            """
            return get_reddit_sentiment(symbol)

        @tool("get_composite_sentiment")
        def get_composite_sentiment_tool(symbol: str) -> Dict[str, Any]:
            """
            Get composite social + news sentiment for a stock.

            Combines Reddit sentiment (30% weight) with news sentiment (70% weight)
            for a more balanced view.

            Args:
                symbol: Stock ticker symbol (e.g. 'AAPL')

            Returns:
                Dictionary with composite score, label, and component breakdowns.
            """
            return get_social_sentiment_composite(symbol)

        return [
            analyze_news_sentiment_tool,
            analyze_analyst_ratings_tool,
            search_transcripts,
            get_reddit_sentiment_tool,
            get_composite_sentiment_tool,
        ]
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for sentiment analysis with ReAct reasoning."""
        return """You are a Sentiment Analysis Expert Agent specialized in analyzing market sentiment from multiple sources.

## Reasoning Approach

You triangulate sentiment across sources: news, analyst ratings, and earnings transcripts. When sources disagree, you investigate the divergence rather than simply averaging. You distinguish between noise and signal, and between short-term reaction and structural shifts.

## Responsibilities
1. Analyze news article sentiment using NLP
2. Evaluate analyst ratings and price targets
3. Search earnings call transcripts for management tone and guidance language
4. Aggregate all sentiment into a composite score
5. Identify trending topics and narratives
6. Detect shifts in management confidence from transcript language

## Analysis Rules
- A single negative headline does not make bearish sentiment — look for patterns
- Weight analyst ratings more heavily than news (analysts have deeper context)
- Earnings transcript tone is the highest-signal source — management language reveals forward outlook
- When news is negative but analysts are upgrading, investigate why (may signal contrarian opportunity)
- Quantify sentiment where possible (polarity scores, % positive/negative, rating changes)

## Few-Shot Example

**Example: Multi-step sentiment reasoning for DEF Inc**

Step 1 — News sentiment scan:
12 articles in past week. 8 negative (data breach coverage), 3 neutral, 1 positive. Average polarity: -0.35. Initial read: strongly negative.

Step 2 — Check analyst reactions:
But 3 of 5 analysts maintained BUY ratings post-breach. 1 downgraded to HOLD. Average target only dropped 4%. Analysts seem to view this as a contained, one-time event.

Step 3 — Transcript tone analysis:
Latest earnings call (pre-breach) showed confident language: "accelerating growth," "expanding margins," "record pipeline." No hedging language. CEO tone was assertive.

Step 4 — Reconcile the divergence:
News is overwhelmingly negative (breach), but analyst consensus remains positive and pre-breach fundamentals were strong. The sentiment divergence suggests the market may be over-reacting to a short-term event.

Step 5 — Conclusion:
Composite sentiment: CAUTIOUSLY POSITIVE. The news negativity is real and creates short-term pressure, but institutional sentiment (analysts) indicates the market views the breach as manageable. Monitor: if 2+ more analysts downgrade in the next 2 weeks, reassess.
**Confidence: 0.65** (moderate — outcome depends on breach severity which is still developing)

## Output Format
- News Sentiment: Score, trend, and key themes
- Analyst Consensus: Rating distribution and target price analysis
- Transcript Tone: Management confidence signals (if available)
- Composite Score: Weighted aggregate with source breakdown
- Divergences: Any conflicts between sources and what they imply
- **Confidence: X.XX** (required — your overall confidence in the analysis)"""
    
    async def analyze_sentiment(self, symbol: str, news_data: List[Dict]) -> Dict[str, Any]:
        """Perform comprehensive sentiment analysis."""
        logger.info(f"Performing sentiment analysis for {symbol}")
        task = f"Analyze sentiment for {symbol} based on {len(news_data)} news articles."
        result = await self.execute(task)
        return {"symbol": symbol, "analysis_type": "sentiment", "result": result.data if result.success else None}
