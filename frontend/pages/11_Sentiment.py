"""
Enhanced News & Sentiment Analysis - FinBERT/VADER sentiment scoring,
news volume tracking, sentiment trends, source diversity, and topic extraction.
"""

import streamlit as st
from utils.theme import inject_css, COLORS
from utils.session import init_session_state
from utils.formatters import format_percent, format_date
from utils.data_service import analyze_news_sentiment
from components.sidebar import render_sidebar
from components.plotly_charts import (
    create_gauge_chart,
    create_donut_chart,
    create_line_chart,
    create_horizontal_bar,
)

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Sentiment Analysis | FinancialAI",
    page_icon=":newspaper:",
    layout="wide",
)
inject_css()
init_session_state()
render_sidebar()

st.markdown("## News & Sentiment Analysis")
st.caption("AI-powered sentiment scoring, news volume tracking, trends & source diversity")

# ─── Symbol Input ────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    symbol = st.text_input(
        "Stock Symbol",
        value=st.session_state.get("selected_symbol", "AAPL"),
        placeholder="Enter ticker (e.g., AAPL)",
        key="sent_symbol",
    ).strip().upper()

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("Analyze Sentiment", use_container_width=True, type="primary")

if analyze_btn and symbol:
    st.session_state.sent_symbol_active = symbol

active = st.session_state.get("sent_symbol_active", "")
if not active:
    st.info("Enter a stock symbol and click **Analyze Sentiment** to get started.")
    st.stop()

# ─── Fetch Data ──────────────────────────────────────────────
result = analyze_news_sentiment(active)

if "error" in result:
    st.error(f"Error: {result['error']}")
    st.stop()

agg = result.get("aggregate_sentiment", {})
dist = result.get("distribution", {})
volume = result.get("volume", {})
sources = result.get("source_diversity", {})
trend = result.get("sentiment_trend", {})
topics = result.get("topics", [])
correlation = result.get("news_price_correlation", {})
engine = result.get("engine", "unknown")

# ─── Header ──────────────────────────────────────────────────
agg_score = agg.get("score", 0)
agg_label = agg.get("label", "Neutral")
agg_conf = agg.get("confidence", 0)

if agg_label == "Positive":
    label_color = COLORS["success"]
elif agg_label == "Negative":
    label_color = COLORS["danger"]
else:
    label_color = COLORS["text_muted"]

engine_label = "FinBERT" if engine == "finbert" else "VADER (Financial-Enhanced)" if engine == "vader" else engine

st.markdown(f"""
<div style="display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem;
            background: {COLORS['bg_card']}; border-radius: 10px; border: 1px solid {COLORS['border']};
            margin-bottom: 1.5rem;">
    <div>
        <span style="font-size: 1.5rem; font-weight: 700; color: {COLORS['text_primary']}; font-family: 'Inter', sans-serif;">
            {active}
        </span>
        <span style="color: {COLORS['text_muted']}; font-size: 0.85rem; margin-left: 0.75rem;">
            {result.get('articles_analyzed', 0)} articles analyzed
        </span>
    </div>
    <div style="margin-left: auto; text-align: right;">
        <span style="font-size: 1.25rem; font-weight: 600; color: {label_color}; font-family: 'JetBrains Mono', monospace;">
            {agg_label}
        </span>
        <div style="font-size: 0.7rem; color: {COLORS['text_muted']};">Engine: {engine_label}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Section helper ──────────────────────────────────────────

def section_header(title):
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; margin-top: 0.5rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            {title}
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """, unsafe_allow_html=True)


# ─── Aggregate Sentiment ────────────────────────────────────
section_header("Aggregate Sentiment")

g1, g2, g3, g4 = st.columns(4)

with g1:
    # Map score from [-1, 1] to [0, 100] for gauge
    gauge_val = (agg_score + 1) / 2 * 100
    fig = create_gauge_chart(
        value=round(gauge_val, 1),
        title="Sentiment Score",
        min_val=0,
        max_val=100,
        ranges=[
            {"range": [0, 30], "color": "rgba(239, 68, 68, 0.3)"},
            {"range": [30, 45], "color": "rgba(245, 158, 11, 0.3)"},
            {"range": [45, 55], "color": "rgba(161, 161, 170, 0.2)"},
            {"range": [55, 70], "color": "rgba(59, 130, 246, 0.3)"},
            {"range": [70, 100], "color": "rgba(16, 185, 129, 0.3)"},
        ],
        height=220,
    )
    st.plotly_chart(fig, use_container_width=True)

