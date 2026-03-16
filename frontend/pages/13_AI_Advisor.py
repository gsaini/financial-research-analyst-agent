"""
AI Financial Advisor - Chat with AI about stocks, ETFs, and investing.
"""

import streamlit as st
from utils.theme import inject_css
from utils.session import init_session_state
from utils.formatters import format_currency, format_large_number, format_percent
from utils.data_service import (
    screen_etfs,
    ask_financial_question,
)
from components.sidebar import render_sidebar

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Advisor | FinancialAI",
    page_icon=":speech_balloon:",
    layout="wide",
)
inject_css()
init_session_state()
render_sidebar()


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


# ─── Header ──────────────────────────────────────────────────

st.markdown(
    """
    <div style="text-align: center; padding: 2rem 1rem 1rem;">
        <h1 style="font-family: 'Inter', sans-serif; font-size: 2rem; font-weight: 800;
                   letter-spacing: -0.03em; margin-bottom: 0.5rem;">
            <span style="color: #fafafa;">AI Financial</span>
            <span style="background: linear-gradient(135deg, #6366f1, #8b5cf6);
                         -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Advisor
            </span>
        </h1>
        <p style="font-size: 0.9rem; color: #71717a; max-width: 520px; margin: 0 auto; line-height: 1.6;">
            Ask me anything about stocks, ETFs, dividends, portfolio strategy, or market themes.
            I'll ask clarifying questions to give you the most relevant advice.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─── Build financial context (cached in session) ─────────────

@st.cache_data(ttl=1800, show_spinner=False)
def _build_advisor_context() -> str:
    """Build a rich context string from ETF screening data for the AI."""
    result = screen_etfs(top_n=10)
    if "error" in result:
        return "ETF screening data unavailable."

    lines = ["TOP 10 ETF RECOMMENDATIONS:"]
    for i, etf in enumerate(result.get("top_recommendations", [])):
        returns = etf.get("returns", {})
        lines.append(
            f"#{i+1} {etf['symbol']} ({etf.get('name', '')}) | "
            f"Theme: {etf.get('theme', '')} | Score: {etf['composite_score']}/100 | "
            f"Rec: {etf.get('recommendation', '')} | "
            f"Price: ${etf.get('current_price', 'N/A')} | "
            f"YTD: {returns.get('ytd', 'N/A')}% | 3M: {returns.get('3m', 'N/A')}% | "
            f"1Y: {returns.get('1y', 'N/A')}% | "
            f"Vol: {etf.get('volatility', 'N/A')}% | "
            f"Risk: {etf.get('risk_level', 'N/A')} | "
            f"Expense: {etf.get('expense_ratio') or 'N/A'} | "
            f"AUM: {format_large_number(etf.get('total_assets')) if etf.get('total_assets') else 'N/A'}"
        )

    theme_rankings = result.get("theme_rankings", [])
    if theme_rankings:
        lines.append("\nTHEME RANKINGS:")
        for t in theme_rankings:
            lines.append(
                f"{t['theme_name']} | Health: {t['health_score']} | "
                f"Momentum: {t['momentum_score']} | Risk: {t['risk_level']} | "
                f"1Y: {t.get('performance_1y', 'N/A')} | YTD: {t.get('performance_ytd', 'N/A')}"
            )

    lines.append(f"\nTotal themes: {result.get('total_themes_analyzed', 0)} | "
                 f"Total ETFs screened: {result.get('total_etfs_screened', 0)}")

    return "\n".join(lines)


# Load context in background (only once)
if "advisor_context" not in st.session_state:
    with st.spinner("Loading market data..."):
        st.session_state.advisor_context = _build_advisor_context()

# ─── FAQ Templates ────────────────────────────────────────────

# Initialize chat history
if "advisor_chat_history" not in st.session_state:
    st.session_state.advisor_chat_history = []

if not st.session_state.advisor_chat_history:
    _section("Quick Questions")

    _faqs = [
        ["Which ETF should I invest in right now?",  "What are the top 3 safest ETFs for beginners?"],
        ["I bought QQQM at $180 — should I hold or sell?", "Compare QQQ vs VOO for long-term investing"],
        ["Build me a $10K diversified ETF portfolio", "Which investment themes have the strongest momentum?"],
        ["What's the best dividend ETF for passive income?", "Which sectors should I avoid right now?"],
    ]

    for row in _faqs:
        cols = st.columns(2)
        for j, faq in enumerate(row):
            with cols[j]:
                if st.button(faq, key=f"adv_faq_{faq[:20]}", use_container_width=True):
                    st.session_state.advisor_faq_selected = faq
                    st.rerun()

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

else:
    # Show clear chat button when conversation is active
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
    # Show user message
    st.session_state.advisor_chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = ask_financial_question(
                question=prompt,
                context=st.session_state.advisor_context,
                chat_history=st.session_state.advisor_chat_history[:-1],
            )
        st.markdown(response)

    st.session_state.advisor_chat_history.append({"role": "assistant", "content": response})
