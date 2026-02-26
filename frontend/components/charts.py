"""
TradingView Lightweight Charts components for Streamlit.
Renders financial charts via st.components.v1.html().
"""

import json
import streamlit.components.v1 as components


CHART_THEME = {
    "bg": "#0a0e17",
    "text": "#9ca3af",
    "grid": "#1f2937",
    "border": "#374151",
    "crosshair": "#6b7280",
    "up": "#10b981",
    "down": "#ef4444",
    "volume_up": "rgba(16, 185, 129, 0.3)",
    "volume_down": "rgba(239, 68, 68, 0.3)",
    "sma20": "#3b82f6",
    "sma50": "#f59e0b",
    "sma200": "#8b5cf6",
    "bb_fill": "rgba(59, 130, 246, 0.05)",
    "bb_line": "rgba(59, 130, 246, 0.3)",
    "sr_support": "#10b981",
    "sr_resistance": "#ef4444",
}


def render_candlestick_chart(
    dates: list,
    opens: list,
    highs: list,
    lows: list,
    closes: list,
    volumes: list = None,
    sma_data: dict = None,
    bollinger_data: dict = None,
    support_levels: list = None,
    resistance_levels: list = None,
    height: int = 500,
):
    """
    Render a TradingView Lightweight Charts candlestick chart.

    Args:
        dates: List of date strings (YYYY-MM-DD)
        opens, highs, lows, closes: Price arrays
        volumes: Optional volume array
        sma_data: Dict like {"sma_20": [...], "sma_50": [...], "sma_200": [...]}
        bollinger_data: Dict like {"upper": [...], "lower": [...], "middle": [...]}
        support_levels: List of support price levels
        resistance_levels: List of resistance price levels
        height: Chart height in pixels
    """
    # Build candlestick data
    candle_data = []
    for i in range(len(dates)):
        candle_data.append({
            "time": dates[i],
            "open": round(opens[i], 2) if opens[i] else 0,
            "high": round(highs[i], 2) if highs[i] else 0,
            "low": round(lows[i], 2) if lows[i] else 0,
            "close": round(closes[i], 2) if closes[i] else 0,
        })

    # Build volume data
    volume_data = []
    if volumes:
        for i in range(len(dates)):
            color = CHART_THEME["volume_up"] if i == 0 or closes[i] >= closes[i - 1] else CHART_THEME["volume_down"]
            volume_data.append({
                "time": dates[i],
                "value": volumes[i] if volumes[i] else 0,
                "color": color,
            })

    # Build SMA line data
    sma_series_js = ""
    if sma_data:
        colors = {"sma_20": CHART_THEME["sma20"], "sma_50": CHART_THEME["sma50"], "sma_200": CHART_THEME["sma200"]}
        labels = {"sma_20": "SMA 20", "sma_50": "SMA 50", "sma_200": "SMA 200"}
        for key, values in sma_data.items():
            if values and key in colors:
                line_data = []
                for i in range(len(dates)):
                    if i < len(values) and values[i] is not None:
                        line_data.append({"time": dates[i], "value": round(values[i], 2)})
                if line_data:
                    sma_series_js += f"""
                    const {key}Series = chart.addLineSeries({{
                        color: '{colors[key]}',
                        lineWidth: 1,
                        title: '{labels.get(key, key)}',
                        priceLineVisible: false,
                        lastValueVisible: false,
                    }});
                    {key}Series.setData({json.dumps(line_data)});
                    """

    # Build S/R price lines
    price_lines_js = ""
    if support_levels:
        for level in support_levels[:3]:
            price_lines_js += f"""
            candleSeries.createPriceLine({{
                price: {level},
                color: '{CHART_THEME["sr_support"]}',
                lineWidth: 1,
                lineStyle: 2,
                axisLabelVisible: true,
                title: 'S {level:.2f}',
            }});
            """
    if resistance_levels:
        for level in resistance_levels[:3]:
            price_lines_js += f"""
            candleSeries.createPriceLine({{
                price: {level},
                color: '{CHART_THEME["sr_resistance"]}',
                lineWidth: 1,
                lineStyle: 2,
                axisLabelVisible: true,
                title: 'R {level:.2f}',
            }});
            """

    # Volume pane JS
    volume_js = ""
    if volume_data:
        volume_js = f"""
        const volumeSeries = chart.addHistogramSeries({{
            priceFormat: {{ type: 'volume' }},
            priceScaleId: 'volume',
        }});
        chart.priceScale('volume').applyOptions({{
            scaleMargins: {{ top: 0.8, bottom: 0 }},
        }});
        volumeSeries.setData({json.dumps(volume_data)});
        """

    html = f"""
    <div id="chart-container" style="width: 100%; height: {height}px; border-radius: 12px; overflow: hidden; border: 1px solid {CHART_THEME['border']}; background: {CHART_THEME['bg']};"></div>
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        const container = document.getElementById('chart-container');
        const chart = LightweightCharts.createChart(container, {{
            width: container.clientWidth,
            height: {height},
            layout: {{
                background: {{ color: '{CHART_THEME["bg"]}' }},
                textColor: '{CHART_THEME["text"]}',
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
            }},
            grid: {{
                vertLines: {{ color: '{CHART_THEME["grid"]}' }},
                horzLines: {{ color: '{CHART_THEME["grid"]}' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {{ color: '{CHART_THEME["crosshair"]}', width: 1, style: 3 }},
                horzLine: {{ color: '{CHART_THEME["crosshair"]}', width: 1, style: 3 }},
            }},
            rightPriceScale: {{
                borderColor: '{CHART_THEME["border"]}',
                scaleMargins: {{ top: 0.05, bottom: 0.2 }},
            }},
            timeScale: {{
                borderColor: '{CHART_THEME["border"]}',
                timeVisible: false,
            }},
            handleScroll: {{ vertTouchDrag: false }},
        }});

        const candleSeries = chart.addCandlestickSeries({{
            upColor: '{CHART_THEME["up"]}',
            downColor: '{CHART_THEME["down"]}',
            borderUpColor: '{CHART_THEME["up"]}',
            borderDownColor: '{CHART_THEME["down"]}',
            wickUpColor: '{CHART_THEME["up"]}',
            wickDownColor: '{CHART_THEME["down"]}',
        }});
        candleSeries.setData({json.dumps(candle_data)});

        {volume_js}
        {sma_series_js}
        {price_lines_js}

        chart.timeScale().fitContent();

        new ResizeObserver(entries => {{
            const {{ width }} = entries[0].contentRect;
            chart.applyOptions({{ width }});
        }}).observe(container);
    </script>
    """

    components.html(html, height=height + 10, scrolling=False)


