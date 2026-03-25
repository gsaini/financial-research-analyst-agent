from datetime import timezone
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
from src.agents.thematic import ThematicAnalystAgent
from src.agents.disruption import DisruptionAnalystAgent
from src.agents.earnings import EarningsAnalystAgent
from src.agents.options import OptionsAnalystAgent
from src.agents.dividend import DividendAnalystAgent
from src.tools.event_analyzer import analyze_events as run_event_analysis
from src.tools.backtesting_engine import run_backtest as execute_backtest
from src.tools.insight_engine import generate_observations as run_observations
from src.tools.llm_insight_engine import generate_smart_observations
from src.tools.insider_activity import analyze_smart_money as run_smart_money
from src.tools.document_search import ingest_company_filings
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Cross-agent investigation signals ────────────────────────────

def _detect_conflicting_signals(results: Dict[str, Any]) -> List[Dict[str, str]]:
    """Detect contradictions across agent results that warrant deeper investigation.

    Returns a list of dicts with keys: ``conflict``, ``investigation``, ``agents``.
    """
    conflicts: List[Dict[str, str]] = []

    tech = results.get("technical", {})
    fund = results.get("fundamental", {})
    sent = results.get("sentiment", {})
    risk = results.get("risk", {})

    # Extract nested result data (agents wrap output in "result" key)
    tech_data = tech.get("result", {}).get("output", "") if isinstance(tech.get("result"), dict) else ""
    fund_data = fund.get("result", {}).get("output", "") if isinstance(fund.get("result"), dict) else ""

    # 1. Technical bullish but fundamental bearish (or vice versa)
    tech_conf = results.get("confidence_scores", {}).get("technical", 0.5)
    fund_conf = results.get("confidence_scores", {}).get("fundamental", 0.5)
    if tech_conf > 0.6 and fund_conf > 0.6:
        # Check for directional divergence via simple keyword heuristic
        tech_bull = any(w in str(tech_data).lower() for w in ["bullish", "buy", "uptrend", "oversold"])
        tech_bear = any(w in str(tech_data).lower() for w in ["bearish", "sell", "downtrend", "overbought"])
        fund_bull = any(w in str(fund_data).lower() for w in ["undervalued", "strong buy", "buy", "healthy"])
        fund_bear = any(w in str(fund_data).lower() for w in ["overvalued", "sell", "weak", "deteriorating"])

        if tech_bull and fund_bear:
            conflicts.append({
                "conflict": "Technical signals are bullish but fundamentals suggest weakness",
                "investigation": "Check if the technical bounce is a dead-cat bounce or if fundamentals are lagging price action",
                "agents": "technical,fundamental",
            })
        elif tech_bear and fund_bull:
            conflicts.append({
                "conflict": "Fundamentals are strong but technical indicators show weakness",
                "investigation": "Check if the stock is in a temporary pullback within a healthy trend or if technicals are leading a fundamental deterioration",
                "agents": "technical,fundamental",
            })

    # 2. Sentiment divergence from price action
    sent_conf = results.get("confidence_scores", {}).get("sentiment", 0.5)
    if sent_conf > 0.5:
        sent_data = sent.get("result", {}).get("output", "") if isinstance(sent.get("result"), dict) else ""
        sent_negative = any(w in str(sent_data).lower() for w in ["negative", "bearish", "pessimistic"])
        sent_positive = any(w in str(sent_data).lower() for w in ["positive", "bullish", "optimistic"])
        if sent_negative and tech_bull:
            conflicts.append({
                "conflict": "Negative sentiment despite positive price action",
                "investigation": "Check institutional flows — smart money may be accumulating while retail is fearful",
                "agents": "sentiment,technical",
            })

    # 3. Low overall confidence across multiple agents
    low_conf_agents = [
        k for k, v in results.get("confidence_scores", {}).items()
        if v < 0.4
    ]
    if len(low_conf_agents) >= 2:
        conflicts.append({
            "conflict": f"Low confidence across {', '.join(low_conf_agents)}",
            "investigation": "Data quality may be poor or the stock may be in an unusual regime — consider widening the analysis window",
            "agents": ",".join(low_conf_agents),
        })

    return conflicts


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
        self.thematic_analyst = ThematicAnalystAgent()
        self.disruption_analyst = DisruptionAnalystAgent()
        self.earnings_analyst = EarningsAnalystAgent()
        self.dividend_analyst = DividendAnalystAgent()

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
        
        @tool("delegate_to_thematic_analyst")
        def delegate_thematic_tool(theme_id: str) -> str:
            """Delegate thematic investing analysis to the Thematic Analyst Agent."""
            return f"Delegating thematic analysis for theme '{theme_id}' to ThematicAnalystAgent"

        @tool("delegate_to_disruption_analyst")
        def delegate_disruption_tool(symbol: str) -> str:
            """Delegate market disruption analysis to the Disruption Analyst Agent."""
            return f"Delegating disruption analysis for {symbol} to DisruptionAnalystAgent"

        @tool("delegate_to_earnings_analyst")
        def delegate_earnings_tool(symbol: str) -> str:
            """Delegate quarterly earnings analysis to the Earnings Analyst Agent."""
            return f"Delegating earnings analysis for {symbol} to EarningsAnalystAgent"

        @tool("delegate_to_dividend_analyst")
        def delegate_dividend_tool(symbol: str) -> str:
            """Delegate dividend analysis to the Dividend Analyst Agent."""
            return f"Delegating dividend analysis for {symbol} to DividendAnalystAgent"

        return [delegate_data_collector_tool, delegate_technical_tool,
                delegate_fundamental_tool, coordinate_analysis_tool,
                delegate_thematic_tool, delegate_disruption_tool,
                delegate_earnings_tool, delegate_dividend_tool]
    
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
- ThematicAnalystAgent: Thematic investing analysis across investment themes
- DisruptionAnalystAgent: Market disruption analysis (R&D intensity, growth trajectory, disruptor vs at-risk)
- EarningsAnalystAgent: Quarterly earnings analysis (EPS surprises, beat/miss patterns, earnings quality)

