"""
LLM-Powered Insight Engine (Phase 1.4).

Replaces the rule-based ``insight_engine.py`` with an LLM-driven synthesis
layer that reasons across all analysis dimensions and generates prioritized,
actionable insights.

The rule-based detectors from ``insight_engine.py`` are still used to
*structure* the input — the LLM then reasons over them, detects
contradictions, and generates richer observations.

Usage::

    from src.tools.llm_insight_engine import generate_smart_observations
    obs = await generate_smart_observations("AAPL", analyses={...})
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from src.tools.insight_engine import (
    _detect_technical_signals,
    _detect_valuation_signals,
    _detect_earnings_signals,
    _detect_performance_signals,
    _detect_anomalies,
    _detect_confluences,
    _rank_observations,
    generate_observations as generate_rule_based_observations,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─── Historical Context Engine ─────────────────────────────────


def compute_historical_context(symbol: str) -> Dict[str, Any]:
    """
    Compare current metrics against their own historical ranges.

    Returns a dict of metric comparisons like:
        {"pe_ratio": {"current": 22.5, "5y_low": 14.2, "5y_high": 35.1,
                       "percentile": 62, "context": "P/E is in the upper half ..."}}

    Fails gracefully — returns empty dict on any error.
    """
    try:
        from src.data import get_provider

        provider = get_provider()
        info = provider.get_info(symbol)
        hist: Any = provider.get_history(symbol, period="5y", interval="1mo")

        if hist is None or (hasattr(hist, "empty") and hist.empty):
            return {}

        # Convert to DataFrame if not already
        if isinstance(hist, dict):
            import pandas as pd
            hist = pd.DataFrame(hist)

        context: Dict[str, Any] = {}

        # --- Price context ---
        closes = hist["Close"].dropna() if "Close" in hist.columns else None
        if closes is not None and len(closes) > 12:
            current_price = info.get(
                "currentPrice", info.get("regularMarketPrice", 0)
            )
            if current_price and current_price > 0:
                low_5y = float(closes.min())
                high_5y = float(closes.max())
                pct = _percentile_rank(closes.values, current_price)
                context["price"] = {
                    "current": round(current_price, 2),
                    "5y_low": round(low_5y, 2),
                    "5y_high": round(high_5y, 2),
                    "percentile": pct,
                    "context": _range_label("Price", current_price, low_5y, high_5y, pct),
                }

        # --- P/E context ---
        pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        if pe is not None:
            # Use trailing P/E with industry comparison
            industry_pe = info.get("industryPE", info.get("sectorPE"))
            pe_entry: Dict[str, Any] = {"current": round(pe, 2)}
            if forward_pe:
                pe_entry["forward"] = round(forward_pe, 2)
                if forward_pe < pe:
                    pe_entry["context"] = (
                        f"Forward P/E ({forward_pe:.1f}) is below trailing ({pe:.1f}), "
                        "implying expected earnings growth."
                    )
                else:
                    pe_entry["context"] = (
                        f"Forward P/E ({forward_pe:.1f}) above trailing ({pe:.1f}), "
                        "implying expected earnings decline."
                    )
            if industry_pe:
                pe_entry["industry_avg"] = round(industry_pe, 2)
            context["pe_ratio"] = pe_entry

        # --- P/B context ---
        pb = info.get("priceToBook")
        if pb is not None:
            context["pb_ratio"] = {
                "current": round(pb, 2),
                "context": (
                    "Below book value — potential deep value or distressed"
                    if pb < 1
                    else "Moderate premium to book"
                    if pb < 3
                    else "High premium to book — priced for growth"
                ),
            }

        # --- Dividend yield context ---
        div_yield = info.get("dividendYield")
        if div_yield is not None and div_yield > 0:
            five_yr_avg = info.get("fiveYearAvgDividendYield")
            dy_entry: Dict[str, Any] = {"current_pct": round(div_yield * 100, 2)}
            if five_yr_avg:
                dy_entry["5y_avg_pct"] = round(five_yr_avg, 2)
                ratio = (div_yield * 100) / five_yr_avg if five_yr_avg > 0 else 1
                if ratio > 1.2:
                    dy_entry["context"] = (
                        f"Yield ({div_yield*100:.2f}%) is significantly above "
                        f"5-year avg ({five_yr_avg:.2f}%) — may signal price decline "
                        "or dividend increase."
                    )
                elif ratio < 0.8:
                    dy_entry["context"] = (
                        f"Yield ({div_yield*100:.2f}%) is below "
                        f"5-year avg ({five_yr_avg:.2f}%) — price appreciation "
                        "has compressed yield."
                    )
                else:
                    dy_entry["context"] = "Yield is near its 5-year average."
            context["dividend_yield"] = dy_entry

        # --- Volatility context (annualized from monthly returns) ---
        if closes is not None and len(closes) > 12:
            monthly_returns = closes.pct_change().dropna()
            if len(monthly_returns) > 6:
                current_vol = float(monthly_returns[-12:].std() * np.sqrt(12) * 100)
                hist_vol = float(monthly_returns.std() * np.sqrt(12) * 100)
                context["volatility"] = {
                    "current_annual_pct": round(current_vol, 1),
                    "5y_avg_annual_pct": round(hist_vol, 1),
                    "context": (
                        f"Current annualized vol ({current_vol:.1f}%) vs "
                        f"5-year avg ({hist_vol:.1f}%). "
                        + (
                            "Elevated volatility — risk is above normal."
                            if current_vol > hist_vol * 1.3
                            else "Compressed volatility — may precede a large move."
                            if current_vol < hist_vol * 0.7
                            else "Volatility is near historical average."
                        )
                    ),
                }

        # --- 52-week position ---
        high_52w = info.get("fiftyTwoWeekHigh", 0)
        low_52w = info.get("fiftyTwoWeekLow", 0)
        curr = info.get("currentPrice", info.get("regularMarketPrice", 0))
        if high_52w and low_52w and curr and (high_52w - low_52w) > 0:
            pct_of_range = round(
                (curr - low_52w) / (high_52w - low_52w) * 100
            )
            context["52_week_range"] = {
                "current": round(curr, 2),
                "low": round(low_52w, 2),
                "high": round(high_52w, 2),
                "pct_of_range": pct_of_range,
                "context": (
                    f"Trading at {pct_of_range}% of 52-week range. "
                    + (
                        "Near 52-week high — momentum intact but limited upside to recent peak."
                        if pct_of_range > 85
                        else "Near 52-week low — potential value if fundamentals support."
                        if pct_of_range < 15
                        else "Mid-range — no extreme positioning signal."
                    )
                ),
            }

        return context

    except Exception as e:
        logger.warning(f"Historical context computation failed for {symbol}: {e}")
        return {}


def _percentile_rank(values, current: float) -> int:
    """What % of historical values are below the current value."""
    arr = np.array(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return 50
    return int(round(np.sum(arr < current) / len(arr) * 100))


def _range_label(
    metric: str, current: float, low: float, high: float, pct: int
) -> str:
    """Human-readable label for where current sits in its historical range."""
    if pct >= 90:
        return f"{metric} at {current} is near its 5-year high ({high}) — {pct}th percentile."
    if pct <= 10:
        return f"{metric} at {current} is near its 5-year low ({low}) — {pct}th percentile."
    if pct >= 70:
        return f"{metric} at {current} is in the upper range — {pct}th percentile of 5-year history."
    if pct <= 30:
        return f"{metric} at {current} is in the lower range — {pct}th percentile of 5-year history."
    return f"{metric} at {current} is mid-range — {pct}th percentile of 5-year history."

# ─── LLM Synthesis Prompt ───────────────────────────────────────

INSIGHT_SYSTEM_PROMPT = """You are an elite financial analyst synthesizer. You receive structured analysis data for a stock and must generate deep, actionable insights that go beyond surface-level observations.

