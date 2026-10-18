from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime
from app.payments.models import PaymentStatus

class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    method: str = Field(min_length=1, max_length=50)
    transaction_id: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)

class PaymentRead(BaseModel):
    id: int
    business_id: int
    order_id: int
    amount: Decimal
    method: str
    transaction_id: str | None
    status: PaymentStatus
    notes: str | None
    paid_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
