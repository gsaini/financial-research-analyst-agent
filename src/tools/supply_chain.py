"""
Supply Chain Analysis Tool (Phase 4).

Identifies a company's key customers, suppliers, and competitors
using financial data and provides supply chain risk assessment.

Usage::

    from src.tools.supply_chain import analyze_supply_chain
    result = analyze_supply_chain("AAPL")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Known major supply chain relationships (manually curated)
_SUPPLY_CHAINS = {
    "AAPL": {
        "suppliers": ["TSM", "QCOM", "AVGO", "TXN", "SWKS", "CRUS", "LRCX"],
        "customers": [],  # B2C company
        "competitors": ["SAMSUNG", "GOOGL", "MSFT"],
    },
    "TSLA": {
        "suppliers": ["ALB", "SQM", "PCRFY", "APH", "GNRC"],
        "customers": [],
        "competitors": ["F", "GM", "RIVN", "LCID", "NIO"],
    },
    "MSFT": {
        "suppliers": ["INTC", "AMD", "NVDA"],
        "customers": [],
        "competitors": ["GOOGL", "AMZN", "CRM", "ORCL"],
    },
    "AMZN": {
        "suppliers": ["INTC", "AMD", "NVDA"],
        "customers": [],
        "competitors": ["WMT", "SHOP", "BABA", "MSFT"],
    },
    "NVDA": {
        "suppliers": ["TSM", "ASML", "LRCX", "AMAT"],
        "customers": ["MSFT", "AMZN", "GOOGL", "META"],
        "competitors": ["AMD", "INTC", "QCOM"],
    },
}


def _get_sector_peers(symbol: str, sector: str) -> List[str]:
    """Get peer companies from the same sector."""
    # Common large-caps by sector
    sector_peers = {
        "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AVGO", "CRM", "ORCL", "AMD", "INTC"],
        "Healthcare": ["UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY"],
        "Financial Services": ["JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP"],
        "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TJX", "LOW", "BKNG", "CMG"],
        "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL"],
        "Communication Services": ["GOOGL", "META", "DIS", "NFLX", "CMCSA", "TMUS", "VZ", "T", "CHTR"],
        "Industrials": ["GE", "CAT", "RTX", "HON", "UPS", "BA", "DE", "LMT", "MMM", "GD"],
    }
    peers = sector_peers.get(sector, [])
    return [p for p in peers if p != symbol][:8]


def analyze_supply_chain(symbol: str) -> Dict[str, Any]:
    """
    Analyze a company's supply chain relationships and risks.

    Uses known relationships where available, falls back to sector
    peer analysis.

    Args:
        symbol: Stock ticker.

    Returns:
        Dict with suppliers, customers, competitors, correlation analysis,
        and risk assessment.
    """
    try:
        provider = get_provider()
        info = provider.get_info(symbol)
        sector = info.get("sector", "Other")
        industry = info.get("industry", "Other")
        company_name = info.get("shortName", symbol)

        # Get known relationships or generate from sector
        known = _SUPPLY_CHAINS.get(symbol.upper(), {})
        suppliers = known.get("suppliers", [])
        customers = known.get("customers", [])
        competitors = known.get("competitors", _get_sector_peers(symbol, sector)[:5])

        # If no known suppliers, use sector-adjacent
        if not suppliers:
            suppliers = _get_sector_peers(symbol, sector)[:4]

        # Correlation analysis
        all_related = list(set(suppliers + customers + competitors))[:10]
        correlations = _compute_correlations(symbol, all_related)

        # Supply chain risk assessment
        risk_factors = []

        # Concentration risk
        if len(suppliers) <= 2:
            risk_factors.append({
                "type": "supplier_concentration",
                "severity": "high",
                "description": "Few identified suppliers — high concentration risk if key supplier disrupted.",
            })

        # Correlation risk (high correlation with suppliers = co-movement risk)
        high_corr_suppliers = [
            s for s in suppliers
            if correlations.get(s, {}).get("correlation", 0) > 0.7
        ]
        if high_corr_suppliers:
            risk_factors.append({
                "type": "correlated_supply_chain",
                "severity": "medium",
                "description": f"Highly correlated with suppliers {high_corr_suppliers} — shared risk factors.",
            })

        # Competitive pressure
        stronger_competitors = [
            c for c in competitors
            if correlations.get(c, {}).get("correlation", 0) > 0.5
        ]
        if len(stronger_competitors) > 3:
            risk_factors.append({
                "type": "competitive_intensity",
                "severity": "medium",
                "description": "Many correlated competitors suggest high competitive intensity in the sector.",
            })

        # Overall risk score
        risk_score = min(100, len(risk_factors) * 25 + (5 - min(5, len(suppliers))) * 10)

        return {
            "symbol": symbol,
            "company": company_name,
            "sector": sector,
            "industry": industry,
            "supply_chain": {
                "suppliers": [
                    {"symbol": s, "correlation": correlations.get(s, {}).get("correlation", None)}
                    for s in suppliers
                ],
                "customers": [
                    {"symbol": c, "correlation": correlations.get(c, {}).get("correlation", None)}
                    for c in customers
                ],
                "competitors": [
                    {"symbol": c, "correlation": correlations.get(c, {}).get("correlation", None)}
                    for c in competitors
                ],
            },
            "risk_assessment": {
                "risk_score": risk_score,
                "risk_level": (
                    "High" if risk_score > 60 else "Medium" if risk_score > 30 else "Low"
                ),
                "risk_factors": risk_factors,
            },
            "correlation_matrix": correlations,
            "data_source": "known" if symbol.upper() in _SUPPLY_CHAINS else "inferred",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Supply chain analysis failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def _compute_correlations(
    symbol: str, related: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Compute return correlations between symbol and related stocks."""
    try:
        provider = get_provider()
        all_syms = [symbol] + related
        prices = {}
        for sym in all_syms:
            hist = provider.get_history(sym, period="1y", interval="1d")
            if hist is not None and not hist.empty and "Close" in hist.columns:
                prices[sym] = hist["Close"]

        if symbol not in prices:
            return {}

        df = pd.DataFrame(prices).dropna()
        returns = df.pct_change().dropna()

        if symbol not in returns.columns:
            return {}

        correlations = {}
        for sym in related:
            if sym in returns.columns:
                corr = float(returns[symbol].corr(returns[sym]))
                correlations[sym] = {
                    "correlation": round(corr, 3),
                    "relationship": (
                        "strongly positive" if corr > 0.7
                        else "moderately positive" if corr > 0.4
                        else "weakly positive" if corr > 0.1
                        else "uncorrelated" if corr > -0.1
                        else "negatively correlated"
                    ),
                }

        return correlations

    except Exception:
        return {}
