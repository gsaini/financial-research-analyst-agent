# Implementation Plan: Smart AI Financial Analyzer

> **Date**: 2026-03-22
> **Reference**: [GAP_ANALYSIS.md](GAP_ANALYSIS.md)
> **Approach**: Priority-based phases, each delivering incremental "smartness"
> **Deferred**: Third-party streaming integrations (Polygon.io, Alpaca, IEX Cloud)

---

## Phase 1: Core AI Intelligence (P0)

**Goal**: Make the system actually "think" — RAG, agentic reasoning, multi-provider data reliability

### 1.1 RAG Pipeline for Financial Documents

**What**: Ingest, embed, and retrieve SEC filings & earnings transcripts so agents can reason over real documents.

**Tasks**:

- [x] Build document ingestion pipeline (`src/rag/ingester.py`)
  - SEC EDGAR API integration for 10-K, 10-Q, 8-K filings
  - Earnings call transcript fetching (SEC EDGAR XBRL or free APIs)
  - Chunking strategy: semantic chunking with overlap (512 tokens, 50 overlap)
- [x] Build embedding pipeline (`src/rag/embedder.py`)
  - Use existing Sentence Transformers config
  - Store embeddings in ChromaDB (already configured)
  - Metadata tagging: ticker, filing type, date, section
- [x] Build retrieval pipeline (`src/rag/retriever.py`)
  - Similarity search with metadata filtering
  - Re-ranking with cross-encoder
  - Context window management (fit relevant chunks into LLM context)
- [x] Create RAG-aware agent mixin (`src/agents/rag_mixin.py`)
  - Agents can query document store as part of analysis
  - FundamentalAnalyst uses 10-K/10-Q data
  - SentimentAnalyst uses earnings transcript tone
- [x] Add RAG tools (`src/tools/document_search.py`)
  - `search_filings(symbol, filing_type, query)` — semantic search over SEC filings
  - `search_transcripts(symbol, quarter, query)` — search earnings call transcripts
  - `get_filing_summary(symbol, filing_type)` — LLM-generated filing summary

**New Dependencies**: `sec-edgar-downloader`, `unstructured`, `sentence-transformers` (existing)

**Files to Create**:

- `src/rag/__init__.py`
- `src/rag/ingester.py`
- `src/rag/embedder.py`
- `src/rag/retriever.py`
- `src/agents/rag_mixin.py`
- `src/tools/document_search.py`

**Files to Modify**:

- `src/agents/fundamental.py` — integrate RAG for filing analysis
- `src/agents/sentiment.py` — integrate RAG for transcript tone analysis
- `src/agents/orchestrator.py` — add document retrieval step
- `src/config.py` — add RAG settings
- `config/agents.yaml` — add RAG parameters

---

### 1.2 Multi-Step Agentic Reasoning (ReAct/CoT)

**What**: Agents should investigate, hypothesize, and follow-up — not just call one tool and return.

**Tasks**:

- [x] Upgrade BaseAgent to support ReAct pattern (`src/agents/base.py`)
  - Thought → Action → Observation → Thought loop
  - Max reasoning steps configurable (default: 5)
  - Early termination when confidence threshold met
- [x] Implement investigation chains in OrchestratorAgent
  - If technical signals conflict with fundamentals → investigate further
  - If sentiment is negative but price is rising → check institutional flows
  - Cross-agent validation: agents can query each other's findings
- [x] Add reasoning prompts per agent
  - Each agent gets a system prompt template encouraging multi-step analysis
  - Include few-shot examples of good financial reasoning
- [x] Implement confidence scoring
  - Each analysis step produces a confidence score
  - Low confidence triggers deeper investigation
  - Final recommendation weighted by confidence

**Files to Modify**:

