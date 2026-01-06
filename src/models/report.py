"""
Report data models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class RecommendationType(str, Enum):
    """Investment recommendation types."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class Recommendation(BaseModel):
    """Investment recommendation."""
    action: RecommendationType = RecommendationType.HOLD
    confidence: float = Field(default=0.5, ge=0, le=1)
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    time_horizon: str = "medium_term"
    reasoning: str = ""
    risks: List[str] = Field(default_factory=list)
    catalysts: List[str] = Field(default_factory=list)


class ReportSection(BaseModel):
    """A section in the research report."""
    title: str
    content: str
    data: Dict[str, Any] = Field(default_factory=dict)
    charts: List[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    """Complete investment research report."""
    report_id: str = ""
    symbol: str
    company_name: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    analyst: str = "AI Financial Research Agent"
    
    executive_summary: str = ""
    recommendation: Recommendation = Field(default_factory=Recommendation)
    
    sections: List[ReportSection] = Field(default_factory=list)
    
    # Analysis summaries
    technical_summary: str = ""
    fundamental_summary: str = ""
    sentiment_summary: str = ""
    risk_summary: str = ""
    
    # Key metrics
    current_price: float = 0.0
    fair_value_estimate: Optional[float] = None
    upside_potential: Optional[float] = None
    
    # Metadata
    data_sources: List[str] = Field(default_factory=list)
    disclaimers: str = "This report is for informational purposes only and does not constitute investment advice."
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
    
    def to_markdown(self) -> str:
        """Convert report to markdown format."""
        md = []
        md.append(f"# Investment Research Report: {self.symbol}")
        md.append(f"**Company:** {self.company_name}")
        md.append(f"**Date:** {self.generated_at.strftime('%Y-%m-%d')}")
        md.append(f"**Analyst:** {self.analyst}")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## Executive Summary")
        md.append(self.executive_summary)
        md.append("")
        md.append("## Recommendation")
        md.append(f"**Action:** {self.recommendation.action.value}")
        md.append(f"**Confidence:** {self.recommendation.confidence * 100:.0f}%")
        if self.recommendation.target_price:
            md.append(f"**Target Price:** ${self.recommendation.target_price:.2f}")
        md.append(f"**Reasoning:** {self.recommendation.reasoning}")
        md.append("")
        
        for section in self.sections:
            md.append(f"## {section.title}")
            md.append(section.content)
            md.append("")
        
        md.append("---")
        md.append(f"*{self.disclaimers}*")
        
        return "\n".join(md)
    
    def to_text(self) -> str:
        """Convert report to plain text format."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"INVESTMENT RESEARCH REPORT: {self.symbol}")
        lines.append("=" * 80)
        lines.append(f"Company: {self.company_name}")
        lines.append(f"Date: {self.generated_at.strftime('%Y-%m-%d')}")
        lines.append("-" * 80)
        lines.append("")
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 40)
        lines.append(self.executive_summary)
        lines.append("")
        lines.append("RECOMMENDATION")
        lines.append("-" * 40)
        lines.append(f"Action: {self.recommendation.action.value}")
        lines.append(f"Confidence: {self.recommendation.confidence * 100:.0f}%")
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
