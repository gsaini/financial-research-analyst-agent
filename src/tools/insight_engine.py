"""
Key Observations & Insights Engine (Feature 11).

A synthesis layer that consumes all analysis results (technical, fundamental,
earnings, performance, peer comparison) and produces ranked, cross-dimensional
observations answering: "What should I pay attention to?"

Usage
-----
>>> from src.tools.insight_engine import generate_observations
>>> obs = generate_observations("AAPL", analyses={
...     "technical": {...},
...     "fundamental": {...},
...     "earnings": {...},
...     "performance": {...},
...     "peers": {...},
... })
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

CATEGORY_BULLISH = "Bullish Signal"
CATEGORY_BEARISH = "Bearish Signal"
CATEGORY_RISK    = "Risk Warning"
CATEGORY_OPPORTUNITY = "Opportunity"
CATEGORY_ANOMALY = "Anomaly"
CATEGORY_WATCH   = "Watch Item"

SEVERITY_CRITICAL = "Critical"
SEVERITY_HIGH     = "High"
SEVERITY_MEDIUM   = "Medium"
SEVERITY_LOW      = "Low"

ICON_MAP = {
    CATEGORY_BULLISH: "🟢",
    CATEGORY_BEARISH: "🔴",
    CATEGORY_RISK: "⚠️",
    CATEGORY_OPPORTUNITY: "💡",
    CATEGORY_ANOMALY: "🔍",
    CATEGORY_WATCH: "👁️",
}


def _obs(
    category: str,
    severity: str,
    title: str,
    observation: str,
    evidence: List[str],
    confidence: float = 0.7,
    actionability: str = "Medium",
    direction: str = "neutral",
) -> Dict[str, Any]:
    """Build a single observation dict."""
    return {
        "category": category,
        "icon": ICON_MAP.get(category, ""),
        "severity": severity,
        "title": title,
        "observation": observation,
        "supporting_evidence": evidence,
        "confidence": round(confidence, 2),
        "actionability": actionability,
        "direction": direction,
    }


# ─────────────────────────────────────────────────────────────
# Detector: Technical Signals
# ─────────────────────────────────────────────────────────────


def _detect_technical_signals(tech: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract observations from technical analysis results."""
    observations: List[Dict[str, Any]] = []
    if not tech:
        return observations

    # --- RSI ---
    rsi_data = tech.get("rsi", {})
    rsi_val = rsi_data.get("value")
    if rsi_val is not None:
        if rsi_val < 30:
            observations.append(_obs(
                CATEGORY_BULLISH, SEVERITY_HIGH,
                "RSI Oversold Condition",
                f"RSI at {rsi_val:.1f} indicates the stock is oversold. "
                "Historically this often precedes a short-term rebound.",
                [f"RSI: {rsi_val:.1f} (oversold < 30)"],
                confidence=0.75, actionability="High — watch for reversal confirmation",
                direction="bullish",
            ))
        elif rsi_val > 70:
            observations.append(_obs(
                CATEGORY_BEARISH, SEVERITY_HIGH,
                "RSI Overbought Condition",
                f"RSI at {rsi_val:.1f} indicates the stock is overbought. "
                "Increased risk of a pullback or consolidation.",
                [f"RSI: {rsi_val:.1f} (overbought > 70)"],
                confidence=0.72, actionability="High — consider taking profits",
                direction="bearish",
            ))

    # --- MACD ---
    macd_data = tech.get("macd", {})
    crossover = macd_data.get("crossover", "none")
    if crossover == "bullish":
        observations.append(_obs(
            CATEGORY_BULLISH, SEVERITY_MEDIUM,
            "MACD Bullish Crossover",
            "MACD line has crossed above the signal line, indicating building upward momentum.",
            [f"MACD crossover: {crossover}", f"Histogram: {macd_data.get('histogram', 'N/A')}"],
            confidence=0.68, actionability="Medium — confirm with volume",
            direction="bullish",
        ))
    elif crossover == "bearish":
        observations.append(_obs(
            CATEGORY_BEARISH, SEVERITY_MEDIUM,
            "MACD Bearish Crossover",
            "MACD line has crossed below the signal line, indicating weakening momentum.",
            [f"MACD crossover: {crossover}", f"Histogram: {macd_data.get('histogram', 'N/A')}"],
            confidence=0.68, actionability="Medium — watch for support levels",
            direction="bearish",
        ))

    # --- Moving Averages (trend) ---
    ma_data = tech.get("moving_averages", {})
    trend = ma_data.get("trend")
    if trend == "bullish":
        observations.append(_obs(
            CATEGORY_BULLISH, SEVERITY_LOW,
            "Bullish Moving Average Trend",
            "50-day SMA is above 200-day SMA, confirming a long-term uptrend.",
            [f"SMA-50: {ma_data.get('sma_50', 'N/A')}", f"SMA-200: {ma_data.get('sma_200', 'N/A')}"],
            confidence=0.65, actionability="Low — trend context",
            direction="bullish",
        ))
    elif trend == "bearish":
        observations.append(_obs(
            CATEGORY_BEARISH, SEVERITY_LOW,
            "Bearish Moving Average Trend",
            "50-day SMA is below 200-day SMA, confirming a long-term downtrend.",
            [f"SMA-50: {ma_data.get('sma_50', 'N/A')}", f"SMA-200: {ma_data.get('sma_200', 'N/A')}"],
            confidence=0.65, actionability="Low — trend context",
            direction="bearish",
        ))

    # --- Bollinger Band position ---
    bb_data = tech.get("bollinger_bands", {})
    bb_pos = bb_data.get("position")
    if bb_pos == "below_lower":
        observations.append(_obs(
            CATEGORY_BULLISH, SEVERITY_MEDIUM,
            "Price Below Lower Bollinger Band",
            "Price has dropped below the lower Bollinger Band — statistically extreme move. "
            "Mean-reversion setups are common in range-bound markets.",
            [f"Position: {bb_pos}", f"Lower band: {bb_data.get('lower_band', 'N/A')}"],
            confidence=0.60, actionability="Medium — mean reversion potential",
            direction="bullish",
        ))
    elif bb_pos == "above_upper":
        observations.append(_obs(
            CATEGORY_BEARISH, SEVERITY_MEDIUM,
            "Price Above Upper Bollinger Band",
            "Price has broken above the upper Bollinger Band — statistically extreme. "
            "May indicate an overextended move.",
            [f"Position: {bb_pos}", f"Upper band: {bb_data.get('upper_band', 'N/A')}"],
            confidence=0.60, actionability="Medium — watch for exhaustion",
            direction="bearish",
        ))

    return observations


