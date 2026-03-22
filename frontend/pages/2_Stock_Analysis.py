"""
Stock Analysis - Comprehensive technical, fundamental, sentiment, and risk analysis.
"""

import streamlit as st
import pandas as pd
import numpy as np
from utils.theme import inject_css
from utils.session import init_session_state
from utils.formatters import (
    format_currency, format_percent, format_large_number,
    format_number, format_date, format_ratio,
)
from utils.data_service import (
    get_stock_price, get_historical_data, get_company_info,
    get_financial_statements, get_technical_analysis,
    get_financial_health, get_valuation_ratios, get_profitability_ratios,
    get_company_news, analyze_news_sentiment,
)
from components.header import render_header
from components.charts import render_candlestick_chart
from components.plotly_charts import create_gauge_chart, create_radar_chart, create_grouped_bar, create_donut_chart
from components.metrics_cards import render_company_header, render_news_card, render_score_badge
from components.data_tables import render_styled_dataframe, render_metrics_table

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(page_title="Stock Analysis | FinancialAI", page_icon=":chart_with_upwards_trend:", layout="wide", initial_sidebar_state="collapsed")
inject_css()
init_session_state()
render_header()

st.markdown("## Stock Analysis")

# ─── Symbol Input ────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    symbol = st.text_input(
        "Stock Symbol",
        value=st.session_state.get("selected_symbol", "AAPL"),
        placeholder="e.g. AAPL",
        key="stock_analysis_symbol",
    ).upper().strip()

with col2:
    period_map = {"1 Week": "5d", "1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y", "5 Years": "5y"}
    period_label = st.selectbox("Period", list(period_map.keys()), index=4, key="stock_period")
    period = period_map[period_label]

with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_clicked = st.button("Analyze", use_container_width=True, key="analyze_btn")

if analyze_clicked:
    st.session_state.selected_symbol = symbol

if not symbol:
    st.info("Enter a stock symbol above to begin analysis.")
    st.stop()

# ─── Fetch Data ──────────────────────────────────────────────
with st.spinner(f"Loading data for {symbol}..."):
    price_data = get_stock_price(symbol)
    company = get_company_info(symbol)

if "error" in price_data:
    st.error(f"Could not find stock data for **{symbol}**. Please check the ticker symbol.")
    st.stop()

# ─── Company Header ──────────────────────────────────────────
render_company_header(
    symbol=symbol,
    name=company.get("name", symbol),
    price=price_data.get("current_price", 0),
    change_pct=price_data.get("change_percent", 0),
    market_cap=format_large_number(price_data.get("market_cap")),
    sector=company.get("sector", ""),
)

# Key metrics row
key_metrics = [
    {"label": "Open", "value": format_currency(price_data.get("open"))},
    {"label": "Day High", "value": format_currency(price_data.get("day_high"))},
    {"label": "Day Low", "value": format_currency(price_data.get("day_low"))},
    {"label": "52W High", "value": format_currency(price_data.get("52_week_high"))},
    {"label": "52W Low", "value": format_currency(price_data.get("52_week_low"))},
    {"label": "Volume", "value": f"{price_data.get('volume', 0):,.0f}" if price_data.get("volume") else "--"},
]

cols = st.columns(6)
for col, m in zip(cols, key_metrics):
    col.metric(label=m["label"], value=m["value"])

# ─── Price Chart ─────────────────────────────────────────────
st.markdown("### Price Chart")

hist = get_historical_data(symbol, period)
tech = get_technical_analysis(symbol, period)

if "error" not in hist and hist.get("dates"):
    # Build MA overlay data
    sma_data = {}
    if "error" not in tech:
        ma = tech.get("moving_averages", {})
        # We need the full series for chart overlays, but tools return single values.
        # For chart display, show single-value MAs as price lines instead.
        # For now, render the candlestick without MA overlays (data limitation).

    # S/R levels
    sr = tech.get("support_resistance", {}) if "error" not in tech else {}
    support = sr.get("support_levels", [])
    resistance = sr.get("resistance_levels", [])

    render_candlestick_chart(
        dates=hist["dates"],
        opens=hist["opens"],
        highs=hist["highs"],
        lows=hist["lows"],
        closes=hist["closes"],
        volumes=hist.get("volumes"),
        support_levels=support[:3],
        resistance_levels=resistance[:3],
        height=480,
    )
