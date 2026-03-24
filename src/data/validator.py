"""
Data Quality Validator.

Validates market data returned by any ``MarketDataProvider`` to catch stale,
missing, or suspicious data before it reaches analysis tools.

Usage::

    from src.data.validator import validate_info, validate_history

    info = provider.get_info("AAPL")
    issues = validate_info(info)
    if issues:
        logger.warning(f"Data quality issues: {issues}")
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Info validation ──────────────────────────────────────────────


def validate_info(info: Dict[str, Any]) -> List[str]:
    """
    Validate a company info dict.

    Returns a list of issue descriptions (empty = no issues).
    """
    issues: List[str] = []

    if not info:
        issues.append("Empty info dict — provider returned no data")
        return issues

    # Required fields for downstream tools
    required = ["currentPrice", "regularMarketPrice"]
    has_price = any(info.get(f) for f in required)
    if not has_price:
        issues.append("Missing price data (currentPrice / regularMarketPrice)")

    # Market cap sanity
    mktcap = info.get("marketCap", 0)
    if mktcap and mktcap < 0:
        issues.append(f"Negative market cap: {mktcap}")

    # P/E sanity
    pe = info.get("trailingPE")
    if pe is not None and (pe < 0 or pe > 10000):
        issues.append(f"Suspicious P/E ratio: {pe}")

    return issues


# ── Historical data validation ───────────────────────────────────


def validate_history(
    df: pd.DataFrame,
    expected_period: str = "1y",
    symbol: str = "",
) -> List[str]:
    """
    Validate a historical OHLCV DataFrame.

    Returns a list of issue descriptions.
    """
    issues: List[str] = []
    prefix = f"[{symbol}] " if symbol else ""

    if df is None or df.empty:
        issues.append(f"{prefix}Empty historical data")
        return issues

    # Check for required columns
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    # Also accept lowercase
    actual_cols = set(df.columns)
    has_cols = required_cols.issubset(actual_cols) or {c.lower() for c in required_cols}.issubset(
        {c.lower() for c in actual_cols}
    )
    if not has_cols:
        issues.append(f"{prefix}Missing OHLCV columns, found: {list(df.columns)}")

    # Check for NaN rows
    nan_pct = df.isna().any(axis=1).mean()
    if nan_pct > 0.1:
        issues.append(f"{prefix}{nan_pct:.0%} of rows contain NaN values")

    # Check for stale data (last row > 5 trading days old)
    if hasattr(df.index, "max"):
        last_date = df.index.max()
        if hasattr(last_date, "date"):
            days_old = (datetime.now(timezone.utc) - last_date.to_pydatetime().replace(tzinfo=timezone.utc)).days
            if days_old > 7:
                issues.append(f"{prefix}Data may be stale — last date is {days_old} days ago ({last_date.date()})")

    # Check for price outliers (>50% daily change)
    close_col = "Close" if "Close" in df.columns else "close" if "close" in df.columns else None
    if close_col and len(df) > 1:
        returns = df[close_col].pct_change().dropna()
        extreme = returns.abs() > 0.5
        if extreme.any():
            count = extreme.sum()
            issues.append(
                f"{prefix}{count} day(s) with >50% price change detected — possible data error"
            )

    # Expected row count
    period_min_rows = {
        "1d": 1, "5d": 3, "1mo": 15, "3mo": 50,
        "6mo": 100, "1y": 200, "2y": 400, "5y": 1000,
    }
    min_rows = period_min_rows.get(expected_period, 0)
    if min_rows and len(df) < min_rows:
        issues.append(
            f"{prefix}Expected ~{min_rows}+ rows for period={expected_period}, got {len(df)}"
        )

    return issues


# ── Financial statement validation ───────────────────────────────


def validate_financials(df: pd.DataFrame, symbol: str = "") -> List[str]:
    """Validate a financial statement DataFrame."""
    issues: List[str] = []
    prefix = f"[{symbol}] " if symbol else ""

    if df is None or df.empty:
        issues.append(f"{prefix}Empty financial statement data")
        return issues

    if len(df.columns) < 2:
        issues.append(f"{prefix}Financial statement has fewer than 2 periods — limited trend analysis")

    return issues


# ── Cross-provider consistency check ─────────────────────────────


def cross_validate_price(
    price_a: float,
    price_b: float,
    source_a: str = "primary",
    source_b: str = "secondary",
    tolerance: float = 0.02,
) -> Optional[str]:
    """
    Compare prices from two providers.

    Returns an issue string if the prices diverge by more than ``tolerance``
    (default 2%), or None if they're consistent.
    """
    if not price_a or not price_b:
        return None

    diff_pct = abs(price_a - price_b) / max(price_a, price_b)
    if diff_pct > tolerance:
        return (
            f"Price mismatch: {source_a}={price_a:.2f} vs {source_b}={price_b:.2f} "
            f"({diff_pct:.1%} divergence, tolerance={tolerance:.0%})"
        )
    return None
