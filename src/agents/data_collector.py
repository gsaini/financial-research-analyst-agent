"""
Data Collector Agent for the Financial Research Analyst.

This agent is responsible for collecting financial data from various sources
including market data APIs, news feeds, and financial databases.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.tools.market_data import (
    get_stock_price,
    get_historical_data,
    get_company_info,
    get_financial_statements,
)
from src.tools.news_fetcher import fetch_news, fetch_company_news
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StockDataInput(BaseModel):
    """Input model for stock data retrieval."""
    symbol: str = Field(description="Stock ticker symbol (e.g., AAPL, GOOGL)")
    period: str = Field(default="1y", description="Historical data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)")


class NewsInput(BaseModel):
    """Input model for news retrieval."""
    query: str = Field(description="Search query for news articles")
    days_back: int = Field(default=7, description="Number of days to look back for news")


class DataCollectorAgent(BaseAgent):
    """
    Agent specialized in collecting financial data from multiple sources.
    
    Capabilities:
    - Fetch real-time and historical stock prices
    - Retrieve company information and financials
    - Collect news articles and press releases
    - Aggregate data from multiple sources
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="DataCollector",
            description="Collects financial data from various sources including market APIs and news feeds",
            **kwargs
        )
    
    def _get_default_tools(self) -> List[BaseTool]:
        """Get data collection tools."""
        
        @tool("get_stock_price")
        def get_stock_price_tool(symbol: str) -> Dict[str, Any]:
            """
            Get the current stock price and basic info for a symbol.
            
            Args:
                symbol: Stock ticker symbol (e.g., AAPL, GOOGL)
                
            Returns:
                Dictionary with current price, change, volume, and other metrics
            """
            return get_stock_price(symbol)
        
        @tool("get_historical_data")
        def get_historical_data_tool(symbol: str, period: str = "1y") -> Dict[str, Any]:
            """
            Get historical price data for a stock.
            
            Args:
                symbol: Stock ticker symbol
                period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
                
            Returns:
                Dictionary with historical OHLCV data
            """
            return get_historical_data(symbol, period)
        
        @tool("get_company_info")
        def get_company_info_tool(symbol: str) -> Dict[str, Any]:
            """
            Get detailed company information.
            
            Args:
                symbol: Stock ticker symbol
                
            Returns:
                Dictionary with company profile, description, and key metrics
            """
            return get_company_info(symbol)
        
        @tool("get_financial_statements")
        def get_financial_statements_tool(symbol: str) -> Dict[str, Any]:
            """
            Get company financial statements (income, balance sheet, cash flow).
            
            Args:
                symbol: Stock ticker symbol
                
            Returns:
                Dictionary with financial statement data
            """
            return get_financial_statements(symbol)
        
        @tool("fetch_news")
        def fetch_news_tool(query: str, days_back: int = 7) -> List[Dict[str, Any]]:
            """
            Fetch news articles related to a query.
            
            Args:
                query: Search query (company name, ticker, or topic)
                days_back: Number of days to look back
                
            Returns:
                List of news articles with title, description, source, and URL
            """
            return fetch_news(query, days_back)
        
        @tool("fetch_company_news")
        def fetch_company_news_tool(symbol: str) -> List[Dict[str, Any]]:
            """
            Fetch recent news specifically about a company.
            
            Args:
                symbol: Stock ticker symbol
                
            Returns:
                List of company-specific news articles
            """
            return fetch_company_news(symbol)
        
        return [
            get_stock_price_tool,
            get_historical_data_tool,
            get_company_info_tool,
            get_financial_statements_tool,
            fetch_news_tool,
            fetch_company_news_tool,
        ]
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for data collection."""
        return """You are a Financial Data Collector Agent specialized in gathering comprehensive 
financial data from multiple sources.

Your responsibilities:
1. Collect real-time and historical stock price data
2. Retrieve company information and financial statements
3. Gather relevant news articles and press releases
4. Aggregate data from multiple sources for comprehensive coverage

When collecting data:
- Always verify the stock symbol is valid
- Collect data from multiple sources when possible
- Note the timestamp of data for freshness
- Report any data collection errors clearly
- Organize data in a structured format for downstream analysis

Output your findings in a clear, structured format that other agents can easily process.
Include metadata about data sources and collection timestamps."""
    
    async def collect_comprehensive_data(self, symbol: str) -> Dict[str, Any]:
        """
        Collect comprehensive data for a stock symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with all collected data
        """
        logger.info(f"Collecting comprehensive data for {symbol}")
        
        task = f"""Collect comprehensive financial data for {symbol}. 
        
Please gather:
1. Current stock price and basic metrics
2. Historical price data for the past year
3. Company information and profile
4. Financial statements (if available)
5. Recent news articles about the company

Organize all data in a structured format."""
        
        result = await self.execute(task)
        
        if result.success:
            return {
                "symbol": symbol,
                "data": result.data,
                "collected_at": datetime.utcnow().isoformat(),
                "status": "success"
            }
        else:
            return {
                "symbol": symbol,
                "error": result.error,
                "collected_at": datetime.utcnow().isoformat(),
                "status": "failed"
            }
    
    def collect_batch_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Collect data for multiple symbols.
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary with data for all symbols
        """
        import asyncio
        
        async def collect_all():
            tasks = [self.collect_comprehensive_data(symbol) for symbol in symbols]
            return await asyncio.gather(*tasks)
        
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(collect_all())
        
        return {
            "symbols": symbols,
            "results": results,
            "total_collected": len([r for r in results if r.get("status") == "success"]),
            "total_failed": len([r for r in results if r.get("status") == "failed"]),
            "collected_at": datetime.utcnow().isoformat()
        }
