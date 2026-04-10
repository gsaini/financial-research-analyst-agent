"""
Data service layer - bridges Streamlit to the project's Python tools.

All functions use @st.cache_data for performance:
- Live prices: 60s TTL
- Historical data: 5 min TTL
- Analysis results: 30 min TTL
"""

import sys
import os

# Ensure the project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st


# ─── Symbol Search ─────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner="Searching stocks...")
def search_symbols(query: str, max_results: int = 8) -> list:
    """
    Search for stock symbols matching a query via Yahoo Finance.

    Returns list of dicts: [{"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NMS", "type": "S"}, ...]
    """
    if not query or len(query) < 2:
        return []

    import requests

    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {
            "q": query,
            "quotesCount": max_results,
            "newsCount": 0,
            "listsCount": 0,
            "enableFuzzyQuery": False,
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for quote in data.get("quotes", []):
            q_type = quote.get("quoteType", "")
            # Only include equities and ETFs
            if q_type not in ("EQUITY", "ETF"):
                continue
            results.append({
                "symbol": quote.get("symbol", ""),
                "name": quote.get("shortname") or quote.get("longname") or "",
                "exchange": quote.get("exchDisp", ""),
                "type": q_type,
            })
        return results
    except Exception:
        return []


# ─── Market Data ───────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def get_stock_price(symbol: str) -> dict:
    """Get current stock price and key data points."""
    from src.tools.market_data import get_stock_price as _fn
    return _fn(symbol)


@st.cache_data(ttl=300, show_spinner=False)
def get_historical_data(symbol: str, period: str = "1y") -> dict:
    """Get OHLCV historical data."""
    from src.tools.market_data import get_historical_data as _fn
    return _fn(symbol, period=period)


@st.cache_data(ttl=600, show_spinner=False)
def get_company_info(symbol: str) -> dict:
    """Get company profile information."""
    from src.tools.market_data import get_company_info as _fn
    return _fn(symbol)


@st.cache_data(ttl=600, show_spinner=False)
def get_financial_statements(symbol: str) -> dict:
    """Get income statement, balance sheet, and cash flow."""
    from src.tools.market_data import get_financial_statements as _fn
    return _fn(symbol)


# ─── Technical Analysis ───────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_technical_analysis(symbol: str, period: str = "1y") -> dict:
    """Run all technical indicators on a symbol."""
    hist = get_historical_data(symbol, period)
    if "error" in hist:
        return {"error": hist["error"]}

    closes = hist.get("closes", [])
    if len(closes) < 30:
        return {"error": "Insufficient historical data for technical analysis."}

    from src.tools.technical_indicators import (
        calculate_rsi,
        calculate_macd,
        calculate_moving_averages,
        calculate_bollinger_bands,
        identify_support_resistance,
        detect_patterns,
    )

    return {
        "rsi": calculate_rsi(closes),
        "macd": calculate_macd(closes),
        "moving_averages": calculate_moving_averages(closes),
        "bollinger_bands": calculate_bollinger_bands(closes),
        "support_resistance": identify_support_resistance(hist),
        "patterns": detect_patterns(hist),
    }


# ─── Financial Metrics ────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def get_financial_health(symbol: str) -> dict:
    """Get comprehensive financial health analysis."""
    from src.tools.financial_metrics import analyze_financial_health

    financials = get_financial_statements(symbol)
    price_data = get_stock_price(symbol)
    company = get_company_info(symbol)

    if "error" in financials or "error" in price_data:
        return {"error": "Unable to fetch financial data."}

    income = financials.get("income_statement") or {}
    balance = financials.get("balance_sheet") or {}
    cashflow = financials.get("cash_flow") or {}

    combined = {
        **income,
        **balance,
        **cashflow,
        "price": price_data.get("current_price", 0),
        "eps": price_data.get("eps", 0),
        "market_cap": price_data.get("market_cap", 0),
        "enterprise_value": company.get("enterprise_value", 0),
        "shares_outstanding": (
            price_data.get("market_cap", 0) / price_data.get("current_price", 1)
            if price_data.get("current_price", 0) > 0
            else 0
        ),
    }

    try:
        return analyze_financial_health(combined)
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=1800, show_spinner=False)
def get_valuation_ratios(symbol: str) -> dict:
    """Get valuation ratios for a symbol."""
    from src.tools.financial_metrics import calculate_valuation_ratios

    financials = get_financial_statements(symbol)
    price_data = get_stock_price(symbol)
    company = get_company_info(symbol)

    income = financials.get("income_statement") or {}
    balance = financials.get("balance_sheet") or {}

    combined = {
        **income,
        **balance,
        "price": price_data.get("current_price", 0),
        "eps": price_data.get("eps", 0),
        "market_cap": price_data.get("market_cap", 0),
        "enterprise_value": company.get("enterprise_value", 0),
    }

    try:
        return calculate_valuation_ratios(combined)
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=1800, show_spinner=False)
def get_profitability_ratios(symbol: str) -> dict:
    """Get profitability ratios for a symbol."""
    from src.tools.financial_metrics import calculate_profitability_ratios

    financials = get_financial_statements(symbol)
    income = financials.get("income_statement") or {}
    balance = financials.get("balance_sheet") or {}

    combined = {**income, **balance}

    try:
        return calculate_profitability_ratios(combined)
    except Exception as e:
        return {"error": str(e)}


# ─── News ─────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def get_company_news(symbol: str) -> list:
    """Fetch company-related news articles."""
    from src.tools.news_fetcher import fetch_company_news as _fn
    try:
        return _fn(symbol)
    except Exception:
        return []


# ─── Sentiment & News Impact ─────────────────────────────────

@st.cache_data(ttl=600, show_spinner="Analyzing sentiment...")
def analyze_news_sentiment(symbol: str) -> dict:
    """Full news & sentiment impact analysis for a symbol."""
    from src.tools.news_impact import analyze_news_impact as _fn
    return _fn(symbol.upper())


# ─── Theme Analysis ───────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def get_themes_list() -> list:
    """List all available investment themes. Auto-refreshes when themes.yaml changes."""
    from src.tools.theme_mapper import list_available_themes as _fn
    return _fn()


def refresh_themes_cache():
    """Clear all theme caches so changes to themes.yaml are picked up immediately."""
    from src.tools.theme_mapper import reload_themes_config
    reload_themes_config()
    get_themes_list.clear()
    analyze_theme.clear()


