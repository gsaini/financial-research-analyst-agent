# AI Financial Advisor — Technical Documentation

> **Feature**: AI Advisor (Page 13)  
> **Version**: 2.0 — Enhanced with context injection, parallel execution, and 9 analysis tools  
> **Files**: [13_AI_Advisor.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/pages/13_AI_Advisor.py), [data_service.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py)

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Processing Pipeline](#processing-pipeline)
4. [Analysis Tools](#analysis-tools)
5. [LLM Integration](#llm-integration)
6. [System Prompt Engineering](#system-prompt-engineering)
7. [Pre-Processing Layer](#pre-processing-layer)
8. [Post-Processing Layer](#post-processing-layer)
9. [Error Handling & Fallback](#error-handling--fallback)
10. [UI Layer](#ui-layer)
11. [Configuration Reference](#configuration-reference)
12. [File Reference](#file-reference)

---

## Overview

The AI Financial Advisor is an interactive chat interface built with **Streamlit** that provides personalized financial guidance about stocks, ETFs, dividends, portfolio strategy, and market themes. It uses a **single LLM agent with tool-calling** (ReAct-style loop) to dynamically fetch and analyze real-time market data before generating responses.

### Key Design Principles

- **On-demand data fetching** — Only queries the data sources relevant to the user's question
- **Context-aware** — Pre-fetches ticker data and tracks user preferences across the conversation
- **Multi-provider** — Supports 6 different LLM backends (local and cloud)
- **Safety-first** — Enforced guardrails prevent crypto, penny stock, and off-topic responses
- **Graceful degradation** — Falls back to plain chat if tool-calling fails

---

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph Frontend ["Frontend Layer (Streamlit)"]
        UI["13_AI_Advisor.py<br/>Chat UI & Progress Display"]
        FAQ["FAQ Templates<br/>Quick Question Buttons"]
        HIST["Session State<br/>advisor_chat_history"]
    end

    subgraph Orchestrator ["Orchestration Layer (data_service.py)"]
        ASK["ask_advisor()<br/>Main Entry Point"]
        
        subgraph PreProcess ["Pre-Processing"]
            TICK["_extract_tickers()<br/>Regex Ticker Detection"]
            PROF["_extract_user_profile()<br/>Keyword Profile Extraction"]
            SUMM["_summarize_chat_history()<br/>Context Compression"]
            SNAP["_fetch_ticker_snapshot()<br/>Parallel Pre-fetch"]
        end

        subgraph ToolLoop ["Tool-Calling Loop (max 4 rounds)"]
            LLM_CALL["LLM.invoke()<br/>with bound tools"]
            PARALLEL["ThreadPoolExecutor<br/>Parallel Tool Execution"]
        end

        subgraph PostProcess ["Post-Processing"]
            VALID["_validate_advisor_response()<br/>Disclaimer & Risk Check"]
        end
    end

    subgraph LLM_Layer ["LLM Provider Layer"]
        OLLAMA["Ollama<br/>ChatOllama"]
        LMSTUDIO["LM Studio<br/>ChatOpenAI"]
        VLLM["vLLM<br/>ChatOpenAI"]
        GROQ["Groq<br/>ChatGroq"]
        ANTHROPIC["Anthropic<br/>ChatAnthropic"]
        OPENAI["OpenAI<br/>ChatOpenAI"]
    end

    subgraph Tools ["9 Analysis Tools"]
        T1["lookup_ticker<br/>📊 Price & Stats"]
        T2["run_technical<br/>📈 RSI, MACD, MA"]
        T3["run_fundamentals<br/>📋 P/E, ROE, Health"]
        T4["run_dividends<br/>💰 Yield, Safety"]
        T5["run_earnings<br/>📑 EPS, Quality"]
        T6["run_sentiment<br/>📰 News Scoring"]
        T7["run_peers<br/>🔄 Peer Comparison"]
        T8["run_options<br/>⚡ Options Flow"]
        T9["run_insider<br/>🔍 Smart Money"]
    end

    subgraph DataSources ["Data Sources"]
        YF["Yahoo Finance<br/>yfinance API"]
        NEWS["News APIs<br/>RSS/Web Scraping"]
    end

    UI --> ASK
    FAQ --> HIST
    HIST --> ASK

    ASK --> TICK
    ASK --> PROF
    ASK --> SUMM
    TICK --> SNAP

    SNAP --> LLM_CALL
    PROF --> LLM_CALL
    SUMM --> LLM_CALL

    LLM_CALL --> PARALLEL
    PARALLEL --> T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9
    T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9 --> LLM_CALL

    LLM_CALL --> VALID
    VALID --> UI

    LLM_CALL -.-> OLLAMA & LMSTUDIO & VLLM & GROQ & ANTHROPIC & OPENAI

    T1 & T2 & T3 & T4 & T5 & T8 & T9 --> YF
    T6 --> NEWS

    style Frontend fill:#1e1b4b,color:#e0e7ff
    style Orchestrator fill:#0c0a09,color:#fafaf9
    style LLM_Layer fill:#064e3b,color:#ecfdf5
    style Tools fill:#172554,color:#dbeafe
    style DataSources fill:#431407,color:#fed7aa
```

### Request-Response Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as 13_AI_Advisor.py
    participant O as ask_advisor()
    participant PP as Pre-Processing
    participant LLM as LLM Provider
    participant T as Tool Layer
    participant V as Validation

    U->>UI: Types question or clicks FAQ
    UI->>O: ask_advisor(question, chat_history, on_progress)
    
    O->>PP: Step 1: _extract_user_profile()
    PP-->>O: {risk_tolerance, budget, holdings, ...}
    
    O->>PP: Step 2: _extract_tickers()
    PP-->>O: ["AAPL", "QQQ"]
    
    O->>T: Parallel _fetch_ticker_snapshot() for each ticker
    T-->>O: JSON snapshots (price, returns, PE, ...)
    
    O->>PP: Step 3: _summarize_chat_history()
    PP-->>O: Condensed message list
    
    O->>O: Step 4: Build system prompt + profile + snapshots
    
    O->>LLM: invoke(messages + bound tools)
    
    loop Tool-Calling Loop (max 4 rounds)
        LLM-->>O: tool_calls: [{name, args, id}]
        O->>T: Execute tools IN PARALLEL (ThreadPoolExecutor)
        T-->>O: Tool results (JSON)
        O->>LLM: Re-invoke with ToolMessages
    end
    
    LLM-->>O: Final response content
    
    O->>V: Step 5: _validate_advisor_response()
    V-->>O: Validated response (+ disclaimer if needed)
    
    O-->>UI: Response text
    UI-->>U: Display in chat bubble
```

---

## Processing Pipeline

The advisor processes every query through a **5-step pipeline**:

### Step 1: User Profile Extraction

| What | How | Speed |
|---|---|---|
| Extract risk tolerance | Keyword matching: "conservative", "aggressive", "moderate" | <1ms |
| Extract investment horizon | Keyword matching: "long-term", "short-term" | <1ms |
| Extract budget | Regex: `$[\d,]+` patterns | <1ms |
| Extract investment goal | Keyword matching: "growth", "income", "preservation" | <1ms |
| Extract holdings | Regex: "I bought/own/have X" patterns | <1ms |
| Extract purchase prices | Regex: "X at $Y" or "X @ $Y" patterns | <1ms |

> [!NOTE]
> Profile extraction uses **pure regex and keyword matching** — no LLM call required. This keeps it fast and deterministic.

**Source**: [_extract_user_profile()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L586-L656)

### Step 2: Ticker Pre-Fetch

```
User: "Compare QQQ vs VOO for long-term growth"
                    ↓
    _extract_tickers() → ["QQQ", "VOO"]
                    ↓
    ThreadPoolExecutor(max_workers=5)
     ├── _fetch_ticker_snapshot("QQQ")  ──→ JSON snapshot
     └── _fetch_ticker_snapshot("VOO")  ──→ JSON snapshot
                    ↓
    Injected as ═══ PRE-FETCHED MARKET DATA ═══ in system prompt
```

**Source**: [_extract_tickers()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L534-L562), [_fetch_ticker_snapshot()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L735-L789)

### Step 3: Chat Summarization

```
If conversation_length > 6 messages:
    older_messages → Truncated to 200 chars each, joined as "[CONVERSATION SUMMARY]"
    recent_6_messages → Kept verbatim
```

**Source**: [_summarize_chat_history()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L696-L729)

### Step 4: LLM Tool-Calling Loop

```mermaid
graph LR
    A["System Prompt<br/>+ User Profile<br/>+ Pre-fetched Data<br/>+ Chat History<br/>+ User Question"] --> B["LLM.invoke()"]
    B --> C{Tool calls?}
    C -->|Yes| D["Execute tools<br/>(parallel if >1)"]
    D --> E["Append ToolMessages"]
    E --> B
    C -->|No| F["Final Response"]
    C -->|Rounds >= 4| F

    style A fill:#1e1b4b,color:#e0e7ff
    style B fill:#064e3b,color:#ecfdf5
    style D fill:#172554,color:#dbeafe
    style F fill:#14532d,color:#bbf7d0
```

- **Max rounds**: 4 (prevents infinite loops)
- **Parallel execution**: `ThreadPoolExecutor(max_workers=5)` when multiple tools are called in the same round
- **Single tool**: Runs directly without thread pool overhead

**Source**: [ask_advisor()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L1009-L1281)

### Step 5: Response Validation

Checks the final LLM response and auto-fixes issues:

| Check | Action |
|---|---|
| Contains recommendation keywords (buy, sell, hold, etc.) but no disclaimer | Appends standard disclaimer |
| Empty response | Returns as-is |

**Source**: [_validate_advisor_response()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L1293-L1319)

---

## Analysis Tools

### Tool Reference Table

| # | Tool Name | Icon | Underlying Module | Data Source | TTL Cache | Key Outputs |
|---|---|---|---|---|---|---|
| 1 | [lookup_ticker](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1102-1110) | 📊 | `yfinance` (direct) | Yahoo Finance | None | Price, returns (1m/3m/YTD/1y), P/E, forward P/E, PEG, beta, dividend yield, analyst target, recommendation |
| 2 | [run_technical](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1111-1120) | 📈 | `src.tools.technical_indicators` | Yahoo Finance | 300s | RSI, MACD, SMA/EMA, Bollinger Bands, support/resistance, chart patterns |
| 3 | [run_fundamentals](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1121-1130) | 📋 | `src.tools.financial_metrics` | Yahoo Finance | 1800s | P/E, P/B, EV/EBITDA, ROE, ROA, profit margins, debt ratios, financial health score |
| 4 | [run_dividends](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1131-1140) | 💰 | `src.tools.dividend_analyzer` | Yahoo Finance | 1800s | Yield, safety score, payout ratio, growth history, Dividend King/Aristocrat classification |
| 5 | [run_earnings](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1141-1150) | 📑 | `src.tools.earnings_data` | Yahoo Finance | 1800s | EPS actual vs estimates, beat/miss patterns, quarterly trends, earnings quality score |
| 6 | [run_sentiment](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1151-1160) | 📰 | `src.tools.news_impact` | News APIs | 600s | Aggregated sentiment score, article count, topic extraction |
| 7 | [run_peers](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1161-1170) | 🔄 | `src.tools.peer_comparison` | Yahoo Finance | 1800s | Sector peer comparison on valuation, performance, profitability |
| 8 | [run_options](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1171-1181) | ⚡ | `src.tools.options_analyzer` | Yahoo Finance | None | Put/call ratio, implied volatility (volume-weighted), IV skew, max pain, unusual activity (top 5), options sentiment score (0-100) |
| 9 | [run_insider](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1182-1193) | 🔍 | `src.tools.insider_activity` | Yahoo Finance | None | Form 4 insider transactions (90d), cluster buying detection, institutional ownership, top holders, smart money score (0-100) |

### Tool Usage Strategy

The system prompt instructs the LLM to combine tools based on question type:

```mermaid
graph LR
    Q1["Quick check<br/>'What's AAPL price?'"] --> T1["lookup_ticker"]
    
    Q2["Buy/Sell decision<br/>'Should I buy AAPL?'"] --> T1b["lookup_ticker"]
    Q2 --> T2["run_technical"]
    Q2 --> T3["run_fundamentals"]
    
    Q3["Timing question<br/>'When to buy NVDA?'"] --> T2b["run_technical"]
    Q3 --> T8["run_options"]
    
    Q4["Income investing<br/>'Best dividend ETF?'"] --> T1c["lookup_ticker"]
    Q4 --> T4["run_dividends"]
    Q4 --> T3b["run_fundamentals"]
    
    Q5["Due diligence<br/>'Research MSFT for me'"] --> T1d["lookup_ticker"]
    Q5 --> T3c["run_fundamentals"]
    Q5 --> T5["run_earnings"]
    Q5 --> T9["run_insider"]
    
    Q6["Full analysis<br/>'Complete analysis of TSLA'"] --> T1e["lookup_ticker"]
    Q6 --> T2c["run_technical"]
    Q6 --> T3d["run_fundamentals"]
    Q6 --> T6["run_sentiment"]
    Q6 --> T8b["run_options"]

    style Q1 fill:#1e1b4b,color:#e0e7ff
    style Q2 fill:#1e1b4b,color:#e0e7ff
    style Q3 fill:#1e1b4b,color:#e0e7ff
    style Q4 fill:#1e1b4b,color:#e0e7ff
    style Q5 fill:#1e1b4b,color:#e0e7ff
    style Q6 fill:#1e1b4b,color:#e0e7ff
```

### Ticker Snapshot Schema

Each [_fetch_ticker_snapshot()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#735-790) call returns:

```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "price": 178.52,
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "pe_ratio": 28.5,
  "forward_pe": 26.1,
  "peg_ratio": 2.3,
  "dividend_yield": 0.56,
  "market_cap": 2780000000000,
  "52w_high": 199.62,
  "52w_low": 155.98,
  "beta": 1.24,
  "returns": {
    "1m": 3.21,
    "3m": 8.45,
    "ytd": 12.67,
    "1y": 22.34
  },
  "analyst_target": 195.00,
  "recommendation": "buy"
}
```

> [!TIP]
> Fields with `None` values are automatically stripped before serialization to reduce token usage in the LLM context.

---

## LLM Integration

### Multi-Provider Architecture

The advisor supports **6 LLM providers** via LangChain's chat model abstraction. The provider is configured in `src/config/settings` and cached per Streamlit session via `@st.cache_resource`.

```mermaid
graph TB
    CONFIG["src.config.settings<br/>settings.llm.provider"] --> FACTORY["_get_llm()"]
    
    FACTORY -->|"ollama"| OL["ChatOllama<br/>Local / Self-hosted"]
    FACTORY -->|"lmstudio"| LS["ChatOpenAI<br/>Local (OpenAI-compatible)"]
    FACTORY -->|"vllm"| VL["ChatOpenAI<br/>Self-hosted GPU"]
    FACTORY -->|"groq"| GR["ChatGroq<br/>Cloud (Ultra-fast)"]
    FACTORY -->|"anthropic"| AN["ChatAnthropic<br/>Cloud (Claude)"]
    FACTORY -->|"openai"| OA["ChatOpenAI<br/>Cloud (GPT-4)"]

    OL -->|"Tool Calling"| BIND["llm.bind_tools(9 tools)"]
    LS --> BIND
    VL --> BIND
    GR --> BIND
    AN --> BIND
    OA --> BIND

    style CONFIG fill:#431407,color:#fed7aa
    style FACTORY fill:#064e3b,color:#ecfdf5
    style BIND fill:#172554,color:#dbeafe
```

| Provider | LangChain Class | Tool-Calling Support | Notes |
|---|---|---|---|
| **Ollama** | `ChatOllama` | ✅ (model-dependent) | Local, free, requires model download |
| **LM Studio** | `ChatOpenAI` | ✅ (model-dependent) | Local, OpenAI-compatible API |
| **vLLM** | `ChatOpenAI` | ✅ | Self-hosted, GPU-accelerated |
| **Groq** | `ChatGroq` | ⚠️ (partial) | Some models fail tool-calling format |
| **Anthropic** | `ChatAnthropic` | ✅ | Claude models, excellent tool-calling |
| **OpenAI** | `ChatOpenAI` | ✅ | GPT-4/GPT-4o, best tool-calling support |

> [!WARNING]
> If a provider does not support tool-calling (raises `NotImplementedError`, `TypeError`, or `AttributeError`), the advisor automatically falls back to plain chat mode with pre-fetched context injected as a static context string.

**Source**: [_get_llm()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L356-L421)

---

## System Prompt Engineering

The system prompt is structured into **7 sections**, each serving a specific role:

```mermaid
graph TD
    SP["System Prompt<br/>(~1200 tokens base)"] --> G["GUARDRAILS<br/>Scope & Safety Rules"]
    SP --> B["BEHAVIOR RULES<br/>No Tool Narration"]
    SP --> C["CONVERSATIONAL APPROACH<br/>Clarifying Questions Strategy"]
    SP --> T["ANALYSIS TOOLS<br/>9 Tool Descriptions"]
    SP --> S["TOOL USAGE STRATEGY<br/>Combo Recommendations"]
    SP --> R["RESPONSE GUIDELINES<br/>Formatting & Content Rules"]
    
    SP -.->|"Dynamic"| UP["USER PREFERENCES<br/>(if extracted)"]
    SP -.->|"Dynamic"| PF["PRE-FETCHED DATA<br/>(if tickers detected)"]

    style SP fill:#1e1b4b,color:#e0e7ff
    style UP fill:#064e3b,color:#ecfdf5
    style PF fill:#064e3b,color:#ecfdf5
```

### Guardrails

| Category | Rule |
|---|---|
| **Scope** | Stocks, ETFs, bonds, portfolio strategy, dividends, earnings, themes, options flow, insider activity |
| **Refused topics** | Crypto/NFTs, penny stocks/OTC, insider trading, tax/legal advice, non-financial topics |
| **Safety** | No return guarantees, no single-stock concentration, leveraged ETF warnings required, risk always acknowledged |
| **Disclaimer** | Every recommendation must end with the standard disclaimer |
| **Behavior** | Never mention tool names, never narrate internal processes |

### Conversational Strategy

The advisor uses a **two-phase approach**:

1. **Phase 1 — Clarification**: On the first message about a topic, ask 2–3 short clarifying questions
2. **Phase 2 — Recommendation**: After user responds, synthesize data + preferences into a specific, data-backed recommendation

**Exception**: If user preferences are already known (from the profile tracker), skip questions about those already-answered preferences.

**Source**: [_ADVISOR_SYSTEM_PROMPT](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L895-L1006)

---

## Pre-Processing Layer

### Ticker Extraction

Uses a multi-strategy regex approach with a **false-positive filter** of ~100 common English words that also happen to be valid ticker symbols.

```
Input: "I bought QQQM at $180, should I hold or sell? Compare with VOO."
                                    ↓
Strategy 1: $TICKER notation       → (none found)
Strategy 2: Uppercase 2-5 chars    → ["QQQM", "VOO"]
Filter: _COMMON_WORD_TICKERS       → removes false positives
                                    ↓
Output: ["QQQM", "VOO"]
```

> [!NOTE]
> The filter list includes financial terms (BUY, SELL, HOLD, PUT, CALL, ETF, AI, SEC, IPO) and common short words (IT, ALL, FOR, ARE, etc.) to prevent false positives.

**Source**: [_extract_tickers()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L534-L562)

### User Profile Extraction

Tracks 8 preference dimensions across the entire conversation:

```mermaid
graph LR
    subgraph Input ["Chat Messages (user role only)"]
        M1["'I'm looking for safe, conservative investments'"]
        M2["'I bought QQQM at $180'"]
        M3["'My budget is $10,000 for long-term growth'"]
    end

    subgraph Extraction ["Keyword Matching"]
        R["risk_tolerance: conservative<br/>holdings: [QQQM]<br/>purchase_prices: {QQQM: 180}<br/>budget: $10,000<br/>investment_horizon: long-term<br/>goal: growth"]
    end

    subgraph Output ["Injected Context"]
        P["═══ KNOWN USER PREFERENCES ═══<br/>- Risk Tolerance: conservative<br/>- Investment Horizon: long-term<br/>- Budget: $10,000<br/>- Investment Goal: growth<br/>- Current Holdings: QQQM<br/>- Purchase Prices: QQQM: $180.0<br/>═══ END USER PREFERENCES ═══"]
    end

    M1 & M2 & M3 --> R --> P
```

**Source**: [_extract_user_profile()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L586-L656), [_format_user_profile()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L659-L691)

---

## Post-Processing Layer

### Response Validation

```mermaid
graph TD
    R["LLM Response"] --> CHK{Contains recommendation<br/>keywords?}
    CHK -->|No| OUT["Return as-is"]
    CHK -->|Yes| DISC{Has disclaimer<br/>fragment?}
    DISC -->|Yes| OUT
    DISC -->|No| ADD["Append standard<br/>disclaimer"] --> OUT
```

**Recommendation keywords monitored**: `recommend`, `suggest`, `consider`, [buy](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/src/tools/insider_activity.py#242-283), `sell`, [hold](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/src/tools/insider_activity.py#342-375), `allocate`, `invest`, `position`, `portfolio`

**Disclaimer fragments checked**: `not personalized`, `financial advice`, `licensed financial advisor`

**Source**: [_validate_advisor_response()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#L1293-L1319)

---

## Error Handling & Fallback

```mermaid
graph TD
    TRY["llm.bind_tools() + invoke()"] --> ERR1{NotImplementedError<br/>TypeError<br/>AttributeError?}
    ERR1 -->|Yes| FB1["Fallback: ask_financial_question()<br/>Plain chat + pre-fetched context"]
    ERR1 -->|No| ERR2{tool_use_failed<br/>failed_generation<br/>Failed to call?}
    ERR2 -->|Yes| FB2["Fallback: ask_financial_question()<br/>Retry without tools"]
    ERR2 -->|No| ERR3["Return error message<br/>'Unable to answer right now...'"]

    style FB1 fill:#064e3b,color:#ecfdf5
    style FB2 fill:#064e3b,color:#ecfdf5
    style ERR3 fill:#7f1d1d,color:#fecaca
```

| Error Scenario | Handling |
|---|---|
| Provider doesn't support tool-calling | Falls back to [ask_financial_question()](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#437-512) with pre-fetched context |
| Tool-calling format error (Groq) | Detects via error message keywords, retries without tools |
| Tool execution error | Returns `"Tool error: {details}"` as ToolMessage, LLM handles gracefully |
| LLM provider offline | Returns user-friendly error with details |
| Yahoo Finance API failure | Individual tool returns `{"error": "..."}`, LLM notes data unavailability |

> [!IMPORTANT]
> In fallback mode, the advisor still benefits from **pre-fetched ticker data** and **user profile context**, which are injected as static context into the fallback's system prompt. This ensures reasonable quality even without tool-calling.

---

## UI Layer

### Page Structure

```
13_AI_Advisor.py
├── Page Config (title, icon, layout)
├── CSS injection + session init + sidebar
├── Header (gradient title + subtitle)
├── FAQ Templates (8 quick-start questions in 2-column grid)
├── Chat History Display (scrollable message bubbles)
├── Chat Input (text input + FAQ click handler)
└── Analysis Pipeline
    ├── Status Widget (expandable, shows live progress steps)
    ├── ask_advisor() invocation
    └── Response display (markdown)
```

### Progress Display

Each step in the pipeline reports progress via the [on_progress](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/pages/13_AI_Advisor.py#134-138) callback with step-specific icons:

| Step Key | Icon | Example Label |
|---|---|---|
| `profiling` | 👤 | Understanding your preferences... |
| `prefetch` | 📡 | Fetching live data for AAPL, QQQ... |
| `analyzing` | 🧠 | Analyzing your question... |
| [lookup](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1102-1110) | 📊 | Fetching AAPL market data... |
| [technical](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1111-1120) | 📈 | Running technical analysis on AAPL (RSI, MACD, Moving Averages)... |
| [fundamentals](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1121-1130) | 📋 | Running fundamental analysis on AAPL (Valuation, Profitability, Health)... |
| [dividends](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1131-1140) | 💰 | Analyzing AAPL dividend profile (Yield, Safety, Growth History)... |
| [earnings](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1141-1150) | 📑 | Analyzing AAPL quarterly earnings (EPS Surprises, Trends, Quality)... |
| [sentiment](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1151-1160) | 📰 | Analyzing AAPL news sentiment... |
| [peers](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1161-1170) | 🔄 | Comparing AAPL against sector peers... |
| [options](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1171-1181) | ⚡ | Analyzing AAPL options flow (Put/Call, IV, Max Pain)... |
| [insider](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py#1182-1193) | 🔍 | Tracking AAPL insider & institutional activity (Smart Money)... |
| `synthesizing` | ✨ | Synthesizing insights & preparing recommendation... |
| `fallback` | 🔁 | Using conversational mode... / Retrying without tool calling... |

**Source**: [13_AI_Advisor.py progress handlers](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/pages/13_AI_Advisor.py#L117-L137)

---

## Configuration Reference

### LLM Settings (`src/config/settings`)

| Setting | Description |
|---|---|
| `llm.provider` | LLM provider: `ollama`, `lmstudio`, `vllm`, `groq`, `anthropic`, `openai` |
| `llm.model` | Model name for OpenAI/Anthropic |
| `llm.ollama_model` | Ollama model name |
| `llm.ollama_base_url` | Ollama API endpoint |
| `llm.groq_model` | Groq model name |
| `llm.groq_api_key` | Groq API key |
| `llm.openai_api_key` | OpenAI API key |
| `llm.anthropic_api_key` | Anthropic API key |
| `llm.max_tokens` | Max tokens for response |

### Internal Constants

| Constant | Value | Description |
|---|---|---|
| Temperature | `0.7` | Conversational temperature for all providers |
| Max tool-calling rounds | `4` | Prevent infinite tool loops |
| Pre-fetch max tickers | `5` | Cap parallel pre-fetch requests |
| Thread pool workers | `5` | Max concurrent tool executions |
| Chat summarization threshold | `6` messages | Messages beyond this are summarized |
| Message truncation length | `200` chars | Max chars per summarized message |

---

## File Reference

| File | Lines | Purpose |
|---|---|---|
| [13_AI_Advisor.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/pages/13_AI_Advisor.py) | 150 | Streamlit page: chat UI, FAQ templates, progress display |
| [data_service.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/frontend/utils/data_service.py) | 1319 | Data service: LLM factory, all tools, orchestrator, pre/post-processing |
| [technical_indicators.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/src/tools/technical_indicators.py) | — | RSI, MACD, Moving Averages, Bollinger Bands, pattern detection |
| [financial_metrics.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/src/tools/financial_metrics.py) | — | Valuation ratios, profitability ratios, financial health analysis |
| [dividend_analyzer.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/src/tools/dividend_analyzer.py) | — | Dividend yield, safety score, growth history, classification |
| [earnings_data.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/src/tools/earnings_data.py) | — | EPS analysis, beat/miss patterns, earnings quality |
| [news_impact.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/src/tools/news_impact.py) | — | News sentiment aggregation and scoring |
| [peer_comparison.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/src/tools/peer_comparison.py) | — | Peer comparison (async), valuation & performance ranking |
| [options_analyzer.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/src/tools/options_analyzer.py) | 420 | Put/call ratio, IV, max pain, unusual activity, options sentiment |
| [insider_activity.py](file:///Users/gopalsaini/Documents/Source/ai-agents-playgrounds/financial-research-analyst-agent/src/tools/insider_activity.py) | 484 | Form 4 parsing, cluster buying, institutional holdings, smart money score |
