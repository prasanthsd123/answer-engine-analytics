"""
QueryExecution model for tracking AI platform queries.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, Uuid, JSON
from sqlalchemy.orm import relationship

from ..database import Base


class QueryExecution(Base):
    """Query execution model for tracking AI platform responses."""

    __tablename__ = "query_executions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    question_id = Column(Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)

    # Platform info
    platform = Column(String(50), nullable=False)  # chatgpt, claude, perplexity, gemini
    model_used = Column(String(100), nullable=True)  # gpt-4o, claude-3-opus, etc.

    # Response data
    raw_response = Column(Text, nullable=True)
    response_metadata = Column(JSON, default=dict)  # tokens, latency, etc.

    # Execution status
    status = Column(String(20), default="pending")  # pending, completed, failed
    error_message = Column(Text, nullable=True)

    # Timing
    executed_at = Column(DateTime, default=datetime.utcnow)
    response_time_ms = Column(Integer, nullable=True)

    # Relationships
    question = relationship("Question", back_populates="executions")
    analysis = relationship("AnalysisResult", back_populates="execution", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QueryExecution {self.platform} - {self.status}>"