- `src/agents/base.py` — ReAct loop, confidence scoring
- `src/agents/orchestrator.py` — cross-agent investigation logic
- `src/agents/technical.py` — multi-step technical reasoning prompts
- `src/agents/fundamental.py` — multi-step fundamental reasoning prompts
- `src/agents/sentiment.py` — multi-step sentiment reasoning prompts
- `src/agents/risk.py` — multi-step risk reasoning prompts
- `config/agents.yaml` — reasoning parameters

---

### 1.3 Second Data Provider (Financial Modeling Prep)

**What**: Implement FMP provider to eliminate single-source dependency and enable data cross-validation.

**Tasks**:

- [x] Implement `FMPProvider` (`src/data/fmp_provider.py`)
  - Implements existing `MarketDataProvider` protocol
  - Covers: quotes, historical, financials, earnings, news
  - Free tier: 250 requests/day (sufficient for dev)
- [x] Implement provider fallback chain (`src/data/provider.py`)
  - Primary → Secondary fallback logic
  - Data validation: cross-check between providers
  - Rate limit awareness per provider
- [x] Add Alpha Vantage as tertiary provider (`src/data/alphavantage_provider.py`)
  - Already in requirements.txt (`alpha-vantage`)
  - Covers: time series, fundamentals, economic indicators
- [x] Data quality validation layer (`src/data/validator.py`)
  - Check for stale data (last update > threshold)
  - Check for missing required fields
  - Outlier detection on price data
  - Log data quality metrics

**Files to Create**:

- `src/data/fmp_provider.py`
- `src/data/alphavantage_provider.py`
- `src/data/validator.py`

**Files to Modify**:

- `src/data/provider.py` — fallback chain logic
- `src/config.py` — FMP/AV API key settings
- `.env.example` — add FMP_API_KEY, document free tier

---

### 1.4 LLM-Powered Insight Engine

**What**: Replace rule-based insight engine with LLM-driven cross-dimensional synthesis.

**Tasks**:

- [x] Refactor `src/tools/insight_engine.py`
  - Feed all analysis results as structured context to LLM
  - LLM generates observations with reasoning chains
  - Categorize insights: opportunity, risk, anomaly, trend
  - Prioritize by actionability and confidence
- [x] Add contradiction detection
  - Identify conflicting signals across analyses
  - Generate "what to watch" alerts
- [x] Add historical context
  - Compare current metrics to historical ranges
  - "P/E is at 5-year high" type insights

**Files to Modify**:

- `src/tools/insight_engine.py` — full refactor to LLM-powered
- `src/agents/orchestrator.py` — feed insight engine with all agent results

---

## Phase 2: Alternative Data & Predictive Models (P1)

**Goal**: Add data sources and models that generate actual predictions and signals

### 2.1 Macroeconomic Data (FRED API)

**Tasks**:

- [x] Create FRED data tool (`src/tools/macro_data.py`)
  - Federal funds rate, CPI, GDP, unemployment, yield curve
  - Treasury yields (2Y, 10Y, 30Y) and spread
  - Consumer confidence, PMI, housing starts
- [x] Add macro context to analysis
  - Rate environment affects sector recommendations
  - Yield curve inversion signals
  - Inflation impact on valuation multiples
- [x] Create macro dashboard frontend page

**New Dependencies**: `fredapi`
**Files to Create**: `src/tools/macro_data.py`, `frontend/pages/13_Macro_Economy.py`
**Files to Modify**: `src/agents/fundamental.py`, `src/agents/risk.py`

---

### 2.2 Social Media Sentiment

**Tasks**:

- [x] Reddit sentiment tool (`src/tools/social_sentiment.py`)
  - r/wallstreetbets, r/stocks, r/investing monitoring
  - Post/comment volume and sentiment scoring
  - Trending ticker detection
- [x] Aggregate social + news sentiment
  - Weighted composite sentiment score
  - Sentiment momentum (trending up/down)
- [x] Add social sentiment to frontend Sentiment page

**New Dependencies**: `praw` (Reddit API)
**Files to Create**: `src/tools/social_sentiment.py`
**Files to Modify**: `src/agents/sentiment.py`, `frontend/pages/11_Sentiment.py`

