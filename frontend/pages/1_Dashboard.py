"""
Dashboard - Market overview, quick analysis, news feed.
"""

import streamlit as st
from utils.theme import inject_css
from utils.session import init_session_state
from utils.formatters import format_currency, format_percent, format_large_number, format_date
from utils.data_service import get_stock_price, get_historical_data, get_company_news, get_technical_analysis
from components.header import render_header
from components.charts import render_candlestick_chart, render_area_chart
from components.metrics_cards import render_kpi_row, render_news_card

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(page_title="Dashboard | FinancialAI", page_icon=":chart_with_upwards_trend:", layout="wide")
inject_css()
init_session_state()
render_header()

st.markdown("## Dashboard")
st.caption("Market overview and quick analysis")

# ─── Market Indices ──────────────────────────────────────────
indices = [
    ("SPY", "S&P 500"),
    ("QQQ", "NASDAQ 100"),
    ("DIA", "Dow Jones"),
    ("IWM", "Russell 2000"),
]

cols = st.columns(4)
for col, (ticker, label) in zip(cols, indices):
    with col:
        data = get_stock_price(ticker)
        if "error" not in data:
            col.metric(
                label=label,
                value=format_currency(data.get("current_price", 0)),
                delta=format_percent(data.get("change_percent", 0)),
            )
        else:
            col.metric(label=label, value="--")

st.markdown("<br>", unsafe_allow_html=True)

# ─── Main Layout ─────────────────────────────────────────────
left_col, right_col = st.columns([3, 2])

# ─── Market Chart ────────────────────────────────────────────
with left_col:
    st.markdown("### Market Chart")
    chart_symbol = st.selectbox(
        "Index",
        ["SPY", "QQQ", "DIA", "IWM"],
        label_visibility="collapsed",
        key="dashboard_chart_symbol",
    )
    period = st.radio(
        "Period",
        ["1mo", "3mo", "6mo", "1y"],
        horizontal=True,
        index=3,
        label_visibility="collapsed",
        key="dashboard_chart_period",
    )

    hist = get_historical_data(chart_symbol, period)
    if "error" not in hist and hist.get("dates"):
        render_candlestick_chart(
            dates=hist["dates"],
            opens=hist["opens"],
            highs=hist["highs"],
            lows=hist["lows"],
            closes=hist["closes"],
            volumes=hist.get("volumes"),
            height=420,
        )
    else:
        st.warning(f"Unable to load chart data for {chart_symbol}.")

# ─── Watchlist & Quick Analysis ──────────────────────────────
with right_col:
    st.markdown("### Watchlist")

    watchlist = st.session_state.get("watchlist", [])
    if watchlist:
        for sym in watchlist:
            data = get_stock_price(sym)
            if "error" not in data:
                price = data.get("current_price", 0)
                change = data.get("change_percent", 0)
                change_color = "#10b981" if change >= 0 else "#ef4444"
                change_sign = "+" if change >= 0 else ""

                c1, c2, c3 = st.columns([1, 1.5, 1])
                c1.markdown(f"**{sym}**")
                c2.markdown(f"`{format_currency(price)}`")
                c3.markdown(
                    f"<span style='color: {change_color}; font-family: JetBrains Mono, monospace; font-size: 0.85rem;'>"
                    f"{change_sign}{change:.2f}%</span>",
                    unsafe_allow_html=True,
                )
    else:
        st.caption("Add symbols to your watchlist in the sidebar.")

    st.markdown("---")

    # Quick analysis
    st.markdown("### Quick Analysis")
    quick_sym = st.text_input(
        "Symbol",
        placeholder="Enter symbol...",
        key="quick_analysis_input",
        label_visibility="collapsed",
    )

    if quick_sym:
        quick_sym = quick_sym.upper().strip()
        with st.spinner(f"Analyzing {quick_sym}..."):
            price_data = get_stock_price(quick_sym)
            tech = get_technical_analysis(quick_sym)

        if "error" not in price_data:
            st.metric("Price", format_currency(price_data.get("current_price", 0)),
                       delta=format_percent(price_data.get("change_percent", 0)))

            if "error" not in tech:
                rsi = tech.get("rsi", {})
                macd = tech.get("macd", {})

                c1, c2 = st.columns(2)
                c1.metric("RSI", f"{rsi.get('value', '--'):.1f}" if isinstance(rsi.get('value'), (int, float)) else "--")
                c2.metric("MACD Signal", macd.get("trend", "--").title())

                rsi_val = rsi.get("value", 50)
                macd_hist = macd.get("histogram", 0) or 0
                if isinstance(rsi_val, (int, float)) and rsi_val < 30 and macd_hist > 0:
                    rec = "BUY"
                elif isinstance(rsi_val, (int, float)) and rsi_val > 70 and macd_hist < 0:
                    rec = "SELL"
                else:
                    rec = "HOLD"

                badge_class = "buy" if "BUY" in rec else "sell" if "SELL" in rec else "neutral"
                st.markdown(f'<span class="score-badge {badge_class}" style="font-size: 1rem;">{rec}</span>', unsafe_allow_html=True)

            if st.button("Full Analysis", key="goto_full_analysis"):
                st.session_state.selected_symbol = quick_sym
                st.switch_page("pages/2_Stock_Analysis.py")
        else:
            st.error(f"Could not find data for '{quick_sym}'.")

# ─── News Feed ───────────────────────────────────────────────
st.markdown("---")
st.markdown("### Latest News")

news_symbol = st.session_state.get("selected_symbol", "") or "AAPL"
news = get_company_news(news_symbol)

if news:
    # Featured article (first one, full-width with thumbnail)
    featured = news[0]
    render_news_card(
        title=featured.get("title", "Untitled"),
        source=featured.get("source", ""),
        date=format_date(featured.get("published_at", "")),
        description=featured.get("description", ""),
        url=featured.get("url", ""),
        thumbnail=featured.get("thumbnail", ""),
        content_type=featured.get("type", ""),
    )

    # Remaining articles in 2-column grid
    cols = st.columns(2)
    for i, article in enumerate(news[1:9]):
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
    st.caption(f"No recent news found for {news_symbol}.")
