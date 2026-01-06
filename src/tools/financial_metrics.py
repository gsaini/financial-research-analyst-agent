"""
Financial metrics calculation tools.
"""

from typing import Any, Dict
from src.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_valuation_ratios(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate valuation ratios (P/E, P/B, P/S, EV/EBITDA)."""
    price = data.get("price", data.get("current_price", 0))
    eps = data.get("eps", 0)
    book_value = data.get("book_value_per_share", 0)
    revenue_per_share = data.get("revenue_per_share", 0)
    enterprise_value = data.get("enterprise_value", 0)
    ebitda = data.get("ebitda", 0)
    
    result = {}
    
    # P/E Ratio
    if eps and eps > 0:
        pe = price / eps
        result["pe_ratio"] = round(pe, 2)
        if pe < 15: result["pe_assessment"] = "Undervalued"
        elif pe > 25: result["pe_assessment"] = "Overvalued"
        else: result["pe_assessment"] = "Fairly Valued"
    
    # P/B Ratio
    if book_value and book_value > 0:
        pb = price / book_value
        result["pb_ratio"] = round(pb, 2)
        if pb < 1: result["pb_assessment"] = "Below Book Value"
        elif pb > 3: result["pb_assessment"] = "Premium to Book"
        else: result["pb_assessment"] = "Fair Value"
    
    # P/S Ratio
    if revenue_per_share and revenue_per_share > 0:
        ps = price / revenue_per_share
        result["ps_ratio"] = round(ps, 2)
    
    # EV/EBITDA
    if ebitda and ebitda > 0:
        ev_ebitda = enterprise_value / ebitda
        result["ev_ebitda"] = round(ev_ebitda, 2)
        if ev_ebitda < 10: result["ev_ebitda_assessment"] = "Attractive"
        elif ev_ebitda > 15: result["ev_ebitda_assessment"] = "Expensive"
        else: result["ev_ebitda_assessment"] = "Fair"
    
    return result


def calculate_profitability_ratios(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate profitability ratios (margins, ROE, ROA)."""
    revenue = data.get("revenue", data.get("total_revenue", 0))
    gross_profit = data.get("gross_profit", 0)
    operating_income = data.get("operating_income", 0)
    net_income = data.get("net_income", 0)
    total_assets = data.get("total_assets", 0)
    total_equity = data.get("total_equity", data.get("shareholders_equity", 0))
    
    result = {}
    
    if revenue > 0:
        if gross_profit:
            result["gross_margin"] = round((gross_profit / revenue) * 100, 2)
        if operating_income:
            result["operating_margin"] = round((operating_income / revenue) * 100, 2)
        if net_income:
            result["net_margin"] = round((net_income / revenue) * 100, 2)
    
    if total_assets > 0 and net_income:
        roa = (net_income / total_assets) * 100
        result["roa"] = round(roa, 2)
    
    if total_equity > 0 and net_income:
        roe = (net_income / total_equity) * 100
        result["roe"] = round(roe, 2)
        if roe > 20: result["roe_assessment"] = "Excellent"
        elif roe > 15: result["roe_assessment"] = "Good"
        elif roe > 10: result["roe_assessment"] = "Average"
        else: result["roe_assessment"] = "Below Average"
    
    return result


def calculate_liquidity_ratios(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate liquidity and solvency ratios."""
    current_assets = data.get("current_assets", 0)
    current_liabilities = data.get("current_liabilities", 0)
    cash = data.get("cash", data.get("cash_and_equivalents", 0))
    inventory = data.get("inventory", 0)
    total_debt = data.get("total_debt", 0)
    total_equity = data.get("total_equity", 0)
    ebit = data.get("ebit", data.get("operating_income", 0))
    interest_expense = data.get("interest_expense", 0)
    
    result = {}
    
    # Current Ratio
    if current_liabilities > 0:
        current_ratio = current_assets / current_liabilities
        result["current_ratio"] = round(current_ratio, 2)
        if current_ratio > 2: result["liquidity_status"] = "Strong"
        elif current_ratio > 1: result["liquidity_status"] = "Adequate"
        else: result["liquidity_status"] = "Weak"
    
    # Quick Ratio
    if current_liabilities > 0:
        quick_ratio = (current_assets - inventory) / current_liabilities
        result["quick_ratio"] = round(quick_ratio, 2)
    
    # Cash Ratio
    if current_liabilities > 0 and cash > 0:
        result["cash_ratio"] = round(cash / current_liabilities, 2)
    
    # Debt to Equity
    if total_equity > 0:
        de_ratio = total_debt / total_equity
        result["debt_to_equity"] = round(de_ratio, 2)
        if de_ratio > 2: result["leverage_status"] = "High Leverage"
        elif de_ratio > 1: result["leverage_status"] = "Moderate Leverage"
        else: result["leverage_status"] = "Low Leverage"
    
    # Interest Coverage
    if interest_expense > 0 and ebit > 0:
        interest_coverage = ebit / interest_expense
        result["interest_coverage"] = round(interest_coverage, 2)
    
    return result


def calculate_growth_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate growth metrics from multi-year data."""
    revenues = data.get("revenues", [])
    earnings = data.get("earnings", [])
    eps_history = data.get("eps_history", [])
    
    result = {}
    
    def calc_cagr(values):
        if len(values) < 2 or values[0] <= 0:
            return None
        years = len(values) - 1
        return ((values[-1] / values[0]) ** (1 / years) - 1) * 100
    
    if len(revenues) >= 2:
        yoy = ((revenues[-1] - revenues[-2]) / revenues[-2]) * 100 if revenues[-2] > 0 else 0
        result["revenue_growth_yoy"] = round(yoy, 2)
        if len(revenues) >= 3:
            cagr = calc_cagr(revenues)
            if cagr: result["revenue_cagr"] = round(cagr, 2)
    
    if len(eps_history) >= 2:
        eps_growth = ((eps_history[-1] - eps_history[-2]) / abs(eps_history[-2])) * 100 if eps_history[-2] != 0 else 0
        result["eps_growth_yoy"] = round(eps_growth, 2)
    
    return result


def analyze_financial_health(data: Dict[str, Any]) -> Dict[str, Any]:
    """Comprehensive financial health analysis."""
    valuation = calculate_valuation_ratios(data)
    profitability = calculate_profitability_ratios(data)
    liquidity = calculate_liquidity_ratios(data)
    
    score = 0
    factors = 0
    strengths = []
    weaknesses = []
    
    # Score valuation
    if "pe_ratio" in valuation:
        factors += 1
        if valuation["pe_ratio"] < 20:
            score += 1
            strengths.append("Attractive P/E ratio")
        elif valuation["pe_ratio"] > 30:
            weaknesses.append("High P/E ratio")
    
    # Score profitability
    if "roe" in profitability:
        factors += 1
        if profitability["roe"] > 15:
            score += 1
            strengths.append("Strong return on equity")
        elif profitability["roe"] < 10:
            weaknesses.append("Weak return on equity")
    
    # Score liquidity
    if "current_ratio" in liquidity:
        factors += 1
        if liquidity["current_ratio"] > 1.5:
            score += 1
            strengths.append("Healthy liquidity position")
        elif liquidity["current_ratio"] < 1:
            weaknesses.append("Liquidity concerns")
    
    health_score = (score / factors * 10) if factors > 0 else 5
    
    return {
        "health_score": round(health_score, 1),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "valuation": valuation,
        "profitability": profitability,
        "liquidity": liquidity,
        "overall_assessment": "Strong" if health_score >= 7 else "Moderate" if health_score >= 5 else "Weak"
    }


def compare_to_industry(data: Dict[str, Any], industry: str) -> Dict[str, Any]:
    """Compare company metrics to industry averages."""
    # Industry average benchmarks (simplified)
    benchmarks = {
        "Technology": {"pe_ratio": 25, "roe": 18, "profit_margin": 15},
        "Healthcare": {"pe_ratio": 22, "roe": 15, "profit_margin": 12},
        "Finance": {"pe_ratio": 12, "roe": 12, "profit_margin": 20},
        "Consumer": {"pe_ratio": 18, "roe": 14, "profit_margin": 8},
        "default": {"pe_ratio": 20, "roe": 15, "profit_margin": 10}
    }
    
    benchmark = benchmarks.get(industry, benchmarks["default"])
    comparison = {"industry": industry, "metrics": {}}
    
    pe = data.get("pe_ratio", 0)
    if pe > 0:
        diff = ((pe - benchmark["pe_ratio"]) / benchmark["pe_ratio"]) * 100
        comparison["metrics"]["pe_ratio"] = {
            "company": pe,
            "industry_avg": benchmark["pe_ratio"],
            "difference_pct": round(diff, 1),
            "status": "Above Average" if diff > 10 else "Below Average" if diff < -10 else "Average"
        }
    
    return comparison
