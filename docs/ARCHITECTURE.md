# Architecture Design Document

> **Project**: Financial Research Analyst Agent
> **Last Updated**: 2026-03-22
> **Type**: AI-Powered Hierarchical Multi-Agent System for Financial Analysis

---

## 1. System Overview

The Financial Research Analyst Agent is a hierarchical multi-agent system that provides comprehensive stock analysis by coordinating 11 specialized AI agents, 20+ analysis tools, a RAG knowledge pipeline, and a multi-provider data layer — all accessible through a Streamlit web app, REST API, and CLI.

```text
+=============================================================================+
|                                                                             |
|                    FINANCIAL RESEARCH ANALYST AGENT                         |
|                                                                             |
|   +-------------------------------------------------------------------+     |
|   | PRESENTATION LAYER                                                 |    |
|   | Streamlit Web App  |  FastAPI REST API  |  CLI Tool                |    |
|   +-------------------------------+-----------------------------------+     |
|                                   |                                         |
|   +-------------------------------v-----------------------------------+     |
|   | ORCHESTRATION LAYER                                                |    |
|   | OrchestratorAgent: dispatch, gather, validate confidence, aggregate|    |
|   +-------------------------------+-----------------------------------+     |
|                                   |                                         |
|   +-------------------------------v-----------------------------------+     |
|   | AGENT LAYER (ReAct Reasoning)                                      |    |
|   |                                                                    |    |
|   | Core Analysts        Specialized Analysts       Output             |    |
|   | +---------------+   +---------------+   +------------------+       |    |
|   | | Technical      |   | Thematic      |   | Report Generator |      |    |
|   | | Fundamental    |   | Disruption    |   | (JSON / MD / PDF)|      |    |
|   | | Sentiment      |   | Earnings      |   +------------------+      |    |
|   | | Risk           |   | Dividend      |                             |    |
|   | | Data Collector |   | Options       |                             |    |
|   | +---------------+   +---------------+                              |    |
|   +-------------------------------+-----------------------------------+     |
|                                   |                                         |
|   +-------------------------------v-----------------------------------+     |
|   | INTELLIGENCE LAYER                                                 |    |
|   |                                                                    |    |
|   | RAG Pipeline                    LLM Insight Engine                 |    |
|   | (SEC filings, transcripts)      (cross-dimensional synthesis)      |    |
|   | ChromaDB + Sentence Transformers Rule-based + LLM reasoning        |    |
|   +-------------------------------+-----------------------------------+     |
|                                   |                                         |
|   +-------------------------------v-----------------------------------+     |
|   | TOOLS LAYER (20+)                                                 |    |
|   | Market Data | Indicators | Metrics | News | Peers | Earnings      |    |
|   | Disruption | Dividends | Options | Events | Backtest | Insider    |    |
|   | Document Search (RAG) | Insight Engine | ETF Screener | Perf      |    |
|   +-------------------------------+-----------------------------------+    |
|                                   |                                        |
|   +-------------------------------v-----------------------------------+    |
|   | DATA PROVIDER LAYER                                               |    |
|   |                                                                   |    |
|   | MarketDataProvider (abstract protocol)                            |    |
|   |   +-- YFinanceProvider (default, free)                            |    |
|   |   +-- FMPProvider (250 req/day free tier)                         |    |
|   |   +-- MultiProvider (automatic primary -> fallback chain)         |    |
|   |                                                                   |    |
|   | Data Validator (stale detection, outliers, cross-provider checks) |    |
|   +-------------------------------+-----------------------------------+    |
|                                   |                                        |
|   +-------------------------------v-----------------------------------+    |
|   | STORAGE LAYER                                                     |    |
|   | SQLite / PostgreSQL  |  Redis Cache  |  ChromaDB Vector Store     |    |
|   +-------------------------------+-----------------------------------+    |
|                                   |                                        |
|   +-------------------------------v-----------------------------------+    |
|   | LLM PROVIDER LAYER                                                 |   |
|   | Ollama | LM Studio | vLLM | Groq | Anthropic | OpenAI              |   |
|   | (local, free)                      (cloud, paid/free-tier)         |   |
|   +-------------------------------------------------------------------+    |
|                                                                            |
+=============================================================================+
```

---

## 2. Agent Architecture

### 2.1 Agent Hierarchy

All agents inherit from `BaseAgent` which provides LLM initialization, tool binding, ReAct reasoning, state management, and confidence scoring.

