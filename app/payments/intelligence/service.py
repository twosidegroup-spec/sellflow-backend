"""High-level payment-intelligence service used by routers and the bridge."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.payments.intelligence.db_models import (
    PaymentDecision,
    PaymentEvent,
    PaymentFeedback,
)
from app.payments.intelligence.memory import SELLER_PAYMENT_MEMORY
from app.payments.intelligence.models import PaymentEventCreate, PaymentFeedbackCreate
from app.payments.intelligence.normalizer import PAYMENT_NORMALIZER
from app.payments.intelligence.reconciliation import PAYMENT_RECONCILIATION_ENGINE
from app.utils.phone import normalize_phone

VERIFICATION_STATUS = {
    "PAID": "verified",
    "FAILED": "rejected",
    "REFUNDED": "refunded",
    "DUPLICATE": "duplicate",
}

REVIEW_STATUSES = (
    "REQUIRES_REVIEW",
    "UNKNOWN_TRANSACTION",
    "AMOUNT_MISMATCH",
    "OVERPAYMENT",
)

DEFAULT_PROVIDER = "bkash"


class PaymentIntelligenceService:
    # ------------------------------------------------------------------ ingest

    def ingest_event(
        self,
        db: Session,
        business_id: int,
        payload: PaymentEventCreate,
        provider: str = DEFAULT_PROVIDER,
    ) -> dict[str, Any]:
        provider = provider.strip().lower()

        status = _validated_phone(payload.sender_identifier, "sender_identifier")
        receiver = _validated_phone(payload.receiver_identifier, "receiver_identifier")

        normalized = PAYMENT_NORMALIZER.normalize(
            provider,
            {
                "transaction_id": payload.transaction_id,
                "amount": str(payload.amount),
                "currency": payload.currency,
                "sender_identifier": status,
                "receiver_identifier": receiver,
                "timestamp": payload.timestamp,
                "source_type": payload.source_type.value,
            },
        )
        normalized_dict = {
            "provider": normalized.provider.value,
            "transaction_id": normalized.transaction_id,
            "amount": normalized.amount,
            "currency": normalized.currency,
            "sender_identifier": normalized.sender_identifier,
            "receiver_identifier": normalized.receiver_identifier,
            "timestamp": normalized.timestamp,
            "source_type": normalized.source_type.value,
            "device_id": payload.device_id,
            "source": payload.source,
            "raw_metadata": normalized.raw_metadata,
        }
        return PAYMENT_RECONCILIATION_ENGINE.process_event(db, business_id, normalized_dict)

    # -------------------------------------------------------------------- read

    def list_events(
        self,
        db: Session,
        business_id: int,
        *,
        search: str | None = None,
        provider: str | None = None,
        status: str | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
        sort: str = "newest",
        limit: int = 50,
        offset: int = 0,
        source_type: str | None = None,
    ) -> tuple[list[dict], int]:
        query = db.query(PaymentEvent).filter(PaymentEvent.business_id == business_id)

        if source_type:
            query = query.filter(PaymentEvent.source_type == source_type)

        if search and search.strip():
            needle = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    PaymentEvent.transaction_id.ilike(needle),
                    PaymentEvent.sender_identifier.ilike(needle),
                )
            )
        if provider:
            query = query.filter(PaymentEvent.provider == provider.strip().lower())
        if status:
            query = _apply_status_filter(query, status)
        if from_timestamp is not None:
            if from_timestamp.utcoffset() is None:
                raise HTTPException(status_code=422, detail="from must include a timezone")
            query = query.filter(PaymentEvent.event_timestamp >= from_timestamp)
        if to_timestamp is not None:
            if to_timestamp.utcoffset() is None:
                raise HTTPException(status_code=422, detail="to must include a timezone")
            query = query.filter(PaymentEvent.event_timestamp < to_timestamp)
        if from_timestamp and to_timestamp and from_timestamp >= to_timestamp:
            raise HTTPException(status_code=422, detail="from must be before to")

        total = query.count()
        ascending = sort == "oldest"
        order_column = PaymentEvent.event_timestamp.asc() if ascending else PaymentEvent.event_timestamp.desc()
        id_column = PaymentEvent.id.asc() if ascending else PaymentEvent.id.desc()
        events = (
            query.order_by(order_column, id_column)
            .limit(max(1, min(limit, 200)))
            .offset(max(0, offset))
            .all()
        )

        decisions = _latest_decisions(db, [event.id for event in events])
        return [_serialize_event(event, decisions.get(event.id)) for event in events], total

    def summary(self, db: Session, business_id: int) -> dict[str, Any]:
        counts = dict(
            db.query(PaymentEvent.status, func.count(PaymentEvent.id))
            .filter(PaymentEvent.business_id == business_id)
            .group_by(PaymentEvent.status)
            .all()
        )
        total = sum(counts.values())

        verified_total = db.query(
            func.coalesce(func.sum(PaymentEvent.amount), 0)
        ).filter(
            PaymentEvent.business_id == business_id,
            PaymentEvent.status == "PAID",
        ).scalar()

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        verified_today = db.query(
            func.coalesce(func.sum(PaymentEvent.amount), 0)
        ).filter(
            PaymentEvent.business_id == business_id,
            PaymentEvent.status == "PAID",
            PaymentEvent.event_timestamp >= today_start,
        ).scalar()

        last_event = (
            db.query(PaymentEvent)
            .filter(PaymentEvent.business_id == business_id)
            .order_by(PaymentEvent.event_timestamp.desc(), PaymentEvent.id.desc())
            .first()
        )

        review_count = sum(counts.get(state, 0) for state in REVIEW_STATUSES)

        return {
            "business_id": business_id,
            "total_events": total,
            "paid_events": counts.get("PAID", 0),
            "partial_events": counts.get("PARTIALLY_PAID", 0),
            "duplicate_events": counts.get("DUPLICATE", 0),
            "review_events": review_count,
            "verified_amount_total": str(Decimal(str(verified_total)).quantize(Decimal("0.01"))),
            "verified_amount_today": str(Decimal(str(verified_today)).quantize(Decimal("0.01"))),
            "last_event_at": last_event.event_timestamp.isoformat() if last_event else None,
            "by_status": {key: int(value) for key, value in counts.items()},
        }

    # ---------------------------------------------------------------- feedback

    def record_feedback(
        self, db: Session, business_id: int, payload: PaymentFeedbackCreate
    ) -> dict[str, Any]:
        event = (
            db.query(PaymentEvent)
            .filter(
                PaymentEvent.id == payload.payment_event_id,
                PaymentEvent.business_id == business_id,
            )
            .first()
        )
        if event is None:
            raise HTTPException(
                status_code=404, detail="No such payment event for this business."
            )

        db.add(
            PaymentFeedback(
                business_id=business_id,
                payment_event_id=payload.payment_event_id,
                order_id=payload.order_id,
                from_decision=payload.from_decision,
                correct_decision=payload.correct_decision,
                correction_reason=payload.correction_reason,
            )
        )
        db.commit()
        SELLER_PAYMENT_MEMORY.update_profile(db, business_id)
        return {"stored": True, "payment_event_id": payload.payment_event_id}

    def memory_profile(self, db: Session, business_id: int) -> dict[str, Any]:
        return {"business_id": business_id, **SELLER_PAYMENT_MEMORY.get_profile(db, business_id)}


def _validated_phone(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    try:
        return normalize_phone(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must be a valid Bangladesh mobile number",
        ) from exc


def _apply_status_filter(query, status: str):
    normalized = status.strip().lower()
    if normalized == "verified":
        return query.filter(PaymentEvent.status == "PAID")
    if normalized in {"pending_verification", "pending"}:
        return query.filter(
            PaymentEvent.status.notin_(("PAID", "FAILED", "REFUNDED", "DUPLICATE"))
        )
    if normalized == "rejected":
        return query.filter(PaymentEvent.status == "FAILED")
    if normalized == "refunded":
        return query.filter(PaymentEvent.status == "REFUNDED")
    if normalized == "duplicate":
        return query.filter(PaymentEvent.status == "DUPLICATE")
    if normalized == "partial":
        return query.filter(PaymentEvent.status == "PARTIALLY_PAID")
    if normalized == "review":
        return query.filter(PaymentEvent.status.in_(REVIEW_STATUSES))
    return query.filter(func.lower(PaymentEvent.status) == normalized)


def _latest_decisions(db: Session, event_ids: list[int]) -> dict[int, PaymentDecision]:
    if not event_ids:
        return {}
    rows = (
        db.query(PaymentDecision)
        .filter(PaymentDecision.payment_event_id.in_(event_ids))
        .order_by(PaymentDecision.payment_event_id.asc(), PaymentDecision.id.desc())
        .all()
    )
    latest: dict[int, PaymentDecision] = {}
    for row in rows:
        if row.payment_event_id not in latest:
            latest[row.payment_event_id] = row
    return latest


def _serialize_event(event: PaymentEvent, decision: PaymentDecision | None) -> dict[str, Any]:
    amount = Decimal(str(event.amount)).quantize(Decimal("0.01"))
    return {
        "event_id": event.id,
        "provider": event.provider,
        "transaction_id": event.transaction_id,
        "amount": str(amount),
        "currency": event.currency,
        "sender_identifier": event.sender_identifier,
        "receiver_identifier": (
            f"****{event.receiver_identifier[-4:]}"
            if event.receiver_identifier and len(event.receiver_identifier) > 4
            else ("****" if event.receiver_identifier else None)
        ),
        "event_timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
        "source_type": event.source_type,
        "status": event.status,
        "confidence": round(float(event.confidence), 4),
        "decision": decision.decision if decision else None,
        "order_id": decision.order_id if decision else None,
        "reason_codes": list(decision.reason_codes or []) if decision else [],
        "explanation": decision.explanation if decision else None,
        "verification_status": VERIFICATION_STATUS.get(event.status, "pending_verification"),
    }


PAYMENT_INTELLIGENCE_SERVICE = PaymentIntelligenceService()
