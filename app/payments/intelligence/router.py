"""Payment intelligence API (tenant-scoped).

Every route uses `get_current_business`, so the tenant is verified from the
JWT user's membership — the same authorization architecture as the rest of
System B. Event ingestion through this API is an authenticated, auditable
path; the device bridge has its own device-credential entry point that
converges on the same engine.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.businesses.dependencies import get_current_business
from app.db.base import Business
from app.db.dependencies import get_db
from app.payments.intelligence.models import PaymentEventCreate, PaymentFeedbackCreate
from app.payments.intelligence.service import PAYMENT_INTELLIGENCE_SERVICE

router = APIRouter(
    prefix="/businesses/{business_id}/payments/intelligence",
    tags=["Payment Intelligence"],
)


@router.post("/events/{provider}", status_code=status.HTTP_200_OK)
def create_payment_event(
    provider: str,
    payload: PaymentEventCreate,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Ingest a payment event for the caller's own business."""
    return PAYMENT_INTELLIGENCE_SERVICE.ingest_event(
        db, business_id=current_business.id, payload=payload, provider=provider
    )


@router.get("/events")
def list_payment_events(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
    search: str | None = Query(None, max_length=128),
    provider: str | None = Query(None, pattern=r"^(bkash|nagad|rocket|upay)$"),
    event_status: str | None = Query(None, alias="status", max_length=32),
    from_timestamp: datetime | None = Query(None, alias="from"),
    to_timestamp: datetime | None = Query(None, alias="to"),
    sort: str = Query("newest", pattern=r"^(newest|oldest)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = PAYMENT_INTELLIGENCE_SERVICE.list_events(
        db,
        business_id=current_business.id,
        search=search,
        provider=provider,
        status=event_status,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total_count": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }


@router.get("/summary")
def payment_intelligence_summary(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    return PAYMENT_INTELLIGENCE_SERVICE.summary(db, current_business.id)


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def create_feedback(
    payload: PaymentFeedbackCreate,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Record a correction to a reconciliation decision (own events only)."""
    return PAYMENT_INTELLIGENCE_SERVICE.record_feedback(
        db, business_id=current_business.id, payload=payload
    )


@router.get("/memory")
def get_memory(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """The caller's own payment profile."""
    return PAYMENT_INTELLIGENCE_SERVICE.memory_profile(db, current_business.id)
