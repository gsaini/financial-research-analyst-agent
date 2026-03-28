"""
Anomaly Detection Tool (Phase 2.4).

Detects volume anomalies, price anomalies, and pattern breaks in
stock data using Z-score and regime change methods.

Usage::

    from src.tools.anomaly_detector import detect_volume_anomalies
    result = detect_volume_anomalies("AAPL")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)


def detect_volume_anomalies(
    symbol: str,
    lookback_days: int = 90,
    z_threshold: float = 2.5,
) -> Dict[str, Any]:
    """
    Detect days with anomalous trading volume.

    Uses Z-score vs 20-day rolling mean/std.

    Args:
        symbol: Stock ticker.
        lookback_days: Number of days to analyze.
        z_threshold: Z-score threshold for anomaly.

    Returns:
        Dict with anomaly dates, Z-scores, and interpretation.
    """
    try:
        provider = get_provider()
        hist = provider.get_history(symbol, period="1y", interval="1d")

        if hist is None or len(hist) < 30:
            return {"symbol": symbol, "error": "Insufficient data"}

        hist = hist.tail(lookback_days)
        volume = hist["Volume"]
        close = hist["Close"]

        # Rolling stats
        rolling_mean = volume.rolling(20).mean()
        rolling_std = volume.rolling(20).std()

        # Z-scores
        z_scores = (volume - rolling_mean) / rolling_std.replace(0, np.nan)
        z_scores = z_scores.dropna()

        # Find anomalies
        anomalies = z_scores[z_scores.abs() > z_threshold]

        anomaly_list = []
        for date, z in anomalies.items():
            date_str = str(date.date()) if hasattr(date, "date") else str(date)
            price_change = 0
            if date in close.index:
                idx = close.index.get_loc(date)
                if idx > 0:
                    price_change = float((close.iloc[idx] / close.iloc[idx - 1] - 1) * 100)

            anomaly_list.append({
                "date": date_str,
                "z_score": round(float(z), 2),
                "volume": int(volume.loc[date]) if date in volume.index else 0,
                "avg_volume": int(rolling_mean.loc[date]) if date in rolling_mean.index else 0,
                "price_change_pct": round(price_change, 2),
                "type": "surge" if z > 0 else "drought",
            })

        return {
            "symbol": symbol,
            "lookback_days": lookback_days,
            "z_threshold": z_threshold,
            "anomaly_count": len(anomaly_list),
            "anomalies": sorted(anomaly_list, key=lambda x: abs(x["z_score"]), reverse=True),
            "interpretation": (
                f"Found {len(anomaly_list)} volume anomalies in the last {lookback_days} days. "
                + ("Volume surges often indicate institutional activity or news events."
                   if anomaly_list else "No unusual volume detected — normal trading activity.")
            ),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Volume anomaly detection failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def detect_price_anomalies(
    symbol: str,
    lookback_days: int = 90,
    z_threshold: float = 2.5,
) -> Dict[str, Any]:
    """
    Detect days with anomalous price movements.

    Flags extreme daily returns and gap openings.

    Args:
        symbol: Stock ticker.
        lookback_days: Number of days to analyze.
        z_threshold: Z-score threshold.

    Returns:
        Dict with anomaly dates, magnitude, and potential causes.
    """
    try:
        provider = get_provider()
        hist = provider.get_history(symbol, period="1y", interval="1d")

        if hist is None or len(hist) < 30:
            return {"symbol": symbol, "error": "Insufficient data"}

        hist = hist.tail(lookback_days + 60)  # Extra for rolling stats
        close = hist["Close"]
        open_price = hist["Open"]

        # Daily returns
        returns = close.pct_change().dropna()

        # Rolling Z-scores (60-day)
        rolling_mean = returns.rolling(60).mean()
        rolling_std = returns.rolling(60).std()
        z_scores = (returns - rolling_mean) / rolling_std.replace(0, np.nan)
        z_scores = z_scores.dropna().tail(lookback_days)

        # Return anomalies
        anomalies = z_scores[z_scores.abs() > z_threshold]

        anomaly_list = []
        for date, z in anomalies.items():
            date_str = str(date.date()) if hasattr(date, "date") else str(date)
            ret = float(returns.loc[date] * 100) if date in returns.index else 0

            anomaly_list.append({
                "date": date_str,
                "z_score": round(float(z), 2),
                "return_pct": round(ret, 2),
                "direction": "up" if ret > 0 else "down",
                "magnitude": "extreme" if abs(z) > 3.5 else "significant",
            })

        # Gap detection (open vs previous close > 2%)
        gaps = []
        for i in range(1, min(lookback_days, len(hist))):
            prev_close = float(close.iloc[-(i + 1)])
            curr_open = float(open_price.iloc[-i])
            if prev_close > 0:
                gap_pct = (curr_open / prev_close - 1) * 100
                if abs(gap_pct) > 2:
                    date = hist.index[-i]
                    date_str = str(date.date()) if hasattr(date, "date") else str(date)
                    gaps.append({
                        "date": date_str,
                        "gap_pct": round(gap_pct, 2),
                        "direction": "gap_up" if gap_pct > 0 else "gap_down",
                    })

        return {
            "symbol": symbol,
            "lookback_days": lookback_days,
            "return_anomalies": {
                "count": len(anomaly_list),
                "anomalies": sorted(anomaly_list, key=lambda x: abs(x["z_score"]), reverse=True),
            },
            "gaps": {
                "count": len(gaps),
                "events": sorted(gaps, key=lambda x: abs(x["gap_pct"]), reverse=True)[:10],
            },
            "interpretation": (
                f"Found {len(anomaly_list)} extreme return days and {len(gaps)} gap events. "
                + ("Frequent anomalies suggest high event risk." if len(anomaly_list) > 3
                   else "Normal price behavior with few outliers.")
            ),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Price anomaly detection failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def detect_pattern_breaks(symbol: str) -> Dict[str, Any]:
    """
    Detect regime changes in volatility, trend, and volume.

    Compares recent 20-day behavior to 60-day baseline.
    """
    try:
        provider = get_provider()
        hist = provider.get_history(symbol, period="6mo", interval="1d")

        if hist is None or len(hist) < 80:
            return {"symbol": symbol, "error": "Insufficient data (need 80+ days)"}

        close = hist["Close"]
        volume = hist["Volume"]
        returns = close.pct_change().dropna()

        breaks = []

        # 1. Volatility regime change
        recent_vol = float(returns.tail(20).std())
        baseline_vol = float(returns.tail(60).head(40).std())
        if baseline_vol > 0:
            vol_ratio = recent_vol / baseline_vol
            if vol_ratio > 1.5:
                breaks.append({
                    "type": "volatility_expansion",
                    "significance": round(vol_ratio, 2),
                    "detail": f"Recent 20-day vol is {vol_ratio:.1f}x the prior baseline — regime shift to higher volatility.",
                })
            elif vol_ratio < 0.5:
                breaks.append({
                    "type": "volatility_compression",
                    "significance": round(1 / vol_ratio, 2),
                    "detail": f"Recent 20-day vol is {vol_ratio:.1f}x the prior baseline — compression may precede a large move.",
                })

        # 2. Trend break (price crossing SMA-50)
        sma_50 = close.rolling(50).mean()
        if len(sma_50.dropna()) >= 20:
            recent_above = float(close.iloc[-1]) > float(sma_50.iloc[-1])
            past_above = float(close.iloc[-20]) > float(sma_50.iloc[-20])
            if recent_above and not past_above:
                breaks.append({
                    "type": "bullish_trend_break",
                    "significance": 1.0,
                    "detail": "Price has crossed above the 50-day SMA — potential trend reversal to bullish.",
                })
            elif not recent_above and past_above:
                breaks.append({
                    "type": "bearish_trend_break",
                    "significance": 1.0,
                    "detail": "Price has fallen below the 50-day SMA — potential trend reversal to bearish.",
                })

        # 3. Volume regime change
        recent_vol_avg = float(volume.tail(20).mean())
        baseline_vol_avg = float(volume.tail(60).head(40).mean())
        if baseline_vol_avg > 0:
            vol_change = recent_vol_avg / baseline_vol_avg
            if vol_change > 2.0:
                breaks.append({
                    "type": "volume_surge_regime",
                    "significance": round(vol_change, 2),
                    "detail": f"Average volume has increased {vol_change:.1f}x — sustained elevated interest.",
                })
            elif vol_change < 0.5:
                breaks.append({
                    "type": "volume_dry_up",
                    "significance": round(1 / vol_change, 2),
                    "detail": "Volume has dropped significantly — reduced market interest or consolidation.",
                })

        return {
            "symbol": symbol,
            "breaks_detected": len(breaks),
            "breaks": breaks,
            "interpretation": (
                f"Detected {len(breaks)} pattern break(s). "
                + ("Regime changes suggest the stock is entering a new phase."
                   if breaks else "No significant regime changes detected — stable behavior.")
            ),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Pattern break detection failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}
