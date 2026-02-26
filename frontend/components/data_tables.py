"""
Styled dataframe and table rendering components.
"""

import streamlit as st
import pandas as pd


def render_styled_dataframe(df: pd.DataFrame, highlight_column: str = None, height: int = None):
    """
    Render a pandas DataFrame with dark theme styling.

    Args:
        df: DataFrame to render
        highlight_column: Column name to apply conditional coloring (green/red for +/-)
        height: Fixed height in pixels (optional)
    """
    if df.empty:
        st.caption("No data available.")
        return

    kwargs = {"use_container_width": True, "hide_index": True}
    if height:
        kwargs["height"] = height

    if highlight_column and highlight_column in df.columns:
        st.dataframe(
            df.style.map(
                lambda val: _color_value(val),
                subset=[highlight_column],
            ),
            **kwargs,
        )
    else:
        st.dataframe(df, **kwargs)


def render_comparison_table(data: list, highlight_symbol: str = None):
    """
    Render a comparison table with optional row highlighting.

    Args:
        data: List of dicts (each dict = one row)
        highlight_symbol: Symbol to highlight in bold
    """
    if not data:
        st.caption("No comparison data available.")
        return

    df = pd.DataFrame(data)

    if highlight_symbol and "symbol" in df.columns:
        def highlight_target(row):
            if row.get("symbol") == highlight_symbol:
                return ["font-weight: 700; background-color: rgba(59, 130, 246, 0.08);"] * len(row)
            return [""] * len(row)

        styled = df.style.apply(highlight_target, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_metrics_table(metrics: dict, title: str = ""):
    """
    Render a vertical key-value metrics table.

    Args:
        metrics: Dict of {label: value}
    """
    if title:
        st.markdown(f"**{title}**")

    if not metrics:
        st.caption("No metrics available.")
        return

    df = pd.DataFrame([
        {"Metric": k, "Value": v}
        for k, v in metrics.items()
    ])

    st.dataframe(df, use_container_width=True, hide_index=True, height=min(400, len(metrics) * 38 + 40))


def _color_value(val):
    """Return CSS for coloring positive/negative values."""
    try:
        v = float(str(val).replace("%", "").replace("+", "").replace("$", "").replace(",", ""))
        if v > 0:
            return "color: #10b981;"
        elif v < 0:
            return "color: #ef4444;"
    except (ValueError, TypeError):
        pass
    return ""
