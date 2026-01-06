"""
Technical Analyst Agent for the Financial Research Analyst.

This agent specializes in technical analysis of stock price data,
identifying patterns, calculating indicators, and generating trading signals.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.tools.technical_indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_bollinger_bands,
    identify_support_resistance,
    detect_patterns,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicatorInput(BaseModel):
    """Input model for technical indicator calculation."""
    prices: List[float] = Field(description="List of closing prices")
    period: int = Field(default=14, description="Calculation period")


class TechnicalAnalystAgent(BaseAgent):
    """
    Agent specialized in technical analysis of financial instruments.
    
    Capabilities:
    - Calculate technical indicators (RSI, MACD, Moving Averages, etc.)
    - Identify chart patterns and trend formations
    - Determine support and resistance levels
    - Generate buy/sell signals based on technical analysis
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="TechnicalAnalyst",
            description="Performs technical analysis on price data to identify trends and generate signals",
            **kwargs
        )
    
    def _get_default_tools(self) -> List[BaseTool]:
        """Get technical analysis tools."""
        
        @tool("calculate_rsi")
        def calculate_rsi_tool(prices: str, period: int = 14) -> Dict[str, Any]:
            """
            Calculate the Relative Strength Index (RSI) for a price series.
            
            Args:
                prices: JSON string of closing prices
                period: RSI calculation period (default: 14)
                
            Returns:
                Dictionary with RSI values and interpretation
            """
            import json
            price_list = json.loads(prices) if isinstance(prices, str) else prices
            return calculate_rsi(price_list, period)
        
        @tool("calculate_macd")
        def calculate_macd_tool(
            prices: str,
            fast_period: int = 12,
            slow_period: int = 26,
            signal_period: int = 9
        ) -> Dict[str, Any]:
            """
            Calculate MACD (Moving Average Convergence Divergence).
            
            Args:
                prices: JSON string of closing prices
                fast_period: Fast EMA period (default: 12)
                slow_period: Slow EMA period (default: 26)
                signal_period: Signal line period (default: 9)
                
            Returns:
                Dictionary with MACD line, signal line, histogram, and interpretation
            """
            import json
            price_list = json.loads(prices) if isinstance(prices, str) else prices
            return calculate_macd(price_list, fast_period, slow_period, signal_period)
        
        @tool("calculate_moving_averages")
        def calculate_moving_averages_tool(
            prices: str,
            periods: str = "[20, 50, 200]"
        ) -> Dict[str, Any]:
            """
            Calculate Simple and Exponential Moving Averages.
            
            Args:
                prices: JSON string of closing prices
                periods: JSON string of periods to calculate (default: [20, 50, 200])
                
            Returns:
                Dictionary with SMA and EMA values for each period
            """
            import json
            price_list = json.loads(prices) if isinstance(prices, str) else prices
            period_list = json.loads(periods) if isinstance(periods, str) else periods
            return calculate_moving_averages(price_list, period_list)
        
        @tool("calculate_bollinger_bands")
        def calculate_bollinger_bands_tool(
            prices: str,
            period: int = 20,
            std_dev: float = 2.0
        ) -> Dict[str, Any]:
            """
            Calculate Bollinger Bands.
            
            Args:
                prices: JSON string of closing prices
                period: Moving average period (default: 20)
                std_dev: Number of standard deviations (default: 2.0)
                
            Returns:
                Dictionary with upper band, middle band, lower band, and bandwidth
            """
            import json
            price_list = json.loads(prices) if isinstance(prices, str) else prices
            return calculate_bollinger_bands(price_list, period, std_dev)
        
        @tool("identify_support_resistance")
        def identify_support_resistance_tool(
            prices: str,
            window: int = 10
        ) -> Dict[str, Any]:
            """
            Identify support and resistance levels.
            
            Args:
                prices: JSON string of price data (highs, lows, closes)
                window: Window size for local extrema detection
                
            Returns:
                Dictionary with support levels, resistance levels, and strength ratings
            """
            import json
            price_data = json.loads(prices) if isinstance(prices, str) else prices
            return identify_support_resistance(price_data, window)
        
        @tool("detect_patterns")
        def detect_patterns_tool(prices: str) -> Dict[str, Any]:
            """
            Detect chart patterns in price data.
            
            Args:
                prices: JSON string of OHLCV price data
                
            Returns:
                Dictionary with detected patterns and their implications
            """
            import json
            price_data = json.loads(prices) if isinstance(prices, str) else prices
            return detect_patterns(price_data)
        
        return [
            calculate_rsi_tool,
            calculate_macd_tool,
            calculate_moving_averages_tool,
            calculate_bollinger_bands_tool,
            identify_support_resistance_tool,
            detect_patterns_tool,
        ]
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for technical analysis."""
        return """You are a Technical Analysis Expert Agent specialized in analyzing price charts 
