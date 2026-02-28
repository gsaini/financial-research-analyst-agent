"""
Performance tracking tool - multi-horizon returns, benchmark comparison,
risk-adjusted metrics, rolling returns, and drawdown analysis.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import math

import yfinance as yf
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Sector-to-ETF mapping for benchmark comparison
SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Financials": "XLF",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
}

RISK_FREE_RATE = 0.05  # ~5% annualized (approximate current T-bill rate)


def _fetch_history(symbol: str, period: str = "5y") -> Optional[Any]:
    """Fetch adjusted close history as a pandas Series."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, auto_adjust=True)
        if hist.empty:
            return None
        return hist["Close"]
    except Exception as e:
        logger.error(f"Error fetching history for {symbol}: {e}")
        return None


def _compute_return(prices, days: Optional[int] = None, ytd: bool = False) -> Optional[float]:
    """Compute total return over last N trading days, or YTD."""
    if prices is None or len(prices) < 2:
        return None
    try:
        end_price = float(prices.iloc[-1])
        if ytd:
            current_year = prices.index[-1].year
            year_start = prices.index[prices.index.year == current_year]
            if len(year_start) == 0:
                return None
            start_price = float(year_start[0])
        elif days is not None:
            idx = max(0, len(prices) - 1 - days)
            start_price = float(prices.iloc[idx])
        else:
            start_price = float(prices.iloc[0])

        if start_price == 0:
            return None
        return round(((end_price / start_price) - 1) * 100, 2)
    except Exception:
        return None


def _compute_rolling_returns(prices, window: int = 30) -> List[float]:
    """Compute rolling N-day returns."""
    if prices is None or len(prices) < window + 1:
        return []
    rolling = []
    for i in range(window, len(prices)):
        start = float(prices.iloc[i - window])
        end = float(prices.iloc[i])
        if start > 0:
            rolling.append(round(((end / start) - 1) * 100, 2))
    return rolling


def _compute_drawdowns(prices) -> Dict[str, Any]:
    """Compute drawdown series and max drawdown."""
    if prices is None or len(prices) < 2:
        return {}

    import numpy as np

    values = np.array([float(p) for p in prices])
    peak = np.maximum.accumulate(values)
    drawdowns = ((values - peak) / peak) * 100

    max_dd = float(np.min(drawdowns))
    max_dd_idx = int(np.argmin(drawdowns))
    max_dd_date = prices.index[max_dd_idx].strftime("%Y-%m-%d") if max_dd_idx < len(prices.index) else "N/A"

    # Recovery: how many days from max_dd to next new high
    recovery_days = None
    for j in range(max_dd_idx + 1, len(values)):
        if values[j] >= peak[max_dd_idx]:
            recovery_days = j - max_dd_idx
            break

    current_dd = float(drawdowns[-1])

    return {
        "max_drawdown": round(max_dd, 2),
        "max_drawdown_date": max_dd_date,
        "recovery_days": recovery_days,
        "current_drawdown": round(current_dd, 2),
        "drawdown_series": [round(float(d), 2) for d in drawdowns],
        "dates": [d.strftime("%Y-%m-%d") for d in prices.index],
    }


