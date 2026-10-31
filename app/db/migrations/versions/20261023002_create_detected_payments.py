"""create detected_payments table

Revision ID: 20261023002
Revises: 20261023001
Create Date: 2026-10-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20261023002'
down_revision = '20261023001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'detected_payments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('business_id', sa.Integer(), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('method', sa.String(50), nullable=False),
        sa.Column('sender_number', sa.String(50), nullable=True),
        sa.Column('receiver_number', sa.String(50), nullable=True),
        sa.Column('transaction_id', sa.String(255), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('matched', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('payment_id', sa.Integer(), sa.ForeignKey('payments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_detected_payments_business_id', 'detected_payments', ['business_id'])


def downgrade():
    op.drop_index('ix_detected_payments_business_id', table_name='detected_payments')
    op.drop_table('detected_payments')
