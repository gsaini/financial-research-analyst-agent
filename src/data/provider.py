"""
Market Data Provider — Abstract Interface & YFinance Implementation.

This module defines the ``MarketDataProvider`` protocol and ships a concrete
``YFinanceProvider`` implementation that wraps every ``yfinance.Ticker.*``
call used across the project's 13 tool modules.

Architecture
------------
                ┌──────────────────────────┐
                │   MarketDataProvider     │  ← abstract protocol
                │   (get_info, get_history │
                │    get_financials, etc.) │
                └────────────┬─────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
   ┌────────┴──────┐ ┌──────┴──────┐ ┌───────┴───────┐
   │ YFinanceProvider│ │ FMPProvider  │ │ TwelveDataProv│  ← future
   │  (yfinance)    │ │  ($19/mo)   │ │  ($29/mo)     │
   └───────────────┘ └─────────────┘ └───────────────┘

Every tool module should import ``get_provider()`` and call its methods
instead of using ``yf.Ticker()`` directly.

Swapping providers is then a one-line config change.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─── Abstract Interface ──────────────────────────────────────────────────────


class MarketDataProvider(ABC):
    """
    Abstract interface for market data providers.

    Every method accepts a ``symbol`` (str) as its first argument and
    returns a plain dict or a pandas object.  Tool modules should depend
    only on this interface — never on ``yfinance`` directly.

    Methods are grouped by the yfinance features they replace:

    Category 1 — Ticker info & quote
        get_info, get_quote

    Category 2 — Historical price data
        get_history

    Category 3 — Financial statements
        get_income_statement, get_balance_sheet, get_cash_flow
        get_quarterly_income_statement

    Category 4 — Earnings
        get_earnings_history, get_calendar

    Category 5 — Dividends
        get_dividends

    Category 6 — Options
        get_options_expirations, get_options_chain

    Category 7 — Holders & Insider data
        get_insider_transactions, get_insider_purchases,
        get_institutional_holders, get_mutualfund_holders,
        get_major_holders

    Category 8 — News
        get_news
    """

    # ── Category 1: Info & Quote ──────────────────────────────────────

    @abstractmethod
    def get_info(self, symbol: str) -> Dict[str, Any]:
        """Return the full info dict for a ticker (company profile, price,
        metrics, sector, etc.).  Equivalent to ``yf.Ticker(s).info``."""
        ...

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Quick quote with price, change, volume.  Default falls through
        to get_info; providers may override with a faster endpoint."""
        info = self.get_info(symbol)
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        prev = info.get("previousClose", 0)
        return {
            "symbol": symbol,
            "price": price,
            "previous_close": prev,
            "change": round(price - prev, 2) if price and prev else 0,
            "change_pct": round(((price - prev) / prev) * 100, 2) if prev else 0,
            "volume": info.get("volume") or info.get("regularMarketVolume", 0),
        }

    # ── Category 2: Historical Prices ─────────────────────────────────

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Return OHLCV DataFrame indexed by datetime.
        Equivalent to ``yf.Ticker(s).history(period=period, interval=interval)``."""
        ...

    # ── Category 3: Financial Statements ──────────────────────────────

    @abstractmethod
    def get_income_statement(self, symbol: str) -> pd.DataFrame:
        """Annual income statement.  Columns = fiscal dates (most recent first)."""
        ...

    @abstractmethod
    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """Annual balance sheet."""
        ...

    @abstractmethod
    def get_cash_flow(self, symbol: str) -> pd.DataFrame:
        """Annual cash flow statement."""
        ...

    @abstractmethod
    def get_quarterly_income_statement(self, symbol: str) -> pd.DataFrame:
        """Quarterly income statement."""
        ...

    # ── Category 4: Earnings ──────────────────────────────────────────

    @abstractmethod
    def get_earnings_history(self, symbol: str) -> pd.DataFrame:
        """Historical EPS actual vs estimate records."""
        ...

    @abstractmethod
    def get_calendar(self, symbol: str) -> Any:
        """Upcoming earnings date and related calendar data.
        Return may be a dict or DataFrame depending on provider."""
        ...

    # ── Category 5: Dividends ─────────────────────────────────────────

    @abstractmethod
    def get_dividends(self, symbol: str) -> pd.Series:
        """Dividend payment history as a DatetimeIndex → amount Series."""
        ...

    # ── Category 6: Options ───────────────────────────────────────────

    @abstractmethod
    def get_options_expirations(self, symbol: str) -> List[str]:
        """List of available options expiration dates (YYYY-MM-DD strings)."""
        ...

    @abstractmethod
    def get_options_chain(self, symbol: str, expiration: str) -> Dict[str, pd.DataFrame]:
        """Options chain for a single expiration.
        Returns ``{"calls": DataFrame, "puts": DataFrame}``."""
        ...

    # ── Category 7: Holders & Insider Data ────────────────────────────

    @abstractmethod
    def get_insider_transactions(self, symbol: str) -> pd.DataFrame:
        """Recent insider transactions (Form 4 filings)."""
        ...

    @abstractmethod
    def get_insider_purchases(self, symbol: str) -> pd.DataFrame:
        """Insider purchase summary."""
        ...

    @abstractmethod
    def get_institutional_holders(self, symbol: str) -> pd.DataFrame:
        """Top institutional holders."""
        ...

    @abstractmethod
    def get_mutualfund_holders(self, symbol: str) -> pd.DataFrame:
        """Top mutual fund holders."""
        ...

    @abstractmethod
    def get_major_holders(self, symbol: str) -> pd.DataFrame:
        """Major holders breakdown (insider %, institutional %, etc.)."""
        ...

    # ── Category 8: News ──────────────────────────────────────────────

    @abstractmethod
    def get_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Recent news articles for the symbol."""
        ...


