"""
Dividend Analysis - Yield, safety scoring, growth history,
classification (King/Aristocrat), and yield comparison.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_css, COLORS
from utils.session import init_session_state
from utils.formatters import format_percent, format_currency
from utils.data_service import analyze_dividends, compare_dividends
from components.header import render_header
from components.plotly_charts import create_gauge_chart, create_horizontal_bar

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dividends | FinancialAI",
    page_icon=":moneybag:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## Dividend Analysis")
st.caption("Dividend safety scoring, growth tracking, yield comparison, and income investing insights")

# ─── Tabs ────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Single Stock", "Compare"])

# ─── Tab 1: Single Stock ────────────────────────────────────
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input(
            "Stock Symbol",
            value=st.session_state.get("selected_symbol", "JNJ"),
            placeholder="Enter ticker (e.g., JNJ, KO, PG)",
            key="div_symbol",
        ).strip().upper()
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("Analyze", use_container_width=True, type="primary", key="div_btn")

    if analyze_btn and symbol:
        st.session_state.div_active = symbol

    active = st.session_state.get("div_active", "")
    if active:
        with st.spinner(f"Analyzing dividends for {active}..."):
            data = analyze_dividends(active)

        if "error" in data:
            st.error(f"Analysis failed: {data['error']}")
        elif not data.get("pays_dividends", False):
            st.warning(data.get("message", f"{active} does not pay a dividend."))
        else:
            name = data.get("name", active)
            current = data.get("current_dividend", {})
            safety = data.get("dividend_safety", {})
            growth = data.get("dividend_growth", {})
            yields = data.get("yield_comparison", {})

            # ── Header ──
            st.markdown(f"### {name} ({active})")

            # ── Key Metrics Row ──
            mcols = st.columns(5)
            with mcols[0]:
                st.metric("Dividend Yield", f"{current.get('dividend_yield', 0):.2f}%")
            with mcols[1]:
                annual = current.get("annual_dividend", 0)
                st.metric("Annual Dividend", f"${annual:.2f}" if annual else "N/A")
            with mcols[2]:
                payout = current.get("payout_ratio")
                st.metric("Payout Ratio", f"{payout:.1f}%" if payout else "N/A")
            with mcols[3]:
                st.metric("Safety Score", f"{safety.get('safety_score', 0)}/100")
            with mcols[4]:
                yrs = growth.get("consecutive_years_increased", 0)
                st.metric("Years Increasing", str(yrs) if yrs else "N/A")

            st.markdown("---")

            # ── Safety + Classification ──
            scol1, scol2 = st.columns([1, 2])

            with scol1:
                score = safety.get("safety_score", 0)
                rating = safety.get("rating", "N/A")
                cut_prob = safety.get("dividend_cut_probability", "N/A")

                color = (
                    COLORS.get("success", "#22c55e") if score >= 70
                    else COLORS.get("warning", "#eab308") if score >= 40
                    else COLORS.get("danger", "#ef4444")
                )

                st.markdown(f"""
                <div style="text-align:center; padding:20px; border-radius:8px; border:1px solid {color};">
                    <div style="font-size:3em; font-weight:bold; color:{color};">{score}</div>
                    <div style="font-size:0.9em; color:{COLORS.get('text_secondary', '#a1a1aa')};">Safety Score</div>
                    <div style="font-size:1.1em; color:{color}; font-weight:bold; margin-top:4px;">{rating}</div>
                    <div style="font-size:0.85em; color:{COLORS.get('text_muted', '#71717a')}; margin-top:4px;">Cut probability: {cut_prob}</div>
                </div>
                """, unsafe_allow_html=True)

                # Classification badge
                classification = growth.get("classification", "")
                if classification:
                    badge_color = (
                        "#FFD700" if "King" in classification
                        else "#C0C0C0" if "Aristocrat" in classification
                        else "#CD7F32" if "Champion" in classification
                        else COLORS.get("accent_primary", "#6366f1")
                    )
                    st.markdown(f"""
                    <div style="text-align:center; margin-top:12px; padding:8px; border-radius:6px; background:{badge_color}20; border:1px solid {badge_color};">
                        <span style="color:{badge_color}; font-weight:bold;">{classification}</span>
                    </div>
                    """, unsafe_allow_html=True)

            with scol2:
                st.markdown("**Safety Factor Breakdown**")
                factors = safety.get("factors", {})
                if factors:
                    factor_rows = []
                    for factor_name, factor_data in factors.items():
                        if isinstance(factor_data, dict):
                            factor_rows.append({
                                "Factor": factor_name.replace("_", " ").title(),
                                "Value": factor_data.get("value", "N/A"),
                                "Assessment": factor_data.get("assessment", ""),
                            })
                    if factor_rows:
                        st.dataframe(pd.DataFrame(factor_rows), use_container_width=True, hide_index=True)

                # Red flags
                flags = safety.get("red_flags", [])
                if flags:
                    st.markdown("**Red Flags:**")
                    for flag in flags:
                        st.markdown(f"- {flag}")
                else:
                    st.success("No red flags detected")

            st.markdown("---")

            # ── Dividend Growth ──
            gcol1, gcol2 = st.columns(2)

            with gcol1:
                st.markdown("**Dividend Growth**")
                cagr_3 = growth.get("cagr_3_year")
                cagr_5 = growth.get("cagr_5_year")
                cagr_10 = growth.get("cagr_10_year")
                last_inc = growth.get("last_increase_pct")

                growth_data = []
                if cagr_3 is not None:
                    growth_data.append({"Period": "3-Year CAGR", "Growth": f"{cagr_3:.1f}%"})
                if cagr_5 is not None:
                    growth_data.append({"Period": "5-Year CAGR", "Growth": f"{cagr_5:.1f}%"})
                if cagr_10 is not None:
                    growth_data.append({"Period": "10-Year CAGR", "Growth": f"{cagr_10:.1f}%"})
                if last_inc is not None:
                    growth_data.append({"Period": "Last Increase", "Growth": f"{last_inc:.1f}%"})

                if growth_data:
                    st.dataframe(pd.DataFrame(growth_data), use_container_width=True, hide_index=True)

            with gcol2:
                st.markdown("**Yield Comparison**")
                stock_yield = yields.get("stock_yield", 0)
                sector_avg = yields.get("sector_average", 0)
                sp500_avg = yields.get("sp500_average", 0)
                treasury = yields.get("treasury_10y", 0)

                comparison_data = [
                    {"Benchmark": f"{active}", "Yield (%)": stock_yield or 0},
                    {"Benchmark": f"Sector Avg ({yields.get('sector', 'N/A')})", "Yield (%)": sector_avg or 0},
                    {"Benchmark": "S&P 500 Avg", "Yield (%)": sp500_avg or 0},
                    {"Benchmark": "10Y Treasury", "Yield (%)": treasury or 0},
                ]
                comp_df = pd.DataFrame(comparison_data)
                st.bar_chart(comp_df.set_index("Benchmark"), color=COLORS.get("accent_primary", "#6366f1"))

                assessment = yields.get("yield_assessment", "")
                if assessment:
                    st.caption(assessment)

            st.markdown("---")

            # ── Payment Details ──
            st.markdown("**Payment Details**")
            dcols = st.columns(4)
            with dcols[0]:
                st.markdown(f"**Frequency:** {current.get('frequency', 'N/A')}")
            with dcols[1]:
                st.markdown(f"**Last Payment:** ${current.get('last_payment_amount', 'N/A')}")
            with dcols[2]:
                st.markdown(f"**Ex-Dividend Date:** {current.get('ex_dividend_date', 'N/A')}")
            with dcols[3]:
                yrs = growth.get("consecutive_years_increased", 0)
                st.markdown(f"**Consecutive Increases:** {yrs} years")

# ─── Tab 2: Compare ──────────────────────────────────────────
with tab2:
    symbols_input = st.text_input(
        "Compare Symbols (comma-separated)",
        value="JNJ, KO, PG, PEP, ABBV",
        placeholder="e.g., JNJ, KO, PG, PEP, ABBV",
        key="div_compare_input",
    )
    compare_btn = st.button("Compare Dividends", key="div_compare_btn", type="primary")

    if compare_btn and symbols_input:
        symbols = tuple(s.strip().upper() for s in symbols_input.split(",") if s.strip())
        if len(symbols) < 2:
            st.warning("Enter at least 2 symbols.")
        else:
            with st.spinner("Comparing dividend profiles..."):
                result = compare_dividends(symbols)

            if "error" in result:
                st.error(result["error"])
            else:
                comparison = result.get("comparison", [])
                if comparison:
                    st.markdown("### Dividend Comparison")

                    # Build summary table
                    rows = []
                    for c in comparison:
                        if "error" in c:
                            continue
                        rows.append({
                            "Symbol": c.get("symbol", ""),
                            "Yield (%)": c.get("dividend_yield", 0),
                            "Safety Score": c.get("safety_score", 0),
                            "Payout Ratio (%)": c.get("payout_ratio", 0),
                            "Consec. Years": c.get("consecutive_years_increased", 0),
                            "Classification": c.get("classification", "N/A"),
                            "5Y CAGR (%)": c.get("cagr_5_year", 0),
                        })

                    if rows:
                        df = pd.DataFrame(rows)
                        st.dataframe(
                            df.style.background_gradient(
                                subset=["Safety Score"], cmap="YlGn"
                            ).background_gradient(
                                subset=["Yield (%)"], cmap="YlOrRd"
                            ),
                            use_container_width=True,
                            hide_index=True,
                        )

                    # Best picks
                    best = result.get("best_safety", {})
                    highest_yield = result.get("highest_yield", {})
                    if best:
                        st.markdown(
                            f"**Safest Dividend:** {best.get('symbol', 'N/A')} "
                            f"(Safety: {best.get('safety_score', 0)}/100)"
                        )
                    if highest_yield:
                        st.markdown(
                            f"**Highest Yield:** {highest_yield.get('symbol', 'N/A')} "
                            f"({highest_yield.get('dividend_yield', 0):.2f}%)"
                        )

# ─── Footer ─────────────────────────────────────────────────
st.markdown("---")
st.caption("Dividend data from Yahoo Finance. Safety scores are algorithmic estimates — not investment advice.")