```text
BaseAgent (abstract)
|-- _create_default_llm()      --> Multi-provider LLM factory
|-- _create_agent_graph()      --> LangGraph agent with tool calling
|-- _build_react_prompt()      --> Multi-step reasoning instructions
|-- _extract_confidence()      --> Parse confidence score from output
|-- execute()                  --> Async ReAct execution loop
+-- execute_sync()             --> Sync wrapper (nest_asyncio)

              +------------------------------------+
              |       OrchestratorAgent            |
              |                                    |
              |  Coordinates all specialized agents|
              |  Dispatches via asyncio.gather()   |
              |  Validates cross-agent confidence  |
              |  Aggregates results + gen. report  |
              +-----------------+------------------+
                                |
       +----------+----------+-+--+----------+
       |          |          |    |           |
  +----v----+ +--v------+ +-v-------+ +-----v---+ +----v----+
  |  Data   | | Technic.| | Fundam. | | Sentim. | |  Risk   |
  | Collect.| | Analyst | | Analyst | | Analyst | | Analyst |
  +---------+ +---------+ +---------+ +---------+ +---------+
                               |           |
                          Uses RAG:    Uses RAG:
                          Filing srch  Transcript
                          Filing ctxt  search

  +---------+ +---------+ +---------+ +---------+ +---------+
  | Thematic| | Disrupt.| | Earnings| | Dividend| | Options |
  | Analyst | | Analyst | | Analyst | | Analyst | | Analyst |
  +---------+ +---------+ +---------+ +---------+ +---------+

                    +--------------------+
                    |  Report Generator   |
                    |  JSON / Markdown /  |
                    |  PDF output         |
                    +--------------------+
```

### 2.2 Agent Responsibilities

| Agent                  | Purpose                          | Key Tools                                                       | Output                            |
|------------------------|----------------------------------|-----------------------------------------------------------------|-----------------------------------|
| **DataCollector**      | Fetch stock prices, history      | market_data                                                     | Raw price/company data            |
| **TechnicalAnalyst**   | Chart analysis, momentum         | RSI, MACD, MA, Bollinger, patterns                              | Trend, signals, support/resistance|
| **FundamentalAnalyst** | Financial health, valuation      | Valuation ratios, profitability, peers, **SEC filing search (RAG)** | Buy/Hold/Sell + intrinsic value|
| **SentimentAnalyst**   | News and market mood             | TextBlob NLP, analyst ratings, **transcript search (RAG)**      | Sentiment score and consensus     |
| **RiskAnalyst**        | Portfolio risk assessment        | VaR, Sharpe, Sortino, beta, max drawdown                        | Risk level and metrics            |
| **ThematicAnalyst**    | Investment theme analysis        | Theme mapper (17 themes), ETF scoring                           | Theme rankings and constituents   |
| **DisruptionAnalyst**  | Market disruption profiling      | R&D intensity, revenue accel, margin trajectory                 | Disruptor/At-Risk classification  |
| **EarningsAnalyst**    | Quarterly earnings tracking      | EPS surprises, beat/miss patterns, quality scoring              | Earnings quality and trends       |
| **DividendAnalyst**    | Income investing analysis        | Yield, safety, payout ratio, growth classification              | Dividend King/Aristocrat status   |
| **OptionsAnalyst**     | Options flow sentiment           | Put/call ratio, IV skew, max pain, unusual activity             | Options sentiment score           |
| **ReportGenerator**    | Aggregate and format output      | Template engine                                                 | JSON, Markdown, PDF reports       |

### 2.3 ReAct Reasoning Protocol

Every agent executes tasks using a structured multi-step reasoning approach injected via `_build_react_prompt()`:

```text
  TASK RECEIVED
       |
       v
  +------------------------------------------+
  |  STEP 1 -- PLAN                          |
  |  Think about what data is needed         |
  |  Identify which tools to call            |
  |  Consider what increases/decreases       |
  |  confidence in the conclusion            |
  +----+-------------------------------------+
       |
       v
  +------------------------------------------+
  |  STEP 2 -- GATHER                        |
  |  Call tools to collect data/evidence     |
  |  Each tool call = 1 reasoning step       |
  +----+-------------------------------------+
       |
       v
  +------------------------------------------+
  |  STEP 3 -- ANALYZE                       |
  |  Examine results for:                    |
  |  - Confirming signals across sources     |
  |  - Contradictions needing investigation  |
  |  - Missing data that limits confidence   |
  |  - Non-obvious patterns or anomalies     |
  +----+-------------------------------------+
       |
       v
  +------------------------------------------+
  |  STEP 4 -- REFLECT                       |
  |  If findings are contradictory:          |
  |  - Call additional tools to investigate  |
  |  - Look from a different angle           |
  |  - Consider alternative explanations     |
  +----+-------------------------------------+
       |
       v
  +------------------------------------------+
  |  STEP 5 -- CONCLUDE                      |
  |  Provide final analysis with:            |
  |  - Conclusions backed by evidence        |
  |  - Confidence: 0.XX (0.0-1.0)            |
  |  - Key risks and caveats                 |
  |  - What to watch going forward           |
  +------------------------------------------+

  Output --> AgentResult:
  |-- success: bool
  |-- data: {output, raw_result}
  |-- confidence: 0.82        <-- extracted from text
  |-- reasoning_steps: 4      <-- tool call count
  +-- execution_time: 3.2s
```