Coordinate efficiently and ensure comprehensive analysis."""
    
    async def analyze(self, symbol: str, include_all: bool = True) -> Dict[str, Any]:
        """Run comprehensive analysis on a symbol.

        Pipeline:
        1. Ingest RAG documents (SEC filings) in background
        2. Collect market data
        3. Run all analysis agents in parallel
        4. Cross-agent conflict detection
        5. LLM insight synthesis
        6. Report generation
        """
        logger.info(f"Starting comprehensive analysis for {symbol}")
        start_time = datetime.now(timezone.utc)
        results = {"symbol": symbol, "started_at": start_time.isoformat()}

        try:
            # Step 1: Kick off RAG ingestion concurrently with data collection
            rag_task = asyncio.create_task(self._ingest_rag_documents(symbol))

            # Step 2: Collect data
            data_result = await self.data_collector.collect_comprehensive_data(symbol)
            results["data"] = data_result

            # Wait for RAG ingestion to complete (best-effort)
            rag_status = await rag_task
            results["rag_status"] = rag_status

            # Step 3: Run analyses in parallel
            tasks = [
                self.technical_analyst.analyze_stock(symbol, data_result.get("data", {})),
                self.fundamental_analyst.analyze_company(symbol, data_result.get("data", {})),
                self.sentiment_analyst.analyze_sentiment(symbol, []),
                self.risk_analyst.analyze_risk(symbol, data_result.get("data", {})),
            ]

            analyses = await asyncio.gather(*tasks, return_exceptions=True)

            analysis_keys = ["technical", "fundamental", "sentiment", "risk"]
            confidence_scores = {}
            for i, key in enumerate(analysis_keys):
                if isinstance(analyses[i], Exception):
                    results[key] = {"error": str(analyses[i])}
                    confidence_scores[key] = 0.0
                else:
                    results[key] = analyses[i]
                    # Extract confidence from AgentResult if available
                    if isinstance(analyses[i], dict):
                        conf = analyses[i].get("confidence", 0.5)
                        confidence_scores[key] = conf if isinstance(conf, (int, float)) else 0.5

            results["confidence_scores"] = confidence_scores
            results["overall_confidence"] = (
                sum(confidence_scores.values()) / len(confidence_scores)
                if confidence_scores else 0.0
            )

            # Step 4: Cross-agent conflict detection & investigation
            conflicts = _detect_conflicting_signals(results)
            if conflicts:
                logger.info(
                    f"Detected {len(conflicts)} cross-agent conflicts for {symbol}: "
                    f"{[c['conflict'] for c in conflicts]}"
                )
                results["cross_agent_conflicts"] = conflicts

            # Flag low-confidence analyses
            low_confidence = {k: v for k, v in confidence_scores.items() if v < 0.4}
            if low_confidence:
                logger.warning(
                    f"Low confidence analyses for {symbol}: "
                    f"{', '.join(f'{k}={v:.2f}' for k, v in low_confidence.items())}"
                )
                results["confidence_warnings"] = low_confidence

            # Step 5: Generate LLM-powered insights (includes conflict context)
            try:
                observations = await self.get_observations(
                    symbol, analyses=results, use_llm=True
                )
                results["observations"] = observations
            except Exception as obs_err:
                logger.warning(f"Observation generation failed: {obs_err}")

            # Step 6: Generate report
            report = await self.report_generator.generate_report(symbol, results)
            results["report"] = report

            results["completed_at"] = datetime.now(timezone.utc).isoformat()
            results["success"] = True

        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            results["error"] = str(e)
            results["success"] = False

        return results

    @staticmethod
    async def _ingest_rag_documents(symbol: str) -> Dict[str, Any]:
        """Best-effort ingestion of SEC filings for RAG context."""
        try:
            result = await ingest_company_filings(
                symbol=symbol,
                filing_types=["10-K", "10-Q"],
                max_filings=2,
            )
            logger.info(
                f"RAG ingestion for {symbol}: {result.get('chunks_ingested', 0)} chunks"
            )
            return result
        except Exception as e:
            logger.warning(f"RAG ingestion failed for {symbol}: {e}")
            return {"status": "failed", "error": str(e)}

    async def analyze_theme(self, theme_id: str, include_narrative: bool = False) -> Dict[str, Any]:
        """
        Run thematic investing analysis on a theme.

        Args:
            theme_id: Theme identifier (e.g., 'ai_machine_learning').
            include_narrative: Whether to generate an LLM narrative outlook.

        Returns:
            Theme analysis results dict.
        """
        logger.info(f"Starting thematic analysis for theme '{theme_id}'")
        if include_narrative:
            return await self.thematic_analyst.analyze_with_narrative(theme_id)
        return await self.thematic_analyst.analyze_theme_direct(theme_id)

    async def analyze_disruption(self, symbol: str, include_narrative: bool = False) -> Dict[str, Any]:
        """
        Run market disruption analysis on a company.

        Evaluates whether the company is a market disruptor or at risk of disruption
        based on R&D intensity, revenue acceleration, and margin trajectory.

        Args:
            symbol: Stock ticker symbol (e.g., 'TSLA', 'NVDA').
            include_narrative: Whether to generate an LLM qualitative assessment.

        Returns:
            Disruption analysis results dict.
        """
        logger.info(f"Starting disruption analysis for '{symbol}'")
        if include_narrative:
            return await self.disruption_analyst.analyze_with_narrative(symbol)
        return await self.disruption_analyst.analyze_company_direct(symbol)

    async def compare_disruption(
        self, symbols: List[str], include_narrative: bool = False
    ) -> Dict[str, Any]:
        """
        Compare disruption profiles across multiple companies.

        Args:
            symbols: List of stock ticker symbols.
            include_narrative: Whether to generate competitive dynamics narrative.

        Returns:
            Comparison dict with disruption rankings.
        """
        logger.info(f"Starting disruption comparison for {symbols}")
        if include_narrative:
            return await self.disruption_analyst.analyze_with_competitive_narrative(symbols)
        return await self.disruption_analyst.compare_companies_direct(symbols)

    async def analyze_earnings(self, symbol: str, include_narrative: bool = False) -> Dict[str, Any]:
        """
        Run quarterly earnings analysis on a company.

        Evaluates EPS actual vs estimates, beat/miss patterns,
        quarterly trends, and earnings quality.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT').
            include_narrative: Whether to generate an LLM qualitative assessment.

        Returns:
            Earnings analysis results dict.
        """
        logger.info(f"Starting earnings analysis for '{symbol}'")
        if include_narrative:
            return await self.earnings_analyst.analyze_with_narrative(symbol)
        return await self.earnings_analyst.analyze_company_direct(symbol)

    async def compare_earnings(
        self, symbols: List[str], include_narrative: bool = False
    ) -> Dict[str, Any]:
        """
        Compare earnings profiles across multiple companies.

        Args:
            symbols: List of stock ticker symbols.
            include_narrative: Whether to generate comparative earnings narrative.

        Returns:
            Comparison dict with earnings rankings.
        """
        logger.info(f"Starting earnings comparison for {symbols}")
        if include_narrative:
            return await self.earnings_analyst.analyze_with_comparative_narrative(symbols)
        return await self.earnings_analyst.compare_companies_direct(symbols)

    async def analyze_events(
        self, symbol: str, event_type: str = "earnings"
    ) -> Dict[str, Any]:
        """
        Run event-driven performance analysis on a company.

        Analyzes stock price behaviour in a ±5-day window around
        significant events and identifies repeating patterns.

        Args:
            symbol: Stock ticker symbol.
            event_type: Type of event — "earnings", "dividends", or "splits".

        Returns:
            Event analysis results dict.
        """
        logger.info(f"Starting event analysis for {symbol} ({event_type})")
        return run_event_analysis(symbol, event_type=event_type)

    async def run_backtest(
        self, symbol: str, strategy: str = "rsi_reversal", **kwargs
    ) -> Dict[str, Any]:
        """
        Run a backtesting simulation for a stock.

        Args:
            symbol: Stock ticker symbol.
            strategy: Strategy key from the registry.
            **kwargs: Forwarded to run_backtest (period, initial_capital, etc.).

        Returns:
            Backtest results dict.
        """
        logger.info(f"Starting backtest for {symbol} ({strategy})")
        return execute_backtest(symbol, strategy=strategy, **kwargs)

    async def get_observations(
        self, symbol: str, analyses: Optional[Dict[str, Any]] = None,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate key observations and insights for a stock.

        Args:
            symbol: Stock ticker symbol.
            analyses: Pre-computed analysis results. If None, observation
                      engine will work with empty data.
            use_llm: If True, use LLM-powered insight engine (falls back
                     to rule-based automatically if LLM is unavailable).

        Returns:
            Observations results dict.
        """
        logger.info(f"Generating observations for {symbol} (llm={use_llm})")
        if use_llm:
            return await generate_smart_observations(symbol, analyses or {})
        return run_observations(symbol, analyses or {})

    async def analyze_insider_activity(
        self, symbol: str, days: int = 90,
    ) -> Dict[str, Any]:
        """
        Analyze insider & institutional activity for a stock.

        Args:
            symbol: Stock ticker symbol.
            days: Look-back window for insider transactions.

        Returns:
            Smart money analysis results dict.
        """
        logger.info(f"Analyzing insider activity for {symbol}")
        return run_smart_money(symbol, days=days)

    async def analyze_options(self, symbol: str) -> Dict[str, Any]:
        """
        Run options flow analysis for a stock.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Options analysis results dict.
        """
        logger.info(f"Analyzing options flow for {symbol}")
        agent = OptionsAnalystAgent()
        return await agent.analyze(symbol)

    async def analyze_dividends(
        self, symbol: str, include_narrative: bool = False
    ) -> Dict[str, Any]:
        """
        Run dividend analysis on a company.

        Evaluates dividend yield, safety score, growth history,
        and sustainability for income investors.

        Args:
            symbol: Stock ticker symbol (e.g., 'JNJ', 'PG').
            include_narrative: Whether to generate an LLM qualitative assessment.

        Returns:
            Dividend analysis results dict.
        """
        logger.info(f"Starting dividend analysis for '{symbol}'")
        if include_narrative:
            return await self.dividend_analyst.analyze_with_narrative(symbol)
        return await self.dividend_analyst.analyze_company_direct(symbol)

    async def compare_dividends(
        self, symbols: List[str], include_narrative: bool = False
    ) -> Dict[str, Any]:
        """
        Compare dividend profiles across multiple companies.

        Args:
            symbols: List of stock ticker symbols.
            include_narrative: Whether to generate comparative dividend narrative.

        Returns:
            Comparison dict with dividend rankings.
        """
        logger.info(f"Starting dividend comparison for {symbols}")
        if include_narrative:
            return await self.dividend_analyst.analyze_with_comparative_narrative(symbols)
        return await self.dividend_analyst.compare_companies_direct(symbols)


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