with g2:
    st.metric("Raw Score", f"{agg_score:+.3f}")
    st.metric("Confidence", format_percent(agg_conf * 100, include_sign=False))
    tw = agg.get("time_weighted_score", 0)
    st.metric("Time-Weighted", f"{tw:+.3f}")

with g3:
    if dist:
        fig = create_donut_chart(
            labels=["Positive", "Neutral", "Negative"],
            values=[dist.get("positive", 0), dist.get("neutral", 0), dist.get("negative", 0)],
            title="Sentiment Distribution",
            colors=[COLORS["success"], COLORS.get("text_muted", "#71717a"), COLORS["danger"]],
            height=220,
        )
        st.plotly_chart(fig, use_container_width=True)

with g4:
    if dist:
        st.metric("Positive", f"{dist.get('positive', 0)} ({dist.get('positive_pct', 0)}%)")
        st.metric("Neutral", f"{dist.get('neutral', 0)} ({dist.get('neutral_pct', 0)}%)")
        st.metric("Negative", f"{dist.get('negative', 0)} ({dist.get('negative_pct', 0)}%)")

st.markdown("<br>", unsafe_allow_html=True)

# ─── News Volume ────────────────────────────────────────────
section_header("News Volume")

v1, v2, v3, v4 = st.columns(4)
v1.metric("Last 24h", volume.get("last_24h", 0))
v2.metric("Last 48h", volume.get("last_48h", 0))
v3.metric("Last 7 Days", volume.get("last_7d", 0))
v4.metric("Avg Daily", volume.get("avg_daily", 0))

spike = volume.get("spike_detected", False)
assessment = volume.get("spike_assessment", "Normal news flow")
if spike:
    st.warning(f"Volume Spike Detected: {assessment}")
else:
    st.caption(assessment)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Sentiment Trend ────────────────────────────────────────
