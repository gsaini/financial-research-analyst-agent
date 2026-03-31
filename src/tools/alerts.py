"""
Real-Time Alerts & Notification System (Phase 4).

Provides price alerts, technical signal alerts, and a WebSocket-compatible
alert manager. Alerts are evaluated on-demand or via polling.

Usage::

    from src.tools.alerts import AlertManager, check_alerts
    manager = AlertManager()
    manager.add_alert("AAPL", "price_above", threshold=200)
    triggered = manager.evaluate_all()
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AlertType(str, Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE = "percent_change"
    VOLUME_SPIKE = "volume_spike"
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    MA_CROSSOVER = "ma_crossover"
    NEW_HIGH_52W = "new_52w_high"
    NEW_LOW_52W = "new_52w_low"


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
    current_value: Optional[float] = None
    user_id: str = "default"

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.symbol}_{self.alert_type}_{int(time.time())}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class AlertManager:
    """
    In-memory alert manager.

    Supports adding, removing, and evaluating alerts against live data.
    """

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}

    def add_alert(
        self,
        symbol: str,
        alert_type: str,
        threshold: float = 0,
        message: str = "",
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """Add a new alert. Returns alert details."""
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
            message=message or f"{at.value} alert for {symbol} at {threshold}",
            user_id=user_id,
        )
        self.alerts[alert.id] = alert
        logger.info(f"Alert created: {alert.id}")
        return {"status": "created", "alert": asdict(alert)}

    def remove_alert(self, alert_id: str) -> Dict[str, Any]:
        """Remove an alert by ID."""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            return {"status": "removed", "alert_id": alert_id}
        return {"status": "not_found", "alert_id": alert_id}

    def list_alerts(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all alerts, optionally filtered by user."""
        alerts = self.alerts.values()
        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id]
        return [asdict(a) for a in alerts]

    def evaluate_all(self) -> List[Dict[str, Any]]:
        """
        Evaluate all pending alerts against current market data.

        Returns list of newly triggered alerts.
        """
        triggered = []

        # Group by symbol to minimize API calls
        symbols = set(a.symbol for a in self.alerts.values() if not a.triggered)
        if not symbols:
            return []

        market_data = {}
        try:
            from src.data import get_provider
            provider = get_provider()
            for sym in symbols:
                info = provider.get_info(sym)
                market_data[sym] = {
                    "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                    "prev_close": info.get("previousClose", 0),
                    "volume": info.get("volume", 0),
                    "avg_volume": info.get("averageVolume", 0),
                    "high_52w": info.get("fiftyTwoWeekHigh", 0),
                    "low_52w": info.get("fiftyTwoWeekLow", 0),
                }
        except Exception as e:
            logger.error(f"Alert evaluation data fetch failed: {e}")
            return []

        for alert_id, alert in self.alerts.items():
            if alert.triggered:
                continue

            data = market_data.get(alert.symbol)
            if not data:
                continue

            is_triggered = self._check_condition(alert, data)
            if is_triggered:
                alert.triggered = True
                alert.triggered_at = datetime.now(timezone.utc).isoformat()
                alert.current_value = data.get("price", 0)
                triggered.append(asdict(alert))
                logger.info(f"Alert triggered: {alert.id}")

        return triggered

    def _check_condition(self, alert: Alert, data: Dict) -> bool:
        """Check if alert condition is met."""
        price = data.get("price", 0)
        prev_close = data.get("prev_close", 0)

        if alert.alert_type == AlertType.PRICE_ABOVE:
            return price >= alert.threshold

        elif alert.alert_type == AlertType.PRICE_BELOW:
            return price <= alert.threshold

        elif alert.alert_type == AlertType.PERCENT_CHANGE:
            if prev_close > 0:
                pct = abs((price - prev_close) / prev_close * 100)
                return pct >= alert.threshold
            return False

        elif alert.alert_type == AlertType.VOLUME_SPIKE:
            vol = data.get("volume", 0)
            avg_vol = data.get("avg_volume", 1)
            return (vol / avg_vol) >= alert.threshold if avg_vol > 0 else False

        elif alert.alert_type == AlertType.NEW_HIGH_52W:
            return price >= data.get("high_52w", float("inf"))

        elif alert.alert_type == AlertType.NEW_LOW_52W:
            return price <= data.get("low_52w", 0) and data.get("low_52w", 0) > 0

        return False


# Singleton instance
_alert_manager = AlertManager()


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    return _alert_manager


def check_alerts() -> List[Dict[str, Any]]:
    """Convenience: evaluate all alerts and return triggered ones."""
    return _alert_manager.evaluate_all()


def add_alert(
    symbol: str, alert_type: str, threshold: float = 0, message: str = ""
) -> Dict[str, Any]:
    """Convenience: add a new alert."""
    return _alert_manager.add_alert(symbol, alert_type, threshold, message)


def list_alerts() -> List[Dict[str, Any]]:
    """Convenience: list all alerts."""
    return _alert_manager.list_alerts()