def render_line_chart(
    dates: list,
    values: list,
    title: str = "",
    color: str = "#3b82f6",
    height: int = 300,
):
    """Render a simple line chart."""
    line_data = []
    for i in range(len(dates)):
        if i < len(values) and values[i] is not None:
            line_data.append({"time": dates[i], "value": round(float(values[i]), 2)})

    html = f"""
    <div id="line-chart-{hash(title)}" style="width: 100%; height: {height}px; border-radius: 12px; overflow: hidden; border: 1px solid {CHART_THEME['border']}; background: {CHART_THEME['bg']};"></div>
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        const container = document.getElementById('line-chart-{hash(title)}');
        const chart = LightweightCharts.createChart(container, {{
            width: container.clientWidth,
            height: {height},
            layout: {{
                background: {{ color: '{CHART_THEME["bg"]}' }},
                textColor: '{CHART_THEME["text"]}',
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
            }},
            grid: {{
                vertLines: {{ color: '{CHART_THEME["grid"]}' }},
                horzLines: {{ color: '{CHART_THEME["grid"]}' }},
            }},
            rightPriceScale: {{ borderColor: '{CHART_THEME["border"]}' }},
            timeScale: {{ borderColor: '{CHART_THEME["border"]}' }},
        }});
        const series = chart.addLineSeries({{
            color: '{color}',
            lineWidth: 2,
            title: '{title}',
        }});
        series.setData({json.dumps(line_data)});
        chart.timeScale().fitContent();

        new ResizeObserver(entries => {{
            chart.applyOptions({{ width: entries[0].contentRect.width }});
        }}).observe(container);
    </script>
    """
    components.html(html, height=height + 10, scrolling=False)


def render_area_chart(
    dates: list,
    values: list,
    title: str = "",
    color: str = "#3b82f6",
    height: int = 300,
):
    """Render an area chart with gradient fill."""
    area_data = []
    for i in range(len(dates)):
        if i < len(values) and values[i] is not None:
            area_data.append({"time": dates[i], "value": round(float(values[i]), 2)})

    html = f"""
    <div id="area-chart-{hash(title)}" style="width: 100%; height: {height}px; border-radius: 12px; overflow: hidden; border: 1px solid {CHART_THEME['border']}; background: {CHART_THEME['bg']};"></div>
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        const container = document.getElementById('area-chart-{hash(title)}');
        const chart = LightweightCharts.createChart(container, {{
            width: container.clientWidth,
            height: {height},
            layout: {{
                background: {{ color: '{CHART_THEME["bg"]}' }},
                textColor: '{CHART_THEME["text"]}',
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
            }},
            grid: {{
                vertLines: {{ color: '{CHART_THEME["grid"]}' }},
                horzLines: {{ color: '{CHART_THEME["grid"]}' }},
            }},
            rightPriceScale: {{ borderColor: '{CHART_THEME["border"]}' }},
            timeScale: {{ borderColor: '{CHART_THEME["border"]}' }},
        }});
        const series = chart.addAreaSeries({{
            lineColor: '{color}',
            topColor: '{color}33',
            bottomColor: '{color}05',
            lineWidth: 2,
            title: '{title}',
        }});
        series.setData({json.dumps(area_data)});
        chart.timeScale().fitContent();

        new ResizeObserver(entries => {{
            chart.applyOptions({{ width: entries[0].contentRect.width }});
        }}).observe(container);
    </script>
    """
    components.html(html, height=height + 10, scrolling=False)
