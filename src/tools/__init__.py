"""
Tools module for the Financial Research Analyst Agent.
"""

from src.tools.market_data import (
    get_stock_price,
    get_historical_data,
    get_company_info,
    get_financial_statements,
)
from src.tools.news_fetcher import fetch_news, fetch_company_news
from src.tools.technical_indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_bollinger_bands,
    identify_support_resistance,
    detect_patterns,
)
from src.tools.financial_metrics import (
    calculate_valuation_ratios,
    calculate_profitability_ratios,
    calculate_liquidity_ratios,
    calculate_growth_metrics,
    analyze_financial_health,
    compare_to_industry,
)

__all__ = [
    "get_stock_price",
    "get_historical_data",
    "get_company_info",
    "get_financial_statements",
    "fetch_news",
    "fetch_company_news",
    "calculate_rsi",
    "calculate_macd",
    "calculate_moving_averages",
    "calculate_bollinger_bands",
    "identify_support_resistance",
    "detect_patterns",
    "calculate_valuation_ratios",
    "calculate_profitability_ratios",
    "calculate_liquidity_ratios",
    "calculate_growth_metrics",
    "analyze_financial_health",
    "compare_to_industry",
]
