"""Provider adapters (ported from System A's `app/payment/providers`).

Only bKash has an adapter today. The registry shape is preserved so the
Nagad/Rocket/Upay adapters can be added without touching the normalizer.
Adding an adapter here is NOT a provider integration: it only normalizes a
payload that some trusted ingest path already accepted.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from app.payments.intelligence.models import (
    NormalizedPaymentEvent,
    PaymentSourceType,
    Provider,
    ProviderDetectionResult,
)


class ProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    def detect(self, payload: dict) -> ProviderDetectionResult: ...

    @abstractmethod
    def parse(self, payload: dict) -> NormalizedPaymentEvent: ...


class BkashProviderAdapter(ProviderAdapter):
    provider_name = Provider.BKASH.value

    def detect(self, payload: dict) -> ProviderDetectionResult:
        transaction_id = payload.get("transaction_id", "")
        amount = payload.get("amount")
        sender = payload.get("sender_identifier", "")
        receiver = payload.get("receiver_identifier", "")

        score = 0.0
        if transaction_id:
            score += 0.35
        if amount is not None:
            score += 0.25
        if sender:
            score += 0.2
        if receiver:
            score += 0.2

        return ProviderDetectionResult(
            provider=Provider.BKASH,
            confidence=min(score, 0.99),
        )

    def parse(self, payload: dict) -> NormalizedPaymentEvent:
        amount = payload["amount"]
        if isinstance(amount, str):
            amount = Decimal(amount)

        return NormalizedPaymentEvent(
            provider=Provider.BKASH,
            transaction_id=str(payload["transaction_id"]).strip(),
            amount=amount,
            currency=str(payload.get("currency", "BDT")).strip().upper(),
            sender_identifier=payload.get("sender_identifier"),
            receiver_identifier=payload.get("receiver_identifier"),
            timestamp=str(payload["timestamp"]).strip(),
            source_type=PaymentSourceType(payload.get("source_type", "device_event")),
            raw_metadata={
                "transaction_id": str(payload.get("transaction_id", "")).strip(),
                "receiver_identifier": payload.get("receiver_identifier"),
            },
        )


PROVIDERS: dict[str, ProviderAdapter] = {
    BkashProviderAdapter.provider_name: BkashProviderAdapter(),
}

SUPPORTED_PROVIDERS = tuple(PROVIDERS.keys())