---

### 2.3 DCF Valuation Model

**Tasks**:

- [x] Implement DCF calculator (`src/tools/dcf_model.py`)
  - Free cash flow projection (3 scenarios: bull/base/bear)
  - WACC calculation (CAPM-based)
  - Terminal value (perpetuity growth + exit multiple)
  - Sensitivity analysis (discount rate vs growth rate matrix)
- [x] Integrate with FundamentalAnalyst
  - Auto-populate inputs from financial statements
  - LLM-assisted growth rate estimation
- [x] Add DCF visualization to Stock Analysis page

**Files to Create**: `src/tools/dcf_model.py`
**Files to Modify**: `src/agents/fundamental.py`, `frontend/pages/2_Stock_Analysis.py`

---

### 2.4 ML-Based Forecasting

**Tasks**:

- [x] Time-series forecasting tool (`src/tools/ml_forecast.py`)
  - GradientBoosting with engineered features (lag returns, MAs, RSI, volatility)
  - Feature engineering: technical indicators as features
  - Confidence intervals on predictions
  - 30/60/90-day price targets
- [x] Anomaly detection (`src/tools/anomaly_detector.py`)
  - Volume anomaly detection (Z-score based)
  - Price movement anomaly detection
  - Pattern break detection
- [x] Add forecast visualization to frontend

**New Dependencies**: `prophet`, `scikit-learn`
**Files to Create**: `src/tools/ml_forecast.py`, `src/tools/anomaly_detector.py`
**Files to Modify**: `src/agents/technical.py`, `frontend/pages/2_Stock_Analysis.py`

---

### 2.5 Portfolio Optimization

**Tasks**:

- [x] Portfolio optimizer tool (`src/tools/portfolio_optimizer.py`)
  - Mean-variance optimization (Markowitz)
  - Efficient frontier calculation
  - Maximum Sharpe ratio portfolio
  - Minimum volatility portfolio
  - Risk-parity allocation
  - Constraints: min/max weights, sector limits
- [x] Benchmark comparison tool (`src/tools/benchmark.py`)
  - Alpha, beta, tracking error vs S&P 500
  - Rolling alpha/beta over time
  - Information ratio
- [x] Add optimization UI to Portfolio Analysis page

**New Dependencies**: `pypfopt` (or scipy.optimize)
**Files to Create**: `src/tools/portfolio_optimizer.py`, `src/tools/benchmark.py`
**Files to Modify**: `frontend/pages/7_Portfolio_Analysis.py`

---

### 2.6 Data Validation Layer

**Tasks**:

- [x] Implement validation in data provider (`src/data/validator.py`)
  - Stale data detection (market hours awareness)
  - Missing field handling with defaults/warnings
  - Price outlier detection (>20% daily move flagged)
  - Cross-provider consistency checks
- [x] Fix news fetcher sample data fallback
  - Log warnings when falling back to sample data
  - Try multiple news sources before fallback
  - Make fallback behavior configurable

**Files to Modify**: `src/data/validator.py` (from Phase 1), `src/tools/news_fetcher.py`

---

## Phase 3: Enhanced Analysis & UX (P2)

**Goal**: Deepen analysis capabilities and improve user experience

### 3.1 Monte Carlo Simulation

**Tasks**:

- [x] Monte Carlo risk tool (`src/tools/monte_carlo.py`)
  - Geometric Brownian Motion simulation
  - 10,000+ paths for VaR/CVaR estimation
  - Probability of reaching target price
  - Portfolio-level simulation with correlations (Cholesky)
- [x] Integrate with RiskAnalyst
- [x] Add visualization (distribution plots, fan charts)

---

### 3.2 Enhanced Backtesting

**Tasks**:

- [x] Add more strategies (mean reversion, breakout, pairs trading, trend following)
- [x] Walk-forward analysis
- [x] Multi-asset backtesting
- [x] Transaction cost modeling improvements

