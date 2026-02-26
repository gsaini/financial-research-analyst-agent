"""
Reports - Generate and download research reports.
"""

import json
from datetime import datetime

import streamlit as st
from utils.theme import inject_css
from utils.session import init_session_state
from utils.formatters import format_currency, format_percent, format_large_number, format_number, format_date
from utils.data_service import (
    get_stock_price, get_company_info, get_technical_analysis,
    get_financial_health, get_company_news, analyze_disruption, analyze_earnings,
)
from components.sidebar import render_sidebar

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(page_title="Reports | FinancialAI", page_icon=":chart_with_upwards_trend:", layout="wide")
inject_css()
init_session_state()
render_sidebar()

st.markdown("## Research Reports")
st.caption("Generate and download investment research reports")

# ─── Report Configuration ────────────────────────────────────
c1, c2 = st.columns([2, 1])

with c1:
    symbols_input = st.text_input(
        "Symbols (comma-separated)",
        value=st.session_state.get("selected_symbol", "AAPL"),
        placeholder="e.g. AAPL, MSFT",
        key="report_symbols",
    )

with c2:
    report_format = st.selectbox("Format", ["Markdown", "JSON"], key="report_format")

symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

# Section selection
st.markdown("**Include Sections:**")
sections = st.columns(5)
include_overview = sections[0].checkbox("Overview", value=True)
include_technical = sections[1].checkbox("Technical", value=True)
include_fundamental = sections[2].checkbox("Fundamental", value=True)
include_disruption = sections[3].checkbox("Disruption", value=False)
include_earnings = sections[4].checkbox("Earnings", value=False)

generate = st.button("Generate Report", use_container_width=False)

if not generate:
    st.info("Configure your report above and click Generate.")
    st.stop()

if not symbols:
    st.warning("Enter at least one symbol.")
    st.stop()

