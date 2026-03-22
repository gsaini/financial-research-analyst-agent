"""
Historical Stock Performance - Multi-horizon returns, benchmark comparison,
risk-adjusted metrics, rolling returns, and drawdown analysis.
"""

import streamlit as st
from utils.theme import inject_css, COLORS
from utils.session import init_session_state
from utils.formatters import format_percent, format_currency, format_number
from utils.data_service import track_performance
from components.header import render_header
from components.plotly_charts import (
    create_gauge_chart,
    create_line_chart,
    create_area_chart,
    create_benchmark_bar,
    create_horizontal_bar,
)

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Performance Tracking | FinancialAI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## Historical Performance Tracking")
st.caption("Multi-horizon returns, benchmark comparison, risk-adjusted metrics & drawdown analysis")

# ─── Symbol Input ────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    symbol = st.text_input(
        "Stock Symbol",
        value=st.session_state.get("selected_symbol", "AAPL"),
        placeholder="Enter ticker (e.g., AAPL)",
        key="perf_symbol",
    ).strip().upper()

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("Analyze Performance", use_container_width=True, type="primary")

if analyze_btn and symbol:
    st.session_state.perf_symbol_active = symbol

active = st.session_state.get("perf_symbol_active", "")
if not active:
    st.info("Enter a stock symbol and click **Analyze Performance** to get started.")
    st.stop()

# ─── Fetch Data ──────────────────────────────────────────────
result = track_performance(active)

if "error" in result:
    st.error(f"Error: {result['error']}")
    st.stop()

# ─── Header ──────────────────────────────────────────────────
sector = result.get("sector", "")
sector_etf = result.get("sector_etf", "")
current_price = result.get("current_price", 0)
date_range = f"{result.get('start_date', '')} to {result.get('end_date', '')}"

