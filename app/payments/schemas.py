from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from enum import Enum
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


class GatewayTransaction(BaseModel):
    transaction_id: str
    amount: Decimal
    method: str
    status: str
    paid_at: Optional[datetime] = None
    order_id: Optional[int] = None
    order_ref: Optional[str] = None


class ReconciliationRequest(BaseModel):
    gateway: str = Field(..., description="Payment gateway name")
    transactions: List[GatewayTransaction] = Field(..., description="Transactions from gateway")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ReconciliationResponse(BaseModel):
    total_transactions: int
    matched: int
    unmatched_remote: List[dict]
    unmatched_local: List[dict]
    amount_mismatches: List[dict]
    status_mismatches: List[dict]
    processed_at: datetime


class MobilePaymentVerification(BaseModel):
    transaction_id: str
    amount: Decimal
    method: str
    order_id: Optional[int] = None


class MobilePaymentVerificationResponse(BaseModel):
    verified: bool
    status: str
    amount: Optional[float]
    order_id: Optional[int]
    paid_at: Optional[str]


class ReconciliationReport(BaseModel):
    business_id: int
    gateway: str
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    total_local_payments: int
    total_gateway_transactions: int
    match_rate: float
    discrepancy_amount: Decimal
    recommendations: List[str]
    generated_at: datetime
