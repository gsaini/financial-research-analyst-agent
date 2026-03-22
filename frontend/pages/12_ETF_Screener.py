"""
ETF Recommendations - AI-driven ETF picks based on thorough thematic analysis.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_css, COLORS, get_plotly_layout
from utils.session import init_session_state
from utils.formatters import format_currency, format_large_number, format_percent
from utils.data_service import screen_etfs
from components.header import render_header
from components.plotly_charts import create_horizontal_bar, create_grouped_bar

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(page_title="ETF Recommendations | FinancialAI", page_icon=":bar_chart:", layout="wide", initial_sidebar_state="collapsed")
inject_css()
init_session_state()
render_header()

st.markdown("## ETF Recommendations")
st.caption("Top 10 ETF picks ranked by AI analysis across 17 investment themes")

# ─── Auto-run full analysis ──────────────────────────────────

with st.spinner("Analyzing 17 investment themes and scoring ETFs..."):
    result = screen_etfs(top_n=10)

if "error" in result:
    st.error(f"Analysis failed: {result['error']}")
    st.stop()

top_recs = result.get("top_recommendations", [])
all_etfs = result.get("all_etfs", [])
theme_rankings = result.get("theme_rankings", [])

if not top_recs:
    st.warning("No ETF data available at this time. Please try again later.")
    st.stop()

# ─── Summary KPIs ────────────────────────────────────────────

k1, k2, k3, k4 = st.columns(4)
k1.metric("Themes Analyzed", result.get("total_themes_analyzed", 0))
k2.metric("ETFs Screened", result.get("total_etfs_screened", 0))
k3.metric("Top Pick", top_recs[0]["symbol"] if top_recs else "--")
k4.metric(
    "Top Score",
    f"{top_recs[0]['composite_score']}/100" if top_recs else "--",
)


# ─── Section header helper ───────────────────────────────────

def _section(title: str):
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 0.75rem; margin: 1.5rem 0 1rem;">
            <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
            <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: #fafafa; font-size: 0.9rem;
                        font-weight: 600; letter-spacing: -0.01em;">{title}</h3>
            <div style="flex: 1; height: 1px; background: linear-gradient(90deg, rgba(255,255,255,0.06), transparent);"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Top 10 Recommendation Cards ────────────────────────────

_section("Top 10 Recommended ETFs")

REC_COLORS = {
    "Strong Buy": "#22c55e",
    "Buy": "#4ade80",
    "Hold": "#eab308",
    "Underweight": "#f97316",
    "Avoid": "#ef4444",
}

for row_start in range(0, len(top_recs), 2):
    cols = st.columns(2)
    for j, col in enumerate(cols):
        idx = row_start + j
        if idx >= len(top_recs):
            break
        etf = top_recs[idx]
        rank = idx + 1

        rec = etf.get("recommendation", "Hold")
        rc = REC_COLORS.get(rec, "#a1a1aa")

        returns = etf.get("returns", {})
        ret_1y = returns.get("1y")
        ret_1y_str = format_percent(ret_1y) if ret_1y is not None else "--"
        ret_1y_color = "#22c55e" if (ret_1y or 0) >= 0 else "#ef4444"

        ret_3m = returns.get("3m")
        ret_3m_str = format_percent(ret_3m) if ret_3m is not None else "--"
        ret_3m_color = "#22c55e" if (ret_3m or 0) >= 0 else "#ef4444"

        ret_ytd = returns.get("ytd")
        ret_ytd_str = format_percent(ret_ytd) if ret_ytd is not None else "--"
        ret_ytd_color = "#22c55e" if (ret_ytd or 0) >= 0 else "#ef4444"

        expense = etf.get("expense_ratio")
        expense_str = f"{expense * 100:.2f}%" if expense else "--"

        assets = etf.get("total_assets")
        assets_str = format_large_number(assets) if assets else "--"

        vol = etf.get("volatility")
        vol_str = f"{vol:.1f}%" if vol else "--"

        with col:
            st.markdown(
                f"""
                <div class="card" style="position: relative; overflow: hidden;">
                    <div style="position: absolute; top: 0; left: 0; padding: 0.35rem 0.7rem;
                                background: rgba(99, 102, 241, 0.1); color: #818cf8; font-size: 0.7rem;
                                font-weight: 700; border-radius: 16px 0 8px 0; font-family: 'IBM Plex Mono', monospace;">
                        #{rank}
                    </div>
                    <div style="position: absolute; top: 0; right: 0; padding: 0.35rem 0.75rem;
                                background: {rc}12; color: {rc}; font-size: 0.65rem;
                                font-weight: 600; border-radius: 0 16px 0 8px; border-left: 1px solid {rc}25;
                                border-bottom: 1px solid {rc}25; font-family: 'IBM Plex Mono', monospace;">
                        {rec}
                    </div>
                    <div style="padding-top: 0.25rem;">
                        <div style="display: flex; align-items: baseline; gap: 0.5rem; margin-bottom: 0.125rem;">
                            <span style="font-family: 'IBM Plex Mono', monospace; font-size: 1.2rem;
                                         font-weight: 700; color: #fafafa;">{etf['symbol']}</span>
                            <span style="font-size: 0.85rem; font-weight: 600; color: #6366f1;">
                                {etf['composite_score']}/100
                            </span>
                        </div>
                        <div style="font-size: 0.78rem; color: #a1a1aa; margin-bottom: 0.375rem;
                                    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 90%;">
                            {etf.get('name', etf['symbol'])}
                        </div>
                        <div style="font-size: 0.675rem; color: #52525b; margin-bottom: 0.75rem;">
                            {etf.get('theme', '')} &middot; {etf.get('risk_level', '')}
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem;
                                padding: 0.625rem 0; border-top: 1px solid rgba(255,255,255,0.06);
                                border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">YTD</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem;
                                        font-weight: 600; color: {ret_ytd_color};">{ret_ytd_str}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">3M</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem;
                                        font-weight: 600; color: {ret_3m_color};">{ret_3m_str}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">1Y</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem;
                                        font-weight: 600; color: {ret_1y_color};">{ret_1y_str}</div>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; padding-top: 0.5rem;">
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">Expense</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #a1a1aa;">{expense_str}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">AUM</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #a1a1aa;">{assets_str}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">Volatility</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #a1a1aa;">{vol_str}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ─── Performance Comparison Chart ────────────────────────────

