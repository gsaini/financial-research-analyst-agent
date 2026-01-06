"""
Helper utilities for the Financial Research Analyst Agent.
"""

from typing import Any, Optional, Union
from decimal import Decimal


def format_currency(value: Union[int, float, Decimal], currency: str = "USD") -> str:
    """
    Format a number as currency.
    
    Args:
        value: Numeric value to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    symbol = symbols.get(currency, currency + " ")
    
    if abs(value) >= 1_000_000_000_000:
        return f"{symbol}{value / 1_000_000_000_000:.2f}T"
    elif abs(value) >= 1_000_000_000:
        return f"{symbol}{value / 1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"{symbol}{value / 1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{symbol}{value / 1_000:.2f}K"
    else:
        return f"{symbol}{value:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a number as percentage.
    
    Args:
        value: Decimal value (0.15 = 15%)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def format_large_number(value: Union[int, float]) -> str:
    """
    Format large numbers with suffixes.
    
    Args:
        value: Numeric value
        
    Returns:
        Formatted number string
    """
    if abs(value) >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    elif abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return f"{value:,.0f}"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: The numerator
        denominator: The denominator
        default: Default value if division fails
        
    Returns:
        Result of division or default value
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default


def calculate_percentage_change(old_value: float, new_value: float) -> Optional[float]:
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change or None if calculation fails
    """
    if old_value == 0:
        return None
    return ((new_value - old_value) / abs(old_value)) * 100


def clean_numeric(value: Any) -> Optional[float]:
    """
    Clean and convert a value to float.
    
    Args:
        value: Value to clean
        
    Returns:
        Float value or None
    """
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Remove common formatting
        cleaned = value.replace(",", "").replace("$", "").replace("%", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    return None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