### 2.4 Orchestration & Confidence Validation

The `OrchestratorAgent` runs all analysis agents in parallel and validates their confidence:

```text
  OrchestratorAgent.analyze("AAPL")
       |
       v
  +--------------------------------------------------+
  |  1. Data Collection                               |
  |     data_result = await data_collector.collect()  |
  +----+----------------------------------------------+
       |
       v
  +--------------------------------------------------+
  |  2. Parallel Analysis (asyncio.gather)            |
  |     |-- technical_analyst.analyze_stock()         |
  |     |-- fundamental_analyst.analyze_company()     |
  |     |-- sentiment_analyst.analyze_sentiment()     |
  |     +-- risk_analyst.analyze_risk()               |
  +----+----------------------------------------------+
       |
       v
  +--------------------------------------------------+
  |  3. Confidence Validation                         |
  |                                                   |
  |  confidence_scores = {                            |
  |    "technical": 0.82,                             |
  |    "fundamental": 0.75,                           |
  |    "sentiment": 0.38,   <-- LOW: flagged          |
  |    "risk": 0.90                                   |
  |  }                                                |
  |  overall_confidence = 0.71                        |
  |  confidence_warnings = {"sentiment": 0.38}        |
  +----+----------------------------------------------+
       |
       v
  +--------------------------------------------------+
  |  4. Report Generation                            |
  |     report_generator.generate_report()           |
  +--------------------------------------------------+
```

---

## 3. Intelligence Layer

### 3.1 RAG Pipeline

The Retrieval-Augmented Generation pipeline ingests, embeds, and retrieves financial documents so agents can reason over SEC filings and earnings transcripts.

```text
  +=====================================================================+
  |                        INGESTION                                     |
  |                                                                      |
  |  SEC EDGAR (free, no API key)          Manual Ingest                 |
  |  +--------------------------+          +------------------+          |
  |  | 1. Ticker --> CIK        |          | Earnings call    |          |
  |  |    (company_tickers.json)|          | transcripts      |          |
  |  |                          |          |                  |          |
  |  | 2. CIK --> Filing list   |          | ingest_text()    |          |
  |  |    (submissions API)     |          |                  |          |
  |  |                          |          +--------+---------+          |
  |  | 3. Download filing HTML  |                   |                    |
  |  |                          |                   |                    |
  |  | 4. Strip HTML --> text   |                   |                    |
  |  |    (max 200K chars)      |                   |                    |
  |  +------------+-------------+                   |                    |
  |               |                                 |                    |
  |               v                                 v                    |
  |  +-----------------------------------------------------------+       |
  |  |  Text Chunker                                              |      |
  |  |  - 512 tokens per chunk (~2048 chars)                      |      |
  |  |  - 64 token overlap for continuity                         |      |
  |  |  - Sentence-aware boundary breaking                        |      |
  |  +--------------------------+--------------------------------+       |
  |                             |                                        |
  |                             v                                        |
  |  +-----------------------------------------------------------+       |
  |  |  Embedder                                                  |      |
  |  |  - Sentence Transformers (all-MiniLM-L6-v2) -- default     |      |
  |  |  - OpenAI embeddings -- optional                           |      |
  |  |  - Batched upsert (500 per batch)                          |      |
  |  +--------------------------+--------------------------------+       |
  |                             |                                        |
  |                             v                                        |
  |  +-----------------------------------------------------------+       |
  |  |  ChromaDB (Persistent)                                     |      |
  |  |  Collection: "financial_documents"                         |      |
  |  |                                                            |      |
  |  |  Metadata per chunk:                                       |      |
  |  |  symbol | filing_type | filed_date | doc_type | chunk_idx  |      |
  |  |  source ("sec_edgar" | "manual") | total_chunks            |      |
  |  +-----------------------------------------------------------+       |
  +=====================================================================+

  +=====================================================================+
  |                        RETRIEVAL                                     |
  |                                                                      |
  |  RAGRetriever                                                        |
  |  |-- search(query, symbol, filing_type, top_k)                       |
  |  |   Similarity search + metadata filter --> relevance scored results|
  |  |                                                                   |
  |  |-- search_filings(query, symbol, "10-K")                           |
  |  |   Targeted SEC filing search                                      |
  |  |                                                                   |
  |  |-- search_transcripts(query, symbol)                               |
  |  |   Earnings call transcript search                                 |
  |  |                                                                   |
  |  +-- get_context_for_llm(query, symbol, max_chars=8000)              |
  |      Formatted context block with source citations:                  |
  |      "[Source 1: AAPL 10-K (filed 2024-01-15) | Relevance: 87%]"     |
  |                                                                      |
  |  Agent Tool Bindings:                                                |
  |  - search_sec_filings          --> FundamentalAnalyst                |
  |  - get_filing_context          --> FundamentalAnalyst                |
  |  - search_earnings_transcripts --> SentimentAnalyst                  |
  +=====================================================================+
```