@st.cache_data(ttl=1800, show_spinner=False)
def analyze_theme(theme_id: str) -> dict:
    """Analyze an investment theme."""
    from src.tools.theme_mapper import analyze_theme as _fn
    return _fn(theme_id)


# ─── Disruption Analysis ─────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def analyze_disruption(symbol: str) -> dict:
    """Analyze a company's disruption profile."""
    from src.tools.disruption_metrics import analyze_disruption as _fn
    return _fn(symbol.upper())


@st.cache_data(ttl=1800, show_spinner=False)
def compare_disruption(symbols: tuple) -> dict:
    """Compare disruption profiles across companies. Pass symbols as tuple for caching."""
    from src.tools.disruption_metrics import compare_disruption as _fn
    return _fn(list(symbols))


# ─── Earnings Analysis ────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def analyze_earnings(symbol: str) -> dict:
    """Analyze quarterly earnings."""
    from src.tools.earnings_data import analyze_earnings as _fn
    return _fn(symbol.upper())


@st.cache_data(ttl=1800, show_spinner=False)
def compare_earnings(symbols: tuple) -> dict:
    """Compare earnings profiles. Pass symbols as tuple for caching."""
    from src.tools.earnings_data import compare_earnings as _fn
    return _fn(list(symbols))


# ─── Peer Comparison ──────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner="Analyzing performance...")
def track_performance(symbol: str) -> dict:
    """Track comprehensive historical performance for a symbol."""
    from src.tools.performance_tracker import track_performance as _fn
    return _fn(symbol.upper())


@st.cache_data(ttl=1800, show_spinner=False)
def compare_peers(symbol: str, peers: tuple = None) -> dict:
    """Compare a stock against peers. Wraps async function."""
    import asyncio
    from src.tools.peer_comparison import compare_peers as _fn

    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass

    peer_list = list(peers) if peers else None
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_fn(symbol, peer_list))
        return result
    except Exception as e:
        return {"error": str(e)}
    finally:
        loop.close()


# ─── Dividend Analysis ───────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def analyze_dividends(symbol: str) -> dict:
    """Analyze dividend profile for a stock."""
    from src.tools.dividend_analyzer import analyze_dividends as _fn
    return _fn(symbol.upper())


@st.cache_data(ttl=1800, show_spinner=False)
def compare_dividends(symbols: tuple) -> dict:
    """Compare dividend profiles. Pass symbols as tuple for caching."""
    from src.tools.dividend_analyzer import compare_dividends as _fn
    return _fn(list(symbols))


# ─── ETF Screener ────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def screen_etfs(theme_ids: tuple = None, max_risk: str = None, top_n: int = 10) -> dict:
    """Screen and rank ETFs across investment themes."""
    from src.tools.etf_screener import screen_etfs as _fn
    ids = list(theme_ids) if theme_ids else None
    return _fn(theme_ids=ids, max_risk=max_risk, top_n=top_n)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_etf_data(symbol: str) -> dict:
    """Fetch data for a single ETF."""
    from src.tools.etf_screener import fetch_etf_data as _fn
    return _fn(symbol.upper())


# ─── Macro Economic Data (Phase 2) ────────────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def get_macro_summary() -> dict:
    """Get key macroeconomic indicators from FRED."""
    from src.tools.macro_data import get_macro_summary as _fn
    return _fn()


@st.cache_data(ttl=1800, show_spinner=False)
def get_treasury_yields() -> dict:
    """Get treasury yields and yield curve status."""
    from src.tools.macro_data import get_treasury_yields as _fn
    return _fn()


@st.cache_data(ttl=1800, show_spinner=False)
def get_rate_environment() -> dict:
    """Get rate environment analysis."""
    from src.tools.macro_data import get_rate_environment as _fn
    return _fn()


@st.cache_data(ttl=1800, show_spinner=False)
def get_macro_context(symbol: str) -> dict:
    """Get macro context for a specific stock."""
    from src.tools.macro_data import get_macro_context_for_stock as _fn
    return _fn(symbol)


# ─── DCF Valuation (Phase 2) ─────────────────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def get_dcf_analysis(symbol: str) -> dict:
    """Run DCF valuation analysis with 3 scenarios."""
    from src.tools.dcf_model import get_dcf_summary as _fn
    return _fn(symbol)


# ─── Social Sentiment (Phase 2) ──────────────────────────


@st.cache_data(ttl=600, show_spinner=False)
def get_social_sentiment(symbol: str) -> dict:
    """Get Reddit and social media sentiment for a stock."""
    from src.tools.social_sentiment import get_social_sentiment_composite as _fn
    return _fn(symbol)


@st.cache_data(ttl=600, show_spinner=False)
def get_trending_tickers() -> dict:
    """Get trending tickers from Reddit."""
    from src.tools.social_sentiment import get_trending_tickers as _fn
    return _fn()


# ─── ML Forecast (Phase 2) ──────────────────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def get_price_forecast(symbol: str) -> dict:
    """Get ML-based price forecast with targets."""
    from src.tools.ml_forecast import get_price_targets as _fn
    return _fn(symbol)


# ─── Alerts (Feature 18) ────────────────────────────────


def create_alert(symbol: str, alert_type: str, threshold: float = 0, message: str = "", repeat: bool = False) -> dict:
    """Create a new alert (not cached — mutates state)."""
    from src.tools.alerts import add_alert as _fn
    return _fn(symbol, alert_type, threshold, message, repeat=repeat)


def remove_alert(alert_id: str) -> dict:
    """Remove an alert."""
    from src.tools.alerts import remove_alert as _fn
    return _fn(alert_id)


def get_all_alerts(status: str = None) -> list:
    """List all alerts."""
    from src.tools.alerts import list_alerts as _fn
    return _fn(status=status)


def evaluate_alerts() -> list:
    """Evaluate all pending alerts."""
    from src.tools.alerts import check_alerts as _fn
    return _fn()


def get_alert_types() -> list:
    """Get available alert types."""
    from src.tools.alerts import get_available_alert_types as _fn
    return _fn()


def get_triggered_alerts() -> list:
    """Get triggered alert history."""
    from src.tools.alerts import get_triggered_history as _fn
    return _fn()


# ─── Analyst Consensus ──────────────────────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def get_analyst_consensus(symbol: str) -> dict:
    """Get analyst consensus, price targets, and estimate revisions."""
    from src.tools.analyst_tracker import get_analyst_consensus as _fn
    return _fn(symbol)


