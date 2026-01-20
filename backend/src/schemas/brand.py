"""
Brand and Competitor schemas for API validation.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class ProductInfo(BaseModel):
    """Product information within a brand."""
    name: str
    category: Optional[str] = None
    description: Optional[str] = None


class CompetitorBase(BaseModel):
    """Base competitor schema."""
    name: str = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = None


class CompetitorCreate(CompetitorBase):
    """Schema for creating a competitor."""
    pass


class CompetitorResponse(CompetitorBase):
    """Schema for competitor response."""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class BrandBase(BaseModel):
    """Base brand schema."""
    name: str = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None


class BrandCreate(BrandBase):
    """Schema for creating a brand."""
    keywords: List[str] = Field(default_factory=list)
    products: List[ProductInfo] = Field(default_factory=list)
    competitors: List[CompetitorCreate] = Field(default_factory=list)


class BrandUpdate(BaseModel):
    """Schema for updating a brand."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    keywords: Optional[List[str]] = None
    products: Optional[List[ProductInfo]] = None


class BrandResponse(BrandBase):
    """Schema for brand response."""
    id: UUID
    keywords: List[str]
    products: List[ProductInfo]
    competitors: List[CompetitorResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BrandListResponse(BaseModel):
    """Schema for paginated brand list response."""
    items: List[BrandResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
