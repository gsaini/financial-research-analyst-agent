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


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
