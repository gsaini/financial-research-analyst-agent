"""
Tax-Loss Harvesting Tool (Phase 4).

Identifies positions with unrealized losses eligible for tax-loss
harvesting, suggests replacement securities, and estimates tax savings.

Usage::

    from src.tools.tax_loss_harvesting import analyze_tax_loss_opportunities
    result = analyze_tax_loss_opportunities(holdings)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Wash sale rule: 30 days before/after
_WASH_SALE_DAYS = 30

# Sector-to-alternative ETF (for replacement securities)
_SECTOR_ALTERNATIVES = {
    "Technology": ["VGT", "FTEC", "IYW"],
    "Healthcare": ["VHT", "FHLC", "IYH"],
    "Financial Services": ["VFH", "FNCL", "IYF"],
    "Financials": ["VFH", "FNCL", "IYF"],
    "Consumer Cyclical": ["VCR", "FDIS", "IYC"],
    "Consumer Defensive": ["VDC", "FSTA", "IYK"],
    "Communication Services": ["VOX", "FCOM"],
    "Industrials": ["VIS", "FIDU", "IYJ"],
    "Energy": ["VDE", "FENY", "IYE"],
    "Utilities": ["VPU", "FUTY", "IDU"],
    "Real Estate": ["VNQ", "FREL", "IYR"],
    "Basic Materials": ["VAW", "FMAT"],
}


def analyze_tax_loss_opportunities(
    holdings: List[Dict[str, Any]],
    tax_rate: float = 0.25,
) -> Dict[str, Any]:
    """
    Identify tax-loss harvesting opportunities in a portfolio.

    Args:
        holdings: List of dicts with keys: symbol, shares, cost_basis.
            Example: [{"symbol": "AAPL", "shares": 100, "cost_basis": 180.50}]
        tax_rate: Combined federal + state capital gains tax rate.

    Returns:
        Dict with harvestable losses, replacement suggestions, and tax savings.
    """
    try:
        provider = get_provider()
        opportunities = []
        total_harvestable_loss = 0
        total_unrealized_gain = 0

        for holding in holdings:
            symbol = holding.get("symbol", "").upper()
            shares = holding.get("shares", 0)
            cost_basis = holding.get("cost_basis", 0)

            if not symbol or shares <= 0 or cost_basis <= 0:
                continue

            # Get current price
            info = provider.get_info(symbol)
            current_price = info.get(
                "currentPrice", info.get("regularMarketPrice", 0)
            )
            if not current_price:
                continue

            sector = info.get("sector", "Other")
            unrealized = (current_price - cost_basis) * shares
            unrealized_pct = (current_price / cost_basis - 1) * 100

            entry = {
                "symbol": symbol,
                "shares": shares,
                "cost_basis": round(cost_basis, 2),
                "current_price": round(current_price, 2),
                "unrealized_pnl": round(unrealized, 2),
                "unrealized_pct": round(unrealized_pct, 2),
                "sector": sector,
            }

            if unrealized < 0:
                # Loss — harvestable
                tax_savings = abs(unrealized) * tax_rate
                alternatives = _SECTOR_ALTERNATIVES.get(sector, [])

                entry["harvestable"] = True
                entry["tax_savings"] = round(tax_savings, 2)
                entry["replacement_candidates"] = alternatives[:3]
                entry["wash_sale_warning"] = (
                    f"Cannot repurchase {symbol} or substantially identical "
                    f"securities within {_WASH_SALE_DAYS} days before/after sale."
                )
                total_harvestable_loss += abs(unrealized)
                opportunities.append(entry)
            else:
                entry["harvestable"] = False
                total_unrealized_gain += unrealized

        # Sort by largest loss first
        opportunities.sort(key=lambda x: x["unrealized_pnl"])

        total_tax_savings = total_harvestable_loss * tax_rate

        # Strategy recommendation
        if total_harvestable_loss > 3000:
            strategy = (
                "Significant harvesting opportunity. The IRS allows up to $3,000 "
                "in net capital losses to offset ordinary income per year, with "
                "excess carried forward. Consider harvesting the largest losses first."
            )
        elif total_harvestable_loss > 0:
            strategy = (
                "Minor harvesting opportunity. Consider harvesting if losses "
                "can offset realized gains from other positions."
            )
        else:
            strategy = "No tax-loss harvesting opportunities — all positions are in profit."

        return {
            "total_positions": len(holdings),
            "harvestable_positions": len(opportunities),
            "total_harvestable_loss": round(total_harvestable_loss, 2),
            "total_unrealized_gain": round(total_unrealized_gain, 2),
            "estimated_tax_savings": round(total_tax_savings, 2),
            "tax_rate_used": tax_rate,
            "opportunities": opportunities,
            "strategy": strategy,
            "wash_sale_rule": (
                "IRS wash sale rule: You cannot claim a tax loss if you purchase "
                "the same or substantially identical security within 30 days "
                "before or after the sale."
            ),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Tax-loss harvesting analysis failed: {e}")
        return {"error": str(e)}
