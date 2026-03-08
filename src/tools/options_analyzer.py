"""
Options Flow Analysis Tracker (Feature 13).

Analyzes the options market to understand sentiment and positioning.
Uses yfinance option chains to calculate put/call ratios, implied
volatility, unusual activity, and max pain.

Key capabilities:
- Put/Call ratio and total volume
- Implied Volatility (IV) percentile and Call vs Put skew
- Max Pain price (where most options expire worthless)
- Unusual activity detection (volume > 2x open interest)
- Combined options sentiment score

Usage
-----
>>> from src.tools.options_analyzer import analyze_options
>>> result = analyze_options("AAPL")
>>> print(result["options_sentiment"]["put_call_ratio"])
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from src.utils.logger import get_logger

logger = get_logger(__name__)


def analyze_options(symbol: str) -> Dict[str, Any]:
    """
    Comprehensive options flow analysis for a stock.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with sentiment, volatility, unusual activity, max pain,
        and an overall signal.
    """
    start_time = datetime.now(timezone.utc)
    sym = symbol.upper()

    try:
        ticker = yf.Ticker(sym)
        current_price = _get_current_price(ticker)

        if not current_price:
            raise ValueError(f"Could not fetch current price for {sym}")

        expirations = getattr(ticker, "options", [])
        if not expirations:
            raise ValueError(f"No options data available for {sym}")

        # Limit to first 4 expirations to keep API requests reasonable
        target_expirations = list(expirations)[:4]

        all_calls = []
        all_puts = []

        for exp in target_expirations:
            try:
                chain = ticker.option_chain(exp)
                calls = chain.calls.copy()
                puts = chain.puts.copy()

                # Add expiration date to rows
                calls["expiration"] = exp
                puts["expiration"] = exp

                all_calls.append(calls)
                all_puts.append(puts)
            except Exception as e:
                logger.warning(f"Failed to fetch option chain for {sym} at {exp}: {e}")

        if not all_calls or not all_puts:
            raise ValueError(f"Could not fetch any option chains for {sym}")

        calls_df = pd.concat(all_calls, ignore_index=True)
        puts_df = pd.concat(all_puts, ignore_index=True)

        sentiment = _calculate_sentiment(calls_df, puts_df)
        volatility = _calculate_volatility(calls_df, puts_df)
        unusual = _detect_unusual_activity(calls_df, puts_df, current_price)
        
        # Max pain is typically calculated for the nearest expiration
        nearest_calls = all_calls[0]
        nearest_puts = all_puts[0]
        max_pain = _calculate_max_pain(nearest_calls, nearest_puts, current_price)

        signal = _generate_options_signal(sentiment, volatility, unusual)

        exec_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        return {
            "symbol": sym,
            "current_price": current_price,
            "options_sentiment": sentiment,
            "implied_volatility": volatility,
            "max_pain": max_pain,
            "unusual_activity": unusual,
            "options_signal": signal,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "execution_time_seconds": round(exec_time, 3),
            "expirations_analyzed": target_expirations,
        }

    except Exception as exc:
        logger.error(f"Failed options analysis for {sym}: {exc}")
        return _empty_options_response(sym, str(exc))


def _get_current_price(ticker: yf.Ticker) -> Optional[float]:
    """Safely fetch current price."""
    try:
        info = ticker.info
        price = info.get("currentPrice", info.get("regularMarketPrice", info.get("previousClose")))
        if price:
            return float(price)
        
        # Fallback to history
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _calculate_sentiment(calls: pd.DataFrame, puts: pd.DataFrame) -> Dict[str, Any]:
    """Calculate Put/Call ratio and total volume."""
    call_vol = int(calls["volume"].sum()) if "volume" in calls and not calls.empty else 0
    put_vol = int(puts["volume"].sum()) if "volume" in puts and not puts.empty else 0
    
    total_vol = call_vol + put_vol
    
    # Avoid division by zero
    pc_ratio = round(put_vol / call_vol, 2) if call_vol > 0 else 0.0
    
    if pc_ratio == 0:
        assessment = "Indeterminate (no call volume)"
    elif pc_ratio < 0.7:
        assessment = "Bullish (heavy call buying)"
    elif pc_ratio > 1.2:
        assessment = "Bearish (heavy put buying/hedging)"
    else:
        assessment = "Neutral"

    return {
        "put_call_ratio": pc_ratio,
        "put_call_assessment": assessment,
        "call_volume": call_vol,
        "put_volume": put_vol,
        "total_options_volume": total_vol,
    }


def _calculate_volatility(calls: pd.DataFrame, puts: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate volume-weighted average implied volatility and skew.
    """
    def _vw_iv(df):
        if df.empty or "impliedVolatility" not in df or "volume" not in df:
            return 0.0
        # Filter valid rows
        valid = df[(df["impliedVolatility"] > 0) & (df["volume"] > 0)].copy()
        if valid.empty:
            return 0.0
        
        vol_sum = valid["volume"].sum()
        if vol_sum == 0:
            return 0.0
            
        weighted_iv = (valid["impliedVolatility"] * valid["volume"]).sum() / vol_sum
        return round(weighted_iv * 100, 2)  # Convert to percentage

    call_iv = _vw_iv(calls)
    put_iv = _vw_iv(puts)
    
    # Combined IV weighted by side volume
    call_vol = int(calls["volume"].sum()) if "volume" in calls and not calls.empty else 0
    put_vol = int(puts["volume"].sum()) if "volume" in puts and not puts.empty else 0
    
    if call_vol + put_vol > 0:
        combined_iv = round(((call_iv * call_vol) + (put_iv * put_vol)) / (call_vol + put_vol), 2)
    else:
        combined_iv = max(call_iv, put_iv)

    # Assess skew
    if put_iv > call_iv * 1.1:
        skew = "Put skew (higher demand for downside protection)"
    elif call_iv > put_iv * 1.1:
        skew = "Call skew (higher demand for upside speculation)"
    else:
        skew = "Balanced"

    # Assess absolute level (rough baseline, normally we'd compare to historical 30d IV)
    if combined_iv > 50:
        assessment = "Highly elevated - market expects massive move"
    elif combined_iv > 30:
        assessment = "Elevated - market expects significant move"
    else:
        assessment = "Normal/Low volatility expected"

    return {
        "current_iv": combined_iv,
        "iv_assessment": assessment,
        "iv_skew": {
            "put_iv": put_iv,
            "call_iv": call_iv,
            "skew_assessment": skew
        }
    }


