"""
Predefined Trading Strategy Definitions (Feature 8).

Each strategy is a function that receives a price array, the current bar
index, and pre-computed indicator values, and returns one of:
    "BUY"  – enter a long position
    "SELL" – exit the current position
    "HOLD" – do nothing

A central STRATEGIES registry maps human-readable names to their
implementation function and description.
"""

from typing import Any, Callable, Dict, List, Optional

import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Helper: compute indicators on-the-fly for a given bar index
# ─────────────────────────────────────────────────────────────


def _rsi(prices: np.ndarray, idx: int, period: int = 14) -> Optional[float]:
    """Return RSI value at *idx*, or None if insufficient history."""
    if idx < period + 1:
        return None
    window = prices[idx - period : idx + 1]
    deltas = np.diff(window)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def _sma(prices: np.ndarray, idx: int, period: int) -> Optional[float]:
    """Return simple moving average ending at *idx*."""
    if idx < period - 1:
        return None
    return float(np.mean(prices[idx - period + 1 : idx + 1]))


def _ema(prices: np.ndarray, idx: int, period: int) -> Optional[float]:
    """Return exponential moving average ending at *idx*."""
    if idx < period - 1:
        return None
    alpha = 2.0 / (period + 1)
    window = prices[: idx + 1]
    ema_val = window[0]
    for p in window[1:]:
        ema_val = alpha * p + (1 - alpha) * ema_val
    return float(ema_val)


