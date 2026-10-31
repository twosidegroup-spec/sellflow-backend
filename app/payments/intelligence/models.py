"""Pydantic contracts for payment intelligence (ported from System A)."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Provider(str, Enum):
    BKASH = "bkash"
    NAGAD = "nagad"
    ROCKET = "rocket"
    UPAY = "upay"


class PaymentEventStatus(str, Enum):
    PENDING = "PENDING"
    MATCHED = "MATCHED"
    PAID = "PAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    UNKNOWN_TRANSACTION = "UNKNOWN_TRANSACTION"
    DUPLICATE = "DUPLICATE"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    OVERPAYMENT = "OVERPAYMENT"


class PaymentDecision(str, Enum):
    AUTO_MATCHED = "AUTO_MATCHED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    DUPLICATE_DETECTED = "DUPLICATE_DETECTED"
    UNKNOWN_TRANSACTION = "UNKNOWN_TRANSACTION"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    OVERPAYMENT = "OVERPAYMENT"


class PaymentSourceType(str, Enum):
    DEVICE_EVENT = "device_event"
    SMS = "sms"
    API = "api"
    MANUAL = "manual"


class ProviderDetectionResult(BaseModel):
    provider: Provider
    confidence: float = Field(ge=0, le=1)


class NormalizedPaymentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Provider
    transaction_id: str
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    sender_identifier: str | None = None
    receiver_identifier: str | None = None
    timestamp: str
    source_type: PaymentSourceType
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("transaction_id")
    @classmethod
    def validate_transaction_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("transaction_id is required")
        return normalized

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("sender_identifier", "receiver_identifier")
    @classmethod
    def normalize_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class PaymentEventCreate(BaseModel):
    """A payment event as submitted to the intelligence pipeline.

    `device_id` and `source` are optional attribution fields: the device
    bridge sets them; manual/API callers normally do not.
    """

    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    amount: Decimal = Field(gt=0)
    currency: str = "BDT"
    sender_identifier: str | None = None
    receiver_identifier: str | None = None
    timestamp: str
    source_type: PaymentSourceType = PaymentSourceType.DEVICE_EVENT
    device_id: int | None = None
    source: str | None = None

    @field_validator("transaction_id")
    @classmethod
    def validate_transaction_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("transaction_id is required")
        return normalized

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()


class PaymentFeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_event_id: int
    order_id: int
    from_decision: str
    correct_decision: str
    correction_reason: str = Field(min_length=1, max_length=2000)


class PaymentIntelligenceResult(BaseModel):
    event_id: int
    provider: str
    transaction_id: str
    amount: str
    currency: str
    status: PaymentEventStatus
    decision: PaymentDecision
    confidence: float
    matched_order_id: int | None = None
    reason_codes: list[str]
    explanation: str
    anomalies: list[str]
    duplicate: bool = False
