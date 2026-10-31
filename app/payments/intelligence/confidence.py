"""Deterministic, explainable confidence scoring (ported from System A).

Thresholds and weights are unchanged: exact amount 0.45, customer 0.25,
timing 0.15, historical 0.15. Overpayment and partial settlements are capped
at MEDIUM and can never auto-verify.
"""

from __future__ import annotations

from decimal import Decimal

from app.payments.intelligence.models import PaymentDecision, PaymentEventStatus


class ConfidenceEngine:
    VERY_HIGH = 0.95
    MEDIUM = 0.75

    def score(
        self,
        order_amount: Decimal,
        payment_amount: Decimal,
        customer_match: bool,
        timing_match: bool,
        historical_match: bool,
        is_duplicate: bool,
    ) -> tuple[float, list[str], PaymentDecision, PaymentEventStatus]:
        scores: dict[str, float] = {
            "EXACT_AMOUNT_MATCH": 1.0 if payment_amount == order_amount else 0.0,
            "CUSTOMER_MATCH": 1.0 if customer_match else 0.0,
            "TIME_MATCH": 1.0 if timing_match else 0.0,
            "HISTORICAL_MATCH": 1.0 if historical_match else 0.0,
            "DUPLICATE_DETECTED": 0.0 if not is_duplicate else 1.0,
        }

        reason_codes = [name for name, value in scores.items() if value > 0]
        if is_duplicate:
            return (
                0.0,
                ["DUPLICATE_DETECTED"],
                PaymentDecision.DUPLICATE_DETECTED,
                PaymentEventStatus.DUPLICATE,
            )

        combined = (
            scores["EXACT_AMOUNT_MATCH"] * 0.45
            + scores["CUSTOMER_MATCH"] * 0.25
            + scores["TIME_MATCH"] * 0.15
            + scores["HISTORICAL_MATCH"] * 0.15
        )

        if payment_amount > order_amount:
            return (
                min(combined, self.MEDIUM),
                ["EXACT_AMOUNT_MATCH" if payment_amount == order_amount else "AMOUNT_MISMATCH"],
                PaymentDecision.OVERPAYMENT,
                PaymentEventStatus.OVERPAYMENT,
            )

        if payment_amount < order_amount:
            return (
                min(combined, self.MEDIUM),
                ["EXACT_AMOUNT_MATCH" if payment_amount == order_amount else "PARTIAL_PAYMENT"],
                PaymentDecision.PARTIALLY_PAID,
                PaymentEventStatus.PARTIALLY_PAID,
            )

        if customer_match and payment_amount == order_amount:
            return (
                self.VERY_HIGH,
                ["EXACT_AMOUNT_MATCH", "CUSTOMER_MATCH"],
                PaymentDecision.AUTO_MATCHED,
                PaymentEventStatus.PAID,
            )

        if combined >= self.VERY_HIGH:
            return combined, reason_codes, PaymentDecision.AUTO_MATCHED, PaymentEventStatus.PAID

        if combined >= self.MEDIUM:
            return (
                combined,
                reason_codes,
                PaymentDecision.REQUIRES_REVIEW,
                PaymentEventStatus.REQUIRES_REVIEW,
            )

        return (
            combined,
            reason_codes,
            PaymentDecision.UNKNOWN_TRANSACTION,
            PaymentEventStatus.UNKNOWN_TRANSACTION,
        )


CONFIDENCE_ENGINE = ConfidenceEngine()