def _macd_histogram(prices: np.ndarray, idx: int,
                    fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[float]:
    """Return MACD histogram value at *idx*."""
    if idx < slow + signal - 1:
        return None

    # Compute full EMA arrays up to idx
    window = prices[: idx + 1]
    alpha_fast = 2.0 / (fast + 1)
    alpha_slow = 2.0 / (slow + 1)

    ema_fast = np.zeros(len(window))
    ema_slow = np.zeros(len(window))
    ema_fast[0] = ema_slow[0] = window[0]
    for i in range(1, len(window)):
        ema_fast[i] = alpha_fast * window[i] + (1 - alpha_fast) * ema_fast[i - 1]
        ema_slow[i] = alpha_slow * window[i] + (1 - alpha_slow) * ema_slow[i - 1]

    macd_line = ema_fast - ema_slow

    alpha_sig = 2.0 / (signal + 1)
    sig_line = np.zeros(len(macd_line))
    sig_line[0] = macd_line[0]
    for i in range(1, len(macd_line)):
        sig_line[i] = alpha_sig * macd_line[i] + (1 - alpha_sig) * sig_line[i - 1]

    return float(macd_line[-1] - sig_line[-1])


def _bollinger(prices: np.ndarray, idx: int,
               period: int = 20, num_std: float = 2.0):
    """Return (lower_band, upper_band) at *idx*, or (None, None)."""
    if idx < period - 1:
        return None, None
    window = prices[idx - period + 1 : idx + 1]
    mean = float(np.mean(window))
    std = float(np.std(window))
    return mean - num_std * std, mean + num_std * std


# ─────────────────────────────────────────────────────────────
# Strategy 1: RSI Reversal
# ─────────────────────────────────────────────────────────────


def rsi_reversal(prices: np.ndarray, idx: int, **kwargs) -> str:
    """
    Buy when RSI < 30 (oversold), Sell when RSI > 70 (overbought).
    """
    rsi = _rsi(prices, idx, period=kwargs.get("rsi_period", 14))
    if rsi is None:
        return "HOLD"
    if rsi < 30:
        return "BUY"
    if rsi > 70:
        return "SELL"
    return "HOLD"


# ─────────────────────────────────────────────────────────────
# Strategy 2: MACD Crossover
# ─────────────────────────────────────────────────────────────


def macd_crossover(prices: np.ndarray, idx: int, **kwargs) -> str:
    """
    Buy when MACD histogram crosses above zero, Sell when below zero.
    """
    if idx < 1:
        return "HOLD"
    curr = _macd_histogram(prices, idx)
    prev = _macd_histogram(prices, idx - 1)
    if curr is None or prev is None:
        return "HOLD"
    if curr > 0 and prev <= 0:
        return "BUY"
    if curr < 0 and prev >= 0:
        return "SELL"
    return "HOLD"


# ─────────────────────────────────────────────────────────────
# Strategy 3: Golden / Death Cross
# ─────────────────────────────────────────────────────────────


def golden_death_cross(prices: np.ndarray, idx: int, **kwargs) -> str:
    """
    Buy when 50-SMA crosses above 200-SMA (golden cross).
    Sell when 50-SMA crosses below 200-SMA (death cross).
    """
    if idx < 1:
        return "HOLD"
    sma50_now = _sma(prices, idx, 50)
    sma200_now = _sma(prices, idx, 200)
    sma50_prev = _sma(prices, idx - 1, 50)
    sma200_prev = _sma(prices, idx - 1, 200)

    if any(v is None for v in [sma50_now, sma200_now, sma50_prev, sma200_prev]):
        return "HOLD"

    if sma50_now > sma200_now and sma50_prev <= sma200_prev:
        return "BUY"
    if sma50_now < sma200_now and sma50_prev >= sma200_prev:
        return "SELL"
    return "HOLD"


# ─────────────────────────────────────────────────────────────
# Strategy 4: Bollinger Band Mean Reversion
# ─────────────────────────────────────────────────────────────


def bollinger_reversion(prices: np.ndarray, idx: int, **kwargs) -> str:
    """
    Buy when price touches lower Bollinger Band.
    Sell when price touches upper Bollinger Band.
    """
    lower, upper = _bollinger(prices, idx, period=20, num_std=2.0)
    if lower is None or upper is None:
        return "HOLD"
    price = prices[idx]
    if price <= lower:
        return "BUY"
    if price >= upper:
        return "SELL"
    return "HOLD"


# ─────────────────────────────────────────────────────────────
# Strategy 5: Momentum Composite
# ─────────────────────────────────────────────────────────────


def momentum_composite(prices: np.ndarray, idx: int, **kwargs) -> str:
    """
    Buy when:  Price > 200-SMA AND RSI > 50 AND MACD histogram > 0.
    Sell when: Price < 200-SMA OR RSI < 40.
    """
    sma200 = _sma(prices, idx, 200)
    rsi = _rsi(prices, idx)
    macd_hist = _macd_histogram(prices, idx)

    if sma200 is None or rsi is None or macd_hist is None:
        return "HOLD"

    price = prices[idx]

    # Buy condition — all three must agree
    if price > sma200 and rsi > 50 and macd_hist > 0:
        return "BUY"

    # Sell condition — any bearish trigger
    if price < sma200 or rsi < 40:
        return "SELL"

    return "HOLD"


# ─────────────────────────────────────────────────────────────
# Strategy Registry
# ─────────────────────────────────────────────────────────────

StrategyFn = Callable[[np.ndarray, int], str]

STRATEGIES: Dict[str, Dict[str, Any]] = {
    "rsi_reversal": {
        "fn": rsi_reversal,
        "name": "RSI Reversal",
        "description": "Buy when RSI < 30 (oversold), sell when RSI > 70 (overbought).",
    },
    "macd_crossover": {
        "fn": macd_crossover,
        "name": "MACD Crossover",
        "description": "Buy when MACD histogram crosses above zero, sell when it crosses below.",
    },
    "golden_death_cross": {
        "fn": golden_death_cross,
        "name": "Golden / Death Cross",
        "description": "Buy on 50-SMA crossing above 200-SMA, sell on the reverse.",
    },
    "bollinger_reversion": {
        "fn": bollinger_reversion,
        "name": "Bollinger Band Mean Reversion",
        "description": "Buy at lower Bollinger Band, sell at upper Bollinger Band.",
    },
    "momentum_composite": {
        "fn": momentum_composite,
        "name": "Momentum Composite",
        "description": "Buy when price > 200-SMA, RSI > 50, and MACD > 0; sell when bearish.",
    },
}


def get_strategy(name: str) -> Optional[Dict[str, Any]]:
    """Look up a strategy by its registry key."""
    return STRATEGIES.get(name)


def list_strategy_names() -> List[str]:
    """Return all available strategy keys."""
    return list(STRATEGIES.keys())