else:
    st.warning("Unable to load historical data for chart.")

# ─── Analysis Tabs ───────────────────────────────────────────
tab_tech, tab_fund, tab_sent, tab_risk = st.tabs(["Technical", "Fundamental", "Sentiment", "Risk"])

# ═══ TECHNICAL TAB ═══════════════════════════════════════════
with tab_tech:
    if "error" in tech:
        st.warning("Technical analysis unavailable.")
    else:
        # RSI, MACD, Trend row
        c1, c2, c3 = st.columns(3)

        # RSI Gauge
        with c1:
            rsi = tech.get("rsi", {})
            rsi_val = rsi.get("value", 50)
            if isinstance(rsi_val, (int, float)):
                fig = create_gauge_chart(
                    value=round(rsi_val, 1),
                    title="RSI (14)",
                    min_val=0,
                    max_val=100,
                    ranges=[
                        {"range": [0, 30], "color": "rgba(16, 185, 129, 0.3)"},
                        {"range": [30, 70], "color": "rgba(245, 158, 11, 0.15)"},
                        {"range": [70, 100], "color": "rgba(239, 68, 68, 0.3)"},
                    ],
                    height=220,
                )
                st.plotly_chart(fig, use_container_width=True)
                signal = rsi.get("signal", "NEUTRAL")
                badge = "bullish" if "OVERSOLD" in str(signal).upper() else "bearish" if "OVERBOUGHT" in str(signal).upper() else "neutral"
                st.markdown(f'<div style="text-align:center;"><span class="score-badge {badge}">{signal}</span></div>', unsafe_allow_html=True)

        # MACD
        with c2:
            macd = tech.get("macd", {})
            st.markdown("#### MACD")
            macd_metrics = {
                "MACD Line": format_number(macd.get("macd_line"), 4),
                "Signal Line": format_number(macd.get("signal_line"), 4),
                "Histogram": format_number(macd.get("histogram"), 4),
                "Crossover": str(macd.get("crossover", "--")).title(),
                "Trend": str(macd.get("trend", "--")).title(),
            }
            for label, val in macd_metrics.items():
                st.markdown(f"**{label}:** `{val}`")

            trend = macd.get("trend", "neutral")
            badge = "bullish" if "bullish" in str(trend).lower() else "bearish" if "bearish" in str(trend).lower() else "neutral"
            st.markdown(f'<div style="text-align:center; margin-top: 0.5rem;"><span class="score-badge {badge}">{str(trend).upper()}</span></div>', unsafe_allow_html=True)

        # Moving Averages
        with c3:
            ma = tech.get("moving_averages", {})
            st.markdown("#### Moving Averages")
            current = ma.get("current_price", price_data.get("current_price", 0))
            ma_items = [
                ("SMA 20", ma.get("sma_20")),
                ("EMA 20", ma.get("ema_20")),
                ("SMA 50", ma.get("sma_50")),
                ("EMA 50", ma.get("ema_50")),
                ("SMA 200", ma.get("sma_200")),
                ("EMA 200", ma.get("ema_200")),
            ]
            for label, val in ma_items:
                if val is not None:
                    color = "#10b981" if current > val else "#ef4444"
                    pos = "Above" if current > val else "Below"
                    st.markdown(f"**{label}:** `{format_currency(val)}` <span style='color:{color}; font-size:0.8rem;'>({pos})</span>", unsafe_allow_html=True)

            trend = ma.get("trend", "neutral")
            badge = "bullish" if "bullish" in str(trend).lower() else "bearish" if "bearish" in str(trend).lower() else "neutral"
            st.markdown(f'<div style="text-align:center; margin-top: 0.5rem;"><span class="score-badge {badge}">{str(trend).upper()} TREND</span></div>', unsafe_allow_html=True)

        st.markdown("---")

        # Bollinger Bands & Patterns
        c1, c2 = st.columns(2)

        with c1:
            bb = tech.get("bollinger_bands", {})
            if bb and "error" not in bb:
                st.markdown("#### Bollinger Bands")
                bb_items = {
                    "Upper Band": format_currency(bb.get("upper_band")),
                    "Middle Band": format_currency(bb.get("middle_band")),
                    "Lower Band": format_currency(bb.get("lower_band")),
                    "Bandwidth": format_number(bb.get("bandwidth"), 4),
                    "%B": format_number(bb.get("percent_b"), 4),
                    "Position": str(bb.get("position", "--")).replace("_", " ").title(),
                }
                for label, val in bb_items.items():
                    st.markdown(f"**{label}:** `{val}`")

        with c2:
            patterns = tech.get("patterns", {})
            detected = patterns.get("patterns_detected", [])
            st.markdown("#### Pattern Detection")
            if detected:
                for p in detected:
                    conf = p.get("confidence", 0)
                    impl = p.get("implication", "neutral")
                    badge = "bullish" if "bullish" in str(impl).lower() else "bearish" if "bearish" in str(impl).lower() else "neutral"
                    st.markdown(
                        f'<span class="score-badge {badge}">{p.get("name", "Unknown")} '
                        f'({conf*100:.0f}% confidence)</span>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No significant patterns detected in the current period.")

        # Support & Resistance
        sr = tech.get("support_resistance", {})
        if sr and "error" not in sr:
            st.markdown("---")
            st.markdown("#### Support & Resistance Levels")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Support Levels**")
                for level in sr.get("support_levels", [])[:5]:
                    st.markdown(f"<span style='color: #10b981; font-family: JetBrains Mono;'>{format_currency(level)}</span>", unsafe_allow_html=True)
            with c2:
                st.markdown("**Resistance Levels**")
                for level in sr.get("resistance_levels", [])[:5]:
                    st.markdown(f"<span style='color: #ef4444; font-family: JetBrains Mono;'>{format_currency(level)}</span>", unsafe_allow_html=True)

# ═══ FUNDAMENTAL TAB ═════════════════════════════════════════
with tab_fund:
    with st.spinner("Loading fundamentals..."):
        financials = get_financial_statements(symbol)
        health = get_financial_health(symbol)
        valuation = get_valuation_ratios(symbol)
        profitability = get_profitability_ratios(symbol)

    # Valuation metrics row
    if "error" not in valuation:
        st.markdown("#### Valuation")
        val_metrics = [
            {"label": "P/E Ratio", "value": format_number(valuation.get("pe_ratio"))},
            {"label": "P/B Ratio", "value": format_number(valuation.get("pb_ratio"))},
            {"label": "P/S Ratio", "value": format_number(valuation.get("ps_ratio"))},
            {"label": "EV/EBITDA", "value": format_number(valuation.get("ev_ebitda"))},
        ]
        cols = st.columns(4)
        for col, m in zip(cols, val_metrics):
            col.metric(label=m["label"], value=m["value"])

        # Assessments
        assessments = []
        for key in ["pe_assessment", "pb_assessment", "ev_ebitda_assessment"]:
            a = valuation.get(key)
            if a:
                assessments.append(a)
        if assessments:
            st.caption("Assessments: " + " | ".join(assessments))

    st.markdown("---")

    # Financial Health & Profitability
    c1, c2 = st.columns(2)

    with c1:
        if "error" not in health:
            health_score = health.get("health_score", 0)
            fig = create_gauge_chart(
                value=round(health_score, 1),
                title="Financial Health Score",
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
            assessment = health.get("overall_assessment", "")
            if assessment:
                badge = "bullish" if "strong" in assessment.lower() else "bearish" if "weak" in assessment.lower() else "neutral"
                st.markdown(f'<div style="text-align:center;"><span class="score-badge {badge}">{assessment}</span></div>', unsafe_allow_html=True)

            # Strengths/Weaknesses
            strengths = health.get("strengths", [])
            weaknesses = health.get("weaknesses", [])
            if strengths:
                st.markdown("**Strengths**")
                for s in strengths[:5]:
                    st.markdown(f'<div class="strength-item">{s}</div>', unsafe_allow_html=True)
            if weaknesses:
                st.markdown("**Weaknesses**")
                for w in weaknesses[:5]:
                    st.markdown(f'<div class="weakness-item">{w}</div>', unsafe_allow_html=True)
        else:
            st.caption("Financial health data unavailable.")

    with c2:
        if "error" not in profitability:
            # Radar chart
            categories = ["Gross Margin", "Op Margin", "Net Margin", "ROE", "ROA"]
            raw_vals = [
                profitability.get("gross_margin"),
                profitability.get("operating_margin"),
                profitability.get("net_margin"),
                profitability.get("roe"),
                profitability.get("roa"),
            ]
            values = [round(v * 100, 1) if v and abs(v) < 1 else round(v, 1) if v else 0 for v in raw_vals]

            fig = create_radar_chart(categories, values, title="Profitability Profile", height=320)
            st.plotly_chart(fig, use_container_width=True)

            # ROE assessment
            roe_assessment = profitability.get("roe_assessment", "")
            if roe_assessment:
                st.caption(f"ROE Assessment: {roe_assessment}")
        else:
            st.caption("Profitability data unavailable.")

    # Financial Statements
    st.markdown("---")
    st.markdown("#### Financial Statements")

    if "error" not in financials:
        fs_tabs = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])

        with fs_tabs[0]:
            income = financials.get("income_statement")
            if income:
                render_metrics_table({
                    "Total Revenue": format_large_number(income.get("total_revenue")),
                    "Gross Profit": format_large_number(income.get("gross_profit")),
                    "Operating Income": format_large_number(income.get("operating_income")),
                    "Net Income": format_large_number(income.get("net_income")),
                    "EBITDA": format_large_number(income.get("ebitda")),
                })
            else:
                st.caption("Income statement data unavailable.")

        with fs_tabs[1]:
            balance = financials.get("balance_sheet")
            if balance:
                render_metrics_table({
                    "Total Assets": format_large_number(balance.get("total_assets")),
                    "Total Liabilities": format_large_number(balance.get("total_liabilities")),
                    "Total Equity": format_large_number(balance.get("total_equity")),
                    "Cash": format_large_number(balance.get("cash")),
                    "Total Debt": format_large_number(balance.get("total_debt")),
                })
            else:
                st.caption("Balance sheet data unavailable.")

        with fs_tabs[2]:
            cashflow = financials.get("cash_flow")
            if cashflow:
                render_metrics_table({
                    "Operating Cash Flow": format_large_number(cashflow.get("operating_cash_flow")),
                    "Capital Expenditure": format_large_number(cashflow.get("capital_expenditure")),
                    "Free Cash Flow": format_large_number(cashflow.get("free_cash_flow")),
                })
            else:
                st.caption("Cash flow data unavailable.")
    else:
        st.caption("Financial statements data unavailable.")

