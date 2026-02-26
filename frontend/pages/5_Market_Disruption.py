"""
Market Disruption Analysis - Disruption scoring, classification, and comparison.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_css
from utils.session import init_session_state
from utils.formatters import format_currency, format_large_number, format_number
from utils.data_service import analyze_disruption, compare_disruption
from components.sidebar import render_sidebar
from components.plotly_charts import create_gauge_chart, create_horizontal_bar, create_grouped_bar
from components.metrics_cards import render_score_badge, render_strength_weakness
from components.data_tables import render_styled_dataframe

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(page_title="Market Disruption | FinancialAI", page_icon=":chart_with_upwards_trend:", layout="wide")
inject_css()
init_session_state()
render_sidebar()

st.markdown("## Market Disruption Analysis")
st.caption("Evaluate a company's innovation and disruption potential")

# ─── Mode Toggle ─────────────────────────────────────────────
mode = st.radio("Mode", ["Single Company", "Compare Companies"], horizontal=True, label_visibility="collapsed")

if mode == "Single Company":
    # ─── Single Analysis ─────────────────────────────────────
    c1, c2 = st.columns([2, 1])
    with c1:
        symbol = st.text_input(
            "Stock Symbol",
            value=st.session_state.get("selected_symbol", "NVDA"),
            placeholder="e.g. NVDA",
            key="disruption_symbol",
        ).upper().strip()
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze = st.button("Analyze Disruption", use_container_width=True)

    if not symbol:
        st.info("Enter a stock symbol to analyze its disruption profile.")
        st.stop()

    if analyze or symbol:
        with st.spinner(f"Analyzing disruption profile for {symbol}..."):
            result = analyze_disruption(symbol)

        if "error" in result:
            st.error(f"Error: {result['error']}")
            st.stop()

        # Company header
        st.markdown(
            f"**{result.get('name', symbol)}** &middot; "
            f"{result.get('sector', '')} &middot; {result.get('industry', '')} &middot; "
            f"MCap: {format_large_number(result.get('financial_summary', {}).get('market_cap'))}"
        )

        st.markdown("---")

        # ─── Disruption Score Hero ───────────────────────────
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            score = result.get("disruption_score", 0)
            classification = result.get("classification", "Unknown")

            # Classification badge class
            cls_map = {
                "Active Disruptor": "disruptor",
                "Moderate Innovator": "innovator",
                "Stable Incumbent": "incumbent",
                "At Risk": "at-risk",
            }
            badge_cls = cls_map.get(classification, "neutral")

            fig = create_gauge_chart(
                value=score,
                title="Disruption Score",
                ranges=[
                    {"range": [0, 30], "color": "rgba(239, 68, 68, 0.25)"},
                    {"range": [30, 50], "color": "rgba(245, 158, 11, 0.25)"},
                    {"range": [50, 70], "color": "rgba(59, 130, 246, 0.25)"},
                    {"range": [70, 100], "color": "rgba(16, 185, 129, 0.25)"},
                ],
                height=280,
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown(
                f'<div style="text-align: center;"><span class="classification-badge {badge_cls}">{classification}</span></div>',
                unsafe_allow_html=True,
            )
            desc = result.get("classification_description", "")
            if desc:
                st.caption(desc)

        # ─── Score Components ────────────────────────────────
        st.markdown("---")
        st.markdown("### Score Components")

        components_data = result.get("score_components", {})
        weights = result.get("score_weights", {})

        c1, c2, c3 = st.columns(3)

        with c1:
            rd_score = components_data.get("rd_score", 0)
            weight = weights.get("rd_intensity", 0.35)
            fig = create_gauge_chart(rd_score, f"R&D Intensity ({weight*100:.0f}%)", height=200)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            growth_score = components_data.get("growth_score", 0)
            weight = weights.get("revenue_acceleration", 0.40)
            fig = create_gauge_chart(growth_score, f"Revenue Growth ({weight*100:.0f}%)", height=200)
            st.plotly_chart(fig, use_container_width=True)

        with c3:
            margin_score = components_data.get("margin_score", 0)
            weight = weights.get("margin_trajectory", 0.25)
            fig = create_gauge_chart(margin_score, f"Margin Trajectory ({weight*100:.0f}%)", height=200)
            st.plotly_chart(fig, use_container_width=True)

        # ─── Quantitative Signals ────────────────────────────
        st.markdown("---")
        st.markdown("### Quantitative Signals")

        signals = result.get("quantitative_signals", {})

        # R&D Intensity
        rd = signals.get("rd_intensity", {})
        if rd:
            with st.expander("R&D Intensity", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("R&D / Revenue", rd.get("rd_to_revenue_ratio", "N/A"))
                c2.metric("Trend", rd.get("trend", "N/A"))
                c3.metric("vs Industry", rd.get("vs_industry_multiple", "N/A"))

                # R&D trend chart
                ratios = rd.get("rd_ratios_by_year", [])
                if ratios:
                    fig = create_horizontal_bar(
                        labels=[f"Year {i+1}" for i in range(len(ratios))],
                        values=[r * 100 for r in ratios],
                        title="R&D / Revenue by Year (%)",
                        colors=["#3b82f6"] * len(ratios),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                assessment = rd.get("assessment", "")
                if assessment:
                    st.info(assessment)

        # Revenue Acceleration
        rev = signals.get("revenue_acceleration", {})
        if rev:
            with st.expander("Revenue Acceleration", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("YoY Growth", rev.get("yoy_growth", "N/A"))
                c2.metric("CAGR", rev.get("cagr", "N/A"))
                c3.metric("Trajectory", rev.get("trajectory", "N/A"))

                growth_rates = rev.get("growth_rates_by_year", [])
                if growth_rates:
                    colors = ["#10b981" if g >= 0 else "#ef4444" for g in growth_rates]
                    fig = create_horizontal_bar(
                        labels=[f"Year {i+1}" for i in range(len(growth_rates))],
                        values=[g * 100 for g in growth_rates],
                        title="Revenue Growth by Year (%)",
                        colors=colors,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                assessment = rev.get("assessment", "")
                if assessment:
                    st.info(assessment)

        # Margin Trajectory
        margin = signals.get("gross_margin_trajectory", {})
        if margin:
            with st.expander("Gross Margin Trajectory", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Gross Margin", margin.get("current_gross_margin", "N/A"))
                c2.metric("Op Margin", margin.get("current_operating_margin", "N/A"))
                c3.metric("Trend", margin.get("trend", "N/A"))

                gm_by_year = margin.get("gross_margins_by_year", [])
                if gm_by_year:
                    fig = create_horizontal_bar(
                        labels=[f"Year {i+1}" for i in range(len(gm_by_year))],
                        values=[g * 100 for g in gm_by_year],
                        title="Gross Margin by Year (%)",
                        colors=["#8b5cf6"] * len(gm_by_year),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                assessment = margin.get("assessment", "")
                if assessment:
                    st.info(assessment)

        # ─── Strengths & Risk Factors ────────────────────────
        st.markdown("---")
        render_strength_weakness(
            strengths=result.get("strengths", []),
            weaknesses=result.get("risk_factors", []),
        )

else:
    # ─── Compare Mode ────────────────────────────────────────
    st.markdown("### Compare Disruption Profiles")

    symbols_input = st.text_input(
        "Enter symbols (comma-separated, 2-10)",
        placeholder="e.g. NVDA, MSFT, AAPL, AMZN",
        key="disruption_compare_input",
    )

    if symbols_input:
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

        if len(symbols) < 2:
            st.warning("Enter at least 2 symbols to compare.")
            st.stop()

        with st.spinner("Comparing disruption profiles..."):
            result = compare_disruption(tuple(symbols))

        if "error" in result:
            st.error(f"Error: {result['error']}")
            st.stop()

        comparison = result.get("comparison", [])
        if comparison:
            # Comparison table
            df = pd.DataFrame(comparison)
            column_order = ["symbol", "name", "industry", "disruption_score", "classification",
                           "rd_intensity", "revenue_growth", "margin_trend"]
            existing_cols = [c for c in column_order if c in df.columns]
            df = df[existing_cols]
            df = df.sort_values("disruption_score", ascending=False)

            st.dataframe(df, use_container_width=True, hide_index=True)

            # Visual comparison
            if len(comparison) > 0:
                labels = [c.get("symbol", "?") for c in comparison]
                scores = [c.get("disruption_score", 0) for c in comparison]
                # Sort by score
                sorted_pairs = sorted(zip(labels, scores), key=lambda x: x[1], reverse=True)
                labels, scores = zip(*sorted_pairs)

                colors = []
                for s in scores:
                    if s >= 70:
                        colors.append("#10b981")
                    elif s >= 50:
                        colors.append("#3b82f6")
                    elif s >= 30:
                        colors.append("#f59e0b")
                    else:
                        colors.append("#ef4444")

                fig = create_horizontal_bar(
                    list(labels), list(scores),
                    title="Disruption Score Ranking",
                    colors=list(colors),
                )
                st.plotly_chart(fig, use_container_width=True)

            most = result.get("most_disruptive")
            if most:
                st.success(f"Most disruptive company: **{most}**")
    else:
        st.info("Enter comma-separated symbols above to compare disruption profiles.")