# ─── YFinance Implementation ─────────────────────────────────────────────────


class YFinanceProvider(MarketDataProvider):
    """
    Concrete provider backed by ``yfinance``.

    This is a drop-in wrapper: every method instantiates a ``yf.Ticker``
    and returns the same data that tool modules were previously fetching
    directly.  No business logic lives here — that stays in the tools.

    Thread-safe: yfinance Ticker objects are created per-call (they are
    lightweight and internally cache HTTP responses).
    """

    def __init__(self) -> None:
        import yfinance  # fail-fast if not installed
        self._yf = yfinance
        logger.info("YFinanceProvider initialized")

    # helpers ──────────────────────────────────────────────────────────

    def _ticker(self, symbol: str):
        """Create a fresh yf.Ticker — lightweight, avoids stale state."""
        return self._yf.Ticker(symbol.upper().strip())

    @staticmethod
    def _empty_df() -> pd.DataFrame:
        return pd.DataFrame()

    @staticmethod
    def _empty_series() -> pd.Series:
        return pd.Series(dtype=float)

    # Category 1 ──────────────────────────────────────────────────────

    def get_info(self, symbol: str) -> Dict[str, Any]:
        try:
            return self._ticker(symbol).info
        except Exception as e:
            logger.error(f"YFinanceProvider.get_info({symbol}): {e}")
            return {}

    # Category 2 ──────────────────────────────────────────────────────

    def get_history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        try:
            return self._ticker(symbol).history(period=period, interval=interval)
        except Exception as e:
            logger.error(f"YFinanceProvider.get_history({symbol}): {e}")
            return self._empty_df()

    # Category 3 ──────────────────────────────────────────────────────

    def get_income_statement(self, symbol: str) -> pd.DataFrame:
        try:
            return self._ticker(symbol).income_stmt
        except Exception as e:
            logger.error(f"YFinanceProvider.get_income_statement({symbol}): {e}")
            return self._empty_df()

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        try:
            return self._ticker(symbol).balance_sheet
        except Exception as e:
            logger.error(f"YFinanceProvider.get_balance_sheet({symbol}): {e}")
            return self._empty_df()

    def get_cash_flow(self, symbol: str) -> pd.DataFrame:
        try:
            return self._ticker(symbol).cashflow
        except Exception as e:
            logger.error(f"YFinanceProvider.get_cash_flow({symbol}): {e}")
            return self._empty_df()

    def get_quarterly_income_statement(self, symbol: str) -> pd.DataFrame:
        try:
            return self._ticker(symbol).quarterly_income_stmt
        except Exception as e:
            logger.error(f"YFinanceProvider.get_quarterly_income_statement({symbol}): {e}")
            return self._empty_df()

    # Category 4 ──────────────────────────────────────────────────────

    def get_earnings_history(self, symbol: str) -> pd.DataFrame:
        try:
            eh = self._ticker(symbol).earnings_history
            return eh if eh is not None else self._empty_df()
        except Exception as e:
            logger.error(f"YFinanceProvider.get_earnings_history({symbol}): {e}")
            return self._empty_df()

    def get_calendar(self, symbol: str) -> Any:
        try:
            return self._ticker(symbol).calendar
        except Exception as e:
            logger.error(f"YFinanceProvider.get_calendar({symbol}): {e}")
            return None

    # Category 5 ──────────────────────────────────────────────────────

    def get_dividends(self, symbol: str) -> pd.Series:
        try:
            return self._ticker(symbol).dividends
        except Exception as e:
            logger.error(f"YFinanceProvider.get_dividends({symbol}): {e}")
            return self._empty_series()

    # Category 6 ──────────────────────────────────────────────────────

    def get_options_expirations(self, symbol: str) -> List[str]:
        try:
            return list(getattr(self._ticker(symbol), "options", []))
        except Exception as e:
            logger.error(f"YFinanceProvider.get_options_expirations({symbol}): {e}")
            return []

    def get_options_chain(self, symbol: str, expiration: str) -> Dict[str, pd.DataFrame]:
        try:
            chain = self._ticker(symbol).option_chain(expiration)
            return {"calls": chain.calls, "puts": chain.puts}
        except Exception as e:
            logger.error(f"YFinanceProvider.get_options_chain({symbol}, {expiration}): {e}")
            return {"calls": self._empty_df(), "puts": self._empty_df()}

    # Category 7 ──────────────────────────────────────────────────────

    def get_insider_transactions(self, symbol: str) -> pd.DataFrame:
        try:
            ticker = self._ticker(symbol)
            df = getattr(ticker, "insider_transactions", None)
            return df if df is not None and not df.empty else self._empty_df()
        except Exception as e:
            logger.error(f"YFinanceProvider.get_insider_transactions({symbol}): {e}")
            return self._empty_df()

    def get_insider_purchases(self, symbol: str) -> pd.DataFrame:
        try:
            ticker = self._ticker(symbol)
            df = getattr(ticker, "insider_purchases", None)
            return df if df is not None and not df.empty else self._empty_df()
        except Exception as e:
            logger.error(f"YFinanceProvider.get_insider_purchases({symbol}): {e}")
            return self._empty_df()

    def get_institutional_holders(self, symbol: str) -> pd.DataFrame:
        try:
            ticker = self._ticker(symbol)
            df = getattr(ticker, "institutional_holders", None)
            return df if df is not None and not df.empty else self._empty_df()
        except Exception as e:
            logger.error(f"YFinanceProvider.get_institutional_holders({symbol}): {e}")
            return self._empty_df()

    def get_mutualfund_holders(self, symbol: str) -> pd.DataFrame:
        try:
            ticker = self._ticker(symbol)
            df = getattr(ticker, "mutualfund_holders", None)
            return df if df is not None and not df.empty else self._empty_df()
        except Exception as e:
            logger.error(f"YFinanceProvider.get_mutualfund_holders({symbol}): {e}")
            return self._empty_df()

    def get_major_holders(self, symbol: str) -> pd.DataFrame:
        try:
            ticker = self._ticker(symbol)
            df = getattr(ticker, "major_holders", None)
            return df if df is not None and not df.empty else self._empty_df()
        except Exception as e:
            logger.error(f"YFinanceProvider.get_major_holders({symbol}): {e}")
            return self._empty_df()

    # Category 8 ──────────────────────────────────────────────────────

    def get_news(self, symbol: str) -> List[Dict[str, Any]]:
        try:
            return self._ticker(symbol).news or []
        except Exception as e:
            logger.error(f"YFinanceProvider.get_news({symbol}): {e}")
            return []


