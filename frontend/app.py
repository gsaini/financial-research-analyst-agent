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
    <div style="text-align: center; padding: 4rem 1rem 2.5rem; position: relative;">
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                    width: 500px; height: 500px; background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
                    pointer-events: none; z-index: 0;"></div>
        <h1 style="font-family: 'Inter', -apple-system, sans-serif; font-size: 2.75rem; font-weight: 800;
                   margin-bottom: 0.75rem; line-height: 1.15; position: relative; z-index: 1; letter-spacing: -0.03em;">
            <span style="color: #fafafa;">Financial</span>
            <span style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                         -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                         background-clip: text;">
                AI Platform
            </span>
        </h1>
        <p style="font-family: 'Inter', sans-serif; color: #a1a1aa; font-size: 1.05rem;
                  max-width: 600px; margin: 0 auto 2rem; line-height: 1.6; position: relative; z-index: 1; font-weight: 400;">
            Advanced stock analysis, thematic investing, disruption scoring, earnings intelligence,
            and portfolio optimization — powered by AI agents.
        </p>
        <div style="display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; position: relative; z-index: 1;">
            <div style="display: flex; align-items: center; gap: 0.5rem; color: #a1a1aa; font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; font-weight: 500;">
                <span style="width: 6px; height: 6px; background: #22c55e; border-radius: 50%;"></span>
                Real-time Data
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem; color: #a1a1aa; font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; font-weight: 500;">
                <span style="width: 6px; height: 6px; background: #22c55e; border-radius: 50%;"></span>
                10 AI Agents
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem; color: #a1a1aa; font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; font-weight: 500;">
                <span style="width: 6px; height: 6px; background: #22c55e; border-radius: 50%;"></span>
                LLM Powered
            </div>
        </div>
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
st.markdown("""
<div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
    <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
    <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: #fafafa; font-size: 0.9rem; font-weight: 600; letter-spacing: -0.01em;">
        Market Pulse
    </h3>
    <div style="flex: 1; height: 1px; background: linear-gradient(90deg, rgba(255,255,255,0.06), transparent);"></div>
</div>
""", unsafe_allow_html=True)
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

st.markdown("<br><br>", unsafe_allow_html=True)

# Feature cards
st.markdown("""
<div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.25rem;">
    <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
    <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: #fafafa; font-size: 0.9rem; font-weight: 600; letter-spacing: -0.01em;">
        Features
    </h3>
    <div style="flex: 1; height: 1px; background: linear-gradient(90deg, rgba(255,255,255,0.06), transparent);"></div>
</div>
""", unsafe_allow_html=True)

features = [
    ("Stock Analysis", "Comprehensive technical, fundamental & sentiment analysis", "pages/2_Stock_Analysis.py"),
    ("Thematic Investing", "Browse and analyze investment themes & megatrends", "pages/3_Thematic_Investing.py"),
    ("Peer Comparison", "Compare stocks against industry peers", "pages/4_Peer_Comparison.py"),
    ("Market Disruption", "Score companies on innovation and disruption potential", "pages/5_Market_Disruption.py"),
    ("Quarterly Earnings", "Track EPS beats/misses, trends, and quality scores", "pages/6_Quarterly_Earnings.py"),
    ("Portfolio Analysis", "Analyze multi-stock portfolios with correlation insights", "pages/7_Portfolio_Analysis.py"),
    ("Reports", "Generate downloadable research reports in Markdown or JSON", "pages/8_Reports.py"),
    ("Financial News", "Browse latest headlines across your watchlist and any ticker", "pages/9_News.py"),
    ("Performance Tracking", "Multi-horizon returns, benchmark comparison & drawdown analysis", "pages/10_Performance.py"),
    ("Sentiment Analysis", "AI-powered news sentiment scoring, trends & source diversity", "pages/11_Sentiment.py"),
]

cols = st.columns(3)
for i, (title, desc, page) in enumerate(features):
    with cols[i % 3]:
        st.markdown(
            f"""
            <div class="card" style="min-height: 120px; cursor: pointer;">
                <div style="font-family: 'Inter', sans-serif; font-weight: 600; font-size: 0.95rem;
                            margin-bottom: 0.4rem; color: #fafafa; letter-spacing: -0.01em;">
                    {title}
                </div>
                <div style="font-family: 'Inter', sans-serif; font-size: 0.825rem; color: #a1a1aa; line-height: 1.5;">
                    {desc}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"Launch", key=f"nav_{i}", use_container_width=True):
            st.switch_page(page)

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align: center; padding: 1.25rem; border-top: 1px solid rgba(255,255,255,0.06); position: relative;">
        <div style="position: absolute; top: -1px; left: 50%; transform: translateX(-50%);
                    width: 80px; height: 1px; background: linear-gradient(90deg, #6366f1, #8b5cf6);"></div>
        <p style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #52525b; font-weight: 400;">
            Financial AI Platform v1.0 · For informational purposes only · Data: Yahoo Finance
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
