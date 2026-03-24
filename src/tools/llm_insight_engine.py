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

    # Step 2: Try LLM synthesis
    llm_result = None
    try:
        llm_result = await _run_llm_synthesis(symbol, analyses, rule_signals, llm)
    except Exception as e:
        logger.warning(f"LLM insight synthesis failed for {symbol}: {e}")
        logger.info("Falling back to rule-based observations only")

    exec_time = (datetime.now(timezone.utc) - start).total_seconds()

    # Step 3: Merge LLM insights with rule-based
    if llm_result:
        return _build_llm_result(symbol, llm_result, rule_based, exec_time)
    else:
        # Graceful fallback to rule-based
        rule_based["engine"] = "rule-based (LLM unavailable)"
        rule_based["execution_time_seconds"] = round(exec_time, 3)
        return rule_based


async def _run_llm_synthesis(
    symbol: str,
    analyses: Dict[str, Any],
    rule_signals: List[Dict],
    llm=None,
) -> Dict[str, Any]:
    """Run the LLM synthesis and parse the JSON response."""
    if llm is None:
        llm = _get_default_llm()

    prompt = INSIGHT_USER_PROMPT.format(
        symbol=symbol,
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