st.markdown(f"""
<div style="display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem;
            background: {COLORS['bg_card']}; border-radius: 10px; border: 1px solid {COLORS['border']};
            margin-bottom: 1.5rem;">
    <div>
        <span style="font-size: 1.5rem; font-weight: 700; color: {COLORS['text_primary']}; font-family: 'Inter', sans-serif;">
            {active}
        </span>
        <span style="color: {COLORS['text_muted']}; font-size: 0.85rem; margin-left: 0.75rem;">
            {sector}{f' · {sector_etf}' if sector_etf else ''}
        </span>
    </div>
    <div style="margin-left: auto; text-align: right;">
        <span style="font-size: 1.25rem; font-weight: 600; color: {COLORS['text_primary']}; font-family: 'JetBrains Mono', monospace;">
            {format_currency(current_price)}
        </span>
        <div style="font-size: 0.7rem; color: {COLORS['text_muted']};">{date_range} · {result.get('data_points', 0)} data points</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Absolute Returns ───────────────────────────────────────
abs_returns = result.get("absolute_returns", {})

st.markdown(f"""
<div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
    <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
    <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
        Multi-Horizon Returns
    </h3>
    <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
</div>
""", unsafe_allow_html=True)

horizon_display = [
    ("1D", "1_day"), ("1W", "1_week"), ("1M", "1_month"), ("3M", "3_month"),
    ("6M", "6_month"), ("YTD", "ytd"), ("1Y", "1_year"), ("3Y", "3_year"), ("5Y", "5_year"),
]

cols = st.columns(len(horizon_display))
for col, (label, key) in zip(cols, horizon_display):
    val = abs_returns.get(key)
    with col:
        if val is not None:
            delta_color = "normal" if val >= 0 else "inverse"
            col.metric(label=label, value=format_percent(val), delta=format_percent(val), delta_color=delta_color)
        else:
            col.metric(label=label, value="N/A")

st.markdown("<br>", unsafe_allow_html=True)

# ─── Benchmark Comparison ───────────────────────────────────
bench = result.get("benchmark_comparison", {})

if bench:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            Benchmark Comparison
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """, unsafe_allow_html=True)

    bench_tabs = list(bench.keys())
    bench_tab_labels = []
    for bt in bench_tabs:
        entry = bench[bt]
        bench_tab_labels.append(entry.get("benchmark", bt))

    tabs = st.tabs(bench_tab_labels)

    for tab, bt in zip(tabs, bench_tabs):
        entry = bench[bt]
        with tab:
            # Assessment
            assessment = entry.get("assessment", "")
            if "Outperforming" in assessment:
                assessment_color = COLORS["success"]
            elif "Underperforming" in assessment:
                assessment_color = COLORS["danger"]
            else:
                assessment_color = COLORS["text_muted"]

            st.markdown(f"""
            <div style="font-size: 0.9rem; color: {assessment_color}; font-weight: 600;
                        font-family: 'Inter', sans-serif; margin-bottom: 1rem;">
                {assessment}
            </div>
            """, unsafe_allow_html=True)

            # Alpha metrics
            alpha_horizons = ["1_month", "3_month", "1_year", "3_year"]
            alpha_labels = ["1M", "3M", "1Y", "3Y"]
            stock_vals = []
            bench_vals = []
            valid_labels = []

            for al, ah in zip(alpha_labels, alpha_horizons):
                s = entry.get(f"{ah}_stock")
                b = entry.get(f"{ah}_benchmark")
                if s is not None and b is not None:
                    stock_vals.append(s)
                    bench_vals.append(b)
                    valid_labels.append(al)

            if stock_vals:
                fig = create_benchmark_bar(
                    valid_labels,
                    stock_vals,
                    bench_vals,
                    stock_label=active,
                    benchmark_label=entry.get("benchmark", "Benchmark"),
                    title=f"{active} vs {entry.get('benchmark', 'Benchmark')} Returns",
                    height=350,
                )
                st.plotly_chart(fig, use_container_width=True)

            # Alpha summary row
            alpha_cols = st.columns(len(alpha_horizons))
            for col, al, ah in zip(alpha_cols, alpha_labels, alpha_horizons):
                alpha = entry.get(f"{ah}_alpha")
                if alpha is not None:
                    col.metric(
                        label=f"{al} Alpha",
                        value=format_percent(alpha),
                        delta=format_percent(alpha),
                        delta_color="normal" if alpha >= 0 else "inverse",
                    )

    st.markdown("<br>", unsafe_allow_html=True)

# ─── Risk-Adjusted Metrics ──────────────────────────────────
risk = result.get("risk_adjusted_metrics", {})