### 3.2 LLM Insight Engine

A hybrid rule-based + LLM synthesis layer that generates cross-dimensional observations, detects contradictions, and provides actionable watch items.

```text
  +--------------------------------------------------------------+
  |                  ALL ANALYSIS RESULTS                          |
  |                                                                |
  | technical  fundamental  earnings  performance  peers  sentiment|
  +-----------------------------+--------------------------------+
                                |
            +-------------------v---------------------+
            |     RULE-BASED DETECTORS                |
            |                                         |
            |  _detect_technical_signals()     RSI oversold, MACD cross
            |  _detect_valuation_signals()     P/E vs peer median
            |  _detect_earnings_signals()      Beat/miss patterns
            |  _detect_performance_signals()   Drawdown, alpha
            |  _detect_anomalies()             Contradicting signals
            |  _detect_confluences()           3+ aligned signals
            +-------------------+---------------------+
                                |
                   Structured signals as input
                                |
            +-------------------v---------------------+
            |     LLM SYNTHESIS                       |
            |                                         |
            |  All analysis data + rule signals       |
            |         |                               |
            |         v                               |
            |  LLM reasons across dimensions          |
            |         |                               |
            |         v                               |
            |  Structured JSON output:                |
            |  |-- key_insights[]                     |
            |  |   (category, severity, title,        |
            |  |    observation, evidence,            |
            |  |    confidence, direction,            |
            |  |    time_horizon)                     |
            |  |-- contradictions[]                   |
            |  |   (description, assessment,          |
            |  |    risk_level, resolution)           |
            |  |-- overall_assessment                 |
            |  |   (bias, conviction, reasoning,      |
            |  |    key_risk, key_catalyst)           |
            |  +-- watch_items[]                      |
            |      (trigger, action, timeframe)       |
            |                                         |
            |  FALLBACK: If LLM unavailable,          |
            |  returns rule-based observations        |
            |  automatically (graceful degradation)   |
            +-----------------------------------------+
```

---

## 4. Data Provider Layer

### 4.1 Provider Architecture

All tools access market data through an abstract `MarketDataProvider` protocol, enabling provider-swapping with zero tool changes.

```text
  MarketDataProvider (abstract protocol)
  |
  |  8 categories, 18 methods:
  |  |-- Info & Quote:    get_info(), get_quote()
  |  |-- Historical:      get_history()
  |  |-- Financials:      get_income_statement(), get_balance_sheet(),
  |  |                    get_cash_flow(), get_quarterly_income_statement()
  |  |-- Earnings:        get_earnings_history(), get_calendar()
  |  |-- Dividends:       get_dividends()
  |  |-- Options:         get_options_expirations(), get_options_chain()
  |  |-- Holders:         get_insider_transactions(), get_institutional_holders(),
  |  |                    get_major_holders()
  |  +-- News:            get_news()
  |
  |-- YFinanceProvider        (default, free, no API key)
  |-- FMPProvider             (free tier: 250 req/day)
  +-- [TwelveDataProvider]    (future)
```

### 4.2 Fallback Chain

The `MultiProvider` wraps a primary + fallback provider so every call automatically retries on the secondary when the primary fails or returns empty data.

