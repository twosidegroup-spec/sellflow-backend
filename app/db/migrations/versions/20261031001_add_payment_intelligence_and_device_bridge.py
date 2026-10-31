"""add payment intelligence and device bridge (System A -> System B migration)

Revision ID: 20261031001
Revises: 20261023002
Create Date: 2026-10-31

Consolidates the valuable System A database functionality into System B's
single canonical migration history:

* payment_events / payment_decisions / payment_matches / payment_anomalies /
  payment_feedback / seller_payment_profiles  (System A migrations 002)
* payment_accounts                            (System A migration 003)
* device_pairing_codes + device-bridge columns on the existing `devices`
  table                                       (System A migration 004/005)
* payment_status / payment_method on the existing `orders` table
  (System A's order payment state)

Idempotent-friendly: every create is guarded by an existence check so the
migration can be re-run against a database that partially applied it (for
example a database where these tables were created by hand from System A).
"""
from alembic import op
import sqlalchemy as sa

revision = '20261031001'
down_revision = '20261023002'
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade():
    # ------------------------------------------------------------------ accounts
    if not _has_table("payment_accounts"):
        op.create_table(
            "payment_accounts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider", sa.String(32), nullable=False),
            sa.Column("receiving_number", sa.String(50), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="configured"),
            sa.Column("mode", sa.String(16), nullable=False, server_default="live"),
            sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("business_id", "provider", "receiving_number", name="uq_payment_account_business_provider_number"),
        )
        op.create_index("ix_payment_accounts_business_id", "payment_accounts", ["business_id"])

    # ------------------------------------------------------------- pairing codes
    if not _has_table("device_pairing_codes"):
        op.create_table(
            "device_pairing_codes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("code_hash", sa.String(128), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_device_pairing_codes_business_id", "device_pairing_codes", ["business_id"])
        op.create_index("ix_device_pairing_codes_business", "device_pairing_codes", ["business_id", "expires_at"])

    # ----------------------------------------------------------- devices columns
    if not _has_column("devices", "device_name"):
        op.add_column("devices", sa.Column("device_name", sa.String(128), nullable=True))
    if not _has_column("devices", "device_token_hash"):
        op.add_column("devices", sa.Column("device_token_hash", sa.String(128), nullable=True))
        op.create_index("ix_devices_device_token_hash", "devices", ["device_token_hash"], unique=True)
    if not _has_column("devices", "pairing_code_id"):
        op.add_column(
            "devices",
            sa.Column("pairing_code_id", sa.Integer(), sa.ForeignKey("device_pairing_codes.id", ondelete="SET NULL"), nullable=True),
        )
    if not _has_column("devices", "status"):
        op.add_column("devices", sa.Column("status", sa.String(16), nullable=False, server_default="paired"))
    if not _has_column("devices", "sms_permission_granted"):
        op.add_column("devices", sa.Column("sms_permission_granted", sa.Boolean(), nullable=False, server_default=sa.false()))
    if not _has_column("devices", "monitoring_active"):
        op.add_column("devices", sa.Column("monitoring_active", sa.Boolean(), nullable=False, server_default=sa.false()))
    if not _has_column("devices", "paired_at"):
        op.add_column("devices", sa.Column("paired_at", sa.DateTime(timezone=True), nullable=True))

    # ------------------------------------------------------------ orders columns
    if not _has_column("orders", "payment_status"):
        op.add_column("orders", sa.Column("payment_status", sa.String(32), nullable=False, server_default="pending"))
    if not _has_column("orders", "payment_method"):
        op.add_column("orders", sa.Column("payment_method", sa.String(32), nullable=True))

    # ----------------------------------------------------------- payment events
    if not _has_table("payment_events"):
        op.create_table(
            "payment_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
            sa.Column("provider", sa.String(32), nullable=False),
            sa.Column("transaction_id", sa.String(255), nullable=False),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("currency", sa.String(8), nullable=False, server_default="BDT"),
            sa.Column("sender_identifier", sa.String(32), nullable=True),
            sa.Column("receiver_identifier", sa.String(32), nullable=True),
            sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source_type", sa.String(32), nullable=False),
            sa.Column("source", sa.String(32), nullable=True),
            sa.Column("raw_metadata", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("business_id", "provider", "transaction_id", name="uq_payment_events_business_provider_txid"),
        )
        op.create_index("ix_payment_events_business_id", "payment_events", ["business_id"])
        op.create_index("ix_payment_events_business_timestamp", "payment_events", ["business_id", "event_timestamp"])
        op.create_index("ix_payment_events_provider_txid", "payment_events", ["provider", "transaction_id"])

    # -------------------------------------------------------- payment decisions
    if not _has_table("payment_decisions"):
        op.create_table(
            "payment_decisions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("payment_event_id", sa.Integer(), sa.ForeignKey("payment_events.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("decision", sa.String(32), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
            sa.Column("reason_codes", sa.JSON(), nullable=True),
            sa.Column("explanation", sa.Text(), nullable=False),
            sa.Column("engine_version", sa.String(32), nullable=False, server_default="payment-intelligence-1.0.0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_payment_decisions_payment_event_id", "payment_decisions", ["payment_event_id"])

    # ----------------------------------------------------------- payment matches
    if not _has_table("payment_matches"):
        op.create_table(
            "payment_matches",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("payment_event_id", sa.Integer(), sa.ForeignKey("payment_events.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("amount_match", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("customer_match", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("timing_match", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("historical_match", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_payment_matches_payment_event_id", "payment_matches", ["payment_event_id"])

    # --------------------------------------------------------- payment anomalies
    if not _has_table("payment_anomalies"):
        op.create_table(
            "payment_anomalies",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("payment_event_id", sa.Integer(), sa.ForeignKey("payment_events.id", ondelete="CASCADE"), nullable=False),
            sa.Column("anomaly_type", sa.String(64), nullable=False),
            sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_payment_anomalies_payment_event_id", "payment_anomalies", ["payment_event_id"])

    # ----------------------------------------------------------- payment feedback
    if not _has_table("payment_feedback"):
        op.create_table(
            "payment_feedback",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("payment_event_id", sa.Integer(), sa.ForeignKey("payment_events.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
            sa.Column("from_decision", sa.String(32), nullable=False),
            sa.Column("correct_decision", sa.String(32), nullable=False),
            sa.Column("correction_reason", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_payment_feedback_business_id", "payment_feedback", ["business_id"])

    # --------------------------------------------------- seller payment profiles
    if not _has_table("seller_payment_profiles"):
        op.create_table(
            "seller_payment_profiles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("average_order_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("average_payment_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("average_time_to_payment_seconds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("partial_payment_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
            sa.Column("payment_mismatch_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade():
    op.drop_table("seller_payment_profiles")
    op.drop_index("ix_payment_feedback_business_id", table_name="payment_feedback")
    op.drop_table("payment_feedback")
    op.drop_index("ix_payment_anomalies_payment_event_id", table_name="payment_anomalies")
    op.drop_table("payment_anomalies")
    op.drop_index("ix_payment_matches_payment_event_id", table_name="payment_matches")
    op.drop_table("payment_matches")
    op.drop_index("ix_payment_decisions_payment_event_id", table_name="payment_decisions")
    op.drop_table("payment_decisions")
    op.drop_index("ix_payment_events_provider_txid", table_name="payment_events")
    op.drop_index("ix_payment_events_business_timestamp", table_name="payment_events")
    op.drop_index("ix_payment_events_business_id", table_name="payment_events")
    op.drop_table("payment_events")

    op.drop_column("orders", "payment_method")
    op.drop_column("orders", "payment_status")

    op.drop_column("devices", "paired_at")
    op.drop_column("devices", "monitoring_active")
    op.drop_column("devices", "sms_permission_granted")
    op.drop_column("devices", "status")
    op.drop_column("devices", "pairing_code_id")
    op.drop_index("ix_devices_device_token_hash", table_name="devices")
    op.drop_column("devices", "device_token_hash")
    op.drop_column("devices", "device_name")

    op.drop_index("ix_device_pairing_codes_business", table_name="device_pairing_codes")
    op.drop_index("ix_device_pairing_codes_business_id", table_name="device_pairing_codes")
    op.drop_table("device_pairing_codes")

    op.drop_index("ix_payment_accounts_business_id", table_name="payment_accounts")
    op.drop_table("payment_accounts")
