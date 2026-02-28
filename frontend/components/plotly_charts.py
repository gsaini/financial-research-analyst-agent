"""
Plotly chart builders for supplementary visualizations.
All charts use a consistent dark theme matching the app design.
"""

import plotly.graph_objects as go
from utils.theme import COLORS, get_plotly_layout


def create_gauge_chart(
    value,
    title="",
    min_val=0,
    max_val=100,
    ranges=None,
    height=250,
    suffix="",
):
    """
    Create a gauge chart (e.g., for scores, RSI, health).

    Args:
        value: Current value
        title: Chart title
        ranges: List of dicts [{"range": [0, 30], "color": "red"}, ...]
                Defaults to red/yellow/blue/green quartiles.
        suffix: Value suffix (e.g., '%', '/10')
    """
    if ranges is None:
        ranges = [
            {"range": [0, 30], "color": "rgba(239, 68, 68, 0.3)"},
            {"range": [30, 50], "color": "rgba(245, 158, 11, 0.3)"},
            {"range": [50, 70], "color": "rgba(59, 130, 246, 0.3)"},
            {"range": [70, 100], "color": "rgba(16, 185, 129, 0.3)"},
        ]

    steps = [{"range": r["range"], "color": r["color"]} for r in ranges]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix, "font": {"size": 36, "family": "JetBrains Mono, monospace", "color": COLORS["text_primary"]}},
        title={"text": title, "font": {"size": 14, "color": COLORS["text_secondary"]}},
        gauge={
            "axis": {
                "range": [min_val, max_val],
                "tickcolor": COLORS["text_muted"],
                "tickfont": {"color": COLORS["text_muted"], "size": 10},
            },
            "bar": {"color": COLORS["accent_blue"], "thickness": 0.3},
            "bgcolor": COLORS["bg_card"],
            "borderwidth": 0,
            "steps": steps,
            "threshold": {
                "line": {"color": COLORS["text_primary"], "width": 2},
                "thickness": 0.8,
                "value": value,
            },
        },
    ))

    fig.update_layout(
        **get_plotly_layout(margin={"l": 30, "r": 30, "t": 50, "b": 10}),
        height=height,
    )

    return fig


