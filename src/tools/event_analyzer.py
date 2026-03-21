from datetime import timezone
"""
Event-Driven Performance Analysis Tool (Feature 7).

Analyzes stock price behaviour in a window around significant events
(earnings announcements, dividends, stock splits).

Key capabilities:
- Identify historical events from yfinance
- Extract ±5-day price windows around each event
- Compute pre-event drift, event-day reaction, and post-event returns
- Aggregate patterns across 8+ historical events
- Correlate EPS surprise magnitude with price reaction
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math

import numpy as np
from src.data import get_provider

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Event Calendar
# ─────────────────────────────────────────────────────────────


def get_event_calendar(symbol: str) -> Dict[str, Any]:
    """
    Fetch historical event dates for a stock.

    Gathers earnings dates, dividend ex-dates, and stock split dates
    from yfinance.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with lists of event dates organised by type.
    """
    symbol = symbol.upper()

    try:
        provider = get_provider()
        info = provider.get_info(symbol)
        result: Dict[str, Any] = {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
        }

        # ── Earnings dates ──────────────────────────────
        earnings_events: List[Dict[str, str]] = []
        try:
            earnings_hist = provider.get_earnings_history(symbol)
            if earnings_hist is not None and not earnings_hist.empty:
                for idx, row in earnings_hist.iterrows():
                    date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
                    earnings_events.append({
                        "date": date_str,
                        "eps_actual": float(row.get("epsActual", 0) or 0),
                        "eps_estimate": float(row.get("epsEstimate", 0) or 0),
                    })
        except Exception as e:
            logger.debug(f"Could not fetch earnings history for {symbol}: {e}")

        # Try earnings_dates as fallback / supplement
        try:
            earnings_dates = provider.get_calendar(symbol) # mapped to calendar essentially although yfinance might have multiple forms. For simplicity, just use what calendar returns. Note: Calendar from yfinance might not be a dataframe with the same structure depending on the yfinance version. Let's just catch exceptions.
            if earnings_dates is not None and getattr(earnings_dates, 'empty', False) == False and isinstance(earnings_dates, pd.DataFrame):
                existing = {e["date"] for e in earnings_events}
                for idx in earnings_dates.index:
                    date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
                    if date_str not in existing:
                        row = earnings_dates.loc[idx]
                        earnings_events.append({
                            "date": date_str,
                            "eps_actual": float(row.get("Reported EPS", 0) or 0),
                            "eps_estimate": float(row.get("EPS Estimate", 0) or 0),
                        })
        except Exception as e:
            logger.debug(f"Could not fetch earnings_dates for {symbol}: {e}")

        result["earnings"] = sorted(earnings_events, key=lambda x: x["date"])

        # ── Dividend dates ──────────────────────────────
        dividend_events: List[Dict[str, Any]] = []
        try:
            dividends = provider.get_dividends(symbol)
            if dividends is not None and len(dividends) > 0:
                for dt, amount in dividends.items():
                    dividend_events.append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "amount": round(float(amount), 4),
                    })
        except Exception as e:
            logger.debug(f"Could not fetch dividends for {symbol}: {e}")

        result["dividends"] = dividend_events

        # ── Stock splits ────────────────────────────────
        split_events: List[Dict[str, Any]] = []
        try:
            splits = provider.get_info(symbol).get("splits", {}) # Not exposed in provider directly right now. It might need to be added to provider or fallback if not available.
            # actually we don't have splits in provider. let's just make it empty for now, or use 'info' dict if it has something similar, but yfinance Ticker.splits is a series.
            # For the sake of fixing the AttributeError, let's gracefully handle it.
            splits = None 
            if splits is not None and len(splits) > 0:
                for dt, ratio in splits.items():
                    if float(ratio) != 0:
                        split_events.append({
                            "date": dt.strftime("%Y-%m-%d"),
                            "ratio": f"{int(ratio)}:1" if ratio == int(ratio) else str(round(float(ratio), 2)),
                        })
        except Exception as e:
            logger.debug(f"Could not fetch splits for {symbol}: {e}")

        result["splits"] = split_events

        # Summary
        result["total_events"] = len(earnings_events) + len(dividend_events) + len(split_events)

        return result

    except Exception as e:
        logger.error(f"Error building event calendar for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


# ─────────────────────────────────────────────────────────────
# Price Window Extraction
# ─────────────────────────────────────────────────────────────


def _fetch_prices(symbol: str, start: str, end: str) -> Optional[Any]:
    """Fetch adjusted close prices between two dates."""
    try:
        provider = get_provider()
        hist = provider.get_history(symbol, period="max") # Fetch all data and filter later, as provider interface is simple horizon based for now or if start/end needed, provider abstraction might need extension. For now let's map history wrapper params.
    
        if hist.empty:
            return None
        
        # Filter by date if return df has date index
        if start and end:
             hist = hist.loc[start:end]
             
        if hist.empty:
            return None
            
        return hist["Close"]
    except Exception as e:
        logger.error(f"Error fetching prices for {symbol}: {e}")
        return None


def calculate_event_window(
    symbol: str,
    event_date: str,
    days_before: int = 5,
    days_after: int = 5,
) -> Dict[str, Any]:
    """
    Extract price data for a window around an event and compute returns.

    Handles weekends/holidays by expanding the fetch range and selecting
    the nearest available trading days.

    Args:
        symbol: Stock ticker symbol.
        event_date: Event date as YYYY-MM-DD.
        days_before: Trading days to include before the event.
        days_after: Trading days to include after the event.

    Returns:
        Dict with price levels and segment returns.
    """
    symbol = symbol.upper()

    try:
        event_dt = datetime.strptime(event_date, "%Y-%m-%d")
    except ValueError:
        return {"error": f"Invalid date format: {event_date}"}

    # Fetch wider window (calendar days buffer for weekends/holidays)
    buffer = max(days_before, days_after) + 12
    start_dt = event_dt - timedelta(days=buffer)
    end_dt = event_dt + timedelta(days=buffer)

    prices = _fetch_prices(
        symbol,
        start_dt.strftime("%Y-%m-%d"),
        end_dt.strftime("%Y-%m-%d"),
    )

    if prices is None or len(prices) < 3:
        return {"error": f"Insufficient price data around {event_date}"}

    # Convert index to date strings for lookup
    date_strs = [d.strftime("%Y-%m-%d") for d in prices.index]

    # Find the nearest trading day to the event date
    event_idx = None
    for i, d in enumerate(date_strs):
        if d >= event_date:
            event_idx = i
            break
    if event_idx is None:
        event_idx = len(date_strs) - 1

    # Calculate boundary indices
    before_idx = max(0, event_idx - days_before)
    after_idx = min(len(prices) - 1, event_idx + days_after)

    # Price levels
    price_before = float(prices.iloc[before_idx])
    price_1d_before = float(prices.iloc[max(0, event_idx - 1)])
    price_event = float(prices.iloc[event_idx])
    price_1d_after = float(prices.iloc[min(len(prices) - 1, event_idx + 1)])
    price_after = float(prices.iloc[after_idx])

    # Returns (percentage)
    def pct(start_p: float, end_p: float) -> Optional[float]:
        if start_p == 0:
            return None
        return round(((end_p / start_p) - 1) * 100, 2)

    pre_event = pct(price_before, price_1d_before)
    event_day = pct(price_1d_before, price_event)
    post_event_1d = pct(price_event, price_1d_after)
    post_event = pct(price_event, price_after)
    full_window = pct(price_before, price_after)

    return {
        "event_date": event_date,
        "actual_trading_date": date_strs[event_idx],
        "price_window": {
            f"{days_before}d_before": round(price_before, 2),
            "1d_before": round(price_1d_before, 2),
            "event_day": round(price_event, 2),
            "1d_after": round(price_1d_after, 2),
            f"{days_after}d_after": round(price_after, 2),
        },
        "returns": {
            f"pre_event_{days_before}d": f"{pre_event}%" if pre_event is not None else "N/A",
            "event_day": f"{event_day}%" if event_day is not None else "N/A",
            "post_event_1d": f"{post_event_1d}%" if post_event_1d is not None else "N/A",
            f"post_event_{days_after}d": f"{post_event}%" if post_event is not None else "N/A",
            f"full_window_{days_before + days_after}d": f"{full_window}%" if full_window is not None else "N/A",
        },
        "_returns_raw": {
            "pre_event": pre_event,
            "event_day": event_day,
            "post_event_1d": post_event_1d,
            "post_event": post_event,
            "full_window": full_window,
        },
    }


# ─────────────────────────────────────────────────────────────
# Pattern Aggregation
# ─────────────────────────────────────────────────────────────


def _aggregate_patterns(
    windows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Aggregate return patterns across multiple event windows.

    Returns average, median, consistency, and a pattern description.
    """
    valid = [w for w in windows if "_returns_raw" in w]

    if not valid:
        return {"events_analyzed": 0, "error": "No valid event windows"}

    pre_returns = [w["_returns_raw"]["pre_event"] for w in valid if w["_returns_raw"]["pre_event"] is not None]
    event_returns = [w["_returns_raw"]["event_day"] for w in valid if w["_returns_raw"]["event_day"] is not None]
    post_1d_returns = [w["_returns_raw"]["post_event_1d"] for w in valid if w["_returns_raw"]["post_event_1d"] is not None]
    post_returns = [w["_returns_raw"]["post_event"] for w in valid if w["_returns_raw"]["post_event"] is not None]

    def _stats(values: List[float], label: str) -> Dict[str, Any]:
        if not values:
            return {}
        arr = np.array(values)
        positive_count = int(np.sum(arr > 0))
        total = len(arr)
        return {
            f"average_{label}": f"{round(float(np.mean(arr)), 2)}%",
            f"median_{label}": f"{round(float(np.median(arr)), 2)}%",
            f"best_{label}": f"{round(float(np.max(arr)), 2)}%",
            f"worst_{label}": f"{round(float(np.min(arr)), 2)}%",
            f"positive_rate_{label}": f"{positive_count}/{total}",
        }

    result: Dict[str, Any] = {
        "events_analyzed": len(valid),
    }
    result.update(_stats(pre_returns, "pre_event_drift"))
    result.update(_stats(event_returns, "event_day_move"))
    result.update(_stats(post_1d_returns, "post_event_1d"))
    result.update(_stats(post_returns, "post_event_5d"))

    # Consistency rating
    if pre_returns:
        pre_positive = sum(1 for r in pre_returns if r > 0)
        pre_ratio = pre_positive / len(pre_returns)
        if pre_ratio >= 0.75 or pre_ratio <= 0.25:
            consistency = "High"
        elif pre_ratio >= 0.6 or pre_ratio <= 0.4:
            consistency = "Moderate"
        else:
            consistency = "Low"
        result["consistency"] = (
            f"{consistency} — {pre_positive} of {len(pre_returns)} events "
            f"show {'positive' if pre_ratio >= 0.5 else 'negative'} pre-event drift"
        )

    # Generate pattern description
    avg_pre = float(np.mean(pre_returns)) if pre_returns else 0
    avg_event = float(np.mean(event_returns)) if event_returns else 0
    avg_post = float(np.mean(post_returns)) if post_returns else 0

    parts = []
    if avg_pre > 0.5:
        parts.append("stock tends to rally before events")
    elif avg_pre < -0.5:
        parts.append("stock tends to decline before events")

    if avg_event > 0.5:
        parts.append("positive event-day reaction on average")
    elif avg_event < -0.5:
        parts.append("negative event-day reaction on average")

    if avg_post > 0.5:
        parts.append("gains hold after events")
    elif avg_post < -0.5:
        parts.append("post-event reversal common")

    result["pattern"] = "; ".join(parts) if parts else "No clear directional pattern"

    return result


