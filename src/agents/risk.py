"""
Risk Analyst Agent for the Financial Research Analyst.

This agent specializes in risk assessment and portfolio risk management.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import numpy as np
from langchain_core.tools import BaseTool, tool
from src.agents.base import BaseAgent
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
            import json
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
            import json
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
            import json
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
            import json
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
        
        return [calculate_volatility_tool, calculate_var_tool, calculate_sharpe_ratio_tool, calculate_max_drawdown_tool]
    
    def _get_system_prompt(self) -> str:
        return """You are a Risk Analysis Expert Agent. Calculate risk metrics including:
1. Volatility (daily and annualized)
2. Value at Risk (VaR) and Conditional VaR
3. Sharpe Ratio for risk-adjusted returns
4. Maximum Drawdown analysis
Provide clear risk assessments and recommendations."""
    
    async def analyze_risk(self, symbol: str, price_data: Dict) -> Dict[str, Any]:
        """Perform comprehensive risk analysis."""
        logger.info(f"Performing risk analysis for {symbol}")
        task = f"Analyze risk metrics for {symbol}."
        result = await self.execute(task)
        return {"symbol": symbol, "analysis_type": "risk", "result": result.data if result.success else None}
