"""
Analysis data models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TechnicalIndicators(BaseModel):
    """Technical indicator values."""
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None


class TechnicalAnalysis(BaseModel):
    """Technical analysis results."""
    symbol: str
    trend: str = "neutral"
    trend_strength: float = 0.5
    indicators: TechnicalIndicators = Field(default_factory=TechnicalIndicators)
    support_levels: List[float] = Field(default_factory=list)
    resistance_levels: List[float] = Field(default_factory=list)
    patterns: List[Dict[str, Any]] = Field(default_factory=list)
    signal: str = "HOLD"
    confidence: float = 0.5
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class ValuationMetrics(BaseModel):
    """Valuation ratio metrics."""
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    peg_ratio: Optional[float] = None


class ProfitabilityMetrics(BaseModel):
    """Profitability metrics."""
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    roic: Optional[float] = None


class FundamentalAnalysis(BaseModel):
    """Fundamental analysis results."""
    symbol: str
    company_name: str = ""
    sector: str = ""
    industry: str = ""
    market_cap: float = 0
    valuation: ValuationMetrics = Field(default_factory=ValuationMetrics)
    profitability: ProfitabilityMetrics = Field(default_factory=ProfitabilityMetrics)
    valuation_status: str = "fairly_valued"
    growth_score: float = 5.0
    quality_score: float = 5.0
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class SentimentAnalysis(BaseModel):
    """Sentiment analysis results."""
    symbol: str
    overall_sentiment: str = "neutral"
    sentiment_score: float = 0.0
    news_sentiment: float = 0.0
    social_sentiment: float = 0.0
    analyst_sentiment: float = 0.0
    news_volume: int = 0
    key_themes: List[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class RiskMetrics(BaseModel):
    """Risk analysis metrics."""
    volatility_daily: float = 0.0
    volatility_annual: float = 0.0
    var_95: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    beta: Optional[float] = None
    risk_level: str = "medium"


class AnalysisResult(BaseModel):
    """Complete analysis result combining all analyses."""
    symbol: str
    current_price: float = 0.0
    technical: Optional[TechnicalAnalysis] = None
    fundamental: Optional[FundamentalAnalysis] = None
    sentiment: Optional[SentimentAnalysis] = None
    risk: Optional[RiskMetrics] = None
    overall_score: float = 5.0
    recommendation: str = "HOLD"
    confidence: float = 0.5
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
