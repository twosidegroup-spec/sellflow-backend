from pydantic import BaseModel, Field, ConfigDict, field_validator
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Literal
from enum import Enum

class PaymentMethod(str, Enum):
    # Local (Bangladesh)
    BKASH = "bkash"
    NAGAD = "nagad"
    ROCKET = "rocket"
    UPAY = "upay"
    # International
    PAYPAL = "paypal"
    CASHAPP = "cashapp"
    STRIPE = "stripe"
    WISE = "wise"
    # Manual
    CASH = "cash"


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    method: str = Field(min_length=1, max_length=50)
    transaction_id: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        allowed = [m.value for m in PaymentMethod]
        if v.lower() not in allowed:
            raise ValueError(f"Invalid payment method. Allowed: {', '.join(allowed)}")
        return v.lower()


class PaymentRead(BaseModel):
    id: int
    business_id: int
    order_id: int
    amount: Decimal
    method: str
    transaction_id: str | None
    status: str  # Using string instead of Enum for flexibility
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
    # International specific fields
    payer_email: Optional[str] = None
    buyer_id: Optional[str] = None


class ReconciliationRequest(BaseModel):
    gateway: str = Field(..., description="Payment gateway name (bkash, paypal, stripe, etc.)")
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


class DetectionRequest(BaseModel):
    receiver_number: str = Field(min_length=1, max_length=50)
    amount: Decimal = Field(gt=0, decimal_places=2)
    method: str = Field(min_length=1, max_length=50)
    sender_number: Optional[str] = Field(default=None, max_length=50)
    transaction_id: Optional[str] = Field(default=None, max_length=255)
    paid_at: Optional[datetime] = None


class DetectionResponse(BaseModel):
    detection_id: int
    business_id: int
    matched: bool
    order_id: Optional[int] = None
    payment_id: Optional[int] = None


class DetectedPaymentRead(BaseModel):
    id: int
    business_id: int
    amount: Decimal
    method: str
    sender_number: Optional[str]
    receiver_number: Optional[str]
    transaction_id: Optional[str]
    paid_at: Optional[datetime]
    matched: bool
    order_id: Optional[int]
    payment_id: Optional[int]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
