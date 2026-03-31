"""
Brinson Performance Attribution (Phase 4).

Decomposes portfolio returns into allocation, selection, and
interaction effects relative to a benchmark.

Usage::

    from src.tools.brinson_attribution import brinson_attribution
    result = brinson_attribution(portfolio_holdings, benchmark="SPY")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Sector-to-ETF mapping for sector-level attribution
_SECTOR_ETFS = {
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


def brinson_attribution(
    symbols: List[str],
    weights: List[float],
    benchmark: str = "SPY",
    period: str = "1y",
) -> Dict[str, Any]:
    """
    Brinson-Fachler attribution: decompose portfolio performance into
    allocation, selection, and interaction effects.

    Args:
        symbols: Portfolio holdings.
        weights: Portfolio weights (must sum to ~1).
        benchmark: Benchmark symbol.
        period: Analysis period.

    Returns:
        Dict with total, allocation, selection, interaction effects
        at portfolio and sector level.
    """
    try:
        provider = get_provider()
        n = len(symbols)
        port_weights = np.array(weights[:n])
        port_weights = port_weights / port_weights.sum()

        # Fetch returns
        all_syms = list(set(symbols + [benchmark]))
        prices = {}
        sectors = {}
        for sym in all_syms:
            hist = provider.get_history(sym, period=period, interval="1d")
            if hist is not None and not hist.empty:
                prices[sym] = hist["Close"]
            info = provider.get_info(sym)
            sectors[sym] = info.get("sector", "Other")

        if benchmark not in prices:
            return {"error": f"Benchmark {benchmark} data not available"}

        price_df = pd.DataFrame(prices).dropna()
        returns = price_df.pct_change().dropna()

        missing = [s for s in symbols if s not in returns.columns]
        if missing:
            return {"error": f"Missing data for: {missing}"}

        # Cumulative returns
        cum_returns = {}
        for col in returns.columns:
            cum_returns[col] = float((1 + returns[col]).prod() - 1)

        bench_return = cum_returns.get(benchmark, 0)

        # Portfolio return
        port_return = sum(
            float(port_weights[i]) * cum_returns.get(sym, 0)
            for i, sym in enumerate(symbols)
        )
        excess_return = port_return - bench_return

        # Group by sector for Brinson decomposition
        sector_groups: Dict[str, Dict] = {}
        for i, sym in enumerate(symbols):
            sec = sectors.get(sym, "Other")
            if sec not in sector_groups:
                sector_groups[sec] = {"symbols": [], "weights": [], "returns": []}
            sector_groups[sec]["symbols"].append(sym)
            sector_groups[sec]["weights"].append(float(port_weights[i]))
            sector_groups[sec]["returns"].append(cum_returns.get(sym, 0))

        # Benchmark sector weights (approximate: equal weight across sectors present)
        # In practice, you'd use actual benchmark weights; we approximate
        all_sectors = set(sector_groups.keys())
        bench_sector_weight = 1.0 / len(all_sectors) if all_sectors else 0
        bench_sector_returns: Dict[str, float] = {}
        for sec in all_sectors:
            etf = _SECTOR_ETFS.get(sec)
            if etf and etf in cum_returns:
                bench_sector_returns[sec] = cum_returns[etf]
            else:
                bench_sector_returns[sec] = bench_return

        # Brinson decomposition per sector
        sector_attribution = {}
        total_allocation = 0
        total_selection = 0
        total_interaction = 0

        for sec, data in sector_groups.items():
            port_sector_weight = sum(data["weights"])
            port_sector_return = (
                sum(w * r for w, r in zip(data["weights"], data["returns"])) / port_sector_weight
                if port_sector_weight > 0 else 0
            )
            bench_sec_weight = bench_sector_weight
            bench_sec_return = bench_sector_returns.get(sec, bench_return)

            # Brinson-Fachler formulas
            allocation = (port_sector_weight - bench_sec_weight) * (bench_sec_return - bench_return)
            selection = bench_sec_weight * (port_sector_return - bench_sec_return)
            interaction = (port_sector_weight - bench_sec_weight) * (port_sector_return - bench_sec_return)

            total_allocation += allocation
            total_selection += selection
            total_interaction += interaction

            sector_attribution[sec] = {
                "portfolio_weight_pct": round(port_sector_weight * 100, 2),
                "benchmark_weight_pct": round(bench_sec_weight * 100, 2),
                "portfolio_return_pct": round(port_sector_return * 100, 2),
                "benchmark_return_pct": round(bench_sec_return * 100, 2),
                "allocation_effect_pct": round(allocation * 100, 3),
                "selection_effect_pct": round(selection * 100, 3),
                "interaction_effect_pct": round(interaction * 100, 3),
                "total_effect_pct": round((allocation + selection + interaction) * 100, 3),
                "holdings": data["symbols"],
            }

        # Per-stock contribution
        stock_contributions = {}
        for i, sym in enumerate(symbols):
            w = float(port_weights[i])
            r = cum_returns.get(sym, 0)
            stock_contributions[sym] = {
                "weight_pct": round(w * 100, 2),
                "return_pct": round(r * 100, 2),
                "contribution_pct": round(w * r * 100, 2),
                "sector": sectors.get(sym, "Other"),
            }

        return {
            "benchmark": benchmark,
            "period": period,
            "portfolio_return_pct": round(port_return * 100, 2),
            "benchmark_return_pct": round(bench_return * 100, 2),
            "excess_return_pct": round(excess_return * 100, 2),
            "attribution": {
                "allocation_effect_pct": round(total_allocation * 100, 2),
                "selection_effect_pct": round(total_selection * 100, 2),
                "interaction_effect_pct": round(total_interaction * 100, 2),
                "total_explained_pct": round((total_allocation + total_selection + total_interaction) * 100, 2),
            },
            "interpretation": {
                "allocation": (
                    "Positive — overweighting outperforming sectors added value"
                    if total_allocation > 0.005
                    else "Negative — sector allocation detracted from performance"
                    if total_allocation < -0.005
                    else "Neutral — sector allocation had minimal impact"
                ),
                "selection": (
                    "Positive — stock selection within sectors added value"
                    if total_selection > 0.005
                    else "Negative — stock selection detracted from performance"
                    if total_selection < -0.005
                    else "Neutral — stock selection had minimal impact"
                ),
            },
            "sector_detail": sector_attribution,
            "stock_contributions": stock_contributions,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Brinson attribution failed: {e}")
        return {"error": str(e)}