and technical indicators to identify trading opportunities.

Your responsibilities:
1. Calculate and interpret technical indicators (RSI, MACD, Moving Averages, Bollinger Bands)
2. Identify chart patterns (head and shoulders, double tops/bottoms, triangles, etc.)
3. Determine support and resistance levels
4. Generate trading signals based on technical analysis
5. Assess trend strength and potential reversals

When performing analysis:
- Always consider multiple indicators for confirmation
- Note the timeframe of analysis
- Identify the current trend (bullish, bearish, or neutral)
- Highlight any divergences between price and indicators
- Provide clear buy/sell/hold signals with reasoning

Output Format:
- Trend Assessment: Overall trend direction and strength
- Key Indicators: Values and interpretations of main indicators
- Patterns: Any detected chart patterns
- Support/Resistance: Key price levels
- Signals: Trading recommendations with confidence levels
- Risks: Technical risks and invalidation points"""
    
    async def analyze_stock(
        self,
        symbol: str,
        price_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Perform comprehensive technical analysis on a stock.
        
        Args:
            symbol: Stock ticker symbol
            price_data: Historical price data
            
        Returns:
            Dictionary with technical analysis results
        """
        logger.info(f"Performing technical analysis for {symbol}")
        
        task = f"""Perform a comprehensive technical analysis for {symbol}.

Price Data Summary:
- Current Price: {price_data.get('current_price', 'N/A')}
- 52-Week High: {price_data.get('high_52w', 'N/A')}
- 52-Week Low: {price_data.get('low_52w', 'N/A')}
- Average Volume: {price_data.get('avg_volume', 'N/A')}

Historical Prices (last 30 days closing): {price_data.get('closes', [])[:30]}

Please analyze:
1. Calculate RSI, MACD, and key moving averages
2. Identify the current trend
3. Find support and resistance levels
4. Detect any chart patterns
5. Generate a trading signal with confidence level

Provide a structured technical analysis report."""
        
        result = await self.execute(task)
        
        return {
            "symbol": symbol,
            "analysis_type": "technical",
            "result": result.data if result.success else None,
            "error": result.error if not result.success else None,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    
    def generate_signals(
        self,
        indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate trading signals from technical indicators.
        
        Args:
            indicators: Dictionary of calculated indicators
            
        Returns:
            Dictionary with trading signals and recommendations
        """
        signals = {
            "overall": "NEUTRAL",
            "confidence": 0.0,
            "individual_signals": [],
            "reasoning": [],
        }
        
        bullish_count = 0
        bearish_count = 0
        
        # RSI Signal
        rsi = indicators.get("rsi", {}).get("value", 50)
        if rsi < 30:
            bullish_count += 1
            signals["individual_signals"].append({"indicator": "RSI", "signal": "OVERSOLD - BUY", "value": rsi})
        elif rsi > 70:
            bearish_count += 1
            signals["individual_signals"].append({"indicator": "RSI", "signal": "OVERBOUGHT - SELL", "value": rsi})
        else:
            signals["individual_signals"].append({"indicator": "RSI", "signal": "NEUTRAL", "value": rsi})
        
        # MACD Signal
        macd = indicators.get("macd", {})
        if macd.get("histogram", 0) > 0 and macd.get("crossover") == "bullish":
            bullish_count += 1
            signals["individual_signals"].append({"indicator": "MACD", "signal": "BULLISH CROSSOVER", "value": macd})
        elif macd.get("histogram", 0) < 0 and macd.get("crossover") == "bearish":
            bearish_count += 1
            signals["individual_signals"].append({"indicator": "MACD", "signal": "BEARISH CROSSOVER", "value": macd})
        
        # Moving Average Signal
        ma = indicators.get("moving_averages", {})
        current_price = indicators.get("current_price", 0)
        if current_price > ma.get("sma_200", 0) > 0:
            bullish_count += 1
            signals["individual_signals"].append({"indicator": "SMA 200", "signal": "ABOVE - BULLISH", "value": ma.get("sma_200")})
        elif current_price < ma.get("sma_200", float('inf')):
            bearish_count += 1
            signals["individual_signals"].append({"indicator": "SMA 200", "signal": "BELOW - BEARISH", "value": ma.get("sma_200")})
        
        # Determine overall signal
        total_signals = bullish_count + bearish_count
        if total_signals > 0:
            if bullish_count > bearish_count:
                signals["overall"] = "BUY"
                signals["confidence"] = bullish_count / (total_signals + 1)
            elif bearish_count > bullish_count:
                signals["overall"] = "SELL"
                signals["confidence"] = bearish_count / (total_signals + 1)
        
        return signals