# ═══ SENTIMENT TAB ═══════════════════════════════════════════
with tab_sent:
    st.markdown("#### News Sentiment")

    sent_data = analyze_news_sentiment(symbol)
    if "error" not in sent_data and sent_data.get("articles_analyzed", 0) > 0:
        agg_sent = sent_data.get("aggregate_sentiment", {})
        sent_dist = sent_data.get("distribution", {})

        # Sentiment overview row
        sc1, sc2, sc3 = st.columns([1, 1, 1])
        with sc1:
            agg_score = agg_sent.get("score", 0)
            gauge_val = (agg_score + 1) / 2 * 100
            fig = create_gauge_chart(
                value=round(gauge_val, 1),
                title="Sentiment Score",
                min_val=0, max_val=100,
                ranges=[
                    {"range": [0, 30], "color": "rgba(239, 68, 68, 0.3)"},
                    {"range": [30, 45], "color": "rgba(245, 158, 11, 0.3)"},
                    {"range": [45, 55], "color": "rgba(161, 161, 170, 0.2)"},
                    {"range": [55, 70], "color": "rgba(59, 130, 246, 0.3)"},
                    {"range": [70, 100], "color": "rgba(16, 185, 129, 0.3)"},
                ],
                height=200,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"**{agg_sent.get('label', 'Neutral')}** · {sent_data.get('articles_analyzed', 0)} articles")

        with sc2:
            if sent_dist:
                fig = create_donut_chart(
                    labels=["Positive", "Neutral", "Negative"],
                    values=[sent_dist.get("positive", 0), sent_dist.get("neutral", 0), sent_dist.get("negative", 0)],
                    title="Distribution",
                    colors=["#22c55e", "#71717a", "#ef4444"],
                    height=200,
                )
                st.plotly_chart(fig, use_container_width=True)

        with sc3:
            vol = sent_data.get("volume", {})
            st.metric("24h Volume", vol.get("last_24h", 0))
            st.metric("7d Volume", vol.get("last_7d", 0))
            trend_dir = sent_data.get("sentiment_trend", {}).get("direction", "Stable")
            st.metric("Trend", trend_dir)

        # Scored articles
        scored = sent_data.get("scored_articles", [])
        if scored:
            st.markdown("##### Scored Articles")
            cols = st.columns(2)
            for i, article in enumerate(scored[:8]):
                sent = article.get("sentiment", {})
                score = sent.get("score", 0)
                label = sent.get("label", "Neutral")
                with cols[i % 2]:
                    render_news_card(
                        title=f"[{score:+.2f}] {article.get('title', 'Untitled')}",
                        source=article.get("source", ""),
                        date=format_date(article.get("published_at", "")),
                        description=article.get("description", ""),
                        url=article.get("url", ""),
                        thumbnail=article.get("thumbnail", ""),
                        content_type=article.get("type", ""),
                    )
    else:
        news = get_company_news(symbol)
        if news:
            cols = st.columns(2)
            for i, article in enumerate(news[:8]):
                with cols[i % 2]:
                    render_news_card(
                        title=article.get("title", "Untitled"),
                        source=article.get("source", ""),
                        date=format_date(article.get("published_at", "")),
                        description=article.get("description", ""),
                        url=article.get("url", ""),
                        thumbnail=article.get("thumbnail", ""),
                        content_type=article.get("type", ""),
                    )
        else:
            st.info(f"No recent news found for {symbol}.")

