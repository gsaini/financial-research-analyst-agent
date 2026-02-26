"""
Theme utilities - CSS injection and design constants.
"""

import os
import streamlit as st


# Design color constants for use in Plotly charts and dynamic styling
COLORS = {
    "bg_primary": "#0a0e17",
    "bg_secondary": "#111827",
    "bg_card": "#1a2235",
    "bg_card_hover": "#1f2a42",
    "text_primary": "#f9fafb",
    "text_secondary": "#9ca3af",
    "text_muted": "#6b7280",
    "accent_blue": "#3b82f6",
    "accent_violet": "#8b5cf6",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "border": "#374151",
    "border_light": "#1f2937",
}

# Plotly chart template
PLOTLY_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": COLORS["bg_secondary"],
    "font": {"color": COLORS["text_primary"], "family": "Inter, sans-serif"},
    "xaxis": {
        "gridcolor": COLORS["border_light"],
        "zerolinecolor": COLORS["border"],
    },
    "yaxis": {
        "gridcolor": COLORS["border_light"],
        "zerolinecolor": COLORS["border"],
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
