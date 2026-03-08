"""
Options Analyst Agent (Feature 13).

Specialized agent for analyzing options market data, sentiment,
positioning, and unusual volatility/volume signals.
"""

from typing import Any, Dict, List
from src.agents.base import BaseAgent
from src.tools.options_analyzer import analyze_options
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OptionsAnalystAgent(BaseAgent):
    """
    Agent responsible for analyzing options chains, implied volatility,
    put/call ratios, and max pain to determine smart money sentiment.
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="OptionsAnalyst",
            description=(
                "Analyzes options chains, implied volatility, put/call ratios, "
                "and max pain to determine smart money sentiment and positioning."
            ),
            **kwargs,
        )

    def _get_default_tools(self) -> List[Any]:
        """Get the tools available to this agent."""
        return []

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the options agent."""
        return (
            "You are an expert Options Analyst specializing in derivatives, "
            "volatility, and tracking 'smart money' positioning.\n\n"
            "Your goal is to interpret options flow data—including put/call "
            "ratios, implied volatility skew, unusual volume, and max pain—to "
            "determine market sentiment for a given asset.\n\n"
            "Always interpret data objectively, highlighting both bullish and "
            "bearish signals found in the options chain."
        )

    async def analyze(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Run options analysis for the given symbol.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Dict containing options analysis results.
        """
        logger.info(f"[{self.name}] Analyzing options data for {symbol}")
        
        try:
            options_data = analyze_options(symbol)
            
            # Additional LLM-based narrative could be generated here in the future
            return {
                "symbol": symbol,
                "data": options_data,
                "agent_name": self.name
            }
        except Exception as e:
            logger.error(f"[{self.name}] Error analyzing options for {symbol}: {e}")
            return {"error": str(e), "symbol": symbol}