def _detect_unusual_activity(
    calls: pd.DataFrame, puts: pd.DataFrame, current_price: float,
) -> List[Dict[str, Any]]:
    """
    Detect unusual activity: Volume >> Open Interest.
    """
    unusual = []
    
    def _scan(df, opt_type):
        if df.empty or "volume" not in df or "openInterest" not in df:
            return
            
        # Filter: meaningful volume, and volume > 2x open interest
        # Also require at least 500 contracts to filter noise
        candidates = df[
            (df["volume"] >= 500) & 
            (df["volume"] > df["openInterest"] * 2) &
            (df["impliedVolatility"] > 0)
        ].copy()
        
        for _, row in candidates.iterrows():
            strike = float(row.get("strike", 0))
            vol = int(row.get("volume", 0))
            oi = int(row.get("openInterest", 0))
            exp = str(row.get("expiration", ""))
            last_price = float(row.get("lastPrice", 0))
            
            # Premium paid estimate (assumes all volume was traded at last price)
            premium = round(vol * 100 * last_price, 2)
            
            # Implied move needed to reach strike
            if current_price > 0:
                implied_move = round(((strike - current_price) / current_price) * 100, 2)
            else:
                implied_move = 0.0

            # Directional assessment
            opt_type_upper = opt_type.upper()
            if opt_type == "call" and strike > current_price:
                assessment = f"Bullish: Buying OTM {exp} calls"
            elif opt_type == "put" and strike < current_price:
                assessment = f"Bearish/Hedge: Buying OTM {exp} puts"
            elif opt_type == "call" and strike < current_price:
                assessment = f"Bullish: Buying ITM {exp} calls"
            else:
                assessment = f"Bearish/Hedge: Buying ITM {exp} puts"
                
            unusual.append({
                "type": opt_type_upper,
                "strike": strike,
                "expiration": exp,
                "volume": vol,
                "open_interest": oi,
                "vol_oi_ratio": round(vol / max(oi, 1), 1),
                "est_premium_paid": premium,
                "implied_move_pct": implied_move,
                "assessment": assessment
            })

    _scan(calls, "call")
    _scan(puts, "put")

    # Sort largest premium first
    unusual.sort(key=lambda x: x["est_premium_paid"], reverse=True)
    
    # Return top 5
    return unusual[:5]


