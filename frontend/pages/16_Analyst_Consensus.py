"""
Analyst Consensus Tracking - Rating distribution, price targets,
upgrades/downgrades, estimate revisions, and analyst signal scoring.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_css, COLORS
from utils.session import init_session_state
from utils.data_service import get_analyst_consensus, compare_analyst_consensus
from components.header import render_header

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Analyst Consensus | FinancialAI",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## Analyst Consensus Tracking")
st.caption("Wall Street ratings, price targets, estimate revisions, and upgrade/downgrade activity")

# ─── Tabs ────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Single Stock", "Compare"])

# ─── Tab 1: Single Stock ────────────────────────────────────
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input(
            "Stock Symbol",
            value=st.session_state.get("selected_symbol", "AAPL"),
            placeholder="Enter ticker (e.g., AAPL, MSFT, NVDA)",
            key="ac_symbol",
        ).strip().upper()
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("Analyze", use_container_width=True, type="primary", key="ac_btn")

    if analyze_btn and symbol:
        st.session_state.ac_active = symbol

    active = st.session_state.get("ac_active", "")
    if active:
        with st.spinner(f"Fetching analyst data for {active}..."):
            data = get_analyst_consensus(active)

        if "error" in data:
            st.error(f"Failed: {data['error']}")
        else:
            cr = data.get("consensus_rating", {})
            pt = data.get("price_targets", {})
            rc = data.get("recent_changes", {})
            er = data.get("estimate_revisions", {})
            sig = data.get("analyst_signal", {})
            price = data.get("current_price", 0)

            # ── Header ──
            st.markdown(f"### {data.get('company_name', active)} ({active})")

            # ── Key Metrics ──
            mcols = st.columns(5)
            with mcols[0]:
                rating = cr.get("rating", "N/A")
                rating_color = (
                    COLORS.get("success", "#22c55e") if "Buy" in rating
                    else COLORS.get("danger", "#ef4444") if "Sell" in rating
                    else COLORS.get("warning", "#eab308")
                )
                st.markdown(f"<div style='font-size:0.85em;color:{COLORS.get('text_muted', '#71717a')}'>Consensus Rating</div>"
                            f"<div style='font-size:1.5em;font-weight:bold;color:{rating_color}'>{rating}</div>",
                            unsafe_allow_html=True)
            with mcols[1]:
                st.metric("Analyst Score", f"{cr.get('score', 0):.1f} / 5")
            with mcols[2]:
                st.metric("Total Analysts", cr.get("total_analysts", 0))
            with mcols[3]:
                consensus_pt = pt.get("consensus")
                st.metric("Price Target", f"${consensus_pt:.2f}" if consensus_pt else "N/A")
            with mcols[4]:
                upside = pt.get("upside_to_consensus_pct", 0)
                st.metric("Upside/Downside", f"{upside:+.1f}%",
                          delta=f"vs ${price:.2f}" if price else None)

            st.markdown("---")

            # ── Rating Distribution + Signal Score ──
            rcol1, rcol2 = st.columns([2, 1])

            with rcol1:
                st.markdown("**Rating Distribution**")
                dist = cr.get("distribution", {})
                if dist:
                    dist_df = pd.DataFrame([
                        {"Rating": "Strong Buy", "Count": dist.get("strong_buy", 0)},
                        {"Rating": "Buy", "Count": dist.get("buy", 0)},
                        {"Rating": "Hold", "Count": dist.get("hold", 0)},
                        {"Rating": "Sell", "Count": dist.get("sell", 0)},
                        {"Rating": "Strong Sell", "Count": dist.get("strong_sell", 0)},
                    ])
                    st.bar_chart(dist_df.set_index("Rating"), color=COLORS.get("accent_primary", "#6366f1"))

                    bullish = cr.get("bullish_percent", 0)
                    st.caption(f"**{bullish:.0f}%** of analysts are bullish (Buy or Strong Buy)")
                else:
                    st.info("Detailed rating distribution not available")

            with rcol2:
                score = sig.get("score", 50)
                color = (
                    COLORS.get("success", "#22c55e") if score >= 65
                    else COLORS.get("danger", "#ef4444") if score <= 35
                    else COLORS.get("warning", "#eab308")
                )
                st.markdown(f"""
                <div style="text-align:center; padding:20px; border-radius:8px; border:1px solid {color};">
                    <div style="font-size:3em; font-weight:bold; color:{color};">{score}</div>
                    <div style="font-size:0.9em; color:{COLORS.get('text_secondary', '#a1a1aa')};">Analyst Signal</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"**{sig.get('assessment', '')}**")
                insight = sig.get("key_insight", "")
                if insight:
                    st.caption(insight)

            st.markdown("---")

            # ── Price Targets ──
            st.markdown("**Price Targets**")
            ptcols = st.columns(4)
            with ptcols[0]:
                st.metric("Low", f"${pt.get('low', 0):.2f}" if pt.get('low') else "N/A")
            with ptcols[1]:
                st.metric("Median", f"${pt.get('median', 0):.2f}" if pt.get('median') else "N/A")
            with ptcols[2]:
                st.metric("Consensus", f"${pt.get('consensus', 0):.2f}" if pt.get('consensus') else "N/A")
            with ptcols[3]:
                st.metric("High", f"${pt.get('high', 0):.2f}" if pt.get('high') else "N/A")

            # Visual: current price position in target range
            if pt.get("low") and pt.get("high") and price:
                low_pt = pt["low"]
                high_pt = pt["high"]
                rng = high_pt - low_pt
                if rng > 0:
                    pos = min(100, max(0, (price - low_pt) / rng * 100))
                    st.progress(int(pos), text=f"Current ${price:.2f} within analyst target range")

            st.markdown("---")

            # ── Recent Changes ──
            changes = rc.get("changes", [])
            if changes:
                st.markdown("**Recent Upgrades / Downgrades**")
                upgrades = rc.get("upgrades_30d", 0)
                downgrades = rc.get("downgrades_30d", 0)
                momentum = rc.get("momentum", "Neutral")
                st.caption(f"Last 30 days: **{upgrades} upgrades**, **{downgrades} downgrades** — Momentum: **{momentum}**")

                change_rows = []
                for c in changes[:10]:
                    action = c.get("action", "")
                    icon = "⬆️" if "Upgrade" in action or "up" in action.lower() else "⬇️" if "Downgrade" in action or "down" in action.lower() else "➡️"
                    change_rows.append({
                        "Date": c.get("date", ""),
                        "": icon,
                        "Firm": c.get("firm", ""),
                        "Action": action,
                        "From": c.get("from_rating", ""),
                        "To": c.get("to_rating", ""),
                    })
                st.dataframe(pd.DataFrame(change_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No recent analyst rating changes available")

            st.markdown("---")

            # ── Estimate Revisions ──
            eps_trend = er.get("eps_trend", {})
            eps_est = er.get("eps_estimates", {})

            if eps_trend or eps_est:
                st.markdown("**EPS Estimate Revisions**")

                if eps_trend:
                    trend_rows = []
                    for period, td in eps_trend.items():
                        rev = td.get("revision_30d_pct")
                        trend = td.get("revision_trend", "N/A")
                        trend_icon = "📈" if trend == "Positive" else "📉" if trend == "Negative" else "➡️"
                        trend_rows.append({
                            "Period": period,
                            "Current Est.": f"${td.get('current', 0):.2f}" if td.get('current') else "N/A",
                            "30 Days Ago": f"${td.get('30_days_ago', 0):.2f}" if td.get('30_days_ago') else "N/A",
                            "90 Days Ago": f"${td.get('90_days_ago', 0):.2f}" if td.get('90_days_ago') else "N/A",
                            "30d Revision": f"{rev:+.1f}%" if rev is not None else "N/A",
                            "Trend": f"{trend_icon} {trend}",
                        })
                    if trend_rows:
                        st.dataframe(pd.DataFrame(trend_rows), use_container_width=True, hide_index=True)

                if eps_est:
                    st.markdown("**Upcoming EPS Estimates**")
                    est_rows = []
                    for period, ed in eps_est.items():
                        est_rows.append({
                            "Period": period,
                            "Avg Estimate": f"${ed.get('avg_estimate', 0):.2f}" if ed.get('avg_estimate') else "N/A",
                            "Low": f"${ed.get('low', 0):.2f}" if ed.get('low') else "N/A",
                            "High": f"${ed.get('high', 0):.2f}" if ed.get('high') else "N/A",
                            "Analysts": ed.get("num_analysts", "N/A"),
                            "Growth": f"{ed.get('growth', 0):.1f}%" if ed.get('growth') is not None else "N/A",
                        })
                    if est_rows:
                        st.dataframe(pd.DataFrame(est_rows), use_container_width=True, hide_index=True)
            else:
                st.info("Estimate revision data not available")

# ─── Tab 2: Compare ──────────────────────────────────────────
with tab2:
    symbols_input = st.text_input(
        "Compare Symbols (comma-separated)",
        value="AAPL, MSFT, GOOGL, NVDA, META",
        placeholder="e.g., AAPL, MSFT, GOOGL",
        key="ac_compare_input",
    )
    compare_btn = st.button("Compare Analyst Consensus", key="ac_compare_btn", type="primary")

    if compare_btn and symbols_input:
        symbols = tuple(s.strip().upper() for s in symbols_input.split(",") if s.strip())
        if len(symbols) < 2:
            st.warning("Enter at least 2 symbols.")
        else:
            with st.spinner("Comparing analyst consensus..."):
                result = compare_analyst_consensus(symbols)

            if "error" in result:
                st.error(result["error"])
            else:
                ranking = result.get("ranking", [])
                if ranking:
                    st.markdown("### Analyst Consensus Ranking")
                    rank_df = pd.DataFrame(ranking)
                    st.dataframe(
                        rank_df.style.background_gradient(subset=["signal_score"], cmap="YlGn"),
                        use_container_width=True,
                        hide_index=True,
                    )

                    most_bullish = result.get("most_bullish")
                    if most_bullish:
                        st.success(f"Most bullish consensus: **{most_bullish}**")

                # Expandable per-stock detail
                individual = result.get("individual", {})
                for sym, sdata in individual.items():
                    if "error" in sdata:
                        continue
                    cr = sdata.get("consensus_rating", {})
                    pt = sdata.get("price_targets", {})
                    with st.expander(f"{sym} — {cr.get('rating', 'N/A')} (Score: {cr.get('score', 0):.1f})"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.markdown(f"**Analysts:** {cr.get('total_analysts', 0)}")
                            st.markdown(f"**Bullish:** {cr.get('bullish_percent', 0):.0f}%")
                        with c2:
                            consensus_pt = pt.get('consensus')
                            st.markdown(f"**Target:** ${consensus_pt:.2f}" if consensus_pt else "**Target:** N/A")
                            st.markdown(f"**Upside:** {pt.get('upside_to_consensus_pct', 0):+.1f}%")
                        with c3:
                            sig = sdata.get("analyst_signal", {})
                            st.markdown(f"**Signal:** {sig.get('score', 0)}/100")
                            st.markdown(f"**Assessment:** {sig.get('assessment', 'N/A')}")

# ─── Footer ─────────────────────────────────────────────────
st.markdown("---")
st.caption("Analyst data from Yahoo Finance. Consensus reflects aggregated Wall Street opinions — not investment advice.")
