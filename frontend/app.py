"""
FinancialAI Research Platform - AI Advisor Landing Page
Chat with AI about stocks, ETFs, and investing with real-time data.
"""

import streamlit as st
from utils.theme import inject_css
from utils.session import init_session_state
from utils.data_service import ask_advisor, get_stock_price
from utils.formatters import format_currency, format_percent
from components.header import render_header

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="FinancialAI Research",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Theme & State ───────────────────────────────────────────
inject_css()
init_session_state()

# ─── Header Navigation ───────────────────────────────────────
render_header()

# ─── Section header helper ───────────────────────────────────


def _section(title: str):
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 0.75rem; margin: 1.25rem 0 1rem;">
            <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
            <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: #fafafa; font-size: 0.9rem;
                        font-weight: 600; letter-spacing: -0.01em;">{title}</h3>
            <div style="flex: 1; height: 1px; background: linear-gradient(90deg, rgba(255,255,255,0.06), transparent);"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Hero Header ─────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align: center; padding: 1.5rem 1rem 2.5rem; position: relative;">
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                    width: 400px; height: 400px; background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
                    pointer-events: none; z-index: 0;"></div>
        <h1 style="font-family: 'Inter', sans-serif; font-size: 2.25rem; font-weight: 800;
                   letter-spacing: -0.03em; margin-bottom: 0.5rem; position: relative; z-index: 1;">
            <span style="color: #fafafa;">AI Financial</span>
            <span style="background: linear-gradient(135deg, #6366f1, #8b5cf6);
                         -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Advisor
            </span>
        </h1>
        <p style="font-size: 0.9rem; color: #71717a; max-width: 520px; margin: 0 auto; line-height: 1.6; position: relative; z-index: 1;">
            Ask me anything about stocks, ETFs, dividends, portfolio strategy, or market themes.
            I fetch real-time data on demand to give you the most relevant advice.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Market Pulse (Compact) ──────────────────────────────────
indices = [
    ("SPY", "S&P 500"),
    ("QQQ", "NASDAQ"),
    ("DIA", "Dow"),
    ("IWM", "Russell"),
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

st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

# ─── Initialize Chat History ─────────────────────────────────
if "advisor_chat_history" not in st.session_state:
    st.session_state.advisor_chat_history = []

# ─── FAQ Templates (shown when chat is empty) ────────────────
if not st.session_state.advisor_chat_history:
    _section("Quick Questions")

    _faqs = [
        [
            "Which ETF should I invest in right now?",
            "What are the top 3 safest ETFs for beginners?",
            "I bought QQQM at $180 - should I hold or sell?",
        ],
        [
            "Compare QQQ vs VOO for long-term investing",
            "Build me a $10K diversified ETF portfolio",
            "Which sectors are performing best this year?",
        ],
        [
            "What's the best dividend ETF for passive income?",
            "Is AAPL a good buy at current price?",
            "What are the top AI stocks to watch?",
        ],
    ]

    for row in _faqs:
        cols = st.columns(3)
        for j, faq in enumerate(row):
            with cols[j]:
                if st.button(faq, key=f"adv_faq_{faq[:20]}", use_container_width=True):
                    st.session_state.advisor_faq_selected = faq
                    st.rerun()

else:
    # Show clear chat button when there's history
    col_clear, _ = st.columns([1, 5])
    with col_clear:
        if st.button("Clear chat", use_container_width=True):
            st.session_state.advisor_chat_history = []
            st.rerun()

# ─── Chat Messages ────────────────────────────────────────────
for msg in st.session_state.advisor_chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ─── Chat Input ──────────────────────────────────────────────
_faq_prompt = st.session_state.pop("advisor_faq_selected", None)
_typed_prompt = st.chat_input("Ask about any stock, ETF, theme, or investment strategy...")
prompt = _faq_prompt or _typed_prompt

if prompt:
    st.session_state.advisor_chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Live progress display with step icons
        status = st.status("Analyzing your question...", expanded=True)

        _step_icons = {
            "profiling": "👤",
            "prefetch": "📡",
            "analyzing": "🧠",
            "lookup": "📊",
            "technical": "📈",
            "fundamentals": "📋",
            "dividends": "💰",
            "earnings": "📑",
            "sentiment": "📰",
            "peers": "🔄",
            "options": "⚡",
            "insider": "🔍",
            "synthesizing": "✨",
            "fallback": "🔁",
        }

        def _on_progress(key: str, label: str):
            icon = _step_icons.get(key, "⏳")
            status.update(label=f"{icon} {label}")
            status.write(f"{icon} {label}")

        response = ask_advisor(
            question=prompt,
            chat_history=st.session_state.advisor_chat_history[:-1],
            on_progress=_on_progress,
        )

        status.update(label="Analysis complete", state="complete", expanded=False)
        st.markdown(response)

    st.session_state.advisor_chat_history.append(
        {"role": "assistant", "content": response}
    )

# ─── Fixed Footer ────────────────────────────────────────────
st.markdown(
    """
    <style>
        .fixed-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #09090b;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding: 0.75rem 1rem;
            text-align: center;
            z-index: 998;
        }
        .fixed-footer p {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.7rem;
            color: #52525b;
            margin: 0;
        }
        /* Add padding at bottom of page to prevent content being hidden behind footer */
        [data-testid="stMainBlockContainer"] {
            padding-bottom: 3rem !important;
        }
    </style>
    <div class="fixed-footer">
        <p>Financial AI Platform v1.0 - For informational purposes only</p>
    </div>
    """,
    unsafe_allow_html=True,
)
