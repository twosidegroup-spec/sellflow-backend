"""Server-generated order system notes

Revision ID: 20261031004
Revises: 20261031003
Create Date: 2026-10-31

Adds `orders.system_notes` (nullable text): machine-written operational notes,
currently the stock warnings captured when an order is created (approved
Inventory Option C behaviour). Kept separate from the seller-editable
`orders.notes` so system text never mixes with or overwrites seller text.

Idempotent: guarded by an existence check.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261031004"
down_revision = "20261031003"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade():
    if not _has_column("orders", "system_notes"):
        op.add_column(
            "orders",
            sa.Column("system_notes", sa.String(1000), nullable=True),
        )


def downgrade():
    if _has_column("orders", "system_notes"):
        op.drop_column("orders", "system_notes")
