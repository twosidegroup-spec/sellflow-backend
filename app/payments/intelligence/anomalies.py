"""Anomaly detection (ported from System A's `app/payment/anomalies.py`)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


class AnomalyEngine:
    def analyze(
        self,
        payment_amount: Decimal,
        order_amount: Decimal | None,
        customer_phone: str | None,
        transaction_id: str,
        previous_event_count: int,
    ) -> list[dict[str, Any]]:
        anomalies: list[dict[str, Any]] = []
        if order_amount is not None and payment_amount > order_amount * Decimal("2"):
            anomalies.append(
                {
                    "type": "overpayment",
                    "severity": "high",
                    "details": {
                        "payment_amount": str(payment_amount),
                        "order_amount": str(order_amount),
                    },
                }
            )
        if order_amount is not None and payment_amount < order_amount * Decimal("0.5"):
            anomalies.append(
                {
                    "type": "underpayment",
                    "severity": "medium",
                    "details": {
                        "payment_amount": str(payment_amount),
                        "order_amount": str(order_amount),
                    },
                }
            )
        if previous_event_count > 0:
            anomalies.append(
                {
                    "type": "repeated_payment",
                    "severity": "medium",
                    "details": {"previous_event_count": previous_event_count},
                }
            )
        if payment_amount >= Decimal("100000"):
            anomalies.append(
                {
                    "type": "large_payment",
                    "severity": "high",
                    "details": {"payment_amount": str(payment_amount)},
                }
            )
        if customer_phone is None:
            anomalies.append(
                {
                    "type": "missing_customer_identifier",
                    "severity": "medium",
                    "details": {},
                }
            )
        return anomalies


ANOMALY_ENGINE = AnomalyEngine()
