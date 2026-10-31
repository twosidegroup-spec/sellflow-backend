"""Order matching for payment events.

ADAPTED from System A's `app/payment/matcher.py`:

* Queries go through System B's SQLAlchemy session instead of raw psycopg.
* The candidate amount comes from `orders.total_amount` (System B's schema);
  System A's denormalized `orders.revenue` does not exist here.
* The customer phone comes from the related `customers` row (System B keeps
  the phone on the customer, not denormalized on the order).
* Tenant scoping is mandatory: the caller passes the verified `business_id`.
* Only CANCELLED orders are excluded: System B's `OrderStatus` enum has no
  "returned"/"failed" members.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.customers.models import Customer
from app.db.base import Order
from app.orders.models import OrderStatus
from app.utils.phone import digits_only, phones_equivalent


class PaymentMatcher:
    def find_candidates(
        self,
        db: Session,
        business_id: int,
        payment_amount: Decimal,
        customer_phone: str | None,
    ) -> list[dict]:
        """Orders in `business_id` that could match this payment.

        Phone comparison is format-tolerant: the payment's sender is stored
        canonical (`8801...`) while a customer's phone may have been entered in
        local form (`01...`). Both sides are reduced to their last 10 digits,
        which is the same rule `phones_equivalent` applies in Python.
        """
        query = (
            db.query(Order)
            .outerjoin(Customer, Order.customer_id == Customer.id)
            .options(joinedload(Order.customer))
            .filter(
                Order.business_id == business_id,
                Order.status != OrderStatus.CANCELLED,
            )
        )
        if customer_phone:
            phone_last10 = (digits_only(customer_phone) or "")[-10:]
            phone_match = func.right(
                func.regexp_replace(Customer.phone, "[^0-9]", "", "g"), 10
            ) == phone_last10
            query = query.filter(
                or_(
                    Order.total_amount == payment_amount,
                    phone_match,
                )
            )
        else:
            query = query.filter(Order.total_amount == payment_amount)

        orders = query.order_by(Order.created_at.desc()).all()
        return [
            {
                "id": order.id,
                "customer_id": order.customer_id,
                "customer_name": order.customer.name if order.customer else None,
                "phone": order.customer.phone if order.customer else None,
                "amount": order.total_amount,
                "created_at": order.created_at,
            }
            for order in orders
        ]

    def evaluate_candidate(
        self,
        order: dict,
        payment_amount: Decimal,
        payment_time: datetime,
        customer_phone: str | None,
    ) -> dict:
        order_amount = Decimal(str(order["amount"]))
        created_at = order["created_at"]
        if created_at.tzinfo is None:
            from datetime import timezone as _timezone

            created_at = created_at.replace(tzinfo=_timezone.utc)
        time_delta = abs((payment_time - created_at).total_seconds())
        customer_match = bool(
            customer_phone and phones_equivalent(customer_phone, order.get("phone"))
        )
        timing_match = time_delta <= 3600
        historical_match = False
        return {
            "order_id": int(order["id"]),
            "customer_match": customer_match,
            "timing_match": timing_match,
            "historical_match": historical_match,
            "amount_match": payment_amount == order_amount,
            "score": (
                (1.0 if payment_amount == order_amount else 0.0) * 0.45
                + (1.0 if customer_match else 0.0) * 0.25
                + (1.0 if timing_match else 0.0) * 0.15
                + (1.0 if historical_match else 0.0) * 0.15
            ),
        }

    def select_best_match(
        self,
        db: Session,
        business_id: int,
        payment_amount: Decimal,
        customer_phone: str | None,
        payment_time: datetime,
    ) -> dict | None:
        """Best candidate order for this payment, within ONE tenant."""
        candidates = self.find_candidates(db, business_id, payment_amount, customer_phone)
        if not candidates:
            return None

        evaluated = [
            self.evaluate_candidate(candidate, payment_amount, payment_time, customer_phone)
            for candidate in candidates
        ]
        if customer_phone:
            phone_matches = [item for item in evaluated if item["customer_match"]]
            if phone_matches:
                return max(phone_matches, key=lambda item: item["score"])

        exact_matches = [item for item in evaluated if item["amount_match"]]
        if exact_matches:
            return max(exact_matches, key=lambda item: item["score"])

        return max(evaluated, key=lambda item: item["score"])


PAYMENT_MATCHER = PaymentMatcher()