@st.cache_data(ttl=1800, show_spinner=False)
def compare_analyst_consensus(symbols: tuple) -> dict:
    """Compare analyst consensus across multiple stocks."""
    from src.tools.analyst_tracker import compare_analyst_consensus as _fn
    return _fn(list(symbols))


# ─── Short Interest Analysis ────────────────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def get_short_interest(symbol: str) -> dict:
    """Get short interest analysis and squeeze scoring."""
    from src.tools.short_interest import analyze_short_interest as _fn
    return _fn(symbol)


@st.cache_data(ttl=1800, show_spinner=False)
def compare_short_interest(symbols: tuple) -> dict:
    """Compare short interest across multiple stocks."""
    from src.tools.short_interest import compare_short_interest as _fn
    return _fn(list(symbols))


@st.cache_data(ttl=1800, show_spinner=False)
def get_squeeze_watchlist(min_score: int = 50) -> dict:
    """Screen for short squeeze candidates."""
    from src.tools.short_interest import get_short_squeeze_watchlist as _fn
    return _fn(min_squeeze_score=min_score)


# ─── Anomaly Detection (Phase 2) ────────────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def detect_anomalies(symbol: str) -> dict:
    """Detect volume and price anomalies."""
    from src.tools.anomaly_detector import detect_volume_anomalies, detect_price_anomalies
    return {
        "volume": detect_volume_anomalies(symbol),
        "price": detect_price_anomalies(symbol),
    }


# ─── Portfolio Optimization (Phase 2) ───────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def optimize_portfolio(symbols: tuple, method: str = "max_sharpe") -> dict:
    """Run portfolio optimization."""
    from src.tools.portfolio_optimizer import optimize_portfolio as _fn
    return _fn(list(symbols), method=method)


@st.cache_data(ttl=1800, show_spinner=False)
def get_efficient_frontier(symbols: tuple) -> dict:
    """Calculate efficient frontier."""
    from src.tools.portfolio_optimizer import calculate_efficient_frontier as _fn
    return _fn(list(symbols))


@st.cache_data(ttl=1800, show_spinner=False)
def get_portfolio_benchmark(symbols: tuple, weights: tuple) -> dict:
    """Compare portfolio vs benchmark."""
    from src.tools.benchmark import calculate_portfolio_vs_benchmark as _fn
    return _fn(list(symbols), list(weights))


@st.cache_data(ttl=1800, show_spinner=False)
def get_correlation_analysis(symbols: tuple) -> dict:
    """Get correlation matrix with insights."""
    from src.tools.portfolio_optimizer import correlation_analysis as _fn
    return _fn(list(symbols))


@st.cache_data(ttl=1800, show_spinner=False)
def get_full_portfolio_optimization(symbols: tuple, weights: tuple = None) -> dict:
    """Run comprehensive portfolio optimization."""
    from src.tools.portfolio_optimizer import full_portfolio_optimization as _fn
    return _fn(list(symbols), current_weights=list(weights) if weights else None)


@st.cache_data(ttl=1800, show_spinner=False)
def get_rebalance_suggestions(symbols: tuple, weights: tuple, method: str = "max_sharpe") -> dict:
    """Get rebalancing suggestions."""
    from src.tools.portfolio_optimizer import rebalance_suggestions as _fn
    return _fn(list(symbols), list(weights), target_method=method)


# ─── LLM Chat ──────────────────────────────────────────────


@st.cache_resource(show_spinner=False)
def _get_llm():
    """
    Create a shared LLM instance using the configured provider.

    Uses @st.cache_resource so the LLM object is created once per session
    and reused across calls (it is not serializable with cache_data).
    """
    from src.config import settings

    provider = settings.llm.provider.lower()
    temperature = 0.7  # Conversational temperature

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.llm.ollama_model,
            base_url=settings.llm.ollama_base_url,
            temperature=temperature,
        )
    elif provider == "lmstudio":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm.lmstudio_model,
            base_url=settings.llm.lmstudio_base_url,
            temperature=temperature,
            api_key="lm-studio",
        )
    elif provider == "vllm":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm.vllm_model,
            base_url=settings.llm.vllm_base_url,
            temperature=temperature,
            api_key="vllm",
        )
    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.llm.groq_model,
            api_key=settings.llm.groq_api_key,
            temperature=temperature,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.llm.model,
            api_key=settings.llm.anthropic_api_key,
            temperature=temperature,
            max_tokens=settings.llm.max_tokens,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm.model,
            temperature=temperature,
            api_key=settings.llm.openai_api_key,
            max_tokens=settings.llm.max_tokens,
        )
    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.llm.ollama_model,
            base_url=settings.llm.ollama_base_url,
            temperature=temperature,
        )


def ask_etf_question(
    question: str,
    etf_context: str,
    chat_history: list[dict] | None = None,
) -> str:
    """Answer a user question about ETFs. Delegates to ask_financial_question."""
    return ask_financial_question(
        question=question,
        context=etf_context,
        chat_history=chat_history,
    )


def ask_financial_question(
    question: str,
    context: str = "",
    chat_history: list[dict] | None = None,
) -> str:
    """
    Answer a user question about stocks, ETFs, or investing using the configured LLM.

    Args:
        question: The user's question.
        context: Pre-formatted string with financial data (ETFs, stock info, etc.).
        chat_history: List of {"role": "user"|"assistant", "content": "..."} dicts.

    Returns:
        The LLM response text.
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

    llm = _get_llm()

    system_prompt = f"""You are an expert AI financial advisor. You can help with:
- ETFs and thematic investing (buy/sell/hold recommendations, comparisons)
- Individual stocks (valuation, technical signals, fundamentals)
- Portfolio strategy (diversification, allocation, rebalancing)
- Dividend investing (yield, safety, income planning)
- Market themes and sector analysis
- Risk management and investment timing

IMPORTANT — Conversational Approach:
When a user's question needs more context to give a truly helpful answer, ASK 2-3 short
clarifying questions BEFORE answering. This makes your advice much more relevant.

Examples of when to ask follow-up questions:
- "How long should I hold X?" → Ask: When did you buy it? What's your target return or goal?
- "Should I sell X?" → Ask: What's your purchase price? Are you investing for income or growth?
- "Is X good for me?" → Ask: What's your risk tolerance? What's your investment horizon?
- "Build me a portfolio" → Ask: What's your total budget? Are you conservative or aggressive?
- "When should I buy X?" → Ask: Are you looking for a short-term trade or long-term investment?

