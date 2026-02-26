"""
FinancialAI Research Platform - Main Entry Point
"""

import streamlit as st
from utils.theme import inject_css
from utils.session import init_session_state
from components.sidebar import render_sidebar

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="FinancialAI Research",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Theme & State ───────────────────────────────────────────
inject_css()
init_session_state()
render_sidebar()

# ─── Landing Page ────────────────────────────────────────────

# Hero section
st.markdown(
    """
    <div style="text-align: center; padding: 3rem 1rem 2rem;">
        <h1 style="font-size: 3rem; font-weight: 800; margin-bottom: 0.5rem; line-height: 1.1;">
            AI-Powered
            <span style="background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                         -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                         background-clip: text;">
                Financial Research
            </span>
        </h1>
        <p style="color: #9ca3af; font-size: 1.1rem; max-width: 600px; margin: 0 auto 2rem;">
            Comprehensive stock analysis, thematic investing, disruption scoring,
            earnings tracking, and portfolio management — powered by intelligent agents.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Quick search with auto-suggestions
from utils.data_service import search_symbols

col_pad1, col_search, col_pad2 = st.columns([1, 2, 1])
with col_search:
    query = st.text_input(
        "Quick Analysis",
        placeholder="Search stocks (e.g., Apple, AAPL, Tesla)",
        label_visibility="collapsed",
        key="home_search",
    )

    if query and len(query.strip()) > 2:
        # show_spinner on @st.cache_data renders a visible overlay on cache miss
        suggestions = search_symbols(query.strip())
        if suggestions:
            with st.container(border=True):
                st.caption(f"Found {len(suggestions[:6])} results")
                for s in suggestions[:6]:
                    sym = s["symbol"]
                    name = s["name"]
                    exchange = s["exchange"]
                    type_label = "ETF" if s["type"] == "ETF" else exchange
                    if st.button(
                        f":mag:  **{sym}**  ·  {name}  _({type_label})_",
                        key=f"suggest_{sym}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_symbol = sym
                        st.switch_page("pages/2_Stock_Analysis.py")
        else:
            st.caption("No matches found.")
    elif query and len(query.strip()) <= 2:
        st.caption("Type 3+ characters to see suggestions.")

st.markdown("<br>", unsafe_allow_html=True)

# Market indices KPIs
st.markdown("### Market Overview")
from utils.data_service import get_stock_price
from utils.formatters import format_currency, format_percent

indices = [
    ("SPY", "S&P 500"),
    ("QQQ", "NASDAQ 100"),
    ("DIA", "Dow Jones"),
    ("IWM", "Russell 2000"),
]

cols = st.columns(4)
for col, (ticker, label) in zip(cols, indices):
    with col:
        data = get_stock_price(ticker)
        if "error" not in data:
            price = data.get("current_price", 0)
            change = data.get("change_percent", 0)
            col.metric(
                label=label,
                value=format_currency(price),
                delta=format_percent(change),
            )
        else:
            col.metric(label=label, value="--", delta="N/A")

st.markdown("<br>", unsafe_allow_html=True)

# Feature cards
st.markdown("### Explore")

features = [
    ("Stock Analysis", "Comprehensive technical, fundamental & sentiment analysis", "pages/2_Stock_Analysis.py"),
    ("Thematic Investing", "Browse and analyze investment themes & megatrends", "pages/3_Thematic_Investing.py"),
    ("Peer Comparison", "Compare stocks against industry peers", "pages/4_Peer_Comparison.py"),
    ("Market Disruption", "Score companies on innovation and disruption potential", "pages/5_Market_Disruption.py"),
    ("Quarterly Earnings", "Track EPS beats/misses, trends, and quality scores", "pages/6_Quarterly_Earnings.py"),
    ("Portfolio Analysis", "Analyze multi-stock portfolios with correlation insights", "pages/7_Portfolio_Analysis.py"),
    ("Reports", "Generate downloadable research reports in Markdown or JSON", "pages/8_Reports.py"),
    ("Financial News", "Browse latest headlines across your watchlist and any ticker", "pages/9_News.py"),
]

cols = st.columns(3)
for i, (title, desc, page) in enumerate(features):
    with cols[i % 3]:
        st.markdown(
            f"""
            <div class="card" style="min-height: 120px;">
                <div style="font-weight: 700; font-size: 1rem; margin-bottom: 0.375rem; color: #f9fafb;">
                    {title}
                </div>
                <div style="font-size: 0.8rem; color: #9ca3af; line-height: 1.4;">
                    {desc}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"Open {title}", key=f"nav_{i}", use_container_width=True):
            st.switch_page(page)

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align: center; padding: 1rem; border-top: 1px solid #1f2937;">
        <p style="font-size: 0.7rem; color: #6b7280;">
            For informational purposes only. Not financial advice. Data sourced from Yahoo Finance.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
