from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import secrets
import httpx
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business
from app.webhooks.models import WebhookSubscription
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


router = APIRouter(prefix="/businesses/{business_id}/webhooks", tags=["Webhooks"])


@router.post("/", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
def create_webhook(
    business_id: int,
    data: WebhookCreate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    """Register a webhook endpoint to receive real-time notifications."""
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


async def trigger_webhooks(
    business_id: int,
    event_type: str,
    payload: dict,
    db: Session
):
    """Trigger all active webhooks for an event."""
    import asyncio
    
    webhooks = db.query(WebhookSubscription).filter(
        WebhookSubscription.business_id == business_id,
        WebhookSubscription.is_active == True,
        WebhookSubscription.events.like(f"%{event_type}%")
    ).all()
    
    async def send_webhook(webhook: WebhookSubscription):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook.url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": secrets.token_hex(16)
                    }
                )
                return response.status_code
        except Exception as e:
            return None
    
    # Send all webhooks concurrently
    tasks = [send_webhook(h) for h in webhooks]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