if trend.get("values"):
    section_header("Sentiment Trend")

    tc1, tc2 = st.columns([1, 3])
    with tc1:
        direction = trend.get("direction", "Stable")
        momentum = trend.get("momentum", "No clear trend")
        if "Improving" in direction:
            dir_color = COLORS["success"]
        elif "Deteriorating" in direction:
            dir_color = COLORS["danger"]
        else:
            dir_color = COLORS["text_muted"]
        st.markdown(f"""
        <div style="padding: 1rem; background: {COLORS['bg_card']}; border-radius: 8px; border: 1px solid {COLORS['border']};">
            <div style="font-size: 0.75rem; color: {COLORS['text_muted']};">Direction</div>
            <div style="font-size: 1.1rem; font-weight: 600; color: {dir_color};">{direction}</div>
            <div style="font-size: 0.75rem; color: {COLORS['text_muted']}; margin-top: 0.75rem;">Momentum</div>
            <div style="font-size: 0.85rem; color: {COLORS['text_secondary']};">{momentum}</div>
        </div>
        """, unsafe_allow_html=True)

    with tc2:
        fig = create_line_chart(
            dates=trend.get("dates", []),
            values=trend.get("values", []),
            title="Daily Average Sentiment Score",
            fill=True,
            height=280,
            y_suffix="",
            show_zero_line=True,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ─── Topics & Source Diversity ──────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    if topics:
        section_header("Key Topics")
        labels = [t["topic"].replace("_", " ").title() for t in topics]
        values = [t["mentions"] for t in topics]
        colors = [COLORS.get("accent_primary", "#6366f1")] * len(labels)
        fig = create_horizontal_bar(
            labels=labels,
            values=values,
            title="Topic Frequency",
            colors=colors,
        )
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    if sources.get("source_breakdown"):
        section_header("Source Diversity")
        breakdown = sources["source_breakdown"]
        fig = create_donut_chart(
            labels=list(breakdown.keys()),
            values=list(breakdown.values()),
            title=f"{sources.get('unique_sources', 0)} Unique Sources",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(sources.get("assessment", ""))

st.markdown("<br>", unsafe_allow_html=True)

# ─── Top Articles ───────────────────────────────────────────
section_header("Top Positive Articles")
top_pos = result.get("top_positive", [])
if top_pos:
    for article in top_pos[:3]:
        sent = article.get("sentiment", {})
        score = sent.get("score", 0)
        label = sent.get("label", "Neutral")
        conf = sent.get("confidence", 0)
        title = article.get("title", "Untitled")
        source = article.get("source", "")
        pub = article.get("published_at", "")
        url = article.get("url", "")

        score_color = COLORS["success"] if score > 0 else COLORS["danger"] if score < 0 else COLORS["text_muted"]
        link = f'<a href="{url}" target="_blank" style="color: {COLORS["text_primary"]}; text-decoration: none;">{title}</a>' if url else title

        st.markdown(f"""
        <div style="padding: 0.75rem 1rem; background: {COLORS['bg_card']}; border-radius: 8px;
                    border: 1px solid {COLORS['border']}; margin-bottom: 0.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <div style="font-size: 0.85rem; font-weight: 500;">{link}</div>
                    <div style="font-size: 0.7rem; color: {COLORS['text_muted']}; margin-top: 4px;">
                        {source} · {format_date(pub)}
                    </div>
                </div>
                <div style="text-align: right; min-width: 100px; margin-left: 1rem;">
                    <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: {score_color};">
                        {score:+.3f}
                    </span>
                    <div style="font-size: 0.65rem; color: {COLORS['text_muted']};">{label} · {conf:.0%} conf</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.caption("No positive articles found.")

st.markdown("<br>", unsafe_allow_html=True)

top_neg = result.get("top_negative", [])
if top_neg:
    section_header("Top Negative Articles")
    for article in top_neg[:3]:
        sent = article.get("sentiment", {})
        score = sent.get("score", 0)
        label = sent.get("label", "Neutral")
        conf = sent.get("confidence", 0)
        title = article.get("title", "Untitled")
        source = article.get("source", "")
        pub = article.get("published_at", "")
        url = article.get("url", "")

        score_color = COLORS["success"] if score > 0 else COLORS["danger"] if score < 0 else COLORS["text_muted"]
        link = f'<a href="{url}" target="_blank" style="color: {COLORS["text_primary"]}; text-decoration: none;">{title}</a>' if url else title

        st.markdown(f"""
        <div style="padding: 0.75rem 1rem; background: {COLORS['bg_card']}; border-radius: 8px;
                    border: 1px solid {COLORS['border']}; margin-bottom: 0.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <div style="font-size: 0.85rem; font-weight: 500;">{link}</div>
                    <div style="font-size: 0.7rem; color: {COLORS['text_muted']}; margin-top: 4px;">
                        {source} · {format_date(pub)}
                    </div>
                </div>
                <div style="text-align: right; min-width: 100px; margin-left: 1rem;">
                    <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: {score_color};">
                        {score:+.3f}
                    </span>
                    <div style="font-size: 0.65rem; color: {COLORS['text_muted']};">{label} · {conf:.0%} conf</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── All Scored Articles ────────────────────────────────────
all_articles = result.get("scored_articles", [])
if all_articles:
    section_header(f"All Scored Articles ({len(all_articles)})")

    for article in all_articles:
        sent = article.get("sentiment", {})
        score = sent.get("score", 0)
        label = sent.get("label", "Neutral")
        title = article.get("title", "Untitled")
        source = article.get("source", "")
        pub = article.get("published_at", "")
        url = article.get("url", "")

        if score >= 0.15:
            badge_bg = "rgba(34, 197, 94, 0.15)"
            badge_color = COLORS["success"]
        elif score <= -0.15:
            badge_bg = "rgba(239, 68, 68, 0.15)"
            badge_color = COLORS["danger"]
        else:
            badge_bg = "rgba(161, 161, 170, 0.1)"
            badge_color = COLORS["text_muted"]

        link = f'<a href="{url}" target="_blank" style="color: {COLORS["text_primary"]}; text-decoration: none;">{title}</a>' if url else title

        st.markdown(f"""
        <div style="padding: 0.6rem 1rem; border-bottom: 1px solid {COLORS['border']}; display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 600;
                         color: {badge_color}; background: {badge_bg}; padding: 2px 8px; border-radius: 4px; min-width: 55px; text-align: center;">
                {score:+.2f}
            </span>
            <div style="flex: 1;">
                <div style="font-size: 0.8rem;">{link}</div>
                <div style="font-size: 0.65rem; color: {COLORS['text_muted']};">{source} · {format_date(pub)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─── Footer ─────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align: center; padding: 1rem; border-top: 1px solid {COLORS['border']};">
    <p style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: {COLORS['text_muted']};">
        Sentiment powered by {engine_label} · News from Yahoo Finance · Sentiment scores range from -1 (bearish) to +1 (bullish)
    </p>
</div>
""", unsafe_allow_html=True)
