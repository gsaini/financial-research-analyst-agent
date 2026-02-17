# Enhancement Scope Document - Financial Research Analyst Agent

**Version**: 2.0
**Last Updated**: February 16, 2026
**Status**: Planning

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Feature Specifications](#feature-specifications)
   - [Feature 1: Thematic Investing Analysis](#feature-1-thematic-investing-analysis)
   - [Feature 2: Peer Comparison](#feature-2-peer-comparison)
   - [Feature 3: Market Disruption Analysis](#feature-3-market-disruption-analysis)
   - [Feature 4: Quarterly Earnings Analysis](#feature-4-quarterly-earnings-analysis)
   - [Feature 5: Historical Stock Performance Tracking](#feature-5-historical-stock-performance-tracking)
   - [Feature 6: Enhanced Multi-Format Reports](#feature-6-enhanced-multi-format-reports)
   - [Feature 7: Event-Driven Performance Analysis](#feature-7-event-driven-performance-analysis)
   - [Feature 8: Backtesting Engine](#feature-8-backtesting-engine)
   - [Feature 9: Enhanced News and Sentiment Analysis](#feature-9-enhanced-news-and-sentiment-analysis)
   - [Feature 10: Bloomberg-like Terminal](#feature-10-bloomberg-like-terminal)
   - [Feature 11: Key Observations and Insights](#feature-11-key-observations-and-insights)
   - [Feature 12: Insider & Institutional Activity](#feature-12-insider--institutional-activity)
   - [Feature 13: Options Flow Analysis](#feature-13-options-flow-analysis)
   - [Feature 14: Short Interest Analysis](#feature-14-short-interest-analysis)
   - [Feature 15: Dividend Analysis](#feature-15-dividend-analysis)
   - [Feature 16: Analyst Consensus Tracking](#feature-16-analyst-consensus-tracking)
   - [Feature 17: Macro Economic Integration](#feature-17-macro-economic-integration)
   - [Feature 18: Alert & Notification System](#feature-18-alert--notification-system)
   - [Feature 19: Portfolio Optimization](#feature-19-portfolio-optimization)
4. [Architecture Changes](#architecture-changes)
5. [New Agents Required](#new-agents-required)
6. [New Tools Required](#new-tools-required)
7. [Phased Implementation Roadmap](#phased-implementation-roadmap)
8. [Priority Matrix](#priority-matrix)

---

## Executive Summary

### What We're Building

This document defines 19 enhancement features that will transform the Financial Research Analyst Agent from a **basic stock analysis tool** into a **comprehensive investment research platform**. These enhancements cover:

- **Deeper analysis** - Quarterly earnings, peer comparison, event-driven performance
- **Broader coverage** - Thematic investing, market disruption, Bloomberg-like terminal
- **Better intelligence** - Enhanced sentiment (FinBERT), backtesting, key observations
- **Professional output** - PDF/Markdown/HTML reports with charts
- **Smart money tracking** - Insider transactions, institutional ownership, options flow
- **Income investing** - Dividend analysis, payout sustainability, yield tracking
- **Risk management** - Short interest, macro integration, portfolio optimization
- **Proactive alerts** - Price alerts, technical signals, news spikes, earnings reminders

### Why We're Building It

The current system has significant gaps between what's **configured** and what's **actually implemented**:

| What's Advertised | What Actually Works |
|---|---|
| Sentiment analysis from news + social media | TextBlob on news only, social media missing |
| Risk metrics: Volatility, VaR, Sharpe, Sortino, Beta | Sortino and Beta not implemented |
| Report formats: JSON, Markdown, PDF, HTML | Only JSON works |
| Data sources: Yahoo, Alpha Vantage, Finnhub | Only Yahoo Finance works |
| Industry comparison with benchmarks | Hardcoded benchmarks for 4 industries only |
| Real-time market summary | Returns hardcoded static data |

### Expected Outcome

After implementing all 19 features, the system will:

- Analyze stocks with **real peer comparison** instead of hardcoded benchmarks
- Track **quarterly earnings** trends and predict earnings impact
- Provide **event-driven analysis** (performance before/after earnings)
- Generate **professional PDF/Markdown reports** with charts
- Use **financial-domain AI** (FinBERT) instead of generic TextBlob
- Support **backtesting** trading strategies against historical data
- Deliver **thematic investing** analysis across sectors/themes
- Provide **Bloomberg-like** market terminal capabilities
- Synthesize **key observations** across all analysis dimensions
- Track **insider buying/selling** and institutional ownership changes
- Analyze **options flow** for unusual activity and sentiment signals
- Monitor **short interest** for squeeze potential and bearish sentiment
- Evaluate **dividend safety** and income investing opportunities
- Aggregate **analyst ratings** and price target consensus
- Integrate **macro economic factors** (Fed policy, rates, inflation)
- Send **proactive alerts** on price levels, signals, and news events
- Optimize **portfolio allocation** using modern portfolio theory

---

## Current State Assessment

### What Works Today

| Component | Status | Details |
|---|---|---|
| **Technical Analysis** | Working | RSI, MACD, Moving Averages, Bollinger Bands, Support/Resistance |
| **Fundamental Analysis** | Partial | P/E, P/B, P/S, EV/EBITDA, ROE, ROA, ROIC, DCF, Multiples |
| **Sentiment Analysis** | Minimal | TextBlob on news articles only, no financial-domain NLP |
| **Risk Analysis** | Partial | Volatility, VaR, CVaR, Sharpe, Max Drawdown (Beta/Sortino missing) |
| **Data Collection** | Basic | Yahoo Finance only (single source, no fallback) |
| **Report Generation** | Minimal | JSON only (no PDF, Markdown, HTML despite being configured) |
| **API Endpoints** | Partial | Several endpoints return hardcoded/placeholder data |

### Critical Gaps Identified

#### 1. Hardcoded Placeholder Responses

**File**: `src/api/routes.py`

```python
# Sentiment endpoint (lines 206-215) - Returns static data
@router.get("/sentiment/{symbol}")
async def get_sentiment_analysis(symbol: str):
    return {
        "sentiment": "positive",   # Always "positive"!
        "score": 0.65,             # Always 0.65!
        "news_sentiment": 0.7,     # Always the same
        "social_sentiment": 0.6,   # Social media not implemented
    }

# Market summary (lines 267-278) - Returns static data
@router.get("/market/summary")
async def get_market_summary():
    return {
        "indices": {
            "SPY": {"price": 470.50},   # Hardcoded price!
            "QQQ": {"price": 395.20},   # Never updates!
        }
    }
```

#### 2. Hardcoded Industry Benchmarks

**File**: `src/tools/financial_metrics.py`

```python
# compare_to_industry() uses hardcoded values for only 4 industries:
industry_benchmarks = {
    "Technology": {"pe_ratio": 25.0, "roe": 20.0},
    "Healthcare": {"pe_ratio": 22.0, "roe": 15.0},
    "Finance":    {"pe_ratio": 12.0, "roe": 12.0},
    "Consumer":   {"pe_ratio": 20.0, "roe": 18.0},
}
# No real peer data, no dynamic calculation
```

#### 3. Missing Configured Features

**File**: `config/agents.yaml` configures features that don't exist in code:

| Configured | Implemented | Gap |
|---|---|---|
| `risk_metrics: [sortino, beta]` | Not in `risk.py` | Missing risk calculations |
| `report_formats: [json, markdown, pdf, html]` | Only JSON | Missing 3 report formats |
| `sentiment_sources: [social, insider]` | Not in `sentiment.py` | Missing data sources |
| `patterns: [head_shoulders, double_top]` | Only basic patterns | Missing advanced pattern detection |
| `data_sources: [alpha_vantage, finnhub]` | Only yfinance | Missing fallback sources |

---

## Feature Specifications

---

### Feature 1: Thematic Investing Analysis

#### What It Is

**Simple explanation**: Instead of analyzing stocks by traditional sectors (Technology, Healthcare), thematic investing groups stocks by **investment themes** or **megatrends**. For example:

```
Traditional Sector:  "Technology"
  → AAPL, MSFT, GOOGL, META, NVDA (all lumped together)

Thematic Approach:
  "AI & Machine Learning"  → NVDA, MSFT, GOOGL, AMD, PLTR
  "Electric Vehicles"      → TSLA, RIVN, LCID, NIO, LI
  "Green Energy"           → ENPH, SEDG, FSLR, NEE, PLUG
  "Cybersecurity"          → CRWD, PANW, ZS, FTNT, S
  "Aging Population"       → UNH, JNJ, ABT, MDT, TMO
```

A semiconductor company like NVDA appears in "AI" theme, not just "Technology."

#### Why It Matters

- Investors increasingly allocate by **theme**, not sector
- Discovers **non-obvious investment opportunities** (e.g., a utility company as a data center play)
- Provides **portfolio construction** guidance for thematic exposure
- Shows whether a theme is **gaining or losing momentum**
- Differentiates from basic stock screeners

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance | Existing | Individual stock data, sector/industry classification |
| Theme-to-ticker YAML | New (config) | Predefined mapping of themes to constituent stocks |
| ETF holdings | New | Reverse-engineer themes from thematic ETFs (ARKK, ICLN, LIT) |
| News feeds | Existing | Theme momentum from news volume/sentiment |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/agents/thematic.py` | New `ThematicAnalystAgent` |
| **CREATE** | `src/tools/theme_mapper.py` | Theme-to-ticker mapping, ETF holdings, theme metrics |
| **CREATE** | `config/themes.yaml` | Theme definitions with ticker lists and ETF references |
| **MODIFY** | `src/agents/orchestrator.py` | Add thematic analysis as optional workflow step |
| **MODIFY** | `src/api/routes.py` | Add `POST /api/v1/theme/{theme_name}`, `GET /api/v1/themes` |
| **MODIFY** | `src/api/schemas.py` | Add `ThemeAnalysisRequest`, `ThemeAnalysisResponse` |

#### Key Metrics and Outputs

```json
{
  "theme": "AI & Machine Learning",
  "constituents": ["NVDA", "MSFT", "GOOGL", "AMD", "PLTR"],
  "theme_performance": {
    "1_week": "+3.2%",
    "1_month": "+8.5%",
    "3_month": "+15.2%",
    "6_month": "+28.7%",
    "1_year": "+45.3%"
  },
  "momentum_score": 82,
  "top_performers": [
    {"symbol": "NVDA", "1_year_return": "+120%"},
    {"symbol": "PLTR", "1_year_return": "+85%"}
  ],
  "laggards": [
    {"symbol": "AMD", "1_year_return": "+5%"}
  ],
  "sector_overlap": {
    "Technology": "80%",
    "Communication": "20%"
  },
  "theme_risk": {
    "intra_correlation": 0.72,
    "diversification_score": "Low"
  },
  "theme_health_score": 78,
  "outlook": "Strong momentum with high correlation risk"
}
```

#### Implementation Approach

1. Create `config/themes.yaml` with predefined themes and their constituent tickers
2. Build `ThematicAnalystAgent` that:
   - Accepts a theme name
   - Expands it to constituent stocks
   - Runs batch data collection via existing `DataCollectorAgent`
   - Aggregates performance, calculates correlation matrix
   - Uses LLM to generate theme outlook narrative
3. Use ETF holdings as secondary source for theme membership
4. Compute aggregate statistics: weighted returns, correlation, momentum

#### Priority: P1

High-value differentiation. Depends on having peer comparison (Feature 2) and performance tracking (Feature 5) working first.

#### Dependencies

- Feature 2 (Peer Comparison) - Enriches theme analysis with relative metrics
- Feature 5 (Stock Performance) - Provides return calculations for theme aggregation
- Feature 9 (Enhanced News) - Theme-level sentiment from news

---

### Feature 2: Peer Comparison

#### What It Is

**Simple explanation**: Comparing a stock against its **closest competitors** across financial, valuation, performance, and risk metrics. No stock exists in isolation - you need to know if Apple's P/E ratio of 28 is high or low compared to Microsoft, Google, and Amazon.

```
Example: "Is AAPL expensive?"

Without peer comparison:
  AAPL P/E = 28.5 → "Compared to what? We don't know."

With peer comparison:
  AAPL P/E = 28.5
  MSFT P/E = 35.2
  GOOGL P/E = 24.1
  AMZN P/E = 62.3
  META P/E = 22.7
  Peer Median = 28.5
  → "AAPL is FAIRLY VALUED - right at the peer median"
```

#### Why It Matters

- **Relative valuation** is how professionals actually invest (not absolute numbers)
- Reveals if a stock is **cheap or expensive** vs. competitors
- Shows **competitive positioning** - who has better margins, growth, returns
- Currently the **biggest gap**: `compare_to_industry()` in `financial_metrics.py` uses hardcoded benchmarks for only 4 industries instead of real peer data
- Essential for: investment decisions, reports, observations, thematic analysis

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance | Existing | Financial data, sector/industry classification for peer discovery |
| yfinance sector/industry | Existing | Find peers by matching sector + industry + market cap range |
| Manual peer mapping | New (config) | Override automatic peer discovery for edge cases |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/peer_comparison.py` | Peer discovery, multi-stock comparison, percentile ranking |
| **MODIFY** | `src/agents/fundamental.py` | Integrate real peer comparison into analysis flow |
| **MODIFY** | `src/tools/financial_metrics.py` | Replace hardcoded `compare_to_industry()` with real peer data |
| **MODIFY** | `src/agents/orchestrator.py` | Include peer comparison data in workflow |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/peers/{symbol}` endpoint |
| **MODIFY** | `src/api/schemas.py` | Add peer comparison request/response schemas |

#### Key Metrics and Outputs

```json
{
  "target": "AAPL",
  "peer_group": ["MSFT", "GOOGL", "AMZN", "META"],
  "peer_selection_criteria": "Same sector (Technology), market cap > $500B",

  "comparison_table": {
    "pe_ratio":      {"AAPL": 28.5, "MSFT": 35.2, "GOOGL": 24.1, "AMZN": 62.3, "META": 22.7, "peer_median": 28.5},
    "pb_ratio":      {"AAPL": 45.2, "MSFT": 12.3, "GOOGL": 6.1,  "AMZN": 8.2,  "META": 7.5,  "peer_median": 8.2},
    "revenue_growth": {"AAPL": 8.2, "MSFT": 15.3, "GOOGL": 12.7, "AMZN": 11.8, "META": 23.1, "peer_median": 12.7},
    "net_margin":     {"AAPL": 25.3, "MSFT": 35.1, "GOOGL": 22.4, "AMZN": 5.1, "META": 28.7, "peer_median": 25.3},
    "roe":           {"AAPL": 147.3, "MSFT": 38.2, "GOOGL": 25.1, "AMZN": 15.8, "META": 22.4, "peer_median": 25.1}
  },

  "percentile_rankings": {
    "pe_ratio": "50th percentile (fairly valued)",
    "revenue_growth": "20th percentile (below peers)",
    "net_margin": "60th percentile (above average)",
    "roe": "100th percentile (best in class)"
  },

  "relative_valuation": {
    "premium_discount_to_median": "0% (at median)",
    "assessment": "Fairly valued relative to peers"
  },

  "strengths_vs_peers": [
    "Highest ROE in peer group (147.3% vs median 25.1%)",
    "Best net margin among hardware-exposed peers"
  ],
  "weaknesses_vs_peers": [
    "Lowest revenue growth (8.2% vs median 12.7%)",
    "Highest P/B ratio (45.2 vs median 8.2)"
  ]
}
```

#### Implementation Approach

1. Build `discover_peers(symbol, max_peers=10)`:
   - Use yfinance to get target's sector and industry
   - Find all stocks in same industry
   - Filter by market cap similarity (0.25x to 4x of target)
   - Return top 5-10 closest peers
2. Build `compare_peers(target, peer_symbols)`:
   - Fetch all metrics for target + peers in parallel
   - Compute peer median for each metric
   - Calculate percentile rank of target within peer group
   - Determine premium/discount to median
3. Replace `compare_to_industry()` hardcoded benchmarks with computed peer medians
4. Integrate into `FundamentalAnalystAgent.analyze()` as an additional step
5. Add peer comparison section to generated reports

#### Priority: P0 (Most Critical)

This is the **single most important gap** to fill. No dependencies, enriches every other feature, and the current implementation is a placeholder.

#### Dependencies

- None - can be built immediately using existing yfinance infrastructure

---

### Feature 3: Market Disruption Analysis

#### What It Is

**Simple explanation**: Analyzing whether a company is a **market disruptor** (like Tesla disrupting traditional automakers) or **at risk of being disrupted** (like Blockbuster being disrupted by Netflix). This combines quantitative financial signals with qualitative AI reasoning.

```
Disruptor signals:
  - High R&D spending (investing in innovation)
  - Rapid revenue growth (gaining market share)
  - New market creation (expanding the pie)
  - Technology leadership (patents, products)

At-risk signals:
  - Declining market share
  - Low R&D investment
  - Revenue deceleration
  - Industry being disrupted by new entrants
```

#### Why It Matters

- Disruption is the **primary driver of multi-bagger returns** (10x+) and catastrophic losses
- Identifies **asymmetric opportunities** early (e.g., investing in Netflix before Blockbuster collapsed)
- Warns about companies **at risk of displacement** (incumbents losing relevance)
- Combines **quantitative signals** (R&D spending, growth) with **qualitative AI reasoning** (competitive narrative)

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance financial statements | Existing | R&D spending, revenue growth, market cap trajectory |
| News articles | Existing | Competitive landscape, disruption narratives |
| yfinance company info | Existing | Sector, industry, business description |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/agents/disruption.py` | New `DisruptionAnalystAgent` |
| **CREATE** | `src/tools/disruption_metrics.py` | R&D intensity, innovation scoring, disruption indicators |
| **MODIFY** | `src/agents/orchestrator.py` | Add disruption analysis as optional workflow step |
| **MODIFY** | `src/agents/data_collector.py` | Collect R&D and competitive data |

#### Key Metrics and Outputs

```json
{
  "symbol": "TSLA",
  "disruption_score": 85,
  "classification": "Active Disruptor",

  "quantitative_signals": {
    "rd_intensity": {
      "rd_to_revenue_ratio": "5.2%",
      "trend": "Increasing (was 3.8% two years ago)",
      "vs_industry_average": "2x industry average"
    },
    "revenue_acceleration": {
      "yoy_growth": "45%",
      "growth_rate_of_change": "Accelerating",
      "assessment": "Rapid market share capture"
    },
    "gross_margin_trajectory": {
      "current": "25.6%",
      "2_years_ago": "21.0%",
      "trend": "Expanding (economies of scale)"
    }
  },

  "qualitative_assessment": {
    "competitive_moat": "Strong - vertical integration, brand, charging network",
    "disruption_vector": "EV transition + autonomous driving + energy storage",
    "incumbent_risk": "Traditional automakers (F, GM, TM) face margin compression",
    "innovation_pipeline": "FSD software, Cybertruck, Robotaxi, Optimus robot"
  },

  "risk_factors": [
    "Competition intensifying from legacy automakers",
    "Regulatory risk in autonomous driving",
    "Valuation already prices in disruption premium"
  ]
}
```

#### Implementation Approach

1. Extract R&D data from yfinance financial statements (already available via `get_financial_statements()`)
2. Compute quantitative disruption signals:
   - R&D/Revenue ratio and its trend over 3-5 years
   - Revenue growth rate of change (acceleration vs deceleration)
   - Gross margin expansion (indicator of competitive advantage)
3. Use the LLM to synthesize disruption narrative from:
   - News articles about competitive landscape
   - Company description and business model
   - Financial trajectory (growth, margins, R&D)
4. Create scoring framework: Disruptor (70+), Moderate Innovator (40-70), At Risk (<40)
5. Output classification with supporting evidence

#### Priority: P2

High value but heavily **LLM-dependent** and harder to validate quantitatively. Best built after foundational features are solid.

#### Dependencies

- Feature 9 (Enhanced News) - For competitive intelligence from news
- Feature 2 (Peer Comparison) - For competitive context and market share estimation

---

### Feature 4: Quarterly Earnings Analysis

#### What It Is

**Simple explanation**: Every public company reports its financial results **4 times per year** (quarterly). Each earnings report includes:

```
What investors look at in quarterly earnings:

1. EPS (Earnings Per Share): How much profit per share?
   Actual: $1.52  vs  Estimated: $1.45  →  Beat by $0.07 (4.8% surprise)

2. Revenue: How much money did the company make?
   Actual: $94.9B  vs  Estimated: $92.3B  →  Beat by $2.6B (2.8% surprise)

3. Guidance: What does management expect NEXT quarter?
   "We expect revenue of $97-99B next quarter" (vs $95B consensus)

4. Trends: Is the company growing or shrinking?
   Q1: $85B → Q2: $88B → Q3: $91B → Q4: $94.9B  →  Accelerating!
```

This feature analyzes all 4 quarterly earnings per year, tracks trends, and identifies patterns.

#### Why It Matters

- Earnings are the **single most important fundamental driver** of stock prices
- Earnings surprises cause the **biggest single-day price moves** (5-20% swings)
- **Trend analysis** across quarters reveals if a company is accelerating or decelerating
- **Beat/miss patterns** help predict future earnings reactions
- Currently **completely missing** from the system despite being fundamental financial data

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance `quarterly_income_stmt` | Existing | Revenue, net income, EBITDA by quarter |
| yfinance `quarterly_earnings` | Existing | EPS actual vs estimate, surprise |
| yfinance `earnings_dates` | Existing | Past and upcoming earnings dates |
| yfinance `analyst_price_targets` | Existing | Forward estimates |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/agents/earnings.py` | New `EarningsAnalystAgent` |
| **CREATE** | `src/tools/earnings_data.py` | Fetch quarterly data, compute surprises, trends |
| **MODIFY** | `src/agents/data_collector.py` | Include earnings data in comprehensive collection |
| **MODIFY** | `src/agents/orchestrator.py` | Add earnings analysis to workflow |
| **MODIFY** | `src/agents/fundamental.py` | Incorporate quarterly trends |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/earnings/{symbol}` |
| **MODIFY** | `src/api/schemas.py` | Add earnings request/response schemas |

#### Key Metrics and Outputs

```json
{
  "symbol": "AAPL",
  "last_4_quarters": [
    {
      "quarter": "Q4 2025",
      "date": "2025-10-30",
      "eps_actual": 1.64,
      "eps_estimate": 1.60,
      "eps_surprise_pct": 2.5,
      "revenue_actual": 94900000000,
      "revenue_estimate": 92300000000,
      "revenue_surprise_pct": 2.8,
      "verdict": "BEAT"
    },
    {
      "quarter": "Q3 2025",
      "eps_actual": 1.40,
      "eps_estimate": 1.35,
      "eps_surprise_pct": 3.7,
      "verdict": "BEAT"
    }
  ],

  "earnings_surprise_history": {
    "last_8_quarters": {
      "beats": 7,
      "misses": 0,
      "inline": 1,
      "average_surprise": "+3.2%",
      "pattern": "Consistent beater"
    }
  },

  "quarterly_trends": {
    "revenue_qoq_growth": ["+2.1%", "+3.4%", "+4.1%", "+4.3%"],
    "revenue_trend": "Accelerating",
    "eps_qoq_growth": ["+1.8%", "+2.5%", "+3.0%", "+3.7%"],
    "eps_trend": "Accelerating",
    "margin_trajectory": "Expanding"
  },

  "yoy_comparison": {
    "q4_2025_vs_q4_2024": {
      "revenue_growth": "+8.2%",
      "eps_growth": "+12.1%"
    }
  },

  "next_earnings": {
    "date": "2026-01-30",
    "eps_estimate": 2.35,
    "revenue_estimate": 124500000000,
    "days_until": 15
  },

  "earnings_quality": {
    "score": 8.5,
    "assessment": "High quality - driven by operations, not one-time items"
  }
}
```

#### Implementation Approach

1. Use `yf.Ticker(symbol).quarterly_income_stmt` for quarterly financial data
2. Use `yf.Ticker(symbol).quarterly_earnings` for EPS actual vs estimate
3. Use `yf.Ticker(symbol).earnings_dates` for past and upcoming dates
4. Compute surprise metrics: `(actual - estimate) / abs(estimate) * 100`
5. Calculate QoQ (quarter-over-quarter) and YoY (year-over-year) growth
6. Track beat/miss pattern across last 8 quarters
7. Use LLM to assess earnings quality (operational vs one-time)
8. Link to Feature 7 for stock price reaction on earnings day

#### Priority: P0

Quarterly earnings are **foundational financial data**. Many other features (event performance, observations, reports) depend on having this data available.

#### Dependencies

- None for basic implementation
- Feature 5 (Stock Performance) - For earnings day price reaction
- Feature 7 (Event Performance) - For before/after analysis around earnings

---

### Feature 5: Historical Stock Performance Tracking

#### What It Is

**Simple explanation**: Comprehensive tracking of how a stock has performed over different time periods, compared to benchmarks (like the S&P 500) and peers.

```
"How has AAPL performed?"

Time-based returns:
  1 Day:  +1.2%
  1 Week: +3.5%
  1 Month: +7.8%
  3 Month: +12.4%
  YTD:     +18.9%
  1 Year:  +32.1%
  3 Year:  +85.4%

vs Benchmarks:
  vs S&P 500:      +12.3% better (outperforming)
  vs Nasdaq:       +5.1% better
  vs Tech Sector:  +2.8% better

Risk-Adjusted:
  Beta:    1.15 (15% more volatile than market)
  Sortino: 1.8  (good downside-risk-adjusted return)
```

#### Why It Matters

- Answers the **most fundamental question**: "How has this stock done?"
- **Benchmark comparison** shows if a stock is outperforming or underperforming the market
- **Risk-adjusted returns** reveal if high returns came with acceptable risk
- Currently: `get_historical_data()` returns raw prices but **no computed performance metrics**
- Fills critical gaps: **Beta and Sortino** are listed in `config/agents.yaml` but not implemented in `risk.py`

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance historical data | Existing | Stock price history (already implemented) |
| yfinance benchmark data | Enhancement | SPY, QQQ, sector ETF data for comparison |
| yfinance adjusted close | Existing | Dividend-adjusted returns for accuracy |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/performance_tracker.py` | Multi-horizon returns, benchmark comparison, rolling returns |
| **MODIFY** | `src/agents/risk.py` | Implement Beta and Sortino (currently missing despite being in `agents.yaml`) |
| **MODIFY** | `src/agents/technical.py` | Include performance summary in analysis output |
| **MODIFY** | `src/tools/market_data.py` | Add `get_benchmark_data()` for SPY, QQQ, sector ETFs |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/performance/{symbol}` |

#### Key Metrics and Outputs

```json
{
  "symbol": "AAPL",

  "absolute_returns": {
    "1_day": "+1.2%",
    "1_week": "+3.5%",
    "1_month": "+7.8%",
    "3_month": "+12.4%",
    "6_month": "+22.1%",
    "ytd": "+18.9%",
    "1_year": "+32.1%",
    "3_year": "+85.4%",
    "5_year": "+210.5%"
  },

  "benchmark_comparison": {
    "vs_spy": {
      "1_year_alpha": "+12.3%",
      "assessment": "Outperforming S&P 500"
    },
    "vs_qqq": {
      "1_year_alpha": "+5.1%",
      "assessment": "Outperforming Nasdaq"
    },
    "vs_sector_etf_xlk": {
      "1_year_alpha": "+2.8%",
      "assessment": "Outperforming Tech sector"
    }
  },

  "risk_adjusted_metrics": {
    "beta": {
      "value": 1.15,
      "interpretation": "15% more volatile than S&P 500"
    },
    "sortino_ratio": {
      "value": 1.8,
      "rating": "Good (above 1.0 is positive)"
    },
    "sharpe_ratio": {
      "value": 1.5,
      "rating": "Good"
    }
  },

  "rolling_returns": {
    "30_day_rolling": ["+2.1%", "+3.5%", "+1.8%", "+4.2%"],
    "trend": "Stable positive momentum"
  },

  "drawdown_analysis": {
    "max_drawdown": "-15.3%",
    "max_drawdown_date": "2025-08-15",
    "recovery_days": 22,
    "current_drawdown": "-2.1%"
  },

  "dividend_adjusted_total_return": {
    "1_year": "+33.8%",
    "dividend_contribution": "+1.7%"
  }
}
```

#### Implementation Approach

1. Create `calculate_performance(symbol, benchmarks=["SPY", "QQQ"])`:
   - Fetch price data for stock and all benchmarks
   - Compute returns for standard horizons (1D through 5Y)
   - Handle weekends/holidays correctly
2. Implement **Beta** (currently missing from `risk.py`):

   ```
   Beta = Covariance(stock_returns, market_returns) / Variance(market_returns)
   ```

3. Implement **Sortino** (currently missing from `risk.py`):

   ```
   Sortino = (Mean Return - Risk-Free Rate) / Downside Deviation
   ```

   Where downside deviation only considers negative returns
4. Add rolling return windows (30/60/90 day) for trend visualization
5. Compute dividend-adjusted total returns using yfinance adjusted close
6. Integrate into `RiskAnalystAgent` to fill the Beta/Sortino gaps

#### Priority: P0

**Foundational data** that 4+ other features depend on. Also fills critical gaps in existing risk analysis (Beta, Sortino are listed in config but not implemented).

#### Dependencies

- None - can be built immediately using existing yfinance infrastructure

---

### Feature 6: Enhanced Multi-Format Reports

#### What It Is

**Simple explanation**: Currently the system generates reports only in **JSON format** (raw data). This feature adds professional-grade reports in **PDF, Markdown, and HTML** with charts, tables, and structured sections.

```
Current State:
  Report = JSON blob → Hard to read, no charts, no formatting

Enhanced State:
  PDF Report:
    ┌─────────────────────────────────────┐
    │  📊 Investment Research Report      │
    │  Apple Inc. (AAPL)                  │
    │                                     │
    │  [Price Chart with Indicators]      │
    │  [Peer Comparison Table]            │
    │  [Earnings History Chart]           │
    │                                     │
    │  Recommendation: BUY               │
    │  Confidence: 85%                    │
    │  Target Price: $195.00              │
    └─────────────────────────────────────┘
```

#### Why It Matters

- Professional reports are how analysis gets **consumed by stakeholders**
- PDF reports are the **standard format** for sharing with clients and teams
- Charts and visualizations make data **actionable at a glance**
- Currently: `agents.yaml` lists JSON, Markdown, PDF, HTML but **only JSON works**
- Libraries (`plotly`, `matplotlib`, `reportlab`) are already in `requirements.txt` but unused

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| All agent analysis results | Existing | Content for reports |
| plotly / matplotlib | Existing (in requirements.txt) | Chart generation |
| reportlab | Existing (in requirements.txt) | PDF generation |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/report_formatter.py` | PDF, Markdown, HTML generation engines |
| **CREATE** | `src/tools/chart_generator.py` | Price charts, indicator overlays, comparison charts |
| **MODIFY** | `src/agents/report_generator.py` | Major overhaul to support multiple output formats |
| **MODIFY** | `src/api/routes.py` | Update `POST /reports` to return correct format |
| **MODIFY** | `src/api/schemas.py` | Update `ReportResponse` for binary content (PDF) |

#### Key Metrics and Outputs

**PDF Report Structure:**

```
1. Cover Page
   - Stock symbol, company name, date
   - Report type, analyst info

2. Executive Summary
   - Recommendation (BUY/SELL/HOLD)
   - Confidence score, target price
   - 3-bullet key findings

3. Technical Analysis Section
   - Price chart with RSI, MACD overlays
   - Support/resistance levels marked
   - Signal summary table

4. Fundamental Analysis Section
   - Key ratios table
   - Peer comparison chart (bar chart)
   - DCF valuation summary

5. Earnings Analysis Section (Feature 4)
   - Quarterly earnings history chart
   - Beat/miss pattern
   - Next earnings date

6. Sentiment Analysis Section
   - Sentiment gauge (positive/negative)
   - News summary with sentiment scores
   - Trend chart

7. Risk Analysis Section
   - Risk metrics dashboard
   - Drawdown chart
   - Risk/reward assessment

8. Key Observations (Feature 11)
   - Top 5 ranked observations
   - Cross-dimensional insights

9. Disclaimer
   - Not financial advice
   - Data sources and methodology
```

#### Implementation Approach

1. Create `ChartGenerator` class using plotly:
   - `generate_price_chart(data, indicators)` - Candlestick with overlays
   - `generate_comparison_chart(symbols, metric)` - Bar chart for peer comparison
   - `generate_earnings_chart(quarters)` - Earnings history bar chart
   - `generate_risk_gauge(metrics)` - Risk dashboard visualization
2. Create `ReportFormatter` class:
   - `to_pdf(analysis_data)` - Uses reportlab for professional PDF layout
   - `to_markdown(analysis_data)` - Structured markdown with tables
   - `to_html(analysis_data)` - HTML with embedded plotly interactive charts
   - `to_json(analysis_data)` - Enhanced structured JSON (already exists, improve)
3. Wire up `ReportGeneratorAgent` to use formatter based on `format` parameter
4. Update API `/reports` endpoint to serve binary content for PDF

#### Priority: P1

High-value user-facing feature. Libraries are already installed but nothing is implemented. This is a direct gap between what's advertised and what's delivered.

#### Dependencies

- All analysis agents should be working (they are, at basic level)
- Feature 4 (Earnings) - Adds earnings section to report
- Feature 2 (Peer Comparison) - Adds comparison charts
- Feature 5 (Performance) - Adds performance charts

---

### Feature 7: Event-Driven Performance Analysis

#### What It Is

**Simple explanation**: Analyzing stock price performance in the **window around significant events**, primarily earnings announcements. Specifically: how did the stock perform **1 week before** and **1 week after** an event?

```
Example: AAPL Earnings on Jan 30, 2026

Timeline:
  Jan 23 (1 week before): $180.00
  Jan 29 (1 day before):  $183.50  → Pre-earnings drift: +1.9%
  Jan 30 (earnings day):  $189.00  → Earnings day: +3.0%
  Jan 31 (1 day after):   $191.20  → Next day: +1.2%
  Feb 6  (1 week after):  $188.50  → 1 week after: -0.3%

Insight: "AAPL typically rallies +2-3% into earnings
          and gives back ~1% the following week"
```

This is what the user's note "Weekly performance 1 week after & before" refers to.

#### Why It Matters

- Reveals **pre-event drift** (market pricing in expectations)
- Quantifies **market reaction** to events (post-event move)
- Identifies **repeating patterns** (does this stock always rally before earnings?)
- Enables **event-driven trading strategies** (buy before, sell after)
- Directly requested by user in their notes

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance historical prices | Existing | Price data around events |
| yfinance `earnings_dates` | Existing | Earnings event calendar |
| yfinance dividend dates | Existing | Ex-dividend date calendar |
| News with timestamps | Enhancement | Non-earnings event detection |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/event_analyzer.py` | Event identification, price window extraction, pattern analysis |
| **MODIFY** | `src/agents/earnings.py` (Feature 4) | Incorporate event-driven price analysis |
| **MODIFY** | `src/agents/technical.py` | Identify pre-event patterns in technical signals |
| **MODIFY** | `src/agents/data_collector.py` | Collect event calendar data |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/events/{symbol}` |

#### Key Metrics and Outputs

```json
{
  "symbol": "AAPL",
  "event_type": "earnings",

  "events": [
    {
      "date": "2025-10-30",
      "quarter": "Q4 2025",
      "eps_surprise": "+4.8%",

      "price_window": {
        "5_days_before": 178.50,
        "1_day_before": 182.30,
        "event_day_open": 183.00,
        "event_day_close": 189.50,
        "1_day_after": 191.20,
        "5_days_after": 188.50
      },

      "returns": {
        "pre_event_5d": "+2.1%",
        "event_day": "+3.6%",
        "post_event_1d": "+0.9%",
        "post_event_5d": "-0.5%",
        "full_window_10d": "+5.6%"
      }
    }
  ],

  "historical_patterns": {
    "events_analyzed": 8,
    "average_pre_event_drift": "+1.8%",
    "average_event_day_move": "+2.5%",
    "average_post_event_5d": "-0.3%",
    "consistency": "High - 7 of 8 events show pre-earnings rally",
    "pattern": "Buy 5 days before earnings, sell on earnings day"
  },

  "correlation_with_surprise": {
    "correlation": 0.72,
    "insight": "Larger EPS beats correlate with larger event-day moves"
  }
}
```

#### Implementation Approach

1. Build `get_event_calendar(symbol)` that pulls earnings dates, dividend dates, split dates from yfinance
2. Build `calculate_event_window(symbol, event_date, days_before=5, days_after=5)`:
   - Extract exact price data for the window (handling weekends/holidays)
   - Compute returns for each segment: pre-event, event-day, post-event
3. Aggregate across 8+ historical events to find patterns
4. For earnings events, correlate surprise magnitude with price reaction
5. Add statistical significance test (is the pattern real or random?)
6. Use LLM to generate actionable insight from the pattern

#### Priority: P1

**Explicitly requested** in user's notes. High user interest. Depends on earnings data and performance tracking.

#### Dependencies

- Feature 4 (Quarterly Earnings) - For earnings event dates and surprise data
- Feature 5 (Stock Performance) - For return calculations

---

### Feature 8: Backtesting Engine

#### What It Is

**Simple explanation**: Testing trading strategies against **historical data** to see how they would have performed in the past. Like a "what if" time machine for trading.

```
Strategy: "Buy when RSI drops below 30, sell when it goes above 70"
Period: January 2021 - January 2026 (5 years)
Symbol: AAPL

Result:
  Total Trades: 12
  Wins: 8 (66.7% win rate)
  Losses: 4
  Total Return: +45.3%
  Buy & Hold Return: +72.1%
  Max Drawdown: -18.5%
  Sharpe Ratio: 1.2

  Verdict: Strategy works but underperforms buy-and-hold.
           Better suited for range-bound markets.
```

#### Why It Matters

- **Validates** whether technical signals actually produce profitable trades
- Provides **evidence-based confidence** in recommendations (not just theory)
- Reveals strategy **weaknesses** (drawdowns, losing streaks, whipsaws)
- Transforms the agent from "analysis only" to **"actionable strategy validation"**
- Significant competitive differentiation from other analysis tools

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance historical data | Existing | Long-term OHLCV data (5Y, 10Y) |
| Technical indicators | Existing | RSI, MACD, MA calculations for signal generation |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/agents/backtesting.py` | New `BacktestingAgent` |
| **CREATE** | `src/tools/backtesting_engine.py` | Strategy simulation, trade log, performance metrics |
| **CREATE** | `src/tools/strategy_definitions.py` | Predefined strategies (RSI, MACD, MA crossover) |
| **MODIFY** | `src/agents/technical.py` | Expose signal history (not just current values) |
| **MODIFY** | `src/api/routes.py` | Add `POST /api/v1/backtest` |
| **MODIFY** | `src/api/schemas.py` | Add backtest request/response schemas |

#### Predefined Strategies

```python
# Strategy 1: RSI Reversal
Buy when:  RSI < 30 (oversold)
Sell when: RSI > 70 (overbought)

# Strategy 2: MACD Crossover
Buy when:  MACD line crosses ABOVE signal line
Sell when: MACD line crosses BELOW signal line

# Strategy 3: Golden/Death Cross
Buy when:  50-day SMA crosses ABOVE 200-day SMA (golden cross)
Sell when: 50-day SMA crosses BELOW 200-day SMA (death cross)

# Strategy 4: Bollinger Band Mean Reversion
Buy when:  Price touches lower Bollinger Band
Sell when: Price touches upper Bollinger Band

# Strategy 5: Momentum
Buy when:  Price > 200 SMA AND RSI > 50 AND MACD positive
Sell when: Price < 200 SMA OR RSI < 40
```

#### Key Metrics and Outputs

```json
{
  "strategy": "RSI Reversal",
  "symbol": "AAPL",
  "period": "2021-01-01 to 2026-01-01",
  "initial_capital": 10000,

  "trade_log": [
    {
      "entry_date": "2021-03-05",
      "entry_price": 121.42,
      "exit_date": "2021-04-15",
      "exit_price": 134.72,
      "return": "+11.0%",
      "holding_days": 41
    }
  ],

  "performance": {
    "total_return": "+45.3%",
    "annualized_return": "+7.8%",
    "buy_and_hold_return": "+72.1%",
    "excess_return": "-26.8% (underperforms buy & hold)",
    "total_trades": 12,
    "win_rate": "66.7%",
    "average_win": "+8.5%",
    "average_loss": "-3.2%",
    "profit_factor": 2.1,
    "max_drawdown": "-18.5%",
    "sharpe_ratio": 1.2,
    "sortino_ratio": 1.6
  },

  "annual_breakdown": {
    "2021": "+12.3%",
    "2022": "-8.5%",
    "2023": "+18.2%",
    "2024": "+15.1%",
    "2025": "+8.2%"
  },

  "verdict": "Strategy profitable but underperforms buy-and-hold. Better in sideways markets.",

  "risk_metrics": {
    "worst_drawdown": "-18.5%",
    "longest_drawdown_days": 45,
    "recovery_time_days": 30,
    "max_consecutive_losses": 2
  }
}
```

#### Implementation Approach

1. Define `Strategy` base class:

   ```
   generate_signals(price_data, indicators) → List of BUY/SELL signals with dates
   ```

2. Implement 5 predefined strategies using existing technical indicator tools
3. Build backtesting engine:
   - Iterate through historical data day-by-day
   - Apply strategy rules at each step
   - Track entry/exit with configurable commission (0.1%) and slippage (0.05%)
   - Maintain portfolio state and equity curve
4. Compute all performance metrics from trade log
5. Generate equity curve chart for visualization
6. LLM summarizes backtest results with actionable insights

#### Priority: P2

Complex feature with significant engineering effort. Very high value but requires solid foundational features to be useful.

#### Dependencies

- Feature 5 (Stock Performance) - For benchmark comparison
- Technical indicators (existing) - For strategy signals
- Feature 6 (Enhanced Reports) - For visualizing backtest results and equity curves

---

### Feature 9: Enhanced News and Sentiment Analysis

#### What It Is

**Simple explanation**: Upgrading from basic text sentiment to **financial-domain AI** (FinBERT), adding multiple news sources, and measuring how news actually impacts stock prices.

```
Current State (TextBlob):
  News: "Apple reported strong Q4 earnings beating estimates"
  TextBlob: "positive" (score: 0.3)  → Generic, low confidence

Enhanced State (FinBERT):
  News: "Apple reported strong Q4 earnings beating estimates"
  FinBERT: "positive" (score: 0.92) → Financial-domain, high confidence

  + News Impact: This type of article historically causes +2.3% next-day move
  + Volume: 15 articles in 24 hours (3x normal = significant event)
  + Trend: Sentiment improving from 0.45 → 0.72 over past 2 weeks
```

#### Why It Matters

- TextBlob is **not designed for financial text** (misclassifies financial jargon like "beat estimates" or "cut forecast")
- FinBERT (trained on financial text) is **dramatically more accurate** for financial sentiment
- **News impact measurement** quantifies how news actually moves prices
- Current implementation is effectively **non-functional**: sentiment endpoint returns hardcoded data, news fetcher falls back to 3 sample articles
- `transformers` library is already in `requirements.txt` but unused for sentiment

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance company news | Existing | Basic news articles |
| NewsAPI | Existing (configured, fallback to samples) | Multi-source news aggregation |
| FinBERT model | New | Financial-domain sentiment (`ProsusAI/finbert` on HuggingFace) |
| GNews API | New (in `.env.example`) | Additional news source |
| RSS feeds | New | Financial news from major outlets |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/sentiment_engine.py` | FinBERT-based sentiment, entity extraction, topic classification |
| **CREATE** | `src/tools/news_impact.py` | News-price correlation, impact scoring |
| **MODIFY** | `src/agents/sentiment.py` | Major overhaul: replace TextBlob with FinBERT, multi-source |
| **MODIFY** | `src/tools/news_fetcher.py` | Add RSS feeds, GNews, multiple fallback sources, deduplication |
| **MODIFY** | `src/api/routes.py` | Replace hardcoded sentiment endpoint with real analysis |
| **MODIFY** | `src/config.py` | Add sentiment engine configuration |

#### Key Metrics and Outputs

```json
{
  "symbol": "AAPL",

  "aggregate_sentiment": {
    "score": 0.72,
    "label": "Positive",
    "confidence": 0.89,
    "articles_analyzed": 25,
    "time_weighted_score": 0.68
  },

  "sentiment_trend": {
    "1_week_ago": 0.45,
    "3_days_ago": 0.58,
    "current": 0.72,
    "direction": "Improving",
    "momentum": "Strong positive shift"
  },

  "news_volume": {
    "last_24h": 15,
    "average_24h": 5,
    "spike_detected": true,
    "spike_assessment": "3x normal volume - significant event coverage"
  },

  "top_articles": [
    {
      "title": "Apple Reports Record Q4 Earnings",
      "source": "Reuters",
      "published": "2026-01-30T16:00:00Z",
      "sentiment": {
        "label": "Positive",
        "score": 0.94,
        "confidence": 0.97
      },
      "key_topics": ["earnings", "revenue", "services growth"],
      "estimated_impact": "+2.3% next-day move"
    }
  ],

  "news_impact_analysis": {
    "historical_correlation": 0.68,
    "positive_news_avg_impact": "+1.8% next day",
    "negative_news_avg_impact": "-2.5% next day",
    "current_prediction": "Positive sentiment suggests +1.5% potential"
  },

  "source_diversity": {
    "unique_sources": 8,
    "source_list": ["Reuters", "Bloomberg", "CNBC", "WSJ", "MarketWatch"],
    "assessment": "Broad coverage from multiple independent sources"
  }
}
```

#### Implementation Approach

1. Integrate FinBERT from HuggingFace:

   ```python
   from transformers import AutoTokenizer, AutoModelForSequenceClassification
   model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
   ```

   (`transformers` is already in requirements.txt)
2. Build `FinancialSentimentAnalyzer` class:
   - Batch process articles through FinBERT
   - Return per-article scores with confidence
   - Compute time-weighted aggregate (recent articles weighted more)
3. Expand `news_fetcher.py`:
   - Add fallback chain: yfinance news -> NewsAPI -> GNews -> RSS feeds
   - Add deduplication via title similarity (using sentence-transformers, already available)
   - Track article timestamps for volume analysis
4. Build news-price correlation:
   - For each article, measure price change in 24h after publication
   - Build historical correlation model
5. Replace hardcoded sentiment endpoint in `routes.py` with real analysis
6. Add caching for FinBERT results (model inference is expensive)

#### Priority: P0

Current sentiment implementation is **effectively non-functional** (TextBlob on financial text + hardcoded API responses). This is a critical quality gap.

#### Dependencies

- None for basic FinBERT integration
- Feature 5 (Stock Performance) - For news impact scoring
- Feature 7 (Event Analysis) - For correlating news with price moves

---

### Feature 10: Bloomberg-like Terminal

#### What It Is

**Simple explanation**: A real-time or near-real-time **market command center** that provides at-a-glance market overview, sector heatmaps, watchlists, and market breadth. Think of a simplified Bloomberg Terminal accessible via API.

```
┌──────────────────────────────────────────────────┐
│  📊 MARKET TERMINAL                              │
├──────────────────────────────────────────────────┤
│                                                  │
│  Major Indices:                                  │
│  SPY  $512.30  +0.8%  ▲   QQQ  $445.10  +1.2% ▲│
│  DIA  $395.50  +0.3%  ▲   IWM  $210.80  -0.2% ▼│
│                                                  │
│  Sector Heatmap:                                 │
│  Tech    +1.5% ███████████                       │
│  Health  +0.8% ████████                          │
│  Energy  -0.3% ███                               │
│  Finance +0.5% ██████                            │
│                                                  │
│  Market Breadth:                                 │
│  Advancing: 312  Declining: 188                  │
│  New Highs: 45   New Lows: 12                    │
│  % Above 200 SMA: 68%                           │
│                                                  │
│  VIX: 15.2 (Low Fear)                            │
│  Top Gainer: NVDA +5.2%                          │
│  Top Loser:  INTC -3.1%                          │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### Why It Matters

- Provides the **"command center" experience** for monitoring markets
- Aggregates multiple data views into a **single interface**
- The existing `/market/summary` endpoint returns **hardcoded static data**
- Enables **real-time monitoring** and alerting
- Professional traders need this level of market awareness

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance | Existing | Index and ETF quotes (rate-limited) |
| Finnhub WebSocket | New (API key in `.env.example`) | Real-time streaming quotes |
| Sector ETFs (XLF, XLK, XLV, etc.) | Enhancement | Sector performance data |
| Redis | Existing (in requirements/config) | Caching and pub/sub for real-time |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/market_terminal.py` | Market overview, sector heatmap, breadth, watchlist |
| **CREATE** | `src/tools/streaming_data.py` | WebSocket connection to Finnhub (optional) |
| **MODIFY** | `src/tools/market_data.py` | Add index data, sector ETF data, market breadth |
| **MODIFY** | `src/api/routes.py` | Replace hardcoded market summary + add terminal endpoints |

#### Key Metrics and Outputs

```json
{
  "market_overview": {
    "indices": {
      "SPY": {"price": 512.30, "change_pct": 0.8, "volume": "85M"},
      "QQQ": {"price": 445.10, "change_pct": 1.2, "volume": "62M"},
      "DIA": {"price": 395.50, "change_pct": 0.3, "volume": "15M"},
      "IWM": {"price": 210.80, "change_pct": -0.2, "volume": "32M"}
    },
    "timestamp": "2026-02-07T15:30:00Z",
    "market_status": "open"
  },

  "sector_heatmap": {
    "XLK": {"name": "Technology", "change_pct": 1.5},
    "XLV": {"name": "Healthcare", "change_pct": 0.8},
    "XLF": {"name": "Financials", "change_pct": 0.5},
    "XLE": {"name": "Energy", "change_pct": -0.3},
    "XLY": {"name": "Consumer Discretionary", "change_pct": 1.1},
    "XLP": {"name": "Consumer Staples", "change_pct": 0.2},
    "XLI": {"name": "Industrials", "change_pct": 0.7},
    "XLB": {"name": "Materials", "change_pct": -0.1},
    "XLRE": {"name": "Real Estate", "change_pct": -0.4},
    "XLU": {"name": "Utilities", "change_pct": 0.1},
    "XLC": {"name": "Communication", "change_pct": 1.3}
  },

  "market_breadth": {
    "advancing": 312,
    "declining": 188,
    "unchanged": 0,
    "advance_decline_ratio": 1.66,
    "new_52w_highs": 45,
    "new_52w_lows": 12,
    "pct_above_200_sma": 68,
    "assessment": "Healthy breadth - broad participation in rally"
  },

  "fear_greed": {
    "vix": 15.2,
    "vix_assessment": "Low fear",
    "put_call_ratio": 0.85,
    "assessment": "Market is complacent - moderate risk"
  },

  "movers": {
    "top_gainers": [
      {"symbol": "NVDA", "change_pct": 5.2, "price": 890.50},
      {"symbol": "TSLA", "change_pct": 3.8, "price": 245.30}
    ],
    "top_losers": [
      {"symbol": "INTC", "change_pct": -3.1, "price": 42.50}
    ]
  }
}
```

#### API Endpoints

```
GET  /api/v1/terminal/overview   → Market summary with real data
GET  /api/v1/terminal/sectors    → Sector heatmap
GET  /api/v1/terminal/breadth    → Market breadth indicators
GET  /api/v1/terminal/movers     → Top gainers/losers
GET  /api/v1/terminal/watchlist  → User's watchlist
WS   /api/v1/terminal/stream    → WebSocket for real-time updates (Phase 2)
```

#### Implementation Approach

1. **Phase 1**: Replace hardcoded `/market/summary` with real data from yfinance
   - Fetch SPY, QQQ, DIA, IWM for market overview
   - Fetch all 11 sector ETFs for heatmap
   - Add VIX for fear/greed
2. **Phase 2**: Add market breadth
   - Analyze S&P 500 components: advance/decline, % above 200 SMA
   - Track new 52-week highs/lows
3. **Phase 3** (optional): Add Finnhub WebSocket for real-time streaming
   - Use Redis pub/sub for distributing updates
   - Build WebSocket endpoint in FastAPI

#### Priority: P2

Largest scope, best delivered **incrementally**. Phase 1 (replace hardcoded data) is quick and high-value.

#### Dependencies

- Feature 5 (Stock Performance) - For benchmark data infrastructure
- Redis infrastructure (configured but not utilized in codebase)
- Finnhub API key for real-time data (optional)

---

### Feature 11: Key Observations and Insights

#### What It Is

**Simple explanation**: An intelligent **synthesis engine** that looks at ALL analysis results and identifies the **most important things an investor should know**. Instead of overwhelming users with raw data, it answers: **"What should I pay attention to?"**

```
Raw Data Overload (Current):
  RSI: 32.5
  MACD: Positive crossover
  P/E: 18.2
  Peer median P/E: 25.0
  Earnings: Beat by 5%
  Sentiment: 0.78
  Insider buying: $2.3M last month
  ... 50 more data points ...

Key Observations (Enhanced):
  🔴 CRITICAL: RSI oversold (32.5) + MACD bullish crossover
     = Strong technical reversal signal

  🟢 HIGH: Trading at 27% P/E discount to peers (18.2 vs 25.0)
     + Earnings beat by 5% = Undervalued with positive momentum

  🟡 MEDIUM: Insider buying $2.3M while sentiment is positive
     = Smart money aligning with market sentiment

  ⚪ WATCH: Revenue growth decelerating (15% → 12% → 8.2%)
     = Monitor if growth stabilizes or continues declining
```

#### Why It Matters

- **Raw data overload** is the biggest problem in financial analysis
- Professionals value the **"so what?"** - not just numbers but interpretation
- **Cross-dimensional insights** are more powerful than individual metrics
  - Example: "RSI oversold" + "earnings beat" + "insider buying" = much stronger signal than any one alone
- This is where the **LLM adds unique value** - connecting dots across different analysis types
- Acts as the **capstone** that makes the entire system more useful

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| All agent outputs | Existing | No new external data needed |

This is purely a **synthesis/intelligence layer** that consumes all other analysis results.

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/agents/observations.py` | New `ObservationsAgent` |
| **CREATE** | `src/tools/insight_engine.py` | Cross-reference analyses, detect anomalies, rank insights |
| **MODIFY** | `src/agents/orchestrator.py` | Run observations as FINAL step (after all analyses) |
| **MODIFY** | `src/agents/report_generator.py` | Include "Key Observations" section in reports |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/observations/{symbol}` |

#### Observation Categories

| Category | Icon | Example |
|---|---|---|
| **Bullish Signal** | 🟢 | "Technical reversal + earnings beat = buy signal" |
| **Bearish Signal** | 🔴 | "Broken support + declining margins = sell signal" |
| **Risk Warning** | ⚠️ | "VaR exceeded + high correlation to sector = elevated risk" |
| **Opportunity** | 💡 | "P/E discount to peers + positive sentiment = value opportunity" |
| **Anomaly** | 🔍 | "Insider selling despite positive earnings = investigate" |
| **Watch Item** | 👁️ | "Revenue deceleration not yet critical but trending wrong" |

#### Key Metrics and Outputs

```json
{
  "symbol": "AAPL",

  "observations": [
    {
      "rank": 1,
      "severity": "Critical",
      "category": "Bullish Signal",
      "title": "Technical Reversal Signal with Fundamental Confirmation",
      "observation": "RSI at 32.5 (oversold) with a fresh MACD bullish crossover, while trading at a 27% P/E discount to peers. This confluence of technical and fundamental signals historically precedes a 10-15% rally.",
      "supporting_evidence": [
        "RSI: 32.5 (oversold < 30 zone)",
        "MACD: Bullish crossover as of yesterday",
        "P/E: 18.2 vs peer median 25.0 (27% discount)",
        "Last 3 similar setups resulted in +12%, +8%, +15% over 30 days"
      ],
      "confidence": 0.82,
      "actionability": "High - Consider entry with stop-loss at support $175"
    },
    {
      "rank": 2,
      "severity": "High",
      "category": "Opportunity",
      "title": "Earnings Momentum Diverging from Valuation",
      "observation": "AAPL has beaten earnings estimates for 7 consecutive quarters with an average surprise of +3.2%, yet trades at a 27% discount to peer median P/E. This suggests the market has not fully priced in the earnings trajectory.",
      "supporting_evidence": [
        "Earnings beats: 7/8 last quarters",
        "Avg surprise: +3.2%",
        "P/E discount: 27% below peers"
      ],
      "confidence": 0.75,
      "actionability": "Medium - Valuation gap may close over 3-6 months"
    },
    {
      "rank": 3,
      "severity": "Medium",
      "category": "Watch Item",
      "title": "Revenue Growth Deceleration",
      "observation": "Revenue growth has decelerated from 15% to 12% to 8.2% over the last 3 quarters. While still positive, this trend needs monitoring. If growth drops below 5%, the current valuation premium may not be justified.",
      "supporting_evidence": [
        "Q2: +15% YoY",
        "Q3: +12% YoY",
        "Q4: +8.2% YoY",
        "Trend: Decelerating"
      ],
      "confidence": 0.88,
      "actionability": "Low - Monitor next earnings for trend confirmation"
    }
  ],

  "confluences": [
    {
      "signals": ["RSI oversold", "MACD bullish", "P/E discount", "Earnings beat"],
      "combined_strength": "Very Strong",
      "interpretation": "4 independent signals aligning bullishly across technical, fundamental, and earnings dimensions"
    }
  ],

  "anomalies": [
    {
      "description": "Revenue growth declining but margins expanding",
      "assessment": "Possible mix shift to higher-margin products (Services)",
      "risk_level": "Low"
    }
  ]
}
```

#### Implementation Approach

1. Create `InsightEngine` class that accepts all analysis results as input
2. Define **rule-based observation generators** for quantitative signals:
   - RSI oversold + MACD bullish = "Technical reversal signal"
   - P/E below peer median + earnings beat = "Undervalued with positive momentum"
   - High insider buying + low sentiment = "Smart money divergence"
   - Revenue deceleration across 3+ quarters = "Growth warning"
   - VaR exceeded + high beta = "Elevated portfolio risk"
3. Use the **LLM to generate natural language** observations from structured signals
4. Rank observations by importance using a scoring framework:
   - Number of supporting signals
   - Historical reliability of the pattern
   - Magnitude of the deviation
5. Run ObservationsAgent LAST in orchestrator pipeline (it needs all other results)
6. Add "Key Observations" as the capstone section in all reports

#### Priority: P1

**Highest-value "capstone" feature** that makes the entire system more useful. However, it requires other features to exist first.

#### Dependencies

- All other analysis features (the more data available, the better the observations)
- At minimum: Technical (existing), Fundamental (existing), Sentiment (enhanced Feature 9)
- Feature 2 (Peer Comparison) and Feature 4 (Earnings) significantly enrich observations

---

### Feature 12: Insider & Institutional Activity

#### What It Is

**Simple explanation**: Tracking what company insiders (executives, directors) and large institutional investors (hedge funds, mutual funds) are doing with the stock. This is often called "smart money" tracking.

```
Insider Activity:
  CEO John Smith    BOUGHT  50,000 shares @ $145.00  ($7.25M)  Jan 15
  CFO Jane Doe      BOUGHT  10,000 shares @ $146.50  ($1.47M)  Jan 12
  Director Bob Lee  SOLD     5,000 shares @ $148.00  ($0.74M)  Jan 10

  Net Insider Activity (90 days): +$7.98M (Bullish)
  Insider Ownership: 2.3% of shares outstanding

Institutional Activity:
  Berkshire Hathaway  INCREASED  +2.5M shares  (now owns 5.2%)
  Vanguard Group      INCREASED  +1.2M shares  (now owns 8.1%)
  BlackRock           DECREASED  -0.5M shares  (now owns 6.8%)

  Institutional Ownership: 72.3%
  Net Institutional Buying (Quarter): +$450M
```

#### Why It Matters

- Insiders know their company best - when they buy aggressively, it's a **bullish signal**
- Insider selling is more nuanced (could be diversification, tax planning)
- Institutional buying indicates **professional validation** of the investment thesis
- Clustered insider buying is one of the **most reliable bullish indicators**
- Data is readily available via yfinance but currently **not utilized**

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance `insider_transactions` | Existing (unused) | Form 4 filings - insider buys/sells |
| yfinance `insider_purchases` | Existing (unused) | Summary of insider purchase activity |
| yfinance `institutional_holders` | Existing (unused) | Top institutional holders |
| yfinance `major_holders` | Existing (unused) | % institutional vs insider ownership |
| yfinance `mutualfund_holders` | Existing (unused) | Top mutual fund holders |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/insider_tracker.py` | Parse insider transactions, compute net activity, detect clusters |
| **CREATE** | `src/tools/institutional_tracker.py` | Track institutional ownership changes, identify accumulation |
| **MODIFY** | `src/agents/fundamental.py` | Include insider/institutional signals in analysis |
| **MODIFY** | `src/agents/data_collector.py` | Collect insider and institutional data |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/insiders/{symbol}`, `GET /api/v1/institutions/{symbol}` |

#### Key Metrics and Outputs

```json
{
  "symbol": "AAPL",

  "insider_activity": {
    "transactions_90_days": [
      {
        "name": "Tim Cook",
        "title": "CEO",
        "transaction_type": "Sale",
        "shares": 50000,
        "price": 185.50,
        "value": 9275000,
        "date": "2026-01-15",
        "shares_remaining": 3280000
      }
    ],
    "net_activity_90_days": {
      "net_shares": -45000,
      "net_value": -8500000,
      "assessment": "Net selling (likely planned sales)"
    },
    "insider_ownership_pct": 0.07,
    "notable_patterns": "No cluster buying detected"
  },

  "institutional_activity": {
    "institutional_ownership_pct": 60.5,
    "top_holders": [
      {"name": "Vanguard Group", "shares": 1280000000, "pct": 7.8, "change": "+0.2%"},
      {"name": "BlackRock", "shares": 1050000000, "pct": 6.4, "change": "-0.1%"},
      {"name": "Berkshire Hathaway", "shares": 915000000, "pct": 5.6, "change": "0.0%"}
    ],
    "quarterly_change": {
      "net_buying": true,
      "net_shares_change": 25000000,
      "assessment": "Moderate institutional accumulation"
    }
  },

  "smart_money_signal": {
    "score": 65,
    "assessment": "Neutral to slightly bullish - institutions accumulating despite insider sales"
  }
}
```

#### Implementation Approach

1. Use `yf.Ticker(symbol).insider_transactions` and `insider_purchases` for Form 4 data
2. Use `yf.Ticker(symbol).institutional_holders` and `major_holders` for ownership
3. Compute net insider activity over 30/60/90 day windows
4. Detect "cluster buying" - multiple insiders buying in short window (strongest signal)
5. Track quarter-over-quarter institutional ownership changes
6. Weight insider purchases more heavily than sales (sales can be for many reasons)
7. Generate combined "smart money" score

#### Priority: P1

Data is **already available** in yfinance but completely unused. High signal value with low implementation effort.

#### Dependencies

- None - can be built immediately using existing yfinance data

---

### Feature 13: Options Flow Analysis

#### What It Is

**Simple explanation**: Analyzing the options market to understand what sophisticated traders are betting on. Options traders often have an "edge" and options flow can predict stock moves.

```
Options Flow for AAPL:

Put/Call Ratio: 0.65 (More calls = Bullish)
Implied Volatility: 28.5% (vs Historical 22.3% = Elevated)
IV Percentile: 78th (Higher than 78% of past year)

Unusual Activity Detected:
  🔥 1,500 contracts of $200 Calls (Feb 21 expiry) bought for $2.3M
     → Someone betting on 8% upside in 5 days

  🔥 Large put spread: Buy $175P, Sell $165P (10,000 contracts)
     → Hedging or bearish bet on downside to $175

Max Pain: $185.00 (price where most options expire worthless)
Current Price: $188.50

Interpretation: Bullish flow with elevated IV suggests
               expectation of significant move (likely earnings)
```

#### Why It Matters

- Options traders are often **more sophisticated** than stock traders
- Unusual options activity can **predict price moves** before they happen
- Put/Call ratio reveals **market sentiment** at the options level
- Implied volatility shows **expected magnitude** of moves
- "Max pain" theory helps predict short-term price magnets
- Options flow is heavily used by professional traders

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance `options` | Existing (unused) | Options chain data (calls, puts, strikes, expiries) |
| yfinance `option_chain` | Existing (unused) | Detailed options data with Greeks |
| Yahoo Finance options page | Enhancement | Unusual activity detection |
| CBOE data | New (optional) | VIX, put/call ratios for market-wide analysis |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/options_analyzer.py` | P/C ratio, IV analysis, unusual activity, max pain |
| **CREATE** | `src/agents/options.py` | New `OptionsAnalystAgent` |
| **MODIFY** | `src/agents/risk.py` | Include IV in volatility assessment |
| **MODIFY** | `src/agents/orchestrator.py` | Add options analysis as optional step |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/options/{symbol}` |

#### Key Metrics and Outputs

```json
{
  "symbol": "AAPL",
  "current_price": 188.50,

  "options_sentiment": {
    "put_call_ratio": 0.65,
    "put_call_assessment": "Bullish (below 0.7)",
    "call_volume": 125000,
    "put_volume": 81250,
    "total_options_volume": 206250,
    "volume_vs_average": "1.8x normal (elevated)"
  },

  "implied_volatility": {
    "current_iv": 28.5,
    "historical_volatility_30d": 22.3,
    "iv_percentile": 78,
    "iv_assessment": "Elevated - market expects significant move",
    "iv_skew": {
      "put_iv": 30.2,
      "call_iv": 26.8,
      "skew": "Put skew (downside protection demand)"
    }
  },

  "unusual_activity": [
    {
      "type": "call",
      "strike": 200,
      "expiry": "2026-02-21",
      "contracts": 1500,
      "premium_paid": 2300000,
      "implied_move": "+8.0%",
      "assessment": "Large bullish bet on near-term upside"
    }
  ],

  "max_pain": {
    "price": 185.00,
    "distance_from_current": "-1.9%",
    "interpretation": "Options makers benefit if price drifts to $185 by expiry"
  },

  "options_signal": {
    "score": 72,
    "direction": "Bullish",
    "confidence": "Moderate",
    "key_insight": "Heavy call buying with elevated IV suggests upside expectation, possibly pre-earnings positioning"
  }
}
```

#### Implementation Approach

1. Use `yf.Ticker(symbol).options` to get available expiration dates
2. Use `yf.Ticker(symbol).option_chain(date)` for full options chain
3. Calculate put/call ratio from volume data
4. Calculate aggregate implied volatility (weighted by volume)
5. Detect unusual activity: volume > 2x open interest on a strike
6. Calculate max pain by finding strike that minimizes total option value
7. Assess IV skew (put IV vs call IV) for directional bias
8. Generate overall options sentiment score

#### Priority: P2

High value for sophisticated users but requires understanding of options. More complex to implement correctly.

#### Dependencies

- Feature 5 (Stock Performance) - For historical volatility comparison
- Feature 7 (Event Analysis) - Options often spike around events

---

### Feature 14: Short Interest Analysis

#### What It Is

**Simple explanation**: Tracking how many shares are being "shorted" (bet against). High short interest means many investors are betting the stock will go down, but it also creates **short squeeze potential** (like GameStop in 2021).

```
Short Interest for GME:

Short Interest: 45.2M shares (24.8% of float)
Days to Cover: 8.5 days (very high)
Short Interest Change: +15.2% vs last month

Short Squeeze Score: 85/100 (High Risk)

Why this matters:
- 24.8% of tradeable shares are shorted
- At current volume, it would take 8.5 days for shorts to cover
- If price rises, shorts may be FORCED to buy (causing more price rise)
- This is called a "short squeeze"

Historical Squeezes:
  Jan 2021: Price went from $20 → $483 (+2,315%)
  Mar 2021: Price went from $40 → $348 (+770%)
```

#### Why It Matters

- High short interest = many investors betting against the stock
- **Contrarian signal**: Sometimes the crowd is wrong
- **Short squeeze potential**: Forced buying can cause explosive rallies
- **Risk indicator**: High short interest often means something is wrong fundamentally
- Essential for identifying **asymmetric risk/reward** opportunities

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| Yahoo Finance key stats | Enhancement | Short interest, short ratio, short % of float |
| yfinance `info` | Existing | Contains some short interest data |
| FINRA short data | New (optional) | Official short interest (delayed 2 weeks) |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/short_interest.py` | Short metrics, squeeze scoring, historical tracking |
| **MODIFY** | `src/agents/risk.py` | Include short squeeze risk in assessment |
| **MODIFY** | `src/agents/data_collector.py` | Collect short interest data |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/shorts/{symbol}` |

#### Key Metrics and Outputs

```json
{
  "symbol": "GME",

  "short_interest": {
    "shares_short": 45200000,
    "short_percent_of_float": 24.8,
    "short_percent_of_shares": 18.2,
    "short_ratio_days_to_cover": 8.5,
    "previous_month_shares_short": 39200000,
    "change_vs_previous": "+15.3%"
  },

  "short_squeeze_analysis": {
    "squeeze_score": 85,
    "risk_level": "High",
    "factors": {
      "short_percent_score": 90,
      "days_to_cover_score": 85,
      "recent_increase_score": 75,
      "borrow_cost_score": 80
    },
    "assessment": "High short squeeze potential - elevated short interest with increasing trend"
  },

  "historical_context": {
    "52_week_high_short_pct": 140.0,
    "52_week_low_short_pct": 15.2,
    "current_percentile": 45,
    "trend": "Increasing"
  },

  "borrow_data": {
    "borrow_rate": 8.5,
    "borrow_rate_assessment": "Elevated (hard to borrow)",
    "shares_available_to_short": 250000
  },

  "risk_assessment": {
    "for_longs": "Short squeeze could amplify gains significantly",
    "for_shorts": "Dangerous - high squeeze risk, consider stop losses",
    "catalyst_watch": ["Earnings date", "Potential positive news", "Options expiration"]
  }
}
```

#### Implementation Approach

1. Extract short interest from `yf.Ticker(symbol).info`:
   - `shortPercentOfFloat`
   - `sharesShort`
   - `shortRatio` (days to cover)
   - `sharesShortPriorMonth`
2. Calculate squeeze score based on:
   - Short % of float (>20% = high risk)
   - Days to cover (>5 = high risk)
   - Month-over-month change (increasing = higher risk)
   - Borrow rate if available
3. Track historical short interest percentiles
4. Generate risk assessment for both longs and shorts
5. Identify potential squeeze catalysts (earnings, events)

#### Priority: P1

Important risk metric that's often overlooked. Data mostly available in yfinance. High interest from retail investors.

#### Dependencies

- Feature 7 (Event Analysis) - Squeezes often trigger around events
- Feature 13 (Options) - Options activity can trigger squeezes (gamma squeeze)

---

### Feature 15: Dividend Analysis

#### What It Is

**Simple explanation**: Comprehensive analysis of a company's dividend - how much they pay, how safe it is, and whether it's a good income investment.

```
Dividend Analysis for JNJ:

Annual Dividend: $4.76 per share
Dividend Yield: 2.95%
Payout Ratio: 44.2% (Healthy - keeps 55.8% of earnings)

Dividend Safety Score: 92/100 (Very Safe)
  ✓ 61 years of consecutive increases (Dividend King)
  ✓ Payout ratio below 60%
  ✓ Free cash flow covers dividend 2.3x
  ✓ Strong balance sheet (AA credit rating)

Dividend Growth:
  5-Year CAGR: 5.8%
  10-Year CAGR: 6.2%
  Last Increase: +4.2% (April 2025)

Yield Comparison:
  JNJ: 2.95%
  Healthcare Sector Avg: 1.8%
  S&P 500 Avg: 1.5%
  10-Year Treasury: 4.2%

Next Ex-Dividend Date: Feb 21, 2026
Next Payment Date: Mar 10, 2026
```

#### Why It Matters

- Dividends are a **major source of total returns** (historically ~40% of S&P returns)
- Income investors need to know if dividends are **safe and sustainable**
- Dividend growth is a **sign of financial health** and management confidence
- Dividend cuts are **major red flags** that often precede price declines
- Currently **completely missing** despite yfinance having full dividend data

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance `dividends` | Existing (unused) | Full dividend history |
| yfinance `info` | Existing | Dividend yield, payout ratio, ex-date |
| yfinance `income_stmt` | Existing | Earnings for payout ratio calculation |
| yfinance `cashflow` | Existing | Free cash flow for dividend coverage |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/dividend_analyzer.py` | Dividend metrics, safety scoring, growth analysis |
| **CREATE** | `src/agents/dividend.py` | New `DividendAnalystAgent` |
| **MODIFY** | `src/agents/fundamental.py` | Include dividend metrics in analysis |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/dividends/{symbol}` |

#### Key Metrics and Outputs

```json
{
  "symbol": "JNJ",

  "current_dividend": {
    "annual_dividend": 4.76,
    "dividend_yield": 2.95,
    "frequency": "Quarterly",
    "next_ex_date": "2026-02-21",
    "next_payment_date": "2026-03-10",
    "next_payment_amount": 1.19
  },

  "dividend_safety": {
    "safety_score": 92,
    "rating": "Very Safe",
    "factors": {
      "payout_ratio": {
        "value": 44.2,
        "assessment": "Healthy (below 60%)"
      },
      "fcf_coverage": {
        "value": 2.3,
        "assessment": "Strong (FCF covers dividend 2.3x)"
      },
      "debt_to_equity": {
        "value": 0.45,
        "assessment": "Conservative leverage"
      },
      "earnings_stability": {
        "value": 0.92,
        "assessment": "Very stable earnings history"
      }
    },
    "red_flags": [],
    "dividend_cut_probability": "Very Low (<5%)"
  },

  "dividend_growth": {
    "consecutive_years_increased": 61,
    "classification": "Dividend King (50+ years)",
    "cagr_5_year": 5.8,
    "cagr_10_year": 6.2,
    "last_increase": {
      "date": "2025-04-15",
      "percent_increase": 4.2,
      "old_dividend": 4.57,
      "new_dividend": 4.76
    },
    "projected_next_increase": {
      "expected_date": "2026-04-15",
      "expected_range": "4.0% - 5.5%"
    }
  },

  "yield_comparison": {
    "current_yield": 2.95,
    "sector_average": 1.8,
    "sp500_average": 1.5,
    "treasury_10y": 4.2,
    "yield_percentile_vs_history": 65,
    "assessment": "Above sector average, below risk-free rate"
  },

  "dividend_history": {
    "5_year_history": [
      {"year": 2025, "annual": 4.76, "yield_avg": 2.9},
      {"year": 2024, "annual": 4.57, "yield_avg": 2.8},
      {"year": 2023, "annual": 4.45, "yield_avg": 2.7}
    ],
    "dividend_cuts": [],
    "dividend_freezes": []
  },

  "income_investor_summary": {
    "recommendation": "Strong Income Buy",
    "key_points": [
      "61-year dividend growth streak (Dividend King)",
      "44% payout ratio leaves room for increases",
      "2.3x FCF coverage provides safety margin",
      "Yield premium vs sector of +115 bps"
    ]
  }
}
```

#### Implementation Approach

1. Use `yf.Ticker(symbol).dividends` for complete dividend history
2. Use `yf.Ticker(symbol).info` for current yield, ex-date, payout ratio
3. Calculate dividend growth rates (CAGR) over 1/3/5/10 year periods
4. Count consecutive years of increases for Aristocrat/King classification:
   - Dividend Achiever: 10+ years
   - Dividend Aristocrat: 25+ years
   - Dividend King: 50+ years
5. Calculate safety score based on:
   - Payout ratio (<60% = safe)
   - FCF coverage (>1.5x = safe)
   - Debt levels
   - Earnings stability
6. Compare yield to sector, market, and risk-free rate
7. Identify dividend cuts/freezes in history as red flags

#### Priority: P1

Income investing is **extremely popular** with retail investors. Data is fully available in yfinance but unused.

#### Dependencies

- Feature 2 (Peer Comparison) - For yield comparison vs peers
- Feature 4 (Earnings) - For payout ratio calculations

---

### Feature 16: Analyst Consensus Tracking

#### What It Is

**Simple explanation**: Aggregating what Wall Street analysts think about a stock - their ratings (Buy/Hold/Sell), price targets, and how these have changed over time.

```
Analyst Consensus for AAPL:

Overall Rating: BUY (4.2 out of 5)
Price Target: $210.50 (consensus of 45 analysts)
  High: $250.00
  Low:  $165.00
  Current Price: $188.50 → 11.7% upside to target

Rating Distribution:
  Strong Buy: 18 (40%)
  Buy:        15 (33%)
  Hold:       10 (22%)
  Sell:        2 (5%)
  Strong Sell: 0 (0%)

Recent Changes (Last 30 Days):
  ↑ Morgan Stanley upgraded to Buy (from Hold), PT $225
  ↑ Goldman Sachs raised PT to $215 (from $200)
  ↓ Barclays downgraded to Hold (from Buy), PT $180

Estimate Revisions:
  EPS Estimates (Next Quarter): $2.35
  30 Days Ago: $2.28
  Revision Trend: +3.1% (Positive momentum)
```

#### Why It Matters

- Analyst consensus provides a **professional baseline** for valuation
- Price target changes often **precede stock moves**
- Estimate revisions are a **leading indicator** of earnings surprises
- Upgrades/downgrades cause significant **short-term price impact**
- Currently: yfinance has this data but **it's not being used**

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance `recommendations` | Existing (unused) | Historical analyst ratings |
| yfinance `recommendations_summary` | Existing (unused) | Current rating distribution |
| yfinance `analyst_price_targets` | Existing (unused) | Price target data |
| yfinance `earnings_estimate` | Existing (unused) | EPS estimates and revisions |
| yfinance `revenue_estimate` | Existing (unused) | Revenue estimates |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/analyst_tracker.py` | Consensus, price targets, revisions, upgrade/downgrade tracking |
| **MODIFY** | `src/agents/fundamental.py` | Include analyst consensus in valuation |
| **MODIFY** | `src/agents/data_collector.py` | Collect analyst data |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/analysts/{symbol}` |

#### Key Metrics and Outputs

```json
{
  "symbol": "AAPL",
  "current_price": 188.50,

  "consensus_rating": {
    "rating": "Buy",
    "score": 4.2,
    "total_analysts": 45,
    "distribution": {
      "strong_buy": 18,
      "buy": 15,
      "hold": 10,
      "sell": 2,
      "strong_sell": 0
    },
    "bullish_percent": 73.3,
    "change_vs_30_days_ago": "+2 upgrades, -1 downgrade"
  },

  "price_targets": {
    "consensus": 210.50,
    "high": 250.00,
    "low": 165.00,
    "median": 208.00,
    "upside_to_consensus": 11.7,
    "number_of_analysts": 42
  },

  "recent_changes": [
    {
      "date": "2026-02-10",
      "firm": "Morgan Stanley",
      "analyst": "Erik Woodring",
      "action": "Upgrade",
      "old_rating": "Hold",
      "new_rating": "Buy",
      "old_pt": 195.00,
      "new_pt": 225.00
    },
    {
      "date": "2026-02-05",
      "firm": "Goldman Sachs",
      "action": "PT Raise",
      "old_pt": 200.00,
      "new_pt": 215.00
    }
  ],

  "estimate_revisions": {
    "next_quarter_eps": {
      "current_estimate": 2.35,
      "30_days_ago": 2.28,
      "90_days_ago": 2.20,
      "revision_trend": "+3.1%",
      "assessment": "Positive momentum - estimates rising"
    },
    "full_year_eps": {
      "current_estimate": 7.85,
      "30_days_ago": 7.65,
      "revision_trend": "+2.6%"
    },
    "revenue_estimate_next_q": {
      "current": 124500000000,
      "revision_trend": "+1.2%"
    }
  },

  "analyst_signal": {
    "score": 75,
    "assessment": "Bullish consensus with positive estimate revisions",
    "key_insight": "73% of analysts are bullish with 11.7% upside to consensus PT. Rising estimates suggest potential earnings beat."
  }
}
```

#### Implementation Approach

1. Use `yf.Ticker(symbol).recommendations` for historical ratings
2. Use `yf.Ticker(symbol).recommendations_summary` for current distribution
3. Use `yf.Ticker(symbol).analyst_price_targets` for PT data
4. Use `yf.Ticker(symbol).earnings_estimate` for EPS estimates
5. Track changes over 30/60/90 days
6. Identify upgrades/downgrades from recommendations history
7. Calculate estimate revision momentum
8. Generate overall analyst signal score

#### Priority: P1

Highly requested feature. Data is **fully available** in yfinance but completely unused. Low implementation effort.

#### Dependencies

- Feature 4 (Earnings) - Estimates relate to upcoming earnings
- Feature 11 (Observations) - Analyst changes feed into key observations

---

### Feature 17: Macro Economic Integration

#### What It Is

**Simple explanation**: Understanding how macroeconomic factors (interest rates, inflation, Fed policy, economic cycles) affect individual stocks and sectors.

```
Macro Environment Impact on AAPL:

Interest Rate Sensitivity: HIGH
  - Growth stock with high valuations are rate-sensitive
  - Fed Funds Rate: 5.25% (↓ expected)
  - 10Y Treasury: 4.2%
  - When rates fall, growth stocks typically outperform

Inflation Impact: MODERATE
  - Consumer discretionary spending affected by inflation
  - CPI: 3.2% (cooling)
  - Impact: Moderating inflation is positive for consumer spending

Economic Cycle Position: LATE CYCLE
  - Consumer Discretionary typically underperforms late cycle
  - Recession probability (12mo): 25%
  - Impact: Monitor for signs of consumer weakness

Sector Rotation Signal:
  - Current favored sectors: Utilities, Healthcare, Staples
  - Tech typically underperforms in late cycle/recession
  - AAPL has defensive qualities vs pure growth tech

Dollar Impact: NEGATIVE
  - AAPL has 60% international revenue
  - Strong dollar hurts international earnings
  - DXY: 104.5 (moderately strong)
```

#### Why It Matters

- **"Don't fight the Fed"** - monetary policy drives markets
- Interest rates have **huge impact on growth stock valuations**
- Economic cycles favor **different sectors** at different times
- Inflation affects consumer spending and corporate margins
- Currently: No macro awareness at all - analyzing stocks in a vacuum

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| FRED API | New | Federal Reserve economic data (rates, CPI, GDP, unemployment) |
| yfinance | Existing | Treasury yields (^TNX), VIX (^VIX), Dollar index (DX-Y.NYB) |
| Fed calendar | New | FOMC meeting dates, rate decision expectations |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/macro_data.py` | Fetch macro indicators (rates, inflation, employment) |
| **CREATE** | `src/tools/macro_analyzer.py` | Sector rotation, rate sensitivity, cycle positioning |
| **CREATE** | `src/agents/macro.py` | New `MacroAnalystAgent` |
| **MODIFY** | `src/agents/orchestrator.py` | Include macro context in analysis |
| **MODIFY** | `src/api/routes.py` | Add `GET /api/v1/macro`, `GET /api/v1/macro/impact/{symbol}` |

#### Key Metrics and Outputs

```json
{
  "macro_environment": {
    "interest_rates": {
      "fed_funds_rate": 5.25,
      "fed_funds_direction": "Cuts expected",
      "treasury_10y": 4.2,
      "treasury_2y": 4.8,
      "yield_curve": "Inverted (-60bps)",
      "yield_curve_signal": "Recession warning"
    },
    "inflation": {
      "cpi_yoy": 3.2,
      "cpi_trend": "Cooling",
      "pce_yoy": 2.8,
      "fed_target": 2.0,
      "inflation_assessment": "Above target but improving"
    },
    "employment": {
      "unemployment_rate": 3.9,
      "nonfarm_payrolls_last": 215000,
      "labor_market": "Still tight but cooling"
    },
    "economic_cycle": {
      "current_phase": "Late Cycle",
      "recession_probability_12m": 25,
      "gdp_growth_last": 2.1
    }
  },

  "stock_macro_impact": {
    "symbol": "AAPL",
    "sector": "Technology",

    "rate_sensitivity": {
      "sensitivity": "High",
      "rationale": "Growth stock with high P/E is rate-sensitive",
      "impact_of_rate_cut": "Positive - lower rates support higher multiples",
      "duration_risk": "Moderate"
    },

    "inflation_sensitivity": {
      "sensitivity": "Moderate",
      "rationale": "Consumer discretionary affected by real income",
      "current_impact": "Slightly positive - inflation cooling helps consumers"
    },

    "cycle_positioning": {
      "typical_performance": "Tech underperforms late cycle",
      "aapl_specific": "More defensive than pure growth - strong balance sheet, cash flows",
      "recommendation": "Quality tech like AAPL more resilient than speculative growth"
    },

    "currency_exposure": {
      "international_revenue_pct": 60,
      "dollar_impact": "Strong dollar hurts earnings translation",
      "current_dxy": 104.5,
      "assessment": "Moderate headwind"
    },

    "sector_rotation_signal": {
      "current_favored_sectors": ["Utilities", "Healthcare", "Consumer Staples"],
      "tech_positioning": "Underweight in late cycle playbook",
      "aapl_exception": "Quality + cash + dividend = more defensive"
    }
  },

  "upcoming_macro_events": [
    {"date": "2026-02-19", "event": "FOMC Minutes", "importance": "High"},
    {"date": "2026-02-28", "event": "PCE Inflation", "importance": "High"},
    {"date": "2026-03-19", "event": "FOMC Decision", "importance": "Critical"}
  ],

  "macro_signal": {
    "overall": "Cautiously Bullish",
    "rationale": "Cooling inflation + expected rate cuts are tailwinds. Late cycle positioning is a concern but AAPL's quality characteristics provide some defense."
  }
}
```

#### Implementation Approach

1. Create `macro_data.py` to fetch:
   - Treasury yields via yfinance (^TNX, ^FVX, ^IRX)
   - VIX via yfinance (^VIX)
   - Dollar index via yfinance (DX-Y.NYB)
   - FRED API for: CPI, PCE, unemployment, Fed Funds rate, GDP
2. Build rate sensitivity scoring based on:
   - P/E ratio (higher = more sensitive)
   - Sector (Tech, Real Estate most sensitive)
   - Leverage (more debt = more sensitive)
3. Map economic cycles to sector rotation:
   - Early: Financials, Industrials, Consumer Discretionary
   - Mid: Technology, Communication, Materials
   - Late: Energy, Healthcare, Consumer Staples
   - Recession: Utilities, Healthcare, Consumer Staples
4. Calculate currency exposure from geographic revenue breakdown
5. Maintain calendar of upcoming macro events

#### Priority: P2

Significant value-add but requires new data source (FRED API). More complex implementation. Best suited for sophisticated users.

#### Dependencies

- Feature 5 (Stock Performance) - For correlation with macro factors
- Feature 2 (Peer Comparison) - For sector-level analysis

---

### Feature 18: Alert & Notification System

#### What It Is

**Simple explanation**: A proactive system that monitors stocks and notifies users when important events occur - price levels hit, technical signals trigger, news spikes, or earnings approach.

```
Alert Types:

📊 PRICE ALERTS
  "AAPL crossed above $190" (triggered 2 mins ago)
  "TSLA dropped below $200 support" (triggered 1 hour ago)

📈 TECHNICAL SIGNALS
  "NVDA: RSI dropped below 30 (oversold)"
  "MSFT: Golden Cross detected (50 SMA > 200 SMA)"
  "AMD: MACD bullish crossover"

📰 NEWS ALERTS
  "AAPL: 5x normal news volume detected (possible earnings leak)"
  "GOOGL: Sentiment shifted from positive to negative"

📅 CALENDAR ALERTS
  "AAPL earnings in 3 days (Jan 30, after market)"
  "JNJ ex-dividend date tomorrow"
  "FOMC decision tomorrow at 2pm ET"

⚠️ RISK ALERTS
  "Portfolio VaR exceeded threshold"
  "GME short interest spiked +20%"
```

#### Why It Matters

- Investors can't monitor markets 24/7
- **Time-sensitive opportunities** get missed without alerts
- Technical signals are only useful if you know **when they trigger**
- Earnings dates and ex-dividend dates require **advance notice**
- Transforms the agent from **reactive to proactive**

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| All existing analysis tools | Existing | Generate signals to alert on |
| Redis | Existing (configured) | Store user alerts, pub/sub for notifications |
| Scheduler (APScheduler) | New | Periodic monitoring jobs |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/alert_manager.py` | Alert creation, storage, evaluation, delivery |
| **CREATE** | `src/services/alert_scheduler.py` | Background jobs to monitor conditions |
| **CREATE** | `src/services/notification_service.py` | Delivery via webhook, email, websocket |
| **MODIFY** | `src/api/routes.py` | Add alert CRUD endpoints, websocket for real-time |
| **MODIFY** | `src/config.py` | Alert configuration settings |

#### Alert Types and Conditions

```python
# Price Alerts
{
    "type": "price",
    "symbol": "AAPL",
    "condition": "crosses_above",  # crosses_below, reaches
    "value": 200.00,
    "repeat": False
}

# Technical Signal Alerts
{
    "type": "technical",
    "symbol": "AAPL",
    "indicator": "rsi",
    "condition": "below",  # above, crosses_above, crosses_below
    "value": 30,
    "timeframe": "daily"
}

# News/Sentiment Alerts
{
    "type": "news",
    "symbol": "AAPL",
    "condition": "volume_spike",  # sentiment_change, keyword
    "threshold": 3.0,  # 3x normal volume
}

# Calendar Alerts
{
    "type": "calendar",
    "symbol": "AAPL",
    "event": "earnings",  # dividend, split
    "days_before": 3
}

# Risk Alerts
{
    "type": "risk",
    "portfolio_id": "default",
    "metric": "var_95",
    "condition": "exceeds",
    "threshold": 50000
}
```

#### Key Metrics and Outputs

```json
{
  "alerts": {
    "active": [
      {
        "id": "alert_001",
        "type": "price",
        "symbol": "AAPL",
        "condition": "crosses_above",
        "value": 200.00,
        "created": "2026-02-10T10:00:00Z",
        "status": "watching",
        "last_checked": "2026-02-16T15:30:00Z"
      }
    ],

    "triggered_today": [
      {
        "id": "alert_002",
        "type": "technical",
        "symbol": "NVDA",
        "condition": "RSI below 30",
        "triggered_at": "2026-02-16T14:22:00Z",
        "price_at_trigger": 875.50,
        "message": "NVDA RSI dropped to 28.5 (oversold territory)"
      }
    ]
  },

  "upcoming_events": [
    {
      "symbol": "AAPL",
      "event": "Earnings",
      "date": "2026-01-30",
      "time": "After Market",
      "days_until": 3,
      "alert_set": true
    },
    {
      "symbol": "JNJ",
      "event": "Ex-Dividend",
      "date": "2026-02-21",
      "days_until": 5,
      "alert_set": true
    }
  ]
}
```

#### API Endpoints

```
POST   /api/v1/alerts              → Create new alert
GET    /api/v1/alerts              → List all alerts
GET    /api/v1/alerts/{id}         → Get alert details
DELETE /api/v1/alerts/{id}         → Delete alert
PATCH  /api/v1/alerts/{id}         → Update alert
GET    /api/v1/alerts/triggered    → Get recently triggered alerts
WS     /api/v1/alerts/stream       → Real-time alert notifications
```

#### Implementation Approach

1. Create alert data model stored in Redis:
   - Alert ID, type, symbol, conditions, status
   - User ID (for multi-user support)
   - Notification preferences (webhook URL, email, websocket)
2. Build alert evaluator for each type:
   - Price alerts: Compare current price to threshold
   - Technical alerts: Run indicator calculations
   - News alerts: Check sentiment/volume from news fetcher
   - Calendar alerts: Check days until event
3. Use APScheduler for background monitoring:
   - Price/technical checks every 1-5 minutes during market hours
   - News checks every 15 minutes
   - Calendar checks daily
4. Build notification service:
   - Webhook delivery (most flexible)
   - WebSocket push (for real-time UI)
   - Email (optional, requires SMTP config)
5. Add WebSocket endpoint for real-time streaming to frontend
6. Implement alert history and triggered alert log

#### Priority: P2

High user value but requires **background infrastructure** (scheduler, Redis). More complex deployment.

#### Dependencies

- All analysis tools (alerts based on their outputs)
- Redis infrastructure (configured but not utilized)
- Feature 4 (Earnings) - For earnings date alerts
- Feature 15 (Dividends) - For ex-dividend alerts

---

### Feature 19: Portfolio Optimization

#### What It Is

**Simple explanation**: Using Modern Portfolio Theory (MPT) to help users build optimal portfolios - maximizing returns for a given level of risk, or minimizing risk for a target return.

```
Portfolio Optimization for: AAPL, MSFT, GOOGL, JNJ, JPM

Current Allocation:
  AAPL:  20%
  MSFT:  20%
  GOOGL: 20%
  JNJ:   20%
  JPM:   20%

Optimized Allocation (Max Sharpe Ratio):
  AAPL:  28%  (+8%)
  MSFT:  32%  (+12%)
  GOOGL: 15%  (-5%)
  JNJ:   18%  (-2%)
  JPM:    7%  (-13%)

Expected Improvement:
  Return: 12.5% → 14.2% (+1.7%)
  Risk:   18.3% → 16.8% (-1.5%)
  Sharpe: 0.68 → 0.85 (+0.17)

Efficient Frontier:
  ┌────────────────────────────────┐
  │        *Max Sharpe             │
  │       /                        │
  │      /   *Current Portfolio    │
  │     /                          │
  │    /                           │
  │   /*Min Variance               │
  │  /                             │
  └────────────────────────────────┘
    Risk (Standard Deviation) →
```

#### Why It Matters

- Most investors are **not efficiently diversified**
- Small allocation changes can **significantly improve risk-adjusted returns**
- Correlation analysis reveals **hidden concentration risks**
- Essential for moving from "stock picking" to **portfolio management**
- Libraries already in requirements.txt (scipy, numpy) support optimization

#### Data Sources Needed

| Source | Type | Purpose |
|---|---|---|
| yfinance historical data | Existing | Returns for correlation and optimization |
| Risk-free rate | Enhancement | For Sharpe ratio calculation (use Treasury data) |

#### Agents/Tools to Create or Modify

| Action | File | What Changes |
|---|---|---|
| **CREATE** | `src/tools/portfolio_optimizer.py` | MPT optimization, efficient frontier, correlation |
| **CREATE** | `src/agents/portfolio.py` | New `PortfolioAnalystAgent` |
| **MODIFY** | `src/api/routes.py` | Add `POST /api/v1/portfolio/optimize` |
| **MODIFY** | `src/api/schemas.py` | Add optimization request/response schemas |

#### Key Metrics and Outputs

```json
{
  "portfolio": {
    "symbols": ["AAPL", "MSFT", "GOOGL", "JNJ", "JPM"],
    "current_weights": [0.20, 0.20, 0.20, 0.20, 0.20]
  },

  "correlation_matrix": {
    "AAPL-MSFT": 0.82,
    "AAPL-GOOGL": 0.78,
    "AAPL-JNJ": 0.35,
    "AAPL-JPM": 0.55,
    "MSFT-GOOGL": 0.85,
    "MSFT-JNJ": 0.32,
    "MSFT-JPM": 0.52,
    "GOOGL-JNJ": 0.28,
    "GOOGL-JPM": 0.48,
    "JNJ-JPM": 0.45
  },

  "correlation_insights": [
    "MSFT-GOOGL correlation of 0.85 is very high - consider reducing one",
    "JNJ provides best diversification (low correlation to tech)",
    "Tech concentration: AAPL+MSFT+GOOGL = 60% with high inter-correlation"
  ],

  "current_portfolio_metrics": {
    "expected_return": 12.5,
    "volatility": 18.3,
    "sharpe_ratio": 0.68,
    "max_drawdown_historical": -28.5,
    "beta": 1.15
  },

  "optimized_portfolios": {
    "max_sharpe": {
      "weights": {
        "AAPL": 0.28,
        "MSFT": 0.32,
        "GOOGL": 0.15,
        "JNJ": 0.18,
        "JPM": 0.07
      },
      "expected_return": 14.2,
      "volatility": 16.8,
      "sharpe_ratio": 0.85
    },
    "min_variance": {
      "weights": {
        "AAPL": 0.12,
        "MSFT": 0.15,
        "GOOGL": 0.08,
        "JNJ": 0.42,
        "JPM": 0.23
      },
      "expected_return": 9.8,
      "volatility": 12.2,
      "sharpe_ratio": 0.80
    },
    "target_return_15": {
      "target_return": 15.0,
      "weights": {
        "AAPL": 0.30,
        "MSFT": 0.35,
        "GOOGL": 0.18,
        "JNJ": 0.12,
        "JPM": 0.05
      },
      "volatility": 18.5,
      "sharpe_ratio": 0.81
    }
  },

  "efficient_frontier": {
    "points": [
      {"return": 8.0, "risk": 10.5},
      {"return": 10.0, "risk": 12.0},
      {"return": 12.0, "risk": 14.5},
      {"return": 14.0, "risk": 17.0},
      {"return": 16.0, "risk": 20.5}
    ]
  },

  "rebalancing_recommendations": [
    {
      "action": "Reduce GOOGL by 5%",
      "rationale": "High correlation with MSFT, lower Sharpe contribution"
    },
    {
      "action": "Increase AAPL by 8%",
      "rationale": "Best risk-adjusted return in portfolio"
    },
    {
      "action": "Reduce JPM by 13%",
      "rationale": "Lowest Sharpe contribution, high volatility"
    }
  ],

  "constraints_applied": {
    "min_weight": 0.05,
    "max_weight": 0.40,
    "max_sector_weight": 0.60
  }
}
```

#### Implementation Approach

1. Use scipy.optimize for portfolio optimization:

   ```python
   from scipy.optimize import minimize

   def optimize_sharpe(weights, returns, cov_matrix, rf_rate):
       portfolio_return = np.dot(weights, returns)
       portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
       sharpe = (portfolio_return - rf_rate) / portfolio_std
       return -sharpe  # Minimize negative Sharpe
   ```

2. Calculate returns covariance matrix from historical data
3. Implement optimization objectives:
   - Max Sharpe: Maximize risk-adjusted return
   - Min Variance: Minimize portfolio volatility
   - Target Return: Minimize risk for specified return
4. Generate efficient frontier by solving for multiple target returns
5. Build correlation matrix with heatmap visualization
6. Identify concentration risks from correlation analysis
7. Generate rebalancing recommendations with rationale

#### Priority: P2

Sophisticated feature that transforms the agent from stock analysis to **portfolio management**. Requires careful implementation of optimization algorithms.

#### Dependencies

- Feature 5 (Stock Performance) - For historical returns
- Feature 6 (Enhanced Reports) - For efficient frontier charts
- Multiple stocks analyzed (uses multi-stock data)

---

## Architecture Changes

### Current Architecture

```
FinancialResearchAgent (sync wrapper)
         |
OrchestratorAgent (coordinator)
         |
         +-- DataCollectorAgent
         |
         +-- (parallel) TechnicalAnalystAgent
         +-- (parallel) FundamentalAnalystAgent
         +-- (parallel) SentimentAnalystAgent
         +-- (parallel) RiskAnalystAgent
         |
         +-- ReportGeneratorAgent
```

### Enhanced Architecture

```
FinancialResearchAgent (sync wrapper)
         |
OrchestratorAgent (coordinator)
         |
    Phase 1: Data Collection
         |
         +-- DataCollectorAgent (enhanced: earnings, benchmarks, peers)
         |
    Phase 2: Core Analysis (parallel)
         |
         +-- TechnicalAnalystAgent (+ signal history, performance)
         +-- FundamentalAnalystAgent (+ real peer comparison)
         +-- SentimentAnalystAgent (FinBERT, multi-source)
         +-- RiskAnalystAgent (+ Beta, Sortino)
         +-- EarningsAnalystAgent (NEW)
         |
    Phase 3: Specialized Analysis (conditional, parallel)
         |
         +-- ThematicAnalystAgent (if theme requested)
         +-- DisruptionAnalystAgent (if disruption analysis requested)
         +-- BacktestingAgent (if backtest requested)
         +-- EventAnalysis (via EarningsAnalyst)
         +-- OptionsAnalystAgent (if options analysis requested)
         +-- DividendAnalystAgent (for income stocks)
         +-- MacroAnalystAgent (for macro context)
         +-- PortfolioAnalystAgent (for portfolio optimization)
         |
    Phase 4: Synthesis
         |
         +-- ObservationsAgent (NEW - synthesizes ALL results)
         |
    Phase 5: Output
         |
         +-- ReportGeneratorAgent (enhanced: PDF, MD, HTML, charts)
```

---

## New Agents Required

| # | Agent | File Path | Rationale |
|---|---|---|---|
| 1 | `EarningsAnalystAgent` | `src/agents/earnings.py` | Earnings is a distinct analytical domain with its own data, metrics, and quarterly cadence |
| 2 | `ThematicAnalystAgent` | `src/agents/thematic.py` | Thematic analysis operates at portfolio/group level with unique aggregation logic |
| 3 | `DisruptionAnalystAgent` | `src/agents/disruption.py` | Disruption analysis combines quantitative + qualitative in a distinct reasoning pattern |
| 4 | `BacktestingAgent` | `src/agents/backtesting.py` | Completely different execution model (time-series simulation vs point-in-time analysis) |
| 5 | `ObservationsAgent` | `src/agents/observations.py` | Synthesis agent that consumes ALL other outputs - distinct "meta-analysis" role |
| 6 | `OptionsAnalystAgent` | `src/agents/options.py` | Options analysis requires specialized knowledge of Greeks, IV, and flow interpretation |
| 7 | `DividendAnalystAgent` | `src/agents/dividend.py` | Income investing is a distinct strategy with unique metrics (safety, growth, yield) |
| 8 | `MacroAnalystAgent` | `src/agents/macro.py` | Macro analysis operates at economy level with sector rotation and rate sensitivity |
| 9 | `PortfolioAnalystAgent` | `src/agents/portfolio.py` | Portfolio optimization requires multi-asset correlation and MPT algorithms |

---

## New Tools Required

| # | Tool | File Path | Primary Consumer |
|---|---|---|---|
| 1 | Peer Comparison | `src/tools/peer_comparison.py` | FundamentalAnalystAgent |
| 2 | Earnings Data | `src/tools/earnings_data.py` | EarningsAnalystAgent |
| 3 | Performance Tracker | `src/tools/performance_tracker.py` | TechnicalAnalyst, RiskAnalyst |
| 4 | Event Analyzer | `src/tools/event_analyzer.py` | EarningsAnalystAgent |
| 5 | Sentiment Engine | `src/tools/sentiment_engine.py` | SentimentAnalystAgent |
| 6 | News Impact | `src/tools/news_impact.py` | SentimentAnalystAgent |
| 7 | Backtesting Engine | `src/tools/backtesting_engine.py` | BacktestingAgent |
| 8 | Strategy Definitions | `src/tools/strategy_definitions.py` | BacktestingAgent |
| 9 | Theme Mapper | `src/tools/theme_mapper.py` | ThematicAnalystAgent |
| 10 | Disruption Metrics | `src/tools/disruption_metrics.py` | DisruptionAnalystAgent |
| 11 | Market Terminal | `src/tools/market_terminal.py` | API routes |
| 12 | Report Formatter | `src/tools/report_formatter.py` | ReportGeneratorAgent |
| 13 | Chart Generator | `src/tools/chart_generator.py` | ReportGeneratorAgent |
| 14 | Insight Engine | `src/tools/insight_engine.py` | ObservationsAgent |
| 15 | Insider Tracker | `src/tools/insider_tracker.py` | FundamentalAnalystAgent |
| 16 | Institutional Tracker | `src/tools/institutional_tracker.py` | FundamentalAnalystAgent |
| 17 | Options Analyzer | `src/tools/options_analyzer.py` | OptionsAnalystAgent |
| 18 | Short Interest | `src/tools/short_interest.py` | RiskAnalystAgent |
| 19 | Dividend Analyzer | `src/tools/dividend_analyzer.py` | DividendAnalystAgent |
| 20 | Analyst Tracker | `src/tools/analyst_tracker.py` | FundamentalAnalystAgent |
| 21 | Macro Data | `src/tools/macro_data.py` | MacroAnalystAgent |
| 22 | Macro Analyzer | `src/tools/macro_analyzer.py` | MacroAnalystAgent |
| 23 | Alert Manager | `src/tools/alert_manager.py` | AlertService |
| 24 | Portfolio Optimizer | `src/tools/portfolio_optimizer.py` | PortfolioAnalystAgent |

---

## Phased Implementation Roadmap

### Phase 0: Foundation Fixes (Weeks 1-2)

**Goal**: Fix gaps between what `agents.yaml` advertises and what the code delivers.

| Task | Feature | Effort |
|---|---|---|
| Implement Beta calculation in `risk.py` | Feature 5 | 1 day |
| Implement Sortino ratio in `risk.py` | Feature 5 | 1 day |
| Replace hardcoded sentiment endpoint | Feature 9 | 1 day |
| Replace hardcoded market summary endpoint | Feature 10 | 1 day |
| Create `performance_tracker.py` tool | Feature 5 | 3 days |

### Phase 1: Core Analysis Enhancements (Weeks 3-6)

**Goal**: Build foundational features that everything else depends on.

| Task | Feature | Effort |
|---|---|---|
| Build `peer_comparison.py` tool | Feature 2 | 3 days |
| Replace hardcoded `compare_to_industry()` | Feature 2 | 2 days |
| Create `EarningsAnalystAgent` | Feature 4 | 4 days |
| Create `earnings_data.py` tool | Feature 4 | 3 days |
| Integrate FinBERT into sentiment | Feature 9 | 4 days |
| Expand `news_fetcher.py` with multiple sources | Feature 9 | 3 days |

### Phase 2: Event-Driven and Reporting (Weeks 7-10)

**Goal**: Build on Phase 1 to deliver user-facing features.

| Task | Feature | Effort |
|---|---|---|
| Create `event_analyzer.py` tool | Feature 7 | 4 days |
| Build event-driven analysis pipeline | Feature 7 | 3 days |
| Create `chart_generator.py` | Feature 6 | 4 days |
| Create `report_formatter.py` (PDF, MD, HTML) | Feature 6 | 5 days |
| Create `ObservationsAgent` | Feature 11 | 4 days |
| Create `insight_engine.py` | Feature 11 | 3 days |

### Phase 3: Advanced Features (Weeks 11-16)

**Goal**: Complex, differentiating features.

| Task | Feature | Effort |
|---|---|---|
| Create `ThematicAnalystAgent` + tools | Feature 1 | 5 days |
| Create `BacktestingAgent` + engine | Feature 8 | 8 days |
| Create predefined strategies | Feature 8 | 3 days |
| Create `DisruptionAnalystAgent` + tools | Feature 3 | 5 days |

### Phase 4: Smart Money & Income (Weeks 17-22)

**Goal**: Track what insiders, institutions, and income investors care about.

| Task | Feature | Effort |
|---|---|---|
| Create `insider_tracker.py` tool | Feature 12 | 2 days |
| Create `institutional_tracker.py` tool | Feature 12 | 2 days |
| Create `dividend_analyzer.py` tool | Feature 15 | 3 days |
| Create `DividendAnalystAgent` | Feature 15 | 2 days |
| Create `analyst_tracker.py` tool | Feature 16 | 2 days |
| Create `short_interest.py` tool | Feature 14 | 2 days |

### Phase 5: Options & Macro (Weeks 23-28)

**Goal**: Advanced analysis for sophisticated investors.

| Task | Feature | Effort |
|---|---|---|
| Create `options_analyzer.py` tool | Feature 13 | 4 days |
| Create `OptionsAnalystAgent` | Feature 13 | 3 days |
| Create `macro_data.py` tool (FRED integration) | Feature 17 | 4 days |
| Create `macro_analyzer.py` tool | Feature 17 | 3 days |
| Create `MacroAnalystAgent` | Feature 17 | 3 days |

### Phase 6: Portfolio & Alerts (Weeks 29-34)

**Goal**: Portfolio management and proactive notifications.

| Task | Feature | Effort |
|---|---|---|
| Create `portfolio_optimizer.py` tool | Feature 19 | 5 days |
| Create `PortfolioAnalystAgent` | Feature 19 | 3 days |
| Create `alert_manager.py` tool | Feature 18 | 4 days |
| Create `alert_scheduler.py` service | Feature 18 | 4 days |
| Create `notification_service.py` | Feature 18 | 3 days |
| Add WebSocket for real-time alerts | Feature 18 | 3 days |

### Phase 7: Terminal Experience (Weeks 35-38)

**Goal**: Bloomberg-like market command center.

| Task | Feature | Effort |
|---|---|---|
| Build `market_terminal.py` with real data | Feature 10 | 5 days |
| Add sector heatmap and market breadth | Feature 10 | 3 days |
| Add Finnhub WebSocket (optional) | Feature 10 | 4 days |
| Build WebSocket API endpoint | Feature 10 | 3 days |

---

## Priority Matrix

| Priority | Features | Rationale |
|---|---|---|
| **P0** (Build First) | Feature 2: Peer Comparison | Most critical gap, no dependencies, enriches everything |
| | Feature 4: Quarterly Earnings | Foundational financial data, many features depend on it |
| | Feature 5: Stock Performance | Fills Beta/Sortino gaps, required by 4+ features |
| | Feature 9: Enhanced News/Sentiment | Current implementation is non-functional |
| **P1** (Build Next) | Feature 1: Thematic Investing | Strong differentiation, depends on P0 features |
| | Feature 6: Enhanced Reports | Libraries already installed, big user value |
| | Feature 7: Event Performance | Explicitly requested by user, high interest |
| | Feature 11: Observations | Capstone that makes everything more useful |
| | Feature 12: Insider/Institutional | Data already in yfinance, high signal value, low effort |
| | Feature 14: Short Interest | Important risk metric, mostly available in yfinance |
| | Feature 15: Dividend Analysis | Income investing is popular, data fully available |
| | Feature 16: Analyst Consensus | Data fully available in yfinance, frequently requested |
| **P2** (Build Last) | Feature 3: Disruption | LLM-heavy, hard to validate, niche |
| | Feature 8: Backtesting | High effort, high value, many dependencies |
| | Feature 10: Bloomberg Terminal | Largest scope, best delivered incrementally |
| | Feature 13: Options Flow | Complex to implement correctly, sophisticated users only |
| | Feature 17: Macro Integration | Requires FRED API, more complex implementation |
| | Feature 18: Alert System | Requires background infrastructure (scheduler, Redis) |
| | Feature 19: Portfolio Optimization | Sophisticated MPT algorithms, multi-asset focus |

---

## API Endpoints Summary (New)

| Method | Endpoint | Feature | Description |
|---|---|---|---|
| `GET` | `/api/v1/peers/{symbol}` | Feature 2 | Peer comparison |
| `GET` | `/api/v1/earnings/{symbol}` | Feature 4 | Quarterly earnings |
| `GET` | `/api/v1/performance/{symbol}` | Feature 5 | Performance tracking |
| `GET` | `/api/v1/events/{symbol}` | Feature 7 | Event-driven analysis |
| `POST` | `/api/v1/backtest` | Feature 8 | Strategy backtesting |
| `POST` | `/api/v1/theme/{theme_name}` | Feature 1 | Thematic analysis |
| `GET` | `/api/v1/themes` | Feature 1 | List available themes |
| `GET` | `/api/v1/observations/{symbol}` | Feature 11 | Key observations |
| `GET` | `/api/v1/terminal/overview` | Feature 10 | Market overview |
| `GET` | `/api/v1/terminal/sectors` | Feature 10 | Sector heatmap |
| `GET` | `/api/v1/terminal/breadth` | Feature 10 | Market breadth |
| `GET` | `/api/v1/terminal/movers` | Feature 10 | Top gainers/losers |
| `WS` | `/api/v1/terminal/stream` | Feature 10 | Real-time updates |
| `GET` | `/api/v1/insiders/{symbol}` | Feature 12 | Insider transactions |
| `GET` | `/api/v1/institutions/{symbol}` | Feature 12 | Institutional ownership |
| `GET` | `/api/v1/options/{symbol}` | Feature 13 | Options flow analysis |
| `GET` | `/api/v1/shorts/{symbol}` | Feature 14 | Short interest data |
| `GET` | `/api/v1/dividends/{symbol}` | Feature 15 | Dividend analysis |
| `GET` | `/api/v1/analysts/{symbol}` | Feature 16 | Analyst consensus |
| `GET` | `/api/v1/macro` | Feature 17 | Macro environment |
| `GET` | `/api/v1/macro/impact/{symbol}` | Feature 17 | Stock macro sensitivity |
| `POST` | `/api/v1/alerts` | Feature 18 | Create alert |
| `GET` | `/api/v1/alerts` | Feature 18 | List alerts |
| `DELETE` | `/api/v1/alerts/{id}` | Feature 18 | Delete alert |
| `GET` | `/api/v1/alerts/triggered` | Feature 18 | Triggered alerts |
| `WS` | `/api/v1/alerts/stream` | Feature 18 | Real-time alert notifications |
| `POST` | `/api/v1/portfolio/optimize` | Feature 19 | Portfolio optimization |

---

## Success Criteria

### Phase 0 Complete When

- [ ] Beta and Sortino calculations work in risk analysis
- [ ] Sentiment endpoint returns real analysis (not hardcoded)
- [ ] Market summary returns live data (not hardcoded)
- [ ] Performance metrics available for any stock

### Phase 1 Complete When

- [ ] Peer comparison returns real peer data for any stock
- [ ] Quarterly earnings history available for last 8 quarters
- [ ] FinBERT produces accurate financial sentiment scores
- [ ] News aggregation from 3+ sources with deduplication

### Phase 2 Complete When

- [ ] Event performance shows before/after analysis for earnings
- [ ] PDF reports generate with charts and professional formatting
- [ ] Key observations synthesize insights across all analysis types

### Phase 3 Complete When

- [ ] Thematic analysis covers 10+ predefined themes
- [ ] Backtesting runs 5 predefined strategies with performance metrics
- [ ] Disruption scoring classifies companies as disruptors or at-risk

### Phase 4 Complete When

- [ ] Insider transactions displayed with net activity scoring
- [ ] Institutional ownership changes tracked quarter-over-quarter
- [ ] Dividend safety score calculated with growth history
- [ ] Analyst consensus aggregated with revision tracking
- [ ] Short interest displayed with squeeze scoring

### Phase 5 Complete When

- [ ] Options flow analysis shows put/call ratio and unusual activity
- [ ] Implied volatility compared to historical with IV percentile
- [ ] Macro environment data fetched from FRED API
- [ ] Stock-level macro sensitivity calculated (rate, inflation, cycle)
- [ ] Sector rotation signals based on economic cycle

### Phase 6 Complete When

- [ ] Portfolio optimizer generates efficient frontier
- [ ] Correlation matrix identifies concentration risks
- [ ] Max Sharpe and Min Variance portfolios calculated
- [ ] Alert system monitors price, technical, and news conditions
- [ ] WebSocket delivers real-time alert notifications

### Phase 7 Complete When

- [ ] Market terminal shows real-time index and sector data
- [ ] Market breadth indicators computed from S&P 500 components
- [ ] WebSocket endpoint delivers streaming updates

---

**Document Version**: 2.0
**Last Updated**: February 16, 2026
**Status**: Ready for Implementation
