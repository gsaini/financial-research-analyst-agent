"""
Thematic Investing - Browse themes, analyze performance, compare.
"""

import streamlit as st
from utils.theme import inject_css
from utils.session import init_session_state
from utils.formatters import format_percent, format_currency, format_large_number
from utils.data_service import get_themes_list, analyze_theme, refresh_themes_cache
from components.header import render_header
from components.plotly_charts import create_gauge_chart, create_donut_chart, create_horizontal_bar, create_radar_chart
from components.metrics_cards import render_kpi_row

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(page_title="Thematic Investing | FinancialAI", page_icon=":chart_with_upwards_trend:", layout="wide", initial_sidebar_state="collapsed")
inject_css()
init_session_state()
render_header()

st.markdown("## Thematic Investing")
st.caption("Explore investment themes and megatrends")

# ─── Theme Browser ───────────────────────────────────────────

# Refresh themes from disk on first load of this session
if "themes_refreshed" not in st.session_state:
    refresh_themes_cache()
    st.session_state.themes_refreshed = True

themes = get_themes_list()

_hdr1, _hdr2 = st.columns([3, 1])
with _hdr2:
    if st.button("Refresh Themes", use_container_width=True, key="refresh_themes_btn"):
        refresh_themes_cache()
        st.rerun()

if not themes:
    st.warning("Unable to load investment themes. Check that config/themes.yaml is available.")
    st.stop()

# Mode toggle
mode = st.radio("Mode", ["Browse & Analyze", "Compare Themes"], horizontal=True, label_visibility="collapsed")

