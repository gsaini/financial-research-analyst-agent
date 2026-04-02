"""
Short Interest Analysis Tool (Feature 14).

Tracks shares sold short, days to cover, short squeeze scoring,
and risk assessment for both long and short positions.

Usage::

    from src.tools.short_interest import analyze_short_interest
    result = analyze_short_interest("GME")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Squeeze scoring thresholds ───────────────────────────────

# Short % of float scoring: higher = more squeeze potential
_SHORT_PCT_THRESHOLDS = [
    (40, 100),   # >= 40% -> score 100
    (25, 85),    # >= 25% -> 85
    (15, 65),    # >= 15% -> 65
    (10, 45),    # >= 10% -> 45
    (5, 25),     # >= 5%  -> 25
    (0, 10),     # < 5%   -> 10
]

# Days to cover scoring: higher = harder for shorts to exit
_DTC_THRESHOLDS = [
    (10, 100),   # >= 10 days -> 100
    (7, 85),     # >= 7 days  -> 85
    (5, 65),     # >= 5 days  -> 65
    (3, 45),     # >= 3 days  -> 45
    (1, 25),     # >= 1 day   -> 25
    (0, 10),     # < 1 day    -> 10
]


def _score_from_thresholds(value: float, thresholds: list) -> int:
    """Look up score for a value using threshold table."""
    for threshold, score in thresholds:
        if value >= threshold:
            return score
    return 0


# ── Main analysis ────────────────────────────────────────────


def analyze_short_interest(symbol: str) -> Dict[str, Any]:
    """
    Comprehensive short interest analysis for a stock.

    Fetches short interest metrics from the data provider, calculates a
    squeeze score (0-100), and provides risk assessment for both longs
    and shorts.

    Args:
        symbol: Stock ticker (e.g. "GME", "AAPL").

    Returns:
        Dict with short_interest metrics, squeeze_analysis,
        historical_context, and risk_assessment.
    """
    try:
        provider = get_provider()
        info = provider.get_info(symbol)

        if not info:
            return {"symbol": symbol, "error": "Could not fetch stock data"}

        # ── Extract short interest data from provider info ──

        shares_short = info.get("sharesShort", 0) or 0
        shares_short_prior = info.get("sharesShortPriorMonth", 0) or 0
        short_ratio = info.get("shortRatio", 0) or 0  # Days to cover
        short_pct_float = info.get("shortPercentOfFloat", 0) or 0
        shares_outstanding = info.get("sharesOutstanding", 0) or 0
        float_shares = info.get("floatShares", 0) or 0

        # Convert short_pct_float from decimal to percentage if needed
        if 0 < short_pct_float < 1:
            short_pct_float *= 100

        # Calculate short % of shares outstanding
        short_pct_outstanding = (
            (shares_short / shares_outstanding * 100)
            if shares_outstanding > 0 else 0
        )

        # Month-over-month change
        short_change_pct = 0
        short_change_dir = "stable"
        if shares_short_prior > 0:
            short_change_pct = (shares_short - shares_short_prior) / shares_short_prior * 100
            if short_change_pct > 5:
                short_change_dir = "increasing"
            elif short_change_pct < -5:
                short_change_dir = "decreasing"

        # ── Short interest data block ──

        short_interest = {
            "shares_short": shares_short,
            "shares_short_formatted": _format_number(shares_short),
            "short_percent_of_float": round(short_pct_float, 2),
            "short_percent_of_shares": round(short_pct_outstanding, 2),
            "short_ratio_days_to_cover": round(short_ratio, 2),
            "previous_month_shares_short": shares_short_prior,
            "previous_month_formatted": _format_number(shares_short_prior),
            "change_vs_previous_pct": round(short_change_pct, 1),
            "change_direction": short_change_dir,
            "float_shares": float_shares,
            "shares_outstanding": shares_outstanding,
        }

        # ── Squeeze scoring ──

        # Component scores
        pct_score = _score_from_thresholds(short_pct_float, _SHORT_PCT_THRESHOLDS)
        dtc_score = _score_from_thresholds(short_ratio, _DTC_THRESHOLDS)

        # Increasing short interest adds to squeeze risk
        increase_score = 0
        if short_change_pct > 20:
            increase_score = 90
        elif short_change_pct > 10:
            increase_score = 70
        elif short_change_pct > 5:
            increase_score = 50
        elif short_change_pct > 0:
            increase_score = 30
        else:
            increase_score = 10

        # Cost to borrow (approximated from short ratio and short %)
        # Higher short interest usually correlates with harder borrowing
        borrow_score = min(100, int(short_pct_float * 2 + short_ratio * 5))

        # Weighted squeeze score
        squeeze_score = int(
            pct_score * 0.35 +
            dtc_score * 0.30 +
            increase_score * 0.15 +
            borrow_score * 0.20
        )
        squeeze_score = min(100, max(0, squeeze_score))

        # Risk level
        if squeeze_score >= 75:
            squeeze_risk = "High"
        elif squeeze_score >= 50:
            squeeze_risk = "Elevated"
        elif squeeze_score >= 25:
            squeeze_risk = "Moderate"
        else:
            squeeze_risk = "Low"

        squeeze_analysis = {
            "squeeze_score": squeeze_score,
            "risk_level": squeeze_risk,
            "factors": {
                "short_percent_score": pct_score,
                "days_to_cover_score": dtc_score,
                "recent_increase_score": increase_score,
                "borrow_cost_score": borrow_score,
            },
            "assessment": _generate_squeeze_assessment(
                squeeze_score, squeeze_risk, short_pct_float, short_ratio, short_change_dir
            ),
        }

        # ── Historical context ──

        # Approximate percentile based on typical market ranges
        # Most stocks: 1-5% short interest; above 15% is notably high
        if short_pct_float >= 30:
            percentile = 99
        elif short_pct_float >= 20:
            percentile = 95
        elif short_pct_float >= 15:
            percentile = 90
        elif short_pct_float >= 10:
            percentile = 80
        elif short_pct_float >= 5:
            percentile = 60
        elif short_pct_float >= 2:
            percentile = 40
        else:
            percentile = 20

        historical_context = {
            "current_short_pct": round(short_pct_float, 2),
            "market_percentile": percentile,
            "percentile_label": (
                "Extremely high (top 1%)" if percentile >= 99
                else "Very high (top 5%)" if percentile >= 95
                else "High (top 10%)" if percentile >= 90
                else "Above average" if percentile >= 60
                else "Average" if percentile >= 40
                else "Below average"
            ),
            "trend": short_change_dir,
        }

        # ── Borrow data (estimated) ──

        # Estimate borrow rate from short interest intensity
        estimated_borrow_rate = round(max(0.5, short_pct_float * 0.3 + short_ratio * 0.5), 1)
        borrow_data = {
            "estimated_borrow_rate_pct": estimated_borrow_rate,
            "borrow_assessment": (
                "Very hard to borrow — elevated cost" if estimated_borrow_rate > 10
                else "Hard to borrow" if estimated_borrow_rate > 5
                else "Moderate borrow cost" if estimated_borrow_rate > 2
                else "Easy to borrow"
            ),
            "note": "Borrow rate is estimated — actual rates vary by broker.",
        }

        # ── Risk assessment ──

        risk_assessment = _generate_risk_assessment(
            symbol, info, short_pct_float, short_ratio, squeeze_score, short_change_dir
        )

        return {
            "symbol": symbol,
            "company_name": info.get("shortName", symbol),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "short_interest": short_interest,
            "squeeze_analysis": squeeze_analysis,
            "historical_context": historical_context,
            "borrow_data": borrow_data,
            "risk_assessment": risk_assessment,
            "data_freshness": "Short interest is typically reported bi-monthly by exchanges with a ~10 day delay.",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Short interest analysis failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def compare_short_interest(symbols: List[str]) -> Dict[str, Any]:
    """
    Compare short interest across multiple stocks.

    Args:
        symbols: List of tickers.

    Returns:
        Dict with per-stock short metrics and ranking.
    """
    results = {}
    for sym in symbols:
        results[sym] = analyze_short_interest(sym)

    # Ranking by squeeze score
    valid = {s: r for s, r in results.items() if "error" not in r}
    ranked = sorted(
        valid.items(),
        key=lambda x: x[1].get("squeeze_analysis", {}).get("squeeze_score", 0),
        reverse=True,
    )

    ranking = [
        {
            "rank": i + 1,
            "symbol": sym,
            "squeeze_score": data.get("squeeze_analysis", {}).get("squeeze_score", 0),
            "short_pct_float": data.get("short_interest", {}).get("short_percent_of_float", 0),
            "days_to_cover": data.get("short_interest", {}).get("short_ratio_days_to_cover", 0),
            "risk_level": data.get("squeeze_analysis", {}).get("risk_level", "N/A"),
        }
        for i, (sym, data) in enumerate(ranked)
    ]

    return {
        "symbols": symbols,
        "individual": results,
        "ranking": ranking,
        "most_shorted": ranked[0][0] if ranked else None,
        "highest_squeeze_risk": ranking[0] if ranking else None,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def get_short_squeeze_watchlist(
    symbols: Optional[List[str]] = None,
    min_squeeze_score: int = 50,
) -> Dict[str, Any]:
    """
    Screen stocks for short squeeze potential.

    Args:
        symbols: Stocks to screen (defaults to a built-in high-short list).
        min_squeeze_score: Minimum squeeze score to include.

    Returns:
        Dict with stocks meeting the squeeze threshold.
    """
    if symbols is None:
        # Common high-short-interest stocks to scan
        symbols = [
            "GME", "AMC", "BBBY", "CVNA", "UPST", "BYND", "SPCE",
            "RIVN", "LCID", "NKLA", "PLUG", "SKLZ", "WISH", "CLOV",
            "SOFI", "PLTR", "NIO", "FUBO", "OPEN", "ASTS",
        ]

    candidates = []
    for sym in symbols:
        result = analyze_short_interest(sym)
        if "error" in result:
            continue
        score = result.get("squeeze_analysis", {}).get("squeeze_score", 0)
        if score >= min_squeeze_score:
            candidates.append({
                "symbol": sym,
                "company": result.get("company_name", sym),
                "price": result.get("current_price", 0),
                "squeeze_score": score,
                "risk_level": result.get("squeeze_analysis", {}).get("risk_level", ""),
                "short_pct_float": result.get("short_interest", {}).get("short_percent_of_float", 0),
                "days_to_cover": result.get("short_interest", {}).get("short_ratio_days_to_cover", 0),
                "trend": result.get("historical_context", {}).get("trend", ""),
            })

    candidates.sort(key=lambda x: x["squeeze_score"], reverse=True)

    return {
        "screened": len(symbols),
        "matches": len(candidates),
        "min_squeeze_score": min_squeeze_score,
        "candidates": candidates,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Helpers ──────────────────────────────────────────────────


def _format_number(n: int) -> str:
    """Format large numbers for display."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _generate_squeeze_assessment(
    score: int, risk: str, short_pct: float, dtc: float, trend: str
) -> str:
    """Generate human-readable squeeze assessment."""
    parts = []

    if score >= 75:
        parts.append(f"High short squeeze potential (score: {score}/100).")
    elif score >= 50:
        parts.append(f"Elevated squeeze potential (score: {score}/100).")
    elif score >= 25:
        parts.append(f"Moderate squeeze potential (score: {score}/100).")
    else:
        parts.append(f"Low squeeze potential (score: {score}/100).")

    if short_pct >= 20:
        parts.append(f"{short_pct:.1f}% of float is shorted — very high concentration.")
    elif short_pct >= 10:
        parts.append(f"{short_pct:.1f}% of float is shorted — above average.")

    if dtc >= 5:
        parts.append(f"Days to cover is {dtc:.1f} — shorts would need multiple days to exit.")

    if trend == "increasing":
        parts.append("Short interest is rising, adding to squeeze pressure.")
    elif trend == "decreasing":
        parts.append("Short interest is declining — shorts may be covering.")

    return " ".join(parts)


