"""
Monte Carlo Simulation Tool (Phase 3.1).

Geometric Brownian Motion simulation for VaR/CVaR estimation,
price target probability, and portfolio-level risk analysis.

Usage::

    from src.tools.monte_carlo import simulate_stock, simulate_portfolio
    result = simulate_stock("AAPL", days=252, n_simulations=10000)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_SIMULATIONS = 10_000
_TRADING_DAYS = 252


# ── Core GBM Engine ──────────────────────────────────────────


def _gbm_paths(
    s0: float,
    mu: float,
    sigma: float,
    days: int,
    n_paths: int,
    seed: int = 42,
) -> np.ndarray:
    """
    Generate Geometric Brownian Motion price paths.

    Args:
        s0: Initial price.
        mu: Annualized drift (expected return).
        sigma: Annualized volatility.
        days: Number of trading days to simulate.
        n_paths: Number of simulation paths.
        seed: Random seed for reproducibility.

    Returns:
        Array of shape (n_paths, days+1) with simulated prices.
    """
    rng = np.random.default_rng(seed)
    dt = 1 / _TRADING_DAYS
    # Daily drift and diffusion
    drift = (mu - 0.5 * sigma ** 2) * dt
    diffusion = sigma * np.sqrt(dt)

    # Generate random shocks
    shocks = rng.standard_normal((n_paths, days))
    log_returns = drift + diffusion * shocks

    # Cumulative returns
    log_paths = np.cumsum(log_returns, axis=1)
    # Prepend zero for initial price
    log_paths = np.concatenate([np.zeros((n_paths, 1)), log_paths], axis=1)

    return s0 * np.exp(log_paths)


def _extract_stats(
    final_prices: np.ndarray,
    s0: float,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """Extract statistics from simulation final prices."""
    returns = final_prices / s0 - 1

    var_level = 1 - confidence
    var = float(np.percentile(returns, var_level * 100))
    cvar = float(np.mean(returns[returns <= var]))

    return {
        "mean_price": round(float(np.mean(final_prices)), 2),
        "median_price": round(float(np.median(final_prices)), 2),
        "std_price": round(float(np.std(final_prices)), 2),
        "min_price": round(float(np.min(final_prices)), 2),
        "max_price": round(float(np.max(final_prices)), 2),
        "percentile_5": round(float(np.percentile(final_prices, 5)), 2),
        "percentile_25": round(float(np.percentile(final_prices, 25)), 2),
        "percentile_75": round(float(np.percentile(final_prices, 75)), 2),
        "percentile_95": round(float(np.percentile(final_prices, 95)), 2),
        "mean_return_pct": round(float(np.mean(returns)) * 100, 2),
        "var": {
            "confidence": confidence,
            "value_pct": round(var * 100, 2),
            "interpretation": f"{confidence*100:.0f}% confidence: max loss of {abs(var)*100:.2f}%",
        },
        "cvar": {
            "value_pct": round(cvar * 100, 2),
            "interpretation": f"Expected loss in worst {(1-confidence)*100:.0f}% of scenarios: {abs(cvar)*100:.2f}%",
        },
        "prob_positive_return": round(float(np.mean(returns > 0)) * 100, 1),
        "prob_loss_gt_10pct": round(float(np.mean(returns < -0.10)) * 100, 1),
        "prob_gain_gt_20pct": round(float(np.mean(returns > 0.20)) * 100, 1),
    }


# ── Public API ───────────────────────────────────────────────


def simulate_stock(
    symbol: str,
    days: int = 252,
    n_simulations: int = _DEFAULT_SIMULATIONS,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation for a single stock.

    Uses historical mean return and volatility as GBM parameters.

    Args:
        symbol: Stock ticker.
        days: Number of trading days to simulate.
        n_simulations: Number of paths (default 10,000).
        confidence: VaR confidence level.

    Returns:
        Dict with simulation statistics, VaR/CVaR, price distributions,
        and sample paths for visualization.
    """
    try:
        provider = get_provider()
        hist = provider.get_history(symbol, period="2y", interval="1d")

        if hist is None or len(hist) < 60:
            return {"symbol": symbol, "error": "Insufficient historical data"}

        close = hist["Close"]
        current_price = float(close.iloc[-1])

        # Historical parameters
        daily_returns = close.pct_change().dropna()
        mu = float(daily_returns.mean()) * _TRADING_DAYS  # Annualized
        sigma = float(daily_returns.std()) * np.sqrt(_TRADING_DAYS)  # Annualized

        # Run simulation
        paths = _gbm_paths(current_price, mu, sigma, days, n_simulations)
        final_prices = paths[:, -1]

        # Statistics
        stats = _extract_stats(final_prices, current_price, confidence)

        # Sample paths for visualization (10 paths, sampled at intervals)
        sample_indices = np.linspace(0, n_simulations - 1, 10, dtype=int)
        step = max(1, days // 50)
        sample_paths = [
            [round(float(p), 2) for p in paths[i, ::step]]
            for i in sample_indices
        ]

        # Distribution histogram (20 bins)
        hist_counts, bin_edges = np.histogram(final_prices, bins=20)
        distribution = [
            {
                "range": f"{bin_edges[i]:.0f}-{bin_edges[i+1]:.0f}",
                "count": int(hist_counts[i]),
                "pct": round(int(hist_counts[i]) / n_simulations * 100, 1),
            }
            for i in range(len(hist_counts))
        ]

        return {
            "symbol": symbol,
            "current_price": current_price,
            "simulation_params": {
                "days": days,
                "n_simulations": n_simulations,
                "annualized_return": round(mu * 100, 2),
                "annualized_volatility": round(sigma * 100, 2),
            },
            "statistics": stats,
            "distribution": distribution,
            "sample_paths": sample_paths,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Monte Carlo simulation failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def probability_of_target(
    symbol: str,
    target_price: float,
    days: int = 252,
    n_simulations: int = _DEFAULT_SIMULATIONS,
) -> Dict[str, Any]:
    """
    Calculate probability of reaching a target price.

    Args:
        symbol: Stock ticker.
        target_price: Target price to evaluate.
        days: Simulation horizon in trading days.
        n_simulations: Number of paths.

    Returns:
        Dict with probability of reaching target, expected time, and distribution.
    """
    try:
        provider = get_provider()
        hist = provider.get_history(symbol, period="2y", interval="1d")

        if hist is None or len(hist) < 60:
            return {"symbol": symbol, "error": "Insufficient data"}

        close = hist["Close"]
        current_price = float(close.iloc[-1])
        daily_returns = close.pct_change().dropna()
        mu = float(daily_returns.mean()) * _TRADING_DAYS
        sigma = float(daily_returns.std()) * np.sqrt(_TRADING_DAYS)

        paths = _gbm_paths(current_price, mu, sigma, days, n_simulations)

        # Probability of ever touching target during simulation
        if target_price > current_price:
            max_prices = np.max(paths, axis=1)
            prob_touch = float(np.mean(max_prices >= target_price))
        else:
            min_prices = np.min(paths, axis=1)
            prob_touch = float(np.mean(min_prices <= target_price))

        # Probability of ending above/below target
        final_prices = paths[:, -1]
        prob_end_above = float(np.mean(final_prices >= target_price))

        # First passage time (average days to first touch, for paths that touch)
        first_touch_days = []
        for path in paths:
            if target_price > current_price:
                touches = np.where(path >= target_price)[0]
            else:
                touches = np.where(path <= target_price)[0]
            if len(touches) > 0:
                first_touch_days.append(int(touches[0]))

        avg_first_touch = round(np.mean(first_touch_days), 0) if first_touch_days else None

        direction = "upside" if target_price > current_price else "downside"
        pct_move = (target_price / current_price - 1) * 100

        return {
            "symbol": symbol,
            "current_price": current_price,
            "target_price": target_price,
            "direction": direction,
            "required_move_pct": round(pct_move, 2),
            "horizon_days": days,
            "prob_touch_pct": round(prob_touch * 100, 1),
            "prob_end_above_target_pct": round(prob_end_above * 100, 1),
            "avg_days_to_touch": avg_first_touch,
            "interpretation": (
                f"{prob_touch*100:.1f}% chance of {'reaching' if direction == 'upside' else 'falling to'} "
                f"${target_price:.2f} ({pct_move:+.1f}%) within {days} trading days."
            ),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Target probability failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def simulate_portfolio(
    symbols: List[str],
    weights: List[float],
    days: int = 252,
    n_simulations: int = _DEFAULT_SIMULATIONS,
    confidence: float = 0.95,
    initial_value: float = 100_000,
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation for a portfolio with correlations.

    Uses correlated GBM via Cholesky decomposition.

    Args:
        symbols: Stock tickers.
        weights: Portfolio weights (must sum to 1).
        days: Simulation horizon.
        n_simulations: Number of paths.
        confidence: VaR confidence level.
        initial_value: Starting portfolio value in dollars.

    Returns:
        Dict with portfolio-level VaR/CVaR, distributions, and per-asset stats.
    """
    try:
        provider = get_provider()
        n_assets = len(symbols)
        weights = np.array(weights[:n_assets])
        weights = weights / weights.sum()

        # Fetch returns for all assets
        returns_dict = {}
        for sym in symbols:
            hist = provider.get_history(sym, period="2y", interval="1d")
            if hist is not None and not hist.empty:
                returns_dict[sym] = hist["Close"].pct_change().dropna()

        if len(returns_dict) < 2:
            return {"error": "Need at least 2 assets with data"}

        # Align returns
        returns_df = pd.DataFrame(returns_dict).dropna()
        valid_symbols = list(returns_df.columns)
        valid_weights = np.array([weights[symbols.index(s)] for s in valid_symbols if s in symbols])
        valid_weights = valid_weights / valid_weights.sum()

        # Parameters
        means = returns_df.mean().values * _TRADING_DAYS
        cov_matrix = returns_df.cov().values * _TRADING_DAYS

        # Cholesky decomposition for correlated returns
        try:
            L = np.linalg.cholesky(cov_matrix)
        except np.linalg.LinAlgError:
            # If not positive definite, use diagonal (uncorrelated)
            logger.warning("Covariance matrix not positive definite, using diagonal")
            L = np.diag(np.sqrt(np.diag(cov_matrix)))

        rng = np.random.default_rng(42)
        dt = 1 / _TRADING_DAYS
        n = len(valid_symbols)

        # Simulate portfolio values
        portfolio_values = np.zeros((n_simulations, days + 1))
        portfolio_values[:, 0] = initial_value

        for sim in range(n_simulations):
            asset_values = np.array([initial_value * w for w in valid_weights])
            port_val = initial_value

            for day in range(days):
                z = rng.standard_normal(n)
                correlated_z = L @ z

                for i in range(n):
                    drift = (means[i] - 0.5 * cov_matrix[i, i]) * dt
                    shock = np.sqrt(cov_matrix[i, i]) * np.sqrt(dt) * correlated_z[i] / np.sqrt(cov_matrix[i, i]) if cov_matrix[i, i] > 0 else 0
                    asset_values[i] *= np.exp(drift + shock)

                portfolio_values[sim, day + 1] = np.sum(asset_values)

        final_values = portfolio_values[:, -1]
        final_returns = final_values / initial_value - 1

        # VaR / CVaR
        var_level = 1 - confidence
        var_return = float(np.percentile(final_returns, var_level * 100))
        cvar_return = float(np.mean(final_returns[final_returns <= var_return]))

        var_dollar = round(abs(var_return) * initial_value, 2)
        cvar_dollar = round(abs(cvar_return) * initial_value, 2)

        return {
            "symbols": valid_symbols,
            "weights": {s: round(float(w), 4) for s, w in zip(valid_symbols, valid_weights)},
            "initial_value": initial_value,
            "simulation_params": {
                "days": days,
                "n_simulations": n_simulations,
                "confidence": confidence,
            },
            "statistics": {
                "mean_final_value": round(float(np.mean(final_values)), 2),
                "median_final_value": round(float(np.median(final_values)), 2),
                "percentile_5": round(float(np.percentile(final_values, 5)), 2),
                "percentile_95": round(float(np.percentile(final_values, 95)), 2),
                "mean_return_pct": round(float(np.mean(final_returns)) * 100, 2),
                "prob_loss_pct": round(float(np.mean(final_returns < 0)) * 100, 1),
            },
            "risk_metrics": {
                "var_pct": round(var_return * 100, 2),
                "var_dollar": var_dollar,
                "cvar_pct": round(cvar_return * 100, 2),
                "cvar_dollar": cvar_dollar,
                "max_simulated_loss_pct": round(float(np.min(final_returns)) * 100, 2),
                "max_simulated_gain_pct": round(float(np.max(final_returns)) * 100, 2),
            },
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Portfolio Monte Carlo failed: {e}")
        return {"error": str(e)}
