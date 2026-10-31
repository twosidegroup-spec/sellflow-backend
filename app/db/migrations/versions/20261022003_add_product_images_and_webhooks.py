"""Add product images and webhooks tables

Revision ID: 20261022003
Revises: 20261022002
Create Date: 2026-10-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20261022003'
down_revision = '20261022002'
branch_labels = None
depends_on = None


def upgrade():
    # Create product_images table
    op.create_table(
        'product_images',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('image_url', sa.String(500), nullable=False),
        sa.Column('alt_text', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    )
    
    # Create webhook_subscriptions table
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('events', sa.Text(), nullable=False),
        sa.Column('secret_key', sa.String(64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
    )
    
    # Create indexes
    op.create_index('ix_product_images_product', 'product_images', ['product_id'])
    op.create_index('ix_webhooks_business', 'webhook_subscriptions', ['business_id'])


def downgrade():
    op.drop_index('ix_webhooks_business')
    op.drop_table('webhook_subscriptions')
    op.drop_index('ix_product_images_product')
    op.drop_table('product_images')
