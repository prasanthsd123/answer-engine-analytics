"""
Question schemas for API validation.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class QuestionBase(BaseModel):
    """Base question schema."""
    question_text: str = Field(..., min_length=5, max_length=1000)
    category: Optional[str] = None


class QuestionCreate(QuestionBase):
    """Schema for creating a question."""
    pass


class QuestionBulkCreate(BaseModel):
    """Schema for bulk creating questions."""
    questions: List[QuestionCreate]


class QuestionUpdate(BaseModel):
    """Schema for updating a question."""
    question_text: Optional[str] = Field(None, min_length=5, max_length=1000)
    category: Optional[str] = None
    is_active: Optional[bool] = None


class QuestionResponse(QuestionBase):
    """Schema for question response."""
    id: UUID
    brand_id: UUID
    is_active: bool
    created_at: datetime
    last_executed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QuestionListResponse(BaseModel):
    """Schema for paginated question list response."""
    items: List[QuestionResponse]
    total: int
    page: int
    page_size: int


class QuestionGenerateRequest(BaseModel):
    """Schema for automatic question generation request."""
    categories: Optional[List[str]] = None  # If None, generate for all categories
    include_competitors: bool = True
    max_questions_per_category: int = Field(default=5, ge=1, le=20)
