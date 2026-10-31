"""Add status column to products table

Revision ID: 20261022004
Revises: 20261022003
Create Date: 2026-10-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20261022004'
down_revision = '20261022003'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('status', sa.String(20), nullable=True))
    # Set default value for existing products
    op.execute("UPDATE products SET status = 'active'")
    op.alter_column('products', 'status', nullable=False)


def downgrade():
    op.drop_column('products', 'status')