When you DO have enough context (e.g. general data questions, theme comparisons, or the user
already provided their details in previous messages), answer directly without unnecessary questions.

Once the user answers your clarifying questions, synthesize ALL the context and give a
specific, actionable recommendation backed by numbers from the data.

Guidelines:
- Be specific with numbers from the data when available
- When recommending buy/sell/hold, explain your reasoning clearly
- Reference composite scores, returns, volatility, and theme health where relevant
- For stocks not in the data, use your financial knowledge but note limited data
- Always end with a brief disclaimer that this is informational analysis, not personalized financial advice

Keep answers concise and actionable. Use markdown formatting for readability.

=== FINANCIAL DATA ===
{context}
=== END DATA ==="""

    messages = [SystemMessage(content=system_prompt)]

    # Add chat history
    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=question))

    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"I'm unable to answer right now. Please check that your LLM provider is running.\n\nError: {e}"


# ─── Ticker Extraction ─────────────────────────────────────

import re as _re

# Common tickers that are also English words — avoid false positives
_COMMON_WORD_TICKERS = {
    "A", "I", "IT", "ALL", "ARE", "AT", "BE", "BIG", "CAN", "CEO",
    "DO", "FOR", "GO", "HAS", "HE", "HER", "HIM", "HIS", "IF",
    "IN", "IS", "ITS", "LOW", "ME", "MY", "NEW", "NOW", "OLD",
    "ON", "ONE", "OR", "OUT", "OWN", "PAY", "SO", "THE", "TO",
    "TOO", "TWO", "UP", "US", "WAS", "WAR", "WAY", "WE",
    "WHO", "WHY", "WIN", "YOU", "AN", "AM", "AS", "BY", "OF",
    "HOLD", "BUY", "SELL", "LONG", "PUT", "CALL", "RUN",
    "VERY", "WELL", "GOOD", "BEST", "TOP", "HIGH", "ANY",
    "HOW", "WHAT", "WHEN", "JUST", "THAN", "THEN",
    "MOST", "NOT", "YET", "BUT", "AND", "THAT", "THIS",
    "FROM", "WILL", "BEEN", "HAVE", "WITH", "THEM",
    "ETF", "AI", "SEC", "IPO", "CEO", "CFO", "COO",
}

def _extract_tickers(text: str) -> list[str]:
    """
    Extract likely stock/ETF ticker symbols from user text.

    Handles:
    - Explicit $AAPL notation
    - Standalone uppercase 1-5 letter words that look like tickers
    - Filters out common English words and financial abbreviations
    """
    tickers = set()

    # 1) Explicit $TICKER notation (highest confidence)
    for m in _re.finditer(r"\$([A-Z]{1,5})\b", text.upper()):
        tickers.add(m.group(1))

    # 2) Standalone uppercase words that look like tickers
    for m in _re.finditer(r"\b([A-Z]{1,5})\b", text):
        candidate = m.group(1)
        if candidate not in _COMMON_WORD_TICKERS and len(candidate) >= 2:
            tickers.add(candidate)

    # 3) Mixed-case common tickers (e.g. "aapl", "Aapl")
    for m in _re.finditer(r"\b([A-Za-z]{2,5})\b", text):
        upper = m.group(1).upper()
        if upper not in _COMMON_WORD_TICKERS:
            # Only add if the original was already uppercase or $ prefixed
            pass  # handled above

    return sorted(tickers)


# ─── User Profile Tracker ──────────────────────────────────

_PROFILE_EXTRACTION_PROMPT = """Analyze the following conversation and extract any user preferences or profile information that was mentioned.
Return a JSON object with ONLY the fields that were explicitly mentioned (omit fields with no info).

Possible fields:
- "risk_tolerance": "conservative" | "moderate" | "aggressive"
- "investment_horizon": e.g. "short-term (< 1 year)" | "medium-term (1-5 years)" | "long-term (5+ years)"
- "budget": e.g. "$10,000" | "$50,000"
- "goal": e.g. "growth" | "income" | "preservation" | "retirement"
- "holdings": list of tickers they mentioned owning, e.g. ["QQQ", "AAPL"]
- "purchase_prices": dict of ticker to purchase price, e.g. {"QQQM": 180}
- "preferred_sectors": list of sectors they mentioned interest in
- "age_range": e.g. "20s" | "30s" | "40s" | "retired"

Conversation:
{conversation}