Your job is to:
1. SYNTHESIZE cross-dimensional signals (technical + fundamental + earnings + performance + sentiment)
2. DETECT contradictions between different analysis dimensions and explain what they mean
3. IDENTIFY non-obvious patterns that simple rule-based systems would miss
4. GENERATE actionable "what to watch" items with specific triggers
5. ASSESS overall conviction level with clear reasoning

You must think like a portfolio manager making a real investment decision.

IMPORTANT RULES:
- Never hallucinate data. Only reference numbers and facts from the provided analysis.
- Be specific — cite actual values (RSI=28, P/E=15.2) rather than vague statements.
- Distinguish between short-term tactical signals and long-term structural views.
- Flag when data is insufficient to draw conclusions.
- Rate each insight's confidence (0.0-1.0) based on data quality and signal strength."""

INSIGHT_USER_PROMPT = """Analyze {symbol} using the following multi-dimensional data and generate deep insights.

## Historical Context (current metrics vs their own history)
{historical_context}

## Rule-Based Signals Detected
{rule_based_signals}

## Raw Analysis Data

### Technical Analysis
{technical_data}

### Fundamental Analysis
{fundamental_data}

### Earnings Data
{earnings_data}

### Performance Data
{performance_data}

### Peer Comparison
{peer_data}

### Sentiment Data
{sentiment_data}

---

Respond in this exact JSON format:
{{
  "key_insights": [
    {{
      "category": "Opportunity|Risk Warning|Anomaly|Bullish Signal|Bearish Signal|Watch Item",
      "severity": "Critical|High|Medium|Low",
      "title": "Short descriptive title",
      "observation": "Detailed observation with specific data points",
      "supporting_evidence": ["evidence 1", "evidence 2"],
      "confidence": 0.75,
      "actionability": "Specific action recommendation",
      "direction": "bullish|bearish|neutral",
      "time_horizon": "short-term|medium-term|long-term"
    }}
  ],
  "contradictions": [
    {{
      "description": "What signals conflict",
      "assessment": "What this contradiction likely means",
      "risk_level": "High|Medium|Low",
      "resolution": "What would resolve this contradiction"
    }}
  ],
  "overall_assessment": {{
    "bias": "Bullish|Bearish|Mixed / Neutral",
    "conviction": "High|Medium|Low",
    "reasoning": "2-3 sentence summary of the overall picture",
    "key_risk": "The single most important risk to monitor",
    "key_catalyst": "The single most important potential catalyst"
  }},
  "watch_items": [
    {{
      "trigger": "Specific price/metric threshold",
      "action": "What to do if triggered",
      "timeframe": "When to watch for this"
    }}
  ]
}}"""


