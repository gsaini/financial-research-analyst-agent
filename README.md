# 🏦 Financial Research Analyst Agent

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)

**An AI-powered autonomous agent that automates financial data analysis and generates investment insights using LangChain, Python, and multi-agent orchestration.**

[Features](#-features) • [Architecture](#-architecture) • [Installation](#-installation) • [Usage](#-usage) • [API Reference](#-api-reference) • [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Case Study Details](#-case-study-details)
- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Interactive API Documentation](#-interactive-api-documentation)
- [API Reference](#-api-reference)
- [Agent Capabilities](#-agent-capabilities)
- [Sample Analysis](#-sample-analysis)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

The **Financial Research Analyst Agent** is an end-to-end AI solution designed to automate financial data analysis and insight generation. Built with LangChain and Python, this agent leverages multiple specialized sub-agents to:

- 📊 **Analyze financial data** from multiple sources
- 📈 **Generate investment insights** with detailed reasoning
- 🔍 **Perform market research** autonomously
- 📑 **Create comprehensive reports** with actionable recommendations
- ⚡ **Enhance decision-making speed** through automation

---

## 📚 Case Study Details

| Attribute      | Description                                                                                                                                    |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Objective**  | Leverage AI agent capabilities to automate data analysis and insight generation, enhancing the speed and quality of investment decision-making |
| **Domain**     | Finance, Investment Analysis, Automation                                                                                                       |
| **Skills**     | AI Agents, Data Analysis, Investment Decision-Making, LangChain, Python                                                                        |
| **Complexity** | Advanced                                                                                                                                       |
| **Duration**   | 4-6 weeks implementation                                                                                                                       |

### Problem Statement

Traditional financial research is:

- **Time-consuming**: Analysts spend 60-80% of time on data gathering
- **Error-prone**: Manual analysis leads to inconsistencies
- **Limited in scope**: Human capacity limits coverage
- **Reactive**: Difficulty in real-time market monitoring

### Solution

This AI agent system addresses these challenges by:

1. **Automating data collection** from multiple financial APIs
2. **Performing real-time analysis** using advanced NLP and ML
3. **Generating actionable insights** with confidence scores
4. **Creating structured reports** for decision-makers

---

## ✨ Features

### Core Capabilities

| Feature                            | Description                                                    |
| ---------------------------------- | -------------------------------------------------------------- |
| 🤖 **Multi-Agent Architecture**    | Specialized agents for different analysis tasks                |
| 📊 **Real-time Data Analysis**     | Live market data processing and analysis                       |
| 📈 **Technical Analysis**          | Automated chart pattern and indicator analysis                 |
| 📰 **News Sentiment Analysis**     | NLP-powered news and social media analysis                     |
| 🎯 **Thematic Investing Analysis** | Group stocks by investment themes (AI, EV, Green Energy, etc.) |
| 👥 **Peer Group Comparison**       | Compare stocks against industry peers with real-time metrics   |
| 🚀 **Market Disruption Analysis**  | Identify disruptors and companies at risk of disruption        |
| 📅 **Quarterly Earnings Analysis** | Track EPS surprises, beat/miss patterns, and earnings quality  |
| 📑 **Report Generation**           | Automated investment research reports                          |
| 🔔 **Alert System**                | Configurable alerts for market conditions                      |
| 🌐 **API Integration**             | REST API for external system integration                       |
| 📖 **Interactive API Docs**        | Swagger UI & ReDoc with OpenAPI 3.0 specification              |
| 📱 **Web Dashboard**               | Interactive visualization dashboard                            |

### Agent Types

1. **Data Collector Agent**: Gathers financial data from multiple sources
2. **Technical Analyst Agent**: Performs technical analysis on price data
3. **Fundamental Analyst Agent**: Analyzes company financials and metrics
4. **Sentiment Analyst Agent**: Processes news and social media sentiment
5. **Risk Analyst Agent**: Performs risk assessment and VaR calculations
6. **Thematic Analyst Agent**: Analyzes stocks grouped by investment themes and megatrends
7. **Disruption Analyst Agent**: Identifies market disruptors and at-risk companies via R&D, growth, and margin analysis
8. **Earnings Analyst Agent**: Tracks quarterly EPS surprises, beat/miss patterns, and earnings quality
9. **Report Generator Agent**: Compiles insights into structured reports
10. **Orchestrator Agent**: Coordinates all agents and manages workflow

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          FINANCIAL RESEARCH ANALYST AGENT                        │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                          ORCHESTRATOR AGENT                                │  │
│  │  • Task Planning & Decomposition  • Agent Coordination  • Aggregation     │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                          │
│           ┌───────────────┬───────────┼───────────┬───────────────┐              │
│           │               │           │           │               │              │
│  ┌────────▼───────┐ ┌─────▼─────┐ ┌───▼───┐ ┌────▼────┐ ┌────────▼───────┐     │
│  │ DATA COLLECTOR │ │ TECHNICAL │ │ FUNDA │ │ SENTI-  │ │ RISK           │     │
│  │ AGENT          │ │ ANALYST   │ │ MENTAL│ │ MENT    │ │ ANALYST AGENT  │     │
│  │                │ │ AGENT     │ │ AGENT │ │ AGENT   │ │                │     │
│  │ • Yahoo Finance│ │ • RSI     │ │ • P/E │ │ • News  │ │ • VaR Calc     │     │
│  │ • Alpha Vantage│ │ • MACD    │ │ • EPS │ │ • Social│ │ • Volatility   │     │
│  │ • News APIs    │ │ • SMA/EMA │ │ • ROE │ │ • Trend │ │ • Correlation  │     │
│  └────────────────┘ └───────────┘ └───────┘ └─────────┘ └────────────────┘     │
│                                                                                  │
│  ┌─────────────────────────────────┐  ┌──────────────────────────────────────┐  │
│  │ THEMATIC ANALYST AGENT          │  │ DISRUPTION ANALYST AGENT             │  │
│  │                                 │  │                                      │  │
│  │ • Theme-to-Ticker Mapping       │  │ • R&D Intensity Analysis             │  │
│  │ • Multi-Horizon Performance     │  │ • Revenue Growth Acceleration        │  │
│  │ • Momentum & Health Scoring     │  │ • Gross Margin Trajectory            │  │
│  │ • Correlation & Diversification │  │ • Disruption Score (0-100)           │  │
│  │ • Sector Overlap Analysis       │  │ • Disruptor vs At-Risk Classification│  │
│  └─────────────────────────────────┘  └──────────────────────────────────────┘  │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ EARNINGS ANALYST AGENT                                                    │  │
│  │                                                                           │  │
│  │ • EPS Actual vs Estimate Tracking    • Quarterly Trend Analysis (QoQ/YoY)│  │
│  │ • Beat/Miss Pattern Recognition      • Earnings Quality Scoring (1-10)   │  │
│  │ • Surprise % Calculation             • Upcoming Earnings Dates           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ REPORT GENERATOR AGENT                                                    │  │
│  │                                                                           │  │
│  │ • PDF / Markdown / JSON Reports  • Actionable Recommendations             │  │
│  │ • Executive Summaries            • Multi-Agent Insight Aggregation        │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                  DATA LAYER                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Vector Store │ │ Cache Layer  │ │ Database     │ │ File Store │ │ Theme    │ │
│  │ (ChromaDB)   │ │ (Redis)      │ │ (PostgreSQL) │ │ (S3/Local) │ │ Config   │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ └──────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component           | Technology                                   |
| ------------------- | -------------------------------------------- |
| **AI Framework**    | LangChain, LangGraph                         |
| **LLM**             | Ollama (Llama 4, Mistral) / Groq / LM Studio |
| **Embeddings**      | Sentence Transformers / HuggingFace / Ollama |
| **Vector Store**    | ChromaDB / Qdrant / Milvus / Weaviate        |
| **Backend**         | FastAPI, Python 3.14+                        |
| **Data Processing** | Pandas, NumPy                                |
| **Visualization**   | Plotly, Matplotlib                           |
| **Frontend**        | HTML5, CSS3, JavaScript                      |
| **Database**        | PostgreSQL / SQLite                          |
| **Caching**         | Redis                                        |

---

## 🚀 Installation

### Prerequisites

- Python 3.14 or higher
- pip or conda package manager
- OpenAI API key (or other LLM provider)
- Alpha Vantage API key (optional, for live data)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/gsaini/financial-research-analyst-agent.git
cd financial-research-analyst-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the application
python -m src.main
```

### Docker Installation

```bash
# Build the Docker image
docker build -t financial-analyst-agent .

# Run the container
docker run -p 8000:8000 --env-file .env financial-analyst-agent
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# LLM Configuration (Open Source by Default)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama4:latest
LLM_TEMPERATURE=0.1

# Embedding Configuration (Open Source)
EMBEDDING_PROVIDER=sentence-transformers
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2

# Financial Data APIs (Yahoo Finance is free, others optional)
USE_YFINANCE=true
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key  # Optional
NEWS_API_KEY=your_news_api_key  # Optional

# Database Configuration
DATABASE_URL=sqlite:///./data/financial_agent.db
REDIS_URL=redis://localhost:6379

# Vector Store (Open Source)
VECTOR_STORE_PROVIDER=chroma
CHROMA_PERSIST_DIR=./data/chroma

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

### Agent Configuration

Edit `config/agents.yaml` to customize agent behavior:

```yaml
orchestrator:
  max_iterations: 10
  timeout_seconds: 300

technical_analyst:
  indicators:
    - RSI
    - MACD
    - SMA
    - EMA
    - Bollinger Bands
  lookback_periods: [14, 30, 50, 200]

sentiment_analyst:
  sources:
    - news
    - twitter
    - reddit
  sentiment_threshold: 0.3
```

---

## 📖 Usage

### Python API

```python
from src.agents import FinancialResearchAgent

# Initialize the agent
agent = FinancialResearchAgent()

# Analyze a single stock
result = agent.analyze("AAPL")
print(result.summary)
print(result.recommendation)
print(result.confidence_score)

# Analyze multiple stocks
portfolio = ["AAPL", "GOOGL", "MSFT", "AMZN"]
portfolio_analysis = agent.analyze_portfolio(portfolio)

# Generate a research report
report = agent.generate_report(
    symbols=["AAPL"],
    include_technical=True,
    include_fundamental=True,
    include_sentiment=True,
    format="pdf"
)
```

### REST API

```bash
# Analyze a stock
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "analysis_type": "comprehensive"}'

# Get technical analysis
curl "http://localhost:8000/api/v1/technical/AAPL"

# Generate report
curl -X POST "http://localhost:8000/api/v1/reports" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL", "GOOGL"], "format": "pdf"}'

# List available investment themes
curl "http://localhost:8000/api/v1/themes"

# Analyze an investment theme
curl -X POST "http://localhost:8000/api/v1/theme/ai_machine_learning" \
  -H "Content-Type: application/json" \
  -d '{"theme_id": "ai_machine_learning", "include_narrative": false}'

# Compare multiple themes
curl -X POST "http://localhost:8000/api/v1/themes/compare" \
  -H "Content-Type: application/json" \
  -d '{"theme_ids": ["ai_machine_learning", "cybersecurity", "electric_vehicles"]}'

# Analyze market disruption profile
curl "http://localhost:8000/api/v1/disruption/TSLA"

# Disruption analysis with LLM narrative
curl -X POST "http://localhost:8000/api/v1/disruption/analyze" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "NVDA", "include_narrative": true}'

# Compare disruption profiles across competitors
curl -X POST "http://localhost:8000/api/v1/disruption/compare" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["TSLA", "F", "GM", "TM"], "include_narrative": false}'

# Analyze quarterly earnings
curl "http://localhost:8000/api/v1/earnings/AAPL"

# Earnings analysis with LLM narrative
curl -X POST "http://localhost:8000/api/v1/earnings/analyze" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "MSFT", "include_narrative": true}'

# Compare earnings profiles across companies
curl -X POST "http://localhost:8000/api/v1/earnings/compare" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL", "MSFT", "GOOGL"], "include_narrative": false}'
```

### Command Line Interface

```bash
# Quick analysis
python -m src.cli analyze AAPL

# Portfolio analysis
python -m src.cli portfolio AAPL GOOGL MSFT --output report.pdf

# Start web dashboard
python -m src.cli dashboard --port 8080
```

---

## 📚 Interactive API Documentation

The API includes built-in interactive documentation powered by **OpenAPI 3.0** specification.

### Swagger UI

Access the interactive Swagger UI at: **http://localhost:8000/docs**

Features:
- Interactive API explorer with "Try it out" functionality
- Auto-generated request/response examples
- Authentication testing
- Schema validation

### ReDoc

Access the ReDoc documentation at: **http://localhost:8000/redoc**

Features:
- Clean, responsive three-panel design
- Deep linking to specific endpoints
- Code samples in multiple languages
- Search functionality

### OpenAPI JSON Schema

Download the raw OpenAPI specification: **http://localhost:8000/openapi.json**

Use this to:
- Generate client SDKs (Python, TypeScript, Go, etc.)
- Import into Postman or Insomnia
- Create automated API tests

---

## 🔧 API Reference

### Endpoints

| Method      | Endpoint                       | Description                                    |
| ----------- | ------------------------------ | ---------------------------------------------- |
| `POST`      | `/api/v1/analyze`              | Analyze a stock symbol                         |
| `GET`       | `/api/v1/technical/{symbol}`   | Get technical analysis                         |
| `GET`       | `/api/v1/fundamental/{symbol}` | Get fundamental analysis                       |
| `GET`       | `/api/v1/sentiment/{symbol}`   | Get sentiment analysis                         |
| `POST`      | `/api/v1/portfolio`            | Analyze a portfolio                            |
| `POST`      | `/api/v1/reports`              | Generate a report                              |
| `GET`       | `/api/v1/market/summary`       | Get market summary                             |
| `GET`       | `/api/v1/themes`               | List all available investment themes           |
| `POST`      | `/api/v1/theme/{theme_id}`     | Analyze an investment theme                    |
| `POST`      | `/api/v1/themes/compare`       | Compare multiple themes side by side           |
| `GET`       | `/api/v1/peers/{symbol}`       | Get peer comparison (auto-discovery)           |
| `POST`      | `/api/v1/peers/compare`        | Compare stock against specific peers           |
| `GET`       | `/api/v1/disruption/{symbol}`  | Get market disruption analysis                 |
| `POST`      | `/api/v1/disruption/analyze`   | Analyze disruption with optional LLM narrative |
| `POST`      | `/api/v1/disruption/compare`   | Compare disruption profiles across companies   |
| `GET`       | `/api/v1/earnings/{symbol}`    | Get quarterly earnings analysis                |
| `POST`      | `/api/v1/earnings/analyze`     | Analyze earnings with optional LLM narrative   |
| `POST`      | `/api/v1/earnings/compare`     | Compare earnings profiles across companies     |
| `WebSocket` | `/ws/alerts`                   | Real-time alerts                               |

### Response Schema

```json
{
  "symbol": "AAPL",
  "analysis_date": "2024-01-15T10:30:00Z",
  "technical": {
    "trend": "bullish",
    "signals": [...],
    "indicators": {...}
  },
  "fundamental": {
    "valuation": "fairly_valued",
    "metrics": {...},
    "growth_score": 8.5
  },
  "sentiment": {
    "overall": "positive",
    "score": 0.72,
    "sources": {...}
  },
  "recommendation": {
    "action": "BUY",
    "confidence": 0.85,
    "reasoning": "...",
    "target_price": 195.00,
    "stop_loss": 175.00
  }
}
```

---

## 🤖 Agent Capabilities

### 1. Data Collector Agent

```python
Capabilities:
- Fetch real-time stock prices
- Historical data retrieval
- Financial statements download
- News article collection
- Social media data gathering
```

### 2. Technical Analyst Agent

```python
Indicators Supported:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- SMA/EMA (Simple/Exponential Moving Averages)
- Bollinger Bands
- Fibonacci Retracements
- Volume Analysis
- Support/Resistance Levels
```

### 3. Fundamental Analyst Agent

```python
Metrics Analyzed:
- P/E Ratio, P/B Ratio, P/S Ratio
- EPS and Revenue Growth
- ROE, ROA, ROIC
- Debt-to-Equity Ratio
- Free Cash Flow
- Dividend Yield and Payout Ratio
- Competitive Analysis
```

### 4. Sentiment Analyst Agent

```python
Sources:
- Financial news articles
- SEC filings and earnings calls
- Social media (Twitter, Reddit)
- Analyst ratings
- Insider trading activity
```

### 5. Thematic Analyst Agent

```python
Capabilities:
- Analyze stocks grouped by investment themes (AI, EV, Green Energy, etc.)
- Multi-horizon performance tracking (1W, 1M, 3M, 6M, 1Y, YTD)
- Intra-theme correlation and diversification scoring
- Momentum scoring (0-100) with configurable weights
- Theme health scoring (0-100) combining performance, momentum, risk
- Sector overlap breakdown
- Top performer and laggard identification
- LLM-generated narrative outlook (optional)

Available Themes:
- AI & Machine Learning          - Electric Vehicles
- Green Energy & Clean Tech       - Cybersecurity
- Aging Population & Healthcare   - Cloud Computing & SaaS
- Fintech & Digital Payments      - Space Economy & Aerospace
- Digital Entertainment & Gaming  - Blockchain & Web3
```

### 6. Disruption Analyst Agent

```python
Capabilities:
- Analyze whether a company is a market disruptor or at risk of disruption
- R&D intensity analysis (R&D/Revenue ratio, trend vs industry benchmarks)
- Revenue growth acceleration/deceleration tracking
- Gross margin trajectory analysis (expansion = competitive moat)
- Disruption scoring (0-100) with weighted components
- Classification: Active Disruptor, Moderate Innovator, Stable Incumbent, At Risk
- Industry-specific benchmarks for 18+ industries
- Risk factor and competitive strength identification
- Multi-company disruption comparison with ranking
- LLM-generated qualitative competitive assessment (optional)

Disruption Classification:
- Active Disruptor (70+)    : High R&D, accelerating growth, expanding margins
- Moderate Innovator (50-70): Some disruptive signals, mixed trajectory
- Stable Incumbent (30-50)  : Established position, limited innovation
- At Risk (<30)             : Low innovation, weak growth, margin pressure

Scoring Components:
- R&D Intensity Score     (35% weight): Innovation investment vs industry
- Revenue Growth Score    (40% weight): Growth rate and acceleration
- Margin Trajectory Score (25% weight): Gross margin expansion/contraction
```

### 7. Earnings Analyst Agent

```python
Capabilities:
- Track quarterly EPS actuals vs analyst estimates
- Analyze beat/miss patterns and management guidance accuracy
- Calculate quarter-over-quarter and year-over-year trends
- Assess earnings quality (operational vs one-time items)
- Identify upcoming earnings dates and estimate trends
- Compare earnings profiles across sector peers
- LLM-generated earnings narrative (optional)

Earnings Pattern Classification:
- Consistent Beater (80%+ beat rate): Management under-promises, reliable execution
- Regular Beater (60-80%)           : Tends to exceed expectations
- Mixed Results (40-60%)            : Unpredictable earnings, higher risk
- Regular Misser (20-40%)           : Tends to disappoint
- Consistent Misser (<20%)          : Credibility concerns

Earnings Quality Score (1-10):
- High Quality (8-10)     : Driven by operations, sustainable
- Good Quality (6.5-8)    : Primarily operational with minor concerns
- Average Quality (5-6.5) : Some non-operational factors present
- Below Average (3.5-5)   : Significant non-operational items
- Low Quality (1-3.5)     : Earnings not reflective of core operations

Key Metrics:
- Beat Rate %           : Percentage of quarters exceeding estimates
- Average Surprise %    : Mean EPS surprise across quarters
- Revenue/Income Trends : QoQ and YoY growth trajectory
- Margin Trajectory     : Gross margin expansion/contraction pattern
```

---

## 📊 Sample Analysis

### Example: Apple Inc. (AAPL) Analysis

```
================================================================================
                     FINANCIAL RESEARCH ANALYST REPORT
                              Apple Inc. (AAPL)
                           Generated: 2024-01-15
================================================================================

EXECUTIVE SUMMARY
-----------------
Apple Inc. demonstrates strong fundamentals with continued growth in services
revenue and a robust product ecosystem. Technical indicators suggest a bullish
trend, while sentiment analysis reveals positive market perception.

TECHNICAL ANALYSIS
------------------
Trend: BULLISH
RSI (14): 58.3 (Neutral)
MACD: Bullish crossover detected
Support: $175.00
Resistance: $195.00

FUNDAMENTAL ANALYSIS
--------------------
P/E Ratio: 28.5 (Industry Avg: 25.2)
Revenue Growth: 8.2% YoY
EPS Growth: 12.1% YoY
Debt/Equity: 1.52
ROE: 147.3%

SENTIMENT ANALYSIS
------------------
Overall Sentiment: POSITIVE (Score: 0.72)
News Sentiment: 0.68
Social Media: 0.75
Analyst Consensus: 0.82

RECOMMENDATION
--------------
Action: BUY
Confidence: 85%
Target Price: $195.00
Stop Loss: $175.00

Reasoning: Strong fundamentals combined with positive technical signals and
favorable market sentiment suggest upside potential. The services segment
continues to grow, providing recurring revenue stability.
================================================================================
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_agents.py -v

# Run thematic investing tests
pytest tests/test_thematic.py -v

# Run market disruption analysis tests
pytest tests/test_disruption.py -v

# Run quarterly earnings analysis tests
pytest tests/test_earnings.py -v

# Run peer comparison tests
pytest tests/test_peer_comparison.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run integration tests (requires network access for yfinance)
pytest tests/ -v -m integration
```

---

## 🚢 Deployment

### Docker Compose

```yaml
version: "3.8"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/financial_agent
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: financial_agent
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD} # Set in .env file
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes

See `k8s/` directory for Kubernetes deployment manifests.

---

## 📁 Project Structure

```
financial-research-analyst-agent/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration management
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py             # Base agent class
│   │   ├── orchestrator.py     # Main orchestrator agent
│   │   ├── data_collector.py   # Data collection agent
│   │   ├── technical.py        # Technical analysis agent
│   │   ├── fundamental.py      # Fundamental analysis agent
│   │   ├── sentiment.py        # Sentiment analysis agent
│   │   ├── risk.py             # Risk analysis agent
│   │   ├── thematic.py         # Thematic investing analysis agent ✨
│   │   ├── disruption.py       # Market disruption analysis agent ✨
│   │   ├── earnings.py         # Quarterly earnings analysis agent ✨
│   │   └── report_generator.py # Report generation agent
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── market_data.py      # Market data fetching tools
│   │   ├── news_fetcher.py     # News fetching tools
│   │   ├── technical_indicators.py
│   │   ├── financial_metrics.py
│   │   ├── peer_comparison.py  # Peer discovery & comparison tools ✨
│   │   ├── theme_mapper.py     # Theme-to-ticker mapping & analysis tools ✨
│   │   ├── disruption_metrics.py # R&D, growth, margin & disruption scoring ✨
│   │   └── earnings_data.py    # Quarterly earnings data & quality scoring ✨
│   ├── models/
│   │   ├── __init__.py
│   │   ├── analysis.py         # Analysis data models
│   │   └── report.py           # Report data models
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py           # API routes (incl. thematic endpoints)
│   │   └── schemas.py          # Pydantic schemas (incl. theme schemas)
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # Logging utility
│       └── helpers.py          # Helper functions
├── tests/
│   ├── __init__.py
│   ├── test_agents.py
│   ├── test_tools.py
│   ├── test_api.py
│   ├── test_peer_comparison.py # Peer comparison tests ✨
│   ├── test_thematic.py        # Thematic investing tests ✨
│   ├── test_disruption.py      # Market disruption analysis tests ✨
│   └── test_earnings.py        # Quarterly earnings analysis tests ✨
├── data/
│   └── sample_data.csv
├── docs/
│   ├── architecture.md
│   ├── api_reference.md        # API reference (incl. peer comparison endpoints)
│   └── SCOPE.md                # Feature scope & enhancement roadmap
├── notebooks/
│   └── exploration.ipynb
├── static/
│   └── dashboard/
├── config/
│   ├── agents.yaml             # Agent configuration
│   └── themes.yaml             # Investment theme definitions ✨
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) - AI Agent Framework
- [OpenAI](https://openai.com/) - Language Models
- [Alpha Vantage](https://www.alphavantage.co/) - Financial Data API
- [Yahoo Finance](https://finance.yahoo.com/) - Market Data

---

<div align="center">

**Created by 🤖 Antigravity AI (Google DeepMind)**

**Author: Gopal Saini**

_Part of the AI Agents Case Studies Collection_

[⬆ Back to Top](#-financial-research-analyst-agent)

</div>
