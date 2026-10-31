"""merge heads and add payment fields to users

Revision ID: 20261023001
Revises: a1b2c3d4e5f6, 20261022004
Create Date: 2026-10-23 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20261023001'
down_revision = ('a1b2c3d4e5f6', '20261022004')
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('payment_provider', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('receiving_number', sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column('users', 'receiving_number')
    op.drop_column('users', 'payment_provider')
