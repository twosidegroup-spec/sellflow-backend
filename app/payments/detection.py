"""Dev-only payment simulator + detection matching helpers.

SECURITY NOTE (post-migration):

The previous production "detect" ingest could be called ANONYMOUSLY with any
seller's receiving number and would create a `verified` payment against that
seller's order (a payment-forgery endpoint). It is now:

* **Unavailable in production** — the route raises 404 when
  `settings.is_production` (see `router.detect_incoming_payment`).
* **JWT-protected** — only an authenticated user can call it.
* **Tenant-scoped** — the receiving number must belong to the caller's OWN
  business (`payment_accounts`) or to the caller's own user profile.

What remains is a local development tool that lets the mobile app's
"Test incoming payment" button exercise order matching. The canonical payment
pipeline for real money is the device bridge + payment intelligence engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.base import Business, Order, User
from app.orders.models import OrderStatus
from app.payments.models import DetectedPayment, Payment, PaymentAccount, PaymentStatus
from app.utils.phone import phones_equivalent


def normalize_number(number: str | None) -> str | None:
    if not number:
        return None
    return "".join(ch for ch in number if ch.isdigit())


def find_owned_business_by_number(
    db: Session, business: Business, receiver_number: str
) -> bool:
    """True when `receiver_number` is connected to THIS business.

    Looks at the canonical `payment_accounts` table first (that is what the
    device bridge and registration write), then at the business's users' own
    receiving numbers/phones for backwards compatibility with accounts created
    before `payment_accounts` existed.
    """
    if not receiver_number:
        return False

    accounts = (
        db.query(PaymentAccount)
        .filter(PaymentAccount.business_id == business.id)
        .all()
    )
    for account in accounts:
        if phones_equivalent(account.receiving_number, receiver_number):
            return True

    users = (
        db.query(User)
        .filter(User.memberships.any(business_id=business.id))
        .all()
    )
    for user in users:
        if phones_equivalent(user.receiving_number, receiver_number):
            return True
        if phones_equivalent(user.phone, receiver_number):
            return True
    return False


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
    """Store a simulated incoming payment and try to match it with an order.

    Kept for the development simulator; NOT used by the production pipeline.
    When an order with the exact amount exists (not cancelled, no verified
    payment yet), a `verified` Payment is created and linked. Idempotent on
    `(business_id, method, transaction_id)`.
    """
    method = method.lower()

    if transaction_id:
        existing = db.query(DetectedPayment).filter(
            DetectedPayment.business_id == business_id,
            DetectedPayment.method == method,
            DetectedPayment.transaction_id == transaction_id,
        ).first()
        if existing:
            return existing

    amount_decimal = Decimal(str(amount))

    orders = db.query(Order).filter(
        Order.business_id == business_id,
        Order.status != OrderStatus.CANCELLED,
        func.abs(Order.total_amount - amount_decimal) < Decimal("0.01"),
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
                amount=amount_decimal,
                method=method,
                transaction_id=transaction_id,
                status=PaymentStatus.VERIFIED,
                notes="Simulated payment (development tool)",
                paid_at=paid_at or datetime.now(timezone.utc),
            )
            db.add(payment)
            db.flush()

        matched_order.payment_status = "paid"
        matched_order.payment_method = method

    detection = DetectedPayment(
        business_id=business_id,
        amount=amount_decimal,
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