def create_radar_chart(
    categories,
    values,
    title="",
    comparison_values=None,
    comparison_label="Peer Median",
    height=350,
):
    """
    Create a radar/spider chart for multi-dimensional comparison.

    Args:
        categories: List of metric names
        values: List of values for primary series
        comparison_values: Optional second series for overlay
    """
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(59, 130, 246, 0.15)",
        line={"color": COLORS["accent_blue"], "width": 2},
        name="Company",
        marker={"size": 6, "color": COLORS["accent_blue"]},
    ))

    if comparison_values:
        fig.add_trace(go.Scatterpolar(
            r=comparison_values + [comparison_values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor="rgba(139, 92, 246, 0.1)",
            line={"color": COLORS["accent_violet"], "width": 2, "dash": "dash"},
            name=comparison_label,
            marker={"size": 6, "color": COLORS["accent_violet"]},
        ))

    fig.update_layout(
        **get_plotly_layout(margin={"l": 60, "r": 60, "t": 60, "b": 40}),
        height=height,
        title={"text": title, "font": {"size": 14}},
        polar={
            "bgcolor": COLORS["bg_secondary"],
            "radialaxis": {
                "visible": True,
                "gridcolor": COLORS["border_light"],
                "linecolor": COLORS["border"],
                "tickfont": {"color": COLORS["text_muted"], "size": 10},
            },
            "angularaxis": {
                "gridcolor": COLORS["border_light"],
                "linecolor": COLORS["border"],
                "tickfont": {"color": COLORS["text_secondary"], "size": 11},
            },
        },
        showlegend=bool(comparison_values),
        legend={"font": {"color": COLORS["text_secondary"]}},
    )

    return fig


def create_horizontal_bar(
    labels,
    values,
    title="",
    colors=None,
    height=None,
):
    """Create a horizontal bar chart for rankings/comparisons."""
    if colors is None:
        colors = [COLORS["accent_blue"]] * len(labels)

    if height is None:
        height = max(250, len(labels) * 40 + 80)

    fig = go.Figure(go.Bar(
        y=labels,
        x=values,
        orientation="h",
        marker={"color": colors, "line": {"width": 0}},
        text=[f"{v:.1f}" if isinstance(v, float) else str(v) for v in values],
        textposition="auto",
        textfont={"color": COLORS["text_primary"], "size": 11, "family": "JetBrains Mono"},
    ))

    fig.update_layout(
        **get_plotly_layout(
            margin={"l": 120, "r": 20, "t": 50, "b": 30},
            yaxis={"autorange": "reversed"},
        ),
        height=height,
        title={"text": title, "font": {"size": 14}},
    )

    return fig


def create_grouped_bar(
    categories,
    series_data,
    title="",
    height=400,
):
    """
    Create a grouped bar chart.

    Args:
        categories: X-axis labels
        series_data: List of dicts [{"name": "Company A", "values": [...], "color": "#..."}, ...]
    """
    fig = go.Figure()

    for series in series_data:
        fig.add_trace(go.Bar(
            name=series["name"],
            x=categories,
            y=series["values"],
            marker_color=series.get("color", COLORS["accent_blue"]),
            text=[f"{v:.1f}" if isinstance(v, (int, float)) and v else "" for v in series["values"]],
            textposition="auto",
            textfont={"size": 10, "family": "JetBrains Mono"},
        ))

    fig.update_layout(
        **get_plotly_layout(margin={"l": 50, "r": 20, "t": 50, "b": 60}),
        height=height,
        title={"text": title, "font": {"size": 14}},
        barmode="group",
        legend={"font": {"color": COLORS["text_secondary"]}},
    )

    return fig


def create_heatmap(matrix, x_labels, y_labels, title="", height=400):
    """Create a heatmap for correlation matrices."""
    fig = go.Figure(go.Heatmap(
        z=matrix,
        x=x_labels,
        y=y_labels,
        colorscale=[
            [0, COLORS["danger"]],
            [0.5, COLORS["bg_card"]],
            [1, COLORS["success"]],
        ],
        zmin=-1,
        zmax=1,
        text=[[f"{val:.2f}" for val in row] for row in matrix],
        texttemplate="%{text}",
        textfont={"size": 11, "family": "JetBrains Mono"},
        hovertemplate="X: %{x}<br>Y: %{y}<br>Correlation: %{z:.2f}<extra></extra>",
    ))

    fig.update_layout(
        **get_plotly_layout(margin={"l": 80, "r": 20, "t": 50, "b": 60}),
        height=height,
        title={"text": title, "font": {"size": 14}},
    )

    return fig


def create_earnings_surprise_chart(quarters, surprises, verdicts, height=300):
    """Bar chart for EPS surprises colored by beat/miss."""
    colors = []
    for v in verdicts:
        v_lower = str(v).lower()
        if "beat" in v_lower:
            colors.append(COLORS["success"])
        elif "miss" in v_lower:
            colors.append(COLORS["danger"])
        else:
            colors.append(COLORS["warning"])

    fig = go.Figure(go.Bar(
        x=quarters,
        y=surprises,
        marker_color=colors,
        text=[f"{s:+.1f}%" if isinstance(s, (int, float)) else str(s) for s in surprises],
        textposition="outside",
        textfont={"size": 11, "family": "JetBrains Mono", "color": COLORS["text_primary"]},
    ))

    fig.add_hline(y=0, line_color=COLORS["border"], line_width=1)

    fig.update_layout(
        **get_plotly_layout(margin={"l": 50, "r": 20, "t": 50, "b": 40}),
        height=height,
        title={"text": "EPS Surprise History", "font": {"size": 14}},
        yaxis_title="Surprise %",
    )

    return fig


def create_line_chart(
    dates,
    values,
    title="",
    line_color=None,
    fill=False,
    height=300,
    y_suffix="%",
    show_zero_line=False,
):
    """Create a line chart for time-series data (rolling returns, trends)."""
    if line_color is None:
        line_color = COLORS.get("accent_primary", COLORS.get("accent_blue", "#6366f1"))

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines",
        line={"color": line_color, "width": 2},
        fill="tozeroy" if fill else "none",
        fillcolor=f"rgba(99, 102, 241, 0.08)" if fill else None,
        hovertemplate=f"%{{x}}<br>%{{y:.2f}}{y_suffix}<extra></extra>",
    ))

    if show_zero_line:
        fig.add_hline(y=0, line_color=COLORS["border"], line_width=1, line_dash="dash")

    fig.update_layout(
        **get_plotly_layout(margin={"l": 50, "r": 20, "t": 50, "b": 40}),
        height=height,
        title={"text": title, "font": {"size": 14}},
    )

    return fig


