"""Seller payment memory (adapted from System A's `app/payment/memory.py`).

Maintains per-business aggregate profiles used for context in reviews.
SQLAlchemy instead of raw psycopg; same metric semantics where System B's
schema provides the columns (order value, payment value, time-to-payment,
partial and mismatch rates).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db.base import Order
from app.payments.intelligence.db_models import SellerPaymentProfile
from app.payments.models import Payment, PaymentStatus


class SellerPaymentMemory:
    def get_profile(self, db: Session, business_id: int) -> dict:
        profile = (
            db.query(SellerPaymentProfile)
            .filter(SellerPaymentProfile.business_id == business_id)
            .first()
        )
        if profile is None:
            return {
                "average_order_value": "0.00",
                "average_payment_amount": "0.00",
                "average_time_to_payment_seconds": 0,
                "partial_payment_rate": 0.0,
                "payment_mismatch_rate": 0.0,
            }
        return {
            "average_order_value": str(profile.average_order_value),
            "average_payment_amount": str(profile.average_payment_amount),
            "average_time_to_payment_seconds": int(profile.average_time_to_payment_seconds),
            "partial_payment_rate": float(profile.partial_payment_rate),
            "payment_mismatch_rate": float(profile.payment_mismatch_rate),
        }

    def update_profile(self, db: Session, business_id: int) -> dict:
        average_order_value = db.query(
            func.coalesce(func.avg(Order.total_amount), 0)
        ).filter(Order.business_id == business_id).scalar()

        average_payment_amount = db.query(
            func.coalesce(func.avg(Payment.amount), 0)
        ).filter(
            Payment.business_id == business_id,
            Payment.status == PaymentStatus.VERIFIED,
        ).scalar()

        average_time_to_payment_seconds = db.query(
            func.coalesce(
                func.avg(func.extract("epoch", Payment.paid_at - Order.created_at)),
                0,
            )
        ).join(Order, Payment.order_id == Order.id).filter(
            Payment.business_id == business_id,
            Payment.paid_at.isnot(None),
        ).scalar()

        partial_payment_rate = db.query(
            func.coalesce(
                func.avg(case((Order.payment_status == "partially_paid", 1.0), else_=0.0)),
                0,
            )
        ).filter(Order.business_id == business_id).scalar()

        payment_mismatch_rate = db.query(
            func.coalesce(
                func.avg(case((Order.payment_status == "pending", 1.0), else_=0.0)),
                0,
            )
        ).filter(Order.business_id == business_id).scalar()

        profile = (
            db.query(SellerPaymentProfile)
            .filter(SellerPaymentProfile.business_id == business_id)
            .first()
        )
        if profile is None:
            profile = SellerPaymentProfile(business_id=business_id)
            db.add(profile)

        profile.average_order_value = Decimal(str(average_order_value))
        profile.average_payment_amount = Decimal(str(average_payment_amount))
        profile.average_time_to_payment_seconds = int(float(average_time_to_payment_seconds or 0))
        profile.partial_payment_rate = Decimal(str(float(partial_payment_rate or 0)))
        profile.payment_mismatch_rate = Decimal(str(float(payment_mismatch_rate or 0)))
        db.commit()
        db.refresh(profile)
        return self.get_profile(db, business_id)


SELLER_PAYMENT_MEMORY = SellerPaymentMemory()