```text
  get_provider() factory
  |
  |  Reads env vars:
  |  DATA_PROVIDER=yfinance           (primary)
  |  DATA_FALLBACK_PROVIDER=fmp       (secondary, optional)
  |
  +---> MultiProvider(YFinanceProvider, FMPProvider)

  Call flow:

  +---------------+     +-----------------+     +------------+
  |  Tool calls   |---->|  PRIMARY        |---->|  Result    |
  |  get_info()   |     |  YFinanceProvider|     |  returned |
  |  get_history()|     |                 |     +------------+
  +---------------+     +--------+--------+
                                 |
                            Empty or error?
                                 |
                                 v
                        +--------+--------+     +------------+
                        |  FALLBACK       |---->|  Result    |
                        |  FMPProvider    |     |  returned  |
                        +--------+--------+     +------------+
                                 |
                            Also failed?
                                 |
                                 v
                        +-----------------+
                        |  Return empty   |
                        |  (graceful)     |
                        +-----------------+
```

### 4.3 Data Quality Validation

```text
  validate_info(info_dict)
  |-- Empty dict check
  |-- Price data present (currentPrice / regularMarketPrice)
  |-- Market cap sanity (non-negative)
  +-- P/E ratio sanity (0 < PE < 10000)

  validate_history(dataframe, expected_period)
  |-- Empty DataFrame check
  |-- Required OHLCV columns present
  |-- NaN row percentage (> 10% flagged)
  |-- Stale data (last date > 7 days old)
  |-- Price outliers (> 50% daily change)
  +-- Expected row count for period

  cross_validate_price(price_a, price_b, tolerance=2%)
  +-- Flags divergence between two provider prices
```

---

## 5. Tools Layer

### 5.1 Tool Registry

| Tool Module                | Functions                                                          | Data Source       | Used By                            |
|----------------------------|--------------------------------------------------------------------|-------------------|------------------------------------|
| **market_data.py**         | get_stock_price, get_historical_data, get_company_info             | Data Provider     | DataCollector, all pages           |
| **technical_indicators.py**| calculate_rsi, calculate_macd, calculate_moving_averages, BB       | NumPy (calc)      | TechnicalAnalyst                   |
| **financial_metrics.py**   | valuation_ratios, profitability, liquidity, growth, health         | Data Provider     | FundamentalAnalyst                 |
| **news_fetcher.py**        | fetch_news (multi-source with fallback)                            | YFinance, NewsAPI | SentimentAnalyst                   |
| **peer_comparison.py**     | compare_peers (async, 100-stock universe)                          | Data Provider     | FundamentalAnalyst                 |
| **document_search.py**     | search_sec_filings, search_transcripts, get_filing_context         | ChromaDB (RAG)    | FundamentalAnalyst, SentimentAnalyst|
| **insight_engine.py**      | generate_observations (rule-based detectors)                       | All analyses      | LLM Insight Engine                 |
| **llm_insight_engine.py**  | generate_smart_observations (LLM synthesis)                        | All analyses + LLM| OrchestratorAgent                  |
| **theme_mapper.py**        | load_themes, map_stock_to_themes, theme_performance                | YAML config       | ThematicAnalyst                    |
| **earnings_data.py**       | get_quarterly_earnings, eps_surprises, earnings_quality            | Data Provider     | EarningsAnalyst                    |
| **disruption_metrics.py**  | r&d_intensity, revenue_acceleration, margin_trajectory             | Data Provider     | DisruptionAnalyst                  |
| **dividend_analyzer.py**   | dividend_yield, safety_score, growth_classification                | Data Provider     | DividendAnalyst                    |
| **options_analyzer.py**    | put_call_ratio, iv_skew, max_pain, unusual_activity                | Data Provider     | OptionsAnalyst                     |
| **performance_tracker.py** | track_performance, returns, sharpe, sortino, drawdown              | Data Provider     | Performance page                   |
| **event_analyzer.py**      | analyze_events (earnings, dividends, splits windows)               | Data Provider     | OrchestratorAgent                  |
| **backtesting_engine.py**  | run_backtest (RSI reversal, MACD crossover, SMA)                   | Historical data   | OrchestratorAgent                  |
| **insider_activity.py**    | analyze_smart_money, cluster_buying, institutional_flows           | Data Provider     | OrchestratorAgent                  |
| **etf_screener.py**        | rank_etfs, thematic_scoring                                        | Theme mapper      | ETF Screener page                  |

### 5.2 Tool Binding Pattern

