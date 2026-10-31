from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional

from app.products.models import ProductStatus


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sku: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    cost_price: Decimal = Field(ge=0, decimal_places=2)
    selling_price: Decimal = Field(ge=0, decimal_places=2)
    stock_quantity: int = Field(ge=0, default=0)
    image_url: Optional[str] = Field(default=None)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    cost_price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    selling_price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    stock_quantity: int | None = Field(default=None, ge=0)
    status: ProductStatus | None = None


class ProductRead(BaseModel):
    id: int
    business_id: int
    name: str
    sku: str
    description: str | None
    cost_price: Decimal
    selling_price: Decimal
    stock_quantity: int
    status: ProductStatus = ProductStatus.ACTIVE
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
