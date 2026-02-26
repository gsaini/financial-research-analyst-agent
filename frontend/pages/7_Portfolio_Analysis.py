"""
Portfolio Analysis - Multi-stock portfolio with correlation and sector insights.
"""

import streamlit as st
import pandas as pd
import numpy as np
from utils.theme import inject_css
from utils.session import init_session_state
from utils.formatters import format_currency, format_percent, format_large_number
from utils.data_service import get_stock_price, get_historical_data, get_company_info, get_technical_analysis
from components.sidebar import render_sidebar
from components.plotly_charts import create_donut_chart, create_heatmap, create_gauge_chart
from components.charts import render_area_chart

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(page_title="Portfolio | FinancialAI", page_icon=":chart_with_upwards_trend:", layout="wide")
inject_css()
init_session_state()
render_sidebar()

st.markdown("## Portfolio Analysis")
st.caption("Analyze multi-stock portfolios with correlation insights")

# ─── Portfolio Builder ───────────────────────────────────────
symbols_input = st.text_input(
    "Portfolio Symbols (comma-separated)",
    value=", ".join(st.session_state.get("portfolio_symbols", [])) or "AAPL, MSFT, GOOGL, AMZN, NVDA",
    placeholder="e.g. AAPL, MSFT, GOOGL, AMZN, NVDA",
    key="portfolio_input",
)

symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
st.session_state.portfolio_symbols = symbols

if len(symbols) < 2:
    st.info("Enter at least 2 stock symbols separated by commas.")
    st.stop()

analyze = st.button("Analyze Portfolio", use_container_width=False)