Tools use LangChain's `@tool` decorator and are bound to agents at initialization:

```python
# Tool definition (src/tools/document_search.py)
@tool("search_sec_filings")
def search_filings(symbol: str, filing_type: str, query: str) -> Dict:
    """Search SEC filings using semantic search."""
    ...

# Agent binding (src/agents/fundamental.py)
class FundamentalAnalystAgent(BaseAgent):
    def _get_default_tools(self):
        return [
            calculate_valuation_ratios_tool,
            analyze_financial_health_tool,
            search_filings,         # RAG tool
            get_filing_context,     # RAG tool
        ]
```

---

## 6. Presentation Layer

### 6.1 Streamlit Web App

```text
  frontend/
  |-- app.py                       Landing page (AI Advisor chat interface)
  |-- pages/
  |   |-- 1_Dashboard.py           Market overview + watchlist
  |   |-- 2_Stock_Analysis.py      Comprehensive single-stock analysis
  |   |-- 3_Thematic_Investing.py  17 investment themes browser
  |   |-- 4_Peer_Comparison.py     Side-by-side company comparison
  |   |-- 5_Market_Disruption.py   Disruption scoring
  |   |-- 6_Quarterly_Earnings.py  EPS tracking + quality
  |   |-- 7_Portfolio_Analysis.py  Multi-stock correlation + analysis
  |   |-- 8_Reports.py            Report generation
  |   |-- 9_News.py               Financial news aggregation
  |   |-- 10_Performance.py       Portfolio performance tracking
  |   |-- 11_Sentiment.py         Market sentiment analysis
  |   +-- 12_ETF_Screener.py      AI-driven ETF ranking
  |
  |-- components/
  |   |-- header.py                Grouped dropdown navigation
  |   |-- sidebar.py               Symbol search + watchlist
  |   |-- charts.py                TradingView candlestick/area charts
  |   |-- plotly_charts.py         Gauge, radar, heatmap, bar charts
  |   |-- metrics_cards.py         KPI cards, news cards, score badges
  |   +-- data_tables.py           Styled DataFrames
  |
  |-- utils/
  |   |-- data_service.py          Direct Python tool imports (no API calls)
  |   |-- theme.py                 CSS injection, color system
  |   |-- formatters.py            Currency, percentage, date formatting
  |   +-- session.py               Session state management
  |
  +-- assets/
      +-- style.css                Bloomberg-inspired dark theme
```

**Key design choice**: The frontend imports analysis tools directly via Python — no HTTP API calls needed. Data flows within the same process for maximum performance.

```text
  Page ---> data_service.py ---> src/tools/*.py ---> Data Provider
                                  (same process, no network hop)
```

**Chart libraries**:

- TradingView Lightweight Charts (CDN v4.1.1) for financial charts
- Plotly for gauges, radar charts, heatmaps, bar charts

**Caching**: `@st.cache_data` with TTLs (60s prices, 300s historical, 1800s analysis)

### 6.2 FastAPI REST API

```text
  /api/v1/
  |-- POST   /analyze              Comprehensive stock analysis
  |-- GET    /technical/{symbol}   Technical analysis only
  |-- GET    /fundamental/{symbol} Fundamental analysis only
  |-- GET    /sentiment/{symbol}   Sentiment analysis only
  |-- POST   /portfolio            Multi-stock portfolio analysis
  |-- POST   /reports              Generate research reports
  |-- GET    /themes               List available investment themes
  |-- POST   /themes/analyze       Analyze a specific theme
  |-- GET    /peers/{symbol}       Peer comparison
  |-- GET    /disruption/{symbol}  Disruption analysis
  |-- GET    /earnings/{symbol}    Earnings analysis
  |-- GET    /dividends/{symbol}   Dividend analysis
  |-- GET    /performance/{symbol} Performance tracking
  |-- GET    /events/{symbol}      Event-driven analysis
  |-- POST   /backtest             Strategy backtesting
  |-- GET    /observations/{symbol} LLM-powered insights
  |-- GET    /smart-money/{symbol} Insider activity analysis
  |-- GET    /options/{symbol}     Options flow analysis
  +-- GET    /health               System health check
```

### 6.3 CLI

```bash
python -m src.cli analyze AAPL              # Single stock analysis
python -m src.cli portfolio AAPL GOOGL MSFT # Multi-stock portfolio
python -m src.cli dashboard --port 8080     # Start web dashboard
python -m src.main api                      # Start REST API server
python -m src.main demo                     # Run demo analysis
```