# ─── Generate Report ─────────────────────────────────────────
with st.spinner(f"Generating report for {', '.join(symbols)}..."):
    report_data = {
        "title": "Investment Research Report",
        "generated_at": datetime.utcnow().isoformat(),
        "symbols": symbols,
        "sections": {},
    }

    markdown_parts = [
        f"# Investment Research Report",
        f"**Generated:** {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}",
        f"**Symbols:** {', '.join(symbols)}",
        "",
        "---",
        "",
    ]

    for symbol in symbols:
        markdown_parts.append(f"## {symbol}")
        symbol_data = {}

        # Overview
        if include_overview:
            price = get_stock_price(symbol)
            company = get_company_info(symbol)

            if "error" not in price:
                symbol_data["overview"] = {
                    "name": company.get("name", symbol),
                    "sector": company.get("sector", "N/A"),
                    "industry": company.get("industry", "N/A"),
                    "price": price.get("current_price", 0),
                    "change_percent": price.get("change_percent", 0),
                    "market_cap": price.get("market_cap", 0),
                    "pe_ratio": price.get("pe_ratio"),
                    "eps": price.get("eps"),
                    "52_week_high": price.get("52_week_high"),
                    "52_week_low": price.get("52_week_low"),
                }

                markdown_parts.extend([
                    f"### Overview",
                    f"- **Company:** {company.get('name', symbol)}",
                    f"- **Sector:** {company.get('sector', 'N/A')} / {company.get('industry', 'N/A')}",
                    f"- **Price:** {format_currency(price.get('current_price'))} ({format_percent(price.get('change_percent', 0))})",
                    f"- **Market Cap:** {format_large_number(price.get('market_cap'))}",
                    f"- **P/E Ratio:** {format_number(price.get('pe_ratio'))}",
                    f"- **EPS:** {format_currency(price.get('eps'))}",
                    f"- **52-Week Range:** {format_currency(price.get('52_week_low'))} - {format_currency(price.get('52_week_high'))}",
                    "",
                ])

        # Technical
        if include_technical:
            tech = get_technical_analysis(symbol)
            if "error" not in tech:
                rsi = tech.get("rsi", {})
                macd = tech.get("macd", {})
                ma = tech.get("moving_averages", {})

                symbol_data["technical"] = {
                    "rsi": rsi,
                    "macd": macd,
                    "moving_averages": ma,
                    "bollinger_bands": tech.get("bollinger_bands", {}),
                    "patterns": tech.get("patterns", {}),
                }

                # Recommendation logic
                rsi_val = rsi.get("value", 50)
                macd_hist = macd.get("histogram", 0) or 0
                if isinstance(rsi_val, (int, float)) and rsi_val < 30 and macd_hist > 0:
                    rec = "BUY"
                elif isinstance(rsi_val, (int, float)) and rsi_val > 70 and macd_hist < 0:
                    rec = "SELL"
                else:
                    rec = "HOLD"

                markdown_parts.extend([
                    f"### Technical Analysis",
                    f"- **RSI (14):** {format_number(rsi.get('value'))} ({rsi.get('signal', 'N/A')})",
                    f"- **MACD Trend:** {str(macd.get('trend', 'N/A')).title()}",
                    f"- **MACD Histogram:** {format_number(macd.get('histogram'), 4)}",
                    f"- **MA Trend:** {str(ma.get('trend', 'N/A')).title()}",
                    f"- **Signal:** **{rec}**",
                    "",
                ])

                patterns = tech.get("patterns", {}).get("patterns_detected", [])
                if patterns:
                    markdown_parts.append("**Patterns Detected:**")
                    for p in patterns:
                        markdown_parts.append(f"- {p.get('name', 'Unknown')} ({p.get('implication', 'neutral')}, {p.get('confidence', 0)*100:.0f}% confidence)")
                    markdown_parts.append("")

        # Fundamental
        if include_fundamental:
            health = get_financial_health(symbol)
            if "error" not in health:
                symbol_data["fundamental"] = health

                markdown_parts.extend([
                    f"### Fundamental Analysis",
                    f"- **Health Score:** {format_number(health.get('health_score'))}/10",
                    f"- **Assessment:** {health.get('overall_assessment', 'N/A')}",
                    "",
                ])

                strengths = health.get("strengths", [])
                if strengths:
                    markdown_parts.append("**Strengths:**")
                    for s in strengths:
                        markdown_parts.append(f"- {s}")
                    markdown_parts.append("")

                weaknesses = health.get("weaknesses", [])
                if weaknesses:
                    markdown_parts.append("**Weaknesses:**")
                    for w in weaknesses:
                        markdown_parts.append(f"- {w}")
                    markdown_parts.append("")

        # Disruption
        if include_disruption:
            disruption = analyze_disruption(symbol)
            if "error" not in disruption:
                symbol_data["disruption"] = {
                    "score": disruption.get("disruption_score"),
                    "classification": disruption.get("classification"),
                    "strengths": disruption.get("strengths", []),
                    "risk_factors": disruption.get("risk_factors", []),
                }

                markdown_parts.extend([
                    f"### Disruption Analysis",
                    f"- **Disruption Score:** {disruption.get('disruption_score', 0)}/100",
                    f"- **Classification:** {disruption.get('classification', 'N/A')}",
                    "",
                ])

        # Earnings
        if include_earnings:
            earnings = analyze_earnings(symbol)
            if "error" not in earnings:
                surprise = earnings.get("earnings_surprise_history", {}).get("last_8_quarters", {})
                quality = earnings.get("earnings_quality", {})

                symbol_data["earnings"] = {
                    "beat_rate": surprise.get("beat_rate"),
                    "average_surprise": surprise.get("average_surprise"),
                    "pattern": surprise.get("pattern"),
                    "quality_score": quality.get("score"),
                    "quality_assessment": quality.get("assessment"),
                }

                markdown_parts.extend([
                    f"### Earnings Analysis",
                    f"- **Beat Rate:** {surprise.get('beat_rate', 'N/A')}",
                    f"- **Avg Surprise:** {surprise.get('average_surprise', 'N/A')}",
                    f"- **Pattern:** {surprise.get('pattern', 'N/A')}",
                    f"- **Quality Score:** {format_number(quality.get('score'))}/10 ({quality.get('assessment', 'N/A')})",
                    "",
                ])

        report_data["sections"][symbol] = symbol_data
        markdown_parts.extend(["", "---", ""])

    # Disclaimer
    markdown_parts.extend([
        "## Disclaimer",
        "This report is generated for informational purposes only and does not constitute financial advice. "
        "Always conduct your own research before making investment decisions.",
        "",
        f"*Generated by FinancialAI Research Platform on {datetime.utcnow().strftime('%B %d, %Y')}*",
    ])

    markdown_content = "\n".join(markdown_parts)
    json_content = json.dumps(report_data, indent=2, default=str)

# ─── Report Preview ──────────────────────────────────────────
st.markdown("---")
st.markdown("### Report Preview")

if report_format == "Markdown":
    st.markdown(markdown_content)
else:
    st.json(report_data)

# ─── Download Buttons ────────────────────────────────────────
st.markdown("---")
st.markdown("### Download")

c1, c2 = st.columns(2)

with c1:
    st.download_button(
        label="Download Markdown",
        data=markdown_content,
        file_name=f"report_{'_'.join(symbols)}_{datetime.utcnow().strftime('%Y%m%d')}.md",
        mime="text/markdown",
        use_container_width=True,
    )

with c2:
    st.download_button(
        label="Download JSON",
        data=json_content,
        file_name=f"report_{'_'.join(symbols)}_{datetime.utcnow().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
    )
