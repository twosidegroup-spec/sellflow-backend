"""COD classification, product archiving enablement, account type

Revision ID: 20261031002
Revises: 20261031001
Create Date: 2026-10-31

Small, additive schema additions required by the seller console:

* `orders.is_cod` — cash-on-delivery vs prepaid classification, chosen at
  order creation. Defaults to false for existing rows.
* `payment_accounts.account_type` — personal vs merchant receiving account.
* `ix_orders_business_status` — supports the console's status filters.
* (`products.status` already exists from migration 20261022004; this revision
  only enables it in the API contract.)

Idempotent: every step is guarded by an existence check.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261031002"
down_revision = "20261031001"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return column in {col["name"] for col in inspector.get_columns(table)}


def _has_index(table: str, name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return name in {idx["name"] for idx in inspector.get_indexes(table)}


def upgrade():
    if not _has_column("orders", "is_cod"):
        op.add_column(
            "orders",
            sa.Column("is_cod", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if not _has_column("payment_accounts", "account_type"):
        op.add_column(
            "payment_accounts",
            sa.Column(
                "account_type",
                sa.String(16),
                nullable=False,
                server_default="personal",
            ),
        )

    if not _has_index("orders", "ix_orders_business_status"):
        op.create_index("ix_orders_business_status", "orders", ["business_id", "status"])


def downgrade():
    op.drop_index("ix_orders_business_status", table_name="orders")
    op.drop_column("payment_accounts", "account_type")
    op.drop_column("orders", "is_cod")
