"""
Macroeconomic Data Tool (Phase 2.1).

Fetches key economic indicators from the FRED API (Federal Reserve
Economic Data) for macro context in financial analysis.

Usage::

    from src.tools.macro_data import get_macro_summary
    data = get_macro_summary()
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

# FRED series IDs
_SERIES = {
    "federal_funds_rate": "FEDFUNDS",
    "cpi": "CPIAUCSL",
    "gdp": "GDP",
    "unemployment": "UNRATE",
    "consumer_confidence": "UMCSENT",
    "pmi": "NAPM",
    "housing_starts": "HOUST",
    "treasury_2y": "DGS2",
    "treasury_10y": "DGS10",
    "treasury_30y": "DGS30",
}

# Sector rate sensitivity mapping
_SECTOR_RATE_SENSITIVITY = {
    "Real Estate": ("high_negative", "Rising rates increase mortgage costs and reduce property valuations."),
    "Utilities": ("high_negative", "Higher rates make utility dividend yields less attractive vs bonds."),
    "Consumer Defensive": ("moderate_negative", "Higher borrowing costs reduce consumer spending power."),
    "Financial Services": ("positive", "Banks benefit from wider net interest margins in rising rate environments."),
    "Financials": ("positive", "Banks benefit from wider net interest margins."),
    "Technology": ("moderate_negative", "Higher discount rates compress growth stock valuations."),
    "Healthcare": ("low_impact", "Demand is relatively inelastic to interest rates."),
    "Energy": ("low_impact", "Driven more by commodity prices than interest rates."),
    "Industrials": ("moderate_negative", "Higher rates slow capital investment."),
    "Consumer Cyclical": ("moderate_negative", "Consumers defer big purchases when borrowing costs rise."),
    "Communication Services": ("low_impact", "Mixed — some growth compression but stable demand."),
    "Basic Materials": ("low_impact", "Commodity-driven, limited direct rate sensitivity."),
}


def _get_fred():
    """Create a FRED client. Returns None if unavailable."""
    try:
        from src.config import settings
        api_key = settings.data_api.fred_api_key
        if not api_key or api_key in ("", "your_fred_api_key"):
            return None
        from fredapi import Fred
        return Fred(api_key=api_key)
    except ImportError:
        logger.warning("fredapi not installed — run: pip install fredapi")
        return None
    except Exception as e:
        logger.warning(f"FRED client creation failed: {e}")
        return None


def _unavailable(msg: str = "FRED API not configured") -> Dict[str, Any]:
    return {"source": "unavailable", "message": msg}


def _get_latest(fred, series_id: str, periods: int = 2):
    """Get latest N values from a FRED series."""
    try:
        data = fred.get_series(series_id)
        data = data.dropna()
        if len(data) < 1:
            return None, None
        current = float(data.iloc[-1])
        previous = float(data.iloc[-2]) if len(data) >= 2 else None
        return current, previous
    except Exception as e:
        logger.debug(f"FRED series {series_id} fetch failed: {e}")
        return None, None


def _direction(current, previous) -> str:
    if current is None or previous is None:
        return "unknown"
    if current > previous * 1.001:
        return "rising"
    elif current < previous * 0.999:
        return "falling"
    return "stable"


def _yoy_change(fred, series_id: str) -> Optional[float]:
    """Calculate year-over-year percentage change."""
    try:
        data = fred.get_series(series_id)
        data = data.dropna()
        if len(data) < 13:
            return None
        current = float(data.iloc[-1])
        year_ago = float(data.iloc[-13])  # ~12 months ago
        if year_ago == 0:
            return None
        return round((current - year_ago) / year_ago * 100, 2)
    except Exception:
        return None


# ── Public API ───────────────────────────────────────────────


def get_macro_summary() -> Dict[str, Any]:
    """
    Fetch key macroeconomic indicators from FRED.

    Returns dict with indicators including current values, previous values,
    and direction for: fed funds rate, CPI, GDP, unemployment,
    consumer confidence, PMI, housing starts.
    """
    fred = _get_fred()
    if fred is None:
        return _unavailable()

    indicators: Dict[str, Any] = {}

    # Federal Funds Rate
    curr, prev = _get_latest(fred, _SERIES["federal_funds_rate"])
    indicators["federal_funds_rate"] = {
        "current": curr, "previous": prev,
        "direction": _direction(curr, prev),
        "unit": "%",
    }

    # CPI — year-over-year change
    cpi_yoy = _yoy_change(fred, _SERIES["cpi"])
    cpi_curr, cpi_prev_month = _get_latest(fred, _SERIES["cpi"])
    indicators["cpi_yoy"] = {
        "current": cpi_yoy,
        "direction": _direction(cpi_yoy, 3.0) if cpi_yoy else "unknown",  # 3% as neutral benchmark
        "unit": "% YoY",
    }

    # GDP
    gdp_curr, gdp_prev = _get_latest(fred, _SERIES["gdp"])
    gdp_growth = None
    if gdp_curr and gdp_prev and gdp_prev > 0:
        gdp_growth = round((gdp_curr - gdp_prev) / gdp_prev * 100, 2)
    indicators["gdp_growth"] = {
        "current": gdp_growth,
        "direction": _direction(gdp_growth, 0) if gdp_growth is not None else "unknown",
        "unit": "% QoQ",
    }

    # Unemployment
    curr, prev = _get_latest(fred, _SERIES["unemployment"])
    indicators["unemployment"] = {
        "current": curr, "previous": prev,
        "direction": _direction(curr, prev),
        "unit": "%",
    }

    # Consumer Confidence
    curr, prev = _get_latest(fred, _SERIES["consumer_confidence"])
    indicators["consumer_confidence"] = {
        "current": curr, "previous": prev,
        "direction": _direction(curr, prev),
    }

    # PMI
    curr, prev = _get_latest(fred, _SERIES["pmi"])
    indicators["pmi"] = {
        "current": curr, "previous": prev,
        "direction": _direction(curr, prev),
        "expansion": curr > 50 if curr else None,
    }

    # Housing Starts
    curr, prev = _get_latest(fred, _SERIES["housing_starts"])
    indicators["housing_starts"] = {
        "current": curr, "previous": prev,
        "direction": _direction(curr, prev),
        "unit": "thousands",
    }

    return {
        "source": "fred",
        "indicators": indicators,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_treasury_yields() -> Dict[str, Any]:
    """
    Fetch treasury yields and calculate yield curve status.

    Returns 2Y, 10Y, 30Y yields, 2Y-10Y spread, and curve status
    (normal/flat/inverted).
    """
    fred = _get_fred()
    if fred is None:
        return _unavailable()

    y2, _ = _get_latest(fred, _SERIES["treasury_2y"])
    y10, _ = _get_latest(fred, _SERIES["treasury_10y"])
    y30, _ = _get_latest(fred, _SERIES["treasury_30y"])

    yields = {"2y": y2, "10y": y10, "30y": y30}

    spread = None
    curve_status = "unknown"
    if y2 is not None and y10 is not None:
        spread = round(y10 - y2, 3)
        if spread < -0.1:
            curve_status = "inverted"
        elif spread < 0.2:
            curve_status = "flat"
        else:
            curve_status = "normal"

    return {
        "source": "fred",
        "yields": yields,
        "spread_2y_10y": spread,
        "curve_status": curve_status,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_rate_environment() -> Dict[str, Any]:
    """
    Analyze the current rate environment.

    Returns fed stance, inflation trend, real rate, and sector impact.
    """
    fred = _get_fred()
    if fred is None:
        return _unavailable()

    # Fed funds rate and direction
    ff_curr, ff_prev = _get_latest(fred, _SERIES["federal_funds_rate"])

    if ff_curr is not None and ff_prev is not None:
        if ff_curr > ff_prev + 0.1:
            fed_stance = "hiking"
        elif ff_curr < ff_prev - 0.1:
            fed_stance = "cutting"
        else:
            fed_stance = "holding"
    else:
        fed_stance = "unknown"

    # CPI for inflation trend
    cpi_yoy = _yoy_change(fred, _SERIES["cpi"])
    if cpi_yoy is not None:
        if cpi_yoy > 4:
            inflation_trend = "elevated"
        elif cpi_yoy > 2.5:
            inflation_trend = "above_target"
        elif cpi_yoy > 1.5:
            inflation_trend = "near_target"
        else:
            inflation_trend = "below_target"
    else:
        inflation_trend = "unknown"

    # Real rate
    real_rate = None
    if ff_curr is not None and cpi_yoy is not None:
        real_rate = round(ff_curr - cpi_yoy, 2)

    # Sector impact
    sector_impact: Dict[str, Any] = {}
    for sector, (sensitivity, explanation) in _SECTOR_RATE_SENSITIVITY.items():
        if fed_stance == "hiking":
            if "negative" in sensitivity:
                direction = "negative"
            elif sensitivity == "positive":
                direction = "positive"
            else:
                direction = "neutral"
        elif fed_stance == "cutting":
            if "negative" in sensitivity:
                direction = "positive"
            elif sensitivity == "positive":
                direction = "negative"
            else:
                direction = "neutral"
        else:
            direction = "neutral"

        sector_impact[sector] = {
            "sensitivity": sensitivity,
            "direction": direction,
            "assessment": explanation,
        }

    return {
        "source": "fred",
        "fed_funds_rate": ff_curr,
        "fed_stance": fed_stance,
        "cpi_yoy": cpi_yoy,
        "inflation_trend": inflation_trend,
        "real_rate": real_rate,
        "sector_impact": sector_impact,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_macro_context_for_stock(symbol: str) -> Dict[str, Any]:
    """
    Contextualize macro environment for a specific stock's sector.

    Args:
        symbol: Stock ticker.

    Returns:
        Dict with sector, rate sensitivity, impact direction, and assessment.
    """
    fred = _get_fred()
    if fred is None:
        return _unavailable()

    # Get stock sector
    try:
        from src.data import get_provider
        provider = get_provider()
        info = provider.get_info(symbol)
        sector = info.get("sector", "Unknown")
    except Exception:
        sector = "Unknown"

    # Get rate environment
    rate_env = get_rate_environment()
    fed_stance = rate_env.get("fed_stance", "unknown")

    # Find sector sensitivity
    sensitivity_info = _SECTOR_RATE_SENSITIVITY.get(sector, ("low_impact", "No specific rate sensitivity data."))
    sensitivity, explanation = sensitivity_info

    # Determine impact
    if fed_stance == "hiking":
        if "negative" in sensitivity:
            impact = "negative"
        elif sensitivity == "positive":
            impact = "positive"
        else:
            impact = "neutral"
    elif fed_stance == "cutting":
        if "negative" in sensitivity:
            impact = "positive"
        elif sensitivity == "positive":
            impact = "negative"
        else:
            impact = "neutral"
    else:
        impact = "neutral"

    key_factors = []
    if rate_env.get("cpi_yoy"):
        key_factors.append(f"Inflation at {rate_env['cpi_yoy']:.1f}% YoY")
    if rate_env.get("fed_funds_rate"):
        key_factors.append(f"Fed funds rate at {rate_env['fed_funds_rate']:.2f}%")
    if rate_env.get("real_rate") is not None:
        key_factors.append(f"Real rate at {rate_env['real_rate']:.2f}%")
    key_factors.append(f"Fed stance: {fed_stance}")

    return {
        "symbol": symbol,
        "sector": sector,
        "rate_sensitivity": sensitivity,
        "impact_direction": impact,
        "assessment": explanation,
        "key_factors": key_factors,
        "fed_stance": fed_stance,
        "source": "fred",
    }