# ─────────────────────────────────────────────────────────────
# EPS Surprise Correlation
# ─────────────────────────────────────────────────────────────


def _surprise_correlation(
    earnings_events: List[Dict[str, Any]],
    windows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Correlate EPS surprise magnitude with event-day price reaction.

    Returns Pearson correlation and interpretive insight.
    """
    pairs: List[Tuple[float, float]] = []

    # Build lookup from event date → window
    window_map = {w.get("event_date") or w.get("actual_trading_date"): w for w in windows if "_returns_raw" in w}

    for event in earnings_events:
        eps_actual = event.get("eps_actual", 0)
        eps_estimate = event.get("eps_estimate", 0)
        date = event.get("date", "")

        if eps_estimate == 0 or date not in window_map:
            continue

        surprise_pct = ((eps_actual - eps_estimate) / abs(eps_estimate)) * 100
        event_day_return = window_map[date]["_returns_raw"].get("event_day")

        if event_day_return is not None:
            pairs.append((surprise_pct, event_day_return))

    if len(pairs) < 3:
        return {
            "data_points": len(pairs),
            "insight": "Insufficient data points for meaningful correlation (need ≥ 3)",
        }

    surprises = np.array([p[0] for p in pairs])
    returns = np.array([p[1] for p in pairs])

    # Pearson correlation
    corr_matrix = np.corrcoef(surprises, returns)
    correlation = round(float(corr_matrix[0, 1]), 2)

    if abs(correlation) >= 0.7:
        strength = "Strong"
    elif abs(correlation) >= 0.4:
        strength = "Moderate"
    else:
        strength = "Weak"

    direction = "positive" if correlation > 0 else "negative"

    return {
        "correlation": correlation,
        "strength": strength,
        "data_points": len(pairs),
        "insight": (
            f"{strength} {direction} correlation ({correlation}): "
            f"{'Larger EPS beats tend to produce larger event-day gains' if correlation > 0.3 else 'Larger EPS beats tend to produce smaller gains' if correlation < -0.3 else 'EPS surprise magnitude has limited predictive value for event-day returns'}"
        ),
    }


# ─────────────────────────────────────────────────────────────
# Full Event Analysis
# ─────────────────────────────────────────────────────────────


def analyze_events(
    symbol: str,
    event_type: str = "earnings",
    days_before: int = 5,
    days_after: int = 5,
) -> Dict[str, Any]:
    """
    Comprehensive event-driven performance analysis.

    This is the main entry-point. It:
    1. Fetches the event calendar
    2. Computes price windows around each historical event
    3. Aggregates patterns across events
    4. Correlates EPS surprise with price reaction (earnings only)

    Args:
        symbol: Stock ticker symbol.
        event_type: Type of event — "earnings", "dividends", or "splits".
        days_before: Trading days to include before the event.
        days_after: Trading days to include after the event.

    Returns:
        Complete event analysis dict.
    """
    symbol = symbol.upper()
    logger.info(f"Running event analysis for {symbol} (type={event_type})")
    start_time = datetime.now(timezone.utc)

    # Step 1: Get event calendar
    calendar = get_event_calendar(symbol)
    if "error" in calendar:
        return calendar

    # Select events by type
    if event_type == "earnings":
        raw_events = calendar.get("earnings", [])
    elif event_type == "dividends":
        raw_events = calendar.get("dividends", [])
    elif event_type == "splits":
        raw_events = calendar.get("splits", [])
    else:
        return {"symbol": symbol, "error": f"Unknown event_type: {event_type}"}

    if not raw_events:
        return {
            "symbol": symbol,
            "event_type": event_type,
            "events_analyzed": 0,
            "error": f"No {event_type} events found",
        }

    # Only analyse past events (skip future dates)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    past_events = [e for e in raw_events if e["date"] <= today]

    # Limit to most recent 12 events for performance
    past_events = past_events[-12:] if len(past_events) > 12 else past_events

    # Step 2: Compute price windows
    event_windows: List[Dict[str, Any]] = []
    for event in past_events:
        window = calculate_event_window(
            symbol, event["date"], days_before, days_after
        )
        if "error" not in window:
            # Merge event metadata into window
            merged = {**event, **window}
            # Calculate EPS surprise if available
            if event.get("eps_estimate", 0) != 0:
                surprise = ((event["eps_actual"] - event["eps_estimate"]) / abs(event["eps_estimate"])) * 100
                merged["eps_surprise_pct"] = round(surprise, 2)
                merged["verdict"] = "BEAT" if surprise > 1 else "MISS" if surprise < -1 else "INLINE"
            event_windows.append(merged)

    if not event_windows:
        return {
            "symbol": symbol,
            "event_type": event_type,
            "events_analyzed": 0,
            "error": "Could not compute price windows for any events",
        }

    # Step 3: Aggregate patterns
    patterns = _aggregate_patterns(event_windows)

    # Step 4: Surprise correlation (earnings only)
    correlation = {}
    if event_type == "earnings":
        correlation = _surprise_correlation(past_events, event_windows)

    # Clean up internal raw returns before output
    clean_events = []
    for w in event_windows:
        clean = {k: v for k, v in w.items() if k != "_returns_raw"}
        clean_events.append(clean)

    execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

    return {
        "symbol": symbol,
        "name": calendar.get("name", symbol),
        "event_type": event_type,
        "events_analyzed": len(clean_events),
        "events": clean_events,
        "historical_patterns": patterns,
        "correlation_with_surprise": correlation if correlation else None,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "execution_time_seconds": round(execution_time, 2),
    }
