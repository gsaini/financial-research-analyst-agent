"""
Top header navigation bar with brand and menus on same row.
"""

import streamlit as st


# Navigation structure
NAV_GROUPS = {
    "Analysis": [
        ("Dashboard", "pages/1_Dashboard.py", "📊"),
        ("Stock Analysis", "pages/2_Stock_Analysis.py", "📈"),
        ("Peer Comparison", "pages/4_Peer_Comparison.py", "⚖️"),
        ("Performance", "pages/10_Performance.py", "🎯"),
        ("Sentiment", "pages/11_Sentiment.py", "💬"),
    ],
    "Research": [
        ("Thematic Investing", "pages/3_Thematic_Investing.py", "🎨"),
        ("Market Disruption", "pages/5_Market_Disruption.py", "🚀"),
        ("Quarterly Earnings", "pages/6_Quarterly_Earnings.py", "📑"),
        ("Short Interest", "pages/14_Short_Interest.py", "📉"),
        ("Analyst Consensus", "pages/16_Analyst_Consensus.py", "🎯"),
    ],
    "Portfolio": [
        ("Portfolio Analysis", "pages/7_Portfolio_Analysis.py", "💼"),
        ("Dividends", "pages/15_Dividends.py", "💰"),
        ("Reports", "pages/8_Reports.py", "📄"),
        ("Alerts", "pages/17_Alerts.py", "🔔"),
    ],
    "Data": [
        ("News", "pages/9_News.py", "📰"),
        ("ETF Screener", "pages/12_ETF_Screener.py", "🔍"),
        ("Macro Economy", "pages/13_Macro_Economy.py", "🌐"),
    ],
}

GROUP_ICONS = {
    "Analysis": "📊",
    "Research": "🔬",
    "Portfolio": "💼",
    "Data": "📰",
}


def render_header():
    """Render header with brand and navigation on same row."""

    # Inject sticky header styles - target ONLY the element containing brand-logo
    st.markdown(
        """
        <style>
            /* Sticky header - ONLY target the container with brand-logo */
            [data-testid="stMainBlockContainer"] > div > div:has(.brand-logo) {
                position: sticky !important;
                top: 0 !important;
                z-index: 999 !important;
                background: #09090b !important;
                padding: 0.5rem 0 0.25rem 0 !important;
                margin: 0 -1rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Single row: Logo | Nav menus
    cols = st.columns([2.4, 1, 1, 1, 1])

    # Modern Logo/Brand
    with cols[0]:
        # Modern logo with icon + text
        st.markdown(
            """
            <a href="/" target="_self" style="text-decoration: none;">
                <div class="brand-logo">
                    <div class="logo-icon">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M3 17L9 11L13 15L21 7" stroke="url(#grad1)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M17 7H21V11" stroke="url(#grad1)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                            <circle cx="12" cy="19" r="2" fill="url(#grad1)" opacity="0.6"/>
                            <circle cx="6" cy="19" r="1.5" fill="url(#grad1)" opacity="0.4"/>
                            <circle cx="18" cy="19" r="1.5" fill="url(#grad1)" opacity="0.4"/>
                            <defs>
                                <linearGradient id="grad1" x1="3" y1="7" x2="21" y2="19" gradientUnits="userSpaceOnUse">
                                    <stop stop-color="#818cf8"/>
                                    <stop offset="1" stop-color="#6366f1"/>
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <span class="logo-text">
                        <span class="logo-finance">Finance</span><span class="logo-ai">AI</span>
                    </span>
                </div>
            </a>
            <style>
                .brand-logo {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    height: 38px;
                    transition: all 0.2s ease;
                }
                .brand-logo:hover {
                    opacity: 0.85;
                }
                .logo-icon {
                    width: 28px;
                    height: 28px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .logo-icon svg {
                    width: 100%;
                    height: 100%;
                }
                .logo-text {
                    font-family: 'Inter', -apple-system, sans-serif;
                    font-size: 1.25rem;
                    font-weight: 700;
                    letter-spacing: -0.03em;
                }
                .logo-finance {
                    color: #fafafa;
                }
                .logo-ai {
                    background: linear-gradient(135deg, #818cf8, #6366f1);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

    # Navigation popovers
    for idx, (group_name, pages) in enumerate(NAV_GROUPS.items()):
        with cols[idx + 1]:
            icon = GROUP_ICONS.get(group_name, "📁")
            with st.popover(f"{icon} {group_name}", use_container_width=True):
                for page_name, page_path, page_icon in pages:
                    if st.button(
                        f"{page_icon}  {page_name}",
                        key=f"nav_{page_path}",
                        use_container_width=True,
                    ):
                        st.switch_page(page_path)

    # Theme toggle (compact, in-line)
    from utils.theme import render_theme_toggle
    with st.container():
        c1, c2 = st.columns([10, 1])
        with c2:
            render_theme_toggle()

    # Divider
    st.markdown(
        "<div style='height: 1px; background: linear-gradient(90deg, rgba(99,102,241,0.3), transparent); margin: 0.35rem 0 0.5rem;'></div>",
        unsafe_allow_html=True,
    )
