# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Run the API server
python -m src.main api

# Run demo analysis
python -m src.main demo

# CLI commands
python -m src.cli analyze AAPL              # Single stock analysis
python -m src.cli portfolio AAPL GOOGL MSFT # Portfolio analysis
python -m src.cli dashboard --port 8080     # Web dashboard

# Testing
pytest tests/ -v                            # Run all tests
pytest tests/test_agents.py -v              # Run specific test file
pytest tests/test_agents.py::TestTechnicalAnalyst -v  # Run specific test class
pytest tests/ --cov=src --cov-report=html   # With coverage

# Code quality
black src/ tests/                           # Format code
isort src/ tests/                           # Sort imports
flake8 src/ tests/                          # Lint
mypy src/                                   # Type check

# Docker
docker-compose up -d                        # Full stack (PostgreSQL, Redis, ChromaDB)
docker build -t financial-analyst .         # Build image
```

## Architecture

This is a **hierarchical multi-agent system** for financial research analysis.

### Agent Orchestration Pattern

```
FinancialResearchAgent (sync wrapper)
         ↓
OrchestratorAgent (coordinator)
         ↓ delegates via asyncio.gather()
┌────────┼────────┬────────┬────────┬────────┐
│        │        │        │        │        │
DataColl TechAnly FundAnly SentiAnly RiskAnly → ReportGen
```

**OrchestratorAgent** (`src/agents/orchestrator.py`) coordinates all specialized agents, manages workflow, and aggregates results. Each agent inherits from **BaseAgent** (`src/agents/base.py`) which provides:

- LLM initialization and tool binding
- State management via `AgentState` (idle/running/completed/error)
- Standardized results via `AgentResult`
- Async/sync execution support

### Agent Responsibilities

| Agent | Key Methods |
|-------|-------------|
| DataCollector | `collect_stock_data()`, `collect_news()` |
| TechnicalAnalyst | `analyze()` - RSI, MACD, moving averages, patterns |
| FundamentalAnalyst | `analyze()` - P/E, P/B, ROE, DCF valuation |
| SentimentAnalyst | `analyze()` - News & social media sentiment |
| RiskAnalyst | `analyze()` - VaR, volatility, Sharpe, beta |
| ReportGenerator | `generate()` - JSON/Markdown/PDF reports |

### Tools Layer

Tools in `src/tools/` are bound to agents using LangChain's `@tool` decorator:

- `market_data.py` - Yahoo Finance integration (prices, historical, financials)
- `technical_indicators.py` - RSI, MACD, moving averages calculations
- `news_fetcher.py` - Multi-source news with fallback mechanisms
- `financial_metrics.py` - Fundamental analysis calculations

### API Layer

FastAPI app in `src/api/routes.py` with prefix `/api/v1`:

- `POST /analyze` - Comprehensive stock analysis
- `GET /technical/{symbol}`, `GET /fundamental/{symbol}`, `GET /sentiment/{symbol}`
- `POST /portfolio` - Multi-stock analysis
- `POST /reports` - Generate research reports

## Configuration (Open Source by Default)

**Prerequisites**: Install [Ollama](https://ollama.ai) and pull a model:

```bash
ollama pull llama4:latest
```

**Environment**: Copy `.env.example` to `.env`. Default configuration uses:

- **LLM**: Ollama with Llama 4 (local, free)
- **Embeddings**: Sentence Transformers (local, free)
- **Vector Store**: ChromaDB (local, free)
- **Financial Data**: Yahoo Finance via yfinance (free, no API key)

**Supported LLM providers** (set `LLM_PROVIDER` in `.env`):

| Provider | Local | Free | Notes |
|----------|-------|------|-------|
| `ollama` | Yes | Yes | Default - Llama 4, Mistral, etc. |
| `lmstudio` | Yes | Yes | GUI for local models |
| `vllm` | Yes | Yes | High-performance inference |
| `groq` | No | Free tier | Fast cloud inference |
| `openai` | No | Paid | GPT-4, etc. |
| `anthropic` | No | Paid | Claude models |

**Agent settings**: `config/agents.yaml` contains indicator parameters, recommendation thresholds, and weight distributions:

- Technical: 25%, Fundamental: 35%, Sentiment: 20%, Risk: 20%
- Recommendation thresholds: Strong Buy (0.80+), Buy (0.65+), Hold (0.45+), Sell (0.30+)

**Settings class**: `src/config.py` uses Pydantic for typed configuration with nested settings (LLM, DataAPI, Database, VectorStore, Agent, API).

## Key Patterns

- **Async-first**: Agents use `async execute()` with `execute_sync()` wrapper
- **Multi-provider LLM**: `BaseAgent._create_default_llm()` supports Ollama, LM Studio, vLLM, Groq, OpenAI, Anthropic
- **Tool binding**: Uses `create_tool_calling_agent()` for provider-agnostic tool calling
- **State tracking**: `AgentState` enum tracks execution lifecycle
- **Result standardization**: All agents return `AgentResult` with success, data, error, execution_time