Return ONLY valid JSON, no explanation."""


def _extract_user_profile(chat_history: list[dict]) -> dict:
    """
    Extract user profile/preferences from chat history using simple
    keyword matching. Fast, no LLM call needed.
    """
    profile = {}
    holdings = set()
    purchase_prices = {}

    for msg in chat_history:
        if msg["role"] != "user":
            continue
        text = msg["content"].lower()

        # Risk tolerance
        if not profile.get("risk_tolerance"):
            if any(w in text for w in ["conservative", "safe", "low risk", "risk-averse"]):
                profile["risk_tolerance"] = "conservative"
            elif any(w in text for w in ["aggressive", "high risk", "high-risk", "risky"]):
                profile["risk_tolerance"] = "aggressive"
            elif any(w in text for w in ["moderate", "balanced", "medium risk"]):
                profile["risk_tolerance"] = "moderate"

        # Investment horizon
        if not profile.get("investment_horizon"):
            if any(w in text for w in ["long term", "long-term", "10 year", "5 year", "retire"]):
                profile["investment_horizon"] = "long-term (5+ years)"
            elif any(w in text for w in ["short term", "short-term", "quick", "day trade", "swing"]):
                profile["investment_horizon"] = "short-term (< 1 year)"
            elif any(w in text for w in ["medium term", "medium-term", "1-3 year", "few years"]):
                profile["investment_horizon"] = "medium-term (1-5 years)"

        # Goal
        if not profile.get("goal"):
            if any(w in text for w in ["passive income", "dividend", "income", "yield"]):
                profile["goal"] = "income"
            elif any(w in text for w in ["growth", "capital appreciation", "grow"]):
                profile["goal"] = "growth"
            elif any(w in text for w in ["preserve", "preservation", "protect"]):
                profile["goal"] = "preservation"

        # Budget — look for dollar amounts
        budget_match = _re.search(r"\$([\d,]+(?:\.\d+)?)", msg["content"])
        if budget_match and not profile.get("budget"):
            profile["budget"] = f"${budget_match.group(1)}"

        # Holdings — "I bought X" / "I own X" / "I have X"
        for m in _re.finditer(
            r"(?:bought|own|have|holding|invested in)\s+([A-Z]{1,5})",
            msg["content"],
        ):
            ticker = m.group(1)
            if ticker not in _COMMON_WORD_TICKERS:
                holdings.add(ticker)

        # Purchase prices — "bought X at $Y" / "X at $Y"
        for m in _re.finditer(
            r"([A-Z]{1,5})\s+(?:at|@)\s+\$?([\d.]+)",
            msg["content"],
        ):
            ticker = m.group(1)
            if ticker not in _COMMON_WORD_TICKERS:
                purchase_prices[ticker] = float(m.group(2))
                holdings.add(ticker)

    if holdings:
        profile["holdings"] = sorted(holdings)
    if purchase_prices:
        profile["purchase_prices"] = purchase_prices

    return profile


def _format_user_profile(profile: dict) -> str:
    """Format extracted profile for injection into the system prompt."""
    if not profile:
        return ""

    lines = ["\n═══ KNOWN USER PREFERENCES ═══"]
    mapping = {
        "risk_tolerance": "Risk Tolerance",
        "investment_horizon": "Investment Horizon",
        "budget": "Budget",
        "goal": "Investment Goal",
        "holdings": "Current Holdings",
        "purchase_prices": "Purchase Prices",
        "preferred_sectors": "Preferred Sectors",
        "age_range": "Age Range",
    }
    for key, label in mapping.items():
        val = profile.get(key)
        if val:
            if isinstance(val, list):
                lines.append(f"- {label}: {', '.join(val)}")
            elif isinstance(val, dict):
                pairs = [f"{k}: ${v}" for k, v in val.items()]
                lines.append(f"- {label}: {', '.join(pairs)}")
            else:
                lines.append(f"- {label}: {val}")

    lines.append(
        "\nUse this context to personalize your advice. Do NOT re-ask questions "
        "the user has already answered above."
    )
    lines.append("═══ END USER PREFERENCES ═══")
    return "\n".join(lines)


# ─── Chat Summarization ───────────────────────────────────

def _summarize_chat_history(
    chat_history: list[dict],
    keep_recent: int = 6,
) -> list[dict]:
    """
    For long conversations, keep the most recent messages verbatim
    and compress older messages into a summary to save context window.
    """
    if len(chat_history) <= keep_recent:
        return chat_history

    older = chat_history[:-keep_recent]
    recent = chat_history[-keep_recent:]

    # Build a condensed summary of older messages
    summary_parts = []
    for msg in older:
        role = msg["role"]
        content = msg["content"]
        # Truncate long messages
        if len(content) > 200:
            content = content[:200] + "..."
        summary_parts.append(f"{role}: {content}")

    summary_msg = {
        "role": "user",
        "content": (
            "[CONVERSATION SUMMARY — earlier messages condensed]\n"
            + "\n".join(summary_parts)
            + "\n[END SUMMARY — recent messages follow]"
        ),
    }

    return [summary_msg] + recent


# ─── Tool-Calling AI Advisor ───────────────────────────────


def _fetch_ticker_snapshot(symbol: str) -> str:
    """Fetch a quick data snapshot for a single ticker (stock or ETF). ~1-2s."""
    import json
    import yfinance as yf

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1y")

        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)

        # Basic returns
        returns = {}
        if not hist.empty:
            closes = hist["Close"]
            for label, days in [("1m", 21), ("3m", 63), ("1y", 252)]:
                if len(closes) >= days:
                    start = float(closes.iloc[-days])
                    if start > 0:
                        returns[label] = round(((price - start) / start) * 100, 2)
            # YTD
            from datetime import datetime
            year_data = closes[closes.index.year == datetime.now().year]
            if not year_data.empty:
                ytd_start = float(year_data.iloc[0])
                if ytd_start > 0:
                    returns["ytd"] = round(((price - ytd_start) / ytd_start) * 100, 2)

        snapshot = {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName", symbol),
            "price": round(float(price), 2) if price else None,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "dividend_yield": round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else None,
            "market_cap": info.get("marketCap"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "beta": info.get("beta"),
            "returns": returns,
            "expense_ratio": info.get("annualReportExpenseRatio"),
            "total_assets": info.get("totalAssets"),
            "category": info.get("category"),
            "analyst_target": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey"),
        }
        # Remove None values for cleaner output
        snapshot = {k: v for k, v in snapshot.items() if v is not None}
        return json.dumps(snapshot, indent=2)
    except Exception as e:
        return json.dumps({"symbol": symbol, "error": str(e)})


def _run_technical_analysis(symbol: str) -> str:
    """Run technical analysis (RSI, MACD, moving averages, Bollinger Bands)."""
    import json
    try:
        result = get_technical_analysis(symbol)
        if "error" in result:
            return json.dumps({"symbol": symbol, "error": result["error"]})
        # Flatten for LLM readability
        summary = {"symbol": symbol}
        if "rsi" in result:
            summary["rsi"] = result["rsi"]
        if "macd" in result:
            summary["macd"] = result["macd"]
        if "moving_averages" in result:
            summary["moving_averages"] = result["moving_averages"]
        if "patterns" in result:
            summary["patterns"] = result["patterns"]
        return json.dumps(summary, indent=2, default=str)
    except Exception as e:
        return json.dumps({"symbol": symbol, "error": str(e)})


def _run_fundamental_analysis(symbol: str) -> str:
    """Run fundamental analysis (valuation ratios, profitability, financial health)."""
    import json
    try:
        health = get_financial_health(symbol)
        valuation = get_valuation_ratios(symbol)
        profitability = get_profitability_ratios(symbol)
        return json.dumps({
            "symbol": symbol,
            "financial_health": health if "error" not in health else None,
            "valuation": valuation if "error" not in valuation else None,
            "profitability": profitability if "error" not in profitability else None,
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"symbol": symbol, "error": str(e)})


def _run_dividend_analysis(symbol: str) -> str:
    """Run dividend analysis (yield, safety, growth history)."""
    import json
    try:
        from src.tools.dividend_analyzer import analyze_dividends as _fn
        result = _fn(symbol)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"symbol": symbol, "error": str(e)})


def _run_earnings_analysis(symbol: str) -> str:
    """Run earnings analysis (EPS surprises, beat/miss patterns, quality)."""
    import json
    try:
        from src.tools.earnings_data import analyze_earnings as _fn
        result = _fn(symbol)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"symbol": symbol, "error": str(e)})


def _run_sentiment_analysis(symbol: str) -> str:
    """Run news sentiment analysis."""
    import json
    try:
        result = analyze_news_sentiment(symbol)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"symbol": symbol, "error": str(e)})


def _run_peer_comparison(symbol: str) -> str:
    """Run peer comparison analysis."""
    import json
    try:
        result = compare_peers(symbol)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"symbol": symbol, "error": str(e)})


def _run_options_analysis(symbol: str) -> str:
    """Run options flow analysis (put/call ratio, IV, max pain, unusual activity)."""
    import json
    try:
        from src.tools.options_analyzer import analyze_options as _fn
        result = _fn(symbol)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"symbol": symbol, "error": str(e)})


def _run_insider_analysis(symbol: str) -> str:
    """Run insider & institutional activity analysis (smart money signal)."""
    import json
    try:
        from src.tools.insider_activity import analyze_smart_money as _fn
        result = _fn(symbol)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"symbol": symbol, "error": str(e)})


_ADVISOR_SYSTEM_PROMPT = """You are an expert AI financial advisor with access to real-time market data.

