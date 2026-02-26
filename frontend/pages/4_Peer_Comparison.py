"""
Peer Comparison - Side-by-side stock comparison against industry peers.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_css
from utils.session import init_session_state
from utils.formatters import format_currency, format_percent, format_large_number, format_number
from utils.data_service import compare_peers
from components.sidebar import render_sidebar
from components.plotly_charts import create_radar_chart, create_horizontal_bar, create_grouped_bar
from components.metrics_cards import render_company_header, render_strength_weakness
from components.data_tables import render_comparison_table

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(page_title="Peer Comparison | FinancialAI", page_icon=":chart_with_upwards_trend:", layout="wide")
inject_css()
init_session_state()
render_sidebar()

st.markdown("## Peer Comparison")
st.caption("Compare a stock against its industry peers")

# ─── Input ───────────────────────────────────────────────────
c1, c2 = st.columns([1, 2])
with c1:
    symbol = st.text_input(
        "Target Symbol",
        value=st.session_state.get("selected_symbol", "AAPL"),
        placeholder="e.g. AAPL",
        key="peer_symbol",
    ).upper().strip()

with c2:
    custom_peers = st.text_input(
        "Custom Peers (optional, comma-separated)",
        placeholder="e.g. MSFT, GOOGL, AMZN",
        key="custom_peers",
    )

compare_btn = st.button("Compare", use_container_width=False, key="compare_btn")

if not symbol:
    st.info("Enter a target symbol to begin peer comparison.")
    st.stop()

if compare_btn or symbol:
    peers = None
    if custom_peers:
        peers = tuple(p.strip().upper() for p in custom_peers.split(",") if p.strip())

    with st.spinner(f"Finding peers and comparing metrics for {symbol}..."):
        result = compare_peers(symbol, peers)

    if "error" in result:
        st.error(f"Peer comparison error: {result['error']}")
        st.stop()

    # ─── Header ──────────────────────────────────────────────
    peer_group = result.get("peer_group", [])
    st.markdown(f"**Target:** `{result.get('target', symbol)}` | **Peers:** {', '.join([f'`{p}`' for p in peer_group])}")

    # ─── Strengths & Weaknesses ──────────────────────────────
    render_strength_weakness(
        strengths=result.get("strengths", []),
        weaknesses=result.get("weaknesses", []),
    )

    st.markdown("---")

    # ─── Metrics Comparison Table ────────────────────────────
    st.markdown("### Metrics Comparison")

    metrics = result.get("metrics", {})
    if metrics:
        rows = []
        for sym, data in metrics.items():
            rows.append({
                "Symbol": sym,
                "Price": format_currency(data.get("price")),
                "Market Cap": format_large_number(data.get("market_cap")),
                "P/E": format_number(data.get("pe_ratio")),
                "Forward P/E": format_number(data.get("forward_pe")),
                "PEG": format_number(data.get("peg_ratio")),
                "P/B": format_number(data.get("pb_ratio")),
                "Profit Margin": format_percent(data.get("profit_margin", 0) * 100 if data.get("profit_margin") else None),
                "Op Margin": format_percent(data.get("operating_margin", 0) * 100 if data.get("operating_margin") else None),
                "ROE": format_percent(data.get("roe", 0) * 100 if data.get("roe") else None),
                "Rev Growth": format_percent(data.get("revenue_growth", 0) * 100 if data.get("revenue_growth") else None),
                "Beta": format_number(data.get("beta")),
                "Sector": data.get("sector", ""),
            })

        df = pd.DataFrame(rows)
        render_comparison_table(rows, highlight_symbol=symbol)

    st.markdown("---")

    # ─── Visual Comparisons ──────────────────────────────────
    c1, c2 = st.columns(2)

    # Valuation Comparison
    with c1:
        st.markdown("### Valuation Comparison")
        val_metrics = ["pe_ratio", "pb_ratio"]
        val_labels = ["P/E Ratio", "P/B Ratio"]

        for metric, label in zip(val_metrics, val_labels):
            syms = []
            vals = []
            colors = []
            for sym, data in metrics.items():
                v = data.get(metric)
                if v is not None:
                    syms.append(sym)
                    vals.append(v)
                    colors.append("#3b82f6" if sym == symbol else "#6b7280")

            if vals:
                fig = create_horizontal_bar(syms, vals, title=label, colors=colors)
                st.plotly_chart(fig, use_container_width=True)

    # Profitability Radar
    with c2:
        st.markdown("### Profitability Profile")
        target_data = metrics.get(symbol, {})
        categories = ["Profit Margin", "Op Margin", "ROE", "ROA", "Rev Growth"]
        target_vals = [
            (target_data.get("profit_margin") or 0) * 100,
            (target_data.get("operating_margin") or 0) * 100,
            (target_data.get("roe") or 0) * 100,
            (target_data.get("roa") or 0) * 100,
            (target_data.get("revenue_growth") or 0) * 100,
        ]

        # Peer median
        aggregates = result.get("peer_aggregates", {})
        if aggregates:
            peer_vals = [
                (aggregates.get("profit_margin", {}).get("median") or 0) * 100,
                (aggregates.get("operating_margin", {}).get("median") or 0) * 100,
                (aggregates.get("roe", {}).get("median") or 0) * 100,
                (aggregates.get("roa", {}).get("median") or 0) * 100,
                (aggregates.get("revenue_growth", {}).get("median") or 0) * 100,
            ]
            fig = create_radar_chart(categories, target_vals, title=f"{symbol} vs Peer Median",
                                     comparison_values=peer_vals, comparison_label="Peer Median")
        else:
            fig = create_radar_chart(categories, target_vals, title=f"{symbol} Profile")

        st.plotly_chart(fig, use_container_width=True)

    # ─── Percentile Rankings ─────────────────────────────────
    rankings = result.get("percentile_rankings", {})
    if rankings:
        st.markdown("---")
        st.markdown("### Percentile Rankings")
        for metric, desc in rankings.items():
            st.markdown(f"- **{metric.replace('_', ' ').title()}**: {desc}")

    # ─── Relative Valuation ──────────────────────────────────
    rel_val = result.get("relative_valuation", {})
    if rel_val:
        st.markdown("---")
        st.markdown("### Relative Valuation")
        for metric, desc in rel_val.items():
            color = "#10b981" if "discount" in str(desc).lower() else "#ef4444" if "premium" in str(desc).lower() else "#9ca3af"
            st.markdown(
                f"- **{metric.replace('_', ' ').title()}**: <span style='color:{color};'>{desc}</span>",
                unsafe_allow_html=True,
            )
