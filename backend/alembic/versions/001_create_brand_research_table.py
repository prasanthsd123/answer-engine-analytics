"""Create brand_research table for Perplexity market research caching

Revision ID: 001_brand_research
Revises: None
Create Date: 2025-01-21

"""
from typing import Sequence, Union
from datetime import datetime, timedelta

from alembic import op, context
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_brand_research'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect database dialect for appropriate defaults
    dialect = context.get_context().dialect.name

    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import UUID, JSON
        id_type = UUID(as_uuid=True)
        id_default = sa.text('gen_random_uuid()')
        json_type = JSON
        now_default = sa.text('NOW()')
        expires_default = sa.text("NOW() + INTERVAL '30 days'")
    else:
        # SQLite compatible
        id_type = sa.String(36)
        id_default = None  # Will be handled by application
        json_type = sa.JSON
        now_default = sa.text("(datetime('now'))")
        expires_default = sa.text("(datetime('now', '+30 days'))")

    op.create_table(
        'brand_research',
        # Primary key
        sa.Column('id', id_type, primary_key=True, server_default=id_default),
        sa.Column('brand_id', sa.String(36), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=False),

        # Website scrape data
        sa.Column('website_data', json_type, server_default='{}'),
        sa.Column('pages_crawled', sa.Integer, server_default='0'),
        sa.Column('website_raw_content', json_type, server_default='{}'),

        # Perplexity research data
        sa.Column('perplexity_research', json_type, server_default='{}'),
        sa.Column('perplexity_citations', json_type, server_default='[]'),

        # Combined analysis - Market
        sa.Column('market_landscape', sa.Text, nullable=True),
        sa.Column('market_position', sa.String(100), nullable=True),

        # Competitors
        sa.Column('discovered_competitors', json_type, server_default='[]'),
        sa.Column('competitor_comparison', json_type, server_default='{}'),

        # Customer insights
        sa.Column('customer_industries', json_type, server_default='[]'),
        sa.Column('customer_personas', json_type, server_default='[]'),
        sa.Column('customer_company_sizes', json_type, server_default='[]'),
        sa.Column('customer_pain_points', json_type, server_default='[]'),
        sa.Column('customer_reviews_summary', sa.Text, nullable=True),

        # Product details
        sa.Column('products_discovered', json_type, server_default='[]'),
        sa.Column('features_discovered', json_type, server_default='[]'),
        sa.Column('use_cases', json_type, server_default='[]'),

        # Pricing
        sa.Column('pricing_analysis', json_type, server_default='{}'),

        # Industry/trends
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('industry_trends', json_type, server_default='[]'),

        # Metadata
        sa.Column('research_quality_score', sa.Float, server_default='0.0'),
        sa.Column('research_sources_count', sa.Integer, server_default='0'),
        sa.Column('perplexity_queries_made', sa.Integer, server_default='0'),

        # Research status
        sa.Column('is_complete', sa.Boolean, server_default='false'),
        sa.Column('error_message', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=now_default),
        sa.Column('updated_at', sa.DateTime, server_default=now_default),
        sa.Column('expires_at', sa.DateTime, server_default=expires_default),
    )

    # Create index on brand_id for faster lookups
    op.create_index('ix_brand_research_brand_id', 'brand_research', ['brand_id'])

    # Create index on expires_at for cache cleanup queries
    op.create_index('ix_brand_research_expires_at', 'brand_research', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_brand_research_expires_at')
    op.drop_index('ix_brand_research_brand_id')
    op.drop_table('brand_research')
