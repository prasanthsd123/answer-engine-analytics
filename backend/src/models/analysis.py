"""
Analysis models for storing extracted insights from AI responses.
"""

import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, Boolean, Date, UniqueConstraint, Uuid, JSON
from sqlalchemy.orm import relationship

from ..database import Base


class AnalysisResult(Base):
    """Analysis result model for extracted insights from AI responses."""

    __tablename__ = "analysis_results"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    execution_id = Column(Uuid, ForeignKey("query_executions.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Brand mention analysis
    brand_mentioned = Column(Boolean, default=False)
    mention_count = Column(Integer, default=0)
    mention_contexts = Column(JSON, default=list)  # [{"text": "...", "position": 1}]

    # Sentiment analysis
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    sentiment_confidence = Column(Float, nullable=True)  # 0.0 to 1.0

    # Position tracking
    position = Column(Integer, nullable=True)  # rank in recommendation list
    total_recommendations = Column(Integer, nullable=True)

    # Citation analysis
    citations = Column(JSON, default=list)  # [{"url": "...", "domain": "..."}]
    citation_count = Column(Integer, default=0)

    # Competitor mentions
    competitor_mentions = Column(JSON, default=dict)  # {"competitor_name": {"count": 1, "sentiment": "positive"}}

    # Enhanced citation analysis (Phase 2)
    brand_attributed_citations = Column(Integer, default=0)  # Citations that mention the brand
    citation_quality = Column(JSON, default=dict)  # {"avg_authority": 0.7, "source_types": {"review_site": 2, "news": 1}}

    # Context analysis (Phase 3)
    mention_type_breakdown = Column(JSON, default=dict)  # {"recommendation": 3, "criticism": 1, "comparison": 2, "neutral": 1}
    comparison_stats = Column(JSON, default=dict)  # {"total": 2, "wins": 1, "losses": 0, "draws": 1, "targets": {"Competitor": 2}}

    # Aspect-based sentiment (Phase 4)
    aspect_sentiments = Column(JSON, default=list)  # [{"aspect": "pricing", "label": "negative", "score": -0.5}]
    dominant_aspect = Column(String(50), nullable=True)  # Most discussed aspect

    # Timestamps
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    execution = relationship("QueryExecution", back_populates="analysis")

    def __repr__(self):
        return f"<AnalysisResult brand_mentioned={self.brand_mentioned} sentiment={self.sentiment}>"


class DailyMetrics(Base):
    """Aggregated daily metrics for trending and reporting."""

    __tablename__ = "daily_metrics"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    brand_id = Column(Uuid, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    # Core metrics
    visibility_score = Column(Float, nullable=True)  # 0-100
    sentiment_avg = Column(Float, nullable=True)  # -1.0 to 1.0
    mention_count = Column(Integer, default=0)
    share_of_voice = Column(Float, nullable=True)  # 0-100 percentage

    # Platform breakdown
    platform_breakdown = Column(JSON, default=dict)
    # {
    #     "chatgpt": {"mentions": 5, "sentiment": 0.8, "position_avg": 2.3},
    #     "claude": {"mentions": 3, "sentiment": 0.6, "position_avg": 3.1},
    #     ...
    # }

    # Citation stats
    top_citations = Column(JSON, default=list)  # [{"domain": "example.com", "count": 10}]

    # Query stats
    total_queries = Column(Integer, default=0)
    successful_queries = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    brand = relationship("Brand", back_populates="daily_metrics")

    __table_args__ = (
        UniqueConstraint("brand_id", "date", name="uq_brand_date"),
    )

    def __repr__(self):
        return f"<DailyMetrics {self.brand_id} - {self.date}>"
