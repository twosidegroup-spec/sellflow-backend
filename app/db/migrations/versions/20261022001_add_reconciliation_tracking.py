"""Add reconciliation tracking

Revision ID: 20261022001
Revises: 9d562d7d4184
Create Date: 2026-10-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20261022001'
down_revision = '9d562d7d4184'
branch_labels = None
depends_on = None


def upgrade():
    # Create reconciliation tracking table
    op.create_table(
        'reconciliation_runs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('gateway', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('total_transactions', sa.Integer(), nullable=False, default=0),
        sa.Column('matched', sa.Integer(), nullable=False, default=0),
        sa.Column('unmatched_count', sa.Integer(), nullable=False, default=0),
        sa.Column('discrepancy_amount', sa.Numeric(12, 2), nullable=False, default=0.0),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    
    # Create index for faster lookups
    op.create_index('ix_reconciliation_runs_business', 'reconciliation_runs', ['business_id'])


def downgrade():
    op.drop_table('reconciliation_runs')
