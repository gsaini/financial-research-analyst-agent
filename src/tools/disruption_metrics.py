"""
Disruption Metrics Tools for Market Disruption Analysis (Feature 3).

This module provides tools to analyze whether a company is a market disruptor
or at risk of being disrupted. It combines quantitative financial signals
(R&D spending, revenue growth, margin trajectory) with qualitative scoring.

Disruption Classification:
- Active Disruptor (70+): High R&D, accelerating growth, expanding margins
- Moderate Innovator (40-70): Some innovation signals, mixed trajectory
- Stable Incumbent (20-40): Low R&D, steady growth, established position
- At Risk (<20): Declining metrics, low innovation investment
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np

import yfinance as yf
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Data Fetching
# ─────────────────────────────────────────────────────────────


def fetch_company_financials(symbol: str) -> Dict[str, Any]:
    """
    Fetch comprehensive financial data for disruption analysis.

    Retrieves multi-year income statements, balance sheets, and company info
    needed to calculate R&D intensity, growth metrics, and margin trajectories.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with financial data organized by category.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        income_stmt = ticker.income_stmt
        balance_sheet = ticker.balance_sheet

        result = {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "description": info.get("longBusinessSummary", "")[:1000],
            "employees": info.get("fullTimeEmployees", 0),
        }

        # Extract multi-year revenue data
        if not income_stmt.empty:
            revenues = []
            rd_expenses = []
            gross_profits = []
            operating_incomes = []
            net_incomes = []

            for col in income_stmt.columns[:4]:  # Up to 4 years
                year_data = income_stmt[col]
                revenues.append(float(year_data.get("Total Revenue", 0) or 0))
                rd_expenses.append(float(year_data.get("Research And Development", 0) or 0))
                gross_profits.append(float(year_data.get("Gross Profit", 0) or 0))
                operating_incomes.append(float(year_data.get("Operating Income", 0) or 0))
                net_incomes.append(float(year_data.get("Net Income", 0) or 0))

            # Reverse to chronological order (oldest first)
            result["revenues"] = list(reversed(revenues))
            result["rd_expenses"] = list(reversed(rd_expenses))
            result["gross_profits"] = list(reversed(gross_profits))
            result["operating_incomes"] = list(reversed(operating_incomes))
            result["net_incomes"] = list(reversed(net_incomes))

            # Years available
            years = [col.year if hasattr(col, "year") else str(col)[:4] for col in income_stmt.columns[:4]]
            result["years"] = list(reversed(years))

        # Extract balance sheet data for assets
        if not balance_sheet.empty:
            latest_bs = balance_sheet.iloc[:, 0]
            result["total_assets"] = float(latest_bs.get("Total Assets", 0) or 0)
            result["intangible_assets"] = float(latest_bs.get("Intangible Assets", 0) or 0)
            result["goodwill"] = float(latest_bs.get("Goodwill", 0) or 0)

        return result

    except Exception as e:
        logger.error(f"Error fetching financials for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def fetch_industry_benchmarks(industry: str) -> Dict[str, float]:
    """
    Get industry-specific benchmarks for disruption metrics.

    Args:
        industry: Company's industry classification.

    Returns:
        Dict with benchmark values for R&D intensity, growth rates, etc.
    """
    # Industry benchmarks based on typical values
    benchmarks = {
        "Software—Infrastructure": {"rd_intensity": 15.0, "revenue_growth": 20.0, "gross_margin": 70.0},
        "Software—Application": {"rd_intensity": 18.0, "revenue_growth": 18.0, "gross_margin": 72.0},
        "Semiconductors": {"rd_intensity": 20.0, "revenue_growth": 12.0, "gross_margin": 55.0},
        "Internet Content & Information": {"rd_intensity": 12.0, "revenue_growth": 15.0, "gross_margin": 55.0},
        "Computer Hardware": {"rd_intensity": 8.0, "revenue_growth": 8.0, "gross_margin": 35.0},
        "Biotechnology": {"rd_intensity": 40.0, "revenue_growth": 25.0, "gross_margin": 65.0},
        "Drug Manufacturers": {"rd_intensity": 15.0, "revenue_growth": 8.0, "gross_margin": 65.0},
        "Medical Devices": {"rd_intensity": 10.0, "revenue_growth": 10.0, "gross_margin": 60.0},
        "Auto Manufacturers": {"rd_intensity": 5.0, "revenue_growth": 5.0, "gross_margin": 15.0},
        "Electric Vehicles": {"rd_intensity": 8.0, "revenue_growth": 30.0, "gross_margin": 20.0},
        "Renewable Energy": {"rd_intensity": 5.0, "revenue_growth": 20.0, "gross_margin": 25.0},
        "Banks—Diversified": {"rd_intensity": 2.0, "revenue_growth": 5.0, "gross_margin": 60.0},
        "Fintech": {"rd_intensity": 15.0, "revenue_growth": 25.0, "gross_margin": 45.0},
        "E-Commerce": {"rd_intensity": 10.0, "revenue_growth": 15.0, "gross_margin": 40.0},
        "Retail": {"rd_intensity": 1.0, "revenue_growth": 5.0, "gross_margin": 30.0},
        "Telecom": {"rd_intensity": 3.0, "revenue_growth": 3.0, "gross_margin": 55.0},
        "Aerospace & Defense": {"rd_intensity": 5.0, "revenue_growth": 5.0, "gross_margin": 20.0},
        "default": {"rd_intensity": 5.0, "revenue_growth": 8.0, "gross_margin": 35.0},
    }

    # Try exact match first, then partial match
    if industry in benchmarks:
        return benchmarks[industry]

    for key in benchmarks:
        if key.lower() in industry.lower() or industry.lower() in key.lower():
            return benchmarks[key]

    return benchmarks["default"]


# ─────────────────────────────────────────────────────────────
# R&D Intensity Analysis
# ─────────────────────────────────────────────────────────────


def calculate_rd_intensity(financials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate R&D intensity metrics.

    R&D intensity is the ratio of R&D spending to revenue, indicating
    how much a company invests in innovation relative to its size.

    Args:
        financials: Output of fetch_company_financials().

    Returns:
        Dict with R&D intensity metrics and trend analysis.
    """
    revenues = financials.get("revenues", [])
    rd_expenses = financials.get("rd_expenses", [])
    industry = financials.get("industry", "default")

    if not revenues or not rd_expenses or len(revenues) != len(rd_expenses):
        return {"error": "Insufficient R&D data"}

    # Calculate R&D to revenue ratio for each year
    rd_ratios = []
    for rev, rd in zip(revenues, rd_expenses):
        if rev > 0 and rd > 0:
            rd_ratios.append(round((rd / rev) * 100, 2))
        else:
            rd_ratios.append(0)

    # Current R&D intensity (most recent year)
    current_rd_intensity = rd_ratios[-1] if rd_ratios else 0

    # R&D trend (comparing current to 2 years ago if available)
    if len(rd_ratios) >= 3:
        rd_change = rd_ratios[-1] - rd_ratios[-3]
        if rd_change > 1:
            rd_trend = "Increasing"
        elif rd_change < -1:
            rd_trend = "Decreasing"
        else:
            rd_trend = "Stable"
    elif len(rd_ratios) >= 2:
        rd_change = rd_ratios[-1] - rd_ratios[-2]
        rd_trend = "Increasing" if rd_change > 0 else "Decreasing" if rd_change < 0 else "Stable"
    else:
        rd_trend = "Insufficient data"
        rd_change = 0

    # Compare to industry
    benchmark = fetch_industry_benchmarks(industry)
    industry_avg = benchmark.get("rd_intensity", 5.0)
    vs_industry = round(current_rd_intensity / industry_avg, 2) if industry_avg > 0 else 0

    # Assessment
    if current_rd_intensity >= industry_avg * 1.5:
        assessment = "High innovation investment - significant R&D commitment"
    elif current_rd_intensity >= industry_avg:
        assessment = "Above-average R&D - competitive innovation position"
    elif current_rd_intensity >= industry_avg * 0.5:
        assessment = "Moderate R&D - room for increased innovation"
    else:
        assessment = "Low R&D intensity - potential innovation gap"

    return {
        "rd_to_revenue_ratio": f"{current_rd_intensity}%",
        "rd_ratios_by_year": rd_ratios,
        "trend": rd_trend,
        "trend_change_pct": round(rd_change, 2),
        "industry_average": f"{industry_avg}%",
        "vs_industry_multiple": f"{vs_industry}x",
        "assessment": assessment,
        "rd_absolute": rd_expenses[-1] if rd_expenses else 0,
    }


# ─────────────────────────────────────────────────────────────
# Revenue Growth Analysis
# ─────────────────────────────────────────────────────────────


def calculate_revenue_acceleration(financials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze revenue growth rate and acceleration.

    Disruptors typically show accelerating revenue growth (growth rate
    of change positive), while at-risk companies show deceleration.

    Args:
        financials: Output of fetch_company_financials().

    Returns:
        Dict with revenue growth metrics and trajectory.
    """
    revenues = financials.get("revenues", [])
    industry = financials.get("industry", "default")

    if len(revenues) < 2:
        return {"error": "Insufficient revenue data"}

    # Calculate YoY growth rates
    growth_rates = []
    for i in range(1, len(revenues)):
        if revenues[i - 1] > 0:
            growth = ((revenues[i] - revenues[i - 1]) / revenues[i - 1]) * 100
            growth_rates.append(round(growth, 2))

    # Current YoY growth (most recent)
    current_growth = growth_rates[-1] if growth_rates else 0

    # Calculate growth acceleration (change in growth rate)
    if len(growth_rates) >= 2:
        acceleration = growth_rates[-1] - growth_rates[-2]
        if acceleration > 5:
            trajectory = "Accelerating strongly"
        elif acceleration > 0:
            trajectory = "Accelerating"
        elif acceleration > -5:
            trajectory = "Stable"
        elif acceleration > -10:
            trajectory = "Decelerating"
        else:
            trajectory = "Decelerating sharply"
    else:
        acceleration = 0
        trajectory = "Insufficient data"

    # CAGR calculation (if we have 3+ years)
    if len(revenues) >= 3 and revenues[0] > 0:
        years = len(revenues) - 1
        cagr = ((revenues[-1] / revenues[0]) ** (1 / years) - 1) * 100
        cagr = round(cagr, 2)
    else:
        cagr = current_growth

    # Compare to industry
    benchmark = fetch_industry_benchmarks(industry)
    industry_growth = benchmark.get("revenue_growth", 8.0)

    # Assessment
    if current_growth >= industry_growth * 2 and acceleration > 0:
        assessment = "Rapid market share capture - disruptor characteristic"
    elif current_growth >= industry_growth:
        assessment = "Above-industry growth - competitive position"
    elif current_growth > 0:
        assessment = "Positive but below-industry growth"
    else:
        assessment = "Declining revenue - potential disruption risk"

    return {
        "yoy_growth": f"{current_growth}%",
        "cagr": f"{cagr}%",
        "growth_rates_by_year": growth_rates,
        "growth_acceleration": round(acceleration, 2),
        "trajectory": trajectory,
        "industry_average_growth": f"{industry_growth}%",
        "assessment": assessment,
    }


# ─────────────────────────────────────────────────────────────
# Margin Trajectory Analysis
# ─────────────────────────────────────────────────────────────


def calculate_margin_trajectory(financials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze gross margin and operating margin trajectories.

    Expanding margins indicate economies of scale and competitive moat,
    common among successful disruptors. Contracting margins suggest
    competitive pressure.

    Args:
        financials: Output of fetch_company_financials().

    Returns:
        Dict with margin metrics and trajectory analysis.
    """
    revenues = financials.get("revenues", [])
    gross_profits = financials.get("gross_profits", [])
    operating_incomes = financials.get("operating_incomes", [])
    industry = financials.get("industry", "default")

    if not revenues or len(revenues) < 2:
        return {"error": "Insufficient margin data"}

    # Calculate gross margins
    gross_margins = []
    for rev, gp in zip(revenues, gross_profits):
        if rev > 0 and gp is not None:
            gross_margins.append(round((gp / rev) * 100, 2))
        else:
            gross_margins.append(0)

    # Calculate operating margins
    operating_margins = []
    for rev, oi in zip(revenues, operating_incomes):
        if rev > 0 and oi is not None:
            operating_margins.append(round((oi / rev) * 100, 2))
        else:
            operating_margins.append(0)

    # Current margins
    current_gross_margin = gross_margins[-1] if gross_margins else 0
    current_op_margin = operating_margins[-1] if operating_margins else 0

    # Margin trajectory (comparing to 2 years ago)
    if len(gross_margins) >= 3:
        gm_change = gross_margins[-1] - gross_margins[-3]
        if gm_change > 2:
            gm_trend = "Expanding"
        elif gm_change < -2:
            gm_trend = "Contracting"
        else:
            gm_trend = "Stable"
    elif len(gross_margins) >= 2:
        gm_change = gross_margins[-1] - gross_margins[0]
        gm_trend = "Expanding" if gm_change > 0 else "Contracting" if gm_change < 0 else "Stable"
    else:
        gm_change = 0
        gm_trend = "Insufficient data"

    # Compare to industry
    benchmark = fetch_industry_benchmarks(industry)
    industry_gm = benchmark.get("gross_margin", 35.0)

    # Assessment
    if current_gross_margin >= industry_gm and gm_trend == "Expanding":
        assessment = "Economies of scale - strong competitive position"
    elif current_gross_margin >= industry_gm:
        assessment = "Healthy margins - established competitive position"
    elif gm_trend == "Expanding":
        assessment = "Improving margins - positive trajectory"
    elif gm_trend == "Contracting":
        assessment = "Margin pressure - competitive challenges"
    else:
        assessment = "Below-industry margins - efficiency concerns"

    return {
        "current_gross_margin": f"{current_gross_margin}%",
        "current_operating_margin": f"{current_op_margin}%",
        "gross_margins_by_year": gross_margins,
        "operating_margins_by_year": operating_margins,
        "gross_margin_change": round(gm_change, 2),
        "trend": gm_trend,
        "industry_average_gm": f"{industry_gm}%",
        "assessment": assessment,
    }


# ─────────────────────────────────────────────────────────────
# Disruption Scoring
# ─────────────────────────────────────────────────────────────


def calculate_disruption_score(
    rd_metrics: Dict[str, Any],
    growth_metrics: Dict[str, Any],
    margin_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate overall disruption score (0-100).

    Combines R&D intensity, revenue acceleration, and margin trajectory
    into a single score with weighted components.

    Scoring weights:
    - R&D Intensity: 35%
    - Revenue Acceleration: 40%
    - Margin Trajectory: 25%

    Args:
        rd_metrics: Output of calculate_rd_intensity().
        growth_metrics: Output of calculate_revenue_acceleration().
        margin_metrics: Output of calculate_margin_trajectory().

    Returns:
        Dict with disruption score and component breakdown.
    """
    # Default weights
    rd_weight = 0.35
    growth_weight = 0.40
    margin_weight = 0.25

    # R&D Score (0-100)
    try:
        rd_ratio = float(rd_metrics.get("rd_to_revenue_ratio", "0%").replace("%", ""))
        vs_industry = float(rd_metrics.get("vs_industry_multiple", "0x").replace("x", ""))
        rd_trend = rd_metrics.get("trend", "Stable")

        # Base score from vs_industry comparison
        rd_score = min(100, vs_industry * 50)  # 2x industry = 100

        # Trend bonus/penalty
        if rd_trend == "Increasing":
            rd_score = min(100, rd_score + 15)
        elif rd_trend == "Decreasing":
            rd_score = max(0, rd_score - 15)
    except (ValueError, TypeError):
        rd_score = 30  # Default moderate score

    # Growth Score (0-100)
    try:
        yoy_growth = float(growth_metrics.get("yoy_growth", "0%").replace("%", ""))
        trajectory = growth_metrics.get("trajectory", "Stable")

        # Base score from growth rate
        if yoy_growth >= 50:
            growth_score = 100
        elif yoy_growth >= 30:
            growth_score = 85
        elif yoy_growth >= 15:
            growth_score = 70
        elif yoy_growth >= 5:
            growth_score = 50
        elif yoy_growth >= 0:
            growth_score = 30
        else:
            growth_score = max(0, 20 + yoy_growth)  # Negative growth reduces score

        # Trajectory bonus/penalty
        if "Accelerating" in trajectory:
            growth_score = min(100, growth_score + 15)
        elif "Decelerating" in trajectory:
            growth_score = max(0, growth_score - 15)
    except (ValueError, TypeError):
        growth_score = 30

    # Margin Score (0-100)
    try:
        gm_change = margin_metrics.get("gross_margin_change", 0)
        trend = margin_metrics.get("trend", "Stable")

        # Base score from trend
        if trend == "Expanding" and gm_change > 5:
            margin_score = 90
        elif trend == "Expanding":
            margin_score = 75
        elif trend == "Stable":
            margin_score = 50
        elif trend == "Contracting" and gm_change > -5:
            margin_score = 30
        else:
            margin_score = 15
    except (ValueError, TypeError):
        margin_score = 40

    # Calculate weighted total
    total_score = int(
        rd_score * rd_weight +
        growth_score * growth_weight +
        margin_score * margin_weight
    )
    total_score = max(0, min(100, total_score))

    # Classification
    if total_score >= 70:
        classification = "Active Disruptor"
        description = "High innovation investment, strong growth, and improving margins"
    elif total_score >= 50:
        classification = "Moderate Innovator"
        description = "Some disruptive characteristics, mixed signals"
    elif total_score >= 30:
        classification = "Stable Incumbent"
        description = "Established position, limited innovation signals"
    else:
        classification = "At Risk"
        description = "Low innovation, weak growth, or margin pressure"

    return {
        "score": total_score,
        "classification": classification,
        "description": description,
        "components": {
            "rd_score": round(rd_score, 1),
            "growth_score": round(growth_score, 1),
            "margin_score": round(margin_score, 1),
        },
        "weights": {
            "rd_intensity": rd_weight,
            "revenue_acceleration": growth_weight,
            "margin_trajectory": margin_weight,
        },
    }


# ─────────────────────────────────────────────────────────────
# Risk Factor Analysis
# ─────────────────────────────────────────────────────────────


def identify_risk_factors(
    financials: Dict[str, Any],
    rd_metrics: Dict[str, Any],
    growth_metrics: Dict[str, Any],
    margin_metrics: Dict[str, Any],
) -> List[str]:
    """
    Identify disruption-related risk factors.

    Args:
        financials: Company financial data.
        rd_metrics: R&D intensity metrics.
        growth_metrics: Revenue acceleration metrics.
        margin_metrics: Margin trajectory metrics.

    Returns:
        List of identified risk factors.
    """
    risks = []

    # R&D risks
    try:
        vs_industry = float(rd_metrics.get("vs_industry_multiple", "1x").replace("x", ""))
        rd_trend = rd_metrics.get("trend", "Stable")

        if vs_industry < 0.5:
            risks.append("R&D investment significantly below industry average")
        if rd_trend == "Decreasing":
            risks.append("Declining R&D investment trend")
    except (ValueError, TypeError):
        pass

    # Growth risks
    try:
        yoy_growth = float(growth_metrics.get("yoy_growth", "0%").replace("%", ""))
        trajectory = growth_metrics.get("trajectory", "Stable")

        if yoy_growth < 0:
            risks.append("Declining revenue indicates market share loss")
        if "Decelerating sharply" in trajectory:
            risks.append("Rapid growth deceleration - demand concerns")
    except (ValueError, TypeError):
        pass

    # Margin risks
    margin_trend = margin_metrics.get("trend", "Stable")
    if margin_trend == "Contracting":
        risks.append("Contracting margins suggest competitive pressure")

    # Industry-specific risks
    industry = financials.get("industry", "")
    high_disruption_industries = [
        "Retail", "Media", "Telecom", "Auto Manufacturers", "Banks"
    ]
    for ind in high_disruption_industries:
        if ind.lower() in industry.lower():
            risks.append(f"{ind} industry faces significant disruption from new entrants")
            break

    # Market cap risk (smaller companies more vulnerable)
    market_cap = financials.get("market_cap", 0)
    if market_cap > 0 and market_cap < 2_000_000_000:  # < $2B
        risks.append("Smaller market cap may limit ability to invest in innovation")

    return risks


def identify_strengths(
    rd_metrics: Dict[str, Any],
    growth_metrics: Dict[str, Any],
    margin_metrics: Dict[str, Any],
) -> List[str]:
    """
    Identify disruption-related strengths.

    Args:
        rd_metrics: R&D intensity metrics.
        growth_metrics: Revenue acceleration metrics.
        margin_metrics: Margin trajectory metrics.

    Returns:
        List of identified strengths.
    """
    strengths = []

    # R&D strengths
    try:
        vs_industry = float(rd_metrics.get("vs_industry_multiple", "1x").replace("x", ""))
        rd_trend = rd_metrics.get("trend", "Stable")

        if vs_industry >= 1.5:
            strengths.append(f"R&D investment {vs_industry}x industry average")
        if rd_trend == "Increasing":
            strengths.append("Increasing R&D commitment signals innovation focus")
    except (ValueError, TypeError):
        pass

    # Growth strengths
    try:
        yoy_growth = float(growth_metrics.get("yoy_growth", "0%").replace("%", ""))
        trajectory = growth_metrics.get("trajectory", "Stable")

        if yoy_growth >= 20:
            strengths.append(f"Strong {yoy_growth}% revenue growth demonstrates market demand")
        if "Accelerating" in trajectory:
            strengths.append("Accelerating growth indicates expanding market share")
    except (ValueError, TypeError):
        pass

    # Margin strengths
    margin_trend = margin_metrics.get("trend", "Stable")
    gm_change = margin_metrics.get("gross_margin_change", 0)
    if margin_trend == "Expanding" and gm_change > 3:
        strengths.append("Expanding margins indicate economies of scale and pricing power")

    return strengths


# ─────────────────────────────────────────────────────────────
# Full Disruption Analysis
# ─────────────────────────────────────────────────────────────


def analyze_disruption(symbol: str) -> Dict[str, Any]:
    """
    Run comprehensive market disruption analysis.

    This is the main entry-point used by the DisruptionAnalystAgent.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Complete disruption analysis dict.
    """
    logger.info(f"Running disruption analysis for {symbol}")
    start_time = datetime.utcnow()

    # Fetch financial data
    financials = fetch_company_financials(symbol)
    if "error" in financials:
        return financials

    # Calculate metrics
    rd_metrics = calculate_rd_intensity(financials)
    growth_metrics = calculate_revenue_acceleration(financials)
    margin_metrics = calculate_margin_trajectory(financials)

    # Handle errors in metrics
    if "error" in rd_metrics:
        rd_metrics = {"rd_to_revenue_ratio": "0%", "trend": "Unknown", "vs_industry_multiple": "1x"}
    if "error" in growth_metrics:
        growth_metrics = {"yoy_growth": "0%", "trajectory": "Unknown"}
    if "error" in margin_metrics:
        margin_metrics = {"trend": "Unknown", "gross_margin_change": 0}

    # Calculate disruption score
    score_data = calculate_disruption_score(rd_metrics, growth_metrics, margin_metrics)

    # Identify risks and strengths
    risk_factors = identify_risk_factors(financials, rd_metrics, growth_metrics, margin_metrics)
    strengths = identify_strengths(rd_metrics, growth_metrics, margin_metrics)

    execution_time = (datetime.utcnow() - start_time).total_seconds()

    return {
        "symbol": financials.get("symbol"),
        "name": financials.get("name"),
        "sector": financials.get("sector"),
        "industry": financials.get("industry"),
        "disruption_score": score_data["score"],
        "classification": score_data["classification"],
        "classification_description": score_data["description"],
        "score_components": score_data["components"],
        "score_weights": score_data["weights"],
        "quantitative_signals": {
            "rd_intensity": rd_metrics,
            "revenue_acceleration": growth_metrics,
            "gross_margin_trajectory": margin_metrics,
        },
        "strengths": strengths,
        "risk_factors": risk_factors,
        "financial_summary": {
            "market_cap": financials.get("market_cap", 0),
            "employees": financials.get("employees", 0),
            "years_analyzed": len(financials.get("years", [])),
            "data_years": financials.get("years", []),
        },
        "analyzed_at": datetime.utcnow().isoformat(),
        "execution_time_seconds": round(execution_time, 2),
    }


def compare_disruption(symbols: List[str]) -> Dict[str, Any]:
    """
    Compare disruption metrics across multiple companies.

    Args:
        symbols: List of stock ticker symbols.

    Returns:
        Comparison dict with all companies' disruption profiles.
    """
    comparison = []
    for symbol in symbols:
        result = analyze_disruption(symbol)
        if "error" not in result:
            comparison.append({
                "symbol": result["symbol"],
                "name": result["name"],
                "industry": result["industry"],
                "disruption_score": result["disruption_score"],
                "classification": result["classification"],
                "rd_intensity": result["quantitative_signals"]["rd_intensity"].get("rd_to_revenue_ratio", "N/A"),
                "revenue_growth": result["quantitative_signals"]["revenue_acceleration"].get("yoy_growth", "N/A"),
                "margin_trend": result["quantitative_signals"]["gross_margin_trajectory"].get("trend", "N/A"),
            })
        else:
            comparison.append({"symbol": symbol, "error": result.get("error")})

    # Sort by disruption score
    comparison.sort(key=lambda x: x.get("disruption_score", 0), reverse=True)

    return {
        "companies_compared": len(symbols),
        "comparison": comparison,
        "most_disruptive": comparison[0]["symbol"] if comparison and "error" not in comparison[0] else None,
        "analyzed_at": datetime.utcnow().isoformat(),
    }
