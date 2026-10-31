from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import secrets
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business
from app.webhooks.models import WebhookSubscription
from app.webhooks.dispatcher import is_safe_webhook_url
from pydantic import BaseModel, Field, ConfigDict


class WebhookCreate(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    events: str = Field(..., min_length=1)  # comma-separated: "payment.completed,order.created"
    secret_key: str | None = Field(default=None, max_length=64)
    is_active: bool = Field(default=True)


class WebhookRead(BaseModel):
    id: int
    business_id: int
    url: str
    events: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WebhookCreated(WebhookRead):
    """Creation response: exposes the signing secret exactly once."""

    secret_key: str


router = APIRouter(prefix="/businesses/{business_id}/webhooks", tags=["Webhooks"])


@router.post("/", response_model=WebhookCreated, status_code=status.HTTP_201_CREATED)
def create_webhook(
    business_id: int,
    data: WebhookCreate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """Register a webhook endpoint to receive signed, real-time notifications.

    The payload is signed with HMAC-SHA256 over the exact request body using
    the returned `secret_key`; verify by recomputing
    `sha256=hex(hmac(secret, body))` and comparing to `X-Webhook-Signature`.
    """
    safe, reason = is_safe_webhook_url(data.url)
    if not safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook URL rejected: {reason}",
        )

    secret_key = data.secret_key or secrets.token_hex(32)
    
    webhook = WebhookSubscription(
        business_id=business_id,
        url=data.url,
        events=data.events,
        secret_key=secret_key,
        is_active=data.is_active
    )
    
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    
    return webhook


@router.get("/", response_model=list[WebhookRead])
def list_webhooks(
    business_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """List all webhook subscriptions for this business."""
    return db.query(WebhookSubscription).filter(
        WebhookSubscription.business_id == business_id
    ).all()


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    business_id: int,
    webhook_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """Delete a webhook subscription."""
    webhook = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == webhook_id,
        WebhookSubscription.business_id == business_id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    db.delete(webhook)
    db.commit()
