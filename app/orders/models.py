from datetime import datetime
from sqlalchemy import String, Numeric, Integer, ForeignKey, DateTime, Boolean, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.engine import Base
import enum

class OrderStatus(str, enum.Enum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    PACKED = "packed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Order-status transition policy (approved 2026-10-31, documented in
# STAGING_READINESS.md section 4.1). Same-status requests are no-ops handled
# by the caller and are not listed here. Terminal states allow nothing.
#
#   created   -> confirmed | cancelled
#   confirmed -> packed | shipped | cancelled   (packed is optional)
#   packed    -> shipped | cancelled
#   shipped   -> delivered | cancelled
#   delivered -> terminal (returns/refunds need a dedicated workflow)
#   cancelled -> terminal
ALLOWED_ORDER_TRANSITIONS: dict["OrderStatus", frozenset["OrderStatus"]] = {
    OrderStatus.CREATED: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset(
        {OrderStatus.PACKED, OrderStatus.SHIPPED, OrderStatus.CANCELLED}
    ),
    OrderStatus.PACKED: frozenset({OrderStatus.SHIPPED, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.DELIVERED, OrderStatus.CANCELLED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


def allowed_next_statuses(status: "OrderStatus") -> frozenset["OrderStatus"]:
    """The set of statuses `status` may move to (same-status no-op excluded)."""
    return ALLOWED_ORDER_TRANSITIONS.get(status, frozenset())

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.CREATED, nullable=False)
    
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    total_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    gross_profit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    delivery_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    discount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Payment state maintained by the payment-intelligence engine
    # (migrated from System A's orders.payment_status/payment_method).
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Cash-on-delivery vs prepaid. COD orders are still unpaid until delivery
    # is collected; the flag only classifies the commercial terms.
    is_cod: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    business = relationship("Business", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    delivery = relationship("Delivery", back_populates="order", uselist=False, cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    cost_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    profit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
