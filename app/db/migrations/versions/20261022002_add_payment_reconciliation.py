"""Add migration for reconciliation tracking

Revision ID: 20261022002
Revises: 20261022001
Create Date: 2026-10-22 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20261022002'
down_revision = '20261022001'
branch_labels = None
depends_on = None


def upgrade():
    # Add reconciliation fields to payments table
    op.add_column('payments', sa.Column('reconciliation_run_id', sa.Integer(), nullable=True))
    op.add_column('payments', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('payments', sa.Column('verified_by', sa.String(100), nullable=True))
    
    # Create foreign key
    op.create_foreign_key(
        'fk_payments_reconciliation_run',
        'payments', 'reconciliation_runs',
        ['reconciliation_run_id'], ['id']
    )
    
    # Create index
    op.create_index('ix_payments_reconciliation', 'payments', ['reconciliation_run_id'])


def downgrade():
    op.drop_index('ix_payments_reconciliation')
    op.drop_constraint('fk_payments_reconciliation_run', 'payments', type_='foreignkey')
    op.drop_column('payments', 'verified_by')
    op.drop_column('payments', 'verified_at')
    op.drop_column('payments', 'reconciliation_run_id')
