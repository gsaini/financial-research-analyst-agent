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
from src.tools.peer_comparison import (
    discover_peers,
    compare_peers,
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
    "list_available_themes",
    "get_theme_definition",
    "get_theme_constituents",
    "analyze_theme",
    "fetch_theme_stock_data",
    "calculate_theme_performance",
    "calculate_theme_correlation",
    "calculate_momentum_score",
    "calculate_sector_overlap",
    "calculate_theme_health_score",
    "discover_peers",
    "compare_peers",
]
