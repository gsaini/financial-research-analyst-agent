"""
DCF Valuation Model (Phase 2.3).

Discounted Cash Flow analysis with WACC calculation, multi-scenario
projections, and sensitivity analysis.

Usage::

    from src.tools.dcf_model import get_dcf_summary
    result = get_dcf_summary("AAPL")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_RISK_FREE = 0.045
_EQUITY_RISK_PREMIUM = 0.055
_PROJECTION_YEARS = 10


# ── Helpers ──────────────────────────────────────────────────


def _safe_float(val, default=0.0) -> float:
    """Convert value to float safely."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _get_latest_value(df: pd.DataFrame, row_names: List[str]) -> float:
    """Get the latest (first column) value from a financial statement row."""
    if df is None or df.empty:
        return 0.0
    for name in row_names:
        if name in df.index:
            val = df.loc[name].iloc[0]
            return _safe_float(val)
    return 0.0


# ── WACC Calculation ─────────────────────────────────────────


def calculate_wacc(symbol: str) -> Dict[str, Any]:
    """
    Calculate Weighted Average Cost of Capital using CAPM.

    Returns all components and final WACC.
    """
    try:
        provider = get_provider()
        info = provider.get_info(symbol)
        balance = provider.get_balance_sheet(symbol)
        income = provider.get_income_statement(symbol)

        # Beta
        beta = _safe_float(info.get("beta"), 1.0)

        # Risk-free rate
        risk_free = _DEFAULT_RISK_FREE

        # Cost of equity (CAPM)
        cost_equity = risk_free + beta * _EQUITY_RISK_PREMIUM

        # Market cap (equity value)
        market_cap = _safe_float(info.get("marketCap"), 0)

        # Total debt
        total_debt = _get_latest_value(balance, [
            "Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation",
        ])

        # Interest expense
        interest_expense = abs(_get_latest_value(income, [
            "Interest Expense", "Interest Expense Non Operating",
        ]))

        # Cost of debt
        cost_debt = interest_expense / total_debt if total_debt > 0 else 0.04

        # Tax rate
        pretax_income = _get_latest_value(income, [
            "Pretax Income", "Income Before Tax",
        ])
        tax_provision = _get_latest_value(income, [
            "Tax Provision", "Income Tax Expense",
        ])
        tax_rate = tax_provision / pretax_income if pretax_income > 0 else 0.21

        # WACC
        total_value = market_cap + total_debt
        if total_value > 0:
            equity_weight = market_cap / total_value
            debt_weight = total_debt / total_value
        else:
            equity_weight = 1.0
            debt_weight = 0.0

        wacc = equity_weight * cost_equity + debt_weight * cost_debt * (1 - tax_rate)

        return {
            "symbol": symbol,
            "wacc": round(wacc, 4),
            "wacc_pct": round(wacc * 100, 2),
            "components": {
                "beta": round(beta, 2),
                "risk_free_rate": risk_free,
                "equity_risk_premium": _EQUITY_RISK_PREMIUM,
                "cost_of_equity": round(cost_equity, 4),
                "cost_of_debt": round(cost_debt, 4),
                "tax_rate": round(tax_rate, 3),
                "equity_weight": round(equity_weight, 3),
                "debt_weight": round(debt_weight, 3),
                "market_cap": market_cap,
                "total_debt": total_debt,
            },
        }

    except Exception as e:
        logger.error(f"WACC calculation failed for {symbol}: {e}")
        return {
            "symbol": symbol,
            "wacc": 0.10,
            "wacc_pct": 10.0,
            "error": str(e),
            "note": "Using default WACC of 10%",
        }


# ── DCF Analysis ─────────────────────────────────────────────


