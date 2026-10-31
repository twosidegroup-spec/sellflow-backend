"""SQLAlchemy models for the payment-intelligence schema.

These tables are the consolidated (System B) versions of System A's
`002_payment_intelligence.sql` tables. Differences from System A, all
deliberate and documented in MIGRATION_REPORT.md:

* `reason_codes` is JSON rather than a PostgreSQL TEXT[] so the model stays
  readable through SQLAlchemy without dialect-specific imports.
* `payment_events` carries optional `device_id`/`source` columns so the
  device bridge does not need a second event ledger.
* All business-scoped tables carry `business_id` with a FK to `businesses`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.engine import Base


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BDT")
    sender_identifier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    receiver_identifier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    decisions = relationship(
        "PaymentDecision", back_populates="event", cascade="all, delete-orphan"
    )
    matches = relationship(
        "PaymentMatch", back_populates="event", cascade="all, delete-orphan"
    )
    anomalies = relationship(
        "PaymentAnomaly", back_populates="event", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "provider",
            "transaction_id",
            name="uq_payment_events_business_provider_txid",
        ),
        Index("ix_payment_events_business_timestamp", "business_id", "event_timestamp"),
        Index("ix_payment_events_provider_txid", "provider", "transaction_id"),
    )


class PaymentDecision(Base):
    __tablename__ = "payment_decisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_event_id: Mapped[int] = mapped_column(
        ForeignKey("payment_events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), nullable=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    reason_codes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    engine_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="payment-intelligence-1.0.0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    event = relationship("PaymentEvent", back_populates="decisions")


class PaymentMatch(Base):
    __tablename__ = "payment_matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_event_id: Mapped[int] = mapped_column(
        ForeignKey("payment_events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    amount_match: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    customer_match: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timing_match: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    historical_match: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    event = relationship("PaymentEvent", back_populates="matches")


class PaymentAnomaly(Base):
    __tablename__ = "payment_anomalies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_event_id: Mapped[int] = mapped_column(
        ForeignKey("payment_events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    anomaly_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    event = relationship("PaymentEvent", back_populates="anomalies")


class PaymentFeedback(Base):
    __tablename__ = "payment_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    payment_event_id: Mapped[int] = mapped_column(
        ForeignKey("payment_events.id", ondelete="RESTRICT"), nullable=False
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    from_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    correct_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    correction_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SellerPaymentProfile(Base):
    __tablename__ = "seller_payment_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    average_order_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    average_payment_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    average_time_to_payment_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    partial_payment_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=0
    )
    payment_mismatch_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=0
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
