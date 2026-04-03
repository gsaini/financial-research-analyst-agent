"""
Analyst Consensus Tracking Tool (Feature 16).

Aggregates Wall Street analyst ratings, price targets, estimate revisions,
and upgrade/downgrade activity using yfinance data.

Usage::

    from src.tools.analyst_tracker import get_analyst_consensus
    result = get_analyst_consensus("AAPL")
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Raw data fetchers (direct yfinance access) ──────────────


def _get_ticker(symbol: str):
    """Get a yfinance Ticker object directly for attributes not in provider."""
    try:
        import yfinance as yf
        return yf.Ticker(symbol.upper().strip())
    except ImportError:
        logger.error("yfinance not installed")
        return None


def _safe_df(attr) -> pd.DataFrame:
    """Safely convert a ticker attribute to DataFrame."""
    if attr is None:
        return pd.DataFrame()
    if isinstance(attr, pd.DataFrame):
        return attr
    return pd.DataFrame()


# ── Public API ───────────────────────────────────────────────


def get_analyst_consensus(symbol: str) -> Dict[str, Any]:
    """
    Get comprehensive analyst consensus data for a stock.

    Includes: rating distribution, price targets, recent changes,
    estimate revisions, and overall analyst signal score.

    Args:
        symbol: Stock ticker.

    Returns:
        Dict with consensus_rating, price_targets, recent_changes,
        estimate_revisions, and analyst_signal.
    """
    try:
        ticker = _get_ticker(symbol)
        if ticker is None:
            return {"symbol": symbol, "error": "yfinance not available"}

        provider = get_provider()
        info = provider.get_info(symbol)
        current_price = info.get("currentPrice", info.get("regularMarketPrice", 0))

        # ── Rating Distribution ──
        consensus_rating = _get_rating_distribution(ticker, info)

        # ── Price Targets ──
        price_targets = _get_price_targets(ticker, info, current_price)

        # ── Recent Changes (upgrades/downgrades) ──
        recent_changes = _get_recent_changes(ticker)

        # ── Estimate Revisions ──
        estimate_revisions = _get_estimate_revisions(ticker)

        # ── Analyst Signal Score (0-100) ──
        analyst_signal = _calculate_analyst_signal(
            consensus_rating, price_targets, recent_changes, estimate_revisions
        )

        return {
            "symbol": symbol,
            "company_name": info.get("shortName", symbol),
            "current_price": current_price,
            "consensus_rating": consensus_rating,
            "price_targets": price_targets,
            "recent_changes": recent_changes,
            "estimate_revisions": estimate_revisions,
            "analyst_signal": analyst_signal,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Analyst consensus failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def compare_analyst_consensus(symbols: List[str]) -> Dict[str, Any]:
    """
    Compare analyst consensus across multiple stocks.

    Returns per-stock data and a ranking by analyst signal score.
    """
    results = {}
    for sym in symbols:
        results[sym] = get_analyst_consensus(sym)

    # Ranking
    valid = {s: r for s, r in results.items() if "error" not in r}
    ranked = sorted(
        valid.items(),
        key=lambda x: x[1].get("analyst_signal", {}).get("score", 0),
        reverse=True,
    )

    ranking = [
        {
            "rank": i + 1,
            "symbol": sym,
            "rating": data.get("consensus_rating", {}).get("rating", "N/A"),
            "score": data.get("consensus_rating", {}).get("score", 0),
            "analysts": data.get("consensus_rating", {}).get("total_analysts", 0),
            "upside_pct": data.get("price_targets", {}).get("upside_to_consensus_pct", 0),
            "signal_score": data.get("analyst_signal", {}).get("score", 0),
        }
        for i, (sym, data) in enumerate(ranked)
    ]

    return {
        "symbols": symbols,
        "individual": results,
        "ranking": ranking,
        "most_bullish": ranking[0]["symbol"] if ranking else None,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Internals ────────────────────────────────────────────────


def _get_rating_distribution(ticker, info: Dict) -> Dict[str, Any]:
    """Extract analyst rating distribution."""
    try:
        # Try recommendations_summary first
        rec_summary = getattr(ticker, "recommendations_summary", None)
        if rec_summary is not None and isinstance(rec_summary, pd.DataFrame) and not rec_summary.empty:
            # Latest row
            latest = rec_summary.iloc[0] if len(rec_summary) > 0 else {}
            strong_buy = int(latest.get("strongBuy", 0))
            buy = int(latest.get("buy", 0))
            hold = int(latest.get("hold", 0))
            sell = int(latest.get("sell", 0))
            strong_sell = int(latest.get("strongSell", 0))
        else:
            # Fallback to info fields
            strong_buy = int(info.get("recommendationMean", 0) > 0) * 5
            buy = 0
            hold = 0
            sell = 0
            strong_sell = 0

        total = strong_buy + buy + hold + sell + strong_sell

        if total > 0:
            # Weighted score: 5=Strong Buy, 4=Buy, 3=Hold, 2=Sell, 1=Strong Sell
            weighted = (strong_buy * 5 + buy * 4 + hold * 3 + sell * 2 + strong_sell * 1)
            score = round(weighted / total, 2)
            bullish_pct = round((strong_buy + buy) / total * 100, 1)
        else:
            score = info.get("recommendationMean", 3.0)
            bullish_pct = 0

        # Convert score to rating label
        if score >= 4.5:
            rating = "Strong Buy"
        elif score >= 3.5:
            rating = "Buy"
        elif score >= 2.5:
            rating = "Hold"
        elif score >= 1.5:
            rating = "Sell"
        else:
            rating = "Strong Sell"

        # Also get yfinance recommendation key
        rec_key = info.get("recommendationKey", "").replace("_", " ").title()

        return {
            "rating": rating,
            "yfinance_rating": rec_key or rating,
            "score": score,
            "total_analysts": total,
            "distribution": {
                "strong_buy": strong_buy,
                "buy": buy,
                "hold": hold,
                "sell": sell,
                "strong_sell": strong_sell,
            },
            "bullish_percent": bullish_pct,
        }

    except Exception as e:
        logger.debug(f"Rating distribution failed: {e}")
        rec_key = info.get("recommendationKey", "hold")
        rec_mean = info.get("recommendationMean", 3.0)
        return {
            "rating": rec_key.replace("_", " ").title() if rec_key else "Hold",
            "score": rec_mean,
            "total_analysts": int(info.get("numberOfAnalystOpinions", 0)),
            "distribution": {},
            "bullish_percent": 0,
        }


def _get_price_targets(ticker, info: Dict, current_price: float) -> Dict[str, Any]:
    """Extract analyst price targets."""
    try:
        # Try analyst_price_targets attribute
        apt = getattr(ticker, "analyst_price_targets", None)
        if apt is not None and isinstance(apt, dict) and apt:
            high = apt.get("high", 0)
            low = apt.get("low", 0)
            mean = apt.get("mean", 0)
            median = apt.get("median", 0)
            count = apt.get("numberOfAnalysts", apt.get("numberOfAnalystOpinions", 0))
        else:
            # Fallback to info fields
            high = info.get("targetHighPrice", 0)
            low = info.get("targetLowPrice", 0)
            mean = info.get("targetMeanPrice", 0)
            median = info.get("targetMedianPrice", 0)
            count = info.get("numberOfAnalystOpinions", 0)

        consensus = mean or median or 0
        upside = round((consensus / current_price - 1) * 100, 1) if current_price > 0 and consensus > 0 else 0

        return {
            "consensus": round(consensus, 2) if consensus else None,
            "high": round(high, 2) if high else None,
            "low": round(low, 2) if low else None,
            "median": round(median, 2) if median else None,
            "upside_to_consensus_pct": upside,
            "number_of_analysts": int(count) if count else 0,
            "assessment": (
                f"Consensus target ${consensus:.2f} implies {upside:+.1f}% "
                + ("upside" if upside > 0 else "downside")
            ) if consensus else "No price target data available",
        }

    except Exception as e:
        logger.debug(f"Price targets failed: {e}")
        return {
            "consensus": None, "high": None, "low": None,
            "upside_to_consensus_pct": 0, "number_of_analysts": 0,
            "assessment": "Price target data unavailable",
        }


def _get_recent_changes(ticker, days: int = 90) -> Dict[str, Any]:
    """Extract recent upgrades/downgrades from recommendations history."""
    try:
        recs = getattr(ticker, "recommendations", None)
        recs_df = _safe_df(recs)

        if recs_df.empty:
            return {"changes": [], "upgrades_30d": 0, "downgrades_30d": 0}

        # Filter to recent period
        cutoff = datetime.now() - timedelta(days=days)
        if hasattr(recs_df.index, "tz_localize"):
            try:
                recs_df.index = recs_df.index.tz_localize(None)
            except Exception:
                pass

        recent = recs_df[recs_df.index >= cutoff] if hasattr(recs_df.index, '__ge__') else recs_df.tail(20)

        changes = []
        upgrades_30d = 0
        downgrades_30d = 0
        cutoff_30d = datetime.now() - timedelta(days=30)

        grade_rank = {"Strong Buy": 5, "Buy": 4, "Outperform": 4, "Overweight": 4,
                      "Hold": 3, "Neutral": 3, "Equal-Weight": 3, "Market Perform": 3,
                      "Sell": 2, "Underperform": 2, "Underweight": 2,
                      "Strong Sell": 1}

        for date, row in recent.iterrows():
            firm = row.get("Firm", row.get("firm", ""))
            to_grade = row.get("To Grade", row.get("toGrade", ""))
            from_grade = row.get("From Grade", row.get("fromGrade", ""))
            action = row.get("Action", row.get("action", ""))

            # Determine if upgrade or downgrade
            to_rank = grade_rank.get(to_grade, 3)
            from_rank = grade_rank.get(from_grade, 3)

            if not action:
                if to_rank > from_rank:
                    action = "Upgrade"
                elif to_rank < from_rank:
                    action = "Downgrade"
                else:
                    action = "Reiterate"

            date_str = str(date.date()) if hasattr(date, "date") else str(date)

            changes.append({
                "date": date_str,
                "firm": firm,
                "action": action,
                "from_rating": from_grade,
                "to_rating": to_grade,
            })

            # Count 30-day upgrades/downgrades
            try:
                d = date.to_pydatetime() if hasattr(date, "to_pydatetime") else date
                if hasattr(d, "replace"):
                    d = d.replace(tzinfo=None)
                if d >= cutoff_30d:
                    if "Upgrade" in action or "up" in action.lower():
                        upgrades_30d += 1
                    elif "Downgrade" in action or "down" in action.lower():
                        downgrades_30d += 1
            except Exception:
                pass

        # Sort most recent first
        changes.sort(key=lambda x: x["date"], reverse=True)

        return {
            "changes": changes[:15],  # Last 15
            "total_changes_90d": len(changes),
            "upgrades_30d": upgrades_30d,
            "downgrades_30d": downgrades_30d,
            "net_sentiment_30d": upgrades_30d - downgrades_30d,
            "momentum": (
                "Positive" if upgrades_30d > downgrades_30d
                else "Negative" if downgrades_30d > upgrades_30d
                else "Neutral"
            ),
        }

    except Exception as e:
        logger.debug(f"Recent changes failed: {e}")
        return {"changes": [], "upgrades_30d": 0, "downgrades_30d": 0, "momentum": "N/A"}


def _get_estimate_revisions(ticker) -> Dict[str, Any]:
    """Extract EPS and revenue estimate revision data."""
    try:
        # Earnings estimates
        eps_estimates = {}
        earnings_est = getattr(ticker, "earnings_estimate", None)
        if earnings_est is not None and isinstance(earnings_est, pd.DataFrame) and not earnings_est.empty:
            for col in earnings_est.columns:
                period = str(col)
                row_data = earnings_est[col]
                avg = row_data.get("avg", None)
                low = row_data.get("low", None)
                high = row_data.get("high", None)
                num = row_data.get("numberOfAnalysts", None)
                growth = row_data.get("growth", None)

                eps_estimates[period] = {
                    "avg_estimate": round(float(avg), 2) if avg is not None else None,
                    "low": round(float(low), 2) if low is not None else None,
                    "high": round(float(high), 2) if high is not None else None,
                    "num_analysts": int(num) if num is not None else None,
                    "growth": round(float(growth) * 100, 1) if growth is not None else None,
                }

        # Revenue estimates
        rev_estimates = {}
        revenue_est = getattr(ticker, "revenue_estimate", None)
        if revenue_est is not None and isinstance(revenue_est, pd.DataFrame) and not revenue_est.empty:
            for col in revenue_est.columns:
                period = str(col)
                row_data = revenue_est[col]
                avg = row_data.get("avg", None)
                low = row_data.get("low", None)
                high = row_data.get("high", None)
                num = row_data.get("numberOfAnalysts", None)
                growth = row_data.get("growth", None)

                rev_estimates[period] = {
                    "avg_estimate": round(float(avg)) if avg is not None else None,
                    "low": round(float(low)) if low is not None else None,
                    "high": round(float(high)) if high is not None else None,
                    "num_analysts": int(num) if num is not None else None,
                    "growth_pct": round(float(growth) * 100, 1) if growth is not None else None,
                }

        # EPS trend (estimate revisions over time)
        eps_trend = {}
        eps_trend_data = getattr(ticker, "eps_trend", None)
        if eps_trend_data is not None and isinstance(eps_trend_data, pd.DataFrame) and not eps_trend_data.empty:
            for col in eps_trend_data.columns:
                period = str(col)
                row_data = eps_trend_data[col]
                current = row_data.get("current", None)
                d7_ago = row_data.get("7daysAgo", None)
                d30_ago = row_data.get("30daysAgo", None)
                d60_ago = row_data.get("60daysAgo", None)
                d90_ago = row_data.get("90daysAgo", None)

                revision_30d = None
                if current is not None and d30_ago is not None and d30_ago != 0:
                    revision_30d = round((float(current) - float(d30_ago)) / abs(float(d30_ago)) * 100, 2)

                eps_trend[period] = {
                    "current": round(float(current), 2) if current is not None else None,
                    "7_days_ago": round(float(d7_ago), 2) if d7_ago is not None else None,
                    "30_days_ago": round(float(d30_ago), 2) if d30_ago is not None else None,
                    "60_days_ago": round(float(d60_ago), 2) if d60_ago is not None else None,
                    "90_days_ago": round(float(d90_ago), 2) if d90_ago is not None else None,
                    "revision_30d_pct": revision_30d,
                    "revision_trend": (
                        "Positive" if revision_30d and revision_30d > 1
                        else "Negative" if revision_30d and revision_30d < -1
                        else "Stable"
                    ) if revision_30d is not None else "N/A",
                }

        return {
            "eps_estimates": eps_estimates,
            "revenue_estimates": rev_estimates,
            "eps_trend": eps_trend,
            "has_data": bool(eps_estimates or rev_estimates or eps_trend),
        }

    except Exception as e:
        logger.debug(f"Estimate revisions failed: {e}")
        return {"eps_estimates": {}, "revenue_estimates": {}, "eps_trend": {}, "has_data": False}


def _calculate_analyst_signal(
    consensus: Dict, targets: Dict, changes: Dict, revisions: Dict
) -> Dict[str, Any]:
    """Calculate overall analyst signal score (0-100)."""
    score = 50  # Neutral base

    # Rating component (0-30 points)
    rating_score = consensus.get("score", 3.0)
    # Map 1-5 score to 0-30 points: 5 -> 30, 3 -> 15, 1 -> 0
    score += int((rating_score - 1) / 4 * 30)

    # Bullish percentage component (0-15 points)
    bullish_pct = consensus.get("bullish_percent", 50)
    score += int(bullish_pct / 100 * 15) - 7  # Center around neutral

    # Price target upside (0-15 points)
    upside = targets.get("upside_to_consensus_pct", 0)
    if upside > 20:
        score += 15
    elif upside > 10:
        score += 10
    elif upside > 0:
        score += 5
    elif upside < -10:
        score -= 10
    elif upside < 0:
        score -= 5

    # Recent change momentum (0-10 points)
    net_sentiment = changes.get("net_sentiment_30d", 0)
    score += min(10, max(-10, net_sentiment * 5))

    # Estimate revision momentum (-10 to +10 points)
    eps_trend = revisions.get("eps_trend", {})
    revision_sum = 0
    for period, data in eps_trend.items():
        rev = data.get("revision_30d_pct", 0) or 0
        revision_sum += rev
    if revision_sum > 2:
        score += 10
    elif revision_sum > 0:
        score += 5
    elif revision_sum < -2:
        score -= 10
    elif revision_sum < 0:
        score -= 5

    # Clamp to 0-100
    score = min(100, max(0, score))

    # Assessment
    if score >= 75:
        assessment = "Strongly bullish analyst consensus with positive momentum"
    elif score >= 60:
        assessment = "Bullish consensus — analysts favor the stock"
    elif score >= 40:
        assessment = "Mixed/neutral consensus — no strong directional signal"
    elif score >= 25:
        assessment = "Bearish leaning — analysts are cautious"
    else:
        assessment = "Strongly bearish — significant analyst concern"

    # Key insight
    insights = []
    if bullish_pct > 70:
        insights.append(f"{bullish_pct:.0f}% of analysts are bullish")
    if upside > 10:
        insights.append(f"{upside:.1f}% upside to consensus target")
    if net_sentiment > 0:
        insights.append(f"{changes.get('upgrades_30d', 0)} upgrades in last 30 days")
    if revision_sum > 1:
        insights.append("EPS estimates trending higher")

    return {
        "score": score,
        "assessment": assessment,
        "key_insight": ". ".join(insights) if insights else "Limited analyst activity",
    }
