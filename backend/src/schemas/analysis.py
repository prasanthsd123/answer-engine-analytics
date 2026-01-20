"""
Analysis and metrics schemas for API responses.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class CitationInfo(BaseModel):
    """Citation information from AI response."""
    url: str
    domain: str
    title: Optional[str] = None


class MentionContext(BaseModel):
    """Context around a brand mention."""
    text: str
    position: Optional[int] = None
    sentiment: Optional[str] = None


class CompetitorMention(BaseModel):
    """Competitor mention analysis."""
    name: str
    count: int
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None


class AnalysisResponse(BaseModel):
    """Schema for analysis result response."""
    id: UUID
    execution_id: UUID
    brand_mentioned: bool
    mention_count: int
    mention_contexts: List[MentionContext]
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_confidence: Optional[float] = None
    position: Optional[int] = None
    total_recommendations: Optional[int] = None
    citations: List[CitationInfo]
    citation_count: int
    competitor_mentions: Dict[str, CompetitorMention]
    analyzed_at: datetime

    class Config:
        from_attributes = True


class PlatformMetrics(BaseModel):
    """Metrics for a specific AI platform."""
    platform: str
    mentions: int
    sentiment_avg: Optional[float] = None
    position_avg: Optional[float] = None
    visibility_score: Optional[float] = None
    total_queries: int
    successful_queries: int


class DailyMetricsResponse(BaseModel):
    """Schema for daily metrics response."""
    id: UUID
    brand_id: UUID
    date: date
    visibility_score: Optional[float] = None
    sentiment_avg: Optional[float] = None
    mention_count: int
    share_of_voice: Optional[float] = None
    platform_breakdown: Dict[str, PlatformMetrics]
    top_citations: List[Dict[str, Any]]
    total_queries: int
    successful_queries: int

    class Config:
        from_attributes = True


class VisibilityOverview(BaseModel):
    """High-level visibility overview for dashboard."""
    brand_id: UUID
    brand_name: str
    visibility_score: float = Field(..., ge=0, le=100)
    visibility_change: float  # Change from previous period
    sentiment_score: float = Field(..., ge=-1, le=1)
    sentiment_label: str  # positive, negative, neutral
    share_of_voice: float = Field(..., ge=0, le=100)
    total_mentions: int
    platform_scores: Dict[str, float]  # platform -> visibility score


class TrendDataPoint(BaseModel):
    """Single data point for trend charts."""
    date: date
    value: float
    label: Optional[str] = None


class TrendResponse(BaseModel):
    """Schema for trend data response."""
    metric_name: str
    data_points: List[TrendDataPoint]
    period_start: date
    period_end: date


class CompetitorComparison(BaseModel):
    """Competitor comparison data."""
    name: str
    visibility_score: float
    sentiment_score: float
    mention_count: int
    share_of_voice: float


class CompetitorAnalysisResponse(BaseModel):
    """Schema for competitor analysis response."""
    brand: CompetitorComparison
    competitors: List[CompetitorComparison]
    period_start: date
    period_end: date
