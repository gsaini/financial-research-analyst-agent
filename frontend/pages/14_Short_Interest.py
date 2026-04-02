"""
Short Interest Analysis - Short squeeze scoring, days to cover,
historical context, and risk assessment for longs and shorts.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_css, COLORS
from utils.session import init_session_state
from utils.formatters import format_percent, format_large_number
from utils.data_service import get_short_interest, compare_short_interest, get_squeeze_watchlist
from components.header import render_header
from components.plotly_charts import create_gauge_chart, create_horizontal_bar

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Short Interest | FinancialAI",
    page_icon=":chart_with_downwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## Short Interest Analysis")
st.caption("Track short selling activity, squeeze scoring, and risk assessment")

# ─── Tabs ────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Single Stock", "Compare", "Squeeze Watchlist"])

# ─── Tab 1: Single Stock ────────────────────────────────────
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input(
            "Stock Symbol",
            value=st.session_state.get("selected_symbol", "GME"),
            placeholder="Enter ticker (e.g., GME, AMC, TSLA)",
            key="si_symbol",
        ).strip().upper()
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("Analyze", use_container_width=True, type="primary", key="si_btn")

    if analyze_btn and symbol:
        st.session_state.si_active = symbol

    active = st.session_state.get("si_active", "")
    if active:
        with st.spinner(f"Analyzing short interest for {active}..."):
            data = get_short_interest(active)

        if "error" in data:
            st.error(f"Analysis failed: {data['error']}")
        else:
            si = data.get("short_interest", {})
            sq = data.get("squeeze_analysis", {})
            hist = data.get("historical_context", {})
            borrow = data.get("borrow_data", {})
            risk = data.get("risk_assessment", {})
            price = data.get("current_price", 0)

            # ── Header metrics ──
            st.markdown(f"### {data.get('company_name', active)} ({active})")
            st.markdown(f"**Current Price:** ${price:.2f}")

            mcols = st.columns(4)
            with mcols[0]:
                st.metric(
                    "Short % of Float",
                    f"{si.get('short_percent_of_float', 0):.1f}%",
                    delta=f"{si.get('change_vs_previous_pct', 0):+.1f}% MoM",
                )
            with mcols[1]:
                st.metric("Shares Short", si.get("shares_short_formatted", "N/A"))
            with mcols[2]:
                st.metric("Days to Cover", f"{si.get('short_ratio_days_to_cover', 0):.1f}")
            with mcols[3]:
                st.metric("Squeeze Score", f"{sq.get('squeeze_score', 0)}/100")

            st.markdown("---")

            # ── Squeeze Analysis ──
            scol1, scol2 = st.columns([1, 2])

            with scol1:
                score = sq.get("squeeze_score", 0)
                risk_level = sq.get("risk_level", "Low")
                color = (
                    COLORS.get("danger", "#ef4444") if risk_level == "High"
                    else COLORS.get("warning", "#eab308") if risk_level == "Elevated"
                    else COLORS.get("success", "#22c55e")
                )
                st.markdown(f"""
                <div style="text-align:center; padding:20px; border-radius:8px; border:1px solid {color};">
                    <div style="font-size:3em; font-weight:bold; color:{color};">{score}</div>
                    <div style="font-size:0.9em; color:{COLORS.get('text_secondary', '#a1a1aa')};">Squeeze Score</div>
                    <div style="font-size:1.2em; color:{color}; font-weight:bold; margin-top:4px;">{risk_level}</div>
                </div>
                """, unsafe_allow_html=True)

            with scol2:
                st.markdown("**Squeeze Factor Breakdown**")
                factors = sq.get("factors", {})
                factor_df = pd.DataFrame([
                    {"Factor": "Short % of Float", "Score": factors.get("short_percent_score", 0)},
                    {"Factor": "Days to Cover", "Score": factors.get("days_to_cover_score", 0)},
                    {"Factor": "Short Interest Trend", "Score": factors.get("recent_increase_score", 0)},
                    {"Factor": "Borrow Cost", "Score": factors.get("borrow_cost_score", 0)},
                ])
                st.bar_chart(factor_df.set_index("Factor"), color=COLORS.get("accent_primary", "#6366f1"))

            st.markdown(f"**Assessment:** {sq.get('assessment', '')}")

            st.markdown("---")

            # ── Context + Borrow ──
            ccol1, ccol2 = st.columns(2)

            with ccol1:
                st.markdown("**Historical Context**")
                st.markdown(f"- **Market Percentile:** {hist.get('market_percentile', 'N/A')}th — {hist.get('percentile_label', '')}")
                st.markdown(f"- **Trend:** {hist.get('trend', 'N/A').title()}")
                st.markdown(f"- **Prior Month Shares Short:** {si.get('previous_month_formatted', 'N/A')}")
                st.markdown(f"- **MoM Change:** {si.get('change_vs_previous_pct', 0):+.1f}%")

            with ccol2:
                st.markdown("**Borrow Data (Estimated)**")
                st.markdown(f"- **Est. Borrow Rate:** {borrow.get('estimated_borrow_rate_pct', 0):.1f}%")
                st.markdown(f"- **Assessment:** {borrow.get('borrow_assessment', 'N/A')}")
                st.caption(borrow.get("note", ""))

            st.markdown("---")

            # ── Risk Assessment ──
            st.markdown("**Risk Assessment**")
            rcol1, rcol2 = st.columns(2)
            with rcol1:
                st.markdown("**For Long Positions:**")
                st.info(risk.get("for_longs", "N/A"))
            with rcol2:
                st.markdown("**For Short Positions:**")
                st.warning(risk.get("for_shorts", "N/A"))

            catalysts = risk.get("catalyst_watch", [])
            if catalysts:
                st.markdown("**Catalyst Watch:**")
                for c in catalysts:
                    st.markdown(f"- {c}")

            st.caption(data.get("data_freshness", ""))

# ─── Tab 2: Compare ──────────────────────────────────────────
with tab2:
    symbols_input = st.text_input(
        "Compare Symbols (comma-separated)",
        value="GME, AMC, TSLA, RIVN, NIO",
        placeholder="e.g., GME, AMC, TSLA",
        key="si_compare_input",
    )
    compare_btn = st.button("Compare Short Interest", key="si_compare_btn", type="primary")

    if compare_btn and symbols_input:
        symbols = tuple(s.strip().upper() for s in symbols_input.split(",") if s.strip())
        if len(symbols) < 2:
            st.warning("Enter at least 2 symbols.")
        else:
            with st.spinner("Comparing short interest..."):
                result = compare_short_interest(symbols)

            if "error" in result:
                st.error(result["error"])
            else:
                ranking = result.get("ranking", [])
                if ranking:
                    st.markdown("### Squeeze Risk Ranking")
                    rank_df = pd.DataFrame(ranking)
                    st.dataframe(
                        rank_df.style.background_gradient(subset=["squeeze_score"], cmap="YlOrRd"),
                        use_container_width=True,
                        hide_index=True,
                    )

                # Detail per stock
                individual = result.get("individual", {})
                for sym, data in individual.items():
                    if "error" in data:
                        continue
                    with st.expander(f"{sym} — Squeeze Score: {data.get('squeeze_analysis', {}).get('squeeze_score', 0)}"):
                        si = data.get("short_interest", {})
                        st.markdown(
                            f"**Short % Float:** {si.get('short_percent_of_float', 0):.1f}% | "
                            f"**Days to Cover:** {si.get('short_ratio_days_to_cover', 0):.1f} | "
                            f"**MoM Change:** {si.get('change_vs_previous_pct', 0):+.1f}% | "
                            f"**Risk:** {data.get('squeeze_analysis', {}).get('risk_level', 'N/A')}"
                        )

# ─── Tab 3: Squeeze Watchlist ────────────────────────────────
with tab3:
    st.markdown("### Short Squeeze Screening")
    st.caption("Scanning popular stocks for short squeeze candidates")

    min_score = st.slider("Minimum Squeeze Score", 0, 100, 50, 5, key="si_min_score")
    scan_btn = st.button("Scan for Squeeze Candidates", key="si_scan_btn", type="primary")

    if scan_btn:
        with st.spinner("Screening stocks for short squeeze potential..."):
            result = get_squeeze_watchlist(min_score)

        if "error" in result:
            st.error(result["error"])
        else:
            candidates = result.get("candidates", [])
            st.markdown(f"**Found {len(candidates)} candidates** from {result.get('screened', 0)} stocks scanned")

            if candidates:
                df = pd.DataFrame(candidates)
                st.dataframe(
                    df.style.background_gradient(subset=["squeeze_score"], cmap="YlOrRd"),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info(f"No stocks found with squeeze score >= {min_score}")

# ─── Footer ─────────────────────────────────────────────────
st.markdown("---")
st.caption("Short interest data is reported bi-monthly by exchanges with ~10 day delay. Squeeze scoring is for informational purposes only — not investment advice.")
