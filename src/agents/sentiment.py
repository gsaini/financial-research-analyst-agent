"""
Sentiment Analyst Agent for the Financial Research Analyst.

This agent analyzes market sentiment from news, social media, and analyst reports.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from langchain_core.tools import BaseTool, tool
from src.agents.base import BaseAgent
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
        
        return [analyze_news_sentiment_tool, analyze_analyst_ratings_tool]
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for sentiment analysis."""
        return """You are a Sentiment Analysis Expert Agent specialized in analyzing market sentiment.

Your responsibilities:
1. Analyze news article sentiment using NLP
2. Evaluate analyst ratings and price targets
3. Aggregate all sentiment into a composite score
4. Identify trending topics and narratives

Output sentiment scores, interpretations, and trading implications."""
    
    async def analyze_sentiment(self, symbol: str, news_data: List[Dict]) -> Dict[str, Any]:
        """Perform comprehensive sentiment analysis."""
        logger.info(f"Performing sentiment analysis for {symbol}")
        task = f"Analyze sentiment for {symbol} based on {len(news_data)} news articles."
        result = await self.execute(task)
        return {"symbol": symbol, "analysis_type": "sentiment", "result": result.data if result.success else None}
