"""
ML-Based Price Forecasting Tool (Phase 2.4).

Uses scikit-learn GradientBoosting for time-series forecasting with
engineered features (lag returns, moving averages, RSI, volatility).

Usage::

    from src.tools.ml_forecast import get_price_targets
    result = get_price_targets("AAPL")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.data import get_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Feature Engineering ──────────────────────────────────────


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build ML features from OHLCV data."""
    close = df["Close"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series(0, index=df.index)

    features = pd.DataFrame(index=df.index)

    # Lag returns
    for lag in [1, 5, 10, 20]:
        features[f"return_{lag}d"] = close.pct_change(lag)

    # Moving averages (relative to price)
    for period in [10, 20, 50]:
        sma = close.rolling(period).mean()
        features[f"sma_{period}_ratio"] = close / sma - 1

    # RSI (14-day)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    features["rsi_14"] = 100 - 100 / (1 + rs)

    # Volatility
    features["volatility_20d"] = close.pct_change().rolling(20).std()

    # Volume momentum
    if volume.sum() > 0:
        features["volume_ratio"] = volume / volume.rolling(20).mean()

    # Calendar features
    features["day_of_week"] = df.index.dayofweek
    features["month"] = df.index.month

    # Target: next-day return
    features["target"] = close.pct_change().shift(-1)

    return features.dropna()


# ── Forecasting ──────────────────────────────────────────────


def forecast_price(
    symbol: str,
    horizon_days: int = 90,
) -> Dict[str, Any]:
    """
    Forecast future prices using gradient boosting.

    Args:
        symbol: Stock ticker.
        horizon_days: Number of days to forecast.

    Returns:
        Dict with forecasted prices, confidence bands, trend, model metrics.
    """
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import r2_score, mean_absolute_error

        provider = get_provider()
        hist = provider.get_history(symbol, period="2y", interval="1d")

        if hist is None or len(hist) < 100:
            return {"symbol": symbol, "error": "Insufficient historical data (need 2 years)"}

        current_price = float(hist["Close"].iloc[-1])

        # Build features
        feat_df = _build_features(hist)
        if len(feat_df) < 60:
            return {"symbol": symbol, "error": "Insufficient data after feature engineering"}

        feature_cols = [c for c in feat_df.columns if c != "target"]
        X = feat_df[feature_cols].values
        y = feat_df["target"].values

        # Train/test split (last 20% for validation)
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        # Train model
        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
        )
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)

        # Estimate prediction std from residuals
        residuals = y_test - y_pred
        pred_std = float(np.std(residuals))

        # Forward forecast
        last_features = feat_df[feature_cols].iloc[-1:].values.copy()
        forecasted_returns = []
        price = current_price

        for day in range(horizon_days):
            pred_return = float(model.predict(last_features)[0])
            forecasted_returns.append(pred_return)
            price *= (1 + pred_return)

            # Update features (simplified — shift lags)
            new_feat = last_features.copy()
            # Shift return features
            for i, lag in enumerate([1, 5, 10, 20]):
                if i < new_feat.shape[1]:
                    new_feat[0, i] = pred_return if day < lag else forecasted_returns[max(0, day - lag)]
            last_features = new_feat

        # Build price paths
        prices = [current_price]
        p = current_price
        for r in forecasted_returns:
            p *= (1 + r)
            prices.append(round(p, 2))

        # Confidence bands (widening over time)
        upper = []
        lower = []
        p_up = current_price
        p_down = current_price
        for day, r in enumerate(forecasted_returns, 1):
            width = pred_std * np.sqrt(day) * 1.96  # 95% CI
            p_up *= (1 + r + width)
            p_down *= (1 + r - width)
            upper.append(round(p_up, 2))
            lower.append(round(max(0, p_down), 2))

        # Extract targets at key horizons
        targets = {}
        for h in [30, 60, 90]:
            if h <= horizon_days:
                targets[f"{h}d"] = {
                    "price": prices[h] if h < len(prices) else prices[-1],
                    "upper": upper[h - 1] if h <= len(upper) else upper[-1],
                    "lower": lower[h - 1] if h <= len(lower) else lower[-1],
                    "return_pct": round((prices[min(h, len(prices) - 1)] / current_price - 1) * 100, 2),
                }

        # Trend direction
        final_price = prices[-1]
        if final_price > current_price * 1.05:
            trend = "bullish"
        elif final_price < current_price * 0.95:
            trend = "bearish"
        else:
            trend = "neutral"

        return {
            "symbol": symbol,
            "current_price": current_price,
            "horizon_days": horizon_days,
            "targets": targets,
            "trend": trend,
            "model_metrics": {
                "r2_score": round(r2, 4),
                "mae": round(mae, 6),
                "prediction_std": round(pred_std, 6),
            },
            "forecasted_prices": prices[::5],  # Every 5 days to keep compact
            "confidence_upper": upper[::5],
            "confidence_lower": lower[::5],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except ImportError:
        return {"symbol": symbol, "error": "scikit-learn not installed — pip install scikit-learn"}
    except Exception as e:
        logger.error(f"Forecast failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def get_price_targets(symbol: str) -> Dict[str, Any]:
    """
    Get structured price targets for 30/60/90 days.

    Returns targets with confidence levels and comparison to current price.
    """
    result = forecast_price(symbol, horizon_days=90)
    if "error" in result:
        return result

    targets = result.get("targets", {})
    current = result.get("current_price", 0)

    formatted = {
        "symbol": symbol,
        "current_price": current,
        "trend": result.get("trend"),
        "model_quality": result.get("model_metrics", {}),
    }

    for horizon, data in targets.items():
        formatted[horizon] = {
            "target": data["price"],
            "upside_pct": data["return_pct"],
            "range": f"{data['lower']:.2f} - {data['upper']:.2f}",
            "confidence": "95%",
        }

    formatted["analyzed_at"] = result.get("analyzed_at")
    return formatted


def decompose_trend(symbol: str) -> Dict[str, Any]:
    """
    Decompose price into trend, seasonality, and noise.

    Uses moving average decomposition (no statsmodels required).
    """
    try:
        provider = get_provider()
        hist = provider.get_history(symbol, period="2y", interval="1d")

        if hist is None or len(hist) < 60:
            return {"symbol": symbol, "error": "Insufficient data"}

        close = hist["Close"]

        # Trend: 50-day SMA
        trend = close.rolling(50).mean()

        # Detrended
        detrended = close - trend

        # Seasonal pattern: average by month
        monthly_avg = close.groupby(close.index.month).mean()
        overall_avg = close.mean()
        seasonal_factors = {
            int(m): round((v / overall_avg - 1) * 100, 2)
            for m, v in monthly_avg.items()
        }

        # Noise level (residual std as % of price)
        residual = detrended.dropna()
        noise_level = float(residual.std() / close.mean() * 100)

        # Trend direction
        if len(trend.dropna()) >= 20:
            recent_trend = trend.dropna().iloc[-1]
            past_trend = trend.dropna().iloc[-20]
            if recent_trend > past_trend * 1.02:
                trend_direction = "uptrend"
            elif recent_trend < past_trend * 0.98:
                trend_direction = "downtrend"
            else:
                trend_direction = "sideways"
        else:
            trend_direction = "unknown"

        return {
            "symbol": symbol,
            "trend_direction": trend_direction,
            "seasonal_factors": seasonal_factors,
            "noise_level_pct": round(noise_level, 2),
            "interpretation": (
                f"The stock is in a {trend_direction}. "
                f"Noise level is {noise_level:.1f}% of average price."
            ),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Trend decomposition failed for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}
