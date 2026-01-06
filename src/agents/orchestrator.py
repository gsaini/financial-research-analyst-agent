"""
Orchestrator Agent for the Financial Research Analyst.

This is the main agent that coordinates all specialized agents and manages the workflow.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
from langchain_core.tools import BaseTool, tool
from src.agents.base import BaseAgent, AgentResult
from src.agents.data_collector import DataCollectorAgent
from src.agents.technical import TechnicalAnalystAgent
from src.agents.fundamental import FundamentalAnalystAgent
from src.agents.sentiment import SentimentAnalystAgent
from src.agents.risk import RiskAnalystAgent
from src.agents.report_generator import ReportGeneratorAgent
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """Main orchestrator that coordinates all specialized agents."""
    
    def __init__(self, **kwargs):
        # Initialize sub-agents
        self.data_collector = DataCollectorAgent()
        self.technical_analyst = TechnicalAnalystAgent()
        self.fundamental_analyst = FundamentalAnalystAgent()
        self.sentiment_analyst = SentimentAnalystAgent()
        self.risk_analyst = RiskAnalystAgent()
        self.report_generator = ReportGeneratorAgent()
        
        super().__init__(
            name="Orchestrator",
            description="Coordinates all agents and manages the analysis workflow",
            **kwargs
        )
    
    def _get_default_tools(self) -> List[BaseTool]:
        """Get orchestration tools."""
        
        @tool("delegate_to_data_collector")
        def delegate_data_collector_tool(symbol: str) -> str:
            """Delegate data collection task to the Data Collector Agent."""
            return f"Delegating data collection for {symbol} to DataCollectorAgent"
        
        @tool("delegate_to_technical_analyst")
        def delegate_technical_tool(symbol: str) -> str:
            """Delegate technical analysis to the Technical Analyst Agent."""
            return f"Delegating technical analysis for {symbol} to TechnicalAnalystAgent"
        
        @tool("delegate_to_fundamental_analyst")
        def delegate_fundamental_tool(symbol: str) -> str:
            """Delegate fundamental analysis to the Fundamental Analyst Agent."""
            return f"Delegating fundamental analysis for {symbol} to FundamentalAnalystAgent"
        
        @tool("coordinate_analysis")
        def coordinate_analysis_tool(symbol: str, analysis_types: str) -> str:
            """Coordinate multiple analysis types for a symbol."""
            return f"Coordinating {analysis_types} analysis for {symbol}"
        
        return [delegate_data_collector_tool, delegate_technical_tool, 
                delegate_fundamental_tool, coordinate_analysis_tool]
    
    def _get_system_prompt(self) -> str:
        return """You are the Orchestrator Agent, the central coordinator for financial analysis.

Your role:
1. Receive analysis requests and decompose them into sub-tasks
2. Delegate tasks to specialized agents
3. Aggregate results from all agents
4. Generate final recommendations

Available agents:
- DataCollectorAgent: Gathers financial data
- TechnicalAnalystAgent: Technical analysis
- FundamentalAnalystAgent: Fundamental analysis
- SentimentAnalystAgent: Sentiment analysis
- RiskAnalystAgent: Risk assessment
- ReportGeneratorAgent: Report creation

Coordinate efficiently and ensure comprehensive analysis."""
    
    async def analyze(self, symbol: str, include_all: bool = True) -> Dict[str, Any]:
        """Run comprehensive analysis on a symbol."""
        logger.info(f"Starting comprehensive analysis for {symbol}")
        start_time = datetime.utcnow()
        results = {"symbol": symbol, "started_at": start_time.isoformat()}
        
        try:
            # Collect data
            data_result = await self.data_collector.collect_comprehensive_data(symbol)
            results["data"] = data_result
            
            # Run analyses in parallel
            tasks = [
                self.technical_analyst.analyze_stock(symbol, data_result.get("data", {})),
                self.fundamental_analyst.analyze_company(symbol, data_result.get("data", {})),
                self.sentiment_analyst.analyze_sentiment(symbol, []),
                self.risk_analyst.analyze_risk(symbol, data_result.get("data", {})),
            ]
            
            analyses = await asyncio.gather(*tasks, return_exceptions=True)
            
            results["technical"] = analyses[0] if not isinstance(analyses[0], Exception) else {"error": str(analyses[0])}
            results["fundamental"] = analyses[1] if not isinstance(analyses[1], Exception) else {"error": str(analyses[1])}
            results["sentiment"] = analyses[2] if not isinstance(analyses[2], Exception) else {"error": str(analyses[2])}
            results["risk"] = analyses[3] if not isinstance(analyses[3], Exception) else {"error": str(analyses[3])}
            
            # Generate report
            report = await self.report_generator.generate_report(symbol, results)
            results["report"] = report
            
            results["completed_at"] = datetime.utcnow().isoformat()
            results["success"] = True
            
        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            results["error"] = str(e)
            results["success"] = False
        
        return results


class FinancialResearchAgent:
    """High-level interface for financial research analysis."""
    
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
    
    def analyze(self, symbol: str) -> Dict[str, Any]:
        """Analyze a single stock symbol."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.orchestrator.analyze(symbol))
    
    def analyze_portfolio(self, symbols: List[str]) -> Dict[str, Any]:
        """Analyze multiple stock symbols."""
        results = {"symbols": symbols, "analyses": []}
        for symbol in symbols:
            results["analyses"].append(self.analyze(symbol))
        return results
    
    def generate_report(self, symbols: List[str], **kwargs) -> str:
        """Generate investment report."""
        analyses = self.analyze_portfolio(symbols)
        return self.orchestrator.report_generator.create_report_dict(
            symbols[0] if len(symbols) == 1 else "Portfolio", 
            analyses
        )