═══ GUARDRAILS — STRICTLY ENFORCE ═══

SCOPE — Only answer questions about:
- Stocks, ETFs, mutual funds, bonds, and index funds
- Portfolio strategy, diversification, and asset allocation
- Dividends, earnings, valuations, and financial metrics
- Market themes, sectors, and economic trends
- Investment timing, risk management, and holding periods
- Options flow, insider activity, and institutional positioning

REFUSE politely if the user asks about:
- Cryptocurrency, NFTs, meme coins, or DeFi (say: "I specialize in stocks and ETFs. For crypto, please consult a crypto-focused platform.")
- Penny stocks or OTC securities (say: "I focus on established exchange-listed securities for safety.")
- Insider trading, market manipulation, or any illegal activity
- Tax advice, estate planning, or legal matters (say: "Please consult a tax professional or financial planner for personalized tax/legal advice.")
- Anything unrelated to investing or finance (say: "I'm a financial advisor — I can help with stocks, ETFs, and investing questions.")

SAFETY — Always follow these:
- NEVER guarantee returns or promise specific outcomes. Use words like "historically", "may", "based on current data".
- NEVER recommend putting all money into a single stock or ETF. Always suggest diversification.
- NEVER recommend leveraged/inverse ETFs without explicitly warning about the amplified risk.
- NEVER dismiss risk. Always acknowledge downside scenarios.
- For high-volatility or speculative investments, always flag the risk prominently.
- If a user appears to be making an emotionally-driven decision (panic selling, FOMO buying), gently encourage a measured approach.
- EVERY response with a recommendation MUST end with: "*This is informational analysis based on publicly available data, not personalized financial advice. Please consult a licensed financial advisor before making investment decisions.*"

═══ BEHAVIOR RULES ═══

- NEVER mention tools, functions, or internal processes in your response.
  Do NOT say things like "I'll use lookup_ticker" or "Let me look up the data".
  Just present the information naturally as if you already know it.
- NEVER narrate what you are doing. Just do it and present the result.

═══ CONVERSATIONAL APPROACH — ALWAYS FOLLOW THIS ═══

On the user's FIRST message about a topic, ALWAYS ask 2-3 short clarifying questions
BEFORE giving your analysis. This applies to every type of question. Examples:

- "Compare QQQ vs VOO" → Ask: Are you investing for growth or income? What's your time horizon?
- "How long should I hold X?" → Ask: When did you buy it? What's your target return or goal?
- "Should I sell X?" → Ask: What's your purchase price? Are you investing for income or growth?
- "Is X good for me?" → Ask: What's your risk tolerance? What's your investment horizon?
- "Build me a portfolio" → Ask: What's your total budget? Are you conservative or aggressive?
- "Which ETF should I invest in?" → Ask: What's your investment goal? How much are you looking to invest?
- "What's the best dividend ETF?" → Ask: What yield are you targeting? Do you prefer safety or high yield?

HOWEVER — if a USER PREFERENCES section is present below, the user may have already
answered these questions. Do NOT re-ask questions the user has already answered.
Use their known preferences directly and ask only about MISSING information.

ONLY answer directly WITHOUT questions when:
- The user is answering your previous clarifying questions (follow-up in conversation)
- The user asks a pure factual question like "What's the price of AAPL?"
- All relevant preferences are already known from the USER PREFERENCES section

Once the user answers your clarifying questions, synthesize everything and give a
specific, data-backed recommendation.

For broad questions, look up a few popular ETFs (e.g. QQQ, VOO, VTI, ARKK, XLK)
to compare them when giving your final recommendation.

═══ ANALYSIS TOOLS AVAILABLE ═══

You have access to these specialized analysis tools. Use the RIGHT tools for the question:

- **lookup_ticker**: Quick price, returns, key stats. Use for simple price checks.
- **run_technical**: RSI, MACD, Moving Averages, Bollinger Bands, chart patterns.
  Use when asked about buy/sell timing, entry/exit points, or technical signals.
- **run_fundamentals**: P/E, P/B, ROE, margins, valuation, financial health.
  Use when asked about whether a stock is overvalued, fundamentals, or financials.
- **run_dividends**: Dividend yield, safety score, payout ratio, growth history.
  Use when asked about dividends, passive income, or income investing.
- **run_earnings**: EPS actuals vs estimates, beat/miss patterns, quarterly trends, and earnings quality score.
  Use when asked about earnings, quarterly results, or EPS.
- **run_sentiment**: News sentiment aggregation and scoring.
  Use when asked about market sentiment, news, or public perception.
- **run_peers**: Peer comparison on valuation, performance, and profitability.
  Use when asked to compare companies or for competitive positioning.
- **run_options**: Options flow analysis — put/call ratio, implied volatility,
  max pain, and unusual activity detection.
  Use when asked about options flow, market positioning, or expected moves.
- **run_insider**: Insider & institutional activity — Form 4 filings, cluster buying,
  institutional ownership, and a combined smart money score.
  Use when asked about insider buying/selling, institutional interest, or smart money.

═══ TOOL USAGE STRATEGY ═══

