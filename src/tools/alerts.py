"""
Alert & Notification System (Feature 18).

Full alert lifecycle: creation, evaluation against live data, triggering,
and history tracking. Supports price, technical, news/sentiment, calendar,
and risk alert types.

Usage::

    from src.tools.alerts import add_alert, check_alerts, list_alerts
    add_alert("AAPL", "price_above", threshold=200)
    add_alert("NVDA", "rsi_oversold", threshold=30)
    add_alert("MSFT", "earnings_soon", threshold=5)  # 5 days before
    triggered = check_alerts()
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Alert Types ──────────────────────────────────────────────


class AlertType(str, Enum):
    # Price alerts
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE = "percent_change"

    # Volume alerts
    VOLUME_SPIKE = "volume_spike"

    # Technical alerts
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    MACD_BULLISH = "macd_bullish_crossover"
    MACD_BEARISH = "macd_bearish_crossover"
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"

    # 52-week alerts
    NEW_HIGH_52W = "new_52w_high"
    NEW_LOW_52W = "new_52w_low"

    # News/sentiment alerts
    NEWS_VOLUME_SPIKE = "news_volume_spike"
    SENTIMENT_CHANGE = "sentiment_change"

    # Calendar alerts
    EARNINGS_SOON = "earnings_soon"
    EX_DIVIDEND_SOON = "ex_dividend_soon"

    # Short interest alerts
    SHORT_INTEREST_SPIKE = "short_interest_spike"


@dataclass
class Alert:
    id: str
    symbol: str
    alert_type: AlertType
    threshold: float = 0
    message: str = ""
    created_at: str = ""
    triggered: bool = False
    triggered_at: Optional[str] = None
    trigger_message: str = ""
    current_value: Optional[float] = None
    user_id: str = "default"
    repeat: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.symbol}_{self.alert_type.value}_{int(time.time() * 1000)}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.message:
            self.message = f"{self.alert_type.value} alert for {self.symbol}"


# ── Alert Manager ────────────────────────────────────────────


class AlertManager:
    """
    In-memory alert manager with evaluation for all alert types.

    Supports price, technical, news/sentiment, calendar, and
    short interest alerts.
    """

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.history: List[Dict[str, Any]] = []  # Triggered alert log

    def add_alert(
        self,
        symbol: str,
        alert_type: str,
        threshold: float = 0,
        message: str = "",
        user_id: str = "default",
        repeat: bool = False,
    ) -> Dict[str, Any]:
        """Add a new alert."""
        try:
            at = AlertType(alert_type)
        except ValueError:
            return {
                "error": f"Invalid alert type: {alert_type}. "
                         f"Valid: {[t.value for t in AlertType]}",
            }

        alert = Alert(
            id="",
            symbol=symbol.upper(),
            alert_type=at,
            threshold=threshold,
            message=message,
            user_id=user_id,
            repeat=repeat,
        )
        self.alerts[alert.id] = alert
        logger.info(f"Alert created: {alert.id} ({at.value} for {symbol})")
        return {"status": "created", "alert": asdict(alert)}

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get a single alert by ID."""
        alert = self.alerts.get(alert_id)
        return asdict(alert) if alert else None

    def update_alert(self, alert_id: str, **kwargs) -> Dict[str, Any]:
        """Update alert fields."""
        alert = self.alerts.get(alert_id)
        if not alert:
            return {"status": "not_found", "alert_id": alert_id}

        for key, value in kwargs.items():
            if hasattr(alert, key) and key not in ("id", "created_at"):
                if key == "alert_type":
                    try:
                        value = AlertType(value)
                    except ValueError:
                        continue
                setattr(alert, key, value)

        return {"status": "updated", "alert": asdict(alert)}

    def remove_alert(self, alert_id: str) -> Dict[str, Any]:
        """Remove an alert by ID."""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            return {"status": "removed", "alert_id": alert_id}
        return {"status": "not_found", "alert_id": alert_id}

    def list_alerts(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List alerts, optionally filtered by user and status."""
        alerts = list(self.alerts.values())
        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id]
        if status == "active":
            alerts = [a for a in alerts if not a.triggered]
        elif status == "triggered":
            alerts = [a for a in alerts if a.triggered]
        return [asdict(a) for a in alerts]

    def get_triggered_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently triggered alerts."""
        return self.history[-limit:]

    def evaluate_all(self) -> List[Dict[str, Any]]:
        """
        Evaluate all pending alerts against current data.

        Returns list of newly triggered alerts.
        """
        triggered = []
        pending = [a for a in self.alerts.values() if not a.triggered]
        if not pending:
            return []

        # Group by symbol
        symbols = set(a.symbol for a in pending)

        # Fetch market data for all symbols at once
        market_data = self._fetch_market_data(symbols)

        for alert in pending:
            data = market_data.get(alert.symbol)
            if not data:
                continue

            result = self._evaluate_alert(alert, data)
            if result["triggered"]:
                alert.triggered = True
                alert.triggered_at = datetime.now(timezone.utc).isoformat()
                alert.current_value = result.get("value")
                alert.trigger_message = result.get("message", "")

                entry = asdict(alert)
                triggered.append(entry)
                self.history.append(entry)
                logger.info(f"Alert triggered: {alert.id} — {result.get('message', '')}")

                # Reset if repeat
                if alert.repeat:
                    alert.triggered = False
                    alert.triggered_at = None

        return triggered

    def _fetch_market_data(self, symbols: set) -> Dict[str, Dict]:
        """Fetch all data needed for alert evaluation."""
        market_data = {}
        try:
            from src.data import get_provider
            provider = get_provider()

            for sym in symbols:
                info = provider.get_info(sym)
                hist = provider.get_history(sym, period="3mo", interval="1d")

                data: Dict[str, Any] = {
                    "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                    "prev_close": info.get("previousClose", 0),
                    "volume": info.get("volume", 0),
                    "avg_volume": info.get("averageVolume", 1),
                    "high_52w": info.get("fiftyTwoWeekHigh", 0),
                    "low_52w": info.get("fiftyTwoWeekLow", 0),
                    "short_pct": (info.get("shortPercentOfFloat", 0) or 0),
                }

                # Technical indicators from history
                if hist is not None and not hist.empty and "Close" in hist.columns:
                    closes = hist["Close"].dropna().values
                    data["closes"] = closes
                    if len(closes) >= 14:
                        data["rsi"] = self._calc_rsi(closes)
                    if len(closes) >= 26:
                        data["macd"] = self._calc_macd(closes)
                    if len(closes) >= 200:
                        data["sma_50"] = float(closes[-50:].mean())
                        data["sma_200"] = float(closes[-200:].mean())
                        # Check for recent cross
                        prev_sma_50 = float(closes[-51:-1].mean())
                        prev_sma_200 = float(closes[-201:-1].mean())
                        data["golden_cross"] = data["sma_50"] > data["sma_200"] and prev_sma_50 <= prev_sma_200
                        data["death_cross"] = data["sma_50"] < data["sma_200"] and prev_sma_50 >= prev_sma_200

                # Calendar data
                try:
                    calendar = info.get("earningsDate") or info.get("earningsTimestamp")
                    if calendar:
                        if isinstance(calendar, (list, tuple)) and len(calendar) > 0:
                            # yfinance returns list of timestamps
                            next_earnings = datetime.fromtimestamp(calendar[0], tz=timezone.utc)
                        elif isinstance(calendar, (int, float)):
                            next_earnings = datetime.fromtimestamp(calendar, tz=timezone.utc)
                        else:
                            next_earnings = None

                        if next_earnings:
                            data["days_to_earnings"] = (next_earnings - datetime.now(timezone.utc)).days
                except Exception:
                    pass

                try:
                    ex_date = info.get("exDividendDate")
                    if ex_date:
                        if isinstance(ex_date, (int, float)):
                            ex_dt = datetime.fromtimestamp(ex_date, tz=timezone.utc)
                            data["days_to_ex_dividend"] = (ex_dt - datetime.now(timezone.utc)).days
                except Exception:
                    pass

                market_data[sym] = data

        except Exception as e:
            logger.error(f"Alert data fetch failed: {e}")

        return market_data

    def _evaluate_alert(self, alert: Alert, data: Dict) -> Dict[str, Any]:
        """Evaluate a single alert against market data."""
        price = data.get("price", 0)
        threshold = alert.threshold

        # ── Price alerts ──
        if alert.alert_type == AlertType.PRICE_ABOVE:
            if price >= threshold:
                return {"triggered": True, "value": price,
                        "message": f"{alert.symbol} crossed above ${threshold:.2f} (now ${price:.2f})"}

        elif alert.alert_type == AlertType.PRICE_BELOW:
            if price <= threshold:
                return {"triggered": True, "value": price,
                        "message": f"{alert.symbol} dropped below ${threshold:.2f} (now ${price:.2f})"}

        elif alert.alert_type == AlertType.PERCENT_CHANGE:
            prev = data.get("prev_close", 0)
            if prev > 0:
                pct = abs((price - prev) / prev * 100)
                if pct >= threshold:
                    direction = "up" if price > prev else "down"
                    return {"triggered": True, "value": pct,
                            "message": f"{alert.symbol} moved {direction} {pct:.1f}% today"}

        # ── Volume alerts ──
        elif alert.alert_type == AlertType.VOLUME_SPIKE:
            vol = data.get("volume", 0)
            avg_vol = data.get("avg_volume", 1)
            ratio = vol / avg_vol if avg_vol > 0 else 0
            if ratio >= threshold:
                return {"triggered": True, "value": ratio,
                        "message": f"{alert.symbol} volume is {ratio:.1f}x average ({vol:,} vs avg {avg_vol:,})"}

        # ── Technical alerts ──
        elif alert.alert_type == AlertType.RSI_OVERSOLD:
            rsi = data.get("rsi")
            if rsi is not None and rsi <= threshold:
                return {"triggered": True, "value": rsi,
                        "message": f"{alert.symbol} RSI dropped to {rsi:.1f} (oversold threshold: {threshold})"}

        elif alert.alert_type == AlertType.RSI_OVERBOUGHT:
            rsi = data.get("rsi")
            if rsi is not None and rsi >= threshold:
                return {"triggered": True, "value": rsi,
                        "message": f"{alert.symbol} RSI rose to {rsi:.1f} (overbought threshold: {threshold})"}

        elif alert.alert_type == AlertType.MACD_BULLISH:
            macd = data.get("macd", {})
            if macd.get("crossover") == "bullish":
                return {"triggered": True, "value": macd.get("histogram", 0),
                        "message": f"{alert.symbol} MACD bullish crossover detected"}

        elif alert.alert_type == AlertType.MACD_BEARISH:
            macd = data.get("macd", {})
            if macd.get("crossover") == "bearish":
                return {"triggered": True, "value": macd.get("histogram", 0),
                        "message": f"{alert.symbol} MACD bearish crossover detected"}

        elif alert.alert_type == AlertType.GOLDEN_CROSS:
            if data.get("golden_cross"):
                return {"triggered": True, "value": data.get("sma_50", 0),
                        "message": f"{alert.symbol} Golden Cross: 50-SMA crossed above 200-SMA"}

        elif alert.alert_type == AlertType.DEATH_CROSS:
            if data.get("death_cross"):
                return {"triggered": True, "value": data.get("sma_50", 0),
                        "message": f"{alert.symbol} Death Cross: 50-SMA crossed below 200-SMA"}

        # ── 52-week alerts ──
        elif alert.alert_type == AlertType.NEW_HIGH_52W:
            if price >= data.get("high_52w", float("inf")):
                return {"triggered": True, "value": price,
                        "message": f"{alert.symbol} hit new 52-week high at ${price:.2f}"}

        elif alert.alert_type == AlertType.NEW_LOW_52W:
            low = data.get("low_52w", 0)
            if low > 0 and price <= low:
                return {"triggered": True, "value": price,
                        "message": f"{alert.symbol} hit new 52-week low at ${price:.2f}"}

        # ── Calendar alerts ──
        elif alert.alert_type == AlertType.EARNINGS_SOON:
            days = data.get("days_to_earnings")
            if days is not None and 0 <= days <= threshold:
                return {"triggered": True, "value": days,
                        "message": f"{alert.symbol} earnings in {days} day(s)"}

        elif alert.alert_type == AlertType.EX_DIVIDEND_SOON:
            days = data.get("days_to_ex_dividend")
            if days is not None and 0 <= days <= threshold:
                return {"triggered": True, "value": days,
                        "message": f"{alert.symbol} ex-dividend date in {days} day(s)"}

        # ── Short interest alerts ──
        elif alert.alert_type == AlertType.SHORT_INTEREST_SPIKE:
            short_pct = data.get("short_pct", 0)
            if isinstance(short_pct, (int, float)) and short_pct > 0:
                if short_pct < 1:
                    short_pct *= 100
                if short_pct >= threshold:
                    return {"triggered": True, "value": short_pct,
                            "message": f"{alert.symbol} short interest at {short_pct:.1f}% of float (threshold: {threshold}%)"}

        return {"triggered": False}

    @staticmethod
    def _calc_rsi(closes, period: int = 14) -> float:
        """Calculate RSI from close prices."""
        import numpy as np
        deltas = np.diff(closes[-period - 1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100 - 100 / (1 + rs))

    @staticmethod
    def _calc_macd(closes) -> Dict[str, Any]:
        """Calculate MACD histogram and crossover."""
        import numpy as np

        def ema(data, period):
            alpha = 2 / (period + 1)
            result = [data[0]]
            for d in data[1:]:
                result.append(alpha * d + (1 - alpha) * result[-1])
            return np.array(result)

        fast = ema(closes, 12)
        slow = ema(closes, 26)
        macd_line = fast - slow
        signal = ema(macd_line, 9)
        histogram = macd_line - signal

        crossover = "none"
        if len(histogram) >= 2:
            if histogram[-1] > 0 and histogram[-2] <= 0:
                crossover = "bullish"
            elif histogram[-1] < 0 and histogram[-2] >= 0:
                crossover = "bearish"

        return {
            "histogram": round(float(histogram[-1]), 4),
            "crossover": crossover,
        }


# ── Singleton + Convenience Functions ────────────────────────

_alert_manager = AlertManager()


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    return _alert_manager


def add_alert(
    symbol: str,
    alert_type: str,
    threshold: float = 0,
    message: str = "",
    user_id: str = "default",
    repeat: bool = False,
) -> Dict[str, Any]:
    """Add a new alert."""
    return _alert_manager.add_alert(symbol, alert_type, threshold, message, user_id, repeat)


def remove_alert(alert_id: str) -> Dict[str, Any]:
    """Remove an alert."""
    return _alert_manager.remove_alert(alert_id)


def get_alert(alert_id: str) -> Optional[Dict[str, Any]]:
    """Get a single alert."""
    return _alert_manager.get_alert(alert_id)


def update_alert(alert_id: str, **kwargs) -> Dict[str, Any]:
    """Update an alert."""
    return _alert_manager.update_alert(alert_id, **kwargs)


def check_alerts() -> List[Dict[str, Any]]:
    """Evaluate all alerts and return triggered ones."""
    return _alert_manager.evaluate_all()


def list_alerts(
    user_id: Optional[str] = None, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List alerts with optional filters."""
    return _alert_manager.list_alerts(user_id, status)


def get_triggered_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recently triggered alerts."""
    return _alert_manager.get_triggered_history(limit)


def get_available_alert_types() -> List[Dict[str, str]]:
    """List all available alert types with descriptions."""
    descriptions = {
        "price_above": "Triggers when price crosses above threshold",
        "price_below": "Triggers when price drops below threshold",
        "percent_change": "Triggers when daily % change exceeds threshold",
        "volume_spike": "Triggers when volume is N-x above average",
        "rsi_oversold": "Triggers when RSI drops below threshold (e.g. 30)",
        "rsi_overbought": "Triggers when RSI rises above threshold (e.g. 70)",
        "macd_bullish_crossover": "Triggers on MACD bullish crossover",
        "macd_bearish_crossover": "Triggers on MACD bearish crossover",
        "golden_cross": "Triggers when 50-SMA crosses above 200-SMA",
        "death_cross": "Triggers when 50-SMA crosses below 200-SMA",
        "new_52w_high": "Triggers when stock hits new 52-week high",
        "new_52w_low": "Triggers when stock hits new 52-week low",
        "news_volume_spike": "Triggers on unusual news volume (future)",
        "sentiment_change": "Triggers on sentiment shift (future)",
        "earnings_soon": "Triggers N days before earnings date",
        "ex_dividend_soon": "Triggers N days before ex-dividend date",
        "short_interest_spike": "Triggers when short % of float exceeds threshold",
    }
    return [
        {"type": t.value, "description": descriptions.get(t.value, "")}
        for t in AlertType
    ]
