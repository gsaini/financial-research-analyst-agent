"""
Fama-French Factor Model (Phase 4).

Decomposes stock returns into market, size (SMB), value (HML),
profitability (RMW), and investment (CMA) factors using proxy ETFs.

Usage::

    from src.tools.factor_model import analyze_factor_exposure
    result = analyze_factor_exposure("AAPL")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)

_TRADING_DAYS = 252

# Factor proxy ETFs (Fama-French factors approximated by ETFs)
_FACTOR_PROXIES = {
    "market": "SPY",      # Market excess return
    "size": "IWM",        # Small cap (Russell 2000) — SMB proxy
    "value": "IWD",       # Value (Russell 1000 Value) — HML proxy
    "momentum": "MTUM",   # Momentum factor
    "quality": "QUAL",    # Quality factor (profitability proxy)
    "low_vol": "USMV",    # Low volatility factor
}

_RISK_FREE_PROXY = "SHV"  # Short-term treasury ETF as risk-free proxy


def _fetch_aligned_returns(
    symbol: str, period: str = "2y"
) -> Optional[pd.DataFrame]:
    """Fetch and align returns for symbol and factor proxies."""
    try:
        provider = get_provider()
        all_symbols = [symbol] + list(_FACTOR_PROXIES.values()) + [_RISK_FREE_PROXY]

        prices = {}
        for sym in all_symbols:
            hist = provider.get_history(sym, period=period, interval="1d")
            if hist is not None and not hist.empty and "Close" in hist.columns:
                prices[sym] = hist["Close"]

        if symbol not in prices or len(prices) < 3:
            return None

        df = pd.DataFrame(prices).dropna()
        return df.pct_change().dropna()

    except Exception as e:
        logger.error(f"Factor data fetch failed: {e}")
        return None


def analyze_factor_exposure(symbol: str) -> Dict[str, Any]:
    """
    Decompose stock returns into Fama-French-style factors.

    Uses multivariate regression of stock excess returns on factor
    excess returns.

    Args:
        symbol: Stock ticker.

    Returns:
        Dict with factor betas, R-squared, alpha, and interpretations.
    """
    try:
        returns = _fetch_aligned_returns(symbol)
        if returns is None:
            return {"symbol": symbol, "error": "Could not fetch factor data"}

        # Excess returns (over risk-free proxy)
        rf = returns.get(_RISK_FREE_PROXY, pd.Series(0, index=returns.index))
        stock_excess = returns[symbol] - rf

        # Build factor returns
        factors = {}
        for factor_name, etf in _FACTOR_PROXIES.items():
            if etf in returns.columns:
                factors[factor_name] = returns[etf] - rf

        if len(factors) < 2:
            return {"symbol": symbol, "error": "Insufficient factor proxy data"}

        factor_df = pd.DataFrame(factors)

        # Multivariate regression: stock_excess = alpha + sum(beta_i * factor_i) + epsilon
        X = factor_df.values
        y = stock_excess.values

        # Add intercept
        X_with_intercept = np.column_stack([np.ones(len(X)), X])

        # OLS: beta = (X'X)^-1 X'y
        try:
            betas = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            return {"symbol": symbol, "error": "Regression failed (singular matrix)"}

        alpha = betas[0]
        factor_betas = betas[1:]

        # R-squared
        y_pred = X_with_intercept @ betas
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # Annualize alpha
        annual_alpha = alpha * _TRADING_DAYS

        # Build results
        factor_names = list(factors.keys())
        exposures = {}
        for i, name in enumerate(factor_names):
            beta = float(factor_betas[i])
            exposures[name] = {
                "beta": round(beta, 3),
                "proxy_etf": _FACTOR_PROXIES.get(name, ""),
                "interpretation": _interpret_factor(name, beta),
            }

        # Dominant factor
        abs_betas = {n: abs(exposures[n]["beta"]) for n in factor_names}
        dominant = max(abs_betas, key=abs_betas.get) if abs_betas else "market"

        return {
            "symbol": symbol,
            "alpha": {
                "daily": round(alpha, 6),
                "annualized_pct": round(annual_alpha * 100, 2),
                "interpretation": (
                    f"Positive alpha of {annual_alpha*100:.2f}% — stock generates excess returns beyond factor exposure"
                    if annual_alpha > 0.01
                    else f"Negative alpha of {annual_alpha*100:.2f}% — stock underperforms its factor exposure"
                    if annual_alpha < -0.01
                    else "Near-zero alpha — returns are well-explained by factor exposure"
                ),
            },
            "r_squared": round(r_squared, 3),
            "r_squared_interpretation": (
                "High explanatory power — factors explain most of the return variation"
                if r_squared > 0.7
                else "Moderate — factors explain some variation but stock-specific risk is significant"
                if r_squared > 0.4
                else "Low — stock has high idiosyncratic risk not captured by factors"
            ),
            "factor_exposures": exposures,
            "dominant_factor": dominant,
            "style_classification": _classify_style(exposures),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Factor analysis failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def compare_factor_exposures(symbols: List[str]) -> Dict[str, Any]:
    """Compare factor exposures across multiple stocks."""
    results = {}
    for sym in symbols:
        results[sym] = analyze_factor_exposure(sym)

    # Summary comparison
    factor_comparison = {}
    for factor in _FACTOR_PROXIES:
        factor_comparison[factor] = {
            sym: res.get("factor_exposures", {}).get(factor, {}).get("beta", 0)
            for sym, res in results.items()
            if "error" not in res
        }

    return {
        "symbols": symbols,
        "individual": results,
        "factor_comparison": factor_comparison,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def _interpret_factor(name: str, beta: float) -> str:
    """Human-readable interpretation of a factor beta."""
    strength = "strong" if abs(beta) > 0.5 else "moderate" if abs(beta) > 0.2 else "weak"

    interpretations = {
        "market": f"{'High' if beta > 1.1 else 'Low' if beta < 0.9 else 'Market-like'} market sensitivity (beta={beta:.2f})",
        "size": f"{'Small-cap' if beta > 0.2 else 'Large-cap' if beta < -0.2 else 'Mid-cap'} tilt ({strength})",
        "value": f"{'Value' if beta > 0.2 else 'Growth' if beta < -0.2 else 'Blend'} style ({strength})",
        "momentum": f"{'Positive' if beta > 0.2 else 'Negative' if beta < -0.2 else 'Neutral'} momentum exposure ({strength})",
        "quality": f"{'High' if beta > 0.2 else 'Low' if beta < -0.2 else 'Average'} quality exposure ({strength})",
        "low_vol": f"{'Defensive' if beta > 0.2 else 'Aggressive' if beta < -0.2 else 'Neutral'} volatility profile ({strength})",
    }
    return interpretations.get(name, f"Beta={beta:.2f}")


def _classify_style(exposures: Dict[str, Any]) -> str:
    """Classify stock style based on factor exposures."""
    value_beta = exposures.get("value", {}).get("beta", 0)
    size_beta = exposures.get("size", {}).get("beta", 0)
    momentum_beta = exposures.get("momentum", {}).get("beta", 0)

    style_parts = []
    if size_beta > 0.3:
        style_parts.append("Small-Cap")
    elif size_beta < -0.3:
        style_parts.append("Large-Cap")

    if value_beta > 0.3:
        style_parts.append("Value")
    elif value_beta < -0.3:
        style_parts.append("Growth")
    else:
        style_parts.append("Blend")

    if momentum_beta > 0.3:
        style_parts.append("Momentum")

    return " ".join(style_parts) if style_parts else "Core"
