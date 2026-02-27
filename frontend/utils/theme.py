"""
Theme utilities - CSS injection and design constants.
"""

import os
import streamlit as st


# Design color constants for use in Plotly charts and dynamic styling
COLORS = {
    "bg_base": "#09090b",
    "bg_primary": "#0c0c0f",
    "bg_secondary": "#131316",
    "bg_card": "#1c1c21",
    "bg_card_hover": "#222228",
    "text_primary": "#fafafa",
    "text_secondary": "#a1a1aa",
    "text_muted": "#71717a",
    "accent_primary": "#6366f1",
    "accent_secondary": "#8b5cf6",
    "success": "#22c55e",
    "warning": "#eab308",
    "danger": "#ef4444",
    "border": "rgba(255, 255, 255, 0.08)",
    "border_light": "rgba(255, 255, 255, 0.06)",
}

# Plotly chart template
PLOTLY_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": COLORS["bg_secondary"],
    "font": {"color": COLORS["text_primary"], "family": "Inter, -apple-system, sans-serif"},
    "xaxis": {
        "gridcolor": COLORS["border_light"],
        "zerolinecolor": COLORS["border"],
        "tickfont": {"color": COLORS["text_muted"]},
    },
    "yaxis": {
        "gridcolor": COLORS["border_light"],
        "zerolinecolor": COLORS["border"],
        "tickfont": {"color": COLORS["text_muted"]},
    },
    "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
}


def inject_css():
    """Inject the custom CSS theme into the Streamlit app."""
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")

    css_content = ""
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            css_content = f.read()

    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


def get_plotly_layout(**overrides):
    """Get a copy of the default Plotly layout with optional overrides.

    Performs deep merge for dict values (e.g. xaxis, yaxis, margin, font)
    so overrides extend the defaults rather than replacing them.
    """
    import copy
    layout = copy.deepcopy(PLOTLY_LAYOUT)
    for key, value in overrides.items():
        if key in layout and isinstance(layout[key], dict) and isinstance(value, dict):
            layout[key].update(value)
        else:
            layout[key] = value
    return layout
