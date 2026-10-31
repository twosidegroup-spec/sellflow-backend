"""Per-user token-version revocation channel

Revision ID: 20261031003
Revises: 20261031002
Create Date: 2026-10-31

Adds `users.token_version` (STAGING_READINESS.md section 5.2):

* JWTs carry the value as a `ver` claim; `get_current_user` and the device
  bridge's `_optional_user` reject a mismatch or a missing claim (hard
  cutover), and a password change bumps the value so every existing session
  for that user is revoked.

Idempotent: guarded by an existence check so a re-run (or a database where the
column already exists) is a no-op.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261031003"
down_revision = "20261031002"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade():
    if not _has_column("users", "token_version"):
        op.add_column(
            "users",
            sa.Column(
                "token_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade():
    if _has_column("users", "token_version"):
        op.drop_column("users", "token_version")
