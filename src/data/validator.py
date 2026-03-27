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

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Market hours awareness ───────────────────────────────────────


def is_market_open() -> bool:
    """Check if US stock market is currently in trading hours (approximate)."""
    from datetime import timezone as tz

    now = datetime.now(tz.utc)
    # US market: Mon-Fri, 9:30-16:00 ET (14:30-21:00 UTC, rough)
    if now.weekday() >= 5:
        return False
    hour_utc = now.hour
    return 14 <= hour_utc <= 21


def _trading_days_since(dt: datetime) -> int:
    """Approximate number of trading days between dt and now."""
    now = datetime.now(timezone.utc)
    if hasattr(dt, "tzinfo") and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = (now - dt).days
    # Roughly 5/7 of calendar days are trading days
    return max(0, int(delta * 5 / 7))


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

    # EPS sanity — warn on extreme values
    eps = info.get("trailingEps")
    if eps is not None and abs(eps) > 10000:
        issues.append(f"Suspicious EPS value: {eps}")

    # Check for missing key fields used by downstream tools
    recommended = [
        "marketCap", "sector", "industry", "trailingPE", "trailingEps",
        "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    ]
    missing = [f for f in recommended if info.get(f) is None]
    if missing:
        issues.append(f"Missing recommended fields: {', '.join(missing)}")

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

    # Stale data detection (market-hours aware)
    if hasattr(df.index, "max"):
        last_date = df.index.max()
        if hasattr(last_date, "date"):
            last_dt = last_date.to_pydatetime()
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            trading_days_old = _trading_days_since(last_dt)
            if trading_days_old > 3:
                issues.append(
                    f"{prefix}Data may be stale — last date is ~{trading_days_old} trading days ago ({last_date.date()})"
                )
            elif trading_days_old > 1 and is_market_open():
                issues.append(
                    f"{prefix}Data is {trading_days_old} trading day(s) behind during market hours"
                )

    # Price outlier detection (>20% daily change flagged, >50% likely error)
    close_col = "Close" if "Close" in df.columns else "close" if "close" in df.columns else None
    if close_col and len(df) > 1:
        returns = df[close_col].pct_change().dropna()
        flagged = returns.abs() > 0.20
        extreme = returns.abs() > 0.50
        if extreme.any():
            count = int(extreme.sum())
            issues.append(
                f"{prefix}{count} day(s) with >50% price change — likely data error"
            )
        elif flagged.any():
            count = int(flagged.sum())
            dates = list(returns[flagged].index[:3])
            date_strs = [str(d.date()) if hasattr(d, "date") else str(d) for d in dates]
            issues.append(
                f"{prefix}{count} day(s) with >20% price change (first: {', '.join(date_strs)}) — verify"
            )

    # OHLC consistency: High >= Low, High >= Close, Low <= Close
    if all(c in df.columns for c in ["High", "Low", "Close"]):
        bad_hl = (df["High"] < df["Low"]).sum()
        if bad_hl > 0:
            issues.append(f"{prefix}{bad_hl} row(s) where High < Low — data integrity issue")

    # Zero/negative volume check
    vol_col = "Volume" if "Volume" in df.columns else "volume" if "volume" in df.columns else None
    if vol_col:
        zero_vol = (df[vol_col] <= 0).sum()
        if zero_vol > len(df) * 0.1:
            issues.append(f"{prefix}{zero_vol} row(s) with zero/negative volume ({zero_vol/len(df):.0%})")

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

    # Check for all-NaN rows (line items with no data)
    all_nan_rows = df.isna().all(axis=1).sum()
    if all_nan_rows > len(df) * 0.3:
        issues.append(f"{prefix}{all_nan_rows}/{len(df)} line items are entirely NaN")

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


# ── Comprehensive validation helper ──────────────────────────────


def validate_all(
    symbol: str,
    info: Optional[Dict[str, Any]] = None,
    history: Optional[pd.DataFrame] = None,
    financials: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Run all applicable validations and return a structured report.

    Returns::

        {
            "symbol": "AAPL",
            "is_valid": True,  # no critical issues
            "issues": [...],
            "warnings": [...],
            "checks_run": 3,
        }
    """
    all_issues: List[str] = []
    checks = 0

    if info is not None:
        all_issues.extend(validate_info(info))
        checks += 1

    if history is not None:
        all_issues.extend(validate_history(history, symbol=symbol))
        checks += 1

    if financials is not None:
        all_issues.extend(validate_financials(financials, symbol=symbol))
        checks += 1

    # Classify: critical issues vs warnings
    critical_keywords = ["empty", "missing price", "data error", "integrity"]
    critical = [i for i in all_issues if any(k in i.lower() for k in critical_keywords)]
    warnings = [i for i in all_issues if i not in critical]

    if all_issues:
        logger.warning(f"[{symbol}] Data quality: {len(critical)} critical, {len(warnings)} warnings")

    return {
        "symbol": symbol,
        "is_valid": len(critical) == 0,
        "issues": critical,
        "warnings": warnings,
        "checks_run": checks,
    }
