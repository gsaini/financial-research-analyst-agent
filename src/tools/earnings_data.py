"""
Earnings Data Tools for Quarterly Earnings Analysis (Feature 4).

This module provides tools to fetch and analyze quarterly earnings data:
- Quarterly EPS and revenue actuals vs estimates
- Earnings surprise calculations and beat/miss patterns
- Quarter-over-quarter and year-over-year trends
- Upcoming earnings dates and estimates
- Earnings quality assessment
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

import yfinance as yf
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Data Fetching
# ─────────────────────────────────────────────────────────────


def fetch_quarterly_financials(symbol: str) -> Dict[str, Any]:
    """
    Fetch quarterly financial statements for earnings analysis.

    Retrieves quarterly income statement data including revenue,
    net income, EPS, and EBITDA for the last 8 quarters.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with quarterly financial data.
    """
    try:
        ticker = yf.Ticker(symbol)
        quarterly_income = ticker.quarterly_income_stmt
        info = ticker.info

        if quarterly_income.empty:
            return {"symbol": symbol, "error": "No quarterly financial data available"}

        result = {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "currency": info.get("currency", "USD"),
            "quarters": [],
        }

        # Process each quarter (columns are dates)
        for col in quarterly_income.columns[:8]:  # Up to 8 quarters
            quarter_data = quarterly_income[col]
            quarter_date = col

            # Determine fiscal quarter
            if hasattr(quarter_date, "month"):
                month = quarter_date.month
                year = quarter_date.year
                if month <= 3:
                    quarter_label = f"Q1 {year}"
                elif month <= 6:
                    quarter_label = f"Q2 {year}"
                elif month <= 9:
                    quarter_label = f"Q3 {year}"
                else:
                    quarter_label = f"Q4 {year}"
            else:
                quarter_label = str(quarter_date)[:10]

            quarter_info = {
                "quarter": quarter_label,
                "date": quarter_date.strftime("%Y-%m-%d") if hasattr(quarter_date, "strftime") else str(quarter_date)[:10],
                "revenue": float(quarter_data.get("Total Revenue", 0) or 0),
                "gross_profit": float(quarter_data.get("Gross Profit", 0) or 0),
                "operating_income": float(quarter_data.get("Operating Income", 0) or 0),
                "net_income": float(quarter_data.get("Net Income", 0) or 0),
                "ebitda": float(quarter_data.get("EBITDA", 0) or 0),
            }

            # Calculate EPS if shares outstanding available
            shares = info.get("sharesOutstanding", 0)
            if shares > 0 and quarter_info["net_income"] != 0:
                quarter_info["eps_calculated"] = round(quarter_info["net_income"] / shares, 2)
            else:
                quarter_info["eps_calculated"] = None

            result["quarters"].append(quarter_info)

        return result

    except Exception as e:
        logger.error(f"Error fetching quarterly financials for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def fetch_earnings_history(symbol: str) -> Dict[str, Any]:
    """
    Fetch historical earnings data with actual vs estimate comparisons.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with earnings history including surprises.
    """
    try:
        ticker = yf.Ticker(symbol)

        # Try to get earnings data
        earnings = ticker.earnings_history
        info = ticker.info

        result = {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "earnings_records": [],
        }

        if earnings is not None and not earnings.empty:
            for idx, row in earnings.iterrows():
                record = {
                    "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
                    "eps_actual": float(row.get("epsActual", 0) or 0),
                    "eps_estimate": float(row.get("epsEstimate", 0) or 0),
                }

                # Calculate surprise
                if record["eps_estimate"] != 0:
                    surprise = ((record["eps_actual"] - record["eps_estimate"]) / abs(record["eps_estimate"])) * 100
                    record["eps_surprise_pct"] = round(surprise, 2)

                    if surprise > 1:
                        record["verdict"] = "BEAT"
                    elif surprise < -1:
                        record["verdict"] = "MISS"
                    else:
                        record["verdict"] = "INLINE"
                else:
                    record["eps_surprise_pct"] = 0
                    record["verdict"] = "N/A"

                result["earnings_records"].append(record)

        return result

    except Exception as e:
        logger.error(f"Error fetching earnings history for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e), "earnings_records": []}


def fetch_upcoming_earnings(symbol: str) -> Dict[str, Any]:
    """
    Fetch upcoming earnings date and analyst estimates.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with next earnings date and estimates.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        calendar = ticker.calendar

        result = {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
        }

        # Get earnings date from calendar
        if calendar is not None and not calendar.empty:
            if "Earnings Date" in calendar.index:
                earnings_dates = calendar.loc["Earnings Date"]
                if hasattr(earnings_dates, "__iter__") and len(earnings_dates) > 0:
                    next_date = earnings_dates.iloc[0] if hasattr(earnings_dates, "iloc") else earnings_dates[0]
                    if pd.notna(next_date):
                        if hasattr(next_date, "strftime"):
                            result["next_earnings_date"] = next_date.strftime("%Y-%m-%d")
                            days_until = (next_date - datetime.now()).days
                            result["days_until_earnings"] = max(0, days_until)
                        else:
                            result["next_earnings_date"] = str(next_date)
                            result["days_until_earnings"] = None

        # Get analyst estimates
        result["eps_estimate"] = info.get("forwardEps", None)
        result["revenue_estimate"] = info.get("revenueEstimate", None)
        result["target_mean_price"] = info.get("targetMeanPrice", None)
        result["recommendation"] = info.get("recommendationKey", None)
        result["number_of_analysts"] = info.get("numberOfAnalystOpinions", None)

        return result

    except Exception as e:
        logger.error(f"Error fetching upcoming earnings for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


# ─────────────────────────────────────────────────────────────
# Surprise Analysis
# ─────────────────────────────────────────────────────────────


def calculate_surprise_pattern(earnings_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze beat/miss pattern across earnings history.

    Args:
        earnings_records: List of earnings records with verdicts.

    Returns:
        Dict with surprise pattern analysis.
    """
    if not earnings_records:
        return {
            "total_quarters": 0,
            "beats": 0,
            "misses": 0,
            "inline": 0,
            "beat_rate": 0,
            "average_surprise": 0,
            "pattern": "Insufficient data",
        }

    beats = sum(1 for r in earnings_records if r.get("verdict") == "BEAT")
    misses = sum(1 for r in earnings_records if r.get("verdict") == "MISS")
    inline = sum(1 for r in earnings_records if r.get("verdict") == "INLINE")
    total = len(earnings_records)

    surprises = [r.get("eps_surprise_pct", 0) for r in earnings_records if r.get("eps_surprise_pct") is not None]
    avg_surprise = round(np.mean(surprises), 2) if surprises else 0

    beat_rate = round((beats / total) * 100, 1) if total > 0 else 0

    # Determine pattern
    if beat_rate >= 80:
        pattern = "Consistent beater - management typically under-promises"
    elif beat_rate >= 60:
        pattern = "Regular beater - tends to exceed expectations"
    elif beat_rate >= 40:
        pattern = "Mixed results - unpredictable earnings"
    elif beat_rate >= 20:
        pattern = "Regular misser - tends to disappoint"
    else:
        pattern = "Consistent misser - credibility concerns"

    return {
        "total_quarters": total,
        "beats": beats,
        "misses": misses,
        "inline": inline,
        "beat_rate": f"{beat_rate}%",
        "average_surprise": f"{'+' if avg_surprise >= 0 else ''}{avg_surprise}%",
        "pattern": pattern,
    }


# ─────────────────────────────────────────────────────────────
# Trend Analysis
# ─────────────────────────────────────────────────────────────


def calculate_quarterly_trends(quarters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate quarter-over-quarter and year-over-year trends.

    Args:
        quarters: List of quarterly financial data (most recent first).

    Returns:
        Dict with trend analysis.
    """
    if len(quarters) < 2:
        return {"error": "Insufficient quarterly data for trend analysis"}

    # Reverse to chronological order (oldest first)
    quarters_chrono = list(reversed(quarters))

    # Calculate QoQ growth rates for revenue
    revenue_qoq = []
    for i in range(1, len(quarters_chrono)):
        prev_rev = quarters_chrono[i - 1].get("revenue", 0)
        curr_rev = quarters_chrono[i].get("revenue", 0)
        if prev_rev > 0:
            growth = ((curr_rev - prev_rev) / prev_rev) * 100
            revenue_qoq.append(round(growth, 1))

    # Calculate QoQ growth rates for net income (proxy for EPS trend)
    income_qoq = []
    for i in range(1, len(quarters_chrono)):
        prev_inc = quarters_chrono[i - 1].get("net_income", 0)
        curr_inc = quarters_chrono[i].get("net_income", 0)
        if prev_inc > 0:
            growth = ((curr_inc - prev_inc) / prev_inc) * 100
            income_qoq.append(round(growth, 1))
        elif prev_inc < 0 and curr_inc > 0:
            income_qoq.append(100.0)  # Turnaround
        elif prev_inc == 0:
            income_qoq.append(0.0)

    # Determine trend direction
    def determine_trend(growth_rates: List[float]) -> str:
        if len(growth_rates) < 2:
            return "Insufficient data"

        recent = growth_rates[-2:] if len(growth_rates) >= 2 else growth_rates
        avg_recent = np.mean(recent)
        avg_all = np.mean(growth_rates)

        if avg_recent > avg_all + 2:
            return "Accelerating"
        elif avg_recent < avg_all - 2:
            return "Decelerating"
        elif avg_all > 2:
            return "Growing steadily"
        elif avg_all < -2:
            return "Declining"
        else:
            return "Stable"

    revenue_trend = determine_trend(revenue_qoq)
    income_trend = determine_trend(income_qoq)

    # Calculate gross margin trajectory
    margins = []
    for q in quarters_chrono:
        rev = q.get("revenue", 0)
        gp = q.get("gross_profit", 0)
        if rev > 0:
            margins.append(round((gp / rev) * 100, 2))

    if len(margins) >= 2:
        margin_change = margins[-1] - margins[0]
        if margin_change > 2:
            margin_trajectory = "Expanding"
        elif margin_change < -2:
            margin_trajectory = "Contracting"
        else:
            margin_trajectory = "Stable"
    else:
        margin_trajectory = "Insufficient data"

    return {
        "revenue_qoq_growth": [f"{'+' if g >= 0 else ''}{g}%" for g in revenue_qoq],
        "revenue_trend": revenue_trend,
        "net_income_qoq_growth": [f"{'+' if g >= 0 else ''}{g}%" for g in income_qoq],
        "income_trend": income_trend,
        "margin_trajectory": margin_trajectory,
        "gross_margins_by_quarter": [f"{m}%" for m in margins],
    }


def calculate_yoy_comparison(quarters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate year-over-year comparisons for same quarters.

    Args:
        quarters: List of quarterly financial data (most recent first).

    Returns:
        Dict with YoY comparison data.
    """
    if len(quarters) < 5:
        return {"error": "Need at least 5 quarters for YoY comparison"}

    comparisons = {}

    # Compare current quarter vs same quarter last year (4 quarters ago)
    current = quarters[0]
    year_ago = quarters[4] if len(quarters) > 4 else None

    if year_ago:
        current_quarter = current.get("quarter", "Current")
        year_ago_quarter = year_ago.get("quarter", "Year Ago")

        comparison_key = f"{current_quarter}_vs_{year_ago_quarter}"

        current_rev = current.get("revenue", 0)
        year_ago_rev = year_ago.get("revenue", 0)
        current_inc = current.get("net_income", 0)
        year_ago_inc = year_ago.get("net_income", 0)

        if year_ago_rev > 0:
            rev_growth = ((current_rev - year_ago_rev) / year_ago_rev) * 100
            comparisons["revenue_growth"] = f"{'+' if rev_growth >= 0 else ''}{round(rev_growth, 1)}%"
        else:
            comparisons["revenue_growth"] = "N/A"

        if year_ago_inc > 0:
            inc_growth = ((current_inc - year_ago_inc) / year_ago_inc) * 100
            comparisons["net_income_growth"] = f"{'+' if inc_growth >= 0 else ''}{round(inc_growth, 1)}%"
        elif year_ago_inc < 0 and current_inc > 0:
            comparisons["net_income_growth"] = "Turnaround to profitability"
        else:
            comparisons["net_income_growth"] = "N/A"

        comparisons["comparison_period"] = comparison_key

    return comparisons


# ─────────────────────────────────────────────────────────────
# Earnings Quality Assessment
# ─────────────────────────────────────────────────────────────


def assess_earnings_quality(quarters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assess the quality of earnings (operational vs one-time).

    High-quality earnings are driven by operations, not one-time items.
    Indicators: consistent margins, revenue-driven growth, cash conversion.

    Args:
        quarters: List of quarterly financial data.

    Returns:
        Dict with earnings quality assessment.
    """
    if len(quarters) < 4:
        return {
            "score": 5.0,
            "assessment": "Insufficient data for quality assessment",
            "factors": [],
        }

    factors = []
    score = 5.0  # Start at neutral

    # Factor 1: Revenue consistency (low volatility is good)
    revenues = [q.get("revenue", 0) for q in quarters if q.get("revenue", 0) > 0]
    if len(revenues) >= 4:
        rev_std = np.std(revenues) / np.mean(revenues) if np.mean(revenues) > 0 else 1
        if rev_std < 0.1:
            score += 1.5
            factors.append("Highly consistent revenue (low volatility)")
        elif rev_std < 0.2:
            score += 0.5
            factors.append("Reasonably consistent revenue")
        elif rev_std > 0.3:
            score -= 1.0
            factors.append("Volatile revenue (high variability)")

    # Factor 2: Margin stability
    margins = []
    for q in quarters:
        rev = q.get("revenue", 0)
        gp = q.get("gross_profit", 0)
        if rev > 0:
            margins.append(gp / rev)

    if len(margins) >= 4:
        margin_std = np.std(margins)
        if margin_std < 0.02:
            score += 1.0
            factors.append("Stable gross margins (operational consistency)")
        elif margin_std > 0.05:
            score -= 0.5
            factors.append("Volatile margins (potential quality concerns)")

    # Factor 3: Operating income vs net income alignment
    # Large gaps suggest non-operating items
    for q in quarters[:4]:
        op_inc = q.get("operating_income", 0)
        net_inc = q.get("net_income", 0)
        if op_inc > 0:
            ratio = net_inc / op_inc if op_inc != 0 else 1
            if 0.6 <= ratio <= 1.2:
                pass  # Normal
            else:
                score -= 0.25
                if ratio > 1.5:
                    factors.append("Net income significantly higher than operating income (non-operating gains)")
                elif ratio < 0.5:
                    factors.append("Net income significantly lower than operating income (non-operating losses)")
                break

    # Factor 4: Growth quality (revenue-driven vs margin-driven)
    if len(quarters) >= 4:
        rev_growth = (quarters[0].get("revenue", 0) - quarters[3].get("revenue", 1)) / quarters[3].get("revenue", 1) if quarters[3].get("revenue", 0) > 0 else 0
        inc_growth = (quarters[0].get("net_income", 0) - quarters[3].get("net_income", 1)) / quarters[3].get("net_income", 1) if quarters[3].get("net_income", 0) > 0 else 0

        if rev_growth > 0 and inc_growth > rev_growth:
            score += 0.5
            factors.append("Earnings growing faster than revenue (operating leverage)")
        elif rev_growth > 0:
            factors.append("Revenue-driven growth (sustainable)")
        elif inc_growth > 0 and rev_growth <= 0:
            score -= 0.5
            factors.append("Earnings growth without revenue growth (cost cutting, not sustainable)")

    score = max(1.0, min(10.0, score))

    # Determine assessment
    if score >= 8.0:
        assessment = "High quality - driven by operations, not one-time items"
    elif score >= 6.5:
        assessment = "Good quality - primarily operational with minor concerns"
    elif score >= 5.0:
        assessment = "Average quality - some non-operational factors present"
    elif score >= 3.5:
        assessment = "Below average quality - significant non-operational items"
    else:
        assessment = "Low quality - earnings not reflective of core operations"

    return {
        "score": round(score, 1),
        "assessment": assessment,
        "factors": factors if factors else ["Standard operational earnings profile"],
    }


# ─────────────────────────────────────────────────────────────
# Full Earnings Analysis
# ─────────────────────────────────────────────────────────────


def analyze_earnings(symbol: str) -> Dict[str, Any]:
    """
    Run comprehensive quarterly earnings analysis.

    This is the main entry-point used by the EarningsAnalystAgent.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Complete earnings analysis dict.
    """
    logger.info(f"Running earnings analysis for {symbol}")
    start_time = datetime.now()

    # Fetch all data
    financials = fetch_quarterly_financials(symbol)
    if "error" in financials:
        return financials

    earnings_history = fetch_earnings_history(symbol)
    upcoming = fetch_upcoming_earnings(symbol)

    quarters = financials.get("quarters", [])

    # Build last 4 quarters summary with available data
    last_4_quarters = []
    for i, q in enumerate(quarters[:4]):
        quarter_summary = {
            "quarter": q.get("quarter"),
            "date": q.get("date"),
            "revenue_actual": q.get("revenue"),
            "net_income": q.get("net_income"),
            "eps_calculated": q.get("eps_calculated"),
        }

        # Try to find matching earnings record for estimates
        for er in earnings_history.get("earnings_records", []):
            if er.get("date") and q.get("date") and er["date"][:7] == q["date"][:7]:
                quarter_summary["eps_actual"] = er.get("eps_actual")
                quarter_summary["eps_estimate"] = er.get("eps_estimate")
                quarter_summary["eps_surprise_pct"] = er.get("eps_surprise_pct")
                quarter_summary["verdict"] = er.get("verdict")
                break

        last_4_quarters.append(quarter_summary)

    # Calculate surprise pattern
    surprise_pattern = calculate_surprise_pattern(earnings_history.get("earnings_records", []))

    # Calculate trends
    quarterly_trends = calculate_quarterly_trends(quarters)

    # Calculate YoY comparison
    yoy_comparison = calculate_yoy_comparison(quarters)

    # Assess earnings quality
    earnings_quality = assess_earnings_quality(quarters)

    execution_time = (datetime.now() - start_time).total_seconds()

    return {
        "symbol": financials.get("symbol"),
        "name": financials.get("name"),
        "currency": financials.get("currency", "USD"),
        "last_4_quarters": last_4_quarters,
        "earnings_surprise_history": {
            "last_8_quarters": surprise_pattern,
        },
        "quarterly_trends": quarterly_trends,
        "yoy_comparison": yoy_comparison,
        "next_earnings": {
            "date": upcoming.get("next_earnings_date"),
            "days_until": upcoming.get("days_until_earnings"),
            "eps_estimate": upcoming.get("eps_estimate"),
            "revenue_estimate": upcoming.get("revenue_estimate"),
            "number_of_analysts": upcoming.get("number_of_analysts"),
        },
        "earnings_quality": earnings_quality,
        "analyzed_at": datetime.now().isoformat(),
        "execution_time_seconds": round(execution_time, 2),
    }


def compare_earnings(symbols: List[str]) -> Dict[str, Any]:
    """
    Compare earnings metrics across multiple companies.

    Args:
        symbols: List of stock ticker symbols.

    Returns:
        Comparison dict with all companies' earnings profiles.
    """
    comparison = []
    for symbol in symbols:
        result = analyze_earnings(symbol)
        if "error" not in result:
            surprise_data = result.get("earnings_surprise_history", {}).get("last_8_quarters", {})
            trends = result.get("quarterly_trends", {})
            quality = result.get("earnings_quality", {})

            comparison.append({
                "symbol": result["symbol"],
                "name": result.get("name"),
                "beat_rate": surprise_data.get("beat_rate", "N/A"),
                "average_surprise": surprise_data.get("average_surprise", "N/A"),
                "pattern": surprise_data.get("pattern", "N/A"),
                "revenue_trend": trends.get("revenue_trend", "N/A"),
                "income_trend": trends.get("income_trend", "N/A"),
                "earnings_quality_score": quality.get("score", 0),
                "next_earnings_date": result.get("next_earnings", {}).get("date"),
            })
        else:
            comparison.append({"symbol": symbol, "error": result.get("error")})

    # Sort by earnings quality score
    comparison.sort(key=lambda x: x.get("earnings_quality_score", 0) if "error" not in x else 0, reverse=True)

    return {
        "companies_compared": len(symbols),
        "comparison": comparison,
        "best_earnings_quality": comparison[0]["symbol"] if comparison and "error" not in comparison[0] else None,
        "analyzed_at": datetime.now().isoformat(),
    }
