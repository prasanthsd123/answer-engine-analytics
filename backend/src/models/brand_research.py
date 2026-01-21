"""
BrandResearch model for storing comprehensive brand research data.

This model stores the results of:
1. Website scraping (products, features, testimonials)
2. Perplexity market research (competitors, reviews, trends)
3. Combined analysis for question generation
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Uuid, JSON, Integer, Float, Boolean
from sqlalchemy.orm import relationship

from ..database import Base


class BrandResearchRecord(Base):
    """
    Stores comprehensive research data for a brand.

    This data is used to generate smart, realistic user questions.
    Research is cached for 30 days to save API costs.
    """

    __tablename__ = "brand_research"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    brand_id = Column(Uuid, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)

    # ===== WEBSITE SCRAPE DATA =====
    website_data = Column(JSON, default=dict)  # Products, features, testimonials from website
    pages_crawled = Column(Integer, default=0)
    website_raw_content = Column(JSON, default=dict)  # Raw content by page type

    # ===== PERPLEXITY RESEARCH DATA =====
    perplexity_research = Column(JSON, default=dict)  # Full Perplexity analysis
    perplexity_citations = Column(JSON, default=list)  # Source URLs from Perplexity

    # ===== COMBINED ANALYSIS =====
    # Market landscape
    market_landscape = Column(Text, nullable=True)  # Summary of market position
    market_position = Column(String(100), nullable=True)  # leader, challenger, niche, etc.

    # Competitors (discovered from research)
    discovered_competitors = Column(JSON, default=list)  # [{name, domain, description}]
    competitor_comparison = Column(JSON, default=dict)  # Feature/pricing comparison

    # Customer insights
    customer_industries = Column(JSON, default=list)  # Industries using this product
    customer_personas = Column(JSON, default=list)  # Job titles/roles
    customer_company_sizes = Column(JSON, default=list)  # startup, SMB, enterprise
    customer_pain_points = Column(JSON, default=list)  # Problems they solve
    customer_reviews_summary = Column(Text, nullable=True)  # G2/Capterra review summary

    # Product details
    products_discovered = Column(JSON, default=list)  # Products found
    features_discovered = Column(JSON, default=list)  # Features found
    use_cases = Column(JSON, default=list)  # Use cases from research

    # Pricing
    pricing_analysis = Column(JSON, default=dict)  # Pricing model, tiers, comparison

    # Industry/trends
    industry = Column(String(100), nullable=True)
    industry_trends = Column(JSON, default=list)  # Current trends in the industry

    # ===== METADATA =====
    research_quality_score = Column(Float, default=0.0)  # 0-1 quality score
    research_sources_count = Column(Integer, default=0)  # Number of sources used
    perplexity_queries_made = Column(Integer, default=0)  # API calls to Perplexity

    # Research status
    is_complete = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))

    # Relationships
    brand = relationship("Brand", back_populates="research_records")

    def __repr__(self):
        return f"<BrandResearch brand_id={self.brand_id} quality={self.research_quality_score}>"

    @property
    def is_expired(self) -> bool:
        """Check if research needs to be refreshed."""
        if not self.expires_at:
            return True
        return datetime.utcnow() > self.expires_at

    def get_full_research_context(self) -> dict:
        """Get combined research data for question generation."""
        return {
            "brand_id": str(self.brand_id),
            "website_data": self.website_data or {},
            "perplexity_research": self.perplexity_research or {},
            "market_landscape": self.market_landscape,
            "market_position": self.market_position,
            "competitors": self.discovered_competitors or [],
            "competitor_comparison": self.competitor_comparison or {},
            "customer_industries": self.customer_industries or [],
            "customer_personas": self.customer_personas or [],
            "customer_company_sizes": self.customer_company_sizes or [],
            "customer_pain_points": self.customer_pain_points or [],
            "customer_reviews_summary": self.customer_reviews_summary,
            "products": self.products_discovered or [],
            "features": self.features_discovered or [],
            "use_cases": self.use_cases or [],
            "pricing": self.pricing_analysis or {},
            "industry": self.industry,
            "industry_trends": self.industry_trends or [],
            "citations": self.perplexity_citations or [],
            "quality_score": self.research_quality_score,
        }
