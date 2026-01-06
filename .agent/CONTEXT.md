# Financial Research Analyst Agent - Repository Context

## Quick Reference

**Repository**: https://github.com/gsaini/financial-research-analyst-agent  
**Author**: Gopal Saini  
**Created by**: Antigravity AI (Google DeepMind)  
**Python Version**: 3.14+  
**Last Updated**: 2026-01-05

---

## Project Overview

An AI-powered autonomous agent system for financial data analysis and investment insight generation using LangChain, Python, and multi-agent orchestration.

---

## Directory Structure

```
financial-research-analyst-agent/
├── src/
│   ├── agents/              # AI Agent implementations
│   │   ├── base.py          # Base agent class with LLM integration
│   │   ├── orchestrator.py  # Main orchestrator + FinancialResearchAgent
│   │   ├── data_collector.py
│   │   ├── technical.py     # RSI, MACD, Moving Averages, Bollinger Bands
│   │   ├── fundamental.py   # Valuation ratios, financial metrics
│   │   ├── sentiment.py     # News & analyst sentiment
│   │   ├── risk.py          # VaR, Sharpe Ratio, volatility
│   │   └── report_generator.py
│   ├── tools/               # Analysis tools
│   │   ├── market_data.py   # Yahoo Finance integration
│   │   ├── news_fetcher.py  # NewsAPI integration (with fallback)
│   │   ├── technical_indicators.py
│   │   └── financial_metrics.py
│   ├── models/              # Pydantic data models
│   │   ├── analysis.py      # TechnicalAnalysis, FundamentalAnalysis, etc.
│   │   └── report.py        # ResearchReport, Recommendation
│   ├── api/                 # FastAPI REST API
│   │   ├── routes.py        # API endpoints
│   │   └── schemas.py       # Request/Response schemas
│   ├── utils/               # Logging & helpers
│   ├── main.py              # Application entry point
│   ├── cli.py               # Command-line interface
│   └── config.py            # Pydantic settings configuration
├── tests/                   # pytest test suite
├── static/dashboard/        # Web dashboard (HTML/CSS/JS)
├── notebooks/               # Jupyter exploration notebook
├── config/agents.yaml       # Agent configuration
├── data/sample_data.csv     # Sample stock data
├── Dockerfile               # Multi-stage Docker build (Python 3.14)
├── docker-compose.yml       # PostgreSQL, Redis, ChromaDB
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules
├── README.md                # Full documentation
├── CONTRIBUTING.md          # Contribution guidelines
├── LICENSE                  # MIT License
└── .agent/workflows/start.md  # Quick start workflow
```

---

## Key Commands

### Quick Start

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run API server
python -m src.main api
```

### CLI Usage

```bash
# Analyze a stock
python -m src.cli analyze AAPL

# Analyze portfolio
python -m src.cli portfolio AAPL GOOGL MSFT

# Start dashboard
python -m src.cli dashboard --port 8080
```

### API Endpoints

- `POST /api/v1/analyze` - Analyze a stock
- `GET /api/v1/technical/{symbol}` - Technical analysis
- `GET /api/v1/fundamental/{symbol}` - Fundamental analysis
- `GET /api/v1/sentiment/{symbol}` - Sentiment analysis
- `POST /api/v1/portfolio` - Portfolio analysis
- `POST /api/v1/reports` - Generate report
- `GET /health` - Health check

### Docker

```bash
docker-compose up -d
```

---

## Tech Stack

| Component       | Technology                            |
| --------------- | ------------------------------------- |
| AI Framework    | LangChain, LangGraph                  |
| LLM             | OpenAI GPT-4 / Anthropic Claude       |
| Backend         | FastAPI, Python 3.14+                 |
| Data Processing | Pandas, NumPy                         |
| Financial Data  | Yahoo Finance, Alpha Vantage, NewsAPI |
| Vector Store    | ChromaDB                              |
| Database        | PostgreSQL / SQLite                   |
| Caching         | Redis                                 |
| Frontend        | HTML5, CSS3, JavaScript               |

---

## Agent Architecture

1. **Orchestrator Agent** - Coordinates all agents, manages workflow
2. **Data Collector Agent** - Fetches stock prices, historical data, news
3. **Technical Analyst Agent** - RSI, MACD, Moving Averages, Bollinger Bands, patterns
4. **Fundamental Analyst Agent** - P/E, P/B, ROE, DCF valuation
5. **Sentiment Analyst Agent** - News & social media sentiment
6. **Risk Analyst Agent** - VaR, Volatility, Sharpe Ratio, drawdown
7. **Report Generator Agent** - Creates investment research reports

---

## Environment Variables (Key)

- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key (optional)
- `ALPHA_VANTAGE_API_KEY` - Alpha Vantage API key
- `NEWS_API_KEY` - NewsAPI key
- `DATABASE_URL` - Database connection string
- `REDIS_URL` - Redis connection string
- `POSTGRES_PASSWORD` - PostgreSQL password (for Docker)

---

## Security Notes

- `.env` files are gitignored (only `.env.example` is committed)
- No hardcoded passwords - use environment variables
- Docker uses `${POSTGRES_PASSWORD:-changeme}` pattern

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## Workflow

Use `/start` command to quick start the project with auto-run enabled.
