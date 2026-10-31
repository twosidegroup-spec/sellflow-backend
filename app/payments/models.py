from datetime import datetime
from sqlalchemy import String, Numeric, ForeignKey, DateTime, func, UniqueConstraint, Enum as SQLEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.engine import Base
import enum

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    REFUNDED = "refunded"

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), index=True, nullable=False) # RESTRICT so we don't accidentally delete audit records
    
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., 'bkash', 'nagad', 'cash'
    transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    status: Mapped[PaymentStatus] = mapped_column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    business = relationship("Business", back_populates="payments")
    order = relationship("Order", back_populates="payments")

    # Enforce idempotency at the database level: one transaction ID per method per business
    __table_args__ = (
        UniqueConstraint('business_id', 'method', 'transaction_id', name='uq_payment_business_method_txid'),
    )


class DetectedPayment(Base):
    """A payment captured automatically from bKash / Nagad / other providers.

    Unmatched detections live here until an order with the same amount exists;
    when matched, a real Payment record is created and linked.
    """
    __tablename__ = "detected_payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)

    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    sender_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    receiver_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PaymentAccount(Base):
    """The receiving account a business connects for a provider.

    Migrated from System A's `payment_accounts` table. The account's receiving
    number is what the device bridge reports and what detection matches
    against; every row is owned by exactly one business.
    """

    __tablename__ = "payment_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    receiving_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="configured")
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="live")
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "business_id", "provider", "receiving_number",
            name="uq_payment_account_business_provider_number",
        ),
    )
