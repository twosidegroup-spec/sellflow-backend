"""Automatic payment detection: capture incoming bKash/Nagad payments and
match them to orders of the same amount."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.base import Business, Order, User
from app.orders.models import OrderStatus
from app.payments.models import DetectedPayment, Payment, PaymentStatus


def normalize_number(number: str | None) -> str | None:
    if not number:
        return None
    return "".join(ch for ch in number if ch.isdigit())


def find_business_by_number(db: Session, receiver_number: str) -> Business | None:
    """Find the business whose connected receiving number matches."""
    normalized = normalize_number(receiver_number)
    if not normalized:
        return None

    candidates = db.query(User).filter(
        User.receiving_number.isnot(None)
    ).all()
    for user in candidates:
        if normalize_number(user.receiving_number) == normalized:
            if user.memberships:
                return user.memberships[0].business

    # Fall back to the user's phone number
    for user in db.query(User).filter(User.phone.isnot(None)).all():
        if normalize_number(user.phone) == normalized:
            if user.memberships:
                return user.memberships[0].business

    return None


def record_detection(
    db: Session,
    business_id: int,
    amount: Decimal,
    method: str,
    sender_number: str | None = None,
    receiver_number: str | None = None,
    transaction_id: str | None = None,
    paid_at: datetime | None = None,
) -> DetectedPayment:
    """Store an incoming payment and try to match it with an order.

    If an order with the exact amount (not cancelled, not already paid) exists,
    a verified Payment record is created automatically and linked.
    """
    method = method.lower()

    # Idempotency: ignore duplicate transaction IDs
    if transaction_id:
        existing = db.query(DetectedPayment).filter(
            DetectedPayment.business_id == business_id,
            DetectedPayment.method == method,
            DetectedPayment.transaction_id == transaction_id,
        ).first()
        if existing:
            return existing

    # Find an order with the same total that has no verified payment yet
    orders = db.query(Order).filter(
        Order.business_id == business_id,
        Order.status != OrderStatus.CANCELLED,
        func.abs(Order.total_amount - Decimal(str(amount))) < Decimal("0.01"),
    ).order_by(Order.created_at.asc()).all()

    matched_order = None
    for order in orders:
        already_paid = db.query(Payment).filter(
            Payment.order_id == order.id,
            Payment.status == PaymentStatus.VERIFIED,
        ).first()
        if not already_paid:
            matched_order = order
            break

    payment = None
    if matched_order is not None:
        # Reuse an existing payment record with the same transaction id if any
        if transaction_id:
            payment = db.query(Payment).filter(
                Payment.business_id == business_id,
                Payment.method == method,
                Payment.transaction_id == transaction_id,
            ).first()

        if payment is None:
            payment = Payment(
                business_id=business_id,
                order_id=matched_order.id,
                amount=amount,
                method=method,
                transaction_id=transaction_id,
                status=PaymentStatus.VERIFIED,
                notes="Auto-detected payment",
                paid_at=paid_at or datetime.now(timezone.utc),
            )
            db.add(payment)
            db.flush()

    detection = DetectedPayment(
        business_id=business_id,
        amount=amount,
        method=method,
        sender_number=sender_number,
        receiver_number=receiver_number,
        transaction_id=transaction_id,
        paid_at=paid_at,
        matched=matched_order is not None,
        payment_id=payment.id if payment else None,
        order_id=matched_order.id if matched_order else None,
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)
    return detection
