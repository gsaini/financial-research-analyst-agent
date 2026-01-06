"""
Market data tools for fetching financial data from various sources.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json

import yfinance as yf
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_stock_price(symbol: str) -> Dict[str, Any]:
    """
    Get current stock price and basic metrics.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Dictionary with current price data
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        return {
            "symbol": symbol,
            "current_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "previous_close": info.get("previousClose", 0),
            "open": info.get("open", info.get("regularMarketOpen", 0)),
            "day_high": info.get("dayHigh", info.get("regularMarketDayHigh", 0)),
            "day_low": info.get("dayLow", info.get("regularMarketDayLow", 0)),
            "volume": info.get("volume", info.get("regularMarketVolume", 0)),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", None),
            "eps": info.get("trailingEps", None),
            "52_week_high": info.get("fiftyTwoWeekHigh", 0),
            "52_week_low": info.get("fiftyTwoWeekLow", 0),
            "change": round(info.get("currentPrice", 0) - info.get("previousClose", 0), 2),
            "change_percent": round(
                ((info.get("currentPrice", 0) - info.get("previousClose", 1)) / 
                 info.get("previousClose", 1)) * 100, 2
            ) if info.get("previousClose", 0) > 0 else 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching stock price for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def get_historical_data(symbol: str, period: str = "1y") -> Dict[str, Any]:
    """
    Get historical price data for a stock.
    
    Args:
        symbol: Stock ticker symbol
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        
    Returns:
        Dictionary with historical OHLCV data
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return {"symbol": symbol, "error": "No historical data available"}
        
        return {
            "symbol": symbol,
            "period": period,
            "data_points": len(hist),
            "start_date": hist.index[0].strftime("%Y-%m-%d"),
            "end_date": hist.index[-1].strftime("%Y-%m-%d"),
            "opens": hist["Open"].tolist(),
            "highs": hist["High"].tolist(),
            "lows": hist["Low"].tolist(),
            "closes": hist["Close"].tolist(),
            "volumes": hist["Volume"].tolist(),
            "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
            "returns": hist["Close"].pct_change().dropna().tolist(),
        }
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def get_company_info(symbol: str) -> Dict[str, Any]:
    """
    Get detailed company information.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Dictionary with company profile
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        return {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "description": info.get("longBusinessSummary", "")[:500],
            "website": info.get("website", ""),
            "employees": info.get("fullTimeEmployees", 0),
            "country": info.get("country", ""),
            "city": info.get("city", ""),
            "exchange": info.get("exchange", ""),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap", 0),
            "enterprise_value": info.get("enterpriseValue", 0),
        }
    except Exception as e:
        logger.error(f"Error fetching company info for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def get_financial_statements(symbol: str) -> Dict[str, Any]:
    """
    Get company financial statements.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Dictionary with financial statement data
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # Get financial statements
        income_stmt = ticker.income_stmt
        balance_sheet = ticker.balance_sheet
        cash_flow = ticker.cashflow
        
        result = {"symbol": symbol}
        
        # Income statement metrics
        if not income_stmt.empty:
            latest = income_stmt.iloc[:, 0]
            result["income_statement"] = {
                "total_revenue": float(latest.get("Total Revenue", 0)),
                "gross_profit": float(latest.get("Gross Profit", 0)),
                "operating_income": float(latest.get("Operating Income", 0)),
                "net_income": float(latest.get("Net Income", 0)),
                "ebitda": float(latest.get("EBITDA", 0)),
            }
        
        # Balance sheet metrics
        if not balance_sheet.empty:
            latest = balance_sheet.iloc[:, 0]
            result["balance_sheet"] = {
                "total_assets": float(latest.get("Total Assets", 0)),
                "total_liabilities": float(latest.get("Total Liabilities Net Minority Interest", 0)),
                "total_equity": float(latest.get("Total Equity Gross Minority Interest", 0)),
                "cash": float(latest.get("Cash And Cash Equivalents", 0)),
                "total_debt": float(latest.get("Total Debt", 0)),
            }
        
        # Cash flow metrics
        if not cash_flow.empty:
            latest = cash_flow.iloc[:, 0]
            result["cash_flow"] = {
                "operating_cash_flow": float(latest.get("Operating Cash Flow", 0)),
                "capital_expenditure": float(latest.get("Capital Expenditure", 0)),
                "free_cash_flow": float(latest.get("Free Cash Flow", 0)),
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching financial statements for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}
