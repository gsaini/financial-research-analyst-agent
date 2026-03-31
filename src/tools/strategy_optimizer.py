"""
Strategy Optimization via Genetic Algorithm (Phase 4).

Optimizes trading strategy parameters (RSI thresholds, MA periods,
etc.) using evolutionary optimization to find parameter sets that
maximize Sharpe ratio on historical data.

Usage::

    from src.tools.strategy_optimizer import optimize_strategy
    result = optimize_strategy("AAPL", "rsi_reversal")
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from src.tools.backtesting_engine import _fetch_prices, _simulate, _compute_metrics
from src.tools.strategy_definitions import STRATEGIES, get_strategy
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Parameter spaces per strategy ────────────────────────────

_PARAM_SPACES = {
    "rsi_reversal": {
        "rsi_period": (7, 21),
        "oversold": (20, 35),
        "overbought": (65, 80),
    },
    "macd_crossover": {
        "fast_period": (8, 16),
        "slow_period": (20, 32),
        "signal_period": (6, 12),
    },
    "golden_death_cross": {
        "fast_ma": (30, 70),
        "slow_ma": (150, 250),
    },
    "bollinger_reversion": {
        "bb_period": (15, 30),
        "bb_std": (1.5, 3.0),
    },
    "mean_reversion": {
        "ma_period": (10, 30),
        "entry_z": (1.5, 3.0),
        "exit_z": (0.5, 1.5),
    },
    "breakout": {
        "high_period": (10, 30),
        "low_period": (5, 15),
    },
    "trend_following": {
        "fast_ema": (5, 15),
        "slow_ema": (20, 40),
    },
}


# ── Genetic Algorithm ────────────────────────────────────────


def _create_individual(param_space: Dict[str, Tuple]) -> Dict[str, float]:
    """Create a random individual (parameter set)."""
    individual = {}
    for param, (lo, hi) in param_space.items():
        if isinstance(lo, int) and isinstance(hi, int):
            individual[param] = random.randint(lo, hi)
        else:
            individual[param] = round(random.uniform(lo, hi), 2)
    return individual


def _crossover(
    parent1: Dict[str, float],
    parent2: Dict[str, float],
) -> Dict[str, float]:
    """Uniform crossover between two parents."""
    child = {}
    for key in parent1:
        child[key] = parent1[key] if random.random() < 0.5 else parent2[key]
    return child


def _mutate(
    individual: Dict[str, float],
    param_space: Dict[str, Tuple],
    mutation_rate: float = 0.2,
) -> Dict[str, float]:
    """Mutate an individual with given probability."""
    mutated = individual.copy()
    for param, (lo, hi) in param_space.items():
        if random.random() < mutation_rate:
            if isinstance(lo, int) and isinstance(hi, int):
                mutated[param] = random.randint(lo, hi)
            else:
                mutated[param] = round(random.uniform(lo, hi), 2)
    return mutated


def _evaluate(
    prices: np.ndarray,
    strategy_fn: Callable,
    params: Dict[str, float],
    initial_capital: float = 10_000,
) -> float:
    """Evaluate a parameter set. Returns Sharpe ratio (fitness)."""
    try:
        # Create a wrapper that passes params as kwargs
        def param_strategy(p, idx, **kw):
            return strategy_fn(p, idx, **params)

        trade_log, equity = _simulate(
            prices, param_strategy,
            initial_capital=initial_capital,
            commission_pct=0.1,
        )

        buy_hold = (float(prices[-1]) - float(prices[0])) / float(prices[0]) * 100
        num_years = len(prices) / 252.0
        metrics = _compute_metrics(trade_log, equity, initial_capital, buy_hold, num_years)

        sharpe = metrics.get("sharpe_ratio", 0)
        return float(sharpe) if isinstance(sharpe, (int, float)) else 0

    except Exception:
        return -999  # Penalty for failed evaluation


def optimize_strategy(
    symbol: str,
    strategy: str = "rsi_reversal",
    population_size: int = 50,
    generations: int = 30,
    period: str = "5y",
) -> Dict[str, Any]:
    """
    Optimize strategy parameters using a genetic algorithm.

    Args:
        symbol: Stock ticker.
        strategy: Strategy key from STRATEGIES registry.
        population_size: GA population size.
        generations: Number of GA generations.
        period: Historical data period.

    Returns:
        Dict with best parameters, fitness trajectory, and backtest results.
    """
    strat_info = get_strategy(strategy)
    if strat_info is None:
        return {"error": f"Unknown strategy: {strategy}"}

    param_space = _PARAM_SPACES.get(strategy)
    if param_space is None:
        return {
            "error": f"No parameter space defined for '{strategy}'. "
                     f"Available: {list(_PARAM_SPACES.keys())}",
        }

    prices = _fetch_prices(symbol, period=period)
    if prices is None or len(prices) < 200:
        return {"error": "Insufficient price data for optimization"}

    strategy_fn = strat_info["fn"]

    # Split: 70% training, 30% validation
    split = int(len(prices) * 0.7)
    train_prices = prices[:split]
    val_prices = prices[split:]

    # Initialize population
    random.seed(42)
    population = [_create_individual(param_space) for _ in range(population_size)]

    # Evolution
    fitness_history = []
    best_ever = None
    best_fitness = -999

    for gen in range(generations):
        # Evaluate fitness on training set
        fitnesses = [_evaluate(train_prices, strategy_fn, ind) for ind in population]

        # Track best
        gen_best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
        gen_best_fitness = fitnesses[gen_best_idx]
        gen_best_individual = population[gen_best_idx]

        if gen_best_fitness > best_fitness:
            best_fitness = gen_best_fitness
            best_ever = gen_best_individual.copy()

        fitness_history.append({
            "generation": gen + 1,
            "best_fitness": round(gen_best_fitness, 4),
            "avg_fitness": round(np.mean(fitnesses), 4),
        })

        # Selection (tournament)
        new_population = [best_ever.copy()]  # Elitism
        while len(new_population) < population_size:
            # Tournament selection (size 3)
            candidates = random.sample(range(len(population)), min(3, len(population)))
            winner = max(candidates, key=lambda i: fitnesses[i])
            parent1 = population[winner]

            candidates = random.sample(range(len(population)), min(3, len(population)))
            winner = max(candidates, key=lambda i: fitnesses[i])
            parent2 = population[winner]

            child = _crossover(parent1, parent2)
            child = _mutate(child, param_space)
            new_population.append(child)

        population = new_population

    # Validate best on out-of-sample data
    train_sharpe = _evaluate(train_prices, strategy_fn, best_ever) if best_ever else 0
    val_sharpe = _evaluate(val_prices, strategy_fn, best_ever) if best_ever else 0

    # Overfitting check
    if val_sharpe < train_sharpe * 0.5:
        overfit_warning = "Possible overfitting — validation Sharpe is significantly lower than training."
    elif val_sharpe > train_sharpe * 0.8:
        overfit_warning = "Parameters appear robust — validation performance is close to training."
    else:
        overfit_warning = "Moderate generalization — some parameter decay on validation data."

    return {
        "symbol": symbol,
        "strategy": strat_info["name"],
        "strategy_key": strategy,
        "best_parameters": best_ever,
        "parameter_space": {k: {"min": v[0], "max": v[1]} for k, v in param_space.items()},
        "training_sharpe": round(train_sharpe, 4),
        "validation_sharpe": round(val_sharpe, 4),
        "overfit_assessment": overfit_warning,
        "ga_config": {
            "population_size": population_size,
            "generations": generations,
            "training_bars": len(train_prices),
            "validation_bars": len(val_prices),
        },
        "fitness_history": fitness_history[-10:],  # Last 10 generations
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
