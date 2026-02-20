"""
Earnings Analyst Agent for the Financial Research Analyst.

This agent performs quarterly earnings analysis - tracking EPS actual vs estimates,
beat/miss patterns, quarter-over-quarter and year-over-year trends, and earnings
quality assessment.

It combines quantitative earnings data with qualitative AI reasoning about
earnings sustainability and investor implications.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent, AgentResult
from src.tools.earnings_data import (
    analyze_earnings,
    compare_earnings,
    fetch_quarterly_financials,
    fetch_earnings_history,
    fetch_upcoming_earnings,
    calculate_surprise_pattern,
    calculate_quarterly_trends,
    calculate_yoy_comparison,
    assess_earnings_quality,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EarningsAnalystAgent(BaseAgent):
    """
    Agent specialized in quarterly earnings analysis.

    Capabilities:
    - Track quarterly EPS actuals vs estimates
    - Analyze beat/miss patterns and consistency
    - Calculate quarter-over-quarter and year-over-year trends
    - Assess earnings quality (operational vs one-time)
    - Track upcoming earnings dates and analyst estimates
    - Compare earnings profiles across companies
    - Generate LLM-synthesized earnings narratives
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="EarningsAnalyst",
            description=(
                "Analyzes quarterly earnings data - tracking EPS surprises, "
                "beat/miss patterns, QoQ/YoY trends, and earnings quality. "
                "Helps identify companies with consistent earnings execution."
            ),
            **kwargs,
        )

    # ─────────────────── Tools ───────────────────

    def _get_default_tools(self) -> List[BaseTool]:
        """Get earnings analysis tools."""

        @tool("analyze_earnings_profile")
        def analyze_earnings_tool(symbol: str) -> str:
            """
            Analyze a company's quarterly earnings profile.

            Evaluates EPS actual vs estimates, beat/miss patterns,
            quarterly trends, and earnings quality.

            Args:
                symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT').

            Returns:
                JSON string with earnings analysis.
            """
            result = analyze_earnings(symbol)
            return json.dumps(result, indent=2, default=str)

        @tool("compare_earnings_profiles")
        def compare_earnings_tool(symbols: str) -> str:
            """
            Compare earnings profiles across multiple companies.

            Useful for comparing earnings consistency and quality
            across competitors or sector peers.

            Args:
                symbols: Comma-separated ticker symbols (e.g., 'AAPL,MSFT,GOOGL').

            Returns:
                JSON string with comparison data.
            """
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            result = compare_earnings(symbol_list)
            return json.dumps(result, indent=2, default=str)

        @tool("get_earnings_history")
        def get_earnings_history_tool(symbol: str) -> str:
            """
            Get detailed earnings history with actual vs estimate comparisons.

            Shows historical EPS data with surprise percentages and verdicts.

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with earnings history.
            """
            result = fetch_earnings_history(symbol)
            return json.dumps(result, indent=2, default=str)

        @tool("get_upcoming_earnings")
        def get_upcoming_earnings_tool(symbol: str) -> str:
            """
            Get upcoming earnings date and analyst estimates.

            Returns next earnings date, days until, and analyst forecasts.

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with upcoming earnings info.
            """
            result = fetch_upcoming_earnings(symbol)
            return json.dumps(result, indent=2, default=str)

        @tool("get_quarterly_trends")
        def get_quarterly_trends_tool(symbol: str) -> str:
            """
            Get quarter-over-quarter and year-over-year trend analysis.

            Analyzes revenue and net income trends across quarters.

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with trend analysis.
            """
            financials = fetch_quarterly_financials(symbol)
            if "error" in financials:
                return json.dumps(financials)
            quarters = financials.get("quarters", [])
            trends = calculate_quarterly_trends(quarters)
            yoy = calculate_yoy_comparison(quarters)
            result = {
                "symbol": symbol,
                "quarterly_trends": trends,
                "yoy_comparison": yoy,
            }
            return json.dumps(result, indent=2, default=str)

        @tool("assess_earnings_quality")
        def assess_earnings_quality_tool(symbol: str) -> str:
            """
            Assess the quality of a company's earnings.

            Evaluates whether earnings are driven by operations
            or one-time items, scoring on a 1-10 scale.

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with quality assessment.
            """
            financials = fetch_quarterly_financials(symbol)
            if "error" in financials:
                return json.dumps(financials)
            quarters = financials.get("quarters", [])
            quality = assess_earnings_quality(quarters)
            return json.dumps(
                {"symbol": symbol, "earnings_quality": quality},
                indent=2,
                default=str,
            )

        return [
            analyze_earnings_tool,
            compare_earnings_tool,
            get_earnings_history_tool,
            get_upcoming_earnings_tool,
            get_quarterly_trends_tool,
            assess_earnings_quality_tool,
        ]

    # ─────────────────── System Prompt ───────────────────

    def _get_system_prompt(self) -> str:
        return """You are an Earnings Analyst Agent specializing in quarterly earnings analysis
and earnings quality assessment.

Your role:
1. Track quarterly EPS actuals vs analyst estimates
2. Analyze beat/miss patterns and management guidance accuracy
3. Calculate quarter-over-quarter and year-over-year trends
4. Assess earnings quality (operational vs one-time items)
5. Identify upcoming earnings dates and estimate trends
6. Compare earnings profiles across sector peers
7. Synthesize findings into actionable investment insights

Earnings Pattern Framework:
- Consistent Beater (80%+ beat rate): Management under-promises, reliable execution
- Regular Beater (60-80%): Tends to exceed expectations
- Mixed Results (40-60%): Unpredictable earnings, higher risk
- Regular Misser (20-40%): Tends to disappoint
- Consistent Misser (<20%): Credibility concerns, avoid

Earnings Quality Assessment:
- High Quality (8-10): Driven by operations, sustainable
- Good Quality (6.5-8): Primarily operational with minor concerns
- Average Quality (5-6.5): Some non-operational factors present
- Below Average (3.5-5): Significant non-operational items
- Low Quality (1-3.5): Earnings not reflective of core operations

When conducting analysis:
- Focus on EPS surprise consistency and magnitude
- Consider guidance patterns - conservative vs aggressive
- Analyze revenue-driven vs cost-cutting earnings growth
- Identify margin trends as indicators of competitive position
- Look for red flags: irregular one-time items, accounting changes
- Consider seasonality in quarterly patterns

Present findings with clear patterns, supporting data, and investment implications."""

    # ─────────────────── Direct Analysis Methods ───────────────────

    async def analyze_company_direct(self, symbol: str) -> Dict[str, Any]:
        """
        Run earnings analysis without going through the LLM.

        This is used by the orchestrator and API routes for direct data access.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Complete earnings analysis dict.
        """
        logger.info(f"Running direct earnings analysis for '{symbol}'")
        start = datetime.utcnow()

        try:
            result = analyze_earnings(symbol)
            result["execution_time_seconds"] = (
                datetime.utcnow() - start
            ).total_seconds()
            return result
        except Exception as e:
            logger.error(f"Earnings analysis failed for '{symbol}': {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "execution_time_seconds": (
                    datetime.utcnow() - start
                ).total_seconds(),
            }

    async def analyze_with_narrative(self, symbol: str) -> Dict[str, Any]:
        """
        Run earnings analysis and generate an LLM narrative assessment.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Earnings analysis dict enriched with qualitative assessment.
        """
        # First get quantitative data
        data = await self.analyze_company_direct(symbol)
        if "error" in data:
            return data

        # Build context for LLM narrative
        surprise_history = data.get("earnings_surprise_history", {}).get("last_8_quarters", {})
        trends = data.get("quarterly_trends", {})
        quality = data.get("earnings_quality", {})
        next_earnings = data.get("next_earnings", {})

        task = f"""Based on the following earnings analysis data for {data.get('name', symbol)} ({symbol}),
provide a 3-4 sentence qualitative assessment covering earnings consistency,
quality, and investor implications:

Beat/Miss Pattern: {surprise_history.get('beat_rate', 'N/A')} beat rate
  - Pattern: {surprise_history.get('pattern', 'N/A')}
  - Average Surprise: {surprise_history.get('average_surprise', 'N/A')}

Revenue Trend: {trends.get('revenue_trend', 'N/A')}
Income Trend: {trends.get('income_trend', 'N/A')}
Margin Trajectory: {trends.get('margin_trajectory', 'N/A')}

Earnings Quality Score: {quality.get('score', 'N/A')}/10
  - Assessment: {quality.get('assessment', 'N/A')}

Next Earnings: {next_earnings.get('date', 'N/A')} ({next_earnings.get('days_until', 'N/A')} days away)

Provide a balanced assessment of earnings reliability and investment implications."""

        try:
            result = await self.execute(task)
            if result.success:
                data["qualitative_assessment"] = result.data.get(
                    "output", "Assessment generation failed"
                )
            else:
                data["qualitative_assessment"] = "Unable to generate qualitative assessment"
        except Exception as e:
            logger.warning(f"Failed to generate narrative: {e}")
            data["qualitative_assessment"] = "Unable to generate qualitative assessment"

        return data

    async def compare_companies_direct(
        self, symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Compare earnings profiles across multiple companies.

        Args:
            symbols: List of stock ticker symbols.

        Returns:
            Comparison dict with earnings rankings.
        """
        logger.info(f"Comparing earnings profiles for {symbols}")
        start = datetime.utcnow()

        try:
            result = compare_earnings(symbols)
            result["execution_time_seconds"] = (
                datetime.utcnow() - start
            ).total_seconds()
            return result
        except Exception as e:
            logger.error(f"Earnings comparison failed: {e}")
            return {
                "error": str(e),
                "symbols": symbols,
                "execution_time_seconds": (
                    datetime.utcnow() - start
                ).total_seconds(),
            }

    async def analyze_with_comparative_narrative(
        self, symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Compare companies and generate comparative earnings narrative.

        Args:
            symbols: List of stock ticker symbols (typically competitors).

        Returns:
            Comparison dict with comparative narrative.
        """
        data = await self.compare_companies_direct(symbols)
        if "error" in data:
            return data

        comparison = data.get("comparison", [])
        if not comparison:
            data["comparative_narrative"] = "Insufficient data for comparison"
            return data

        # Build comparison summary for LLM
        summary_lines = []
        for c in comparison:
            if "error" not in c:
                summary_lines.append(
                    f"- {c['symbol']}: Beat Rate {c.get('beat_rate', 'N/A')}, "
                    f"Quality Score {c.get('earnings_quality_score', 'N/A')}/10, "
                    f"Pattern: {c.get('pattern', 'N/A')}"
                )

        task = f"""Based on the following earnings profile comparison,
provide a 3-4 sentence analysis of relative earnings quality,
identifying which companies have the most reliable earnings:

Comparison:
{chr(10).join(summary_lines)}

Focus on earnings consistency, quality scores, and which companies
present the best risk-adjusted earnings profile for investors."""

        try:
            result = await self.execute(task)
            if result.success:
                data["comparative_narrative"] = result.data.get(
                    "output", "Narrative generation failed"
                )
            else:
                data["comparative_narrative"] = "Unable to generate comparative narrative"
        except Exception as e:
            logger.warning(f"Failed to generate comparative narrative: {e}")
            data["comparative_narrative"] = "Unable to generate comparative narrative"

        return data