def create_area_chart(
    dates,
    values,
    title="",
    positive_color=None,
    negative_color=None,
    height=300,
):
    """Create an area chart with color based on positive/negative values (e.g., drawdowns)."""
    if positive_color is None:
        positive_color = COLORS.get("accent_primary", "#6366f1")
    if negative_color is None:
        negative_color = COLORS["danger"]

    colors = [positive_color if v >= 0 else negative_color for v in values]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines",
        line={"color": negative_color, "width": 1.5},
        fill="tozeroy",
        fillcolor="rgba(239, 68, 68, 0.15)",
        hovertemplate="%{x}<br>%{y:.2f}%<extra></extra>",
    ))

    fig.add_hline(y=0, line_color=COLORS["border"], line_width=1)

    fig.update_layout(
        **get_plotly_layout(margin={"l": 50, "r": 20, "t": 50, "b": 40}),
        height=height,
        title={"text": title, "font": {"size": 14}},
    )

    return fig


def create_benchmark_bar(
    horizons,
    stock_values,
    benchmark_values,
    stock_label="Stock",
    benchmark_label="Benchmark",
    title="",
    height=350,
):
    """Create a grouped bar chart comparing stock vs benchmark returns."""
    stock_color = COLORS.get("accent_primary", COLORS.get("accent_blue", "#6366f1"))
    bench_color = COLORS.get("accent_secondary", COLORS.get("accent_violet", "#8b5cf6"))

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name=stock_label,
        x=horizons,
        y=stock_values,
        marker_color=stock_color,
        text=[f"{v:+.1f}%" for v in stock_values],
        textposition="outside",
        textfont={"size": 10, "family": "JetBrains Mono"},
    ))

    fig.add_trace(go.Bar(
        name=benchmark_label,
        x=horizons,
        y=benchmark_values,
        marker_color=bench_color,
        text=[f"{v:+.1f}%" for v in benchmark_values],
        textposition="outside",
        textfont={"size": 10, "family": "JetBrains Mono"},
    ))

    fig.add_hline(y=0, line_color=COLORS["border"], line_width=1)

    fig.update_layout(
        **get_plotly_layout(margin={"l": 50, "r": 20, "t": 50, "b": 60}),
        height=height,
        title={"text": title, "font": {"size": 14}},
        barmode="group",
        legend={"font": {"color": COLORS["text_secondary"]}},
    )

    return fig


def create_donut_chart(labels, values, title="", colors=None, height=300):
    """Create a donut/pie chart."""
    if colors is None:
        colors = [
            COLORS["accent_blue"], COLORS["accent_violet"], COLORS["success"],
            COLORS["warning"], COLORS["danger"], "#06b6d4", "#ec4899", "#84cc16",
        ]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker={"colors": colors[:len(labels)], "line": {"color": COLORS["bg_primary"], "width": 2}},
        textinfo="label+percent",
        textfont={"size": 11, "color": COLORS["text_primary"]},
        hovertemplate="<b>%{label}</b><br>%{value}<br>%{percent}<extra></extra>",
    ))

    fig.update_layout(
        **get_plotly_layout(margin={"l": 20, "r": 20, "t": 50, "b": 20}),
        height=height,
        title={"text": title, "font": {"size": 14}},
        showlegend=False,
    )

    return fig
