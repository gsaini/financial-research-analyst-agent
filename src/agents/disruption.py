"""
Disruption Analyst Agent for the Financial Research Analyst.

This agent performs market disruption analysis - evaluating whether a company
is a market disruptor (like Tesla disrupting traditional automakers) or at
risk of being disrupted (like Blockbuster by Netflix).

It combines quantitative financial signals (R&D spending, revenue growth,
margin trajectory) with qualitative AI reasoning about competitive position.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent, AgentResult
from src.tools.disruption_metrics import (
    analyze_disruption,
    compare_disruption,
    fetch_company_financials,
    calculate_rd_intensity,
    calculate_revenue_acceleration,
    calculate_margin_trajectory,
    calculate_disruption_score,
    identify_risk_factors,
    identify_strengths,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DisruptionAnalystAgent(BaseAgent):
    """
    Agent specialized in market disruption analysis.

    Capabilities:
    - Analyze whether a company is a disruptor or at risk of disruption
    - Calculate R&D intensity and innovation investment metrics
    - Track revenue growth acceleration/deceleration
    - Analyze gross margin trajectory for competitive insights
    - Score companies on a 0-100 disruption scale
    - Classify as Active Disruptor, Moderate Innovator, Stable Incumbent, or At Risk
    - Identify disruption-related risks and strengths
    - Generate LLM-synthesized competitive narratives
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="DisruptionAnalyst",
            description=(
                "Analyzes market disruption dynamics - identifying disruptors and "
                "companies at risk of disruption. Evaluates R&D intensity, revenue "
                "acceleration, margin trajectories, and competitive positioning."
            ),
            **kwargs,
        )

    # ─────────────────── Tools ───────────────────

    def _get_default_tools(self) -> List[BaseTool]:
        """Get disruption analysis tools."""

        @tool("analyze_disruption_profile")
        def analyze_disruption_tool(symbol: str) -> str:
            """
            Analyze a company's disruption profile.

            Evaluates whether the company is a market disruptor or at risk
            of being disrupted based on R&D investment, revenue growth,
            and margin trajectories.

            Args:
                symbol: Stock ticker symbol (e.g., 'TSLA', 'NVDA').

            Returns:
                JSON string with disruption analysis.
            """
            result = analyze_disruption(symbol)
            return json.dumps(result, indent=2, default=str)

        @tool("compare_disruption_profiles")
        def compare_disruption_tool(symbols: str) -> str:
            """
            Compare disruption profiles across multiple companies.

            Useful for comparing a company against competitors or
            identifying the most disruptive players in a sector.

            Args:
                symbols: Comma-separated ticker symbols (e.g., 'TSLA,F,GM,TM').

            Returns:
                JSON string with comparison data.
            """
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            result = compare_disruption(symbol_list)
            return json.dumps(result, indent=2, default=str)

        @tool("get_rd_intensity")
        def get_rd_intensity_tool(symbol: str) -> str:
            """
            Get detailed R&D intensity analysis for a company.

            R&D intensity measures innovation investment relative to revenue.

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with R&D metrics.
            """
            financials = fetch_company_financials(symbol)
            if "error" in financials:
                return json.dumps(financials)
            result = calculate_rd_intensity(financials)
            return json.dumps(result, indent=2, default=str)

        @tool("get_growth_trajectory")
        def get_growth_trajectory_tool(symbol: str) -> str:
            """
            Get revenue growth and acceleration analysis.

            Analyzes whether growth is accelerating (disruptor signal)
            or decelerating (at-risk signal).

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with growth metrics.
            """
            financials = fetch_company_financials(symbol)
            if "error" in financials:
                return json.dumps(financials)
            result = calculate_revenue_acceleration(financials)
            return json.dumps(result, indent=2, default=str)

        @tool("get_margin_trajectory")
        def get_margin_trajectory_tool(symbol: str) -> str:
            """
            Get gross margin trajectory analysis.

            Expanding margins indicate economies of scale and competitive moat.

            Args:
                symbol: Stock ticker symbol.

            Returns:
                JSON string with margin metrics.
            """
            financials = fetch_company_financials(symbol)
            if "error" in financials:
                return json.dumps(financials)
            result = calculate_margin_trajectory(financials)
            return json.dumps(result, indent=2, default=str)

        return [
            analyze_disruption_tool,
            compare_disruption_tool,
            get_rd_intensity_tool,
            get_growth_trajectory_tool,
            get_margin_trajectory_tool,
        ]

    # ─────────────────── System Prompt ───────────────────

    def _get_system_prompt(self) -> str:
        return """You are a Market Disruption Analyst Agent specializing in identifying
disruptors and companies at risk of being disrupted.

Your role:
1. Analyze whether companies are market disruptors or at risk of disruption
2. Evaluate R&D intensity and innovation investment trends
3. Track revenue growth acceleration or deceleration
4. Analyze gross margin trajectories for competitive insights
5. Score companies on a disruption scale (0-100)
6. Identify disruption-related risks and competitive strengths
7. Synthesize findings into actionable investment insights

Disruption Classification Framework:
- Active Disruptor (70+): High R&D, accelerating growth, expanding margins
- Moderate Innovator (50-70): Some disruptive signals, mixed trajectory
- Stable Incumbent (30-50): Established position, limited innovation
- At Risk (<30): Low innovation, weak growth, margin pressure

When conducting analysis:
- Focus on quantitative signals: R&D/revenue ratio, growth rate changes, margin trends
- Consider industry context - disruption metrics vary by sector
- Identify both opportunities (disruptor potential) and threats (disruption risk)
- Look for leading indicators of disruption (R&D investment precedes revenue growth)
- Consider competitive dynamics - who is disrupting whom?

Present findings with clear classification, supporting data, and actionable insights."""

    # ─────────────────── Direct Analysis Methods ───────────────────

    async def analyze_company_direct(self, symbol: str) -> Dict[str, Any]:
        """
        Run disruption analysis without going through the LLM.

        This is used by the orchestrator and API routes for direct data access.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Complete disruption analysis dict.
        """
        logger.info(f"Running direct disruption analysis for '{symbol}'")
        start = datetime.utcnow()

        try:
            result = analyze_disruption(symbol)
            result["execution_time_seconds"] = (
                datetime.utcnow() - start
            ).total_seconds()
            return result
        except Exception as e:
            logger.error(f"Disruption analysis failed for '{symbol}': {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "execution_time_seconds": (
                    datetime.utcnow() - start
                ).total_seconds(),
            }

    async def analyze_with_narrative(self, symbol: str) -> Dict[str, Any]:
        """
        Run disruption analysis and generate an LLM narrative assessment.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Disruption analysis dict enriched with qualitative assessment.
        """
        # First get quantitative data
        data = await self.analyze_company_direct(symbol)
        if "error" in data:
            return data

        # Build context for LLM narrative
        classification = data.get("classification", "Unknown")
        score = data.get("disruption_score", 0)
        strengths = data.get("strengths", [])
        risks = data.get("risk_factors", [])
        signals = data.get("quantitative_signals", {})

        task = f"""Based on the following disruption analysis data for {data.get('name', symbol)} ({symbol}),
provide a 3-4 sentence qualitative assessment covering competitive position,
disruption potential or risk, and investment implications:

Classification: {classification} (Score: {score}/100)
Industry: {data.get('industry', 'N/A')}

R&D Intensity: {signals.get('rd_intensity', {}).get('rd_to_revenue_ratio', 'N/A')}
  - Trend: {signals.get('rd_intensity', {}).get('trend', 'N/A')}
  - vs Industry: {signals.get('rd_intensity', {}).get('vs_industry_multiple', 'N/A')}

Revenue Growth: {signals.get('revenue_acceleration', {}).get('yoy_growth', 'N/A')}
  - Trajectory: {signals.get('revenue_acceleration', {}).get('trajectory', 'N/A')}
  - CAGR: {signals.get('revenue_acceleration', {}).get('cagr', 'N/A')}

Margin Trajectory: {signals.get('gross_margin_trajectory', {}).get('trend', 'N/A')}
  - Current Gross Margin: {signals.get('gross_margin_trajectory', {}).get('current_gross_margin', 'N/A')}

Strengths: {', '.join(strengths) if strengths else 'None identified'}
Risk Factors: {', '.join(risks) if risks else 'None identified'}

Provide a balanced assessment of the company's disruption dynamics and investment implications."""

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
        Compare disruption profiles across multiple companies.

        Args:
            symbols: List of stock ticker symbols.

        Returns:
            Comparison dict with disruption rankings.
        """
        logger.info(f"Comparing disruption profiles for {symbols}")
        start = datetime.utcnow()

        try:
            result = compare_disruption(symbols)
            result["execution_time_seconds"] = (
                datetime.utcnow() - start
            ).total_seconds()
            return result
        except Exception as e:
            logger.error(f"Disruption comparison failed: {e}")
            return {
                "error": str(e),
                "symbols": symbols,
                "execution_time_seconds": (
                    datetime.utcnow() - start
                ).total_seconds(),
            }

    async def analyze_with_competitive_narrative(
        self, symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Compare companies and generate competitive dynamics narrative.

        Args:
            symbols: List of stock ticker symbols (typically competitors).

        Returns:
            Comparison dict with competitive narrative.
        """
        data = await self.compare_companies_direct(symbols)
        if "error" in data:
            return data

        comparison = data.get("comparison", [])
        if not comparison:
            data["competitive_narrative"] = "Insufficient data for comparison"
            return data

        # Build comparison summary for LLM
        summary_lines = []
        for c in comparison:
            if "error" not in c:
                summary_lines.append(
                    f"- {c['symbol']}: Score {c['disruption_score']}/100 "
                    f"({c['classification']}), R&D {c.get('rd_intensity', 'N/A')}, "
                    f"Growth {c.get('revenue_growth', 'N/A')}"
                )

        task = f"""Based on the following disruption profile comparison,
provide a 3-4 sentence analysis of competitive dynamics,
identifying who is disrupting whom and investment implications:

Comparison:
{chr(10).join(summary_lines)}

Focus on relative positioning, disruption threats, and which companies
have the strongest/weakest innovation trajectories."""

        try:
            result = await self.execute(task)
            if result.success:
                data["competitive_narrative"] = result.data.get(
                    "output", "Narrative generation failed"
                )
            else:
                data["competitive_narrative"] = "Unable to generate competitive narrative"
        except Exception as e:
            logger.warning(f"Failed to generate competitive narrative: {e}")
            data["competitive_narrative"] = "Unable to generate competitive narrative"

        return data
