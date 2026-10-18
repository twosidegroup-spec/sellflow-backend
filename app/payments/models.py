from datetime import datetime
from sqlalchemy import String, Numeric, ForeignKey, DateTime, func, UniqueConstraint, Enum as SQLEnum
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