---

## 7. LLM Provider Layer

All agents use `BaseAgent._create_default_llm()` which reads `LLM_PROVIDER` from config and creates the appropriate LangChain chat model:

```text
  settings.llm.provider
       |
       |-- "ollama"     --> ChatOllama(model, base_url)        Local, FREE
       |-- "lmstudio"   --> ChatOpenAI(model, base_url)        Local, FREE
       |-- "vllm"       --> ChatOpenAI(model, base_url)        Local, FREE
       |-- "groq"       --> ChatGroq(model, api_key)           Cloud, Free tier
       |-- "anthropic"  --> ChatAnthropic(model, api_key)      Cloud, Paid
       +-- "openai"     --> ChatOpenAI(model, api_key)         Cloud, Paid
```

**Default**: Ollama with Llama 4 — fully local, zero API keys required.

---

## 8. Storage Layer

| Store                    | Purpose                                        | Default                  | Production         |
|--------------------------|------------------------------------------------|--------------------------|--------------------|
| **SQLite / PostgreSQL**  | Analysis persistence, portfolios, watchlists   | SQLite (file)            | PostgreSQL (Docker)|
| **Redis**                | Response caching (TTL: 3600s default)          | localhost:6379           | Docker service     |
| **ChromaDB**             | RAG vector store (SEC filings, transcripts)    | `./data/chroma` (persist)| Docker service     |
| **Sentence Transformers**| Document embeddings for ChromaDB               | `all-MiniLM-L6-v2`      | Same               |

---

## 9. Configuration Architecture

```text
  Environment Variables (.env)
  |
  +---> Pydantic BaseSettings (src/config.py)
        |
        |-- LLMSettings
        |   provider, ollama_model, ollama_base_url, groq_api_key,
        |   openai_api_key, anthropic_api_key, temperature, max_tokens
        |
        |-- DataAPISettings
        |   fmp_api_key, fred_api_key, alpha_vantage_api_key,
        |   finnhub_api_key, news_api_key
        |
        |-- DatabaseSettings
        |   database_url, redis_url, cache_ttl_seconds
        |
        |-- VectorStoreSettings
        |   provider (chroma), chroma_persist_dir,
        |   embedding_provider (sentence-transformers),
        |   sentence_transformer_model
        |
        |-- AgentSettings
        |   max_iterations, timeout_seconds, enable_memory
        |
        +-- APISettings
            host, port, reload, cors_origins

  Agent Parameters (config/agents.yaml)
  |-- Technical indicators (RSI period, MACD, MA periods)
  |-- Recommendation thresholds (Strong Buy >= 0.80, Buy >= 0.65, ...)
  |-- Analysis weights (Technical 25%, Fundamental 35%, Sentiment 20%, Risk 20%)
  +-- Confidence weights per analysis type

  Investment Themes (config/themes.yaml)
  +-- 17 themes with constituents, ETFs, sector tags, risk levels
```

---

## 10. File Structure

