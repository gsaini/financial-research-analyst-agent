"""
Macro Economy Dashboard - FRED macroeconomic data, treasury yields,
rate environment analysis, and sector impact assessment.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_css, COLORS
from utils.session import init_session_state
from utils.formatters import format_percent
from components.header import render_header
from components.plotly_charts import create_gauge_chart, create_horizontal_bar

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Macro Economy | FinancialAI",
    page_icon=":globe_with_meridians:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## Macroeconomic Dashboard")
st.caption("Key economic indicators, treasury yields, and rate environment analysis (FRED)")

# ─── Data fetch helpers ─────────────────────────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def _get_macro_summary():
    from src.tools.macro_data import get_macro_summary
    return get_macro_summary()


@st.cache_data(ttl=1800, show_spinner=False)
def _get_treasury_yields():
    from src.tools.macro_data import get_treasury_yields
    return get_treasury_yields()


@st.cache_data(ttl=1800, show_spinner=False)
def _get_rate_env():
    from src.tools.macro_data import get_rate_environment
    return get_rate_environment()


@st.cache_data(ttl=1800, show_spinner=False)
def _get_macro_context(symbol: str):
    from src.tools.macro_data import get_macro_context_for_stock
    return get_macro_context_for_stock(symbol)


# ─── Main content ────────────────────────────────────────────

with st.spinner("Loading macroeconomic data from FRED..."):
    macro = _get_macro_summary()
    yields = _get_treasury_yields()
    rate_env = _get_rate_env()

# Check availability
if macro.get("source") == "unavailable":
    st.warning(
        "FRED API is not configured. Set `FRED_API_KEY` in your `.env` file "
        "to enable macroeconomic data. You can get a free key at "
        "[fred.stlouisfed.org/docs/api](https://fred.stlouisfed.org/docs/api/api_key.html)."
    )
    st.stop()

# ─── Key Indicators Row ─────────────────────────────────────
st.markdown("### Key Economic Indicators")

indicators = macro.get("indicators", {})

cols = st.columns(4)

indicator_display = [
    ("Federal Funds Rate", "federal_funds_rate", "%"),
    ("CPI (YoY)", "cpi_yoy", "%"),
    ("Unemployment", "unemployment", "%"),
    ("GDP Growth", "gdp_growth", "%"),
]

for i, (label, key, suffix) in enumerate(indicator_display):
    with cols[i]:
        data = indicators.get(key, {})
        current = data.get("current", "N/A")
        direction = data.get("direction", "")
        arrow = "▲" if direction == "rising" else "▼" if direction == "falling" else "→"
        color = (
            COLORS.get("accent_red", "#ff4444") if direction == "rising" and key in ("cpi_yoy", "unemployment")
            else COLORS.get("accent_green", "#00cc66") if direction == "falling" and key in ("cpi_yoy", "unemployment")
            else COLORS.get("accent_green", "#00cc66") if direction == "rising" and key == "gdp_growth"
            else COLORS.get("text_secondary", "#888")
        )
        if isinstance(current, (int, float)):
            display_val = f"{current:.2f}{suffix}"
        else:
            display_val = str(current)
        st.metric(label=label, value=display_val, delta=f"{arrow} {direction}")

# Second row
cols2 = st.columns(4)
indicator_display_2 = [
    ("Consumer Confidence", "consumer_confidence", ""),
    ("PMI (Manufacturing)", "pmi", ""),
    ("Housing Starts", "housing_starts", "K"),
]
for i, (label, key, suffix) in enumerate(indicator_display_2):
    with cols2[i]:
        data = indicators.get(key, {})
        current = data.get("current", "N/A")
        direction = data.get("direction", "")
        arrow = "▲" if direction == "rising" else "▼" if direction == "falling" else "→"
        if isinstance(current, (int, float)):
            display_val = f"{current:.1f}{suffix}"
        else:
            display_val = str(current)
        st.metric(label=label, value=display_val, delta=f"{arrow} {direction}")

st.markdown("---")

# ─── Treasury Yields ────────────────────────────────────────
st.markdown("### Treasury Yields & Yield Curve")

ycol1, ycol2 = st.columns([2, 1])

with ycol1:
    yield_data = yields.get("yields", {})
    if yield_data:
        yield_df = pd.DataFrame([
            {"Maturity": "2-Year", "Yield (%)": yield_data.get("2y", 0)},
            {"Maturity": "10-Year", "Yield (%)": yield_data.get("10y", 0)},
            {"Maturity": "30-Year", "Yield (%)": yield_data.get("30y", 0)},
        ])
        st.bar_chart(yield_df.set_index("Maturity"), color=COLORS.get("accent_blue", "#4488ff"))

with ycol2:
    spread = yields.get("spread_2y_10y", 0)
    curve_status = yields.get("curve_status", "unknown")

    status_color = (
        COLORS.get("accent_green", "#00cc66") if curve_status == "normal"
        else COLORS.get("accent_red", "#ff4444") if curve_status == "inverted"
        else COLORS.get("accent_yellow", "#ffaa00")
    )

    st.markdown(f"""
    **2Y-10Y Spread**: `{spread:.2f}%`

    **Curve Status**: <span style="color:{status_color};font-weight:bold">{curve_status.upper()}</span>
    """, unsafe_allow_html=True)

    if curve_status == "inverted":
        st.error("Yield curve is inverted — historically a leading recession indicator.")
    elif curve_status == "flat":
        st.warning("Yield curve is flat — economic uncertainty signal.")
    else:
        st.success("Yield curve is normal — consistent with economic expansion.")

st.markdown("---")

# ─── Rate Environment ───────────────────────────────────────
st.markdown("### Rate Environment Analysis")

rcol1, rcol2 = st.columns(2)

with rcol1:
    st.markdown("**Fed Policy Stance**")
    stance = rate_env.get("fed_stance", "unknown")
    real_rate = rate_env.get("real_rate", 0)
    inflation_trend = rate_env.get("inflation_trend", "stable")

    stance_icon = {"hiking": "📈", "cutting": "📉", "holding": "⏸️"}.get(stance, "❓")
    st.markdown(f"- **Stance**: {stance_icon} {stance.title()}")
    st.markdown(f"- **Real Rate**: `{real_rate:.2f}%` (Fed Funds − CPI)")
    st.markdown(f"- **Inflation Trend**: {inflation_trend.title()}")

with rcol2:
    st.markdown("**Sector Impact Assessment**")
    sector_impact = rate_env.get("sector_impact", {})
    if sector_impact:
        for sector, impact in sector_impact.items():
            direction = impact.get("direction", "neutral")
            icon = "🟢" if direction == "positive" else "🔴" if direction == "negative" else "⚪"
            st.markdown(f"- {icon} **{sector}**: {impact.get('assessment', 'N/A')}")

st.markdown("---")

# ─── Stock-Specific Macro Context ────────────────────────────
st.markdown("### Stock-Specific Macro Context")
st.caption("See how the current macro environment affects a specific stock's sector")

symbol = st.text_input(
    "Stock Symbol",
    value=st.session_state.get("selected_symbol", "AAPL"),
    placeholder="Enter ticker (e.g., AAPL)",
    key="macro_symbol",
).strip().upper()

if symbol:
    with st.spinner(f"Analyzing macro context for {symbol}..."):
        ctx = _get_macro_context(symbol)

    if ctx.get("source") == "unavailable":
        st.info("FRED API not configured for stock-specific analysis.")
    elif "error" in ctx:
        st.error(ctx["error"])
    else:
        mcol1, mcol2 = st.columns(2)
        with mcol1:
            st.markdown(f"**Sector**: {ctx.get('sector', 'N/A')}")
            st.markdown(f"**Rate Sensitivity**: {ctx.get('rate_sensitivity', 'N/A')}")
            st.markdown(f"**Macro Impact**: {ctx.get('impact_direction', 'N/A')}")
        with mcol2:
            st.markdown(f"**Assessment**: {ctx.get('assessment', 'N/A')}")
            factors = ctx.get("key_factors", [])
            if factors:
                st.markdown("**Key Factors**:")
                for f in factors:
                    st.markdown(f"- {f}")

# ─── Footer ─────────────────────────────────────────────────
st.markdown("---")
st.caption("Data source: Federal Reserve Economic Data (FRED) | Updated every 30 minutes")
