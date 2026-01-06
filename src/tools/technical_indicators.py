"""
Technical indicator calculation tools.
"""

from typing import Any, Dict, List, Tuple
import numpy as np
from src.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_rsi(prices: List[float], period: int = 14) -> Dict[str, Any]:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return {"error": "Insufficient data for RSI calculation"}
    
    prices_array = np.array(prices)
    deltas = np.diff(prices_array)
    
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    rs = avg_gain / avg_loss if avg_loss != 0 else 100
    rsi = 100 - (100 / (1 + rs))
    
    if rsi > 70: signal = "OVERBOUGHT"
    elif rsi < 30: signal = "OVERSOLD"
    else: signal = "NEUTRAL"
    
    return {"value": round(rsi, 2), "period": period, "signal": signal,
            "interpretation": f"RSI at {rsi:.1f} indicates {signal.lower()} conditions"}


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Any]:
    """Calculate MACD indicator."""
    if len(prices) < slow + signal:
        return {"error": "Insufficient data for MACD calculation"}
    
    prices_array = np.array(prices)
    
    def ema(data, period):
        alpha = 2 / (period + 1)
        ema_values = np.zeros_like(data)
        ema_values[0] = data[0]
        for i in range(1, len(data)):
            ema_values[i] = alpha * data[i] + (1 - alpha) * ema_values[i-1]
        return ema_values
    
    fast_ema = ema(prices_array, fast)
    slow_ema = ema(prices_array, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    current_hist = histogram[-1]
    prev_hist = histogram[-2]
    
    if current_hist > 0 and prev_hist <= 0: crossover = "bullish"
    elif current_hist < 0 and prev_hist >= 0: crossover = "bearish"
    else: crossover = "none"
    
    return {
        "macd_line": round(macd_line[-1], 4),
        "signal_line": round(signal_line[-1], 4),
        "histogram": round(histogram[-1], 4),
        "crossover": crossover,
        "trend": "bullish" if histogram[-1] > 0 else "bearish"
    }


def calculate_moving_averages(prices: List[float], periods: List[int] = [20, 50, 200]) -> Dict[str, Any]:
    """Calculate Simple and Exponential Moving Averages."""
    prices_array = np.array(prices)
    result = {"current_price": prices_array[-1]}
    
    for period in periods:
        if len(prices_array) >= period:
            sma = np.mean(prices_array[-period:])
            
            alpha = 2 / (period + 1)
            ema = prices_array[0]
            for price in prices_array[1:]:
                ema = alpha * price + (1 - alpha) * ema
            
            result[f"sma_{period}"] = round(sma, 2)
            result[f"ema_{period}"] = round(ema, 2)
    
    # Trend analysis
    if "sma_50" in result and "sma_200" in result:
        if result["sma_50"] > result["sma_200"]: result["trend"] = "bullish"
        else: result["trend"] = "bearish"
    
    return result


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, Any]:
    """Calculate Bollinger Bands."""
    if len(prices) < period:
        return {"error": "Insufficient data"}
    
    prices_array = np.array(prices)
    sma = np.mean(prices_array[-period:])
    std = np.std(prices_array[-period:])
    
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    current = prices_array[-1]
    
    bandwidth = (upper - lower) / sma * 100
    percent_b = (current - lower) / (upper - lower) if upper != lower else 0.5
    
    if current > upper: position = "above_upper"
    elif current < lower: position = "below_lower"
    else: position = "within_bands"
    
    return {
        "upper_band": round(upper, 2),
        "middle_band": round(sma, 2),
        "lower_band": round(lower, 2),
        "bandwidth": round(bandwidth, 2),
        "percent_b": round(percent_b, 2),
        "position": position
    }


def identify_support_resistance(price_data: Dict[str, Any], window: int = 10) -> Dict[str, Any]:
    """Identify support and resistance levels."""
    highs = np.array(price_data.get("highs", price_data.get("closes", [])))
    lows = np.array(price_data.get("lows", price_data.get("closes", [])))
    closes = np.array(price_data.get("closes", []))
    
    if len(closes) < window * 2:
        return {"error": "Insufficient data"}
    
    # Find local maxima and minima
    resistance_levels = []
    support_levels = []
    
    for i in range(window, len(highs) - window):
        if highs[i] == max(highs[i-window:i+window+1]):
            resistance_levels.append(highs[i])
        if lows[i] == min(lows[i-window:i+window+1]):
            support_levels.append(lows[i])
    
    # Cluster levels
    current_price = closes[-1]
    
    resistance = [r for r in sorted(set(resistance_levels)) if r > current_price][:3]
    support = [s for s in sorted(set(support_levels), reverse=True) if s < current_price][:3]
    
    return {
        "resistance_levels": [round(r, 2) for r in resistance],
        "support_levels": [round(s, 2) for s in support],
        "current_price": round(current_price, 2),
        "nearest_resistance": round(resistance[0], 2) if resistance else None,
        "nearest_support": round(support[0], 2) if support else None
    }


def detect_patterns(price_data: Dict[str, Any]) -> Dict[str, Any]:
    """Detect chart patterns."""
    closes = np.array(price_data.get("closes", []))
    
    if len(closes) < 20:
        return {"patterns_detected": [], "message": "Insufficient data"}
    
    patterns = []
    
    # Simple trend detection
    short_term = np.mean(closes[-5:])
    medium_term = np.mean(closes[-20:])
    
    if short_term > medium_term * 1.02:
        patterns.append({"name": "Uptrend", "confidence": 0.7, "implication": "bullish"})
    elif short_term < medium_term * 0.98:
        patterns.append({"name": "Downtrend", "confidence": 0.7, "implication": "bearish"})
    else:
        patterns.append({"name": "Consolidation", "confidence": 0.6, "implication": "neutral"})
    
    # Volatility check
    volatility = np.std(closes[-10:]) / np.mean(closes[-10:])
    if volatility > 0.05:
        patterns.append({"name": "High Volatility", "confidence": 0.8, "implication": "caution"})
    
    return {"patterns_detected": patterns, "analysis_period": len(closes)}
