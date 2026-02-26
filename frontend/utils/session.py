"""
Session state management for the Streamlit app.
"""

import streamlit as st


def init_session_state():
    """Initialize all session state variables with sensible defaults."""
    defaults = {
        "selected_symbol": "",
        "watchlist": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        "portfolio_symbols": [],
        "portfolio_weights": {},
        "selected_theme": None,
        "comparison_symbols": [],
        "analysis_period": "1y",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def update_symbol(symbol: str):
    """Update the globally selected symbol."""
    st.session_state.selected_symbol = symbol.upper().strip()


def add_to_watchlist(symbol: str):
    """Add a symbol to the watchlist."""
    symbol = symbol.upper().strip()
    if symbol and symbol not in st.session_state.watchlist:
        st.session_state.watchlist.append(symbol)


def remove_from_watchlist(symbol: str):
    """Remove a symbol from the watchlist."""
    st.session_state.watchlist = [
        s for s in st.session_state.watchlist if s != symbol.upper().strip()
    ]


def get_symbol():
    """Get the currently selected symbol."""
    return st.session_state.get("selected_symbol", "")
