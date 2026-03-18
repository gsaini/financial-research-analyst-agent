"""
AI Financial Advisor - Chat with AI about stocks, ETFs, and investing.
Uses on-demand tool calling — fetches only what's needed per question.
"""

import streamlit as st
from utils.theme import inject_css
from utils.session import init_session_state
from utils.data_service import ask_advisor
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
            I fetch real-time data on demand to give you the most relevant advice.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─── FAQ Templates ────────────────────────────────────────────

if "advisor_chat_history" not in st.session_state:
    st.session_state.advisor_chat_history = []

if not st.session_state.advisor_chat_history:
    _section("Quick Questions")

    _faqs = [
        ["Which ETF should I invest in right now?",  "What are the top 3 safest ETFs for beginners?"],
        ["I bought QQQM at $180 — should I hold or sell?", "Compare QQQ vs VOO for long-term investing"],
        ["Build me a $10K diversified ETF portfolio", "Which sectors are performing best this year?"],
        ["What's the best dividend ETF for passive income?", "Is AAPL a good buy at current price?"],
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
        # Live progress display
        status = st.status("Analyzing your question...", expanded=True)

        def _on_progress(key: str, label: str):
            status.update(label=label)
            status.write(f"  {label}")

        response = ask_advisor(
            question=prompt,
            chat_history=st.session_state.advisor_chat_history[:-1],
            on_progress=_on_progress,
        )

        status.update(label="Analysis complete", state="complete", expanded=False)
        st.markdown(response)

    st.session_state.advisor_chat_history.append({"role": "assistant", "content": response})