if risk:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            Risk-Adjusted Metrics
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """, unsafe_allow_html=True)

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        sharpe = risk.get("sharpe_ratio", 0)
        sharpe_rating = risk.get("sharpe_rating", "")
        fig = create_gauge_chart(
            value=max(-1, min(sharpe, 4)),
            title="Sharpe Ratio",
            min_val=-1,
            max_val=4,
            ranges=[
                {"range": [-1, 0.5], "color": "rgba(239, 68, 68, 0.3)"},
                {"range": [0.5, 1.0], "color": "rgba(245, 158, 11, 0.3)"},
                {"range": [1.0, 2.0], "color": "rgba(59, 130, 246, 0.3)"},
                {"range": [2.0, 4.0], "color": "rgba(16, 185, 129, 0.3)"},
            ],
            height=200,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Rating: **{sharpe_rating}**")

    with r2:
        sortino = risk.get("sortino_ratio", 0)
        sortino_rating = risk.get("sortino_rating", "")
        fig = create_gauge_chart(
            value=max(-1, min(sortino, 4)),
            title="Sortino Ratio",
            min_val=-1,
            max_val=4,
            ranges=[
                {"range": [-1, 0.5], "color": "rgba(239, 68, 68, 0.3)"},
                {"range": [0.5, 1.0], "color": "rgba(245, 158, 11, 0.3)"},
                {"range": [1.0, 2.0], "color": "rgba(59, 130, 246, 0.3)"},
                {"range": [2.0, 4.0], "color": "rgba(16, 185, 129, 0.3)"},
            ],
            height=200,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Rating: **{sortino_rating}**")

    with r3:
        beta = risk.get("beta")
        if beta is not None:
            beta_interp = risk.get("beta_interpretation", "")
            fig = create_gauge_chart(
                value=max(0, min(beta, 3)),
                title="Beta (vs S&P 500)",
                min_val=0,
                max_val=3,
                ranges=[
                    {"range": [0, 0.8], "color": "rgba(16, 185, 129, 0.3)"},
                    {"range": [0.8, 1.2], "color": "rgba(59, 130, 246, 0.3)"},
                    {"range": [1.2, 2.0], "color": "rgba(245, 158, 11, 0.3)"},
                    {"range": [2.0, 3.0], "color": "rgba(239, 68, 68, 0.3)"},
                ],
                height=200,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(beta_interp)
        else:
            st.metric("Beta", "N/A")

    with r4:
        vol = risk.get("annual_volatility", 0)
        st.metric("Annual Volatility", format_percent(vol, include_sign=False))
        st.metric("Daily Volatility", format_percent(risk.get("daily_volatility", 0), include_sign=False))

    st.markdown("<br>", unsafe_allow_html=True)

# ─── Rolling Returns ────────────────────────────────────────
rolling = result.get("rolling_returns", {})

if rolling.get("values"):
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            Rolling 30-Day Returns
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """, unsafe_allow_html=True)

    # Summary metrics
    rc1, rc2, rc3, rc4, rc5 = st.columns(5)
    rc1.metric("Current", format_percent(rolling.get("current")))
    rc2.metric("Average", format_percent(rolling.get("average")))
    rc3.metric("Best", format_percent(rolling.get("max")))
    rc4.metric("Worst", format_percent(rolling.get("min")))
    trend = rolling.get("trend", "")
    trend_color = "normal"
    if "negative" in trend.lower() or "weakening" in trend.lower():
        trend_color = "off"
    rc5.metric("Trend", trend)

    # Rolling returns chart
    fig = create_line_chart(
        dates=rolling.get("dates", []),
        values=rolling.get("values", []),
        title="30-Day Rolling Returns (%)",
        fill=True,
        height=300,
        show_zero_line=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ─── Drawdown Analysis ──────────────────────────────────────
dd = result.get("drawdown_analysis", {})

if dd.get("drawdown_series"):
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            Drawdown Analysis (1 Year)
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """, unsafe_allow_html=True)

    dc1, dc2, dc3, dc4 = st.columns(4)
    dc1.metric("Max Drawdown", format_percent(dd.get("max_drawdown")))
    dc2.metric("Max DD Date", dd.get("max_drawdown_date", "N/A"))
    recovery = dd.get("recovery_days")
    dc3.metric("Recovery Days", f"{recovery} days" if recovery else "Not recovered")
    dc4.metric("Current Drawdown", format_percent(dd.get("current_drawdown")))

    fig = create_area_chart(
        dates=dd.get("dates", []),
        values=dd.get("drawdown_series", []),
        title="Drawdown from Peak (%)",
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ─── Return Statistics ──────────────────────────────────────
stats = result.get("return_statistics", {})

if stats:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            Daily Return Statistics (1 Year)
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """, unsafe_allow_html=True)

    sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
    sc1.metric("Mean Daily", format_percent(stats.get("mean_daily"), decimals=3))
    sc2.metric("Median Daily", format_percent(stats.get("median_daily"), decimals=3))
    sc3.metric("Best Day", format_percent(stats.get("best_day")))
    sc4.metric("Worst Day", format_percent(stats.get("worst_day")))
    sc5.metric("Positive Days", format_percent(stats.get("positive_days_pct"), include_sign=False))
    sc6.metric("Std Dev", format_percent(stats.get("std_daily"), decimals=3, include_sign=False))

# ─── Footer ─────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align: center; padding: 1rem; border-top: 1px solid {COLORS['border']};">
    <p style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: {COLORS['text_muted']};">
        Performance data from Yahoo Finance · Returns are price-based (not total return) · Past performance does not guarantee future results
    </p>
</div>
""", unsafe_allow_html=True)