def _calculate_max_pain(
    calls: pd.DataFrame, puts: pd.DataFrame, current_price: float,
) -> Dict[str, Any]:
    """
    Calculate the max pain strike price for a single expiration.
    Max pain is the strike where options buyers lose the most money
    and options writers (sellers) keep the most premium.
    """
    if calls.empty or puts.empty or "openInterest" not in calls or "openInterest" not in puts:
        return {"price": 0.0, "distance_from_current": 0.0, "interpretation": "Insufficient data"}

    # Extract strike and OI
    call_oi = calls.groupby("strike")["openInterest"].sum().to_dict()
    put_oi = puts.groupby("strike")["openInterest"].sum().to_dict()

    all_strikes = sorted(set(list(call_oi.keys()) + list(put_oi.keys())))
    
    if not all_strikes:
        return {"price": 0.0, "distance_from_current": 0.0, "interpretation": "No open interest found"}

    losses_at_strike = {}

    # For every possible strike price (spot price at expiration)
    for test_price in all_strikes:
        loss = 0.0
        
        # Call buyers lose if strike is BELOW test_price
        for strike, oi in call_oi.items():
            if test_price > strike:
                loss += (test_price - strike) * oi * 100  # * 100 shares per contract
                
        # Put buyers lose if strike is ABOVE test_price
        for strike, oi in put_oi.items():
            if test_price < strike:
                loss += (strike - test_price) * oi * 100
                
        losses_at_strike[test_price] = loss

    # Find strike with MINIMUM loss for option writers
    max_pain_price = min(losses_at_strike, key=losses_at_strike.get)
    
    if current_price > 0:
        dist = round(((max_pain_price - current_price) / current_price) * 100, 2)
    else:
        dist = 0.0

    return {
        "price": float(max_pain_price),
        "distance_from_current_pct": dist,
        "interpretation": f"Options writers benefit most if price drifts to ${max_pain_price:.2f}"
    }


def _generate_options_signal(
    sentiment: Dict[str, Any], volatility: Dict[str, Any], unusual: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate an aggregate 0-100 options sentiment score.
    """
    score = 50  # Neutral
    
    # Evaluate P/C ratio
    pcr = sentiment.get("put_call_ratio", 1.0)
    if pcr < 0.6:
        score += 15  # Very bullish
    elif pcr < 0.8:
        score += 10
    elif pcr > 1.5:
        score -= 15  # Very bearish
    elif pcr > 1.1:
        score -= 10
        
    # Evaluate Skew
    skew = volatility.get("iv_skew", {}).get("skew_assessment", "Balanced")
    if "Put skew" in skew:
        score -= 5
    elif "Call skew" in skew:
        score += 5
        
    # Evaluate Unusual Activity
    call_sweeps = sum(1 for u in unusual if u["type"] == "CALL" and "Bullish" in u["assessment"])
    put_sweeps = sum(1 for u in unusual if u["type"] == "PUT" and "Bearish" in u["assessment"])
    
    if call_sweeps > put_sweeps:
        score += min((call_sweeps - put_sweeps) * 5, 20)
    elif put_sweeps > call_sweeps:
        score -= min((put_sweeps - call_sweeps) * 5, 20)
        
    # Clamp
    score = max(0, min(100, score))
    
    # Direction
    if score >= 70:
        direction = "Bullish"
        conf = "Moderate/High"
    elif score >= 55:
        direction = "Slightly Bullish"
        conf = "Low"
    elif score >= 45:
        direction = "Neutral"
        conf = "Low"
    elif score >= 30:
        direction = "Slightly Bearish"
        conf = "Low"
    else:
        direction = "Bearish"
        conf = "Moderate/High"
        
    return {
        "score": score,
        "direction": direction,
        "confidence": conf,
        "key_insight": f"{direction} signal based on Put/Call ratio of {pcr} and {len(unusual)} unusual trades."
    }


def _empty_options_response(symbol: str, error: str) -> Dict[str, Any]:
    """Return default empty response on error."""
    return {
        "symbol": symbol,
        "current_price": 0.0,
        "options_sentiment": _calculate_sentiment(pd.DataFrame(), pd.DataFrame()),
        "implied_volatility": _calculate_volatility(pd.DataFrame(), pd.DataFrame()),
        "max_pain": {"price": 0.0, "distance_from_current_pct": 0.0, "interpretation": error},
        "unusual_activity": [],
        "options_signal": {"score": 50, "direction": "Neutral", "confidence": "Low", "key_insight": "Data error"},
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "execution_time_seconds": 0.0,
        "expirations_analyzed": [],
        "error": error,
    }
