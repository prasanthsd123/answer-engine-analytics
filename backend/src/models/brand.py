"""
Brand and Competitor models for tracking monitored brands.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Uuid, JSON
from sqlalchemy.orm import relationship

from ..database import Base


class Brand(Base):
    """Brand model for tracking companies/products in AI search engines."""

    __tablename__ = "brands"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Brand information
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Tracking configuration
    keywords = Column(JSON, default=list)  # ["keyword1", "keyword2"]
    products = Column(JSON, default=list)  # [{"name": "Product A", "category": "SaaS"}]
    industry = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="brands")
    competitors = relationship("Competitor", back_populates="brand", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="brand", cascade="all, delete-orphan")
    daily_metrics = relationship("DailyMetrics", back_populates="brand", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Brand {self.name}>"


class Competitor(Base):
    """Competitor model for tracking competing brands."""

    __tablename__ = "competitors"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    brand_id = Column(Uuid, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    brand = relationship("Brand", back_populates="competitors")

    def __repr__(self):
        return f"<Competitor {self.name}>"
