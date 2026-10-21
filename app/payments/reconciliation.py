from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.db.base import Payment, Order, Business
from app.payments.models import PaymentStatus


class ReconciliationResult:
    """Holds the results of a reconciliation run."""
    def __init__(self):
        self.total_transactions: int = 0
        self.matched: int = 0
        self.unmatched_remote: list = []
        self.unmatched_local: list = []
        self.amount_mismatches: list = []
        self.status_mismatches: list = []


def reconcile_transactions(
    db: Session,
    business_id: int,
    gateway: str,
    transactions: list[dict],
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> ReconciliationResult:
    """
    Reconcile payment gateway transactions against local records.
    """
    result = ReconciliationResult()
    
    local_payments = db.query(Payment).filter(
        Payment.business_id == business_id,
        Payment.method == gateway
    )
    
    if start_date:
        local_payments = local_payments.filter(Payment.paid_at >= start_date)
    if end_date:
        local_payments = local_payments.filter(Payment.paid_at <= end_date)
    
    local_payments = local_payments.all()
    local_by_txid = {p.transaction_id: p for p in local_payments if p.transaction_id}
    matched_txids = set()
    
    for tx in transactions:
        result.total_transactions += 1
        tx_id = tx.get('transaction_id') or tx.get('trx_id') or tx.get('tx_ref')
        tx_amount = Decimal(str(tx.get('amount', 0)))
        tx_date = tx.get('paid_at') or tx.get('created_at')
        
        if tx_id and tx_id in local_by_txid:
            local_payment = local_by_txid[tx_id]
            matched_txids.add(tx_id)
            
            if abs(Decimal(str(local_payment.amount)) - tx_amount) > Decimal('0.01'):
                result.amount_mismatches.append({
                    'transaction_id': tx_id,
                    'gateway_amount': float(tx_amount),
                    'local_amount': float(local_payment.amount),
                    'difference': float(Decimal(str(local_payment.amount)) - tx_amount)
                })
            else:
                result.matched += 1
                
            if local_payment.status == PaymentStatus.VERIFIED:
                result.matched += 1
            else:
                result.status_mismatches.append({
                    'transaction_id': tx_id,
                    'gateway_status': 'completed',
                    'local_status': local_payment.status.value
                })
        else:
            result.unmatched_remote.append({
                'transaction_id': tx_id,
                'amount': float(tx_amount),
                'paid_at': tx_date,
                'status': 'pending_reconciliation'
            })
    
    for payment in local_payments:
        if payment.transaction_id and payment.transaction_id not in matched_txids:
            result.unmatched_local.append({
                'id': payment.id,
                'transaction_id': payment.transaction_id,
                'amount': payment.amount,
                'status': payment.status.value
            })
    
    return result


def get_unmatched_transactions(db: Session, business_id: int, gateway: str) -> list[dict]:
    """Get transactions that exist in gateway but not in local DB."""
    local_payments = db.query(Payment).filter(
        Payment.business_id == business_id,
        Payment.method == gateway,
        Payment.status == PaymentStatus.PENDING
    ).all()
    
    return [
        {
            'transaction_id': p.transaction_id,
            'amount': Decimal(str(p.amount)),
            'paid_at': p.paid_at,
            'order_id': p.order_id
        }
        for p in local_payments if p.transaction_id
    ]


def process_unmatched_remote(
    db: Session,
    business_id: int,
    transactions: list[dict],
    auto_verify: bool = True
) -> list[Payment]:
    """Process transactions found in gateway but not in local DB."""
    created_payments = []
    
    for tx in transactions:
        tx_id = tx.get('transaction_id')
        
        existing = db.query(Payment).filter(
            Payment.business_id == business_id,
            Payment.method == gateway,
            Payment.transaction_id == tx_id
        ).first()
        
        if existing:
            continue
        
        order_id = tx.get('order_id')
        
        if order_id:
            order = db.query(Order).filter(
                Order.id == order_id,
                Order.business_id == business_id
            ).first()
            
            if order:
                new_payment = Payment(
                    business_id=business_id,
                    order_id=order_id,
                    amount=float(tx.get('amount', 0)),
                    method=gateway,
                    transaction_id=tx_id,
                    status=PaymentStatus.VERIFIED if auto_verify else PaymentStatus.PENDING,
                    notes=f"Auto-created from reconciliation",
                    paid_at=datetime.now(timezone.utc)
                )
                db.add(new_payment)
                created_payments.append(new_payment)
    
    db.commit()
    return created_payments


def reconcile_mobile_payment(
    db: Session,
    business_id: int,
    transaction_id: str,
    amount: Decimal,
    method: str
) -> dict:
    """Verify a single mobile payment transaction."""
    payment = db.query(Payment).filter(
        Payment.business_id == business_id,
        Payment.method == method,
        Payment.transaction_id == transaction_id
    ).first()
    
    if payment:
        return {
            'verified': payment.status == PaymentStatus.VERIFIED,
            'status': payment.status.value,
            'amount': payment.amount,
            'order_id': payment.order_id,
            'paid_at': payment.paid_at.isoformat() if payment.paid_at else None
        }
    
    return {
        'verified': False,
        'status': 'not_found',
        'amount': None,
        'order_id': None,
        'paid_at': None
    }


def generate_reconciliation_report(
    db: Session,
    business_id: int,
    gateway: str,
    days: int = 30
) -> dict:
    """Generate a reconciliation report."""
    period_start = datetime.now(timezone.utc) - timedelta(days=days)
    
    local_payments = db.query(Payment).filter(
        Payment.business_id == business_id,
        Payment.method == gateway,
        Payment.paid_at >= period_start
    ).all()
    
    verified = [p for p in local_payments if p.status == PaymentStatus.VERIFIED]
    pending = [p for p in local_payments if p.status == PaymentStatus.PENDING]
    
    total_local = sum(p.amount for p in local_payments)
    
    recommendations = []
    if len(pending) > 0:
        recommendations.append(f"Review {len(pending)} pending transactions")
    
    total_local_mismatch = sum(
        abs(Decimal(str(p.amount)) - Decimal(p.transaction_id))
        for p in local_payments if p.transaction_id
    )
    
    return {
        "business_id": business_id,
        "gateway": gateway,
        "period_start": period_start.isoformat(),
        "period_end": datetime.now(timezone.utc).isoformat(),
        "total_local_payments": len(local_payments),
        "total_gateway_transactions": len(local_payments),
        "match_rate": (len(verified) / len(local_payments) * 100) if local_payments else 100.0,
        "discrepancy_amount": float(total_local_mismatch),
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