For comprehensive buy/sell/hold recommendations, use MULTIPLE tools:
- **Quick check**: lookup_ticker only
- **Should I buy/sell?**: lookup_ticker + run_technical + run_fundamentals
- **Timing questions**: run_technical + run_options
- **Income investing**: lookup_ticker + run_dividends + run_fundamentals
- **Due diligence**: lookup_ticker + run_fundamentals + run_earnings + run_insider
- **Full analysis**: lookup_ticker + run_technical + run_fundamentals + run_sentiment + run_options

ALWAYS use lookup_ticker as a starting point for any recommendation. Combine with
deeper analysis tools based on the question type.

═══ RESPONSE GUIDELINES ═══

- Be specific with numbers and explain your reasoning
- For buy/sell/hold, reference price trends, returns, and valuation
- When comparing investments, present a balanced view with pros AND cons
- Flag concentration risk if a user is overweight in one sector or stock
- Suggest position sizing (e.g. "consider allocating 5-10% of your portfolio")
- When options data is available, mention put/call ratio and max pain for context
- When insider data is available, mention the smart money signal
- Structure responses with clear sections using markdown headers

Keep answers concise and use markdown formatting."""


def ask_advisor(
    question: str,
    chat_history: list[dict] | None = None,
    on_progress: "callable | None" = None,
) -> str:
    """
    AI Advisor with on-demand tool calling — the LLM decides which
    analyses to run based on the question.

    Enhanced features:
    - Pre-fetches ticker snapshots for detected symbols (context injection)
    - Parallel tool execution via ThreadPoolExecutor
    - User profile tracking (persists preferences across messages)
    - Chat summarization for long conversations
    - 9 analysis tools including options flow & insider activity
    - Response validation (disclaimer, data references, risk mentions)

    Available tools (orchestrator pipeline):
    - lookup_ticker: Quick price/returns snapshot
    - run_technical: RSI, MACD, moving averages, patterns
    - run_fundamentals: Valuation, profitability, financial health
    - run_dividends: Yield, safety score, growth history
    - run_earnings: EPS surprises, beat/miss patterns, quality
    - run_sentiment: News sentiment analysis
    - run_peers: Peer comparison
    - run_options: Options flow (put/call ratio, IV, max pain)
    - run_insider: Insider & institutional activity (smart money)

    Args:
        question: The user's question.
        chat_history: Previous messages for context.
        on_progress: Optional callback ``fn(step_key, label)`` called as
            the advisor progresses through analysis steps.

    Returns:
        The LLM response text.
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.tools import tool as lc_tool
    import concurrent.futures

    def _emit(key: str, label: str):
        if on_progress:
            on_progress(key, label)

    llm = _get_llm()
    history = chat_history or []

    # ── Step 1: Extract user profile from conversation history ──
    _emit("profiling", "Understanding your preferences...")
    user_profile = _extract_user_profile(history + [{"role": "user", "content": question}])
    profile_context = _format_user_profile(user_profile)

    # ── Step 2: Pre-fetch snapshots for detected tickers ──
    detected_tickers = _extract_tickers(question)
    prefetch_context = ""

    if detected_tickers:
        _emit("prefetch", f"Fetching live data for {', '.join(detected_tickers)}...")
        # Parallel pre-fetch
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            futures = {
                ex.submit(_fetch_ticker_snapshot, t): t
                for t in detected_tickers[:5]  # Cap at 5 tickers
            }
            snapshots = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    snapshots.append(future.result())
                except Exception:
                    pass
        if snapshots:
            prefetch_context = (
                "\n═══ PRE-FETCHED MARKET DATA (for tickers mentioned in the question) ═══\n"
                + "\n---\n".join(snapshots)
                + "\n═══ END PRE-FETCHED DATA ═══\n"
                "\nYou already have this data. Use it directly; only call lookup_ticker for "
                "tickers NOT shown above. Use deeper analysis tools (technical, fundamentals, "
                "etc.) when the user needs more than a quick snapshot."
            )

    # ── Step 3: Summarize long conversations ──
    condensed_history = _summarize_chat_history(history)

    # ── Step 4: Build system prompt with injected context ──
    system_prompt = _ADVISOR_SYSTEM_PROMPT
    if profile_context:
        system_prompt += "\n" + profile_context
    if prefetch_context:
        system_prompt += "\n" + prefetch_context

    # ── Tool definitions — each maps to an orchestrator analysis ──

    @lc_tool
    def lookup_ticker(symbol: str) -> str:
        """Look up real-time price, returns, and key metrics for a stock or ETF.
        Use for quick price checks or when you need an overview.
        Examples: lookup_ticker("QQQ"), lookup_ticker("AAPL")"""
        sym = symbol.upper().strip()
        _emit("lookup", f"Fetching {sym} market data...")
        return _fetch_ticker_snapshot(sym)

    @lc_tool
    def run_technical(symbol: str) -> str:
        """Run technical analysis on a stock — RSI, MACD, moving averages,
        Bollinger Bands, and chart patterns. Use when the user asks about
        buy/sell timing, technical signals, or chart analysis.
        Examples: run_technical("AAPL"), run_technical("QQQ")"""
        sym = symbol.upper().strip()
        _emit("technical", f"Running technical analysis on {sym} (RSI, MACD, Moving Averages)...")
        return _run_technical_analysis(sym)

    @lc_tool
    def run_fundamentals(symbol: str) -> str:
        """Run fundamental analysis — valuation ratios (P/E, P/B, EV/EBITDA),
        profitability (ROE, ROA, margins), and financial health.
        Use when the user asks about valuation, whether a stock is overvalued, or financials.
        Examples: run_fundamentals("MSFT"), run_fundamentals("GOOGL")"""
        sym = symbol.upper().strip()
        _emit("fundamentals", f"Running fundamental analysis on {sym} (Valuation, Profitability, Health)...")
        return _run_fundamental_analysis(sym)

    @lc_tool
    def run_dividends(symbol: str) -> str:
        """Run dividend analysis — yield, safety score, payout ratio,
        growth history, and Dividend King/Aristocrat classification.
        Use when the user asks about dividends, income investing, or yield.
        Examples: run_dividends("JNJ"), run_dividends("KO")"""
        sym = symbol.upper().strip()
        _emit("dividends", f"Analyzing {sym} dividend profile (Yield, Safety, Growth History)...")
        return _run_dividend_analysis(sym)

    @lc_tool
    def run_earnings(symbol: str) -> str:
        """Run quarterly earnings analysis — EPS actual vs estimates,
        beat/miss patterns, quarterly trends, and earnings quality score.
        Use when the user asks about earnings, EPS, or quarterly results.
        Examples: run_earnings("AAPL"), run_earnings("NVDA")"""
        sym = symbol.upper().strip()
        _emit("earnings", f"Analyzing {sym} quarterly earnings (EPS Surprises, Trends, Quality)...")
        return _run_earnings_analysis(sym)

    @lc_tool
    def run_sentiment(symbol: str) -> str:
        """Run news sentiment analysis — aggregates recent news and
        calculates overall sentiment score. Use when the user asks
        about market sentiment, news impact, or public perception.
        Examples: run_sentiment("TSLA"), run_sentiment("META")"""
        sym = symbol.upper().strip()
        _emit("sentiment", f"Analyzing {sym} news sentiment...")
        return _run_sentiment_analysis(sym)

    @lc_tool
    def run_peers(symbol: str) -> str:
        """Run peer comparison — compares a stock against its sector peers
        on valuation, performance, and profitability.
        Use when the user asks to compare a stock, or for competitive positioning.
        Examples: run_peers("AAPL"), run_peers("JPM")"""
        sym = symbol.upper().strip()
        _emit("peers", f"Comparing {sym} against sector peers...")
        return _run_peer_comparison(sym)

    @lc_tool
    def run_options(symbol: str) -> str:
        """Run options flow analysis — put/call ratio, implied volatility,
        max pain calculation, and unusual activity detection.
        Use when the user asks about options flow, expected price moves,
        or market positioning. Helps gauge short-term sentiment.
        Examples: run_options("TSLA"), run_options("AAPL")"""
        sym = symbol.upper().strip()
        _emit("options", f"Analyzing {sym} options flow (Put/Call, IV, Max Pain)...")
        return _run_options_analysis(sym)

    @lc_tool
    def run_insider(symbol: str) -> str:
        """Run insider & institutional activity analysis — recent insider
        buys/sells (Form 4), cluster buying detection, institutional
        ownership, and a combined smart money score (0-100).
        Use when the user asks about insider trading, institutional
        interest, or smart money signals.
        Examples: run_insider("AAPL"), run_insider("NVDA")"""
        sym = symbol.upper().strip()
        _emit("insider", f"Tracking {sym} insider & institutional activity (Smart Money)...")
        return _run_insider_analysis(sym)

    all_tools = [
        lookup_ticker, run_technical, run_fundamentals,
        run_dividends, run_earnings, run_sentiment, run_peers,
        run_options, run_insider,
    ]

    _emit("analyzing", "Analyzing your question...")

    messages = [SystemMessage(content=system_prompt)]

    # Add (possibly summarized) chat history
    for msg in condensed_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=question))

    try:
        llm_with_tools = llm.bind_tools(all_tools)
        tool_map = {t.name: t for t in all_tools}

        response = llm_with_tools.invoke(messages)

        # ── Process tool calls in rounds with PARALLEL execution ──
        max_rounds = 4
        rounds = 0
        while response.tool_calls and rounds < max_rounds:
            messages.append(response)
            from langchain_core.messages import ToolMessage

            # Execute all tool calls in this round IN PARALLEL
            tool_calls = response.tool_calls
            if len(tool_calls) > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
                    future_to_tc = {
                        ex.submit(
                            tool_map[tc["name"]].invoke if tc["name"] in tool_map else lambda _: f"Unknown tool: {tc['name']}",
                            tc["args"],
                        ): tc
                        for tc in tool_calls
                    }
                    for future in concurrent.futures.as_completed(future_to_tc):
                        tc = future_to_tc[future]
                        try:
                            tool_result = future.result()
                        except Exception as exc:
                            tool_result = f"Tool error: {exc}"
                        messages.append(
                            ToolMessage(content=str(tool_result), tool_call_id=tc["id"])
                        )
            else:
                # Single tool call — run directly
                tc = tool_calls[0]
                tool_fn = tool_map.get(tc["name"])
                if tool_fn:
                    tool_result = tool_fn.invoke(tc["args"])
                else:
                    tool_result = f"Unknown tool: {tc['name']}"
                messages.append(
                    ToolMessage(content=str(tool_result), tool_call_id=tc["id"])
                )

            _emit("synthesizing", "Synthesizing insights & preparing recommendation...")
            response = llm_with_tools.invoke(messages)
            rounds += 1

        result = response.content

        # ── Step 5: Validate response ──
        result = _validate_advisor_response(result, question)

        return result

    except (NotImplementedError, TypeError, AttributeError):
        # Provider doesn't support tool calling — fall back to plain chat
        _emit("fallback", "Using conversational mode...")
        context = prefetch_context + profile_context
        return ask_financial_question(question=question, context=context, chat_history=chat_history)
    except Exception as e:
        error_msg = str(e)
        # Detect tool-calling failures (Groq/some models format tool calls incorrectly)
        if "tool_use_failed" in error_msg or "failed_generation" in error_msg or "Failed to call a function" in error_msg:
            _emit("fallback", "Retrying without tool calling...")
            context = prefetch_context + profile_context
            return ask_financial_question(question=question, context=context, chat_history=chat_history)
        return f"I'm unable to answer right now. Please check that your LLM provider is running.\n\nError: {e}"


# ─── Response Validation ──────────────────────────────────

_DISCLAIMER = (
    "\n\n*This is informational analysis based on publicly available data, "
    "not personalized financial advice. Please consult a licensed financial "
    "advisor before making investment decisions.*"
)


def _validate_advisor_response(response: str, question: str) -> str:
    """
    Post-process the advisor response to ensure quality:
    - Appends disclaimer if missing and response contains a recommendation
    - Checks for risk mention on buy recommendations
    """
    if not response:
        return response

    # Keywords that indicate a recommendation was made
    recommendation_keywords = [
        "recommend", "suggest", "consider", "buy", "sell", "hold",
        "allocate", "invest", "position", "portfolio",
    ]
    has_recommendation = any(
        kw in response.lower() for kw in recommendation_keywords
    )

    # Ensure disclaimer is present for recommendations
    if has_recommendation:
        disclaimer_fragments = ["not personalized", "financial advice", "licensed financial advisor"]
        has_disclaimer = any(frag in response.lower() for frag in disclaimer_fragments)
        if not has_disclaimer:
            response += _DISCLAIMER

    return response
