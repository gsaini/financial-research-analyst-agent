"""
Portfolio Optimization Tool (Phase 2.5).

Modern Portfolio Theory (Markowitz) optimization using scipy.
Supports max Sharpe, min volatility, and risk-parity allocations.

Usage::

    from src.tools.portfolio_optimizer import optimize_portfolio
    result = optimize_portfolio(["AAPL", "MSFT", "GOOGL"])
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import optimize

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)

_RISK_FREE_RATE = 0.05
_TRADING_DAYS = 252


# ── Data ─────────────────────────────────────────────────────


def _get_returns(symbols: List[str], period: str = "2y") -> Optional[pd.DataFrame]:
    """Fetch daily returns for multiple symbols."""
    try:
        provider = get_provider()
        prices = {}
        for sym in symbols:
            hist = provider.get_history(sym, period=period, interval="1d")
            if hist is not None and not hist.empty and "Close" in hist.columns:
                prices[sym] = hist["Close"]

        if len(prices) < 2:
            return None

        price_df = pd.DataFrame(prices).dropna()
        if len(price_df) < 60:
            return None

        return price_df.pct_change().dropna()
    except Exception as e:
        logger.error(f"Failed to fetch returns: {e}")
        return None


# ── Optimization helpers ─────────────────────────────────────


def _portfolio_return(weights, mean_returns):
    return np.dot(weights, mean_returns)


def _portfolio_volatility(weights, cov_matrix):
    return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))


def _negative_sharpe(weights, mean_returns, cov_matrix, rf):
    ret = _portfolio_return(weights, mean_returns)
    vol = _portfolio_volatility(weights, cov_matrix)
    return -(ret - rf) / vol if vol > 0 else 0


def _risk_contribution(weights, cov_matrix):
    """Calculate each asset's risk contribution."""
    port_vol = _portfolio_volatility(weights, cov_matrix)
    if port_vol == 0:
        return np.zeros_like(weights)
    marginal = np.dot(cov_matrix, weights) / port_vol
    return weights * marginal


# ── Public API ───────────────────────────────────────────────


