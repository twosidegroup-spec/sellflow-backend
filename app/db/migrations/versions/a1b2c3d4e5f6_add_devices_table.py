"""add_devices_table

Revision ID: a1b2c3d4e5f6
Revises: 6ecc47ac13c3
Create Date: 2026-10-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '6ecc47ac13c3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'devices',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('device_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('business_id', sa.Integer(), nullable=True),
        sa.Column('device_type', sa.String(50), nullable=False),
        sa.Column('app_version', sa.String(50), nullable=True),
        sa.Column('push_token', sa.String(512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_active', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_devices_device_id', 'devices', ['device_id'])
    op.create_index('ix_devices_user_active', 'devices', ['user_id', 'is_active'])
    op.create_index('ix_devices_business_active', 'devices', ['business_id', 'is_active'])
    op.create_foreign_key(
        'fk_devices_user_id',
        'devices', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_devices_business_id',
        'devices', 'businesses',
        ['business_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint('fk_devices_business_id', 'devices', type_='foreignkey')
    op.drop_constraint('fk_devices_user_id', 'devices', type_='foreignkey')
    op.drop_index('ix_devices_business_active', table_name='devices')
    op.drop_index('ix_devices_user_active', table_name='devices')
    op.drop_index('ix_devices_device_id', table_name='devices')
    op.drop_table('devices')