# ═══ RISK TAB ════════════════════════════════════════════════
with tab_risk:
    st.markdown("#### Risk Metrics")

    if "error" not in hist and hist.get("closes"):
        closes = np.array(hist["closes"], dtype=float)
        returns = np.diff(closes) / closes[:-1]

        daily_vol = np.std(returns)
        annual_vol = daily_vol * np.sqrt(252)
        max_dd = 0.0
        peak = closes[0]
        for p in closes:
            if p > peak:
                peak = p
            dd = (peak - p) / peak
            if dd > max_dd:
                max_dd = dd

        # 52-week range
        high_52 = price_data.get("52_week_high", max(closes))
        low_52 = price_data.get("52_week_low", min(closes))
        current = price_data.get("current_price", closes[-1])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Daily Volatility", format_percent(daily_vol * 100))
        c2.metric("Annual Volatility", format_percent(annual_vol * 100))
        c3.metric("Max Drawdown", format_percent(-max_dd * 100))

        # Sharpe (assume risk-free rate ~5%)
        avg_return = np.mean(returns) * 252
        sharpe = (avg_return - 0.05) / annual_vol if annual_vol > 0 else 0
        c4.metric("Sharpe Ratio", format_number(sharpe))

        st.markdown("---")

        # 52-Week Range visualization
        st.markdown("#### 52-Week Range")
        if high_52 > low_52:
            pct_pos = ((current - low_52) / (high_52 - low_52)) * 100
            pct_pos = max(0, min(100, pct_pos))
        else:
            pct_pos = 50

        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 1rem; margin: 1rem 0;">
                <span style="font-family: JetBrains Mono; color: #ef4444; font-size: 0.85rem;">
                    {format_currency(low_52)}
                </span>
                <div style="flex: 1; height: 8px; background: linear-gradient(to right, #ef4444, #f59e0b, #10b981);
                            border-radius: 999px; position: relative;">
                    <div style="position: absolute; top: -8px; left: {pct_pos}%;
                                width: 12px; height: 24px; background: white; border-radius: 6px;
                                transform: translateX(-50%); box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                    </div>
                </div>
                <span style="font-family: JetBrains Mono; color: #10b981; font-size: 0.85rem;">
                    {format_currency(high_52)}
                </span>
            </div>
            <div style="text-align: center; color: #9ca3af; font-size: 0.8rem;">
                Current: {format_currency(current)} ({pct_pos:.0f}% of range)
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Return distribution
        st.markdown("---")
        st.markdown("#### Return Statistics")
        stats = {
            "Mean Daily Return": format_percent(np.mean(returns) * 100, 4),
            "Median Daily Return": format_percent(np.median(returns) * 100, 4),
            "Best Day": format_percent(np.max(returns) * 100),
            "Worst Day": format_percent(np.min(returns) * 100),
            "Positive Days": f"{(returns > 0).sum()} / {len(returns)} ({(returns > 0).mean() * 100:.1f}%)",
            "Skewness": format_number(float(pd.Series(returns).skew()), 4),
            "Kurtosis": format_number(float(pd.Series(returns).kurtosis()), 4),
        }
        render_metrics_table(stats)
    else:
        st.warning("Historical data required for risk analysis.")
