"""
Shared sidebar component - branding, global symbol search, watchlist.
"""

import streamlit as st
from utils.session import init_session_state, add_to_watchlist, remove_from_watchlist


def render_sidebar():
    """Render the shared sidebar with branding, search, and watchlist."""
    init_session_state()

    with st.sidebar:
        # Branding
        st.markdown("# FinancialAI")
        st.caption("AI-Powered Research Platform")
        st.markdown("---")

        # Global symbol search
        st.markdown("### Search")
        symbol = st.text_input(
            "Stock Symbol",
            value=st.session_state.get("selected_symbol", ""),
            placeholder="e.g. AAPL, MSFT, GOOGL",
            key="sidebar_symbol_input",
            label_visibility="collapsed",
        )
        if symbol:
            st.session_state.selected_symbol = symbol.upper().strip()

        st.markdown("---")

        # Watchlist
        st.markdown("### Watchlist")
        watchlist = st.session_state.get("watchlist", [])

        if watchlist:
            cols_per_row = 3
            for i in range(0, len(watchlist), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    idx = i + j
                    if idx < len(watchlist):
                        sym = watchlist[idx]
                        if col.button(sym, key=f"wl_{sym}", use_container_width=True):
                            st.session_state.selected_symbol = sym
                            st.rerun()
        else:
            st.caption("No symbols in watchlist.")

        # Add to watchlist
        new_sym = st.text_input(
            "Add to watchlist",
            placeholder="Symbol",
            key="add_watchlist_input",
            label_visibility="collapsed",
        )
        if new_sym:
            add_to_watchlist(new_sym)
            st.rerun()

        st.markdown("---")

        # System info
        st.markdown("### System")
        st.caption("Data: Yahoo Finance (yfinance)")
        st.caption("Charts: TradingView Lightweight")
        st.caption("Analysis: Local Python Tools")

        st.markdown("---")
        st.markdown(
            "<div style='font-size: 0.65rem; color: #6b7280; line-height: 1.4;'>"
            "For informational purposes only. Not financial advice."
            "</div>",
            unsafe_allow_html=True,
        )
