"""Payload normalization (ported from System A's `app/payment/normalizer.py`)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.payments.intelligence.models import NormalizedPaymentEvent
from app.payments.intelligence.providers import PROVIDERS


class PaymentNormalizer:
    def normalize(self, provider_name: str, payload: dict[str, Any]) -> NormalizedPaymentEvent:
        if provider_name not in PROVIDERS:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider_name}")

        adapter = PROVIDERS[provider_name]
        detection = adapter.detect(payload)
        if detection.provider.value != provider_name:
            raise HTTPException(status_code=400, detail="Provider detection failed")
        if detection.confidence < 0.5:
            raise HTTPException(status_code=422, detail="Provider confidence is too low")

        event = adapter.parse(payload)
        if event.amount <= Decimal("0"):
            raise HTTPException(status_code=422, detail="Payment amount must be greater than zero")
        if event.timestamp == "":
            raise HTTPException(status_code=422, detail="Payment timestamp is required")
        return event


PAYMENT_NORMALIZER = PaymentNormalizer()
