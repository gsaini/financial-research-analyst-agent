"""
Theme Mapper Tools for the Thematic Investing Analysis feature.

This module provides theme-to-ticker mapping, batch stock data fetching,
theme performance aggregation, correlation analysis, and momentum scoring.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import yaml

import yfinance as yf
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────
# Theme Configuration Loader
# ─────────────────────────────────────────────────────────────

_themes_cache: Optional[Dict[str, Any]] = None


def _load_themes_config() -> Dict[str, Any]:
    """
    Load theme definitions from config/themes.yaml.
    Caches the config after first load for performance.

    Returns:
        Parsed YAML as a dictionary.
    """
    global _themes_cache
    if _themes_cache is not None:
        return _themes_cache

    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "themes.yaml"
    try:
        with open(config_path, "r") as f:
            _themes_cache = yaml.safe_load(f)
        logger.info(f"Loaded {len(_themes_cache.get('themes', {}))} theme definitions")
        return _themes_cache
    except Exception as e:
        logger.error(f"Failed to load themes config: {e}")
        return {"themes": {}, "benchmarks": {}, "performance_periods": [], "scoring": {}}


def reload_themes_config() -> Dict[str, Any]:
    """Force reload of theme configuration (useful after edits)."""
    global _themes_cache
    _themes_cache = None
    return _load_themes_config()


# ─────────────────────────────────────────────────────────────
# Theme Discovery & Lookup
# ─────────────────────────────────────────────────────────────


def list_available_themes() -> List[Dict[str, Any]]:
    """
    Return a summary list of all available themes.

    Returns:
        List of dicts with theme_id, name, description,
        constituent_count, risk_level, and growth_stage.
    """
    config = _load_themes_config()
    themes = config.get("themes", {})

    result = []
    for theme_id, theme_data in themes.items():
        result.append({
            "theme_id": theme_id,
            "name": theme_data.get("name", theme_id),
            "description": theme_data.get("description", "").strip(),
            "constituent_count": len(theme_data.get("constituents", [])),
            "constituents": theme_data.get("constituents", []),
            "reference_etfs": theme_data.get("reference_etfs", []),
            "sector_tags": theme_data.get("sector_tags", []),
            "risk_level": theme_data.get("risk_level", "Unknown"),
            "growth_stage": theme_data.get("growth_stage", "Unknown"),
        })
    return result


def get_theme_definition(theme_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the full definition for a specific theme.

    Args:
        theme_id: Theme identifier (e.g., 'ai_machine_learning').

    Returns:
        Theme definition dict or None.
    """
    config = _load_themes_config()
    themes = config.get("themes", {})

    # Exact match first
    if theme_id in themes:
        return {**themes[theme_id], "theme_id": theme_id}

    # Fuzzy-match by name (case-insensitive)
    for tid, tdata in themes.items():
        if tdata.get("name", "").lower() == theme_id.lower():
            return {**tdata, "theme_id": tid}

    return None


def get_theme_constituents(theme_id: str) -> List[str]:
    """
    Get the ticker list for a theme.

    Args:
        theme_id: Theme identifier.

    Returns:
        List of ticker symbols.
    """
    theme = get_theme_definition(theme_id)
    if theme is None:
        return []
    return theme.get("constituents", [])


# ─────────────────────────────────────────────────────────────
# Batch Data Fetching
# ─────────────────────────────────────────────────────────────


def fetch_theme_stock_data(
    symbols: List[str],
    period: str = "1y",
) -> Dict[str, Any]:
    """
    Fetch historical price data for multiple symbols simultaneously.

    Args:
        symbols: List of ticker symbols.
        period: yfinance period string (e.g., '1y', '6mo').

    Returns:
        Dict mapping symbol -> { closes, returns, dates, info, error? }.
    """
    results: Dict[str, Any] = {}

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                results[symbol] = {"error": f"No data available for {symbol}"}
                continue

            info = ticker.info
            closes = hist["Close"].tolist()
            returns = hist["Close"].pct_change().dropna().tolist()
            dates = [d.strftime("%Y-%m-%d") for d in hist.index]

            results[symbol] = {
                "closes": closes,
                "returns": returns,
                "dates": dates,
                "current_price": closes[-1] if closes else 0,
                "start_price": closes[0] if closes else 0,
                "total_return_pct": round(
                    ((closes[-1] - closes[0]) / closes[0]) * 100, 2
                )
                if closes and closes[0] > 0
                else 0,
                "market_cap": info.get("marketCap", 0),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "name": info.get("longName", info.get("shortName", symbol)),
            }
        except Exception as e:
            logger.warning(f"Error fetching data for {symbol}: {e}")
            results[symbol] = {"error": str(e)}

    return results


