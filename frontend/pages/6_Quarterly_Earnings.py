"""
Quarterly Earnings Analysis - EPS tracking, beat/miss patterns, quality scoring.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_css
from utils.session import init_session_state
from utils.formatters import format_currency, format_large_number, format_number, format_date, format_percent
from utils.data_service import analyze_earnings, compare_earnings
from components.header import render_header
from components.plotly_charts import create_gauge_chart, create_earnings_surprise_chart, create_horizontal_bar
from components.metrics_cards import render_score_badge

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(page_title="Quarterly Earnings | FinancialAI", page_icon=":chart_with_upwards_trend:", layout="wide", initial_sidebar_state="collapsed")
inject_css()
init_session_state()
render_header()

st.markdown("## Quarterly Earnings Analysis")
st.caption("Track EPS beats/misses, trends, and earnings quality")

# ─── Mode Toggle ─────────────────────────────────────────────
mode = st.radio("Mode", ["Single Company", "Compare Companies"], horizontal=True, label_visibility="collapsed")

if mode == "Single Company":
    # ─── Single Analysis ─────────────────────────────────────
    c1, c2 = st.columns([2, 1])
    with c1:
        symbol = st.text_input(
            "Stock Symbol",
            value=st.session_state.get("selected_symbol", "AAPL"),
            placeholder="e.g. AAPL",
            key="earnings_symbol",
        ).upper().strip()
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze = st.button("Analyze Earnings", use_container_width=True)

    if not symbol:
        st.info("Enter a stock symbol to analyze earnings.")
        st.stop()

    if analyze or symbol:
        with st.spinner(f"Analyzing earnings for {symbol}..."):
            result = analyze_earnings(symbol)

        if "error" in result:
            st.error(f"Error: {result['error']}")
            st.stop()

        # ─── Header ─────────────────────────────────────────
        name = result.get("name", symbol)
        next_earnings = result.get("next_earnings", {})

        header_parts = [f"**{name}** ({symbol})"]
        if next_earnings and next_earnings.get("date"):
            days = next_earnings.get("days_until")
            date_str = format_date(next_earnings.get("date"))
            if days is not None:
                header_parts.append(f"Next Earnings: **{date_str}** ({days} days)")
            else:
                header_parts.append(f"Next Earnings: **{date_str}**")

        st.markdown(" &middot; ".join(header_parts))

        st.markdown("---")

        # ─── KPI Row ────────────────────────────────────────
        surprise_hist = result.get("earnings_surprise_history", {}).get("last_8_quarters", {})
        quality = result.get("earnings_quality", {})

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Beat Rate", surprise_hist.get("beat_rate", "N/A"))
        c2.metric("Avg Surprise", surprise_hist.get("average_surprise", "N/A"))
        c3.metric("Quality Score", f"{quality.get('score', 0):.1f}/10")
        c4.metric("Pattern", surprise_hist.get("pattern", "N/A"))

        st.markdown("---")

        # ─── Last 4 Quarters Table ──────────────────────────
        st.markdown("### Quarterly Results")

        quarters = result.get("last_4_quarters", [])
        if quarters:
            rows = []
            q_labels = []
            surprises = []
            verdicts = []

            for q in quarters:
                verdict = q.get("verdict", "N/A")
                surprise = q.get("eps_surprise_pct", 0) or 0
                q_label = q.get("quarter", "")

                rows.append({
                    "Quarter": q_label,
                    "Date": format_date(q.get("date")),
                    "Revenue": format_large_number(q.get("revenue_actual")),
                    "Net Income": format_large_number(q.get("net_income")),
                    "EPS Actual": format_currency(q.get("eps_actual"), 2) if q.get("eps_actual") else "--",
                    "EPS Estimate": format_currency(q.get("eps_estimate"), 2) if q.get("eps_estimate") else "--",
                    "Surprise %": format_percent(surprise),
                    "Verdict": verdict,
                })

                q_labels.append(q_label)
                surprises.append(float(surprise) if isinstance(surprise, (int, float)) else 0)
                verdicts.append(verdict)

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # EPS Surprise Chart
            if q_labels and surprises:
                fig = create_earnings_surprise_chart(q_labels, surprises, verdicts, height=280)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ─── Quarterly Trends ────────────────────────────────
        st.markdown("### Quarterly Trends")

        trends = result.get("quarterly_trends", {})

        c1, c2, c3 = st.columns(3)
        c1.metric("Revenue Trend", trends.get("revenue_trend", "N/A"))
        c2.metric("Income Trend", trends.get("income_trend", "N/A"))
        c3.metric("Margin Trajectory", trends.get("margin_trajectory", "N/A"))

        # Revenue QoQ
        rev_qoq = trends.get("revenue_qoq_growth", [])
        if rev_qoq:
            st.markdown("**Revenue QoQ Growth**")
            for i, val in enumerate(rev_qoq):
                color = "#10b981" if "+" in str(val) else "#ef4444" if "-" in str(val) else "#9ca3af"
                st.markdown(f"Q{i+1}: <span style='color:{color}; font-family: JetBrains Mono;'>{val}</span>", unsafe_allow_html=True)

        # Gross margins by quarter
        gm_q = trends.get("gross_margins_by_quarter", [])
        if gm_q:
            st.markdown("**Gross Margins by Quarter**")
            for i, val in enumerate(gm_q):
                st.markdown(f"Q{i+1}: `{val}`")

        st.markdown("---")

        # ─── YoY Comparison ──────────────────────────────────
        yoy = result.get("yoy_comparison", {})
        if yoy:
            st.markdown("### Year-over-Year Comparison")
            c1, c2, c3 = st.columns(3)
            c1.metric("Period", yoy.get("comparison_period", "N/A"))
            c2.metric("Revenue Growth", yoy.get("revenue_growth", "N/A"))
            c3.metric("Net Income Growth", yoy.get("net_income_growth", "N/A"))

        st.markdown("---")

        # ─── Earnings Quality ────────────────────────────────
        st.markdown("### Earnings Quality")

        c1, c2 = st.columns([1, 2])

        with c1:
            score = quality.get("score", 0)
            fig = create_gauge_chart(
                value=round(score, 1),
                title="Quality Score",
                min_val=0,
                max_val=10,
                ranges=[
                    {"range": [0, 3], "color": "rgba(239, 68, 68, 0.3)"},
                    {"range": [3, 5], "color": "rgba(245, 158, 11, 0.3)"},
                    {"range": [5, 7], "color": "rgba(59, 130, 246, 0.3)"},
                    {"range": [7, 10], "color": "rgba(16, 185, 129, 0.3)"},
                ],
                suffix="/10",
                height=230,
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            assessment = quality.get("assessment", "")
            if assessment:
                badge = "bullish" if "high" in assessment.lower() else "bearish" if "low" in assessment.lower() else "neutral"
                st.markdown(f'<span class="score-badge {badge}" style="font-size: 1rem;">{assessment}</span>', unsafe_allow_html=True)

            factors = quality.get("factors", [])
            if factors:
                st.markdown("**Quality Factors:**")
                for f in factors:
                    st.markdown(f"- {f}")

        # ─── Next Earnings ───────────────────────────────────
        if next_earnings and next_earnings.get("date"):
            st.markdown("---")
            st.markdown("### Next Earnings")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Date", format_date(next_earnings.get("date")))
            c2.metric("Days Until", next_earnings.get("days_until", "N/A"))
            c3.metric("EPS Estimate", format_currency(next_earnings.get("eps_estimate"), 2) if next_earnings.get("eps_estimate") else "N/A")
            c4.metric("Analysts", next_earnings.get("number_of_analysts", "N/A"))

else:
    # ─── Compare Mode ────────────────────────────────────────
    st.markdown("### Compare Earnings Profiles")

    symbols_input = st.text_input(
        "Enter symbols (comma-separated, 2-10)",
        placeholder="e.g. AAPL, MSFT, GOOGL",
        key="earnings_compare_input",
    )

    if symbols_input:
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

        if len(symbols) < 2:
            st.warning("Enter at least 2 symbols to compare.")
            st.stop()

        with st.spinner("Comparing earnings profiles..."):
            result = compare_earnings(tuple(symbols))

        if "error" in result:
            st.error(f"Error: {result['error']}")
            st.stop()

        comparison = result.get("comparison", [])
        if comparison:
            df = pd.DataFrame(comparison)
            column_order = ["symbol", "name", "beat_rate", "average_surprise", "pattern",
                           "revenue_trend", "income_trend", "earnings_quality_score", "next_earnings_date"]
            existing_cols = [c for c in column_order if c in df.columns]
            df = df[existing_cols]

            if "earnings_quality_score" in df.columns:
                df = df.sort_values("earnings_quality_score", ascending=False)

            st.dataframe(df, use_container_width=True, hide_index=True)

            # Quality score ranking
            labels = [c.get("symbol", "?") for c in comparison]
            scores = [c.get("earnings_quality_score", 0) or 0 for c in comparison]
            sorted_pairs = sorted(zip(labels, scores), key=lambda x: x[1], reverse=True)
            if sorted_pairs:
                labels, scores = zip(*sorted_pairs)
                colors = ["#10b981" if s >= 7 else "#3b82f6" if s >= 5 else "#f59e0b" if s >= 3 else "#ef4444" for s in scores]

                fig = create_horizontal_bar(
                    list(labels), list(scores),
                    title="Earnings Quality Score Ranking",
                    colors=list(colors),
                )
                st.plotly_chart(fig, use_container_width=True)

            best = result.get("best_earnings_quality")
            if best:
                st.success(f"Best earnings quality: **{best}**")
    else:
        st.info("Enter comma-separated symbols above to compare earnings profiles.")
