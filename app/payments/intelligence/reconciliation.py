"""Payment reconciliation engine.

ADAPTED from System A's `app/payment/reconciliation.py` to System B:

* SQLAlchemy session instead of psycopg connections; the caller (router or
  device-bridge service) owns the transaction and passes a verified
  `business_id`.
* Idempotency comes from the `payment_events` unique constraint
  `(business_id, provider, transaction_id)` plus a pre-check.
* When an exact-amount match is marked paid, the `payments` ledger row uses
  the REAL provider transaction id (System A used a synthetic
  `PAYMENT-INTELLIGENCE-{order_id}`), which removes an entire class of
  duplicate-insert and audit-correlation defects.
* `orders.payment_status` / `orders.payment_method` (added by the migration)
  are updated inside the same transaction as the event and decision rows.

Preserved behaviour, deliberately: an exact-amount match marks the order paid
and records the confidence-engine decision alongside it; partial settlements
mark `partially_paid` but never `verified`; overpayments never auto-mark
anything and are routed to review.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.base import Order
from app.payments.intelligence.anomalies import ANOMALY_ENGINE
from app.payments.intelligence.confidence import CONFIDENCE_ENGINE
from app.payments.intelligence.db_models import (
    PaymentAnomaly,
    PaymentDecision,
    PaymentEvent,
    PaymentMatch,
)
from app.payments.intelligence.matcher import PAYMENT_MATCHER
from app.payments.intelligence.models import PaymentDecision as DecisionEnum
from app.payments.intelligence.models import PaymentEventStatus
from app.payments.models import Payment, PaymentStatus

ENGINE_VERSION = "payment-intelligence-1.0.0"


class PaymentReconciliationEngine:
    def process_event(self, db: Session, business_id: int, normalized: dict) -> dict[str, Any]:
        if business_id is None:
            raise HTTPException(
                status_code=401,
                detail="A verified business is required to record a payment event.",
            )
        business_id = int(business_id)

        provider = normalized["provider"]
        transaction_id = normalized["transaction_id"]
        amount = Decimal(str(normalized["amount"]))
        payment_time = _parse_timestamp(normalized["timestamp"])
        customer_phone = normalized.get("sender_identifier")

        existing = (
            db.query(PaymentEvent)
            .filter(
                PaymentEvent.business_id == business_id,
                PaymentEvent.provider == provider,
                PaymentEvent.transaction_id == transaction_id,
            )
            .first()
        )
        if existing is not None:
            return self._duplicate_result(db, existing, normalized, amount)

        order = PAYMENT_MATCHER.select_best_match(
            db, business_id, amount, customer_phone, payment_time
        )

        order_id: int | None = None
        order_amount: Decimal | None = None
        candidate_result: dict = {}
        if order is not None:
            candidate = (
                db.query(Order)
                .filter(Order.id == order["order_id"], Order.business_id == business_id)
                .first()
            )
            if candidate is not None:
                # `select_best_match` already evaluated this candidate; reuse it.
                candidate_result = order
                order_amount = Decimal(str(candidate.total_amount))
                order_id = int(candidate.id)
            else:
                # The candidate id is not in this tenant; treat as no match.
                order_id = None

        previous_count = self._event_count(db, business_id, customer_phone)
        anomalies = ANOMALY_ENGINE.analyze(
            amount, order_amount, customer_phone, transaction_id, previous_count
        )

        if order_id is None:
            decision = DecisionEnum.REQUIRES_REVIEW
            status = PaymentEventStatus.UNKNOWN_TRANSACTION
            confidence = 0.0
            reason_codes = ["UNKNOWN_ORDER"]
            explanation = (
                "No sufficiently strong order candidate was found. "
                "The payment requires review."
            )
        elif amount == order_amount:
            confidence, reason_codes, decision, status = CONFIDENCE_ENGINE.score(
                order_amount,
                amount,
                bool(candidate_result.get("customer_match")),
                bool(candidate_result.get("timing_match")),
                bool(candidate_result.get("historical_match")),
                False,
            )
            explanation = self._explain(
                decision, reason_codes, amount, order_amount, customer_phone, payment_time, order_id
            )
            self._mark_order_paid(db, business_id, order_id, amount, normalized, payment_time)
            # Consistency: the order IS paid, so the event's reconciliation
            # status is PAID. The confidence engine's decision keeps the nuance
            # (e.g. UNKNOWN_TRANSACTION when only the amount matched) and is
            # stored alongside, so nothing is hidden from the audit trail.
            status = PaymentEventStatus.PAID
        elif amount < order_amount:
            confidence, reason_codes, decision, status = CONFIDENCE_ENGINE.score(
                order_amount,
                amount,
                bool(candidate_result.get("customer_match")),
                bool(candidate_result.get("timing_match")),
                bool(candidate_result.get("historical_match")),
                False,
            )
            explanation = self._explain(
                decision, reason_codes, amount, order_amount, customer_phone, payment_time, order_id
            )
            self._mark_order_partially_paid(
                db, business_id, order_id, amount, normalized, payment_time
            )
        else:
            confidence, reason_codes, decision, status = CONFIDENCE_ENGINE.score(
                order_amount,
                amount,
                bool(candidate_result.get("customer_match")),
                bool(candidate_result.get("timing_match")),
                bool(candidate_result.get("historical_match")),
                False,
            )
            explanation = self._explain(
                decision, reason_codes, amount, order_amount, customer_phone, payment_time, order_id
            )
            status = PaymentEventStatus.OVERPAYMENT
            decision = DecisionEnum.REQUIRES_REVIEW

        event = PaymentEvent(
            business_id=business_id,
            device_id=normalized.get("device_id"),
            provider=provider,
            transaction_id=transaction_id,
            amount=amount,
            currency=normalized.get("currency", "BDT"),
            sender_identifier=normalized.get("sender_identifier"),
            receiver_identifier=normalized.get("receiver_identifier"),
            event_timestamp=payment_time,
            source_type=normalized.get("source_type", "device_event"),
            source=normalized.get("source"),
            raw_metadata=normalized.get("raw_metadata") or {},
            status=status.value,
            confidence=confidence,
        )
        db.add(event)
        db.flush()

        db.add(
            PaymentDecision(
                payment_event_id=event.id,
                order_id=order_id,
                decision=decision.value,
                status=status.value,
                confidence=confidence,
                reason_codes=reason_codes,
                explanation=explanation,
                engine_version=ENGINE_VERSION,
            )
        )
        for anomaly in anomalies:
            db.add(
                PaymentAnomaly(
                    payment_event_id=event.id,
                    anomaly_type=anomaly["type"],
                    severity=anomaly["severity"],
                    details=anomaly["details"],
                )
            )
        if order_id is not None:
            db.add(
                PaymentMatch(
                    payment_event_id=event.id,
                    order_id=order_id,
                    amount_match=bool(candidate_result.get("amount_match")),
                    customer_match=bool(candidate_result.get("customer_match")),
                    timing_match=bool(candidate_result.get("timing_match")),
                    historical_match=bool(candidate_result.get("historical_match")),
                )
            )

        db.commit()
        db.refresh(event)

        return {
            "event_id": event.id,
            "provider": provider,
            "transaction_id": transaction_id,
            "amount": str(amount),
            "currency": normalized.get("currency", "BDT"),
            "status": status.value,
            "decision": decision.value,
            "confidence": round(float(confidence), 4),
            "matched_order_id": order_id,
            "reason_codes": reason_codes,
            "explanation": explanation,
            "anomalies": [anomaly["type"] for anomaly in anomalies],
            "duplicate": False,
        }

    # ------------------------------------------------------------------ helpers

    def _duplicate_result(self, db: Session, existing: PaymentEvent, normalized: dict, amount: Decimal) -> dict:
        latest = (
            db.query(PaymentDecision)
            .filter(PaymentDecision.payment_event_id == existing.id)
            .order_by(PaymentDecision.id.desc())
            .first()
        )
        return {
            "event_id": existing.id,
            "provider": existing.provider,
            "transaction_id": existing.transaction_id,
            "amount": str(amount),
            "currency": normalized.get("currency", "BDT"),
            "status": PaymentEventStatus.DUPLICATE.value,
            "decision": (
                latest.decision if latest else DecisionEnum.DUPLICATE_DETECTED.value
            ),
            "confidence": 0.0,
            "matched_order_id": latest.order_id if latest else None,
            "reason_codes": ["DUPLICATE_DETECTED"],
            "explanation": "This payment event was already processed for this business.",
            "anomalies": [],
            "duplicate": True,
        }

    def _event_count(self, db: Session, business_id: int, customer_phone: str | None) -> int:
        return (
            db.query(PaymentEvent)
            .filter(
                PaymentEvent.business_id == business_id,
                PaymentEvent.sender_identifier == customer_phone,
            )
            .count()
        )

    def _mark_order_paid(
        self,
        db: Session,
        business_id: int,
        order_id: int,
        amount: Decimal,
        normalized: dict,
        payment_time: datetime,
    ) -> None:
        order = (
            db.query(Order)
            .filter(Order.id == order_id, Order.business_id == business_id)
            .first()
        )
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        order.payment_status = "paid"
        order.payment_method = normalized["provider"]

        self._record_payment_row(
            db,
            business_id=business_id,
            order_id=order_id,
            amount=amount,
            normalized=normalized,
            payment_time=payment_time,
            status=PaymentStatus.VERIFIED,
            notes="Auto-matched by payment intelligence",
        )

    def _mark_order_partially_paid(
        self,
        db: Session,
        business_id: int,
        order_id: int,
        amount: Decimal,
        normalized: dict,
        payment_time: datetime,
    ) -> None:
        order = (
            db.query(Order)
            .filter(Order.id == order_id, Order.business_id == business_id)
            .first()
        )
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        order.payment_status = "partially_paid"
        order.payment_method = normalized["provider"]

        self._record_payment_row(
            db,
            business_id=business_id,
            order_id=order_id,
            amount=amount,
            normalized=normalized,
            payment_time=payment_time,
            status=PaymentStatus.PENDING,
            notes="Partial settlement detected by payment intelligence",
        )

    def _record_payment_row(
        self,
        db: Session,
        *,
        business_id: int,
        order_id: int,
        amount: Decimal,
        normalized: dict,
        payment_time: datetime,
        status: PaymentStatus,
        notes: str,
    ) -> None:
        transaction_id = normalized["transaction_id"]
        provider = normalized["provider"]

        existing_payment = (
            db.query(Payment)
            .filter(
                Payment.business_id == business_id,
                Payment.method == provider,
                Payment.transaction_id == transaction_id,
            )
            .first()
        )
        if existing_payment is not None:
            # The provider transaction is already in the ledger (manual entry or
            # an earlier partial). Never duplicate money rows.
            return

        db.add(
            Payment(
                business_id=business_id,
                order_id=order_id,
                amount=amount,
                method=provider,
                transaction_id=transaction_id,
                status=status,
                notes=notes,
                paid_at=payment_time,
            )
        )
        db.flush()

    def _explain(
        self,
        decision: DecisionEnum,
        reason_codes: list[str],
        amount: Decimal,
        order_amount: Decimal | None,
        customer_phone: str | None,
        payment_time: datetime,
        order_id: int | None,
    ) -> str:
        normalized_amount = f"BDT {amount:.2f}"
        normalized_order = f"BDT {order_amount:.2f}" if order_amount is not None else "unknown"
        customer_status = "matched" if customer_phone else "not available"
        return (
            f"Decision: {decision.value}. "
            f"Amount received {normalized_amount} against {normalized_order}. "
            f"Customer phone status: {customer_status}. "
            f"Payment timestamp: {payment_time.isoformat()}. "
            f"Reasons: {', '.join(reason_codes)}."
            f" Order ID: {order_id}."
        )


def _parse_timestamp(value: Any) -> datetime:
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="timestamp must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


PAYMENT_RECONCILIATION_ENGINE = PaymentReconciliationEngine()
