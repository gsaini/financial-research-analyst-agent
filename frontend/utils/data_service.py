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
            "dividend_yield": round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else None,
            "market_cap": info.get("marketCap"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "returns": returns,
            "expense_ratio": info.get("annualReportExpenseRatio"),
            "total_assets": info.get("totalAssets"),
            "category": info.get("category"),
        }
        # Remove None values for cleaner output
        snapshot = {k: v for k, v in snapshot.items() if v is not None}
        return json.dumps(snapshot, indent=2)
    except Exception as e:
        return json.dumps({"symbol": symbol, "error": str(e)})


def ask_advisor(
    question: str,
    chat_history: list[dict] | None = None,
) -> str:
    """
    AI Advisor with on-demand tool calling — fetches only what's needed.

    The LLM has access to a lookup tool that fetches real-time data for
    individual tickers. No bulk pre-fetch required.

    Args:
        question: The user's question.
        chat_history: Previous messages for context.

    Returns:
        The LLM response text.
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.tools import tool as lc_tool

    llm = _get_llm()

    # Define the lookup tool
    @lc_tool
    def lookup_ticker(symbol: str) -> str:
        """Look up real-time price, returns, and key metrics for a stock or ETF symbol.
        Use this when you need current data to answer a question about a specific ticker.
        Examples: lookup_ticker("QQQ"), lookup_ticker("AAPL")"""
        return _fetch_ticker_snapshot(symbol.upper().strip())

    system_prompt = """You are an expert AI financial advisor with access to real-time market data.

You can look up any stock or ETF using the lookup_ticker tool to get current prices, returns,
and key metrics. Use this tool when the user asks about specific tickers.

IMPORTANT — Conversational Approach:
When a user's question needs more context to give a truly helpful answer, ASK 2-3 short
clarifying questions BEFORE answering. For example:
- "How long should I hold X?" → Ask: When did you buy it? What's your target return?
- "Should I sell X?" → Ask: What's your purchase price? Are you investing for income or growth?
- "Is X good for me?" → Ask: What's your risk tolerance? What's your investment horizon?
- "Build me a portfolio" → Ask: What's your total budget? Conservative or aggressive?

When you have enough context, answer directly with specific numbers.

For broad questions like "Which ETF should I invest in?", look up a few popular ETFs
(e.g. QQQ, VOO, VTI, ARKK, XLK) to compare them, then give a recommendation.

Guidelines:
- Use the lookup_ticker tool to get real data — don't guess prices or returns
- Be specific with numbers and explain your reasoning
- For buy/sell/hold, reference price trends, returns, and valuation
- Always end with a brief disclaimer that this is informational, not financial advice

Keep answers concise and use markdown formatting."""

    messages = [SystemMessage(content=system_prompt)]

    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=question))

    try:
        # Try tool-calling agent first
        llm_with_tools = llm.bind_tools([lookup_ticker])
        response = llm_with_tools.invoke(messages)

        # If the LLM made tool calls, execute them and get final answer
        if response.tool_calls:
            messages.append(response)
            from langchain_core.messages import ToolMessage

            for tc in response.tool_calls:
                tool_result = lookup_ticker.invoke(tc["args"])
                messages.append(
                    ToolMessage(content=tool_result, tool_call_id=tc["id"])
                )

            final = llm_with_tools.invoke(messages)

            # Handle case where LLM makes additional tool calls (multi-hop)
            max_rounds = 3
            rounds = 0
            while final.tool_calls and rounds < max_rounds:
                messages.append(final)
                for tc in final.tool_calls:
                    tool_result = lookup_ticker.invoke(tc["args"])
                    messages.append(
                        ToolMessage(content=tool_result, tool_call_id=tc["id"])
                    )
                final = llm_with_tools.invoke(messages)
                rounds += 1

            return final.content
        else:
            return response.content

    except (NotImplementedError, TypeError, AttributeError):
        # Fallback for providers that don't support tool calling —
        # just answer without live data
        return ask_financial_question(question=question, context="", chat_history=chat_history)
    except Exception as e:
        return f"I'm unable to answer right now. Please check that your LLM provider is running.\n\nError: {e}"
