"""Create brand_research table for Perplexity market research caching

Revision ID: 001_brand_research
Revises: None
Create Date: 2025-01-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision: str = '001_brand_research'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'brand_research',
        # Primary key
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('brand_id', UUID(as_uuid=True), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=False),

        # Website scrape data
        sa.Column('website_data', JSON, server_default='{}'),
        sa.Column('pages_crawled', sa.Integer, server_default='0'),
        sa.Column('website_raw_content', JSON, server_default='{}'),

        # Perplexity research data
        sa.Column('perplexity_research', JSON, server_default='{}'),
        sa.Column('perplexity_citations', JSON, server_default='[]'),

        # Combined analysis - Market
        sa.Column('market_landscape', sa.Text, nullable=True),
        sa.Column('market_position', sa.String(100), nullable=True),

        # Competitors
        sa.Column('discovered_competitors', JSON, server_default='[]'),
        sa.Column('competitor_comparison', JSON, server_default='{}'),

        # Customer insights
        sa.Column('customer_industries', JSON, server_default='[]'),
        sa.Column('customer_personas', JSON, server_default='[]'),
        sa.Column('customer_company_sizes', JSON, server_default='[]'),
        sa.Column('customer_pain_points', JSON, server_default='[]'),
        sa.Column('customer_reviews_summary', sa.Text, nullable=True),

        # Product details
        sa.Column('products_discovered', JSON, server_default='[]'),
        sa.Column('features_discovered', JSON, server_default='[]'),
        sa.Column('use_cases', JSON, server_default='[]'),

        # Pricing
        sa.Column('pricing_analysis', JSON, server_default='{}'),

        # Industry/trends
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('industry_trends', JSON, server_default='[]'),

        # Metadata
        sa.Column('research_quality_score', sa.Float, server_default='0.0'),
        sa.Column('research_sources_count', sa.Integer, server_default='0'),
        sa.Column('perplexity_queries_made', sa.Integer, server_default='0'),

        # Research status
        sa.Column('is_complete', sa.Boolean, server_default='false'),
        sa.Column('error_message', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime, server_default=sa.text("NOW() + INTERVAL '30 days'")),
    )

    # Create index on brand_id for faster lookups
    op.create_index('ix_brand_research_brand_id', 'brand_research', ['brand_id'])

    # Create index on expires_at for cache cleanup queries
    op.create_index('ix_brand_research_expires_at', 'brand_research', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_brand_research_expires_at')
    op.drop_index('ix_brand_research_brand_id')
    op.drop_table('brand_research')
