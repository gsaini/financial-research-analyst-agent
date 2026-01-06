"""
Fundamental Analyst Agent for the Financial Research Analyst.

This agent specializes in fundamental analysis of companies,
evaluating financial health, valuation, and growth prospects.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.tools.financial_metrics import (
    calculate_valuation_ratios,
    calculate_profitability_ratios,
    calculate_liquidity_ratios,
    calculate_growth_metrics,
    analyze_financial_health,
    compare_to_industry,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FundamentalAnalystAgent(BaseAgent):
    """
    Agent specialized in fundamental analysis of companies.
    
    Capabilities:
    - Analyze financial statements (income, balance sheet, cash flow)
    - Calculate valuation ratios (P/E, P/B, P/S, EV/EBITDA)
    - Assess profitability (ROE, ROA, margins)
    - Evaluate financial health (debt ratios, liquidity)
    - Compare to industry peers
    - Determine intrinsic value
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="FundamentalAnalyst",
            description="Analyzes company financials, calculates ratios, and assesses intrinsic value",
            **kwargs
        )
    
    def _get_default_tools(self) -> List[BaseTool]:
        """Get fundamental analysis tools."""
        
        @tool("calculate_valuation_ratios")
        def calculate_valuation_ratios_tool(financials: str) -> Dict[str, Any]:
            """
            Calculate valuation ratios for a company.
            
            Args:
                financials: JSON string containing financial data (price, earnings, book value, etc.)
                
            Returns:
                Dictionary with P/E, P/B, P/S, EV/EBITDA ratios and interpretations
            """
            import json
            data = json.loads(financials) if isinstance(financials, str) else financials
            return calculate_valuation_ratios(data)
        
        @tool("calculate_profitability_ratios")
        def calculate_profitability_ratios_tool(financials: str) -> Dict[str, Any]:
            """
            Calculate profitability ratios.
            
            Args:
                financials: JSON string containing income statement data
                
            Returns:
                Dictionary with gross margin, operating margin, net margin, ROE, ROA, ROIC
            """
            import json
            data = json.loads(financials) if isinstance(financials, str) else financials
            return calculate_profitability_ratios(data)
        
        @tool("calculate_liquidity_ratios")
        def calculate_liquidity_ratios_tool(financials: str) -> Dict[str, Any]:
            """
            Calculate liquidity and solvency ratios.
            
            Args:
                financials: JSON string containing balance sheet data
                
            Returns:
                Dictionary with current ratio, quick ratio, debt-to-equity, interest coverage
            """
            import json
            data = json.loads(financials) if isinstance(financials, str) else financials
            return calculate_liquidity_ratios(data)
        
        @tool("calculate_growth_metrics")
        def calculate_growth_metrics_tool(financials: str) -> Dict[str, Any]:
            """
            Calculate growth metrics.
            
            Args:
                financials: JSON string containing multi-year financial data
                
            Returns:
                Dictionary with revenue growth, EPS growth, dividend growth rates
            """
            import json
            data = json.loads(financials) if isinstance(financials, str) else financials
            return calculate_growth_metrics(data)
        
        @tool("analyze_financial_health")
        def analyze_financial_health_tool(financials: str) -> Dict[str, Any]:
            """
            Perform comprehensive financial health analysis.
            
            Args:
                financials: JSON string containing complete financial data
                
            Returns:
                Dictionary with overall health score, strengths, weaknesses, and recommendations
            """
            import json
            data = json.loads(financials) if isinstance(financials, str) else financials
            return analyze_financial_health(data)
        
        @tool("compare_to_industry")
        def compare_to_industry_tool(company_data: str, industry: str) -> Dict[str, Any]:
            """
            Compare company metrics to industry averages.
            
            Args:
                company_data: JSON string containing company financial metrics
                industry: Industry name or sector for comparison
                
            Returns:
                Dictionary with comparison results and relative positioning
            """
            import json
            data = json.loads(company_data) if isinstance(company_data, str) else company_data
            return compare_to_industry(data, industry)
        
        return [
            calculate_valuation_ratios_tool,
            calculate_profitability_ratios_tool,
            calculate_liquidity_ratios_tool,
            calculate_growth_metrics_tool,
            analyze_financial_health_tool,
            compare_to_industry_tool,
        ]
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for fundamental analysis."""
        return """You are a Fundamental Analysis Expert Agent specialized in evaluating companies 
based on their financial statements and business metrics.

Your responsibilities:
1. Analyze financial statements (income statement, balance sheet, cash flow statement)
2. Calculate and interpret valuation ratios (P/E, P/B, P/S, EV/EBITDA)
3. Assess profitability metrics (ROE, ROA, profit margins)
4. Evaluate financial health (debt levels, liquidity, solvency)
5. Analyze growth trends and future prospects
6. Compare company metrics to industry peers
7. Determine if a stock is undervalued, fairly valued, or overvalued