def run_dcf_analysis(
    symbol: str,
    scenarios: Optional[Dict[str, Dict]] = None,
) -> Dict[str, Any]:
    """
    Run DCF valuation with bull/base/bear scenarios.

    Args:
        symbol: Stock ticker.
        scenarios: Optional custom scenarios dict with growth_rate and terminal_growth.

    Returns:
        Per-scenario intrinsic values, current price, upside/downside.
    """
    try:
        provider = get_provider()
        info = provider.get_info(symbol)
        cash_flow = provider.get_cash_flow(symbol)

        current_price = _safe_float(
            info.get("currentPrice", info.get("regularMarketPrice")), 0
        )
        shares = _safe_float(info.get("sharesOutstanding"), 1)

        # Get FCF
        fcf = _get_latest_value(cash_flow, [
            "Free Cash Flow", "FreeCashFlow",
        ])
        if fcf == 0:
            operating_cf = _get_latest_value(cash_flow, [
                "Operating Cash Flow", "Total Cash From Operating Activities",
            ])
            capex = abs(_get_latest_value(cash_flow, [
                "Capital Expenditure", "Capital Expenditures",
            ]))
            fcf = operating_cf - capex

        if fcf <= 0:
            return {
                "symbol": symbol,
                "error": "Negative or zero free cash flow — DCF not applicable",
                "current_price": current_price,
                "fcf": fcf,
            }

        # Historical growth rate estimate
        revenue_growth = _safe_float(info.get("revenueGrowth"), 0.05)
        earnings_growth = _safe_float(info.get("earningsGrowth"), revenue_growth)
        hist_growth = max(0.02, min(0.30, (revenue_growth + earnings_growth) / 2))

        # WACC
        wacc_result = calculate_wacc(symbol)
        wacc = wacc_result.get("wacc", 0.10)

        # Default scenarios
        if scenarios is None:
            scenarios = {
                "bull": {"growth_rate": hist_growth + 0.02, "terminal_growth": 0.03},
                "base": {"growth_rate": hist_growth, "terminal_growth": 0.025},
                "bear": {"growth_rate": max(0.01, hist_growth - 0.02), "terminal_growth": 0.02},
            }

        results: Dict[str, Any] = {}
        for name, params in scenarios.items():
            growth = params["growth_rate"]
            terminal = params["terminal_growth"]

            # Project FCF with decaying growth toward terminal
            projected = []
            current_fcf = fcf
            for year in range(1, _PROJECTION_YEARS + 1):
                # Growth decays linearly toward terminal
                decay = year / _PROJECTION_YEARS
                year_growth = growth * (1 - decay) + terminal * decay
                current_fcf *= (1 + year_growth)
                projected.append(current_fcf)

            # Discount projected FCFs
            pv_fcfs = sum(cf / (1 + wacc) ** i for i, cf in enumerate(projected, 1))

            # Terminal value
            terminal_fcf = projected[-1] * (1 + terminal)
            terminal_value = terminal_fcf / (wacc - terminal) if wacc > terminal else 0
            pv_terminal = terminal_value / (1 + wacc) ** _PROJECTION_YEARS

            # Total value
            enterprise_value = pv_fcfs + pv_terminal
            equity_value = enterprise_value  # Simplified (should subtract net debt)
            intrinsic = equity_value / shares if shares > 0 else 0

            upside = ((intrinsic - current_price) / current_price * 100) if current_price > 0 else 0

            results[name] = {
                "growth_rate": round(growth * 100, 1),
                "terminal_growth": round(terminal * 100, 1),
                "intrinsic_value": round(intrinsic, 2),
                "upside_pct": round(upside, 1),
                "enterprise_value": round(enterprise_value),
                "pv_fcfs": round(pv_fcfs),
                "pv_terminal": round(pv_terminal),
                "terminal_pct": round(pv_terminal / enterprise_value * 100, 1) if enterprise_value > 0 else 0,
            }

        # Recommendation based on base case
        base_upside = results.get("base", {}).get("upside_pct", 0)
        if base_upside > 30:
            recommendation = "Strong Buy"
        elif base_upside > 15:
            recommendation = "Buy"
        elif base_upside > -15:
            recommendation = "Hold"
        elif base_upside > -30:
            recommendation = "Sell"
        else:
            recommendation = "Strong Sell"

        return {
            "symbol": symbol,
            "current_price": current_price,
            "fcf": round(fcf),
            "wacc": wacc_result,
            "scenarios": results,
            "recommendation": recommendation,
            "assumptions": {
                "projection_years": _PROJECTION_YEARS,
                "historical_growth_estimate": round(hist_growth * 100, 1),
            },
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"DCF analysis failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


# ── Sensitivity Analysis ─────────────────────────────────────


def sensitivity_analysis(symbol: str) -> Dict[str, Any]:
    """
    Run sensitivity analysis varying discount rate and terminal growth.

    Returns a 5×5 matrix of intrinsic values.
    """
    try:
        provider = get_provider()
        info = provider.get_info(symbol)
        cash_flow = provider.get_cash_flow(symbol)

        current_price = _safe_float(
            info.get("currentPrice", info.get("regularMarketPrice")), 0
        )
        shares = _safe_float(info.get("sharesOutstanding"), 1)

        fcf = _get_latest_value(cash_flow, ["Free Cash Flow", "FreeCashFlow"])
        if fcf == 0:
            operating_cf = _get_latest_value(cash_flow, ["Operating Cash Flow"])
            capex = abs(_get_latest_value(cash_flow, ["Capital Expenditure"]))
            fcf = operating_cf - capex

        if fcf <= 0:
            return {"symbol": symbol, "error": "Negative FCF — sensitivity not applicable"}

        wacc_result = calculate_wacc(symbol)
        base_wacc = wacc_result.get("wacc", 0.10)

        revenue_growth = _safe_float(info.get("revenueGrowth"), 0.05)
        base_growth = max(0.02, min(0.30, revenue_growth))

        # Vary WACC: ±2% in 1% steps
        discount_rates = [base_wacc - 0.02, base_wacc - 0.01, base_wacc, base_wacc + 0.01, base_wacc + 0.02]
        # Vary terminal growth: ±1% in 0.5% steps
        terminal_rates = [0.015, 0.02, 0.025, 0.03, 0.035]

        matrix: List[List[float]] = []
        for dr in discount_rates:
            row = []
            for tg in terminal_rates:
                if dr <= tg:
                    row.append(float("inf"))
                    continue
                # Quick DCF
                pv = 0
                cf = fcf
                for yr in range(1, _PROJECTION_YEARS + 1):
                    decay = yr / _PROJECTION_YEARS
                    growth = base_growth * (1 - decay) + tg * decay
                    cf *= (1 + growth)
                    pv += cf / (1 + dr) ** yr
                tv = cf * (1 + tg) / (dr - tg)
                pv_tv = tv / (1 + dr) ** _PROJECTION_YEARS
                intrinsic = (pv + pv_tv) / shares if shares > 0 else 0
                row.append(round(intrinsic, 2))
            matrix.append(row)

        return {
            "symbol": symbol,
            "current_price": current_price,
            "discount_rates": [round(dr * 100, 1) for dr in discount_rates],
            "terminal_growth_rates": [round(tg * 100, 1) for tg in terminal_rates],
            "intrinsic_values_matrix": matrix,
            "base_wacc_pct": round(base_wacc * 100, 1),
        }

    except Exception as e:
        logger.error(f"Sensitivity analysis failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


# ── Summary ──────────────────────────────────────────────────


def get_dcf_summary(symbol: str) -> Dict[str, Any]:
    """
    Convenience function combining DCF analysis + sensitivity.

    Returns full DCF with scenarios, sensitivity matrix, margin of safety,
    and recommendation.
    """
    dcf = run_dcf_analysis(symbol)
    if "error" in dcf:
        return dcf

    sens = sensitivity_analysis(symbol)

    # Margin of safety (base case)
    base = dcf.get("scenarios", {}).get("base", {})
    intrinsic = base.get("intrinsic_value", 0)
    current = dcf.get("current_price", 0)
    margin_of_safety = round(
        (intrinsic - current) / intrinsic * 100, 1
    ) if intrinsic > 0 else 0

    dcf["sensitivity"] = sens
    dcf["margin_of_safety_pct"] = margin_of_safety

    return dcf