_section("Performance Comparison")

horizon_labels = ["1W", "1M", "3M", "6M", "1Y", "YTD"]
horizon_keys = ["1w", "1m", "3m", "6m", "1y", "ytd"]
chart_colors = ["#6366f1", "#8b5cf6", "#22c55e", "#eab308", "#ef4444", "#3b82f6", "#ec4899", "#14b8a6", "#f97316", "#06b6d4"]

series_data = []
for i, etf in enumerate(top_recs):
    returns = etf.get("returns", {})
    values = [returns.get(k) or 0 for k in horizon_keys]
    series_data.append({
        "name": etf["symbol"],
        "values": values,
        "color": chart_colors[i % len(chart_colors)],
    })

fig = create_grouped_bar(horizon_labels, series_data, title="Returns by Horizon (%)", height=420)
st.plotly_chart(fig, use_container_width=True)

# ─── Composite Score Ranking ─────────────────────────────────

_section("Composite Score Ranking")

score_etfs = list(reversed(top_recs))
score_labels = [e["symbol"] for e in score_etfs]
score_values = [e["composite_score"] for e in score_etfs]
score_colors = []
for s in score_values:
    if s >= 75:
        score_colors.append("#22c55e")
    elif s >= 60:
        score_colors.append("#4ade80")
    elif s >= 45:
        score_colors.append("#eab308")
    else:
        score_colors.append("#ef4444")

fig_scores = create_horizontal_bar(score_labels, score_values, title="Composite Score (0-100)", colors=score_colors)
fig_scores.update_layout(height=max(280, len(score_etfs) * 36 + 80))
st.plotly_chart(fig_scores, use_container_width=True)

# ─── Theme Rankings ──────────────────────────────────────────

if theme_rankings:
    _section("Theme Rankings")

    theme_df = pd.DataFrame([
        {
            "Theme": t["theme_name"],
            "Health": t["health_score"],
            "Momentum": t["momentum_score"],
            "Risk": t["risk_level"],
            "1Y Perf": t.get("performance_1y", "--"),
            "YTD Perf": t.get("performance_ytd", "--"),
            "Stage": t.get("growth_stage", ""),
        }
        for t in theme_rankings
    ])

    st.dataframe(
        theme_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Health": st.column_config.ProgressColumn("Health", min_value=0, max_value=100, format="%d"),
            "Momentum": st.column_config.ProgressColumn("Momentum", min_value=0, max_value=100, format="%d"),
        },
    )

# ─── All Screened ETFs ───────────────────────────────────────

with st.expander("All Screened ETFs", expanded=False):
    full_df = pd.DataFrame([
        {
            "Symbol": e["symbol"],
            "Name": e.get("name", ""),
            "Theme": e.get("theme", ""),
            "Score": e["composite_score"],
            "Rec": e.get("recommendation", ""),
            "Price": format_currency(e.get("current_price")),
            "1M": format_percent(e.get("returns", {}).get("1m")),
            "3M": format_percent(e.get("returns", {}).get("3m")),
            "1Y": format_percent(e.get("returns", {}).get("1y")),
            "Vol": f"{e['volatility']:.1f}%" if e.get("volatility") else "--",
            "Risk": e.get("risk_level", ""),
        }
        for e in all_etfs
    ])
    st.dataframe(full_df, use_container_width=True, hide_index=True)

# ─── Methodology ─────────────────────────────────────────────

with st.expander("Scoring Methodology", expanded=False):
    st.markdown("""
**Composite Score (0-100)** is calculated from five weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Theme Health | 30% | Overall health score of the underlying investment theme |
| Theme Momentum | 20% | Short/medium/long-term momentum of theme constituents |
| ETF 3M Return | 20% | Recent 3-month ETF price performance |
| ETF 1Y Return | 15% | Longer-term 1-year price trend |
| Volatility | 15% | Lower annualized volatility scores higher |

**Recommendation tiers:** Strong Buy (75+), Buy (60-74), Hold (45-59), Underweight (30-44), Avoid (<30)

Data sourced from Yahoo Finance. Analysis covers 17 investment themes and ~50 reference ETFs.
This is for informational purposes only and does not constitute financial advice.
    """)


# ─── AI Advisor CTA ─────────────────────────────────────────

st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
_section("Have Questions?")

st.markdown(
    """
    <div class="card" style="text-align: center; padding: 1.5rem;">
        <div style="font-size: 0.95rem; font-weight: 600; color: #fafafa; margin-bottom: 0.375rem;">
            Ask our AI Advisor about any ETF, stock, or investment strategy
        </div>
        <div style="font-size: 0.8rem; color: #71717a;">
            Get personalized buy/sell guidance, holding period advice, risk analysis, and portfolio recommendations
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
if st.button("Open AI Advisor", use_container_width=True):
    st.switch_page("app.py")