# ─── Helper: Truncate data for LLM context ──────────────────────


def _summarize_for_llm(data: Any, max_len: int = 2000) -> str:
    """Convert analysis data to a compact string for LLM input."""
    if not data:
        return "No data available."
    if isinstance(data, str):
        return data[:max_len]
    try:
        text = json.dumps(data, indent=1, default=str)
        if len(text) > max_len:
            return text[:max_len] + "\n... (truncated)"
        return text
    except (TypeError, ValueError):
        return str(data)[:max_len]


def _format_historical_context(ctx: Dict[str, Any]) -> str:
    """Format historical context metrics for LLM consumption."""
    if not ctx:
        return "No historical context available."
    lines = []
    for metric, data in ctx.items():
        label = metric.replace("_", " ").title()
        context_str = data.get("context", "")
        current = data.get("current", data.get("current_pct", "N/A"))
        lines.append(f"- **{label}**: Current={current}. {context_str}")
        # Add sub-details
        for k, v in data.items():
            if k not in ("context", "current", "current_pct"):
                lines.append(f"    {k}: {v}")
    return "\n".join(lines)


def _format_rule_signals(observations: List[Dict]) -> str:
    """Format rule-based observations for LLM consumption."""
    if not observations:
        return "No rule-based signals detected."
    lines = []
    for obs in observations:
        icon = obs.get("icon", "")
        title = obs.get("title", "")
        direction = obs.get("direction", "neutral")
        confidence = obs.get("confidence", 0)
        lines.append(f"{icon} [{direction.upper()}] {title} (confidence: {confidence})")
        if obs.get("supporting_evidence"):
            for ev in obs["supporting_evidence"]:
                lines.append(f"   - {ev}")
    return "\n".join(lines)


# ─── Main Entry Points ──────────────────────────────────────────


async def generate_smart_observations(
    symbol: str,
    analyses: Dict[str, Any],
    llm=None,
) -> Dict[str, Any]:
    """
    Generate LLM-powered insights from all analysis results.

    Combines rule-based signal detection with LLM reasoning for
    deeper, cross-dimensional synthesis.

    Args:
        symbol: Stock ticker symbol.
        analyses: Dict with keys like ``"technical"``, ``"fundamental"``,
                  ``"earnings"``, ``"performance"``, ``"peers"``, ``"sentiment"``.
        llm: Optional LangChain LLM instance. If None, creates default.

    Returns:
        Dict with ``observations``, ``contradictions``, ``overall_assessment``,
        ``watch_items``, and metadata.
    """
    start = datetime.now(timezone.utc)

    # Step 1: Run rule-based detectors for structured input
    rule_based = generate_rule_based_observations(symbol, analyses)
    rule_signals = rule_based.get("observations", [])

    # Step 1b: Compute historical context
    hist_context = compute_historical_context(symbol)

    # Step 2: Try LLM synthesis
    llm_result = None
    try:
        llm_result = await _run_llm_synthesis(symbol, analyses, rule_signals, llm, hist_context)
    except Exception as e:
        logger.warning(f"LLM insight synthesis failed for {symbol}: {e}")
        logger.info("Falling back to rule-based observations only")

    exec_time = (datetime.now(timezone.utc) - start).total_seconds()

    # Step 3: Merge LLM insights with rule-based
    if llm_result:
        result = _build_llm_result(symbol, llm_result, rule_based, exec_time)
        if hist_context:
            result["historical_context"] = hist_context
        return result
    else:
        # Graceful fallback to rule-based
        rule_based["engine"] = "rule-based (LLM unavailable)"
        rule_based["execution_time_seconds"] = round(exec_time, 3)
        if hist_context:
            rule_based["historical_context"] = hist_context
        return rule_based


