"""
Dividend Analysis Tools for Income Investing (Feature 15).

This module provides tools to fetch and analyze dividend data:
- Current dividend yield and payment details
- Dividend safety scoring (payout ratio, FCF coverage, debt levels)
- Dividend growth history and CAGR calculations
- Consecutive years of dividend increases (King/Aristocrat/Champion classification)
- Upcoming ex-dividend and payment dates
- Yield comparison vs sector and market averages
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

import yfinance as yf
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Dividend Data Fetching
# ─────────────────────────────────────────────────────────────


def fetch_dividend_info(symbol: str) -> Dict[str, Any]:
    """
    Fetch current dividend information from yfinance.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with dividend details.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Get dividend data
        annual_dividend = info.get("dividendRate", 0) or 0
        dividend_yield = info.get("dividendYield", 0) or 0
        ex_dividend_date = info.get("exDividendDate")
        payout_ratio = info.get("payoutRatio", 0) or 0

        # Convert ex-dividend date from timestamp
        ex_date_str = None
        if ex_dividend_date:
            try:
                if isinstance(ex_dividend_date, (int, float)):
                    ex_date_str = datetime.fromtimestamp(ex_dividend_date).strftime("%Y-%m-%d")
                else:
                    ex_date_str = str(ex_dividend_date)[:10]
            except Exception:
                ex_date_str = None

        # Determine frequency based on dividend history
        dividends = ticker.dividends
        frequency = "Unknown"
        if not dividends.empty and len(dividends) >= 4:
            # Calculate average days between dividends
            dates = dividends.index.tolist()
            if len(dates) >= 2:
                avg_days = np.mean([(dates[i] - dates[i-1]).days for i in range(1, min(5, len(dates)))])
                if avg_days < 45:
                    frequency = "Monthly"
                elif avg_days < 100:
                    frequency = "Quarterly"
                elif avg_days < 200:
                    frequency = "Semi-Annual"
                else:
                    frequency = "Annual"

        return {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "currency": info.get("currency", "USD"),
            "annual_dividend": round(annual_dividend, 4),
            "dividend_yield": round(dividend_yield * 100, 2) if dividend_yield < 1 else round(dividend_yield, 2),
            "payout_ratio": round(payout_ratio * 100, 1) if payout_ratio < 1 else round(payout_ratio, 1),
            "frequency": frequency,
            "ex_dividend_date": ex_date_str,
            "last_dividend_amount": round(dividends.iloc[-1], 4) if not dividends.empty else None,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
        }

    except Exception as e:
        logger.error(f"Error fetching dividend info for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def fetch_dividend_history(symbol: str, years: int = 10) -> Dict[str, Any]:
    """
    Fetch historical dividend payments.

    Args:
        symbol: Stock ticker symbol.
        years: Number of years of history to fetch.

    Returns:
        Dict with dividend history and statistics.
    """
    try:
        ticker = yf.Ticker(symbol)
        dividends = ticker.dividends
        info = ticker.info

        if dividends.empty:
            return {
                "symbol": symbol,
                "name": info.get("longName", symbol),
                "has_dividends": False,
                "dividend_history": [],
            }

        # Filter to requested years
        cutoff_date = datetime.now() - timedelta(days=years * 365)
        dividends_filtered = dividends[dividends.index >= cutoff_date]

        # Build history list
        history = []
        for date, amount in dividends_filtered.items():
            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "amount": round(float(amount), 4),
            })

        # Calculate annual totals by year
        annual_totals = {}
        for date, amount in dividends_filtered.items():
            year = date.year
            if year not in annual_totals:
                annual_totals[year] = 0
            annual_totals[year] += float(amount)

        # Round annual totals
        annual_totals = {y: round(v, 4) for y, v in sorted(annual_totals.items())}

        return {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "has_dividends": True,
            "total_payments": len(history),
            "years_covered": len(annual_totals),
            "dividend_history": history[-20:],  # Last 20 payments
            "annual_totals": annual_totals,
        }

    except Exception as e:
        logger.error(f"Error fetching dividend history for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


# ─────────────────────────────────────────────────────────────
# Dividend Growth Analysis
# ─────────────────────────────────────────────────────────────


def calculate_dividend_growth(symbol: str) -> Dict[str, Any]:
    """
    Calculate dividend growth rates and consecutive increase years.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with growth metrics and classification.
    """
    try:
        ticker = yf.Ticker(symbol)
        dividends = ticker.dividends
        info = ticker.info

        if dividends.empty:
            return {
                "symbol": symbol,
                "has_dividends": False,
                "consecutive_years_increased": 0,
                "classification": "Non-Dividend Payer",
            }

        # Calculate annual totals
        annual_totals = {}
        for date, amount in dividends.items():
            year = date.year
            if year not in annual_totals:
                annual_totals[year] = 0
            annual_totals[year] += float(amount)

        years = sorted(annual_totals.keys())
        if len(years) < 2:
            return {
                "symbol": symbol,
                "has_dividends": True,
                "consecutive_years_increased": 0,
                "classification": "New Dividend Payer",
                "message": "Insufficient history for growth analysis",
            }

        # Count consecutive years of increases (going backwards from most recent)
        consecutive_increases = 0
        current_year = datetime.now().year

        # Start from the most recent complete year
        check_years = [y for y in years if y < current_year]
        if len(check_years) < 2:
            consecutive_increases = 0
        else:
            for i in range(len(check_years) - 1, 0, -1):
                if annual_totals[check_years[i]] > annual_totals[check_years[i-1]]:
                    consecutive_increases += 1
                else:
                    break

        # Calculate CAGR for different periods
        def calc_cagr(start_val: float, end_val: float, years: int) -> Optional[float]:
            if start_val <= 0 or end_val <= 0 or years <= 0:
                return None
            return ((end_val / start_val) ** (1 / years) - 1) * 100

        cagr_3y = None
        cagr_5y = None
        cagr_10y = None

        sorted_years = sorted(years)
        current_year = datetime.now().year

        if len(sorted_years) >= 4:
            recent = annual_totals.get(sorted_years[-1], 0)
            three_years_ago = annual_totals.get(sorted_years[-4], 0) if len(sorted_years) >= 4 else 0
            cagr_3y = calc_cagr(three_years_ago, recent, 3)

        if len(sorted_years) >= 6:
            five_years_ago = annual_totals.get(sorted_years[-6], 0) if len(sorted_years) >= 6 else 0
            cagr_5y = calc_cagr(five_years_ago, annual_totals.get(sorted_years[-1], 0), 5)

        if len(sorted_years) >= 11:
            ten_years_ago = annual_totals.get(sorted_years[-11], 0) if len(sorted_years) >= 11 else 0
            cagr_10y = calc_cagr(ten_years_ago, annual_totals.get(sorted_years[-1], 0), 10)

        # Determine classification
        if consecutive_increases >= 50:
            classification = "Dividend King (50+ years)"
        elif consecutive_increases >= 25:
            classification = "Dividend Aristocrat (25+ years)"
        elif consecutive_increases >= 10:
            classification = "Dividend Champion (10+ years)"
        elif consecutive_increases >= 5:
            classification = "Dividend Contender (5+ years)"
        elif consecutive_increases >= 1:
            classification = "Dividend Initiator"
        else:
            classification = "Inconsistent Dividend Payer"

        # Find last increase details
        last_increase_pct = None
        last_increase_date = None
        if len(sorted_years) >= 2:
            recent_year = sorted_years[-1]
            prev_year = sorted_years[-2]
            if annual_totals[prev_year] > 0:
                last_increase_pct = round(
                    ((annual_totals[recent_year] - annual_totals[prev_year]) / annual_totals[prev_year]) * 100,
                    1
                )
                last_increase_date = f"{recent_year}"

        return {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "has_dividends": True,
            "consecutive_years_increased": consecutive_increases,
            "classification": classification,
            "cagr_3_year": round(cagr_3y, 1) if cagr_3y else None,
            "cagr_5_year": round(cagr_5y, 1) if cagr_5y else None,
            "cagr_10_year": round(cagr_10y, 1) if cagr_10y else None,
            "last_increase_pct": last_increase_pct,
            "last_increase_year": last_increase_date,
            "annual_dividends_by_year": {str(y): round(v, 4) for y, v in sorted(annual_totals.items())[-10:]},
        }

    except Exception as e:
        logger.error(f"Error calculating dividend growth for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


# ─────────────────────────────────────────────────────────────
# Dividend Safety Analysis
# ─────────────────────────────────────────────────────────────


def calculate_dividend_safety(symbol: str) -> Dict[str, Any]:
    """
    Calculate dividend safety score based on multiple factors.

    Factors considered:
    - Payout ratio (lower is safer)
    - Free cash flow coverage
    - Debt levels
    - Earnings stability
    - Consecutive increase history

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with safety score (1-100) and factor breakdown.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        cash_flow = ticker.cashflow
        balance_sheet = ticker.balance_sheet
        income_stmt = ticker.income_stmt

        if info.get("dividendRate", 0) == 0:
            return {
                "symbol": symbol,
                "safety_score": 0,
                "rating": "N/A - No Dividend",
                "factors": {},
            }

        factors = {}
        score = 50  # Start at neutral

        # Factor 1: Payout Ratio (0-25 points)
        payout_ratio = info.get("payoutRatio", 0) or 0
        if payout_ratio > 0:
            payout_pct = payout_ratio * 100 if payout_ratio < 1 else payout_ratio
            factors["payout_ratio"] = {
                "value": round(payout_pct, 1),
                "assessment": "",
            }
            if payout_pct < 30:
                score += 25
                factors["payout_ratio"]["assessment"] = "Very safe - below 30%"
            elif payout_pct < 50:
                score += 18
                factors["payout_ratio"]["assessment"] = "Safe - below 50%"
            elif payout_pct < 60:
                score += 12
                factors["payout_ratio"]["assessment"] = "Acceptable - below 60%"
            elif payout_pct < 80:
                score += 5
                factors["payout_ratio"]["assessment"] = "Elevated - approaching 80%"
            elif payout_pct < 100:
                score -= 5
                factors["payout_ratio"]["assessment"] = "High risk - near 100%"
            else:
                score -= 15
                factors["payout_ratio"]["assessment"] = "Unsustainable - exceeds earnings"

        # Factor 2: Free Cash Flow Coverage (0-25 points)
        if not cash_flow.empty:
            try:
                fcf = float(cash_flow.iloc[:, 0].get("Free Cash Flow", 0) or 0)
                shares = info.get("sharesOutstanding", 0)
                annual_div = info.get("dividendRate", 0) or 0

                if shares > 0 and annual_div > 0:
                    total_div_paid = annual_div * shares
                    if fcf > 0:
                        fcf_coverage = fcf / total_div_paid
                        factors["fcf_coverage"] = {
                            "value": round(fcf_coverage, 2),
                            "assessment": "",
                        }
                        if fcf_coverage >= 2.5:
                            score += 25
                            factors["fcf_coverage"]["assessment"] = f"Excellent - FCF covers dividend {fcf_coverage:.1f}x"
                        elif fcf_coverage >= 1.5:
                            score += 18
                            factors["fcf_coverage"]["assessment"] = f"Strong - FCF covers dividend {fcf_coverage:.1f}x"
                        elif fcf_coverage >= 1.0:
                            score += 10
                            factors["fcf_coverage"]["assessment"] = f"Adequate - FCF covers dividend {fcf_coverage:.1f}x"
                        else:
                            score -= 10
                            factors["fcf_coverage"]["assessment"] = "Warning - FCF does not cover dividend"
            except Exception as e:
                logger.debug(f"FCF calculation error: {e}")

        # Factor 3: Debt to Equity (0-15 points)
        if not balance_sheet.empty:
            try:
                total_debt = float(balance_sheet.iloc[:, 0].get("Total Debt", 0) or 0)
                total_equity = float(balance_sheet.iloc[:, 0].get("Total Equity Gross Minority Interest", 0) or 0)

                if total_equity > 0:
                    debt_to_equity = total_debt / total_equity
                    factors["debt_to_equity"] = {
                        "value": round(debt_to_equity, 2),
                        "assessment": "",
                    }
                    if debt_to_equity < 0.3:
                        score += 15
                        factors["debt_to_equity"]["assessment"] = "Conservative leverage"
                    elif debt_to_equity < 0.6:
                        score += 10
                        factors["debt_to_equity"]["assessment"] = "Moderate leverage"
                    elif debt_to_equity < 1.0:
                        score += 5
                        factors["debt_to_equity"]["assessment"] = "Elevated leverage"
                    else:
                        score -= 5
                        factors["debt_to_equity"]["assessment"] = "High leverage - risk factor"
            except Exception as e:
                logger.debug(f"D/E calculation error: {e}")

        # Factor 4: Earnings Stability (0-15 points)
        if not income_stmt.empty:
            try:
                # Check if earnings are consistently positive
                net_incomes = []
                for col in income_stmt.columns[:4]:
                    ni = income_stmt[col].get("Net Income", 0)
                    if ni is not None:
                        net_incomes.append(float(ni))

                if net_incomes:
                    positive_quarters = sum(1 for ni in net_incomes if ni > 0)
                    stability_ratio = positive_quarters / len(net_incomes)
                    factors["earnings_stability"] = {
                        "value": round(stability_ratio, 2),
                        "assessment": "",
                    }
                    if stability_ratio >= 1.0:
                        score += 15
                        factors["earnings_stability"]["assessment"] = "Consistently profitable"
                    elif stability_ratio >= 0.75:
                        score += 10
                        factors["earnings_stability"]["assessment"] = "Generally profitable"
                    elif stability_ratio >= 0.5:
                        score += 5
                        factors["earnings_stability"]["assessment"] = "Mixed profitability"
                    else:
                        score -= 10
                        factors["earnings_stability"]["assessment"] = "Unstable earnings"
            except Exception as e:
                logger.debug(f"Earnings stability calculation error: {e}")

        # Factor 5: Dividend Growth History (0-20 points bonus)
        growth_data = calculate_dividend_growth(symbol)
        consecutive_years = growth_data.get("consecutive_years_increased", 0)
        if consecutive_years >= 25:
            score += 20
            factors["dividend_history"] = {
                "value": consecutive_years,
                "assessment": f"Dividend Aristocrat - {consecutive_years} consecutive years"
            }
        elif consecutive_years >= 10:
            score += 15
            factors["dividend_history"] = {
                "value": consecutive_years,
                "assessment": f"Dividend Champion - {consecutive_years} consecutive years"
            }
        elif consecutive_years >= 5:
            score += 10
            factors["dividend_history"] = {
                "value": consecutive_years,
                "assessment": f"Dividend Contender - {consecutive_years} consecutive years"
            }
        elif consecutive_years >= 1:
            score += 5
            factors["dividend_history"] = {
                "value": consecutive_years,
                "assessment": f"{consecutive_years} year(s) of increases"
            }

        # Cap score at 0-100
        score = max(0, min(100, score))

        # Determine rating
        if score >= 85:
            rating = "Very Safe"
            cut_probability = "Very Low (<5%)"
        elif score >= 70:
            rating = "Safe"
            cut_probability = "Low (5-15%)"
        elif score >= 55:
            rating = "Moderate"
            cut_probability = "Moderate (15-30%)"
        elif score >= 40:
            rating = "Elevated Risk"
            cut_probability = "Elevated (30-50%)"
        else:
            rating = "High Risk"
            cut_probability = "High (>50%)"

        # Identify red flags
        red_flags = []
        if factors.get("payout_ratio", {}).get("value", 0) > 90:
            red_flags.append("Payout ratio exceeds 90% of earnings")
        if factors.get("fcf_coverage", {}).get("value", 999) < 1.0:
            red_flags.append("Free cash flow does not cover dividend payments")
        if factors.get("debt_to_equity", {}).get("value", 0) > 1.5:
            red_flags.append("High debt levels may pressure future dividends")
        if factors.get("earnings_stability", {}).get("value", 1) < 0.5:
            red_flags.append("Inconsistent earnings threaten dividend sustainability")

        return {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "safety_score": score,
            "rating": rating,
            "dividend_cut_probability": cut_probability,
            "factors": factors,
            "red_flags": red_flags,
        }

    except Exception as e:
        logger.error(f"Error calculating dividend safety for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


# ─────────────────────────────────────────────────────────────
# Yield Comparison
# ─────────────────────────────────────────────────────────────


def compare_yields(symbol: str) -> Dict[str, Any]:
    """
    Compare a stock's dividend yield to benchmarks.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with yield comparisons.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        stock_yield = info.get("dividendYield", 0) or 0
        if stock_yield > 0 and stock_yield < 1:
            stock_yield = stock_yield * 100

        sector = info.get("sector", "Unknown")

        # Approximate sector average yields (static benchmarks)
        sector_yields = {
            "Utilities": 3.5,
            "Real Estate": 3.8,
            "Consumer Defensive": 2.5,
            "Energy": 3.2,
            "Healthcare": 1.8,
            "Financial Services": 2.8,
            "Industrials": 2.0,
            "Technology": 1.0,
            "Consumer Cyclical": 1.5,
            "Communication Services": 1.2,
            "Basic Materials": 2.3,
        }

        sector_avg = sector_yields.get(sector, 2.0)

        # S&P 500 average yield (approximate)
        sp500_yield = 1.5

        # 10-Year Treasury yield (approximate current)
        treasury_10y = 4.2

        # Calculate yield spread
        spread_vs_sector = round(stock_yield - sector_avg, 2)
        spread_vs_market = round(stock_yield - sp500_yield, 2)
        spread_vs_treasury = round(stock_yield - treasury_10y, 2)

        # Yield assessment
        if stock_yield > sector_avg * 1.5:
            yield_assessment = "Significantly above sector average - verify sustainability"
        elif stock_yield > sector_avg:
            yield_assessment = "Above sector average - attractive for income"
        elif stock_yield > sector_avg * 0.7:
            yield_assessment = "Near sector average"
        else:
            yield_assessment = "Below sector average"

        return {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "dividend_yield": round(stock_yield, 2),
            "sector": sector,
            "comparisons": {
                "sector_average": sector_avg,
                "sp500_average": sp500_yield,
                "treasury_10y": treasury_10y,
            },
            "spreads": {
                "vs_sector": f"{'+' if spread_vs_sector >= 0 else ''}{spread_vs_sector}%",
                "vs_market": f"{'+' if spread_vs_market >= 0 else ''}{spread_vs_market}%",
                "vs_treasury": f"{'+' if spread_vs_treasury >= 0 else ''}{spread_vs_treasury}%",
            },
            "yield_assessment": yield_assessment,
        }

    except Exception as e:
        logger.error(f"Error comparing yields for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


# ─────────────────────────────────────────────────────────────
# Full Dividend Analysis
# ─────────────────────────────────────────────────────────────


def analyze_dividends(symbol: str) -> Dict[str, Any]:
    """
    Run comprehensive dividend analysis.

    This is the main entry-point used by the DividendAnalystAgent.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Complete dividend analysis dict.
    """
    logger.info(f"Running dividend analysis for {symbol}")
    start_time = datetime.now()

    # Fetch all data
    dividend_info = fetch_dividend_info(symbol)
    if "error" in dividend_info:
        return dividend_info

    # Check if company pays dividends
    if dividend_info.get("annual_dividend", 0) == 0:
        return {
            "symbol": symbol,
            "name": dividend_info.get("name", symbol),
            "pays_dividends": False,
            "message": f"{dividend_info.get('name', symbol)} does not currently pay a dividend.",
            "analyzed_at": datetime.now().isoformat(),
        }

    growth_data = calculate_dividend_growth(symbol)
    safety_data = calculate_dividend_safety(symbol)
    yield_comparison = compare_yields(symbol)

    execution_time = (datetime.now() - start_time).total_seconds()

    return {
        "symbol": symbol,
        "name": dividend_info.get("name", symbol),
        "pays_dividends": True,
        "current_dividend": {
            "annual_dividend": dividend_info.get("annual_dividend"),
            "dividend_yield": dividend_info.get("dividend_yield"),
            "frequency": dividend_info.get("frequency"),
            "payout_ratio": dividend_info.get("payout_ratio"),
            "ex_dividend_date": dividend_info.get("ex_dividend_date"),
            "last_payment_amount": dividend_info.get("last_dividend_amount"),
        },
        "dividend_safety": {
            "safety_score": safety_data.get("safety_score"),
            "rating": safety_data.get("rating"),
            "dividend_cut_probability": safety_data.get("dividend_cut_probability"),
            "factors": safety_data.get("factors", {}),
            "red_flags": safety_data.get("red_flags", []),
        },
        "dividend_growth": {
            "consecutive_years_increased": growth_data.get("consecutive_years_increased"),
            "classification": growth_data.get("classification"),
            "cagr_3_year": growth_data.get("cagr_3_year"),
            "cagr_5_year": growth_data.get("cagr_5_year"),
            "cagr_10_year": growth_data.get("cagr_10_year"),
            "last_increase_pct": growth_data.get("last_increase_pct"),
            "last_increase_year": growth_data.get("last_increase_year"),
        },
        "yield_comparison": {
            "stock_yield": yield_comparison.get("dividend_yield"),
            "sector": yield_comparison.get("sector"),
            "sector_average": yield_comparison.get("comparisons", {}).get("sector_average"),
            "sp500_average": yield_comparison.get("comparisons", {}).get("sp500_average"),
            "treasury_10y": yield_comparison.get("comparisons", {}).get("treasury_10y"),
            "yield_assessment": yield_comparison.get("yield_assessment"),
        },
        "analyzed_at": datetime.now().isoformat(),
        "execution_time_seconds": round(execution_time, 2),
    }


def compare_dividends(symbols: List[str]) -> Dict[str, Any]:
    """
    Compare dividend metrics across multiple companies.

    Args:
        symbols: List of stock ticker symbols.

    Returns:
        Comparison dict with all companies' dividend profiles.
    """
    comparison = []
    for symbol in symbols:
        result = analyze_dividends(symbol)
        if "error" not in result and result.get("pays_dividends", False):
            current = result.get("current_dividend", {})
            safety = result.get("dividend_safety", {})
            growth = result.get("dividend_growth", {})

            comparison.append({
                "symbol": result["symbol"],
                "name": result.get("name"),
                "dividend_yield": current.get("dividend_yield", 0),
                "payout_ratio": current.get("payout_ratio", 0),
                "safety_score": safety.get("safety_score", 0),
                "safety_rating": safety.get("rating", "N/A"),
                "consecutive_years": growth.get("consecutive_years_increased", 0),
                "classification": growth.get("classification", "N/A"),
                "cagr_5_year": growth.get("cagr_5_year"),
            })
        elif result.get("pays_dividends") is False:
            comparison.append({
                "symbol": symbol,
                "name": result.get("name", symbol),
                "dividend_yield": 0,
                "pays_dividends": False,
            })
        else:
            comparison.append({"symbol": symbol, "error": result.get("error")})

    # Sort by safety score (descending)
    comparison.sort(key=lambda x: x.get("safety_score", 0) if "error" not in x else 0, reverse=True)

    # Find best income candidate
    dividend_payers = [c for c in comparison if c.get("safety_score", 0) > 0]
    best_for_income = dividend_payers[0]["symbol"] if dividend_payers else None

    return {
        "companies_compared": len(symbols),
        "comparison": comparison,
        "best_for_income": best_for_income,
        "analyzed_at": datetime.now().isoformat(),
    }