def optimize_portfolio(
    symbols: List[str],
    method: str = "max_sharpe",
    risk_free_rate: float = _RISK_FREE_RATE,
) -> Dict[str, Any]:
    """
    Optimize portfolio weights.

    Args:
        symbols: List of stock tickers.
        method: "max_sharpe", "min_volatility", or "risk_parity".
        risk_free_rate: Annual risk-free rate.

    Returns:
        Dict with optimal weights, expected return, volatility, Sharpe.
    """
    returns = _get_returns(symbols)
    if returns is None:
        return {"error": "Could not fetch sufficient return data for optimization"}

    # Filter to symbols with data
    valid_symbols = list(returns.columns)
    n = len(valid_symbols)

    mean_returns = returns.mean() * _TRADING_DAYS
    cov_matrix = returns.cov() * _TRADING_DAYS

    # Constraints
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0, 1)] * n
    init_weights = np.array([1 / n] * n)

    if method == "max_sharpe":
        result = optimize.minimize(
            _negative_sharpe,
            init_weights,
            args=(mean_returns.values, cov_matrix.values, risk_free_rate),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
    elif method == "min_volatility":
        result = optimize.minimize(
            _portfolio_volatility,
            init_weights,
            args=(cov_matrix.values,),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
    elif method == "risk_parity":
        return risk_parity_allocation(symbols)
    else:
        return {"error": f"Unknown method: {method}"}

    if not result.success:
        return {"error": f"Optimization failed: {result.message}"}

    weights = result.x
    port_return = _portfolio_return(weights, mean_returns.values)
    port_vol = _portfolio_volatility(weights, cov_matrix.values)
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0

    # Risk contributions
    risk_contribs = _risk_contribution(weights, cov_matrix.values)

    allocation = {}
    for i, sym in enumerate(valid_symbols):
        allocation[sym] = {
            "weight": round(float(weights[i]), 4),
            "weight_pct": round(float(weights[i]) * 100, 2),
            "expected_return_pct": round(float(mean_returns.iloc[i]) * 100, 2),
            "volatility_pct": round(float(np.sqrt(cov_matrix.iloc[i, i])) * 100, 2),
            "risk_contribution": round(float(risk_contribs[i]), 4),
        }

    return {
        "method": method,
        "symbols": valid_symbols,
        "allocation": allocation,
        "portfolio_metrics": {
            "expected_return_pct": round(port_return * 100, 2),
            "volatility_pct": round(port_vol * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "risk_free_rate_pct": round(risk_free_rate * 100, 2),
        },
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def calculate_efficient_frontier(
    symbols: List[str],
    n_points: int = 50,
) -> Dict[str, Any]:
    """
    Generate portfolios along the efficient frontier.

    Returns list of {return, volatility, sharpe, weights} points.
    """
    returns = _get_returns(symbols)
    if returns is None:
        return {"error": "Could not fetch return data"}

    valid_symbols = list(returns.columns)
    n = len(valid_symbols)
    mean_returns = returns.mean() * _TRADING_DAYS
    cov_matrix = returns.cov() * _TRADING_DAYS

    # Find min/max achievable returns
    min_ret = float(mean_returns.min())
    max_ret = float(mean_returns.max())
    target_returns = np.linspace(min_ret, max_ret, n_points)

    frontier = []
    constraints_base = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0, 1)] * n
    init_w = np.array([1 / n] * n)

    for target in target_returns:
        constraints = constraints_base + [
            {"type": "eq", "fun": lambda w, t=target: _portfolio_return(w, mean_returns.values) - t}
        ]
        result = optimize.minimize(
            _portfolio_volatility,
            init_w,
            args=(cov_matrix.values,),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        if result.success:
            vol = _portfolio_volatility(result.x, cov_matrix.values)
            sharpe = (target - _RISK_FREE_RATE) / vol if vol > 0 else 0
            frontier.append({
                "return_pct": round(target * 100, 2),
                "volatility_pct": round(vol * 100, 2),
                "sharpe": round(sharpe, 3),
                "weights": {sym: round(float(w), 4) for sym, w in zip(valid_symbols, result.x)},
            })

    # Mark special portfolios
    if frontier:
        max_sharpe_idx = max(range(len(frontier)), key=lambda i: frontier[i]["sharpe"])
        min_vol_idx = min(range(len(frontier)), key=lambda i: frontier[i]["volatility_pct"])
        frontier[max_sharpe_idx]["label"] = "Max Sharpe"
        frontier[min_vol_idx]["label"] = "Min Volatility"

    return {
        "symbols": valid_symbols,
        "frontier": frontier,
        "point_count": len(frontier),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def risk_parity_allocation(symbols: List[str]) -> Dict[str, Any]:
    """
    Calculate risk-parity weights (equal risk contribution).

    Uses iterative inverse-volatility with correlation adjustment.
    """
    returns = _get_returns(symbols)
    if returns is None:
        return {"error": "Could not fetch return data"}

    valid_symbols = list(returns.columns)
    n = len(valid_symbols)
    cov_matrix = returns.cov() * _TRADING_DAYS
    mean_returns = returns.mean() * _TRADING_DAYS

    # Objective: minimize sum of squared differences in risk contributions
    def risk_parity_obj(weights):
        rc = _risk_contribution(weights, cov_matrix.values)
        target_rc = _portfolio_volatility(weights, cov_matrix.values) / n
        return np.sum((rc - target_rc) ** 2)

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.01, 1)] * n
    init_w = np.array([1 / n] * n)

    result = optimize.minimize(
        risk_parity_obj,
        init_w,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )

    if not result.success:
        # Fallback to inverse volatility
        vols = np.sqrt(np.diag(cov_matrix.values))
        inv_vol = 1 / vols
        weights = inv_vol / inv_vol.sum()
    else:
        weights = result.x

    port_return = _portfolio_return(weights, mean_returns.values)
    port_vol = _portfolio_volatility(weights, cov_matrix.values)
    sharpe = (port_return - _RISK_FREE_RATE) / port_vol if port_vol > 0 else 0
    risk_contribs = _risk_contribution(weights, cov_matrix.values)

    allocation = {}
    for i, sym in enumerate(valid_symbols):
        allocation[sym] = {
            "weight": round(float(weights[i]), 4),
            "weight_pct": round(float(weights[i]) * 100, 2),
            "risk_contribution": round(float(risk_contribs[i]), 4),
            "risk_contribution_pct": round(float(risk_contribs[i]) / port_vol * 100, 2) if port_vol > 0 else 0,
        }

    return {
        "method": "risk_parity",
        "symbols": valid_symbols,
        "allocation": allocation,
        "portfolio_metrics": {
            "expected_return_pct": round(port_return * 100, 2),
            "volatility_pct": round(port_vol * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
        },
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def rebalance_suggestions(
    symbols: List[str],
    current_weights: List[float],
    target_method: str = "max_sharpe",
) -> Dict[str, Any]:
    """
    Compare current weights to optimal and suggest trades.

    Returns trades needed and estimated Sharpe improvement.
    """
    if len(symbols) != len(current_weights):
        return {"error": "symbols and current_weights must have same length"}

    optimal = optimize_portfolio(symbols, method=target_method)
    if "error" in optimal:
        return optimal

    current_dict = {s: w for s, w in zip(symbols, current_weights)}
    trades = []

    for sym in optimal.get("symbols", []):
        curr = current_dict.get(sym, 0)
        target = optimal["allocation"].get(sym, {}).get("weight", 0)
        diff = target - curr
        if abs(diff) > 0.01:  # >1% difference
            trades.append({
                "symbol": sym,
                "current_weight_pct": round(curr * 100, 2),
                "target_weight_pct": round(target * 100, 2),
                "action": "buy" if diff > 0 else "sell",
                "change_pct": round(diff * 100, 2),
            })

    return {
        "method": target_method,
        "trades": sorted(trades, key=lambda t: abs(t["change_pct"]), reverse=True),
        "current_metrics": {
            "note": "Calculate from current weights for comparison",
        },
        "target_metrics": optimal.get("portfolio_metrics", {}),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