def _generate_risk_assessment(
    symbol: str,
    info: Dict,
    short_pct: float,
    dtc: float,
    squeeze_score: int,
    trend: str,
) -> Dict[str, Any]:
    """Generate risk assessment for both longs and shorts."""
    # Catalyst identification
    catalysts = []

    # Check upcoming earnings
    try:
        calendar = info.get("earningsDate")
        if calendar:
            catalysts.append(f"Upcoming earnings (potential volatility catalyst)")
    except Exception:
        pass

    if short_pct >= 15:
        catalysts.append("High short interest creates short-covering rally potential")
    if trend == "increasing":
        catalysts.append("Rising short interest may attract short-squeeze traders")
    if dtc >= 5:
        catalysts.append("High days-to-cover limits short exit speed")

    # Volume context
    avg_volume = info.get("averageVolume", 0)
    if avg_volume:
        catalysts.append(f"Average daily volume: {_format_number(avg_volume)} shares")

    # For longs
    if squeeze_score >= 70:
        long_assessment = (
            "Significant short squeeze potential could amplify gains. "
            "If a positive catalyst triggers covering, forced buying could drive "
            "rapid price appreciation. However, high short interest also signals "
            "fundamental concerns — ensure the bull thesis is sound."
        )
    elif squeeze_score >= 40:
        long_assessment = (
            "Moderate short squeeze upside. Short covering could provide a tailwind, "
            "but is unlikely to be the primary driver. Focus on fundamentals."
        )
    else:
        long_assessment = (
            "Low short squeeze potential. Short interest is not a significant factor "
            "in the investment thesis. Focus on fundamental and technical analysis."
        )

    # For shorts
    if squeeze_score >= 70:
        short_assessment = (
            "CAUTION: High squeeze risk. If price rises, forced covering could cause "
            "explosive moves against short positions. Use tight stop-losses and consider "
            "put options instead of direct shorting for defined-risk exposure."
        )
    elif squeeze_score >= 40:
        short_assessment = (
            "Moderate squeeze risk. Monitor short interest trend and catalysts closely. "
            "Position sizing should account for potential short-covering rallies."
        )
    else:
        short_assessment = (
            "Low squeeze risk. Short position is relatively safe from squeeze dynamics, "
            "but standard risk management still applies."
        )

    return {
        "for_longs": long_assessment,
        "for_shorts": short_assessment,
        "catalyst_watch": catalysts,
        "overall_risk": (
            "High" if squeeze_score >= 70
            else "Moderate" if squeeze_score >= 40
            else "Low"
        ),
    }