---

### 3.3 Report Generation Completion

**Tasks**:

- [x] Complete PDF generation pipeline
- [x] Add Excel export (openpyxl)
- [x] Report templates (executive summary, deep dive, portfolio review)

---

### 3.4 Persistence & User Accounts

**Tasks**:

- [x] Define SQLAlchemy ORM models for analyses, portfolios, watchlists
- [x] Session-based user identification (no full auth yet)
- [x] Persistent watchlists and portfolio tracking
- [x] Analysis history with comparison

---

### 3.5 Authentication & Security

**Tasks**:

- [x] API key authentication for API routes
- [x] Rate limiting enforcement
- [x] Input sanitization audit

---

## Phase 4: Advanced Features (P3)

**Goal**: Advanced analytics, automation, and UX polish

- [x] Factor modeling — Fama-French style decomposition via ETF proxies (`src/tools/factor_model.py`)
- [x] Performance attribution — Brinson-Fachler allocation/selection/interaction effects (`src/tools/brinson_attribution.py`)
- [x] Tax-loss harvesting — identify harvestable losses, replacement securities, wash sale warnings (`src/tools/tax_loss_harvesting.py`)
- [x] Strategy optimization — genetic algorithm parameter tuning with train/validation split (`src/tools/strategy_optimizer.py`)
- [x] Supply chain analysis — suppliers, customers, competitors, correlation risk (`src/tools/supply_chain.py`)
- [x] Real-time alerts — price/volume/technical signal alerts with WebSocket endpoint (`src/tools/alerts.py`, `ws/alerts`)
- [x] Scheduled reports — daily/weekly/monthly digests, SMTP email delivery with disk fallback (`src/tools/scheduled_reports.py`)
- [x] Dark/light theme toggle — dual color palette with `render_theme_toggle()` in header
- [x] Mobile-responsive UI — responsive breakpoints for 768px and 480px
- [ ] Real-time streaming (Polygon.io, Alpaca, IEX Cloud) — deferred pending API subscriptions

---

## Implementation Order & Dependencies

```
Phase 1 (P0) — Core AI Intelligence
├── 1.3 Second Data Provider (FMP)          ← no dependencies, start first
├── 1.4 LLM Insight Engine                  ← no dependencies, start first
├── 1.1 RAG Pipeline                        ← can start in parallel
└── 1.2 Agentic Reasoning (ReAct)           ← benefits from 1.1 and 1.4

Phase 2 (P1) — Alternative Data & Models
├── 2.1 Macro Data (FRED)                   ← no dependencies
├── 2.2 Social Sentiment                    ← no dependencies
├── 2.3 DCF Model                           ← benefits from 1.3 (better data)
├── 2.4 ML Forecasting                      ← benefits from 1.3 (better data)
├── 2.5 Portfolio Optimization              ← no dependencies
└── 2.6 Data Validation                     ← after 1.3 (validates providers)

Phase 3 (P2) — Enhanced Analysis & UX
├── 3.1 Monte Carlo                         ← after 2.5 (portfolio context)
├── 3.2 Enhanced Backtesting                ← no dependencies
├── 3.3 Reports Completion                  ← no dependencies
├── 3.4 Persistence                         ← no dependencies
└── 3.5 Auth & Security                     ← after 3.4
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Data sources | 1 (yfinance) | 3+ (yfinance, FMP, Alpha Vantage, FRED, Reddit) |
| Agent reasoning depth | 1-step tool call | 3-5 step ReAct chains |
| Document intelligence | None | RAG over SEC filings + transcripts |
| Predictive capability | None | ML forecasts with confidence intervals |
| Portfolio optimization | Basic correlation | Efficient frontier + risk-parity |
| Insight generation | Rule-based | LLM-powered with contradiction detection |
| Valuation models | None | DCF with 3 scenarios + sensitivity |
| Risk quantification | VaR (parametric) | Monte Carlo VaR/CVaR |
