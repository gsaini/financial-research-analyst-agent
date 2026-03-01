"""
Risk Analyst Agent for the Financial Research Analyst.

This agent specializes in risk assessment and portfolio risk management.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import numpy as np
from langchain_core.tools import BaseTool, tool
from src.agents.base import BaseAgent
from src.tools.performance_tracker import track_performance
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RiskAnalystAgent(BaseAgent):
    """Agent specialized in risk assessment and management."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="RiskAnalyst",
            description="Assesses investment risks and calculates risk metrics",
            **kwargs
        )
    
    def _get_default_tools(self) -> List[BaseTool]:
        """Get risk analysis tools."""
        
        @tool("calculate_volatility")
        def calculate_volatility_tool(returns: str) -> Dict[str, Any]:
            """Calculate historical volatility from returns."""
            return_list = json.loads(returns) if isinstance(returns, str) else returns
            returns_array = np.array(return_list)
            
            daily_vol = np.std(returns_array)
            annual_vol = daily_vol * np.sqrt(252)
            
            return {
                "daily_volatility": round(daily_vol * 100, 2),
                "annual_volatility": round(annual_vol * 100, 2),
                "risk_level": "High" if annual_vol > 0.4 else "Medium" if annual_vol > 0.2 else "Low"
            }
        
        @tool("calculate_var")
        def calculate_var_tool(returns: str, confidence: float = 0.95) -> Dict[str, Any]:
            """Calculate Value at Risk (VaR)."""
            return_list = json.loads(returns) if isinstance(returns, str) else returns
            returns_array = np.array(return_list)
            
            var = np.percentile(returns_array, (1 - confidence) * 100)
            cvar = returns_array[returns_array <= var].mean()
            
            return {
                "var_95": round(var * 100, 2),
                "cvar_95": round(cvar * 100, 2),
                "interpretation": f"95% confidence: max daily loss of {abs(var)*100:.2f}%"
            }
        
        @tool("calculate_sharpe_ratio")
        def calculate_sharpe_ratio_tool(returns: str, risk_free_rate: float = 0.05) -> Dict[str, Any]:
            """Calculate Sharpe Ratio."""
            return_list = json.loads(returns) if isinstance(returns, str) else returns
            returns_array = np.array(return_list)
            
            mean_return = np.mean(returns_array) * 252
            volatility = np.std(returns_array) * np.sqrt(252)
            sharpe = (mean_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            return {
                "sharpe_ratio": round(sharpe, 2),
                "annualized_return": round(mean_return * 100, 2),
                "interpretation": "Excellent" if sharpe > 2 else "Good" if sharpe > 1 else "Average" if sharpe > 0 else "Poor"
            }
        
        @tool("calculate_max_drawdown")
        def calculate_max_drawdown_tool(prices: str) -> Dict[str, Any]:
            """Calculate maximum drawdown."""
            price_list = json.loads(prices) if isinstance(prices, str) else prices
            prices_array = np.array(price_list)
            
            peak = np.maximum.accumulate(prices_array)
            drawdown = (prices_array - peak) / peak
            max_dd = np.min(drawdown)
            
            return {
                "max_drawdown": round(max_dd * 100, 2),
                "current_drawdown": round(drawdown[-1] * 100, 2),
                "risk_assessment": "High Risk" if max_dd < -0.3 else "Moderate Risk" if max_dd < -0.15 else "Low Risk"
            }

        @tool("calculate_sortino_ratio")
        def calculate_sortino_ratio_tool(symbol: str) -> Dict[str, Any]:
            """
            Calculate the Sortino Ratio for a stock.

            Sortino Ratio measures risk-adjusted return using only downside
            deviation (negative returns), making it a better measure than
            Sharpe for asymmetric return distributions.

            Args:
                symbol: Stock ticker symbol (e.g., 'AAPL').

            Returns:
                Dictionary with Sortino ratio value, rating, and interpretation.
            """
            result = track_performance(symbol)
            if "error" in result:
                return result
            metrics = result.get("risk_adjusted_metrics", {})
            sortino = metrics.get("sortino_ratio", 0)
            rating = metrics.get("sortino_rating", "N/A")
            return {
                "symbol": symbol,
                "sortino_ratio": sortino,
                "rating": rating,
                "interpretation": (
                    f"Sortino of {sortino}: {rating}. "
                    "Values above 1.0 indicate good downside-risk-adjusted returns."
                ),
            }

        @tool("calculate_beta")
        def calculate_beta_tool(symbol: str) -> Dict[str, Any]:
            """
            Calculate Beta for a stock (vs S&P 500).

            Beta measures a stock's volatility relative to the market.
            Beta > 1 means more volatile than the market, < 1 means less volatile.

            Args:
                symbol: Stock ticker symbol (e.g., 'AAPL').

            Returns:
                Dictionary with Beta value and interpretation.
            """
            result = track_performance(symbol)
            if "error" in result:
                return result
            metrics = result.get("risk_adjusted_metrics", {})
            beta = metrics.get("beta", None)
            interpretation = metrics.get("beta_interpretation", "Unable to compute")
            return {
                "symbol": symbol,
                "beta": beta,
                "benchmark": "S&P 500 (SPY)",
                "interpretation": interpretation,
            }

        @tool("track_stock_performance")
        def track_stock_performance_tool(symbol: str) -> str:
            """
            Get comprehensive performance tracking for a stock.

            Returns multi-horizon returns (1D to 5Y), benchmark comparison
            (SPY, QQQ, sector ETF), risk-adjusted metrics (Sharpe, Sortino,
            Beta), rolling returns, and drawdown analysis.

            Args:
                symbol: Stock ticker symbol (e.g., 'AAPL').

            Returns:
                JSON string with comprehensive performance data.
            """
            result = track_performance(symbol)
            return json.dumps(result, indent=2, default=str)

        return [
            calculate_volatility_tool,
            calculate_var_tool,
            calculate_sharpe_ratio_tool,
            calculate_max_drawdown_tool,
            calculate_sortino_ratio_tool,
            calculate_beta_tool,
            track_stock_performance_tool,
        ]
    
    def _get_system_prompt(self) -> str:
        return """You are a Risk Analysis Expert Agent. Calculate risk metrics including:
1. Volatility (daily and annualized)
2. Value at Risk (VaR) and Conditional VaR
3. Sharpe Ratio for risk-adjusted returns
4. Sortino Ratio for downside-risk-adjusted returns
5. Beta (sensitivity to market movements vs S&P 500)
6. Maximum Drawdown analysis
7. Comprehensive performance tracking with benchmark comparison

When analyzing risk:
- Use calculate_sortino_ratio and calculate_beta for individual stock risk profiles
- Use track_stock_performance for a complete picture including returns, benchmarks, and drawdowns
- Compare the stock's Beta to understand market sensitivity
- Consider both upside and downside risk (Sharpe vs Sortino)

Provide clear risk assessments and actionable recommendations."""
    
    async def analyze_risk(self, symbol: str, price_data: Dict) -> Dict[str, Any]:
        """Perform comprehensive risk analysis."""
        logger.info(f"Performing risk analysis for {symbol}")
        task = f"Analyze risk metrics for {symbol}."
        result = await self.execute(task)
        return {"symbol": symbol, "analysis_type": "risk", "result": result.data if result.success else None}
