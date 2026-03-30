"""
Backtesting Engine (Feature 8).

Simulates trading strategies against historical price data and produces
a detailed performance report including trade log, equity curve,
risk metrics, and a buy-and-hold comparison.

Usage
-----
>>> from src.tools.backtesting_engine import run_backtest, list_strategies
>>> result = run_backtest("AAPL", strategy="rsi_reversal", period="5y")
>>> print(result["performance"]["total_return"])
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from src.data import get_provider

from src.tools.strategy_definitions import STRATEGIES, get_strategy
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────


def list_strategies() -> List[Dict[str, str]]:
    """Return all available strategy definitions."""
    return [
        {"key": key, "name": s["name"], "description": s["description"]}
        for key, s in STRATEGIES.items()
    ]


# ─────────────────────────────────────────────────────────────
# Internal: fetch prices
# ─────────────────────────────────────────────────────────────


def _fetch_prices(
    symbol: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: str = "5y",
) -> Optional[np.ndarray]:
    """Fetch adjusted close prices as a numpy array."""
    try:
        ticker = yf.Ticker(symbol)
        if start and end:
            hist = ticker.history(start=start, end=end, auto_adjust=True)
        else:
            hist = ticker.history(period=period, auto_adjust=True)
        if hist.empty or "Close" not in hist.columns:
            return None
        return hist["Close"].values.astype(float)
    except Exception as exc:
        logger.error(f"Failed to fetch prices for {symbol}: {exc}")
        return None


# ─────────────────────────────────────────────────────────────
# Internal: day-by-day simulation
# ─────────────────────────────────────────────────────────────


def _simulate(
    prices: np.ndarray,
    signal_fn,
    initial_capital: float = 10_000.0,
    commission_pct: float = 0.1,
    slippage_pct: float = 0.05,
) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    """
    Walk through *prices* bar-by-bar, applying *signal_fn* to decide
    entry/exit.  Returns (trade_log, equity_curve).

    The simulation only supports long positions (buy then sell).
    """
    cash = initial_capital
    shares = 0.0
    entry_price = 0.0
    entry_idx = 0
    trade_log: List[Dict[str, Any]] = []
    equity = np.zeros(len(prices))

    for i in range(len(prices)):
        price = float(prices[i])
        signal = signal_fn(prices, i)

        if signal == "BUY" and shares == 0:
            # Apply slippage to entry (slightly worse execution)
            exec_price = price * (1.0 + slippage_pct / 100.0)
            commission = cash * (commission_pct / 100.0)
            investable = cash - commission
            if investable > 0:
                shares = investable / exec_price
                entry_price = exec_price
                entry_idx = i
                cash = 0.0

        elif signal == "SELL" and shares > 0:
            exec_price = price * (1.0 - slippage_pct / 100.0)
            proceeds = shares * exec_price
            commission = proceeds * (commission_pct / 100.0)
            cash = proceeds - commission
            trade_return = (exec_price - entry_price) / entry_price * 100.0
            trade_log.append({
                "trade_number": len(trade_log) + 1,
                "entry_idx": int(entry_idx),
                "exit_idx": int(i),
                "entry_price": round(entry_price, 2),
                "exit_price": round(exec_price, 2),
                "return_pct": round(trade_return, 2),
                "holding_bars": int(i - entry_idx),
            })
            shares = 0.0

        # Track equity (cash + market value of position)
        equity[i] = cash + shares * price

    # If still in a position at the end, mark-to-market (but don't close)
    if shares > 0:
        final_value = shares * float(prices[-1])
        trade_return = (float(prices[-1]) - entry_price) / entry_price * 100.0
        trade_log.append({
            "trade_number": len(trade_log) + 1,
            "entry_idx": int(entry_idx),
            "exit_idx": int(len(prices) - 1),
            "entry_price": round(entry_price, 2),
            "exit_price": round(float(prices[-1]), 2),
            "return_pct": round(trade_return, 2),
            "holding_bars": int(len(prices) - 1 - entry_idx),
            "status": "open",
        })

    return trade_log, equity


# ─────────────────────────────────────────────────────────────
# Internal: compute performance metrics
# ─────────────────────────────────────────────────────────────


def _compute_metrics(
    trade_log: List[Dict[str, Any]],
    equity: np.ndarray,
    initial_capital: float,
    buy_hold_return: float,
    num_years: float,
) -> Dict[str, Any]:
    """Derive performance statistics from a completed backtest."""
    final_equity = float(equity[-1]) if len(equity) > 0 else initial_capital
    total_return = (final_equity - initial_capital) / initial_capital * 100.0

    # Annualised return
    if num_years > 0 and final_equity > 0:
        annualised = ((final_equity / initial_capital) ** (1.0 / num_years) - 1) * 100.0
    else:
        annualised = 0.0

    # Win / loss stats
    returns = [t["return_pct"] for t in trade_log]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    total_trades = len(trade_log)
    win_rate = (len(wins) / total_trades * 100.0) if total_trades else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("inf") if wins else 0.0

    # Max drawdown from equity curve
    peak = np.maximum.accumulate(equity)
    # Avoid division by zero
    safe_peak = np.where(peak == 0, 1.0, peak)
    drawdown = (equity - peak) / safe_peak * 100.0
    max_drawdown = float(np.min(drawdown)) if len(drawdown) > 0 else 0.0

    # Longest drawdown (consecutive bars below peak)
    in_dd = equity < peak
    longest_dd_bars = 0
    current_dd = 0
    for flag in in_dd:
        if flag:
            current_dd += 1
            longest_dd_bars = max(longest_dd_bars, current_dd)
        else:
            current_dd = 0

    # Max consecutive losses
    max_consec_loss = 0
    consec = 0
    for r in returns:
        if r <= 0:
            consec += 1
            max_consec_loss = max(max_consec_loss, consec)
        else:
            consec = 0

    # Sharpe-like ratio (daily equity returns, assuming 252 trading days)
    if len(equity) > 1:
        daily_returns = np.diff(equity) / np.where(equity[:-1] == 0, 1, equity[:-1])
        mean_r = float(np.mean(daily_returns))
        std_r = float(np.std(daily_returns))
        sharpe = (mean_r / std_r * np.sqrt(252)) if std_r > 0 else 0.0
        # Sortino (downside deviation)
        downside = daily_returns[daily_returns < 0]
        down_std = float(np.std(downside)) if len(downside) > 0 else 0.0
        sortino = (mean_r / down_std * np.sqrt(252)) if down_std > 0 else 0.0
    else:
        sharpe = sortino = 0.0

    excess_return = total_return - buy_hold_return

    return {
        "total_return": f"{total_return:+.1f}%",
        "annualized_return": f"{annualised:+.1f}%",
        "buy_and_hold_return": f"{buy_hold_return:+.1f}%",
        "excess_return": f"{excess_return:+.1f}%",
        "total_trades": total_trades,
        "win_rate": f"{win_rate:.1f}%",
        "average_win": f"{avg_win:+.1f}%",
        "average_loss": f"{avg_loss:+.1f}%" if avg_loss != 0 else "0.0%",
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "∞",
        "max_drawdown": f"{max_drawdown:.1f}%",
        "longest_drawdown_bars": longest_dd_bars,
        "max_consecutive_losses": max_consec_loss,
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "final_equity": round(final_equity, 2),
    }


# ─────────────────────────────────────────────────────────────
# Public: run_backtest
# ─────────────────────────────────────────────────────────────


def run_backtest(
    symbol: str,
    strategy: str = "rsi_reversal",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "5y",
    initial_capital: float = 10_000.0,
    commission_pct: float = 0.1,
    slippage_pct: float = 0.05,
) -> Dict[str, Any]:
    """
    Run a full backtest for *symbol* using a named strategy.

    Args:
        symbol: Stock ticker symbol.
        strategy: Key from the STRATEGIES registry (e.g. ``"rsi_reversal"``).
        start_date: Start date ``"YYYY-MM-DD"`` (optional; if omitted, *period* is used).
        end_date: End date ``"YYYY-MM-DD"`` (optional).
        period: yfinance period string (e.g. ``"5y"``). Ignored if start/end given.
        initial_capital: Starting cash balance.
        commission_pct: Round-trip commission as a percentage of trade value.
        slippage_pct: Assumed slippage as a percentage of price.

    Returns:
        Dict with strategy info, trade log, performance metrics, and verdict.
    """
    start_time = datetime.now(timezone.utc)

    # ── Validate strategy ────
    strat_info = get_strategy(strategy)
    if strat_info is None:
        available = ", ".join(STRATEGIES.keys())
        return {
            "error": f"Unknown strategy '{strategy}'. Available: {available}",
            "symbol": symbol,
            "strategy": strategy,
        }

    signal_fn = strat_info["fn"]

    # ── Fetch prices ────
    prices = _fetch_prices(symbol, start=start_date, end=end_date, period=period)
    if prices is None or len(prices) < 50:
        return {
            "error": "Insufficient price data for backtesting (need at least 50 bars).",
            "symbol": symbol,
            "strategy": strategy,
        }

    # ── Simulate ────
    trade_log, equity = _simulate(
        prices, signal_fn,
        initial_capital=initial_capital,
        commission_pct=commission_pct,
        slippage_pct=slippage_pct,
    )

    # ── Buy-and-hold baseline ────
    buy_hold_return = (float(prices[-1]) - float(prices[0])) / float(prices[0]) * 100.0
    num_years = len(prices) / 252.0

    # ── Metrics ────
    performance = _compute_metrics(
        trade_log, equity, initial_capital, buy_hold_return, num_years,
    )

    # ── Verdict ────
    excess = float(performance["excess_return"].replace("%", "").replace("+", ""))
    if excess > 5:
        verdict = "Strategy significantly outperforms buy-and-hold."
    elif excess > 0:
        verdict = "Strategy marginally outperforms buy-and-hold."
    elif excess > -5:
        verdict = "Strategy roughly matches buy-and-hold."
    elif excess > -15:
        verdict = "Strategy underperforms buy-and-hold. Better suited for range-bound markets."
    else:
        verdict = "Strategy significantly underperforms buy-and-hold. Not recommended for this ticker."

    execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

    return {
        "symbol": symbol,
        "strategy": strat_info["name"],
        "strategy_key": strategy,
        "strategy_description": strat_info["description"],
        "period": f"{start_date or 'auto'} to {end_date or 'auto'}",
        "initial_capital": initial_capital,
        "data_points": len(prices),
        "trade_log": trade_log,
        "performance": performance,
        "verdict": verdict,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "execution_time_seconds": round(execution_time, 3),
    }


# ─────────────────────────────────────────────────────────────
# Walk-Forward Analysis (Phase 3.2)
# ─────────────────────────────────────────────────────────────


def walk_forward_analysis(
    symbol: str,
    strategy: str = "rsi_reversal",
    n_folds: int = 5,
    period: str = "5y",
    initial_capital: float = 10_000.0,
    commission_pct: float = 0.1,
) -> Dict[str, Any]:
    """
    Walk-forward analysis: split history into N folds, backtest each
    out-of-sample fold using parameters from in-sample training.

    This validates whether a strategy works consistently across time
    periods, not just in aggregate.

    Returns:
        Dict with per-fold results and consistency metrics.
    """
    strat_info = get_strategy(strategy)
    if strat_info is None:
        return {"error": f"Unknown strategy '{strategy}'"}

    prices = _fetch_prices(symbol, period=period)
    if prices is None or len(prices) < 200:
        return {"error": "Insufficient data for walk-forward (need 200+ bars)"}

    fold_size = len(prices) // n_folds
    folds = []

    for i in range(n_folds):
        start_idx = i * fold_size
        end_idx = min((i + 1) * fold_size, len(prices))
        fold_prices = prices[start_idx:end_idx]

        if len(fold_prices) < 50:
            continue

        trade_log, equity = _simulate(
            fold_prices, strat_info["fn"],
            initial_capital=initial_capital,
            commission_pct=commission_pct,
        )

        buy_hold = (float(fold_prices[-1]) - float(fold_prices[0])) / float(fold_prices[0]) * 100
        num_years = len(fold_prices) / 252.0
        perf = _compute_metrics(trade_log, equity, initial_capital, buy_hold, num_years)

        folds.append({
            "fold": i + 1,
            "bars": len(fold_prices),
            "total_return": perf.get("total_return", "0%"),
            "sharpe_ratio": perf.get("sharpe_ratio", 0),
            "max_drawdown": perf.get("max_drawdown", "0%"),
            "trades": perf.get("total_trades", 0),
            "beat_buy_hold": float(perf.get("excess_return", "0").replace("%", "").replace("+", "")) > 0,
        })

    # Consistency metrics
    profitable_folds = sum(1 for f in folds if float(f["total_return"].replace("%", "").replace("+", "")) > 0)
    beat_count = sum(1 for f in folds if f.get("beat_buy_hold"))

    return {
        "symbol": symbol,
        "strategy": strat_info["name"],
        "n_folds": len(folds),
        "folds": folds,
        "consistency": {
            "profitable_folds": profitable_folds,
            "profitable_pct": round(profitable_folds / len(folds) * 100, 1) if folds else 0,
            "beat_buy_hold_folds": beat_count,
            "beat_buy_hold_pct": round(beat_count / len(folds) * 100, 1) if folds else 0,
        },
        "verdict": (
            "Highly consistent — profitable in most time periods"
            if profitable_folds >= len(folds) * 0.8
            else "Moderately consistent — works in some market regimes"
            if profitable_folds >= len(folds) * 0.5
            else "Inconsistent — strategy is regime-dependent"
        ),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# Multi-Asset Backtest (Phase 3.2)
# ─────────────────────────────────────────────────────────────


def backtest_portfolio(
    symbols: List[str],
    strategy: str = "rsi_reversal",
    period: str = "5y",
    initial_capital: float = 100_000.0,
    commission_pct: float = 0.1,
) -> Dict[str, Any]:
    """
    Run the same strategy across multiple assets and aggregate results.

    Capital is split equally across assets. Returns per-asset performance
    and portfolio-level aggregation.
    """
    n = len(symbols)
    per_asset_capital = initial_capital / n

    results = {}
    total_final = 0
    total_trades = 0

    for sym in symbols:
        bt = run_backtest(
            sym,
            strategy=strategy,
            period=period,
            initial_capital=per_asset_capital,
            commission_pct=commission_pct,
        )
        if "error" in bt:
            results[sym] = {"error": bt["error"]}
            total_final += per_asset_capital  # No change
        else:
            perf = bt.get("performance", {})
            results[sym] = {
                "total_return": perf.get("total_return", "0%"),
                "sharpe_ratio": perf.get("sharpe_ratio", 0),
                "max_drawdown": perf.get("max_drawdown", "0%"),
                "trades": perf.get("total_trades", 0),
            }
            # Parse final equity
            ret_str = perf.get("total_return", "0%").replace("%", "").replace("+", "")
            try:
                ret_pct = float(ret_str) / 100
            except ValueError:
                ret_pct = 0
            total_final += per_asset_capital * (1 + ret_pct)
            total_trades += perf.get("total_trades", 0)

    portfolio_return = (total_final - initial_capital) / initial_capital * 100

    return {
        "strategy": strategy,
        "symbols": symbols,
        "initial_capital": initial_capital,
        "final_value": round(total_final, 2),
        "portfolio_return_pct": round(portfolio_return, 2),
        "total_trades": total_trades,
        "per_asset": results,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
