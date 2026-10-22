from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.base import Payment, Order, Business
from app.payments.models import PaymentStatus


def normalize_gateway_transaction(
    tx: Dict[str, Any],
    gateway: str
) -> Dict[str, Any]:
    """
    Normalize transactions from different payment gateways into a standard format.
    
    Gateway-specific mappings:
    - PayPal: 'id', 'payer.email_address', 'create_time'
    - CashApp: 'id', 'merchant_note'
    - Stripe: 'id', 'customer_email', 'created'
    - bKash: 'trx_id', 'paid_at'
    """
    gateway = gateway.lower()
    
    # Map transaction_id based on gateway
    if gateway == 'paypal':
        tx_id = tx.get('id') or tx.get('transaction_id') or tx.get('txn_id')
        amount = Decimal(str(tx.get('amount', {}).get('value', tx.get('amount', 0))))
        paid_at = tx.get('create_time') or tx.get('update_time') or tx.get('paid_at')
        payer_email = tx.get('payer', {}).get('email_address')
    elif gateway == 'cashapp':
        tx_id = tx.get('id') or tx.get('transaction_id')
        amount = Decimal(str(tx.get('amount', 0)))
        paid_at = tx.get('completed_at') or tx.get('created_at')
        payer_email = tx.get('merchant_note')
    elif gateway == 'stripe':
        tx_id = tx.get('id') or tx.get('payment_intent_id')
        amount = Decimal(str(tx.get('amount', 0))) / Decimal('100')  # Stripe uses cents
        paid_at = tx.get('created') or tx.get('created_at')
        payer_email = tx.get('customer_email')
    elif gateway == 'wise':
        tx_id = tx.get('id') or tx.get('payment_id')
        amount = Decimal(str(tx.get('amount', 0)))
        paid_at = tx.get('completed_at') or tx.get('paid_at')
        payer_email = tx.get('source_email')
    else:  # Local gateways (bkash, nagad, etc.)
        tx_id = tx.get('transaction_id') or tx.get('trx_id') or tx.get('tx_ref')
        amount = Decimal(str(tx.get('amount', 0)))
        paid_at = tx.get('paid_at') or tx.get('created_at')
        payer_email = tx.get('payer_email')
    
    return {
        'transaction_id': tx_id,
        'amount': amount,
        'method': gateway,
        'status': tx.get('status', 'completed'),
        'paid_at': paid_at,
        'order_id': tx.get('order_id') or tx.get('metadata', {}).get('order_id'),
        'order_ref': tx.get('order_ref') or tx.get('reference'),
        'payer_email': payer_email
    }


def reconcile_transactions(
    db: Session,
    business_id: int,
    gateway: str,
    transactions: list[dict],
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> dict:
    """
    Reconcile payment gateway transactions against local records.
    Works with both local (bKash, Nagad) and international (PayPal, Cash App, Stripe) gateways.
    """
    gateway = gateway.lower()
    
    # Normalize all transactions
    normalized = [normalize_gateway_transaction(tx, gateway) for tx in transactions]
    
    # Get local payments for this business and gateway
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
    
    result = {
        'total_transactions': len(normalized),
        'matched': 0,
        'unmatched_remote': [],
        'unmatched_local': [],
        'amount_mismatches': [],
        'status_mismatches': []
    }
    
    # Process each gateway transaction
    for tx in normalized:
        tx_id = tx['transaction_id']
        tx_amount = tx['amount']
        
        # Check if this transaction exists locally
        if tx_id and tx_id in local_by_txid:
            local_payment = local_by_txid[tx_id]
            matched_txids.add(tx_id)
            
            # Check amount match (allow tolerance for currency conversion)
            tolerance = Decimal('0.50') if gateway in ['paypal', 'wise'] else Decimal('0.01')
            if abs(Decimal(str(local_payment.amount)) - tx_amount) > tolerance:
                result['amount_mismatches'].append({
                    'transaction_id': tx_id,
                    'gateway_amount': float(tx_amount),
                    'local_amount': float(local_payment.amount),
                    'difference': float(Decimal(str(local_payment.amount)) - tx_amount)
                })
            else:
                result['matched'] += 1
                
            # Check status match
            if local_payment.status == PaymentStatus.VERIFIED:
                result['matched'] += 1
            else:
                result['status_mismatches'].append({
                    'transaction_id': tx_id,
                    'gateway_status': 'completed',
                    'local_status': local_payment.status.value
                })
        else:
            # Transaction in gateway but not in our DB
            result['unmatched_remote'].append({
                'transaction_id': tx_id,
                'amount': float(tx_amount),
                'paid_at': tx['paid_at'],
                'payer_email': tx.get('payer_email'),
                'status': 'pending_reconciliation'
            })
    
    # Find local transactions not in gateway
    for payment in local_payments:
        if payment.transaction_id and payment.transaction_id not in matched_txids:
            result['unmatched_local'].append({
                'id': payment.id,
                'transaction_id': payment.transaction_id,
                'amount': payment.amount,
                'status': payment.status.value
            })
    
    return result


def reconcile_mobile_payment(
    db: Session,
    business_id: int,
    transaction_id: str,
    amount: Decimal,
    method: str
) -> dict:
    """Verify a single mobile payment transaction (local or international)."""
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


def get_supported_gateways() -> list[dict]:
    """Return list of all supported payment gateways with reconciliation support."""
    return [
        {
            'name': 'bKash',
            'code': 'bkash',
            'type': 'local',
            'country': 'Bangladesh',
            'supports_reconciliation': True,
            'transaction_id_field': 'trx_id'
        },
        {
            'name': 'Nagad',
            'code': 'nagad',
            'type': 'local',
            'country': 'Bangladesh',
            'supports_reconciliation': True,
            'transaction_id_field': 'transaction_id'
        },
        {
            'name': 'Rocket',
            'code': 'rocket',
            'type': 'local',
            'country': 'Bangladesh',
            'supports_reconciliation': True,
            'transaction_id_field': 'transaction_id'
        },
        {
            'name': 'Upay',
            'code': 'upay',
            'type': 'local',
            'country': 'Bangladesh',
            'supports_reconciliation': True,
            'transaction_id_field': 'transaction_id'
        },
        {
            'name': 'PayPal',
            'code': 'paypal',
            'type': 'international',
            'country': 'Global',
            'supports_reconciliation': True,
            'transaction_id_field': 'id'
        },
        {
            'name': 'Cash App',
            'code': 'cashapp',
            'type': 'international',
            'country': 'USA',
            'supports_reconciliation': True,
            'transaction_id_field': 'id'
        },
        {
            'name': 'Stripe',
            'code': 'stripe',
            'type': 'international',
            'country': 'Global',
            'supports_reconciliation': True,
            'transaction_id_field': 'id'
        },
        {
            'name': 'Wise',
            'code': 'wise',
            'type': 'international',
            'country': 'Global',
            'supports_reconciliation': True,
            'transaction_id_field': 'id'
        }
    ]
