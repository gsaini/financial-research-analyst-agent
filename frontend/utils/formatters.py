"""
Number and date formatting utilities.
"""

from datetime import datetime


def format_currency(value, decimals=2):
    """Format a number as currency. E.g., 1234.5 -> '$1,234.50'."""
    if value is None:
        return "--"
    try:
        return f"${value:,.{decimals}f}"
    except (TypeError, ValueError):
        return "--"


def format_large_number(value):
    """Format large numbers with T/B/M/K suffixes. E.g., 2.87e12 -> '$2.87T'."""
    if value is None or value == 0:
        return "--"
    try:
        value = float(value)
        if abs(value) >= 1e12:
            return f"${value / 1e12:.2f}T"
        if abs(value) >= 1e9:
            return f"${value / 1e9:.2f}B"
        if abs(value) >= 1e6:
            return f"${value / 1e6:.2f}M"
        if abs(value) >= 1e3:
            return f"${value / 1e3:.1f}K"
        return f"${value:,.0f}"
    except (TypeError, ValueError):
        return "--"


def format_percent(value, decimals=2, include_sign=True):
    """Format a number as percentage. E.g., 1.52 -> '+1.52%'."""
    if value is None:
        return "--"
    try:
        value = float(value)
        sign = "+" if value > 0 and include_sign else ""
        return f"{sign}{value:.{decimals}f}%"
    except (TypeError, ValueError):
        return "--"


def format_ratio(value, decimals=2):
    """Format a ratio/multiple. E.g., 28.5 -> '28.50x'."""
    if value is None:
        return "--"
    try:
        return f"{float(value):.{decimals}f}x"
    except (TypeError, ValueError):
        return "--"


def format_number(value, decimals=2):
    """Format a plain number. E.g., 45.123 -> '45.12'."""
    if value is None:
        return "--"
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "--"


def format_date(iso_string):
    """Format an ISO date string. E.g., '2026-02-21' -> 'Feb 21, 2026'."""
    if not iso_string:
        return "--"
    try:
        if isinstance(iso_string, datetime):
            return iso_string.strftime("%b %d, %Y")
        dt = datetime.fromisoformat(str(iso_string).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return str(iso_string)


def format_date_short(iso_string):
    """Format an ISO date string short. E.g., '2026-02-21' -> '02/21'."""
    if not iso_string:
        return "--"
    try:
        if isinstance(iso_string, datetime):
            return iso_string.strftime("%m/%d")
        dt = datetime.fromisoformat(str(iso_string).replace("Z", "+00:00"))
        return dt.strftime("%m/%d")
    except (ValueError, TypeError):
        return str(iso_string)


def color_for_value(value):
    """Return CSS color class based on positive/negative value."""
    if value is None:
        return "signal-neutral"
    try:
        v = float(value)
        if v > 0:
            return "signal-positive"
        elif v < 0:
            return "signal-negative"
        return "signal-neutral"
    except (TypeError, ValueError):
        return "signal-neutral"
