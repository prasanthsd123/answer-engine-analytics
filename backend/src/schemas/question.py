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


class SmartQuestionGenerateRequest(BaseModel):
    """Schema for AI-powered smart question generation."""
    num_questions: int = Field(default=20, ge=5, le=50)
    research_website: bool = Field(
        default=True,
        description="Whether to crawl the brand's website for research"
    )
    focus_intents: Optional[List[str]] = Field(
        default=None,
        description="Specific intents to focus on: discovery, comparison, evaluation, feature, problem_solving, review, pricing"
    )
    additional_urls: Optional[List[str]] = Field(
        default=None,
        description="Additional URLs to crawl (for small websites or specific pages like /blog, /docs)"
    )


class SmartQuestionResponse(BaseModel):
    """Response for a smart-generated question."""
    text: str
    category: str
    intent: str
    priority: int

    class Config:
        from_attributes = True


class SmartGenerateResponse(BaseModel):
    """Response for smart question generation."""
    questions_generated: int
    questions: List[QuestionResponse]
    research_summary: Optional[dict] = None