# ─────────────────────────────────────────────────────────────
# Performance Calculations
# ─────────────────────────────────────────────────────────────


def _calculate_period_return(closes: List[float], days: int) -> Optional[float]:
    """Calculate return over a specific number of trading days."""
    if len(closes) < days + 1:
        return None
    start = closes[-(days + 1)]
    end = closes[-1]
    if start <= 0:
        return None
    return round(((end - start) / start) * 100, 2)


def calculate_theme_performance(
    stock_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute aggregate theme performance across multiple time horizons.

    Args:
        stock_data: Output of fetch_theme_stock_data().

    Returns:
        Dict with per-period performance, top performers, laggards, etc.
    """
    config = _load_themes_config()
    periods = config.get("performance_periods", [])

    # Filter valid symbols
    valid_symbols = {
        sym: data for sym, data in stock_data.items() if "error" not in data
    }

    if not valid_symbols:
        return {"error": "No valid stock data to compute performance"}

    # Per-period aggregate
    theme_performance: Dict[str, Any] = {}
    for period_cfg in periods:
        period_key = period_cfg["period"]
        days = period_cfg.get("days")

        if days is None:
            # YTD: calculate days from Jan 1
            today = datetime.utcnow()
            start_of_year = datetime(today.year, 1, 1)
            days = (today - start_of_year).days

        returns_for_period = []
        for sym, data in valid_symbols.items():
            closes = data.get("closes", [])
            ret = _calculate_period_return(closes, days)
            if ret is not None:
                returns_for_period.append(ret)

        if returns_for_period:
            avg_return = round(np.mean(returns_for_period), 2)
            # Format with explicit sign
            sign = "+" if avg_return >= 0 else ""
            theme_performance[period_key] = f"{sign}{avg_return}%"
        else:
            theme_performance[period_key] = "N/A"

    # ── Top performers & laggards (by total period return) ──
    sym_returns = []
    for sym, data in valid_symbols.items():
        total_ret = data.get("total_return_pct", 0)
        sym_returns.append({"symbol": sym, "total_return": total_ret})

    sym_returns.sort(key=lambda x: x["total_return"], reverse=True)

    top_performers = [
        {"symbol": s["symbol"], "1_year_return": f"{'+' if s['total_return'] >= 0 else ''}{s['total_return']}%"}
        for s in sym_returns[:3]
    ]
    laggards = [
        {"symbol": s["symbol"], "1_year_return": f"{'+' if s['total_return'] >= 0 else ''}{s['total_return']}%"}
        for s in sym_returns[-3:]
    ]

    return {
        "theme_performance": theme_performance,
        "top_performers": top_performers,
        "laggards": laggards,
        "total_constituents": len(stock_data),
        "valid_constituents": len(valid_symbols),
        "failed_constituents": len(stock_data) - len(valid_symbols),
    }


# ─────────────────────────────────────────────────────────────
# Correlation & Risk
# ─────────────────────────────────────────────────────────────


def calculate_theme_correlation(stock_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute pairwise correlation and intra-theme diversification.

    Args:
        stock_data: Output of fetch_theme_stock_data().

    Returns:
        Dict with average intra-correlation, diversification score,
        and pairwise correlation matrix.
    """
    valid = {
        sym: data for sym, data in stock_data.items()
        if "error" not in data and len(data.get("returns", [])) > 20
    }

    if len(valid) < 2:
        return {
            "intra_correlation": None,
            "diversification_score": "Insufficient data",
            "matrix": {},
        }

    # Build returns matrix
    symbols = list(valid.keys())
    # Align to shortest series
    min_len = min(len(v["returns"]) for v in valid.values())
    returns_matrix = np.array(
        [valid[sym]["returns"][-min_len:] for sym in symbols]
    )

    corr_matrix = np.corrcoef(returns_matrix)

    # Average pairwise correlation (upper triangle, excluding diagonal)
    n = len(symbols)
    upper_tri = []
    pairwise: Dict[str, Dict[str, float]] = {}
    for i in range(n):
        pairwise[symbols[i]] = {}
        for j in range(n):
            corr_val = round(float(corr_matrix[i, j]), 3)
            pairwise[symbols[i]][symbols[j]] = corr_val
            if i < j:
                upper_tri.append(corr_val)

    avg_corr = round(float(np.mean(upper_tri)), 3) if upper_tri else 0.0

    # Diversification assessment
    if avg_corr >= 0.75:
        div_score = "Low"
        div_description = "High correlation — limited diversification benefit"
    elif avg_corr >= 0.50:
        div_score = "Moderate"
        div_description = "Moderate correlation — some diversification"
    elif avg_corr >= 0.25:
        div_score = "Good"
        div_description = "Low-to-moderate correlation — good diversification"
    else:
        div_score = "Excellent"
        div_description = "Low correlation — excellent diversification"

    return {
        "intra_correlation": avg_corr,
        "diversification_score": div_score,
        "diversification_description": div_description,
        "correlation_matrix": pairwise,
    }


# ─────────────────────────────────────────────────────────────
# Sector Overlap
# ─────────────────────────────────────────────────────────────


def calculate_sector_overlap(stock_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Compute what percentage of theme constituents belong to each sector.

    Args:
        stock_data: Output of fetch_theme_stock_data().

    Returns:
        Dict with sector -> percentage string.
    """
    valid = {
        sym: data for sym, data in stock_data.items() if "error" not in data
    }
    total = len(valid)
    if total == 0:
        return {}

    sector_count: Dict[str, int] = {}
    for data in valid.values():
        sector = data.get("sector", "Unknown")
        sector_count[sector] = sector_count.get(sector, 0) + 1

    return {
        sector: f"{round(count / total * 100)}%"
        for sector, count in sorted(sector_count.items(), key=lambda x: -x[1])
    }


# ─────────────────────────────────────────────────────────────
# Momentum Scoring
# ─────────────────────────────────────────────────────────────


def calculate_momentum_score(stock_data: Dict[str, Any]) -> int:
    """
    Compute a 0–100 momentum score for a theme.

    Combines short-term (1-week, 1-month), medium-term (3-month),
    and long-term (6-month, 1-year) returns with configurable weights.

    Args:
        stock_data: Output of fetch_theme_stock_data().

    Returns:
        Integer momentum score 0–100.
    """
    config = _load_themes_config()
    scoring = config.get("scoring", {}).get("momentum", {})
    short_w = scoring.get("short_term_weight", 0.3)
    med_w = scoring.get("medium_term_weight", 0.4)
    long_w = scoring.get("long_term_weight", 0.3)

    valid = {
        sym: data for sym, data in stock_data.items() if "error" not in data
    }
    if not valid:
        return 0

    def _avg_return(days: int) -> float:
        rets = []
        for data in valid.values():
            r = _calculate_period_return(data.get("closes", []), days)
            if r is not None:
                rets.append(r)
        return np.mean(rets) if rets else 0

    ret_1w = _avg_return(5)
    ret_1m = _avg_return(21)
    ret_3m = _avg_return(63)
    ret_6m = _avg_return(126)
    ret_1y = _avg_return(252)

    short_term = (ret_1w + ret_1m) / 2
    medium_term = ret_3m
    long_term = (ret_6m + ret_1y) / 2

    # Normalise to 0-100 range using sigmoid-like approach
    raw = short_term * short_w + medium_term * med_w + long_term * long_w

    # Map: -50% -> ~0, 0% -> 50, +50% -> ~100
    score = int(100 / (1 + np.exp(-raw / 10)))
    return max(0, min(100, score))


# ─────────────────────────────────────────────────────────────
# Theme Health Score
# ─────────────────────────────────────────────────────────────


def calculate_theme_health_score(
    performance_data: Dict[str, Any],
    correlation_data: Dict[str, Any],
    momentum_score: int,
) -> Dict[str, Any]:
    """
    Compute an overall theme health score (0–100).

    Combines performance, momentum, diversification, and risk metrics.

    Args:
        performance_data: Output of calculate_theme_performance().
        correlation_data: Output of calculate_theme_correlation().
        momentum_score: From calculate_momentum_score().

    Returns:
        Dict with health_score and component breakdowns.
    """
    config = _load_themes_config()
    weights = config.get("scoring", {}).get("health", {})

    perf_w = weights.get("performance_weight", 0.35)
    mom_w = weights.get("momentum_weight", 0.25)
    div_w = weights.get("diversification_weight", 0.20)
    risk_w = weights.get("risk_weight", 0.20)

    # Performance score: use 1-year return as proxy
    perf_str = performance_data.get("theme_performance", {}).get("1y", "0%")
    try:
        perf_val = float(perf_str.replace("%", "").replace("+", ""))
    except (ValueError, AttributeError):
        perf_val = 0
    # Scale: -30% -> 0, 0 -> 40, +60% -> 100
    perf_score = max(0, min(100, (perf_val + 30) * (100 / 90)))

    # Momentum is already 0-100
    mom_score = momentum_score

    # Diversification: Lower correlation is better
    avg_corr = correlation_data.get("intra_correlation")
    if avg_corr is not None:
        div_score = max(0, min(100, (1 - avg_corr) * 100))
    else:
        div_score = 50  # default

    # Risk: based on standard deviation of constituent returns
    # Less risk -> higher score
    risk_score = max(0, min(100, 100 - abs(perf_val) * 0.5))

    health = int(
        perf_score * perf_w
        + mom_score * mom_w
        + div_score * div_w
        + risk_score * risk_w
    )
    health = max(0, min(100, health))

    return {
        "health_score": health,
        "components": {
            "performance_score": round(perf_score, 1),
            "momentum_score": mom_score,
            "diversification_score": round(div_score, 1),
            "risk_score": round(risk_score, 1),
        },
        "weights": {
            "performance": perf_w,
            "momentum": mom_w,
            "diversification": div_w,
            "risk": risk_w,
        },
    }


# ─────────────────────────────────────────────────────────────
# Full Theme Analysis (orchestrates all)
# ─────────────────────────────────────────────────────────────


def analyze_theme(theme_id: str) -> Dict[str, Any]:
    """
    Run a complete thematic investing analysis.

    This is the main entry-point used by the ThematicAnalystAgent.

    Args:
        theme_id: Theme identifier from themes.yaml.

    Returns:
        Comprehensive theme analysis dict.
    """
    theme_def = get_theme_definition(theme_id)
    if theme_def is None:
        return {"error": f"Theme '{theme_id}' not found"}

    constituents = theme_def.get("constituents", [])
    if not constituents:
        return {"error": f"Theme '{theme_id}' has no constituents"}

    logger.info(
        f"Analyzing theme '{theme_def.get('name')}' with {len(constituents)} constituents"
    )

    # 1. Fetch stock data
    stock_data = fetch_theme_stock_data(constituents, period="1y")

    # 2. Performance analysis
    performance = calculate_theme_performance(stock_data)

    # 3. Correlation & risk
    correlation = calculate_theme_correlation(stock_data)

    # 4. Sector overlap
    sector_overlap = calculate_sector_overlap(stock_data)

    # 5. Momentum
    momentum = calculate_momentum_score(stock_data)

    # 6. Health score
    health = calculate_theme_health_score(performance, correlation, momentum)

    return {
        "theme": theme_def.get("name"),
        "theme_id": theme_def.get("theme_id"),
        "description": theme_def.get("description", "").strip(),
        "constituents": constituents,
        "reference_etfs": theme_def.get("reference_etfs", []),
        "risk_level": theme_def.get("risk_level", "Unknown"),
        "growth_stage": theme_def.get("growth_stage", "Unknown"),
        "theme_performance": performance.get("theme_performance", {}),
        "momentum_score": momentum,
        "top_performers": performance.get("top_performers", []),
        "laggards": performance.get("laggards", []),
        "sector_overlap": sector_overlap,
        "theme_risk": {
            "intra_correlation": correlation.get("intra_correlation"),
            "diversification_score": correlation.get("diversification_score"),
            "diversification_description": correlation.get(
                "diversification_description", ""
            ),
        },
        "theme_health_score": health.get("health_score", 0),
        "health_components": health.get("components", {}),
        "constituent_details": {
            sym: {
                "name": data.get("name", sym),
                "current_price": data.get("current_price"),
                "total_return_pct": data.get("total_return_pct"),
                "market_cap": data.get("market_cap"),
                "sector": data.get("sector"),
            }
            for sym, data in stock_data.items()
            if "error" not in data
        },
        "failed_constituents": [
            sym for sym, data in stock_data.items() if "error" in data
        ],
        "analyzed_at": datetime.utcnow().isoformat(),
    }