```text
  financial-research-analyst-agent/
  |-- src/
  |   |-- agents/                     # 11 specialized AI agents
  |   |   |-- base.py                 #   BaseAgent (ReAct, confidence, multi-LLM)
  |   |   |-- orchestrator.py         #   Coordinator + confidence validation
  |   |   |-- data_collector.py       #   Market data fetching
  |   |   |-- technical.py            #   Technical analysis (RSI, MACD, MA)
  |   |   |-- fundamental.py          #   Fundamental analysis + RAG filing search
  |   |   |-- sentiment.py            #   Sentiment analysis + RAG transcripts
  |   |   |-- risk.py                 #   Risk assessment (VaR, Sharpe, Beta)
  |   |   |-- thematic.py             #   Thematic investing (17 themes)
  |   |   |-- disruption.py           #   Market disruption scoring
  |   |   |-- earnings.py             #   Quarterly earnings tracking
  |   |   |-- dividend.py             #   Dividend analysis
  |   |   |-- options.py              #   Options flow analysis
  |   |   +-- report_generator.py     #   Report output (JSON/MD/PDF)
  |   |
  |   |-- tools/                      # 20+ analysis tools
  |   |   |-- market_data.py          #   Price, history, company info
  |   |   |-- technical_indicators.py #   RSI, MACD, MA, Bollinger Bands
  |   |   |-- financial_metrics.py    #   Valuation, profitability, liquidity
  |   |   |-- news_fetcher.py         #   Multi-source news with fallback
  |   |   |-- peer_comparison.py      #   Async peer discovery (100-stock universe)
  |   |   |-- document_search.py      #   RAG tools (filing + transcript search)
  |   |   |-- insight_engine.py       #   Rule-based observation detectors
  |   |   |-- llm_insight_engine.py   #   LLM-powered cross-dimensional synthesis
  |   |   |-- theme_mapper.py         #   Theme definitions, scoring, ETF mapping
  |   |   |-- earnings_data.py        #   EPS surprises, quality scoring
  |   |   |-- disruption_metrics.py   #   R&D intensity, revenue acceleration
  |   |   |-- dividend_analyzer.py    #   Yield, safety, growth classification
  |   |   |-- options_analyzer.py     #   Put/call, IV skew, max pain
  |   |   |-- performance_tracker.py  #   Returns, Sharpe, Sortino, drawdown
  |   |   |-- event_analyzer.py       #   Corporate events (earnings, splits)
  |   |   |-- backtesting_engine.py   #   Strategy simulation (RSI, MACD, SMA)
  |   |   |-- insider_activity.py     #   Form 4 parsing, smart money scoring
  |   |   +-- etf_screener.py         #   ETF ranking, thematic scoring
  |   |
  |   |-- rag/                        # RAG knowledge pipeline
  |   |   |-- ingester.py             #   SEC EDGAR fetcher + text chunker
  |   |   |-- embedder.py             #   ChromaDB + Sentence Transformers
  |   |   +-- retriever.py            #   Semantic search + context formatting
  |   |
  |   |-- data/                       # Data provider abstraction
  |   |   |-- provider.py             #   Abstract protocol + YFinance + MultiProvider
  |   |   |-- fmp_provider.py         #   Financial Modeling Prep provider
  |   |   +-- validator.py            #   Data quality validation
  |   |
  |   |-- api/
  |   |   |-- routes.py               #   30+ FastAPI endpoints
  |   |   +-- schemas.py              #   Pydantic request/response models
  |   |
  |   |-- config.py                   #   Pydantic settings (6 sub-settings)
  |   |-- main.py                     #   Entry point (API / CLI / Demo)
  |   +-- cli.py                      #   CLI interface
  |
  |-- frontend/                       # Streamlit web app
  |   |-- app.py                      #   Landing page (AI Advisor chat)
  |   |-- pages/ (12 pages)           #   Analysis, research, portfolio, data
  |   |-- components/                 #   Header, charts, cards, tables
  |   |-- utils/                      #   Data service, theme, formatters
  |   +-- assets/                     #   Bloomberg dark theme CSS
  |
  |-- tests/ (16 files, 5400+ lines)  # Comprehensive test suite
  |-- config/                         # agents.yaml, themes.yaml
  |-- docs/                           # Architecture, gap analysis, plans
  |-- requirements.txt                # 92 Python dependencies
  |-- docker-compose.yml              # PostgreSQL, Redis, ChromaDB
  |-- Dockerfile                      # Container image
  +-- .env.example                    # Environment template
```

---

## 11. Key Design Decisions

| Decision               | Choice                                     | Rationale                                                            |
|------------------------|---------------------------------------------|----------------------------------------------------------------------|
| Agent framework        | LangChain + LangGraph                      | Provider-agnostic tool calling, async support, mature ecosystem      |
| Data abstraction       | Protocol-based providers                   | Swap data sources without touching any tool code                     |
| Fallback strategy      | MultiProvider wrapper                      | Automatic retry on secondary provider, transparent to callers        |
| RAG storage            | ChromaDB (persistent)                      | Open source, local, no API key, supports metadata filtering          |
| Embeddings             | Sentence Transformers                      | Free, local, good quality for financial text (384-dim)               |
| Insight engine         | Hybrid (rules + LLM)                       | Rules provide reliable structure; LLM adds depth; graceful fallback  |
| Reasoning              | ReAct protocol via prompt injection        | Works with any LLM provider, no framework lock-in                    |
| Confidence scoring     | Regex extraction from output text          | Any LLM can produce it; no custom model needed                       |
| Frontend data access   | Direct Python imports                      | No API calls needed, same process, zero latency                      |
| Configuration          | Pydantic BaseSettings + YAML               | Typed validation, env var overrides, agent-specific tuning           |
| Default stack          | Ollama + ChromaDB + Sentence Transformers  | Full functionality with zero API keys or costs                       |
| Async execution        | asyncio.gather() for parallel agents       | 4-5x faster than sequential; all agents run simultaneously           |
