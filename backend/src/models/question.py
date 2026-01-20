"""
Question model for generated research questions.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Uuid
from sqlalchemy.orm import relationship

from ..database import Base


class Question(Base):
    """Generated question model for querying AI platforms."""

    __tablename__ = "questions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    brand_id = Column(Uuid, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)

    # Question content
    question_text = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)  # product_recommendations, brand_perception, etc.

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_executed_at = Column(DateTime, nullable=True)

    # Relationships
    brand = relationship("Brand", back_populates="questions")
    executions = relationship("QueryExecution", back_populates="question", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Question {self.question_text[:50]}...>"
