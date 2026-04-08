"""
Alert & Notification Center - Create, manage, and evaluate
price, technical, calendar, and risk alerts.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_css, COLORS
from utils.session import init_session_state
from utils.data_service import (
    create_alert, remove_alert, get_all_alerts,
    evaluate_alerts, get_alert_types, get_triggered_alerts,
)
from components.header import render_header

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Alerts | FinancialAI",
    page_icon=":bell:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## Alert Center")
st.caption("Create and manage price, technical, calendar, and risk alerts")

# ─── Tabs ────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Create Alert", "Active Alerts", "Triggered History"])

# ─── Tab 1: Create Alert ────────────────────────────────────
with tab1:
    st.markdown("### New Alert")

    alert_types = get_alert_types()
    type_options = {t["type"]: f"{t['type']} — {t['description']}" for t in alert_types}

    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input(
            "Stock Symbol",
            value="AAPL",
            placeholder="e.g., AAPL, NVDA, GME",
            key="alert_symbol",
        ).strip().upper()

    with col2:
        selected_type = st.selectbox(
            "Alert Type",
            options=list(type_options.keys()),
            format_func=lambda x: type_options[x],
            key="alert_type_select",
        )

    col3, col4 = st.columns(2)
    with col3:
        # Dynamic threshold label based on type
        if "price" in selected_type:
            label = "Price Threshold ($)"
            default = 200.0
        elif "rsi" in selected_type:
            label = "RSI Threshold"
            default = 30.0 if "oversold" in selected_type else 70.0
        elif "volume" in selected_type or "spike" in selected_type:
            label = "Multiplier (e.g., 2.5x average)"
            default = 2.5
        elif "percent" in selected_type:
            label = "Percent Change (%)"
            default = 5.0
        elif "earnings" in selected_type or "dividend" in selected_type:
            label = "Days Before Event"
            default = 5.0
        elif "short" in selected_type:
            label = "Short % of Float Threshold"
            default = 20.0
        elif "cross" in selected_type or "macd" in selected_type:
            label = "Not applicable (set to 0)"
            default = 0.0
        else:
            label = "Threshold"
            default = 0.0

        threshold = st.number_input(label, value=default, key="alert_threshold")

    with col4:
        message = st.text_input(
            "Custom Message (optional)",
            placeholder="e.g., Buy signal for my watchlist",
            key="alert_message",
        )

    repeat = st.checkbox("Repeat alert (re-arm after triggering)", key="alert_repeat")

    if st.button("Create Alert", type="primary", key="create_alert_btn"):
        if not symbol:
            st.error("Symbol is required")
        else:
            result = create_alert(symbol, selected_type, threshold, message, repeat)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(f"Alert created: {result.get('alert', {}).get('id', '')}")

    # Quick presets
    st.markdown("---")
    st.markdown("**Quick Presets**")
    pcols = st.columns(4)
    with pcols[0]:
        if st.button("RSI Oversold (30)", key="preset_rsi"):
            sym = st.session_state.get("alert_symbol", "AAPL").strip().upper()
            r = create_alert(sym, "rsi_oversold", 30, f"{sym} RSI oversold alert")
            st.success(f"Created RSI oversold alert for {sym}") if "error" not in r else st.error(r["error"])
    with pcols[1]:
        if st.button("Earnings 5 Days", key="preset_earnings"):
            sym = st.session_state.get("alert_symbol", "AAPL").strip().upper()
            r = create_alert(sym, "earnings_soon", 5, f"{sym} earnings approaching")
            st.success(f"Created earnings alert for {sym}") if "error" not in r else st.error(r["error"])
    with pcols[2]:
        if st.button("Golden Cross", key="preset_golden"):
            sym = st.session_state.get("alert_symbol", "AAPL").strip().upper()
            r = create_alert(sym, "golden_cross", 0, f"{sym} golden cross")
            st.success(f"Created golden cross alert for {sym}") if "error" not in r else st.error(r["error"])
    with pcols[3]:
        if st.button("Volume 3x Spike", key="preset_vol"):
            sym = st.session_state.get("alert_symbol", "AAPL").strip().upper()
            r = create_alert(sym, "volume_spike", 3.0, f"{sym} volume surge")
            st.success(f"Created volume alert for {sym}") if "error" not in r else st.error(r["error"])

# ─── Tab 2: Active Alerts ───────────────────────────────────
with tab2:
    ecol1, ecol2 = st.columns([3, 1])
    with ecol2:
        if st.button("Evaluate All Alerts", type="primary", key="eval_btn"):
            triggered = evaluate_alerts()
            if triggered:
                st.success(f"{len(triggered)} alert(s) triggered!")
                for t in triggered:
                    st.info(f"**{t.get('symbol', '')}**: {t.get('trigger_message', t.get('message', ''))}")
            else:
                st.info("No alerts triggered")

    alerts = get_all_alerts(status="active")

    if not alerts:
        st.info("No active alerts. Create one in the 'Create Alert' tab.")
    else:
        st.markdown(f"### Active Alerts ({len(alerts)})")

        for alert in alerts:
            aid = alert.get("id", "")
            sym = alert.get("symbol", "")
            atype = alert.get("alert_type", "")
            thresh = alert.get("threshold", 0)
            msg = alert.get("message", "")
            created = alert.get("created_at", "")[:19]
            repeat_flag = "🔄" if alert.get("repeat") else ""

            with st.container():
                acol1, acol2, acol3 = st.columns([4, 2, 1])
                with acol1:
                    st.markdown(f"**{sym}** — `{atype}` {repeat_flag}")
                    st.caption(f"Threshold: {thresh} | Created: {created}")
                    if msg:
                        st.caption(msg)
                with acol2:
                    st.markdown(f"ID: `{aid[:20]}...`")
                with acol3:
                    if st.button("Delete", key=f"del_{aid}"):
                        remove_alert(aid)
                        st.rerun()
                st.markdown("---")

# ─── Tab 3: Triggered History ────────────────────────────────
with tab3:
    history = get_triggered_alerts()

    if not history:
        st.info("No alerts have been triggered yet. Create alerts and evaluate them.")
    else:
        st.markdown(f"### Triggered Alerts ({len(history)})")

        rows = []
        for h in reversed(history):
            rows.append({
                "Symbol": h.get("symbol", ""),
                "Type": h.get("alert_type", ""),
                "Message": h.get("trigger_message", h.get("message", "")),
                "Value": h.get("current_value", ""),
                "Triggered At": (h.get("triggered_at") or "")[:19],
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ─── Footer ─────────────────────────────────────────────────
st.markdown("---")
st.caption("Alerts are evaluated on-demand or via the WebSocket endpoint (/ws/alerts). In-memory storage — alerts reset on server restart.")
