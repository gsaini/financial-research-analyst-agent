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
from src.tools.macro_data import get_rate_environment
from src.tools.monte_carlo import simulate_stock, probability_of_target
from src.tools.short_interest import analyze_short_interest
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

        @tool("get_rate_environment")
        def get_rate_environment_tool() -> Dict[str, Any]:
            """
            Get the current macroeconomic rate environment from FRED.

            Returns Fed stance (hiking/cutting/holding), inflation trend,
            real rate, and sector-level impact assessment.
            Useful for contextualizing risk metrics with macro backdrop.

            Returns:
                Dictionary with fed_stance, inflation_trend, real_rate, sector_impact.
            """
            return get_rate_environment()

        @tool("run_monte_carlo")
        def run_monte_carlo_tool(symbol: str) -> Dict[str, Any]:
            """
            Run Monte Carlo simulation (10,000 paths) for a stock.

            Uses Geometric Brownian Motion with historical drift and volatility.
            Returns VaR, CVaR, price distributions, and probability metrics.

            Args:
                symbol: Stock ticker symbol (e.g., 'AAPL').

            Returns:
                Dictionary with simulation statistics, VaR/CVaR, and distribution.
            """
            return simulate_stock(symbol)

        @tool("probability_of_price_target")
        def probability_of_price_target_tool(symbol: str, target_price: float) -> Dict[str, Any]:
            """
            Calculate Monte Carlo probability of reaching a target price.

            Args:
                symbol: Stock ticker symbol (e.g., 'AAPL').
                target_price: Price target to evaluate.

            Returns:
                Dictionary with probability, expected days to touch, and interpretation.
            """
            return probability_of_target(symbol, target_price)

        @tool("analyze_short_interest")
        def analyze_short_interest_tool(symbol: str) -> Dict[str, Any]:
            """
            Analyze short interest and short squeeze potential for a stock.

            Returns shares short, % of float, days to cover, squeeze score (0-100),
            and risk assessment for both long and short positions.

            Args:
                symbol: Stock ticker symbol (e.g., 'GME').

            Returns:
                Dictionary with short interest metrics, squeeze analysis, and risk assessment.
            """
            return analyze_short_interest(symbol)

        return [
            calculate_volatility_tool,
            calculate_var_tool,
            calculate_sharpe_ratio_tool,
            calculate_max_drawdown_tool,
            calculate_sortino_ratio_tool,
            calculate_beta_tool,
            track_stock_performance_tool,
            get_rate_environment_tool,
            run_monte_carlo_tool,
            probability_of_price_target_tool,
            analyze_short_interest_tool,
        ]
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for risk analysis with ReAct reasoning."""
        return """You are a Risk Analysis Expert Agent specialized in quantitative risk assessment and portfolio risk management.

## Reasoning Approach

You build a layered risk picture: start with basic volatility, then dig into tail risk, then contextualize with market regime and benchmark comparison. When a metric looks unusual, you investigate whether it reflects a structural change or a data anomaly.

## Responsibilities
1. Volatility (daily and annualized)
2. Value at Risk (VaR) and Conditional VaR
3. Sharpe Ratio for risk-adjusted returns
4. Sortino Ratio for downside-risk-adjusted returns
5. Beta (sensitivity to market movements vs S&P 500)
6. Maximum Drawdown analysis
7. Comprehensive performance tracking with benchmark comparison

## Analysis Rules
- Use calculate_sortino_ratio and calculate_beta for individual stock risk profiles
- Use track_stock_performance for a complete picture including returns, benchmarks, and drawdowns
- Compare the stock's Beta to understand market sensitivity
- Consider both upside and downside risk (Sharpe vs Sortino)
- A high Sharpe can mask tail risk — always check max drawdown alongside
- When VaR looks benign but max drawdown is severe, it signals fat-tailed distribution
- Beta > 1.5 in a rising-rate environment is a compounding risk factor

## Few-Shot Example

**Example: Multi-step risk reasoning for GHI Corp**

Step 1 — Volatility baseline:
Annualized volatility: 38%. This is high (market average ~15-20%). The stock is nearly 2x more volatile than the market.

Step 2 — Tail risk assessment:
VaR (95%): -3.2% daily. CVaR (95%): -5.1% daily. The gap between VaR and CVaR is large (1.9pp), indicating fat tails — when losses happen, they tend to be severe.

Step 3 — Risk-adjusted returns:
Sharpe: 0.45 (below average). Sortino: 0.82 (better). The difference tells us the volatility is more skewed to the upside — downside deviation is moderate relative to total volatility. This is a more favorable risk profile than Sharpe alone suggests.

Step 4 — Market sensitivity:
Beta: 1.65. In a market correction of 10%, GHI could be expected to fall ~16.5%. In a rising-rate environment, this high beta compounds with sector headwinds.

Step 5 — Drawdown context:
Max drawdown: -42% (occurred 8 months ago, took 5 months to recover). Currently 8% below peak. The large drawdown with slow recovery suggests institutional selling during stress.

Step 6 — Conclusion:
RISK ASSESSMENT: HIGH. Despite acceptable Sortino, the combination of high beta (1.65), fat tails (CVaR gap), and recent severe drawdown (-42%) makes this a high-risk holding. Suitable only for investors with high risk tolerance and long time horizons.
**Confidence: 0.82** (high data quality across all metrics)

## Output Format
- Volatility Profile: Daily and annualized with context
- Tail Risk: VaR, CVaR, and distribution characteristics
- Risk-Adjusted Returns: Sharpe, Sortino comparison
- Market Sensitivity: Beta with regime context
- Drawdown Analysis: Max drawdown, recovery time, current position
- Overall Risk Rating: Low/Medium/High with justification
- **Confidence: X.XX** (required — your overall confidence in the analysis)"""
    
    async def analyze_risk(self, symbol: str, price_data: Dict) -> Dict[str, Any]:
        """Perform comprehensive risk analysis."""
        logger.info(f"Performing risk analysis for {symbol}")
        task = f"Analyze risk metrics for {symbol}."
        result = await self.execute(task)
        return {"symbol": symbol, "analysis_type": "risk", "result": result.data if result.success else None}