def _compute_risk_metrics(prices, benchmark_prices=None) -> Dict[str, Any]:
    """Compute Sharpe, Sortino, Beta, and volatility."""
    if prices is None or len(prices) < 30:
        return {}

    import numpy as np

    returns = np.diff(np.log([float(p) for p in prices]))  # log returns
    daily_rf = RISK_FREE_RATE / 252

    # Annualized volatility
    daily_vol = float(np.std(returns))
    annual_vol = round(daily_vol * math.sqrt(252) * 100, 2)

    # Sharpe ratio
    excess = returns - daily_rf
    sharpe = round(float(np.mean(excess) / np.std(excess)) * math.sqrt(252), 2) if np.std(excess) > 0 else 0

    # Sortino ratio (only penalizes downside volatility)
    downside = returns[returns < daily_rf] - daily_rf
    downside_std = float(np.std(downside)) if len(downside) > 0 else 0
    sortino = round(float(np.mean(excess) / downside_std) * math.sqrt(252), 2) if downside_std > 0 else 0

    result = {
        "daily_volatility": round(daily_vol * 100, 2),
        "annual_volatility": annual_vol,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
    }

    # Beta (vs benchmark)
    if benchmark_prices is not None and len(benchmark_prices) >= 30:
        bench_returns = np.diff(np.log([float(p) for p in benchmark_prices]))
        min_len = min(len(returns), len(bench_returns))
        r = returns[-min_len:]
        b = bench_returns[-min_len:]
        cov = np.cov(r, b)
        if cov.shape == (2, 2) and cov[1, 1] > 0:
            beta = round(float(cov[0, 1] / cov[1, 1]), 2)
            result["beta"] = beta
            if beta > 1:
                result["beta_interpretation"] = f"{int((beta - 1) * 100)}% more volatile than benchmark"
            elif beta < 1:
                result["beta_interpretation"] = f"{int((1 - beta) * 100)}% less volatile than benchmark"
            else:
                result["beta_interpretation"] = "Moves in line with benchmark"

    # Sharpe interpretation
    if sharpe >= 2.0:
        result["sharpe_rating"] = "Excellent"
    elif sharpe >= 1.0:
        result["sharpe_rating"] = "Good"
    elif sharpe >= 0.5:
        result["sharpe_rating"] = "Moderate"
    else:
        result["sharpe_rating"] = "Poor"

    # Sortino interpretation
    if sortino >= 2.0:
        result["sortino_rating"] = "Excellent"
    elif sortino >= 1.0:
        result["sortino_rating"] = "Good"
    elif sortino >= 0.5:
        result["sortino_rating"] = "Moderate"
    else:
        result["sortino_rating"] = "Poor"

    return result


