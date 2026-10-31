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
    MobilePaymentVerification, MobilePaymentVerificationResponse,
    DetectionRequest, DetectionResponse, DetectedPaymentRead
)
from app.payments import service
from app.payments.models import Payment, PaymentStatus, DetectedPayment
from app.payments.reconciliation import (
    reconcile_transactions,
    reconcile_mobile_payment,
    get_supported_gateways
)
from app.payments.detection import find_business_by_number, record_detection

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


# ==================== BUSINESS-LEVEL RECONCILIATION ====================

business_router = APIRouter(prefix="/businesses/{business_id}/payments", tags=["Payment Reconciliation"])


@business_router.get("", response_model=list[PaymentRead])
def list_business_payments(
    business_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    List all payments recorded for this business (newest first).
    """
    return db.query(Payment).filter(
        Payment.business_id == business_id
    ).order_by(Payment.created_at.desc()).all()


@business_router.get("/detected", response_model=list[DetectedPaymentRead])
def list_detected_payments(
    business_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Recent auto-detected incoming payments (newest first).
    """
    return db.query(DetectedPayment).filter(
        DetectedPayment.business_id == business_id
    ).order_by(DetectedPayment.created_at.desc()).limit(30).all()


# ==================== PAYMENT DETECTION (PUBLIC INGEST) ====================

detect_router = APIRouter(prefix="/payments", tags=["Payment Detection"])


@detect_router.post("/detect", response_model=DetectionResponse)
def detect_incoming_payment(
    request: DetectionRequest,
    db: Session = Depends(get_db)
):
    """
    Ingest an incoming provider payment (bKash / Nagad / Rocket / Upay ...).

    The business is identified by the connected receiving number. If an order
    with the exact amount exists (and is not already paid), the payment is
    recorded automatically and linked to that order.
    """
    business = find_business_by_number(db, request.receiver_number)
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business is connected to this receiving number",
        )

    detection = record_detection(
        db=db,
        business_id=business.id,
        amount=request.amount,
        method=request.method,
        sender_number=request.sender_number,
        receiver_number=request.receiver_number,
        transaction_id=request.transaction_id,
        paid_at=request.paid_at,
    )

    return DetectionResponse(
        detection_id=detection.id,
        business_id=business.id,
        matched=detection.matched,
        order_id=detection.order_id,
        payment_id=detection.payment_id,
    )


@business_router.get("/reconciliation/status")
def get_business_reconciliation_status(
    business_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Business-wide reconciliation status across all payment methods.
    """
    from sqlalchemy import func

    methods = ['bkash', 'nagad', 'rocket', 'upay', 'cash']
    payment_methods = {}
    verified_total = Decimal("0")
    pending_total = Decimal("0")
    total_count = 0
    verified_count = 0
    pending_count = 0

    for method in methods:
        total = db.query(func.count(Payment.id)).filter(
            Payment.business_id == business_id,
            Payment.method == method
        ).scalar() or 0

        verified = db.query(func.count(Payment.id)).filter(
            Payment.business_id == business_id,
            Payment.method == method,
            Payment.status == PaymentStatus.VERIFIED
        ).scalar() or 0

        pending = db.query(func.count(Payment.id)).filter(
            Payment.business_id == business_id,
            Payment.method == method,
            Payment.status == PaymentStatus.PENDING
        ).scalar() or 0

        verified_amount = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.business_id == business_id,
            Payment.method == method,
            Payment.status == PaymentStatus.VERIFIED
        ).scalar()

        pending_amount = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.business_id == business_id,
            Payment.method == method,
            Payment.status == PaymentStatus.PENDING
        ).scalar()

        payment_methods[method] = {
            "total": total,
            "verified": verified,
            "pending": pending,
            "verified_amount": float(verified_amount or 0),
            "pending_amount": float(pending_amount or 0),
        }
        total_count += total
        verified_count += verified
        pending_count += pending
        verified_total += Decimal(str(verified_amount or 0))
        pending_total += Decimal(str(pending_amount or 0))

    return {
        "business_id": business_id,
        "total_payments": total_count,
        "verified_payments": verified_count,
        "pending_payments": pending_count,
        "verified_amount": float(verified_total),
        "pending_amount": float(pending_total),
        "payment_methods": payment_methods,
        "last_updated": datetime.utcnow(),
    }


@business_router.post("/verify-mobile", response_model=MobilePaymentVerificationResponse)
def verify_mobile_payment_endpoint(
    business_id: int,
    request: MobilePaymentVerification,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Verify a single bKash/Nagad/Rocket/Upay transaction by its transaction ID.
    Looks up the local payment record for this business.
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