async def _run_llm_synthesis(
    symbol: str,
    analyses: Dict[str, Any],
    rule_signals: List[Dict],
    llm=None,
    historical_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the LLM synthesis and parse the JSON response."""
    if llm is None:
        llm = _get_default_llm()

    prompt = INSIGHT_USER_PROMPT.format(
        symbol=symbol,
        historical_context=_format_historical_context(historical_context or {}),
        rule_based_signals=_format_rule_signals(rule_signals),
        technical_data=_summarize_for_llm(analyses.get("technical")),
        fundamental_data=_summarize_for_llm(analyses.get("fundamental")),
        earnings_data=_summarize_for_llm(analyses.get("earnings")),
        performance_data=_summarize_for_llm(analyses.get("performance")),
        peer_data=_summarize_for_llm(analyses.get("peers")),
        sentiment_data=_summarize_for_llm(analyses.get("sentiment")),
    )

    from langchain_core.messages import SystemMessage, HumanMessage

    messages = [
        SystemMessage(content=INSIGHT_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = await llm.ainvoke(messages)
    content = response.content if hasattr(response, "content") else str(response)

    # Parse JSON from response (handle markdown code blocks)
    return _parse_llm_json(content)


def _parse_llm_json(content: str) -> Dict[str, Any]:
    """Extract and parse JSON from LLM response, handling code blocks."""
    text = content.strip()

    # Strip markdown code blocks
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]

    return json.loads(text.strip())


def _get_default_llm():
    """Create the default LLM for insight synthesis."""
    from src.config import settings

    provider = settings.llm.provider.lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.llm.ollama_model,
            base_url=settings.llm.ollama_base_url,
            temperature=0.2,
        )
    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.llm.groq_model,
            api_key=settings.llm.groq_api_key,
            temperature=0.2,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm.model,
            api_key=settings.llm.openai_api_key,
            temperature=0.2,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.llm.model,
            api_key=settings.llm.anthropic_api_key,
            temperature=0.2,
        )
    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.llm.ollama_model,
            base_url=settings.llm.ollama_base_url,
            temperature=0.2,
        )


def _build_llm_result(
    symbol: str,
    llm_data: Dict[str, Any],
    rule_based: Dict[str, Any],
    exec_time: float,
) -> Dict[str, Any]:
    """Merge LLM insights with rule-based into final output."""
    # Map LLM insights to observation format
    observations = []
    icon_map = {
        "Bullish Signal": "\U0001f7e2",
        "Bearish Signal": "\U0001f534",
        "Risk Warning": "\u26a0\ufe0f",
        "Opportunity": "\U0001f4a1",
        "Anomaly": "\U0001f50d",
        "Watch Item": "\U0001f441\ufe0f",
    }

    for i, insight in enumerate(llm_data.get("key_insights", []), start=1):
        cat = insight.get("category", "Watch Item")
        observations.append({
            "rank": i,
            "category": cat,
            "icon": icon_map.get(cat, ""),
            "severity": insight.get("severity", "Medium"),
            "title": insight.get("title", ""),
            "observation": insight.get("observation", ""),
            "supporting_evidence": insight.get("supporting_evidence", []),
            "confidence": insight.get("confidence", 0.5),
            "actionability": insight.get("actionability", "Medium"),
            "direction": insight.get("direction", "neutral"),
            "time_horizon": insight.get("time_horizon", "medium-term"),
        })

    overall = llm_data.get("overall_assessment", {})
    bullish_count = sum(1 for o in observations if o.get("direction") == "bullish")
    bearish_count = sum(1 for o in observations if o.get("direction") == "bearish")

    return {
        "symbol": symbol,
        "engine": "llm-powered",
        "total_observations": len(observations),
        "overall_bias": overall.get("bias", "Mixed / Neutral"),
        "conviction": overall.get("conviction", "Medium"),
        "reasoning": overall.get("reasoning", ""),
        "key_risk": overall.get("key_risk", ""),
        "key_catalyst": overall.get("key_catalyst", ""),
        "bullish_signals": bullish_count,
        "bearish_signals": bearish_count,
        "observations": observations,
        "contradictions": llm_data.get("contradictions", []),
        "watch_items": llm_data.get("watch_items", []),
        # Keep rule-based as supplementary
        "rule_based_confluences": rule_based.get("confluences", []),
        "rule_based_anomalies": rule_based.get("anomalies", []),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "execution_time_seconds": round(exec_time, 3),
    }


# ─── Sync wrapper ───────────────────────────────────────────────


def generate_smart_observations_sync(
    symbol: str,
    analyses: Dict[str, Any],
    llm=None,
) -> Dict[str, Any]:
    """Synchronous version of generate_smart_observations."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        return loop.run_until_complete(
            generate_smart_observations(symbol, analyses, llm)
        )
    except RuntimeError:
        return asyncio.run(generate_smart_observations(symbol, analyses, llm))