When performing analysis:
- Consider both absolute values and trends over time
- Compare ratios to industry averages and historical norms
- Look for red flags in financial statements
- Consider qualitative factors (management, competitive advantages)
- Account for industry-specific metrics

Output Format:
- Valuation Assessment: P/E, P/B, P/S analysis with fair value estimate
- Profitability Analysis: Margin analysis and return metrics
- Financial Health: Balance sheet strength and risk assessment
- Growth Prospects: Revenue and earnings growth outlook
- Competitive Position: Industry comparison and moat analysis
- Investment Thesis: Buy/Hold/Sell recommendation with reasoning
- Key Risks: Factors that could impact the investment thesis"""
    
    async def analyze_company(
        self,
        symbol: str,
        financial_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Perform comprehensive fundamental analysis on a company.
        
        Args:
            symbol: Stock ticker symbol
            financial_data: Company financial data
            
        Returns:
            Dictionary with fundamental analysis results
        """
        logger.info(f"Performing fundamental analysis for {symbol}")
        
        task = f"""Perform a comprehensive fundamental analysis for {symbol}.

Company Information:
- Name: {financial_data.get('name', symbol)}
- Sector: {financial_data.get('sector', 'N/A')}
- Industry: {financial_data.get('industry', 'N/A')}
- Market Cap: ${financial_data.get('market_cap', 0):,.0f}

Financial Metrics:
- Revenue (TTM): ${financial_data.get('revenue', 0):,.0f}
- Net Income (TTM): ${financial_data.get('net_income', 0):,.0f}
- EPS: ${financial_data.get('eps', 0):.2f}
- P/E Ratio: {financial_data.get('pe_ratio', 'N/A')}
- P/B Ratio: {financial_data.get('pb_ratio', 'N/A')}
- Debt/Equity: {financial_data.get('debt_to_equity', 'N/A')}
- ROE: {financial_data.get('roe', 'N/A')}%
- Dividend Yield: {financial_data.get('dividend_yield', 0):.2f}%

Please analyze:
1. Calculate and interpret all key valuation ratios
2. Assess profitability and efficiency
3. Evaluate balance sheet strength
4. Analyze growth trends
5. Compare to industry peers
6. Determine if the stock is undervalued, fairly valued, or overvalued
7. Provide an investment recommendation

Provide a structured fundamental analysis report."""
        
        result = await self.execute(task)
        
        return {
            "symbol": symbol,
            "analysis_type": "fundamental",
            "result": result.data if result.success else None,
            "error": result.error if not result.success else None,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    
    def calculate_intrinsic_value(
        self,
        financial_data: Dict[str, Any],
        method: str = "dcf"
    ) -> Dict[str, Any]:
        """
        Calculate intrinsic value using specified method.
        
        Args:
            financial_data: Company financial data
            method: Valuation method (dcf, ddm, multiples)
            
        Returns:
            Dictionary with intrinsic value and margin of safety
        """
        result = {
            "method": method,
            "intrinsic_value": 0.0,
            "current_price": financial_data.get("current_price", 0),
            "margin_of_safety": 0.0,
            "recommendation": "HOLD",
        }
        
        if method == "dcf":
            # Simplified DCF calculation
            fcf = financial_data.get("free_cash_flow", 0)
            growth_rate = financial_data.get("growth_rate", 0.05)
            discount_rate = 0.10  # WACC assumption
            terminal_growth = 0.02
            shares = financial_data.get("shares_outstanding", 1)
            
            # 10-year projection
            projected_fcf = []
            for year in range(1, 11):
                projected_fcf.append(fcf * ((1 + growth_rate) ** year))
            
            # Discount projected FCFs
            present_value = sum(
                cf / ((1 + discount_rate) ** (i + 1))
                for i, cf in enumerate(projected_fcf)
            )
            
            # Terminal value
            terminal_value = (projected_fcf[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
            present_terminal = terminal_value / ((1 + discount_rate) ** 10)
            
            # Intrinsic value per share
            total_value = present_value + present_terminal
            intrinsic_value = total_value / shares if shares > 0 else 0
            
            result["intrinsic_value"] = round(intrinsic_value, 2)
            
        elif method == "multiples":
            # P/E based valuation
            eps = financial_data.get("eps", 0)
            industry_pe = financial_data.get("industry_pe", 20)
            intrinsic_value = eps * industry_pe
            result["intrinsic_value"] = round(intrinsic_value, 2)
        
        # Calculate margin of safety
        current_price = result["current_price"]
        if current_price > 0 and result["intrinsic_value"] > 0:
            margin = ((result["intrinsic_value"] - current_price) / current_price) * 100
            result["margin_of_safety"] = round(margin, 2)
            
            if margin > 20:
                result["recommendation"] = "STRONG BUY"
            elif margin > 10:
                result["recommendation"] = "BUY"
            elif margin > -10:
                result["recommendation"] = "HOLD"
            elif margin > -20:
                result["recommendation"] = "SELL"
            else:
                result["recommendation"] = "STRONG SELL"
        
        return result
