"""
Reusable metric cards, KPI rows, score badges, and strength/weakness displays.
"""

import streamlit as st


def render_kpi_row(metrics: list):
    """
    Render a row of KPI metric cards using st.metric.

    Args:
        metrics: List of dicts with keys: label, value, delta (optional), delta_color (optional)
                 delta_color can be "normal" (green=up), "inverse" (red=up), or "off"
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        col.metric(
            label=m.get("label", ""),
            value=m.get("value", "--"),
            delta=m.get("delta"),
            delta_color=m.get("delta_color", "normal"),
        )


def render_score_badge(label: str, score, classification: str = "", badge_class: str = "neutral"):
    """
    Render a styled score badge using HTML.

    Args:
        label: Score label (e.g., "Disruption Score")
        score: Numeric score value
        classification: Text classification (e.g., "Active Disruptor")
        badge_class: CSS class - bullish/bearish/neutral/buy/sell/hold
    """
    st.markdown(
        f"""
        <div style="text-align: center; margin: 0.5rem 0;">
            <div style="font-size: 0.75rem; color: #9ca3af; text-transform: uppercase;
                        letter-spacing: 0.08em; font-weight: 600; margin-bottom: 0.25rem;">
                {label}
            </div>
            <div style="font-size: 2.5rem; font-weight: 800; font-family: 'JetBrains Mono', monospace;
                        color: #f9fafb; margin-bottom: 0.25rem;">
                {score}
            </div>
            <span class="score-badge {badge_class}">{classification}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_company_header(symbol: str, name: str, price: float, change_pct: float, market_cap: str = "", sector: str = ""):
    """Render a company header bar with price and key info."""
    change_class = "change-positive" if change_pct >= 0 else "change-negative"
    change_sign = "+" if change_pct >= 0 else ""

    meta_parts = []
    if sector:
        meta_parts.append(sector)
    if market_cap:
        meta_parts.append(f"MCap: {market_cap}")
    meta_html = " &middot; ".join(meta_parts)

    st.markdown(
        f"""
        <div class="kpi-header">
            <div>
                <div class="symbol">{symbol}</div>
                <div class="company-name">{name}</div>
                <div style="font-size: 0.75rem; color: #6b7280; margin-top: 0.25rem;">{meta_html}</div>
            </div>
            <div style="text-align: right; margin-left: auto;">
                <div class="price">${price:,.2f}</div>
                <span class="{change_class}">{change_sign}{change_pct:.2f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_strength_weakness(strengths: list, weaknesses: list):
    """Render strength and weakness cards side by side."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Strengths**")
        if strengths:
            for s in strengths:
                st.markdown(f'<div class="strength-item">{s}</div>', unsafe_allow_html=True)
        else:
            st.caption("No notable strengths identified.")

    with col2:
        st.markdown("**Risk Factors**")
        if weaknesses:
            for w in weaknesses:
                st.markdown(f'<div class="weakness-item">{w}</div>', unsafe_allow_html=True)
        else:
            st.caption("No notable weaknesses identified.")


def render_news_card(
    title: str,
    source: str = "",
    date: str = "",
    description: str = "",
    url: str = "",
    thumbnail: str = "",
    content_type: str = "",
):
    """Render a news article card with optional thumbnail and type badge."""
    meta_parts = [p for p in [source, date] if p]
    meta = " &middot; ".join(meta_parts)

    title_html = (
        f'<a href="{url}" target="_blank" style="color: inherit; text-decoration: none;">{title}</a>'
        if url else title
    )

    thumb_html = ""
    if thumbnail:
        thumb_html = (
            f'<img src="{thumbnail}" alt="" '
            f'style="width: 100%; height: 120px; object-fit: cover; border-radius: 0.5rem; margin-bottom: 0.5rem;" '
            f'onerror="this.style.display=\'none\'" />'
        )

    type_badge = ""
    if content_type:
        ct = content_type.upper()
        if ct == "VIDEO":
            type_badge = '<span style="display: inline-block; font-size: 0.6rem; padding: 0.15rem 0.5rem; border-radius: 999px; background: rgba(139, 92, 246, 0.15); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.25); font-weight: 600; margin-right: 0.375rem; vertical-align: middle;">VIDEO</span>'
        elif ct == "STORY":
            type_badge = '<span style="display: inline-block; font-size: 0.6rem; padding: 0.15rem 0.5rem; border-radius: 999px; background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.25); font-weight: 600; margin-right: 0.375rem; vertical-align: middle;">ARTICLE</span>'

    desc_html = ""
    if description and len(description) > 10:
        # Truncate cleanly at word boundary
        desc = description[:200]
        if len(description) > 200:
            desc = desc[:desc.rfind(" ")] + "..."
        desc_html = f"<div class='news-desc'>{desc}</div>"

    st.markdown(
        f"""
        <div class="news-card">
            {thumb_html}
            <div class="news-title">{type_badge}{title_html}</div>
            <div class="news-meta">{meta}</div>
            {desc_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
