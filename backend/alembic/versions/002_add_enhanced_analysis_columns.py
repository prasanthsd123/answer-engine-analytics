"""Add enhanced analysis columns for citation attribution and context analysis

Revision ID: 002_enhanced_analysis
Revises: 001_brand_research
Create Date: 2025-01-22

"""
from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_enhanced_analysis'
down_revision: Union[str, None] = '001_brand_research'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect database dialect
    dialect = context.get_context().dialect.name

    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import JSON
        json_type = JSON
    else:
        json_type = sa.JSON

    # Add enhanced citation analysis columns (Phase 2)
    op.add_column('analysis_results', sa.Column('brand_attributed_citations', sa.Integer, server_default='0'))
    op.add_column('analysis_results', sa.Column('citation_quality', json_type, server_default='{}'))

    # Add context analysis columns (Phase 3)
    op.add_column('analysis_results', sa.Column('mention_type_breakdown', json_type, server_default='{}'))
    op.add_column('analysis_results', sa.Column('comparison_stats', json_type, server_default='{}'))

    # Add aspect-based sentiment columns (Phase 4)
    op.add_column('analysis_results', sa.Column('aspect_sentiments', json_type, server_default='[]'))
    op.add_column('analysis_results', sa.Column('dominant_aspect', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('analysis_results', 'dominant_aspect')
    op.drop_column('analysis_results', 'aspect_sentiments')
    op.drop_column('analysis_results', 'comparison_stats')
    op.drop_column('analysis_results', 'mention_type_breakdown')
    op.drop_column('analysis_results', 'citation_quality')
    op.drop_column('analysis_results', 'brand_attributed_citations')
