from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
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
    ReconciliationReport
)
from app.payments import service
from app.payments.models import PaymentStatus
from app.payments.reconciliation import (
    reconcile_transactions,
    process_unmatched_remote,
    reconcile_mobile_payment
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


# ==================== RECONCILIATION ENDPOINTS ====================

@router.post("/reconcile", response_model=ReconciliationResponse)
def run_reconciliation(
    business_id: int,
    request: ReconciliationRequest,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Reconcile payment gateway transactions against local records.
    Used for batch reconciliation after importing gateway reports.
    """
    result = reconcile_transactions(
        db=db,
        business_id=business_id,
        gateway=request.gateway.lower(),
        transactions=[tx.model_dump() for tx in request.transactions],
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    return ReconciliationResponse(
        total_transactions=result.total_transactions,
        matched=result.matched,
        unmatched_remote=result.unmatched_remote,
        unmatched_local=result.unmatched_local,
        amount_mismatches=result.amount_mismatches,
        status_mismatches=result.status_mismatches,
        processed_at=datetime.utcnow()
    )


@router.post("/reconcile-mobile", response_model=MobilePaymentVerificationResponse)
def reconcile_mobile_payment_endpoint(
    business_id: int,
    order_id: int,
    request: MobilePaymentVerification,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Verify a single mobile payment (iOS/Android).
    Used when a mobile app submits payment confirmation.
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


@router.post("/process-unmatched")
def process_unmatched_transactions(
    business_id: int,
    gateway: str,
    auto_verify: bool = True,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Process transactions found in gateway but missing from local DB.
    Creates missing payment records automatically.
    """
    from app.payments.reconciliation import get_unmatched_transactions
    
    unmatched = get_unmatched_transactions(db, business_id, gateway)
    
    if not unmatched:
        return {"processed": 0, "created": []}
    
    created = process_unmatched_remote(db, business_id, unmatched, auto_verify)
    
    return {
        "processed": len(unmatched),
        "created": [
            {"id": p.id, "transaction_id": p.transaction_id, "amount": p.amount}
            for p in created
        ]
    }


@router.get("/reconciliation-report")
def get_reconciliation_report(
    business_id: int,
    gateway: str = "bkash",
    days: int = 30,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Generate a reconciliation report showing discrepancies.
    """
    from app.payments.reconciliation import generate_reconciliation_report
    
    report = generate_reconciliation_report(
        db=db,
        business_id=business_id,
        gateway=gateway.lower(),
        days=days
    )
    
    return report


@router.get("/reconciliation/status")
def get_reconciliation_status(
    business_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """
    Get current reconciliation status for all payment methods.
    """
    from sqlalchemy import func
    
    methods = ['bkash', 'nagad', 'rocket', 'upay', 'cash']
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
        "last_updated": datetime.utcnow(),
        "payment_methods": status
    }


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
