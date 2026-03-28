"""
Benchmark Comparison Tool (Phase 2.5).

Compares portfolio performance against benchmarks (S&P 500, etc.)
with alpha, beta, tracking error, and attribution analysis.

Usage::

    from src.tools.benchmark import calculate_portfolio_vs_benchmark
    result = calculate_portfolio_vs_benchmark(["AAPL", "MSFT"], [0.6, 0.4])
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
_RISK_FREE_RATE = 0.05


def _fetch_returns(symbols: List[str], period: str = "1y") -> Optional[pd.DataFrame]:
    """Fetch daily returns for symbols."""
    try:
        provider = get_provider()
        prices = {}
        for sym in symbols:
            hist = provider.get_history(sym, period=period, interval="1d")
            if hist is not None and not hist.empty:
                prices[sym] = hist["Close"]
        if not prices:
            return None
        df = pd.DataFrame(prices).dropna()
        return df.pct_change().dropna()
    except Exception as e:
        logger.error(f"Fetch returns failed: {e}")
        return None


def calculate_portfolio_vs_benchmark(
    symbols: List[str],
    weights: List[float],
    benchmark: str = "SPY",
    period: str = "1y",
) -> Dict[str, Any]:
    """
    Compare portfolio to benchmark.

    Calculates alpha, beta, tracking error, information ratio, R-squared.
    """
    try:
        all_symbols = list(set(symbols + [benchmark]))
        returns = _fetch_returns(all_symbols, period)
        if returns is None:
            return {"error": "Could not fetch return data"}

        # Ensure all symbols have data
        missing = [s for s in symbols if s not in returns.columns]
        if missing:
            return {"error": f"Missing data for: {missing}"}
        if benchmark not in returns.columns:
            return {"error": f"Missing benchmark data for {benchmark}"}

        # Portfolio returns
        port_weights = np.array(weights[:len(symbols)])
        port_weights = port_weights / port_weights.sum()  # Normalize
        port_returns = (returns[symbols] * port_weights).sum(axis=1)
        bench_returns = returns[benchmark]

        # Align
        aligned = pd.DataFrame({"portfolio": port_returns, "benchmark": bench_returns}).dropna()
        p = aligned["portfolio"]
        b = aligned["benchmark"]

        # Beta and Alpha (regression)
        cov = np.cov(p, b)
        beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 1.0

        ann_port = float(p.mean()) * _TRADING_DAYS
        ann_bench = float(b.mean()) * _TRADING_DAYS
        alpha = ann_port - (_RISK_FREE_RATE + beta * (ann_bench - _RISK_FREE_RATE))

        # Tracking error
        tracking_diff = p - b
        tracking_error = float(tracking_diff.std()) * np.sqrt(_TRADING_DAYS)

        # Information ratio
        info_ratio = float(tracking_diff.mean() * _TRADING_DAYS / tracking_error) if tracking_error > 0 else 0

        # R-squared
        correlation = float(np.corrcoef(p, b)[0, 1])
        r_squared = correlation ** 2

        # Cumulative returns
        cum_port = float((1 + p).prod() - 1)
        cum_bench = float((1 + b).prod() - 1)

        # Volatilities
        port_vol = float(p.std()) * np.sqrt(_TRADING_DAYS)
        bench_vol = float(b.std()) * np.sqrt(_TRADING_DAYS)

        # Sharpe ratios
        port_sharpe = (ann_port - _RISK_FREE_RATE) / port_vol if port_vol > 0 else 0
        bench_sharpe = (ann_bench - _RISK_FREE_RATE) / bench_vol if bench_vol > 0 else 0

        return {
            "benchmark": benchmark,
            "period": period,
            "portfolio": {
                "cumulative_return_pct": round(cum_port * 100, 2),
                "annualized_return_pct": round(ann_port * 100, 2),
                "volatility_pct": round(port_vol * 100, 2),
                "sharpe_ratio": round(port_sharpe, 3),
            },
            "benchmark_stats": {
                "cumulative_return_pct": round(cum_bench * 100, 2),
                "annualized_return_pct": round(ann_bench * 100, 2),
                "volatility_pct": round(bench_vol * 100, 2),
                "sharpe_ratio": round(bench_sharpe, 3),
            },
            "relative_metrics": {
                "alpha_pct": round(alpha * 100, 2),
                "beta": round(beta, 3),
                "tracking_error_pct": round(tracking_error * 100, 2),
                "information_ratio": round(info_ratio, 3),
                "r_squared": round(r_squared, 3),
                "correlation": round(correlation, 3),
                "excess_return_pct": round((cum_port - cum_bench) * 100, 2),
            },
            "interpretation": {
                "alpha": "Outperforming" if alpha > 0 else "Underperforming",
                "beta": (
                    "More volatile than market" if beta > 1.1
                    else "Less volatile than market" if beta < 0.9
                    else "Market-like volatility"
                ),
                "tracking": (
                    "High tracking error — portfolio behaves differently from benchmark"
                    if tracking_error > 0.15
                    else "Moderate tracking" if tracking_error > 0.08
                    else "Low tracking error — closely follows benchmark"
                ),
            },
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Benchmark comparison failed: {e}")
        return {"error": str(e)}


def rolling_analysis(
    symbols: List[str],
    weights: List[float],
    benchmark: str = "SPY",
    window: int = 60,
) -> Dict[str, Any]:
    """
    Calculate rolling alpha and beta over time.

    Returns time series for trend analysis.
    """
    try:
        all_symbols = list(set(symbols + [benchmark]))
        returns = _fetch_returns(all_symbols, period="2y")
        if returns is None:
            return {"error": "Could not fetch return data"}

        missing = [s for s in symbols if s not in returns.columns]
        if missing or benchmark not in returns.columns:
            return {"error": "Missing data for some symbols"}

        port_weights = np.array(weights[:len(symbols)])
        port_weights = port_weights / port_weights.sum()
        port_returns = (returns[symbols] * port_weights).sum(axis=1)
        bench_returns = returns[benchmark]

        aligned = pd.DataFrame({"portfolio": port_returns, "benchmark": bench_returns}).dropna()

        # Rolling calculations
        rolling_beta = []
        rolling_alpha = []
        rolling_corr = []
        dates = []

        for i in range(window, len(aligned)):
            p = aligned["portfolio"].iloc[i - window:i]
            b = aligned["benchmark"].iloc[i - window:i]

            cov = np.cov(p, b)
            beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 1.0

            ann_p = float(p.mean()) * _TRADING_DAYS
            ann_b = float(b.mean()) * _TRADING_DAYS
            alpha = ann_p - (_RISK_FREE_RATE + beta * (ann_b - _RISK_FREE_RATE))
            corr = float(np.corrcoef(p, b)[0, 1])

            date = aligned.index[i]
            dates.append(str(date.date()) if hasattr(date, "date") else str(date))
            rolling_beta.append(round(beta, 3))
            rolling_alpha.append(round(alpha * 100, 2))
            rolling_corr.append(round(corr, 3))

        # Trend detection
        if len(rolling_alpha) >= 20:
            recent_alpha = np.mean(rolling_alpha[-20:])
            early_alpha = np.mean(rolling_alpha[:20])
            alpha_trend = (
                "improving" if recent_alpha > early_alpha + 1
                else "deteriorating" if recent_alpha < early_alpha - 1
                else "stable"
            )
        else:
            alpha_trend = "insufficient data"

        # Sample every 5 days to keep compact
        step = max(1, len(dates) // 50)
        return {
            "benchmark": benchmark,
            "window_days": window,
            "alpha_trend": alpha_trend,
            "time_series": {
                "dates": dates[::step],
                "rolling_alpha_pct": rolling_alpha[::step],
                "rolling_beta": rolling_beta[::step],
                "rolling_correlation": rolling_corr[::step],
            },
            "latest": {
                "alpha_pct": rolling_alpha[-1] if rolling_alpha else None,
                "beta": rolling_beta[-1] if rolling_beta else None,
                "correlation": rolling_corr[-1] if rolling_corr else None,
            },
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Rolling analysis failed: {e}")
        return {"error": str(e)}


def attribution_analysis(
    symbols: List[str],
    weights: List[float],
    benchmark: str = "SPY",
) -> Dict[str, Any]:
    """
    Return attribution: how much each stock contributed to portfolio return.
    """
    try:
        all_symbols = list(set(symbols + [benchmark]))
        returns = _fetch_returns(all_symbols, period="1y")
        if returns is None:
            return {"error": "Could not fetch return data"}

        available = [s for s in symbols if s in returns.columns]
        if not available:
            return {"error": "No symbols have return data"}

        port_weights = np.array([weights[symbols.index(s)] for s in available])
        port_weights = port_weights / port_weights.sum()

        # Cumulative returns per stock
        cum_returns = {}
        contributions = {}
        for i, sym in enumerate(available):
            cum = float((1 + returns[sym]).prod() - 1)
            cum_returns[sym] = round(cum * 100, 2)
            contributions[sym] = {
                "weight_pct": round(float(port_weights[i]) * 100, 2),
                "stock_return_pct": round(cum * 100, 2),
                "contribution_pct": round(cum * float(port_weights[i]) * 100, 2),
            }

        # Equal weight comparison
        eq_weight = 1 / len(available)
        eq_return = sum(
            float((1 + returns[s]).prod() - 1) * eq_weight for s in available
        )
        port_return = sum(
            float((1 + returns[s]).prod() - 1) * float(port_weights[i])
            for i, s in enumerate(available)
        )

        # Benchmark return
        bench_return = 0
        if benchmark in returns.columns:
            bench_return = float((1 + returns[benchmark]).prod() - 1)

        return {
            "benchmark": benchmark,
            "contributions": contributions,
            "portfolio_return_pct": round(port_return * 100, 2),
            "equal_weight_return_pct": round(eq_return * 100, 2),
            "benchmark_return_pct": round(bench_return * 100, 2),
            "allocation_effect_pct": round((port_return - eq_return) * 100, 2),
            "selection_effect_pct": round((eq_return - bench_return) * 100, 2),
            "top_contributor": max(contributions, key=lambda s: contributions[s]["contribution_pct"]),
            "bottom_contributor": min(contributions, key=lambda s: contributions[s]["contribution_pct"]),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Attribution analysis failed: {e}")
        return {"error": str(e)}
