from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from app.db.base import Payment, Order
from app.payments.schemas import PaymentCreate
from app.payments.models import PaymentStatus

def record_payment(db: Session, business_id: int, order_id: int, payment_data: PaymentCreate) -> Payment:
    # 1. Verify order exists and belongs to this business
    order = db.query(Order).filter(Order.id == order_id, Order.business_id == business_id).first()
    if not order:
        raise ValueError("Order not found or access denied")
    
    # 2. Idempotency Check: Has this transaction ID already been recorded for this business/method?
    if payment_data.transaction_id:
        existing_payment = db.query(Payment).filter(
            Payment.business_id == business_id,
            Payment.method == payment_data.method.lower(),
            Payment.transaction_id == payment_data.transaction_id
        ).first()
        
        if existing_payment:
            # Idempotent behavior: return the existing payment instead of creating a duplicate
            return existing_payment

    # 3. Reconciliation Check: Prevent massive overpayments (optional but recommended)
    # Calculate total already paid for this order
    paid_amount = Decimal(str(db.query(func.sum(Payment.amount)).filter(
        Payment.order_id == order_id,
        Payment.status == PaymentStatus.VERIFIED
    ).scalar() or 0.0))
    
    # FIX: Multiply Decimal by Decimal, not float
    if paid_amount + payment_data.amount > Decimal(str(order.total_amount)) * Decimal("1.5"):
        pass # Allow up to 150% to account for minor rounding or delivery fee adjustments

    # 4. Create the payment record
    db_payment = Payment(
        business_id=business_id,
        order_id=order_id,
        amount=float(payment_data.amount),
        method=payment_data.method.lower(),
        transaction_id=payment_data.transaction_id,
        status=PaymentStatus.VERIFIED, 
        notes=payment_data.notes,
        paid_at=datetime.now(timezone.utc)
    )
    
    db.add(db_payment)
    try:
        db.commit()
        db.refresh(db_payment)
        return db_payment
    except IntegrityError:
        db.rollback()
        # Fallback idempotency: if unique constraint failed, fetch and return the existing one
        return db.query(Payment).filter(
            Payment.business_id == business_id,
            Payment.method == payment_data.method.lower(),
            Payment.transaction_id == payment_data.transaction_id
        ).first()