if analyze or symbols:
    with st.spinner(f"Analyzing portfolio of {len(symbols)} stocks..."):
        # Fetch data for all symbols
        stock_data = {}
        hist_data = {}
        company_data = {}

        for sym in symbols:
            stock_data[sym] = get_stock_price(sym)
            hist_data[sym] = get_historical_data(sym, "1y")
            company_data[sym] = get_company_info(sym)

    # Filter out errored symbols
    valid_symbols = [s for s in symbols if "error" not in stock_data.get(s, {"error": True})]
    errored = [s for s in symbols if s not in valid_symbols]

    if errored:
        st.warning(f"Could not fetch data for: {', '.join(errored)}")

    if len(valid_symbols) < 2:
        st.error("Need at least 2 valid symbols for portfolio analysis.")
        st.stop()

    # ─── Portfolio Overview ──────────────────────────────────
    st.markdown("---")
    st.markdown("### Portfolio Overview")

    total_mcap = sum(
        stock_data[s].get("market_cap", 0) or 0
        for s in valid_symbols
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Stocks", len(valid_symbols))
    c2.metric("Total Market Cap", format_large_number(total_mcap))
    c3.metric("Weighting", "Equal Weight")

    # ─── Per-Stock Summary Table ─────────────────────────────
    st.markdown("### Individual Stocks")

    rows = []
    for sym in valid_symbols:
        sd = stock_data[sym]
        cd = company_data.get(sym, {})
        rows.append({
            "Symbol": sym,
            "Name": cd.get("name", sym),
            "Price": format_currency(sd.get("current_price")),
            "Change %": format_percent(sd.get("change_percent", 0)),
            "Market Cap": format_large_number(sd.get("market_cap")),
            "P/E": f"{sd.get('pe_ratio', 0):.1f}" if sd.get("pe_ratio") else "--",
            "Sector": cd.get("sector", "--"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ─── Sector Allocation ───────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Sector Allocation")
        sectors = {}
        for sym in valid_symbols:
            sector = company_data.get(sym, {}).get("sector", "Unknown")
            sectors[sector] = sectors.get(sector, 0) + 1

        if sectors:
            fig = create_donut_chart(
                labels=list(sectors.keys()),
                values=list(sectors.values()),
                title="Sector Breakdown",
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("### Market Cap Distribution")
        cap_buckets = {"Mega (>$200B)": 0, "Large ($10-200B)": 0, "Mid ($2-10B)": 0, "Small (<$2B)": 0}
        for sym in valid_symbols:
            mcap = stock_data[sym].get("market_cap", 0) or 0
            if mcap >= 200e9:
                cap_buckets["Mega (>$200B)"] += 1
            elif mcap >= 10e9:
                cap_buckets["Large ($10-200B)"] += 1
            elif mcap >= 2e9:
                cap_buckets["Mid ($2-10B)"] += 1
            else:
                cap_buckets["Small (<$2B)"] += 1

        non_zero = {k: v for k, v in cap_buckets.items() if v > 0}
        if non_zero:
            fig = create_donut_chart(
                labels=list(non_zero.keys()),
                values=list(non_zero.values()),
                title="Market Cap Tiers",
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ─── Mini Stock Cards ────────────────────────────────────
    st.markdown("### Quick Signals")

    card_cols = st.columns(min(len(valid_symbols), 4))
    for i, sym in enumerate(valid_symbols):
        with card_cols[i % len(card_cols)]:
            sd = stock_data[sym]
            price = sd.get("current_price", 0)
            change = sd.get("change_percent", 0)
            change_color = "#10b981" if change >= 0 else "#ef4444"
            change_sign = "+" if change >= 0 else ""

            # Quick RSI
            tech = get_technical_analysis(sym)
            rsi_val = "--"
            rsi_signal = "Neutral"
            if "error" not in tech:
                rsi = tech.get("rsi", {})
                rsi_val = f"{rsi.get('value', 0):.0f}" if isinstance(rsi.get("value"), (int, float)) else "--"
                rsi_signal = rsi.get("signal", "NEUTRAL")

            st.markdown(
                f"""
                <div class="card" style="text-align: center; padding: 1rem;">
                    <div style="font-weight: 800; font-size: 1.1rem; font-family: JetBrains Mono;">{sym}</div>
                    <div style="font-size: 1.3rem; font-weight: 700; font-family: JetBrains Mono; margin: 0.25rem 0;">
                        {format_currency(price)}
                    </div>
                    <div style="color: {change_color}; font-family: JetBrains Mono; font-size: 0.85rem;">
                        {change_sign}{change:.2f}%
                    </div>
                    <div style="margin-top: 0.5rem; font-size: 0.75rem; color: #9ca3af;">
                        RSI: {rsi_val} ({rsi_signal})
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ─── Correlation Matrix ──────────────────────────────────
    st.markdown("### Correlation Matrix")

    # Build aligned returns
    all_returns = {}
    min_len = float("inf")

    for sym in valid_symbols:
        hd = hist_data.get(sym, {})
        returns = hd.get("returns", [])
        if returns:
            all_returns[sym] = returns
            min_len = min(min_len, len(returns))

    if len(all_returns) >= 2 and min_len > 10:
        # Align to same length
        aligned = {sym: ret[:int(min_len)] for sym, ret in all_returns.items()}
        syms_list = list(aligned.keys())
        returns_matrix = np.array([aligned[s] for s in syms_list])

        corr_matrix = np.corrcoef(returns_matrix)

        fig = create_heatmap(
            matrix=corr_matrix.tolist(),
            x_labels=syms_list,
            y_labels=syms_list,
            title="Returns Correlation Matrix",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Portfolio risk metrics
        avg_corr = (corr_matrix.sum() - len(syms_list)) / (len(syms_list) * (len(syms_list) - 1))
        st.caption(f"Average pairwise correlation: **{avg_corr:.3f}**")

        if avg_corr < 0.3:
            st.success("Good diversification - low average correlation between portfolio components.")
        elif avg_corr < 0.6:
            st.info("Moderate diversification - some correlation between portfolio components.")
        else:
            st.warning("High correlation between portfolio components - consider diversifying further.")
    else:
        st.caption("Insufficient return data to calculate correlation matrix.")

    # ─── Portfolio Risk Metrics ──────────────────────────────
    st.markdown("---")
    st.markdown("### Portfolio Risk Metrics (Equal-Weighted)")

    if len(all_returns) >= 2 and min_len > 10:
        # Equal-weighted portfolio returns
        aligned_arr = np.array([all_returns[s][:int(min_len)] for s in valid_symbols if s in all_returns])
        portfolio_returns = np.mean(aligned_arr, axis=0)

        port_vol_daily = np.std(portfolio_returns)
        port_vol_annual = port_vol_daily * np.sqrt(252)
        port_mean_return = np.mean(portfolio_returns) * 252
        sharpe = (port_mean_return - 0.05) / port_vol_annual if port_vol_annual > 0 else 0

        # Max drawdown
        cumulative = np.cumprod(1 + portfolio_returns)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (peak - cumulative) / peak
        max_dd = np.max(drawdown)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Annual Volatility", format_percent(port_vol_annual * 100))
        c2.metric("Expected Return", format_percent(port_mean_return * 100))
        c3.metric("Sharpe Ratio", f"{sharpe:.2f}")
        c4.metric("Max Drawdown", format_percent(-max_dd * 100))
