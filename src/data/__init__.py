"""
Data provider abstraction layer.

This package decouples all tool modules from the underlying market data source
(currently Yahoo Finance via yfinance). Importing ``get_provider`` and calling
its methods is the recommended way to fetch market data throughout the project.

Usage::

    from src.data import get_provider

    provider = get_provider()        # returns the configured singleton
    info     = provider.get_info("AAPL")
    hist     = provider.get_history("AAPL", period="1y")
    chain    = provider.get_options_chain("AAPL", expiration="2025-06-20")
"""

from src.data.provider import get_provider, MarketDataProvider, MultiProvider, reset_provider

__all__ = [
    "get_provider",
    "MarketDataProvider",
    "MultiProvider",
    "reset_provider",
]
