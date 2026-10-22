from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business, Order
from app.payments.schemas import (
    PaymentCreate, PaymentRead,
    ReconciliationRequest, ReconciliationResponse,
    MobilePaymentVerification, MobilePaymentVerificationResponse
)
from app.payments import service
from app.payments.models import PaymentStatus
from app.payments.reconciliation import (
    reconcile_transactions,
    reconcile_mobile_payment,
    get_supported_gateways
)

router = APIRouter(prefix="/businesses/{business_id}/orders/{order_id}/payments", tags=["Payments"])


@router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def record_payment_endpoint(
    business_id: int,
    order_id: int,
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    try:
        return service.record_payment(db, business_id, order_id, payment_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== GLOBAL ENDPOINTS ====================

@router.get("/supported-gateways")
def get_supported_payment_gateways():
    """
    Get list of all supported payment gateways (local + international).
    """
    return get_supported_gateways()


# ==================== MOBILE VERIFICATION ENDPOINTS ====================

@router.post("/reconcile-mobile", response_model=MobilePaymentVerificationResponse)
def reconcile_mobile_payment_endpoint(
    business_id: int,
    order_id: int,
    request: MobilePaymentVerification,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Verify a single payment from iOS/Android.
    Works with both local (bKash, Nagad) and international (PayPal, Stripe) payments.
    """
    result = reconcile_mobile_payment(
        db=db,
        business_id=business_id,
        transaction_id=request.transaction_id,
        amount=request.amount,
        method=request.method.lower()
    )
    
    return MobilePaymentVerificationResponse(
        verified=result['verified'],
        status=result['status'],
        amount=result['amount'],
        order_id=result['order_id'],
        paid_at=result['paid_at']
    )


# ==================== BATCH RECONCILIATION ENDPOINTS ====================

@router.post("/reconcile", response_model=ReconciliationResponse)
def run_reconciliation(
    business_id: int,
    order_id: int,
    request: ReconciliationRequest,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Reconcile payment gateway transactions against local records.
    Supports local (bKash, Nagad, Rocket, Upay) and international (PayPal, Cash App, Stripe, Wise) gateways.
    
    Example for PayPal:
    {
        "gateway": "paypal",
        "transactions": [
            {
                "id": "3C679366HH908993F",
                "amount": {"value": "99.99", "currency": "USD"},
                "payer": {"email_address": "buyer@example.com"},
                "create_time": "2026-10-22T10:30:00Z",
                "metadata": {"order_id": "123"}
            }
        ]
    }
    """
    result = reconcile_transactions(
        db=db,
        business_id=business_id,
        gateway=request.gateway.lower(),
        transactions=[tx.model_dump() for tx in request.transactions],
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    return ReconciliationResponse(**result, processed_at=datetime.utcnow())


@router.get("/reconciliation/status")
def get_reconciliation_status(
    business_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Get current reconciliation status for all payment methods.
    """
    from sqlalchemy import func
    
    methods = ['bkash', 'nagad', 'rocket', 'upay', 'paypal', 'cashapp', 'stripe', 'wise', 'cash']
    status = {}
    
    for method in methods:
        total = db.query(func.count(Payment.id)).filter(
            Payment.business_id == business_id,
            Payment.method == method
        ).scalar()
        
        verified = db.query(func.count(Payment.id)).filter(
            Payment.business_id == business_id,
            Payment.method == method,
            Payment.status == PaymentStatus.VERIFIED
        ).scalar()
        
        pending = db.query(func.count(Payment.id)).filter(
            Payment.business_id == business_id,
            Payment.method == method,
            Payment.status == PaymentStatus.PENDING
        ).scalar()
        
        status[method] = {
            "total": total,
            "verified": verified,
            "pending": pending
        }
    
    return {
        "business_id": business_id,
        "order_id": order_id,
        "last_updated": datetime.utcnow(),
        "payment_methods": status
    }


# ==================== ORDER RECONCILIATION ====================

@router.post("/verify", response_model=dict)
def reconcile_single_order(
    business_id: int,
    order_id: int,
    gateway_transactions: list[dict],
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Reconcile a single order's payment with gateway data.
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.business_id == business_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Find all payments for this order
    local_payments = db.query(Payment).filter(
        Payment.order_id == order_id,
        Payment.business_id == business_id
    ).all()
    
    local_total = sum(p.amount for p in local_payments)
    gateway_total = sum(Decimal(str(tx.get('amount', 0))) for tx in gateway_transactions)
    
    # Check if amounts match
    if abs(Decimal(str(local_total)) - gateway_total) > Decimal("0.01"):
        # Update payment statuses to verified
        for payment in local_payments:
            if payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.VERIFIED
        db.commit()
    
    return {
        "order_id": order_id,
        "local_total": float(local_total),
        "gateway_total": float(gateway_total),
        "local_payments_count": len(local_payments),
        "gateway_transactions_count": len(gateway_transactions),
        "reconciled": abs(Decimal(str(local_total)) - gateway_total) <= Decimal("0.01")
    }
