from datetime import timezone
"""
Dividend Analyst Agent for the Financial Research Analyst.

This agent performs comprehensive dividend analysis for income investors:
- Current dividend yield and payment details
- Dividend safety scoring with payout ratio and FCF coverage
- Dividend growth history and consecutive increase tracking
- Classification (Dividend King, Aristocrat, Champion, Contender)
- Yield comparison vs sector and market benchmarks
- LLM-synthesized income investing narratives
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent, AgentResult
from src.tools.dividend_analyzer import (
    analyze_dividends,
    compare_dividends,
    fetch_dividend_info,
    fetch_dividend_history,
    calculate_dividend_growth,
    calculate_dividend_safety,
    compare_yields,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DividendAnalystAgent(BaseAgent):
    """
    Agent specialized in dividend and income investing analysis.

    Capabilities:
    - Analyze current dividend yield and payment schedules
    - Calculate dividend safety scores (payout ratio, FCF coverage, debt)
    - Track dividend growth history and consecutive increases
    - Classify stocks (Dividend King, Aristocrat, Champion, etc.)
    - Compare yields vs sector and market benchmarks
    - Generate LLM-synthesized income investing narratives
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="DividendAnalyst",
            description=(
                "Analyzes dividend data for income investing - tracking yield, "
                "safety scores, growth history, and sustainability. "
                "Helps identify reliable dividend-paying stocks for income portfolios."
            ),
            **kwargs,
        )

    # ─────────────────── Tools ───────────────────

    def _get_default_tools(self) -> List[BaseTool]:
        """Get dividend analysis tools."""

        @tool("analyze_dividend_profile")
        def analyze_dividend_tool(symbol: str) -> str:
            """
            Analyze a company's dividend profile comprehensively.

            Evaluates yield, safety, growth history, and sustainability.

            Args:
                symbol: Stock ticker symbol (e.g., 'JNJ', 'PG').

            Returns:
                JSON string with dividend analysis.
            """
            result = analyze_dividends(symbol)
            return json.dumps(result, indent=2, default=str)

        @tool("compare_dividend_profiles")
        def compare_dividends_tool(symbols: str) -> str:
            """
            Compare dividend profiles across multiple companies.

            Useful for comparing income investment candidates.

            Args:
                symbols: Comma-separated ticker symbols (e.g., 'JNJ,PG,KO').

            Returns:
                JSON string with comparison data.
            """
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            result = compare_dividends(symbol_list)
            return json.dumps(result, indent=2, default=str)

        @tool("get_dividend_safety")
        def get_dividend_safety_tool(symbol: str) -> str:
            """
            Get detailed dividend safety analysis.

            Calculates safety score based on payout ratio, FCF coverage,
            debt levels, and earnings stability.

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with safety assessment.
            """
            result = calculate_dividend_safety(symbol)
            return json.dumps(result, indent=2, default=str)

        @tool("get_dividend_growth")
        def get_dividend_growth_tool(symbol: str) -> str:
            """
            Get dividend growth history and classification.

            Shows consecutive years of increases and CAGR calculations.

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with growth analysis.
            """
            result = calculate_dividend_growth(symbol)
            return json.dumps(result, indent=2, default=str)

        @tool("get_dividend_history")
        def get_dividend_history_tool(symbol: str) -> str:
            """
            Get historical dividend payments.

            Shows dividend payment history and annual totals.

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with dividend history.
            """
            result = fetch_dividend_history(symbol)
            return json.dumps(result, indent=2, default=str)

        @tool("compare_dividend_yields")
        def compare_yields_tool(symbol: str) -> str:
            """
            Compare a stock's dividend yield to benchmarks.

            Compares yield vs sector average, S&P 500, and Treasury.

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with yield comparison.
            """
            result = compare_yields(symbol)
            return json.dumps(result, indent=2, default=str)

        return [
            analyze_dividend_tool,
            compare_dividends_tool,
            get_dividend_safety_tool,
            get_dividend_growth_tool,
            get_dividend_history_tool,
            compare_yields_tool,
        ]

    # ─────────────────── System Prompt ───────────────────

    def _get_system_prompt(self) -> str:
        return """You are a Dividend Analyst Agent specializing in income investing
and dividend sustainability analysis.

Your role:
1. Analyze dividend yield, payout ratios, and payment schedules
2. Calculate dividend safety scores based on financial health
3. Track dividend growth history and consecutive increase streaks
4. Classify companies by dividend achievement status
5. Compare yields vs sector and market benchmarks
6. Identify red flags that may indicate dividend cut risk
7. Synthesize findings into actionable income investing insights

Dividend Classification Framework:
- Dividend King: 50+ consecutive years of dividend increases
- Dividend Aristocrat: 25+ consecutive years of increases (S&P 500 member)
- Dividend Champion: 10+ consecutive years of increases
- Dividend Contender: 5-9 consecutive years of increases
- Dividend Initiator: Started paying or recently began increasing

Dividend Safety Assessment:
- Very Safe (85-100): Strong coverage, low payout, stable earnings
- Safe (70-84): Good coverage, reasonable payout
- Moderate (55-69): Adequate coverage, some concerns
- Elevated Risk (40-54): Weak coverage or high payout
- High Risk (<40): Dividend cut likely

Key Safety Factors:
- Payout Ratio: Below 60% generally safe, above 80% concerning
- FCF Coverage: Should cover dividend at least 1.5x
- Debt/Equity: Lower leverage supports dividend sustainability
- Earnings Stability: Consistent profits support consistent dividends

When conducting analysis:
- Focus on dividend sustainability, not just yield
- High yields can be a trap (indicating price decline)
- Consider total return (yield + dividend growth)
- Evaluate sector context (utilities have higher yields naturally)
- Track management commitment to dividend policy
- Watch for red flags: earnings declines, debt increases, payout spikes

Present findings with clear safety ratings, growth trends, and income investing implications."""

    # ─────────────────── Direct Analysis Methods ───────────────────

    async def analyze_company_direct(self, symbol: str) -> Dict[str, Any]:
        """
        Run dividend analysis without going through the LLM.

        This is used by the orchestrator and API routes for direct data access.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Complete dividend analysis dict.
        """
        logger.info(f"Running direct dividend analysis for '{symbol}'")
        start = datetime.now(timezone.utc)

        try:
            result = analyze_dividends(symbol)
            result["execution_time_seconds"] = (
                datetime.now(timezone.utc) - start
            ).total_seconds()
            return result
        except Exception as e:
            logger.error(f"Dividend analysis failed for '{symbol}': {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "execution_time_seconds": (
                    datetime.now(timezone.utc) - start
                ).total_seconds(),
            }

    async def analyze_with_narrative(self, symbol: str) -> Dict[str, Any]:
        """
        Run dividend analysis and generate an LLM narrative assessment.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Dividend analysis dict enriched with qualitative assessment.
        """
        # First get quantitative data
        data = await self.analyze_company_direct(symbol)
        if "error" in data:
            return data

        if not data.get("pays_dividends", False):
            data["qualitative_assessment"] = f"{data.get('name', symbol)} does not pay dividends and is not suitable for income-focused portfolios."
            return data

        # Build context for LLM narrative
        current = data.get("current_dividend", {})
        safety = data.get("dividend_safety", {})
        growth = data.get("dividend_growth", {})
        yield_comp = data.get("yield_comparison", {})

        task = f"""Based on the following dividend analysis data for {data.get('name', symbol)} ({symbol}),
provide a 3-4 sentence qualitative assessment covering dividend safety,
growth potential, and suitability for income investors:

Current Dividend:
  - Yield: {current.get('dividend_yield', 'N/A')}%
  - Payout Ratio: {current.get('payout_ratio', 'N/A')}%
  - Frequency: {current.get('frequency', 'N/A')}

Dividend Safety:
  - Safety Score: {safety.get('safety_score', 'N/A')}/100
  - Rating: {safety.get('rating', 'N/A')}
  - Cut Probability: {safety.get('dividend_cut_probability', 'N/A')}
  - Red Flags: {', '.join(safety.get('red_flags', [])) or 'None'}

Dividend Growth:
  - Classification: {growth.get('classification', 'N/A')}
  - Consecutive Years: {growth.get('consecutive_years_increased', 'N/A')}
  - 5-Year CAGR: {growth.get('cagr_5_year', 'N/A')}%

Yield Comparison:
  - vs Sector Average: {yield_comp.get('sector_average', 'N/A')}%
  - vs S&P 500: {yield_comp.get('sp500_average', 'N/A')}%

Provide a balanced assessment of dividend reliability and income investing suitability."""

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
        Compare dividend profiles across multiple companies.

        Args:
            symbols: List of stock ticker symbols.

        Returns:
            Comparison dict with dividend rankings.
        """
        logger.info(f"Comparing dividend profiles for {symbols}")
        start = datetime.now(timezone.utc)

        try:
            result = compare_dividends(symbols)
            result["execution_time_seconds"] = (
                datetime.now(timezone.utc) - start
            ).total_seconds()
            return result
        except Exception as e:
            logger.error(f"Dividend comparison failed: {e}")
            return {
                "error": str(e),
                "symbols": symbols,
                "execution_time_seconds": (
                    datetime.now(timezone.utc) - start
                ).total_seconds(),
            }

    async def analyze_with_comparative_narrative(
        self, symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Compare companies and generate comparative dividend narrative.

        Args:
            symbols: List of stock ticker symbols (typically income candidates).

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
            if "error" not in c and c.get("dividend_yield", 0) > 0:
                summary_lines.append(
                    f"- {c['symbol']}: Yield {c.get('dividend_yield', 'N/A')}%, "
                    f"Safety {c.get('safety_score', 'N/A')}/100, "
                    f"{c.get('classification', 'N/A')}"
                )
            elif c.get("pays_dividends") is False:
                summary_lines.append(f"- {c['symbol']}: No dividend")

        task = f"""Based on the following dividend profile comparison,
provide a 3-4 sentence analysis identifying which companies are best
suited for income investors seeking reliable dividend income:

Comparison:
{chr(10).join(summary_lines)}

Focus on dividend safety, yield, growth history, and which companies
present the best balance of income and sustainability."""

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