# ─────────────────────────────────────────────────────────────
# Detector: Valuation / Fundamental Signals
# ─────────────────────────────────────────────────────────────


def _detect_valuation_signals(
    fundamental: Dict[str, Any],
    peers: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Extract observations from fundamental and peer comparison."""
    observations: List[Dict[str, Any]] = []
    if not fundamental and not peers:
        return observations

    # --- P/E vs peer median ---
    comparison = peers.get("comparison_table", {}) if peers else {}
    pe_data = comparison.get("pe_ratio", {})
    peer_median_pe = pe_data.get("peer_median")
    # Try to find target PE from the comparison or fundamental data
    target_pe = None
    target_symbol = peers.get("target", "") if peers else ""
    if target_symbol and target_symbol in pe_data:
        target_pe = pe_data[target_symbol]

    if target_pe is not None and peer_median_pe is not None and peer_median_pe > 0:
        discount_pct = (target_pe - peer_median_pe) / peer_median_pe * 100
        if discount_pct < -15:
            observations.append(_obs(
                CATEGORY_OPPORTUNITY, SEVERITY_HIGH,
                "Trading at Significant P/E Discount to Peers",
                f"P/E ratio of {target_pe:.1f} is {abs(discount_pct):.0f}% below the "
                f"peer median of {peer_median_pe:.1f}. This may represent a value opportunity "
                "if the discount is not justified by weaker fundamentals.",
                [f"Target P/E: {target_pe:.1f}", f"Peer median: {peer_median_pe:.1f}",
                 f"Discount: {discount_pct:.1f}%"],
                confidence=0.72, actionability="Medium — investigate the reason for the gap",
                direction="bullish",
            ))
        elif discount_pct > 25:
            observations.append(_obs(
                CATEGORY_RISK, SEVERITY_MEDIUM,
                "Trading at Significant P/E Premium to Peers",
                f"P/E ratio of {target_pe:.1f} is {discount_pct:.0f}% above the peer median "
                f"of {peer_median_pe:.1f}. Elevated valuation increases downside risk if "
                "growth disappoints.",
                [f"Target P/E: {target_pe:.1f}", f"Peer median: {peer_median_pe:.1f}",
                 f"Premium: +{discount_pct:.1f}%"],
                confidence=0.68, actionability="Low — premium may be justified by growth",
                direction="bearish",
            ))

    # --- Financial health from fundamentals ---
    health = fundamental.get("financial_health", {}) if fundamental else {}
    health_score = health.get("overall_score")
    if health_score is not None:
        if health_score < 40:
            observations.append(_obs(
                CATEGORY_RISK, SEVERITY_HIGH,
                "Weak Financial Health Score",
                f"Overall financial health score is {health_score}/100, indicating "
                "potential liquidity or solvency concerns.",
                [f"Health score: {health_score}/100"],
                confidence=0.78, actionability="High — review debt levels and cash flow",
                direction="bearish",
            ))

    return observations


# ─────────────────────────────────────────────────────────────
# Detector: Earnings Signals
# ─────────────────────────────────────────────────────────────


def _detect_earnings_signals(earnings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract observations from earnings data."""
    observations: List[Dict[str, Any]] = []
    if not earnings:
        return observations

    surprise = earnings.get("earnings_surprise_history", earnings.get("surprise_history", {}))
    if not surprise:
        surprise = {}

    beats = surprise.get("beats", 0)
    misses = surprise.get("misses", 0)
    total = beats + misses + surprise.get("inline", 0)
    avg_surprise = surprise.get("average_surprise", "")
    pattern = surprise.get("pattern", "")

    # Consistent beater
    if total >= 4 and beats >= total * 0.75:
        observations.append(_obs(
            CATEGORY_BULLISH, SEVERITY_MEDIUM,
            "Consistent Earnings Beater",
            f"Beat estimates in {beats}/{total} recent quarters "
            f"(avg surprise {avg_surprise}). "
            "Consistent beaters tend to maintain momentum.",
            [f"Beats: {beats}/{total}", f"Avg surprise: {avg_surprise}",
             f"Pattern: {pattern}"],
            confidence=0.80, actionability="Medium — positive earnings trajectory",
            direction="bullish",
        ))
    elif total >= 4 and misses >= total * 0.5:
        observations.append(_obs(
            CATEGORY_BEARISH, SEVERITY_HIGH,
            "Frequent Earnings Misses",
            f"Missed estimates in {misses}/{total} recent quarters. "
            "Repeated misses erode analyst and investor confidence.",
            [f"Misses: {misses}/{total}", f"Pattern: {pattern}"],
            confidence=0.78, actionability="High — review guidance and estimates",
            direction="bearish",
        ))

    # Revenue trend
    trends = earnings.get("quarterly_trends", {})
    rev_trend = trends.get("revenue_trend", "")
    if "decelerat" in rev_trend.lower():
        observations.append(_obs(
            CATEGORY_WATCH, SEVERITY_MEDIUM,
            "Revenue Growth Decelerating",
            "Revenue growth has been decelerating across recent quarters. "
            "Monitor whether growth stabilises or continues declining.",
            [f"Revenue trend: {rev_trend}",
             f"QoQ growth: {trends.get('revenue_qoq_growth', 'N/A')}"],
            confidence=0.82, actionability="Low — monitor next earnings",
            direction="bearish",
        ))
    elif "accelerat" in rev_trend.lower():
        observations.append(_obs(
            CATEGORY_BULLISH, SEVERITY_MEDIUM,
            "Revenue Growth Accelerating",
            "Revenue growth is accelerating quarter-over-quarter, "
            "a strong positive signal for future earnings power.",
            [f"Revenue trend: {rev_trend}",
             f"QoQ growth: {trends.get('revenue_qoq_growth', 'N/A')}"],
            confidence=0.80, actionability="Medium — growth acceleration is a positive catalyst",
            direction="bullish",
        ))

    # Earnings quality
    quality = earnings.get("earnings_quality", {})
    eq_score = quality.get("score")
    if eq_score is not None:
        if eq_score >= 8:
            observations.append(_obs(
                CATEGORY_BULLISH, SEVERITY_LOW,
                "High Earnings Quality",
                f"Earnings quality score of {eq_score}/10 suggests earnings "
                "are driven by sustainable operations rather than one-time items.",
                [f"Quality score: {eq_score}/10",
                 f"Assessment: {quality.get('assessment', 'N/A')}"],
                confidence=0.75, direction="bullish",
            ))
        elif eq_score <= 4:
            observations.append(_obs(
                CATEGORY_RISK, SEVERITY_HIGH,
                "Low Earnings Quality",
                f"Earnings quality score of {eq_score}/10 raises concerns about "
                "sustainability — earnings may be inflated by non-recurring items.",
                [f"Quality score: {eq_score}/10",
                 f"Assessment: {quality.get('assessment', 'N/A')}"],
                confidence=0.78, direction="bearish",
            ))

    return observations


# ─────────────────────────────────────────────────────────────
# Detector: Performance Signals
# ─────────────────────────────────────────────────────────────


def _detect_performance_signals(perf: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract observations from performance tracking data."""
    observations: List[Dict[str, Any]] = []
    if not perf:
        return observations

    # --- Drawdown ---
    dd = perf.get("drawdown_analysis", {})
    max_dd = dd.get("max_drawdown")
    if max_dd is not None:
        try:
            dd_val = float(str(max_dd).replace("%", ""))
        except (ValueError, TypeError):
            dd_val = 0
        if dd_val < -20:
            observations.append(_obs(
                CATEGORY_RISK, SEVERITY_HIGH,
                "Significant Drawdown",
                f"Stock has experienced a maximum drawdown of {max_dd}, "
                "indicating substantial peak-to-trough decline.",
                [f"Max drawdown: {max_dd}",
                 f"Drawdown date: {dd.get('max_drawdown_date', 'N/A')}",
                 f"Recovery days: {dd.get('recovery_days', 'N/A')}"],
                confidence=0.85, actionability="High — assess risk tolerance",
                direction="bearish",
            ))

    # --- Benchmark alpha ---
    bench = perf.get("benchmark_comparison", {})
    spy_data = bench.get("vs_spy", bench.get("vs_SPY", {}))
    alpha_str = spy_data.get("1_year_alpha", spy_data.get("alpha", ""))
    if alpha_str:
        try:
            alpha_val = float(str(alpha_str).replace("%", "").replace("+", ""))
        except (ValueError, TypeError):
            alpha_val = 0
        if alpha_val > 10:
            observations.append(_obs(
                CATEGORY_BULLISH, SEVERITY_MEDIUM,
                "Strong Outperformance vs S&P 500",
                f"Generated {alpha_str} alpha over the S&P 500 in the past year, "
                "demonstrating strong relative strength.",
                [f"1Y alpha vs SPY: {alpha_str}",
                 f"Assessment: {spy_data.get('assessment', 'N/A')}"],
                confidence=0.70, direction="bullish",
            ))
        elif alpha_val < -10:
            observations.append(_obs(
                CATEGORY_BEARISH, SEVERITY_MEDIUM,
                "Significant Underperformance vs S&P 500",
                f"Lagging the S&P 500 by {alpha_str} over the past year. "
                "Persistent underperformance may signal fundamental issues.",
                [f"1Y alpha vs SPY: {alpha_str}",
                 f"Assessment: {spy_data.get('assessment', 'N/A')}"],
                confidence=0.70, direction="bearish",
            ))

    # --- Risk-adjusted returns ---
    risk_adj = perf.get("risk_adjusted_metrics", {})
    sharpe = risk_adj.get("sharpe_ratio", {})
    sharpe_val = sharpe.get("value") if isinstance(sharpe, dict) else sharpe
    if sharpe_val is not None:
        try:
            sv = float(sharpe_val)
        except (ValueError, TypeError):
            sv = None
        if sv is not None and sv < 0:
            observations.append(_obs(
                CATEGORY_RISK, SEVERITY_MEDIUM,
                "Negative Risk-Adjusted Returns",
                f"Sharpe ratio of {sv:.2f} indicates the stock has generated "
                "negative risk-adjusted returns — you'd be better off in cash.",
                [f"Sharpe ratio: {sv:.2f}"],
                confidence=0.75, direction="bearish",
            ))

    return observations


# ─────────────────────────────────────────────────────────────
# Confluence Detection
# ─────────────────────────────────────────────────────────────


def _detect_confluences(observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find groups of 3+ observations pointing in the same direction."""
    confluences: List[Dict[str, Any]] = []

    bullish = [o for o in observations if o.get("direction") == "bullish"]
    bearish = [o for o in observations if o.get("direction") == "bearish"]

    if len(bullish) >= 3:
        signals = [o["title"] for o in bullish[:5]]
        confluences.append({
            "direction": "Bullish",
            "signals": signals,
            "signal_count": len(bullish),
            "combined_strength": _strength_label(len(bullish)),
            "interpretation": (
                f"{len(bullish)} independent signals aligning bullishly across "
                "multiple analysis dimensions."
            ),
        })

    if len(bearish) >= 3:
        signals = [o["title"] for o in bearish[:5]]
        confluences.append({
            "direction": "Bearish",
            "signals": signals,
            "signal_count": len(bearish),
            "combined_strength": _strength_label(len(bearish)),
            "interpretation": (
                f"{len(bearish)} independent signals aligning bearishly — "
                "caution warranted."
            ),
        })

    return confluences


def _strength_label(count: int) -> str:
    if count >= 5:
        return "Very Strong"
    if count >= 4:
        return "Strong"
    if count >= 3:
        return "Moderate"
    return "Weak"


# ─────────────────────────────────────────────────────────────
# Anomaly Detection
# ─────────────────────────────────────────────────────────────


def _detect_anomalies(analyses: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect contradicting signals that warrant investigation."""
    anomalies: List[Dict[str, Any]] = []

    tech = analyses.get("technical", {})
    earnings = analyses.get("earnings", {})
    perf = analyses.get("performance", {})

    # RSI oversold but earnings declining
    rsi_val = tech.get("rsi", {}).get("value") if tech else None
    rev_trend = earnings.get("quarterly_trends", {}).get("revenue_trend", "") if earnings else ""

    if rsi_val is not None and rsi_val < 30 and "decelerat" in rev_trend.lower():
        anomalies.append({
            "description": "RSI oversold but revenue growth decelerating",
            "assessment": (
                "Stock appears technically cheap, but declining revenue growth "
                "suggests the selloff might be fundamentally justified. "
                "The oversold condition may be a value trap."
            ),
            "risk_level": "Medium",
        })

    # Strong outperformance but weak earnings
    bench = perf.get("benchmark_comparison", {}) if perf else {}
    spy_data = bench.get("vs_spy", bench.get("vs_SPY", {}))
    alpha_str = spy_data.get("1_year_alpha", "")
    surprise = earnings.get("earnings_surprise_history", {}) if earnings else {}
    misses = surprise.get("misses", 0)
    total_q = misses + surprise.get("beats", 0) + surprise.get("inline", 0)

    if alpha_str:
        try:
            alpha_val = float(str(alpha_str).replace("%", "").replace("+", ""))
        except (ValueError, TypeError):
            alpha_val = 0
        if alpha_val > 10 and total_q >= 4 and misses >= total_q * 0.5:
            anomalies.append({
                "description": "Strong price performance despite frequent earnings misses",
                "assessment": (
                    "Stock is outperforming the market despite missing earnings "
                    "estimates. This divergence may indicate speculative sentiment "
                    "or anticipation of a turnaround. Exercise caution."
                ),
                "risk_level": "High",
            })

    return anomalies


# ─────────────────────────────────────────────────────────────
# Ranking
# ─────────────────────────────────────────────────────────────

_SEVERITY_SCORE = {
    SEVERITY_CRITICAL: 4,
    SEVERITY_HIGH: 3,
    SEVERITY_MEDIUM: 2,
    SEVERITY_LOW: 1,
}


def _rank_observations(observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Score and rank observations by importance."""
    for obs in observations:
        sev_score = _SEVERITY_SCORE.get(obs.get("severity", ""), 1)
        conf_score = obs.get("confidence", 0.5) * 3  # max ~3
        score = sev_score + conf_score
        obs["_score"] = round(score, 2)

    ranked = sorted(observations, key=lambda o: o["_score"], reverse=True)
    for i, obs in enumerate(ranked, start=1):
        obs["rank"] = i
        obs.pop("_score", None)

    return ranked


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────


def generate_observations(
    symbol: str,
    analyses: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate ranked key observations from all analysis results.

    Args:
        symbol: Stock ticker symbol.
        analyses: Dict with keys like ``"technical"``, ``"fundamental"``,
                  ``"earnings"``, ``"performance"``, ``"peers"``.

    Returns:
        Dict with ``observations``, ``confluences``, ``anomalies``, and metadata.
    """
    start = datetime.now(timezone.utc)

    all_obs: List[Dict[str, Any]] = []

    # Run detectors
    all_obs.extend(_detect_technical_signals(analyses.get("technical", {})))
    all_obs.extend(_detect_valuation_signals(
        analyses.get("fundamental", {}),
        analyses.get("peers", {}),
    ))
    all_obs.extend(_detect_earnings_signals(analyses.get("earnings", {})))
    all_obs.extend(_detect_performance_signals(analyses.get("performance", {})))

    # Rank
    ranked = _rank_observations(all_obs)

    # Confluences & anomalies
    confluences = _detect_confluences(ranked)
    anomalies = _detect_anomalies(analyses)

    # Boost severity of top observation if we have a strong confluence
    if confluences and ranked:
        for c in confluences:
            if c["signal_count"] >= 4 and ranked[0]["severity"] != SEVERITY_CRITICAL:
                ranked[0]["severity"] = SEVERITY_CRITICAL

    exec_time = (datetime.now(timezone.utc) - start).total_seconds()

    # Summary counts
    bullish_count = sum(1 for o in ranked if o.get("direction") == "bullish")
    bearish_count = sum(1 for o in ranked if o.get("direction") == "bearish")

    if bullish_count > bearish_count + 1:
        overall_bias = "Bullish"
    elif bearish_count > bullish_count + 1:
        overall_bias = "Bearish"
    else:
        overall_bias = "Mixed / Neutral"

    return {
        "symbol": symbol,
        "total_observations": len(ranked),
        "overall_bias": overall_bias,
        "bullish_signals": bullish_count,
        "bearish_signals": bearish_count,
        "observations": ranked,
        "confluences": confluences,
        "anomalies": anomalies,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "execution_time_seconds": round(exec_time, 3),
    }
