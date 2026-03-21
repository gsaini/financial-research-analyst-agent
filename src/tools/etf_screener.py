"""
ETF Screener & Recommendation Engine.

Analyzes all investment themes from themes.yaml, fetches real-time ETF data,
and produces a ranked list of recommended ETFs based on:
- Theme health score and momentum
- ETF-specific performance (1M, 3M, 6M, 1Y)
- Expense ratio and AUM (when available)
- Risk-adjusted scoring
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import numpy as np

from src.data import get_provider
from src.tools.theme_mapper import list_available_themes, analyze_theme
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# ETF Data Fetching
# ─────────────────────────────────────────────────────────────


def fetch_etf_data(symbol: str) -> Dict[str, Any]:
    """
    Fetch ETF price data, performance, and metadata from yfinance.

    Args:
        symbol: ETF ticker symbol.

    Returns:
        Dict with ETF details and performance.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1y")

        if hist.empty:
            return {"symbol": symbol, "error": "No data available"}

        current_price = info.get(
            "currentPrice",
            info.get("regularMarketPrice", info.get("navPrice", float(hist["Close"].iloc[-1]))),
        )

        # Calculate returns over various periods
        closes = hist["Close"]
        returns = {}
        for label, days in [("1w", 5), ("1m", 21), ("3m", 63), ("6m", 126), ("1y", 252)]:
            if len(closes) >= days:
                start_price = float(closes.iloc[-days])
                ret = ((current_price - start_price) / start_price) * 100
                returns[label] = round(ret, 2)

        # YTD return
        year_start = closes[closes.index.year == datetime.now().year]
        if not year_start.empty:
            ytd_start = float(year_start.iloc[0])
            returns["ytd"] = round(((current_price - ytd_start) / ytd_start) * 100, 2)

        # Volatility (annualized)
        daily_returns = closes.pct_change().dropna()
        volatility = round(float(daily_returns.std() * np.sqrt(252) * 100), 2) if len(daily_returns) > 20 else None

        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "current_price": round(float(current_price), 2),
            "total_assets": info.get("totalAssets"),
            "expense_ratio": info.get("annualReportExpenseRatio"),
            "category": info.get("category", ""),
            "returns": returns,
            "volatility": volatility,
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "avg_volume": info.get("averageVolume"),
            "dividend_yield": info.get("yield"),
        }

    except Exception as e:
        logger.error(f"Error fetching ETF data for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


# ─────────────────────────────────────────────────────────────
# Theme-Based ETF Scoring
# ─────────────────────────────────────────────────────────────


def _calculate_etf_composite_score(
    etf_data: Dict[str, Any],
    theme_health: int,
    theme_momentum: int,
    theme_risk_level: str,
) -> float:
    """
    Calculate a composite recommendation score (0-100) for an ETF.

    Weights:
    - Theme health (30%): How strong is the underlying theme?
    - Theme momentum (20%): Is the theme gaining traction?
    - ETF 3M return (20%): Recent ETF-specific performance
    - ETF 1Y return (15%): Longer-term trend
    - Volatility penalty (15%): Lower volatility preferred

    Args:
        etf_data: ETF performance and metadata.
        theme_health: Theme health score (0-100).
        theme_momentum: Theme momentum score (0-100).
        theme_risk_level: Theme risk classification.

    Returns:
        Composite score 0-100.
    """
    score = 0.0

    # Theme health contribution (0-30)
    score += (theme_health / 100) * 30

    # Theme momentum contribution (0-20)
    score += (theme_momentum / 100) * 20

    returns = etf_data.get("returns", {})

    # ETF 3M return contribution (0-20)
    ret_3m = returns.get("3m", 0)
    # Normalize: -30% maps to 0, +30% maps to 20
    ret_3m_norm = max(0, min(20, ((ret_3m + 30) / 60) * 20))
    score += ret_3m_norm

    # ETF 1Y return contribution (0-15)
    ret_1y = returns.get("1y", 0)
    ret_1y_norm = max(0, min(15, ((ret_1y + 50) / 100) * 15))
    score += ret_1y_norm

    # Volatility penalty (0-15, lower vol = higher score)
    vol = etf_data.get("volatility")
    if vol is not None:
        # 10% vol → 15 pts, 40% vol → 0 pts
        vol_score = max(0, min(15, ((40 - vol) / 30) * 15))
        score += vol_score
    else:
        score += 7.5  # Neutral if no data

    return round(max(0, min(100, score)), 1)


def _risk_label_to_number(risk_level: str) -> int:
    """Convert risk level string to numeric (1-5)."""
    mapping = {
        "Low": 1,
        "Low-Medium": 2,
        "Medium": 3,
        "Medium-High": 4,
        "High": 5,
        "Very High": 5,
    }
    return mapping.get(risk_level, 3)


# ─────────────────────────────────────────────────────────────
# Main Screener
# ─────────────────────────────────────────────────────────────


def screen_etfs(
    theme_ids: Optional[List[str]] = None,
    max_risk: Optional[str] = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    Screen and rank ETFs across investment themes.

    Analyzes each theme, fetches data for reference ETFs, and produces
    a ranked recommendation list.

    Args:
        theme_ids: Specific theme IDs to analyze. None = all themes.
        max_risk: Maximum risk level filter (e.g. "Medium", "High").
        top_n: Number of top ETFs to return.

    Returns:
        Dict with ranked ETF recommendations and theme summaries.
    """
    logger.info("Starting ETF screening")
    start_time = datetime.now()

    themes = list_available_themes()
    if not themes:
        return {"error": "No themes available. Check config/themes.yaml."}

    # Filter to requested themes
    if theme_ids:
        themes = [t for t in themes if t.get("theme_id") in theme_ids]

    # Apply risk filter
    max_risk_num = _risk_label_to_number(max_risk) if max_risk else 5
    themes = [t for t in themes if _risk_label_to_number(t.get("risk_level", "Medium")) <= max_risk_num]

    all_etf_recommendations = []
    theme_summaries = []
    seen_etfs = set()

    for theme in themes:
        theme_id = theme.get("theme_id")
        theme_name = theme.get("name", theme_id)
        reference_etfs = theme.get("reference_etfs", [])
        risk_level = theme.get("risk_level", "Medium")

        if not reference_etfs:
            continue

        # Analyze theme
        try:
            theme_result = analyze_theme(theme_id)
        except Exception as e:
            logger.warning(f"Failed to analyze theme {theme_id}: {e}")
            continue

        if "error" in theme_result:
            continue

        theme_health = theme_result.get("theme_health_score", 50)
        theme_momentum = theme_result.get("momentum_score", 50)
        perf = theme_result.get("theme_performance", {})

        theme_summaries.append({
            "theme_id": theme_id,
            "theme_name": theme_name,
            "health_score": theme_health,
            "momentum_score": theme_momentum,
            "risk_level": risk_level,
            "growth_stage": theme.get("growth_stage", ""),
            "performance_1y": perf.get("1y", "N/A"),
            "performance_ytd": perf.get("ytd", "N/A"),
            "etf_count": len(reference_etfs),
        })

        # Fetch and score each ETF
        for etf_symbol in reference_etfs:
            if etf_symbol in seen_etfs:
                continue
            seen_etfs.add(etf_symbol)

            etf_data = fetch_etf_data(etf_symbol)
            if "error" in etf_data:
                continue

            composite_score = _calculate_etf_composite_score(
                etf_data, theme_health, theme_momentum, risk_level,
            )

            returns = etf_data.get("returns", {})

            all_etf_recommendations.append({
                "symbol": etf_symbol,
                "name": etf_data.get("name", etf_symbol),
                "theme": theme_name,
                "theme_id": theme_id,
                "composite_score": composite_score,
                "theme_health": theme_health,
                "theme_momentum": theme_momentum,
                "risk_level": risk_level,
                "current_price": etf_data.get("current_price"),
                "returns": {
                    "1w": returns.get("1w"),
                    "1m": returns.get("1m"),
                    "3m": returns.get("3m"),
                    "6m": returns.get("6m"),
                    "1y": returns.get("1y"),
                    "ytd": returns.get("ytd"),
                },
                "volatility": etf_data.get("volatility"),
                "expense_ratio": etf_data.get("expense_ratio"),
                "total_assets": etf_data.get("total_assets"),
                "dividend_yield": etf_data.get("dividend_yield"),
            })

    # Sort by composite score
    all_etf_recommendations.sort(key=lambda x: x["composite_score"], reverse=True)

    # Sort theme summaries by health score
    theme_summaries.sort(key=lambda x: x["health_score"], reverse=True)

    # Determine recommendation tiers
    for etf in all_etf_recommendations:
        score = etf["composite_score"]
        if score >= 75:
            etf["recommendation"] = "Strong Buy"
        elif score >= 60:
            etf["recommendation"] = "Buy"
        elif score >= 45:
            etf["recommendation"] = "Hold"
        elif score >= 30:
            etf["recommendation"] = "Underweight"
        else:
            etf["recommendation"] = "Avoid"

    execution_time = (datetime.now() - start_time).total_seconds()

    return {
        "total_themes_analyzed": len(theme_summaries),
        "total_etfs_screened": len(all_etf_recommendations),
        "top_recommendations": all_etf_recommendations[:top_n],
        "all_etfs": all_etf_recommendations,
        "theme_rankings": theme_summaries,
        "filters_applied": {
            "theme_ids": theme_ids,
            "max_risk": max_risk,
        },
        "screened_at": datetime.now().isoformat(),
        "execution_time_seconds": round(execution_time, 2),
    }
