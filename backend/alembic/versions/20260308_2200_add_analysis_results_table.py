"""add_analysis_results_table

Revision ID: add_analysis_results_table
Revises: adf02cf273dd
Create Date: 2026-03-08 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_analysis_results_table'
down_revision: Union[str, Sequence[str], None] = 'adf02cf273dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create analysis_results table
    op.create_table(
        'analysis_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('n_datasets_analyzed', sa.Integer(), nullable=False),
        sa.Column('n_datasets_with_survival', sa.Integer(), nullable=False),
        sa.Column('n_genes_found', sa.Integer(), nullable=False),
        sa.Column('processing_time_seconds', sa.Float(), nullable=True),
        sa.Column('result_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_analysis_results_user_id', 'analysis_results', ['user_id'])
    op.create_index('ix_analysis_results_created_at', 'analysis_results', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_analysis_results_created_at', table_name='analysis_results')
    op.drop_index('ix_analysis_results_user_id', table_name='analysis_results')

    # Drop table
    op.drop_table('analysis_results')
