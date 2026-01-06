"""
Report Generator Agent for the Financial Research Analyst.

This agent generates comprehensive investment research reports.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from langchain_core.tools import BaseTool, tool
from src.agents.base import BaseAgent
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReportGeneratorAgent(BaseAgent):
    """Agent specialized in generating investment research reports."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="ReportGenerator",
            description="Generates comprehensive investment research reports",
            **kwargs
        )
    
    def _get_default_tools(self) -> List[BaseTool]:
        """Get report generation tools."""
        
        @tool("format_report_section")
        def format_report_section_tool(section_name: str, content: str) -> str:
            """Format a report section with proper headers."""
            separator = "=" * 80
            return f"\n{separator}\n{section_name.upper()}\n{separator}\n{content}\n"
        
        @tool("generate_executive_summary")
        def generate_executive_summary_tool(analysis_data: str) -> str:
            """Generate an executive summary from analysis data."""
            import json
            data = json.loads(analysis_data) if isinstance(analysis_data, str) else analysis_data
            
            symbol = data.get("symbol", "UNKNOWN")
            recommendation = data.get("recommendation", "HOLD")
            confidence = data.get("confidence", 0.5)
            
            return f"""
EXECUTIVE SUMMARY - {symbol}
{'=' * 40}
Recommendation: {recommendation}
Confidence Level: {confidence * 100:.0f}%
Analysis Date: {datetime.utcnow().strftime('%Y-%m-%d')}

Key Findings:
• Technical Analysis: {data.get('technical_summary', 'N/A')}
• Fundamental Analysis: {data.get('fundamental_summary', 'N/A')}
• Sentiment Analysis: {data.get('sentiment_summary', 'N/A')}
• Risk Assessment: {data.get('risk_summary', 'N/A')}
"""
        
        @tool("generate_recommendation")
        def generate_recommendation_tool(scores: str) -> Dict[str, Any]:
            """Generate investment recommendation from scores."""
            import json
            score_data = json.loads(scores) if isinstance(scores, str) else scores
            
            technical = score_data.get("technical", 0.5)
            fundamental = score_data.get("fundamental", 0.5)
            sentiment = score_data.get("sentiment", 0.5)
            risk = score_data.get("risk", 0.5)
            
            weights = {"technical": 0.25, "fundamental": 0.35, "sentiment": 0.20, "risk": 0.20}
            composite = (technical * weights["technical"] + fundamental * weights["fundamental"] +
                        sentiment * weights["sentiment"] + (1 - risk) * weights["risk"])
            
            if composite >= 0.7: recommendation = "STRONG BUY"
            elif composite >= 0.55: recommendation = "BUY"
            elif composite >= 0.45: recommendation = "HOLD"
            elif composite >= 0.3: recommendation = "SELL"
            else: recommendation = "STRONG SELL"
            
            return {"recommendation": recommendation, "confidence": round(composite, 2), "composite_score": round(composite, 2)}
        
        return [format_report_section_tool, generate_executive_summary_tool, generate_recommendation_tool]
    
    def _get_system_prompt(self) -> str:
        return """You are a Report Generator Agent. Create professional investment research reports including:
1. Executive Summary with key findings
2. Detailed analysis sections
3. Investment recommendations with reasoning
4. Risk disclosures and caveats
Use clear, professional language suitable for institutional investors."""
    
    async def generate_report(self, symbol: str, analysis_results: Dict) -> Dict[str, Any]:
        """Generate comprehensive investment report."""
        logger.info(f"Generating report for {symbol}")
        task = f"Generate a comprehensive investment research report for {symbol}."
        result = await self.execute(task)
        return {"symbol": symbol, "report": result.data.get("output", "") if result.success else None}
    
    def create_report_dict(self, symbol: str, analyses: Dict[str, Any]) -> Dict[str, Any]:
        """Create structured report dictionary."""
        return {
            "symbol": symbol,
            "generated_at": datetime.utcnow().isoformat(),
            "technical": analyses.get("technical", {}),
            "fundamental": analyses.get("fundamental", {}),
            "sentiment": analyses.get("sentiment", {}),
            "risk": analyses.get("risk", {}),
            "recommendation": analyses.get("recommendation", {}),
        }
