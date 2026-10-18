from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime
from app.deliveries.models import DeliveryStatus

class DeliveryCreate(BaseModel):
    courier: str | None = Field(default=None, max_length=100)
    tracking_number: str | None = Field(default=None, max_length=255)
    delivery_fee: Decimal = Field(ge=0, decimal_places=2, default=0.0)

class DeliveryUpdate(BaseModel):
    status: DeliveryStatus | None = None
    courier: str | None = Field(default=None, max_length=100)
    tracking_number: str | None = Field(default=None, max_length=255)

class DeliveryRead(BaseModel):
    id: int
    business_id: int
    order_id: int
    courier: str | None
    tracking_number: str | None
    delivery_fee: Decimal
    status: DeliveryStatus
    shipped_at: datetime | None
    delivered_at: datetime | None
    returned_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
