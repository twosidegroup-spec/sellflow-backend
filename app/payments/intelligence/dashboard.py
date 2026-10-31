"""Device-bridge payment dashboard.

Replicates the JSON contract of System A's `app/payment/dashboard.py`
(`get_payment_dashboard`) because the Kotlin Payment Bridge app parses exactly
these keys (`DashboardModels.kt`). Keeping the contract is what allows the
bridge APK to migrate to System B without any mobile code change.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.devices.models import Device
from app.payments.intelligence.db_models import PaymentDecision, PaymentEvent
from app.payments.intelligence.service import (
    PAYMENT_INTELLIGENCE_SERVICE,
    _apply_status_filter,
    _serialize_event,
)
from app.payments.models import PaymentAccount

SMS_SOURCE_TYPES = ("sms",)


def resolve_timezone(timezone_name: str):
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        fixed_zone = re.fullmatch(r"(?:GMT|UTC)([+-])(\d{1,2}):?(\d{2})", timezone_name)
        if timezone_name in {"UTC", "GMT", "Etc/UTC"}:
            return timezone.utc
        if fixed_zone:
            direction = 1 if fixed_zone.group(1) == "+" else -1
            return timezone(
                direction * timedelta(hours=int(fixed_zone.group(2)), minutes=int(fixed_zone.group(3)))
            )
        raise HTTPException(
            status_code=422,
            detail="timezone must be a valid IANA time zone or GMT offset",
        ) from exc


def get_payment_dashboard(
    db: Session,
    *,
    business_id: int,
    device: Device,
    timezone_name: str,
    search: str | None,
    provider: str | None,
    payment_status: str | None,
    from_timestamp: datetime | None,
    to_timestamp: datetime | None,
    sort: str,
    limit: int,
    offset: int,
) -> dict:
    local_zone = resolve_timezone(timezone_name)

    now = datetime.now(local_zone)
    today_start = datetime.combine(now.date(), time.min, local_zone)
    tomorrow_start = datetime.combine(now.date() + timedelta(days=1), time.min, local_zone)
    month_start = datetime.combine(date(now.year, now.month, 1), time.min, local_zone)
    next_month_date = date(
        now.year + (1 if now.month == 12 else 0),
        1 if now.month == 12 else now.month + 1,
        1,
    )
    next_month_start = datetime.combine(next_month_date, time.min, local_zone)
    today_start_utc = today_start.astimezone(timezone.utc)
    tomorrow_start_utc = tomorrow_start.astimezone(timezone.utc)
    month_start_utc = month_start.astimezone(timezone.utc)
    next_month_start_utc = next_month_start.astimezone(timezone.utc)

    sms_events = db.query(PaymentEvent).filter(
        PaymentEvent.business_id == business_id,
        PaymentEvent.source_type.in_(SMS_SOURCE_TYPES),
    )

    today_verified = sms_events.filter(
        PaymentEvent.status == "PAID",
        PaymentEvent.event_timestamp >= today_start_utc,
        PaymentEvent.event_timestamp < tomorrow_start_utc,
    )
    month_verified = sms_events.filter(
        PaymentEvent.status == "PAID",
        PaymentEvent.event_timestamp >= month_start_utc,
        PaymentEvent.event_timestamp < next_month_start_utc,
    )

    today_amount = db.query(func.coalesce(func.sum(PaymentEvent.amount), 0)).filter(
        PaymentEvent.business_id == business_id,
        PaymentEvent.source_type.in_(SMS_SOURCE_TYPES),
        PaymentEvent.status == "PAID",
        PaymentEvent.event_timestamp >= today_start_utc,
        PaymentEvent.event_timestamp < tomorrow_start_utc,
    ).scalar()
    month_amount = db.query(func.coalesce(func.sum(PaymentEvent.amount), 0)).filter(
        PaymentEvent.business_id == business_id,
        PaymentEvent.source_type.in_(SMS_SOURCE_TYPES),
        PaymentEvent.status == "PAID",
        PaymentEvent.event_timestamp >= month_start_utc,
        PaymentEvent.event_timestamp < next_month_start_utc,
    ).scalar()
    today_count = today_verified.count()

    latest_verified = (
        db.query(PaymentEvent)
        .filter(
            PaymentEvent.business_id == business_id,
            PaymentEvent.source_type.in_(SMS_SOURCE_TYPES),
            PaymentEvent.status == "PAID",
        )
        .order_by(PaymentEvent.event_timestamp.desc(), PaymentEvent.id.desc())
        .first()
    )

    latest_processed_at = None
    if latest_verified is not None:
        latest_decision = (
            db.query(PaymentDecision)
            .filter(PaymentDecision.payment_event_id == latest_verified.id)
            .order_by(PaymentDecision.id.desc())
            .first()
        )
        latest_processed_at = latest_decision.created_at if latest_decision else None

    latest_accepted = (
        db.query(PaymentEvent)
        .filter(
            PaymentEvent.business_id == business_id,
            PaymentEvent.source_type.in_(SMS_SOURCE_TYPES),
        )
        .order_by(PaymentEvent.event_timestamp.desc(), PaymentEvent.id.desc())
        .first()
    )

    recent_issue_rows = (
        db.query(PaymentEvent)
        .filter(
            PaymentEvent.business_id == business_id,
            PaymentEvent.source_type.in_(SMS_SOURCE_TYPES),
            PaymentEvent.status != "PAID",
        )
        .order_by(PaymentEvent.event_timestamp.desc(), PaymentEvent.id.desc())
        .limit(5)
        .all()
    )
    recent_issues = []
    for event in recent_issue_rows:
        decision = (
            db.query(PaymentDecision)
            .filter(PaymentDecision.payment_event_id == event.id)
            .order_by(PaymentDecision.id.desc())
            .first()
        )
        recent_issues.append(
            {
                "transaction_id": event.transaction_id,
                "status": event.status,
                "decision": decision.decision if decision else None,
                "timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
            }
        )

    # The list query mirrors System A: SMS-sourced events only, same filters.
    query = db.query(PaymentEvent).filter(
        PaymentEvent.business_id == business_id,
        PaymentEvent.source_type.in_(SMS_SOURCE_TYPES),
    )
    if search and search.strip():
        needle = f"%{search.strip()}%"
        query = query.filter(
            (PaymentEvent.sender_identifier.ilike(needle))
            | (PaymentEvent.transaction_id.ilike(needle))
        )
    if provider:
        query = query.filter(PaymentEvent.provider == provider.strip().lower())
    if payment_status:
        query = _apply_status_filter(query, payment_status)
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

    total_count = query.count()
    ascending = sort == "oldest"
    order_column = PaymentEvent.event_timestamp.asc() if ascending else PaymentEvent.event_timestamp.desc()
    id_column = PaymentEvent.id.asc() if ascending else PaymentEvent.id.desc()
    events = (
        query.order_by(order_column, id_column)
        .limit(limit)
        .offset(offset)
        .all()
    )

    from app.payments.intelligence.service import _latest_decisions

    decisions = _latest_decisions(db, [event.id for event in events])
    items = [_serialize_event(event, decisions.get(event.id)) for event in events]

    account = (
        db.query(PaymentAccount)
        .filter(PaymentAccount.business_id == business_id)
        .order_by(PaymentAccount.id.asc())
        .first()
    )
    masked_receiver = None
    if account and account.receiving_number:
        number = account.receiving_number
        masked_receiver = f"****{number[-4:]}" if len(number) > 4 else "****"

    latest_verified_amount = None
    latest_verified_at = None
    if latest_verified is not None:
        latest_verified_amount = str(Decimal(str(latest_verified.amount)))
        latest_verified_at = (
            latest_verified.event_timestamp.isoformat() if latest_verified.event_timestamp else None
        )

    return {
        "timezone": timezone_name,
        "metrics": {
            "today_verified_amount": str(
                Decimal(str(today_amount)).quantize(Decimal("0.01"))
            ),
            "month_verified_amount": str(
                Decimal(str(month_amount)).quantize(Decimal("0.01"))
            ),
            "today_verified_transactions": int(today_count),
            "latest_verified_amount": latest_verified_amount,
            "latest_verified_at": latest_verified_at,
        },
        "system": {
            "device_name": device.device_name if device else None,
            "device_paired": bool(device and device.status == "paired"),
            "sms_permission_granted": bool(device and device.sms_permission_granted),
            "monitoring_active": bool(device and device.monitoring_active),
            "account_provider": account.provider if account else None,
            "receiving_number_masked": masked_receiver,
            "last_accepted_event_at": (
                latest_accepted.event_timestamp.isoformat() if latest_accepted else None
            ),
            "last_verified_payment_at": latest_verified_at,
            "last_verified_processed_at": (
                latest_processed_at.isoformat() if latest_processed_at else None
            ),
            "recent_unverified_events": recent_issues,
        },
        "items": items,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total_count,
    }