# ─── Provider Singleton & Factory ─────────────────────────────────────────────

_provider_instance: Optional[MarketDataProvider] = None
_provider_lock = threading.Lock()


def get_provider(provider_name: str | None = None) -> MarketDataProvider:
    """
    Return the global MarketDataProvider singleton.

    The provider is created lazily on first call.  Pass ``provider_name``
    to override the default (useful for testing or future multi-provider
    setups).  Currently supported values:

    - ``"yfinance"``  (default)
    - ``"fmp"``       (placeholder — not yet implemented)
    - ``"twelvedata"`` (placeholder — not yet implemented)

    Thread-safe via a simple lock around initialization.

    Example::

        from src.data import get_provider

        provider = get_provider()
        info = provider.get_info("AAPL")
        hist = provider.get_history("AAPL", period="6mo")
    """
    global _provider_instance

    if _provider_instance is not None and provider_name is None:
        return _provider_instance

    with _provider_lock:
        # Double-check lock pattern
        if _provider_instance is not None and provider_name is None:
            return _provider_instance

        name = (provider_name or "yfinance").lower()

        if name == "yfinance":
            _provider_instance = YFinanceProvider()
        elif name == "fmp":
            raise NotImplementedError(
                "FMP provider not yet implemented.  "
                "Install `fmpsdk` and add FMPProvider to src/data/provider.py"
            )
        elif name == "twelvedata":
            raise NotImplementedError(
                "Twelve Data provider not yet implemented.  "
                "Install `twelvedata` and add TwelveDataProvider to src/data/provider.py"
            )
        else:
            raise ValueError(
                f"Unknown provider: {name!r}.  "
                f"Supported: 'yfinance', 'fmp', 'twelvedata'"
            )

        logger.info(f"Market data provider set to: {name}")
        return _provider_instance


def reset_provider() -> None:
    """Reset the singleton (useful in tests)."""
    global _provider_instance
    with _provider_lock:
        _provider_instance = None