if mode == "Browse & Analyze":
    # ─── Theme Selection Grid ────────────────────────────────
    st.markdown("### Select a Theme")

    cols = st.columns(2)
    for i, theme in enumerate(themes):
        with cols[i % 2]:
            risk = theme.get("risk_level", "Medium")
            risk_class = "risk-high" if "high" in risk.lower() else "risk-low" if "low" in risk.lower() else "risk-medium"

            tags_html = "".join([
                f'<span class="tag">{tag}</span>' for tag in theme.get("sector_tags", [])[:3]
            ])
            tags_html += f'<span class="tag {risk_class}">{risk}</span>'

            st.markdown(
                f"""
                <div class="theme-card">
                    <div class="theme-name">{theme.get('name', 'Unknown')}</div>
                    <div class="theme-desc">{theme.get('description', '')[:120]}...</div>
                    <div class="theme-tags">{tags_html}</div>
                    <div style="font-size: 0.7rem; color: #6b7280; margin-top: 0.5rem;">
                        {theme.get('constituent_count', 0)} stocks &middot; {theme.get('growth_stage', '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Analyze {theme.get('name', '')}", key=f"theme_{theme.get('theme_id', i)}", use_container_width=True):
                st.session_state.selected_theme = theme.get("theme_id")
                st.rerun()

    # ─── Theme Analysis ──────────────────────────────────────
    selected = st.session_state.get("selected_theme")
    if selected:
        st.markdown("---")
        with st.spinner(f"Analyzing theme: {selected}..."):
            result = analyze_theme(selected)

        if "error" in result:
            st.error(f"Error analyzing theme: {result['error']}")
            st.stop()

        # Theme Header
        st.markdown(f"### {result.get('theme', selected)}")
        st.caption(result.get("description", ""))

        # KPI Row
        perf = result.get("theme_performance", {})
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            fig = create_gauge_chart(
                value=result.get("theme_health_score", 0),
                title="Health Score",
                height=200,
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig = create_gauge_chart(
                value=result.get("momentum_score", 0),
                title="Momentum",
                height=200,
            )
            st.plotly_chart(fig, use_container_width=True)

        c3.metric("1Y Performance", perf.get("1y", "N/A"))
        c4.metric("YTD Performance", perf.get("ytd", "N/A"))

        # Performance Table
        st.markdown("#### Multi-Horizon Performance")
        perf_cols = st.columns(6)
        horizons = [("1W", "1w"), ("1M", "1m"), ("3M", "3m"), ("6M", "6m"), ("1Y", "1y"), ("YTD", "ytd")]
        for col, (label, key) in zip(perf_cols, horizons):
            val = perf.get(key, "N/A")
            col.metric(label=label, value=val)

        st.markdown("---")

        # Top Performers & Laggards
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### Top Performers")
            top = result.get("top_performers", [])
            if top:
                labels = [t.get("symbol", "?") for t in top]
                values = []
                for t in top:
                    ret = t.get("1_year_return", "0%")
                    try:
                        values.append(float(str(ret).replace("%", "").replace("+", "")))
                    except ValueError:
                        values.append(0)
                colors = ["#10b981" if v >= 0 else "#ef4444" for v in values]
                fig = create_horizontal_bar(labels, values, title="1Y Return (%)", colors=colors)
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("#### Laggards")
            laggards = result.get("laggards", [])
            if laggards:
                labels = [t.get("symbol", "?") for t in laggards]
                values = []
                for t in laggards:
                    ret = t.get("1_year_return", "0%")
                    try:
                        values.append(float(str(ret).replace("%", "").replace("+", "")))
                    except ValueError:
                        values.append(0)
                colors = ["#10b981" if v >= 0 else "#ef4444" for v in values]
                fig = create_horizontal_bar(labels, values, title="1Y Return (%)", colors=colors)
                st.plotly_chart(fig, use_container_width=True)

        # Sector Overlap
        sector_overlap = result.get("sector_overlap", {})
        if sector_overlap:
            st.markdown("#### Sector Breakdown")
            labels = list(sector_overlap.keys())
            values = []
            for v in sector_overlap.values():
                try:
                    values.append(float(str(v).replace("%", "")))
                except ValueError:
                    values.append(0)
            fig = create_donut_chart(labels, values, title="Sector Overlap")
            st.plotly_chart(fig, use_container_width=True)

        # Risk Metrics
        risk = result.get("theme_risk", {})
        if risk:
            st.markdown("#### Theme Risk")
            c1, c2, c3 = st.columns(3)
            c1.metric("Intra-Correlation", f"{risk.get('intra_correlation', 'N/A')}")
            c2.metric("Diversification", risk.get("diversification_score", "N/A"))
            c3.metric("Risk Level", result.get("risk_level", "N/A"))
            desc = risk.get("diversification_description", "")
            if desc:
                st.caption(desc)

        # Constituent Details
        details = result.get("constituent_details", {})
        if details:
            with st.expander("Constituent Details", expanded=False):
                import pandas as pd
                rows = []
                for sym, d in details.items():
                    rows.append({
                        "Symbol": sym,
                        "Name": d.get("name", ""),
                        "Price": format_currency(d.get("current_price")),
                        "Return": format_percent(d.get("total_return_pct")),
                        "Market Cap": format_large_number(d.get("market_cap")),
                        "Sector": d.get("sector", ""),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

else:
    # ─── Compare Mode ────────────────────────────────────────
    st.markdown("### Compare Themes")

    theme_names = {t.get("theme_id"): t.get("name", t.get("theme_id", "")) for t in themes}
    theme_ids = list(theme_names.keys())

    selected_themes = st.multiselect(
        "Select themes to compare (2-5)",
        theme_ids,
        format_func=lambda x: theme_names.get(x, x),
        max_selections=5,
        key="compare_themes",
    )

    if len(selected_themes) >= 2:
        with st.spinner("Analyzing themes..."):
            results = {}
            for tid in selected_themes:
                results[tid] = analyze_theme(tid)

        # Comparison metrics
        st.markdown("#### Performance Comparison")

        horizons = ["1w", "1m", "3m", "6m", "1y", "ytd"]
        horizon_labels = ["1W", "1M", "3M", "6M", "1Y", "YTD"]

        series_data = []
        colors = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444"]
        for i, tid in enumerate(selected_themes):
            r = results.get(tid, {})
            perf = r.get("theme_performance", {})
            values = []
            for h in horizons:
                val = perf.get(h, "0%")
                try:
                    values.append(float(str(val).replace("%", "").replace("+", "")))
                except ValueError:
                    values.append(0)
            series_data.append({
                "name": theme_names.get(tid, tid),
                "values": values,
                "color": colors[i % len(colors)],
            })

        from components.plotly_charts import create_grouped_bar
        fig = create_grouped_bar(horizon_labels, series_data, title="Performance by Horizon (%)", height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Health/Momentum Radar
        st.markdown("#### Health & Momentum")
        categories = ["Health Score", "Momentum", "Diversification"]

        for i, tid in enumerate(selected_themes):
            r = results.get(tid, {})
            risk = r.get("theme_risk", {})
            div_score_str = risk.get("diversification_score", "Moderate")
            div_num = {"Low": 25, "Moderate": 50, "Good": 75, "Excellent": 100}.get(div_score_str, 50)

            cols = st.columns(3)
            cols[0].metric(theme_names.get(tid, tid) + " Health", r.get("theme_health_score", 0))
            cols[1].metric("Momentum", r.get("momentum_score", 0))
            cols[2].metric("Diversification", div_score_str)

    elif selected_themes:
        st.info("Select at least 2 themes to compare.")
