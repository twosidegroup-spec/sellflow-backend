from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import List
from app.orders.models import OrderStatus

class OrderItemCreate(BaseModel):
    product_id: int | None = None
    product_name: str = Field(min_length=1, max_length=255)
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(ge=0, decimal_places=2)
    unit_cost: Decimal = Field(ge=0, decimal_places=2)

class OrderCreate(BaseModel):
    customer_id: int | None = None
    items: List[OrderItemCreate]
    delivery_fee: Decimal = Field(ge=0, decimal_places=2, default=0.0)
    discount: Decimal = Field(ge=0, decimal_places=2, default=0.0)
    notes: str | None = Field(default=None, max_length=1000)

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderItemRead(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    quantity: int
    unit_price: Decimal
    unit_cost: Decimal
    line_total: Decimal
    cost_total: Decimal
    profit: Decimal
    model_config = ConfigDict(from_attributes=True)

class OrderRead(BaseModel):
    id: int
    business_id: int
    customer_id: int | None
    status: OrderStatus
    total_amount: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    delivery_fee: Decimal
    discount: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemRead]
    model_config = ConfigDict(from_attributes=True)