def track_performance(symbol: str) -> Dict[str, Any]:
    """
    Comprehensive performance tracking for a stock symbol.

    Returns multi-horizon returns, benchmark comparison, risk-adjusted
    metrics, rolling returns, and drawdown analysis.
    """
    symbol = symbol.upper()

    # Fetch 5 years of history for the stock
    prices = _fetch_history(symbol, period="5y")
    if prices is None or len(prices) < 5:
        return {"symbol": symbol, "error": f"No historical data available for {symbol}"}

    # ── Absolute Returns ──────────────────────────────
    # Trading days: 1d=1, 1w=5, 1m=21, 3m=63, 6m=126, 1y=252, 3y=756, 5y=1260
    horizons = {
        "1_day": 1,
        "1_week": 5,
        "1_month": 21,
        "3_month": 63,
        "6_month": 126,
        "1_year": 252,
        "3_year": 756,
        "5_year": 1260,
    }
    absolute_returns = {}
    for label, days in horizons.items():
        ret = _compute_return(prices, days=days)
        if ret is not None:
            absolute_returns[label] = ret

    ytd_return = _compute_return(prices, ytd=True)
    if ytd_return is not None:
        absolute_returns["ytd"] = ytd_return

    # ── Benchmark Comparison ──────────────────────────
    spy_prices = _fetch_history("SPY", period="5y")
    qqq_prices = _fetch_history("QQQ", period="5y")

    # Determine sector ETF
    try:
        info = yf.Ticker(symbol).info
        sector = info.get("sector", "")
        sector_etf = SECTOR_ETFS.get(sector)
    except Exception:
        sector = ""
        sector_etf = None

    sector_prices = _fetch_history(sector_etf, period="5y") if sector_etf else None

    benchmark_comparison = {}
    for bench_label, bench_prices, bench_sym in [
        ("vs_spy", spy_prices, "S&P 500"),
        ("vs_qqq", qqq_prices, "Nasdaq 100"),
        ("vs_sector", sector_prices, f"{sector} ({sector_etf})" if sector_etf else None),
    ]:
        if bench_prices is None:
            continue
        bench_entry = {"benchmark": bench_sym}
        for horizon_label, days in [("1_month", 21), ("3_month", 63), ("1_year", 252), ("3_year", 756)]:
            stock_ret = _compute_return(prices, days=days)
            bench_ret = _compute_return(bench_prices, days=days)
            if stock_ret is not None and bench_ret is not None:
                alpha = round(stock_ret - bench_ret, 2)
                bench_entry[f"{horizon_label}_alpha"] = alpha
                if horizon_label == "1_year":
                    if alpha > 0:
                        bench_entry["assessment"] = f"Outperforming {bench_sym}"
                    elif alpha < 0:
                        bench_entry["assessment"] = f"Underperforming {bench_sym}"
                    else:
                        bench_entry["assessment"] = f"In line with {bench_sym}"
                bench_entry[f"{horizon_label}_stock"] = stock_ret
                bench_entry[f"{horizon_label}_benchmark"] = bench_ret

        benchmark_comparison[bench_label] = bench_entry

    # ── Risk-Adjusted Metrics ─────────────────────────
    risk_metrics = _compute_risk_metrics(prices, spy_prices)

    # ── Rolling Returns ───────────────────────────────
    rolling_30 = _compute_rolling_returns(prices, window=30)
    rolling_dates = [d.strftime("%Y-%m-%d") for d in prices.index[30:]] if len(prices) > 30 else []

    rolling_returns = {
        "window": 30,
        "values": rolling_30[-252:] if len(rolling_30) > 252 else rolling_30,  # last 1 year
        "dates": rolling_dates[-252:] if len(rolling_dates) > 252 else rolling_dates,
    }

    if rolling_30:
        rolling_returns["current"] = rolling_30[-1]
        rolling_returns["average"] = round(sum(rolling_30) / len(rolling_30), 2)
        rolling_returns["max"] = max(rolling_30)
        rolling_returns["min"] = min(rolling_30)

        if len(rolling_30) >= 5:
            recent = rolling_30[-5:]
            if all(r > 0 for r in recent):
                rolling_returns["trend"] = "Stable positive momentum"
            elif all(r < 0 for r in recent):
                rolling_returns["trend"] = "Persistent negative trend"
            elif recent[-1] > recent[0]:
                rolling_returns["trend"] = "Improving momentum"
            else:
                rolling_returns["trend"] = "Weakening momentum"

    # ── Drawdown Analysis ─────────────────────────────
    # Use 1-year for drawdown chart
    prices_1y = prices[-252:] if len(prices) > 252 else prices
    drawdown = _compute_drawdowns(prices_1y)

    # ── Return Statistics ─────────────────────────────
    import numpy as np

    daily_returns = np.diff([float(p) for p in prices[-252:]]) / np.array([float(p) for p in prices[-253:-1]]) * 100
    return_stats = {}
    if len(daily_returns) > 0:
        return_stats = {
            "mean_daily": round(float(np.mean(daily_returns)), 3),
            "median_daily": round(float(np.median(daily_returns)), 3),
            "best_day": round(float(np.max(daily_returns)), 2),
            "worst_day": round(float(np.min(daily_returns)), 2),
            "positive_days_pct": round(float(np.sum(daily_returns > 0) / len(daily_returns) * 100), 1),
            "std_daily": round(float(np.std(daily_returns)), 3),
        }

    return {
        "symbol": symbol,
        "sector": sector,
        "sector_etf": sector_etf,
        "data_points": len(prices),
        "start_date": prices.index[0].strftime("%Y-%m-%d"),
        "end_date": prices.index[-1].strftime("%Y-%m-%d"),
        "current_price": round(float(prices.iloc[-1]), 2),
        "absolute_returns": absolute_returns,
        "benchmark_comparison": benchmark_comparison,
        "risk_adjusted_metrics": risk_metrics,
        "rolling_returns": rolling_returns,
        "drawdown_analysis": drawdown,
        "return_statistics": return_stats,
    }
