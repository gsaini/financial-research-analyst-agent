"""
Thematic Analyst Agent for the Financial Research Analyst.

This agent performs thematic investing analysis — grouping stocks by investment
themes (e.g., AI, EV, Green Energy) rather than traditional sectors, and
producing comprehensive theme-level insights.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent, AgentResult
from src.tools.theme_mapper import (
    list_available_themes,
    get_theme_definition,
    get_theme_constituents,
    analyze_theme,
    fetch_theme_stock_data,
    calculate_theme_performance,
    calculate_theme_correlation,
    calculate_momentum_score,
    calculate_sector_overlap,
    calculate_theme_health_score,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ThematicAnalystAgent(BaseAgent):
    """
    Agent specialized in thematic investing analysis.

    Capabilities:
    - List and describe available investment themes
    - Analyze a theme's performance across multiple time horizons
    - Compute intra-theme correlation and diversification metrics
    - Identify top performers and laggards within a theme
    - Score theme momentum and overall health
    - Generate an LLM-synthesized outlook narrative
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="ThematicAnalyst",
            description=(
                "Analyzes stocks grouped by investment themes such as AI, "
                "Electric Vehicles, Green Energy, and Cybersecurity. Computes "
                "aggregate performance, momentum, correlation, and risk metrics."
            ),
            **kwargs,
        )

    # ─────────────────── Tools ───────────────────

    def _get_default_tools(self) -> List[BaseTool]:
        """Get thematic analysis tools."""

        @tool("list_themes")
        def list_themes_tool() -> str:
            """
            List all available investment themes with summary information.

            Returns:
                JSON string with theme summaries.
            """
            themes = list_available_themes()
            return json.dumps(themes, indent=2)

        @tool("get_theme_info")
        def get_theme_info_tool(theme_id: str) -> str:
            """
            Get detailed definition for a specific theme.

            Args:
                theme_id: Theme identifier (e.g., 'ai_machine_learning').

            Returns:
                JSON string with theme definition.
            """
            defn = get_theme_definition(theme_id)
            if defn is None:
                return json.dumps({"error": f"Theme '{theme_id}' not found"})
            return json.dumps(defn, indent=2)

        @tool("analyze_investment_theme")
        def analyze_theme_tool(theme_id: str) -> str:
            """
            Run comprehensive thematic analysis on an investment theme.

            Fetches stock data for all constituents, computes performance,
            correlation, momentum, sector overlap, and health score.

            Args:
                theme_id: Theme identifier (e.g., 'ai_machine_learning').

            Returns:
                JSON string with full theme analysis.
            """
            result = analyze_theme(theme_id)
            return json.dumps(result, indent=2, default=str)

        @tool("compare_themes")
        def compare_themes_tool(theme_ids: str) -> str:
            """
            Compare multiple themes side by side.

            Args:
                theme_ids: Comma-separated theme IDs (e.g., 'ai_machine_learning,cybersecurity').

            Returns:
                JSON string with comparison data.
            """
            ids = [t.strip() for t in theme_ids.split(",")]
            comparison = []
            for tid in ids:
                result = analyze_theme(tid)
                if "error" not in result:
                    comparison.append({
                        "theme": result.get("theme"),
                        "theme_id": tid,
                        "performance": result.get("theme_performance", {}),
                        "momentum_score": result.get("momentum_score", 0),
                        "health_score": result.get("theme_health_score", 0),
                        "diversification": result.get("theme_risk", {}).get(
                            "diversification_score", "N/A"
                        ),
                        "intra_correlation": result.get("theme_risk", {}).get(
                            "intra_correlation"
                        ),
                        "top_performers": result.get("top_performers", [])[:2],
                    })
                else:
                    comparison.append({"theme_id": tid, "error": result["error"]})

            return json.dumps(comparison, indent=2, default=str)

        return [
            list_themes_tool,
            get_theme_info_tool,
            analyze_theme_tool,
            compare_themes_tool,
        ]

    # ─────────────────── System Prompt ───────────────────

    def _get_system_prompt(self) -> str:
        return """You are a Thematic Investing Analyst Agent specializing in investment themes
and megatrends.

Your role:
1. Analyze investment themes (e.g., AI, EV, Green Energy, Cybersecurity)
2. Evaluate theme performance across multiple time horizons
3. Assess intra-theme correlation and diversification
4. Identify top performers and laggards within each theme
5. Score theme momentum and overall health
6. Synthesize your findings into a concise investment outlook

When conducting analysis:
- Use the available tools to list themes and run analysis
- Focus on data-driven insights rather than speculation
- Highlight both opportunities and risks
- Consider correlation risk (highly correlated themes offer limited diversification)
- Note any failed data fetches and their impact on analysis quality

Present your findings in a clear, structured format suitable for investment
decision-making. Include a short narrative outlook at the end."""

    # ─────────────────── Direct Analysis Methods ───────────────────

    async def analyze_theme_direct(self, theme_id: str) -> Dict[str, Any]:
        """
        Run thematic analysis without going through the LLM.

        This is used by the orchestrator and API routes for direct data access.

        Args:
            theme_id: Theme identifier.

        Returns:
            Complete theme analysis dict.
        """
        logger.info(f"Running direct thematic analysis for '{theme_id}'")
        start = datetime.utcnow()

        try:
            result = analyze_theme(theme_id)
            result["execution_time_seconds"] = (
                datetime.utcnow() - start
            ).total_seconds()
            return result
        except Exception as e:
            logger.error(f"Thematic analysis failed for '{theme_id}': {e}")
            return {
                "error": str(e),
                "theme_id": theme_id,
                "execution_time_seconds": (
                    datetime.utcnow() - start
                ).total_seconds(),
            }

    async def analyze_with_narrative(self, theme_id: str) -> Dict[str, Any]:
        """
        Run thematic analysis and generate an LLM narrative outlook.

        Args:
            theme_id: Theme identifier.

        Returns:
            Theme analysis dict enriched with an 'outlook' narrative.
        """
        # First get quantitative data
        data = await self.analyze_theme_direct(theme_id)
        if "error" in data:
            return data

        # Ask the LLM to synthesize an outlook
        task = f"""Based on the following thematic analysis data for the 
'{data.get("theme", theme_id)}' investment theme, write a concise 2-3 sentence 
investment outlook:

Performance: {json.dumps(data.get('theme_performance', {}), indent=2)}
Momentum Score: {data.get('momentum_score', 'N/A')}/100
Health Score: {data.get('theme_health_score', 'N/A')}/100
Top Performers: {json.dumps(data.get('top_performers', []), indent=2)}
Laggards: {json.dumps(data.get('laggards', []), indent=2)}
Correlation: {data.get('theme_risk', {}).get('intra_correlation', 'N/A')}
Diversification: {data.get('theme_risk', {}).get('diversification_score', 'N/A')}

Provide a balanced outlook covering momentum, risk, and portfolio implications."""

        try:
            result = await self.execute(task)
            if result.success:
                data["outlook"] = result.data.get("output", "Outlook generation failed")
            else:
                data["outlook"] = "Unable to generate narrative outlook"
        except Exception as e:
            logger.warning(f"Failed to generate narrative: {e}")
            data["outlook"] = "Unable to generate narrative outlook"

        return data

    async def compare_themes_direct(
        self, theme_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare multiple themes side by side.

        Args:
            theme_ids: List of theme identifiers.

        Returns:
            Comparison dict.
        """
        comparison = []
        for tid in theme_ids:
            result = await self.analyze_theme_direct(tid)
            if "error" not in result:
                comparison.append({
                    "theme": result.get("theme"),
                    "theme_id": tid,
                    "performance": result.get("theme_performance", {}),
                    "momentum_score": result.get("momentum_score", 0),
                    "health_score": result.get("theme_health_score", 0),
                    "diversification": result.get("theme_risk", {}).get(
                        "diversification_score", "N/A"
                    ),
                    "intra_correlation": result.get("theme_risk", {}).get(
                        "intra_correlation"
                    ),
                    "top_performers": result.get("top_performers", [])[:2],
                    "laggards": result.get("laggards", [])[:2],
                })
            else:
                comparison.append({"theme_id": tid, "error": result.get("error")})

        return {
            "themes_compared": len(theme_ids),
            "comparison": comparison,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
