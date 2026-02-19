"""
API request/response schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class AnalysisType(str, Enum):
    """Types of analysis available."""
    COMPREHENSIVE = "comprehensive"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    RISK = "risk"
    THEMATIC = "thematic"


class AnalysisRequest(BaseModel):
    """Request for stock analysis."""
    symbol: str = Field(..., description="Stock ticker symbol", example="AAPL")
    analysis_type: AnalysisType = Field(
        default=AnalysisType.COMPREHENSIVE,
        description="Type of analysis to perform"
    )
    include_news: bool = Field(default=True, description="Include news analysis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "analysis_type": "comprehensive",
                "include_news": True
            }
        }


class PortfolioRequest(BaseModel):
    """Request for portfolio analysis."""
    symbols: List[str] = Field(..., description="List of stock symbols")
    weights: Optional[List[float]] = Field(
        default=None,
        description="Portfolio weights (optional, defaults to equal weight)"
    )


class ReportRequest(BaseModel):
    """Request for report generation."""
    symbols: List[str] = Field(..., description="Symbols to include in report")
    format: str = Field(default="json", description="Output format (json, pdf, markdown)")
    include_charts: bool = Field(default=True, description="Include visualizations")


class IndicatorData(BaseModel):
    """Technical indicator data."""
    name: str
    value: float
    signal: str
    interpretation: str


class AnalysisResponse(BaseModel):
    """Response containing analysis results."""
    symbol: str
    analysis_type: str
    current_price: float
    recommendation: str
    confidence: float
    summary: str
    technical: Optional[Dict[str, Any]] = None
    fundamental: Optional[Dict[str, Any]] = None
    sentiment: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    analyzed_at: datetime
    execution_time_seconds: float
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class PortfolioResponse(BaseModel):
    """Response containing portfolio analysis."""
    symbols: List[str]
    total_value: Optional[float] = None
    individual_analyses: List[Dict[str, Any]]
    portfolio_metrics: Dict[str, Any]
    diversification_score: float
    risk_assessment: str
    recommendations: List[str]
    analyzed_at: datetime


class ReportResponse(BaseModel):
    """Response containing generated report."""
    report_id: str
    symbols: List[str]
    format: str
    content: str
    download_url: Optional[str] = None
    generated_at: datetime


class HealthResponse(BaseModel):
    """API health check response following industry standards."""
    status: str = Field(
        ...,
        description="Overall health status: healthy, degraded, or unhealthy",
        example="healthy"
    )
    version: str = Field(..., description="API version", example="1.0.0")
    timestamp: datetime = Field(..., description="Health check timestamp")
    uptime_seconds: float = Field(..., description="API uptime in seconds")
    checks: Dict[str, str] = Field(
        ...,
        description="Individual service health checks",
        example={
            "market_data": "healthy",
            "agent_engine": "healthy",
            "data_processing": "healthy"
        }
    )
    response_time_ms: Optional[float] = Field(
        None,
        description="Health check response time in milliseconds"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ThemeAnalysisRequest(BaseModel):
    """Request for thematic investing analysis."""
    theme_id: str = Field(
        ...,
        description="Theme identifier (e.g., 'ai_machine_learning', 'electric_vehicles')",
        example="ai_machine_learning",
    )
    include_narrative: bool = Field(
        default=False,
        description="Include LLM-generated narrative outlook",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "theme_id": "ai_machine_learning",
                "include_narrative": False,
            }
        }


class ThemeCompareRequest(BaseModel):
    """Request to compare multiple themes."""
    theme_ids: List[str] = Field(
        ...,
        description="List of theme identifiers to compare",
        example=["ai_machine_learning", "cybersecurity"],
    )


class ThemePerformance(BaseModel):
    """Theme performance across time horizons."""
    period_1w: Optional[str] = Field(None, alias="1w")
    period_1m: Optional[str] = Field(None, alias="1m")
    period_3m: Optional[str] = Field(None, alias="3m")
    period_6m: Optional[str] = Field(None, alias="6m")
    period_1y: Optional[str] = Field(None, alias="1y")
    period_ytd: Optional[str] = Field(None, alias="ytd")


class ThemeRisk(BaseModel):
    """Theme risk metrics."""
    intra_correlation: Optional[float] = None
    diversification_score: str = "N/A"
    diversification_description: str = ""


class ThemeAnalysisResponse(BaseModel):
    """Response containing thematic analysis results."""
    theme: str
    theme_id: str
    description: str = ""
    constituents: List[str]
    reference_etfs: List[str] = []
    risk_level: str = "Unknown"
    growth_stage: str = "Unknown"
    theme_performance: Dict[str, Any] = {}
    momentum_score: int = 0
    top_performers: List[Dict[str, Any]] = []
    laggards: List[Dict[str, Any]] = []
    sector_overlap: Dict[str, str] = {}
    theme_risk: Dict[str, Any] = {}
    theme_health_score: int = 0
    health_components: Dict[str, Any] = {}
    constituent_details: Dict[str, Any] = {}
    failed_constituents: List[str] = []
    outlook: Optional[str] = None
    analyzed_at: datetime
    execution_time_seconds: Optional[float] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ThemeSummary(BaseModel):
    """Summary information for a single theme."""
    theme_id: str
    name: str
    description: str = ""
    constituent_count: int = 0
    constituents: List[str] = []
    reference_etfs: List[str] = []
    sector_tags: List[str] = []
    risk_level: str = "Unknown"
    growth_stage: str = "Unknown"


class ThemeListResponse(BaseModel):
    """Response listing all available themes."""
    themes: List[ThemeSummary]
    total_themes: int
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PeerComparisonRequest(BaseModel):
    """Request for peer group analysis."""
    symbol: str = Field(..., description="Target stock symbol")
    peers: Optional[List[str]] = Field(None, description="Optional list of specific peers to compare against")


class PeerComparisonResponse(BaseModel):
    """Response containing peer comparison analysis."""
    target: str
    peer_group: List[str]
    metrics: Dict[str, Dict[str, Any]]
    peer_aggregates: Dict[str, Dict[str, float]]
    percentile_rankings: Dict[str, str]
    relative_valuation: Dict[str, str]
    strengths: List[str]
    weaknesses: List[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
