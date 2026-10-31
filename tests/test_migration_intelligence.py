"""Regression tests for the migrated payment-intelligence pipeline.

These are integration tests against the isolated test database (guarded by
`tests/conftest.py`). They exercise the REAL API paths: order creation via
System B's router, ingestion via the intelligence endpoint, and the database
state produced by the reconciliation engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import uuid

import pytest

from tests.conftest import create_order, register_seller

from app.payments.intelligence.confidence import CONFIDENCE_ENGINE
from app.payments.intelligence.models import PaymentDecision, PaymentEventStatus
from app.payments.models import Payment, PaymentStatus


def _event_payload(
    *,
    transaction_id: str,
    amount: str,
    sender: str | None = None,
    timestamp: str | None = None,
) -> dict:
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": "BDT",
        "sender_identifier": sender,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------- pure logic


def test_confidence_exact_amount_and_customer_is_auto_matched():
    confidence, reasons, decision, status = CONFIDENCE_ENGINE.score(
        order_amount=Decimal("500.00"),
        payment_amount=Decimal("500.00"),
        customer_match=True,
        timing_match=True,
        historical_match=False,
        is_duplicate=False,
    )
    assert decision == PaymentDecision.AUTO_MATCHED
    assert status == PaymentEventStatus.PAID
    assert confidence >= 0.95
    assert "EXACT_AMOUNT_MATCH" in reasons


def test_confidence_partial_payment_can_never_auto_verify():
    confidence, _, decision, status = CONFIDENCE_ENGINE.score(
        order_amount=Decimal("500.00"),
        payment_amount=Decimal("300.00"),
        customer_match=True,
        timing_match=True,
        historical_match=False,
        is_duplicate=False,
    )
    assert decision == PaymentDecision.PARTIALLY_PAID
    assert status == PaymentEventStatus.PARTIALLY_PAID
    assert confidence <= CONFIDENCE_ENGINE.MEDIUM


# --------------------------------------------------------------- engine via API


def test_exact_amount_with_customer_phone_marks_order_paid(client, db):
    seller = register_seller(client)
    customer = client.post(
        f"/api/v1/businesses/{seller['business_id']}/customers/",
        json={"name": "Paying Customer", "phone": "01712345678"},
        headers=seller["auth"],
    )
    assert customer.status_code == 201, customer.text
    order = create_order(client, seller, customer_id=customer.json()["id"])
    transaction_id = f"MIG-AUTO-{uuid.uuid4().hex[:10]}"

    response = client.post(
        f"/api/v1/businesses/{seller['business_id']}/payments/intelligence/events/bkash",
        json=_event_payload(
            transaction_id=transaction_id,
            amount=str(order["total_amount"]),
            sender="01712345678",
        ),
        headers=seller["auth"],
    )
    assert response.status_code == 200, response.text
    result = response.json()

    assert result["decision"] == "AUTO_MATCHED"
    assert result["status"] == "PAID"
    assert result["matched_order_id"] == order["id"]
    assert result["duplicate"] is False

    payment = (
        db.query(Payment)
        .filter(
            Payment.business_id == seller["business_id"],
            Payment.transaction_id == transaction_id,
        )
        .first()
    )
    assert payment is not None
    assert payment.status == PaymentStatus.VERIFIED
    assert payment.order_id == order["id"]

    refreshed = client.get(
        f"/api/v1/businesses/{seller['business_id']}/orders/{order['id']}",
        headers=seller["auth"],
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["payment_status"] == "paid"


def test_exact_amount_without_customer_phone_marks_paid_and_records_decision(client, db):
    """Documents consolidated semantics: an exact-amount match marks the order
    paid and the event status is PAID (consistent with the order state), while
    the confidence engine's decision is recorded alongside it (here
    UNKNOWN_TRANSACTION because neither phone nor customer matches).

    This is intentionally asserted so any future behaviour change is visible."""
    seller = register_seller(client)
    order = create_order(client, seller)
    transaction_id = f"MIG-EXACT-{uuid.uuid4().hex[:10]}"

    response = client.post(
        f"/api/v1/businesses/{seller['business_id']}/payments/intelligence/events/bkash",
        json=_event_payload(
            transaction_id=transaction_id,
            amount=str(order["total_amount"]),
        ),
        headers=seller["auth"],
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["matched_order_id"] == order["id"]
    assert result["status"] == "PAID"
    assert result["decision"] in {"UNKNOWN_TRANSACTION", "REQUIRES_REVIEW"}
    assert result["confidence"] < 0.95

    refreshed = client.get(
        f"/api/v1/businesses/{seller['business_id']}/orders/{order['id']}",
        headers=seller["auth"],
    )
    assert refreshed.json()["payment_status"] == "paid"


def test_duplicate_event_is_idempotent_and_creates_no_second_payment(client, db):
    seller = register_seller(client)
    order = create_order(client, seller)
    transaction_id = f"MIG-DUP-{uuid.uuid4().hex[:10]}"
    payload = _event_payload(
        transaction_id=transaction_id, amount=str(order["total_amount"])
    )

    first = client.post(
        f"/api/v1/businesses/{seller['business_id']}/payments/intelligence/events/bkash",
        json=payload,
        headers=seller["auth"],
    )
    assert first.status_code == 200
    assert first.json()["duplicate"] is False

    second = client.post(
        f"/api/v1/businesses/{seller['business_id']}/payments/intelligence/events/bkash",
        json=payload,
        headers=seller["auth"],
    )
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert "DUPLICATE_DETECTED" in second.json()["reason_codes"]

    payments = (
        db.query(Payment)
        .filter(
            Payment.business_id == seller["business_id"],
            Payment.transaction_id == transaction_id,
        )
        .all()
    )
    assert len(payments) == 1


def test_partial_payment_marks_partially_paid_but_not_verified(client, db):
    seller = register_seller(client)
    customer = client.post(
        f"/api/v1/businesses/{seller['business_id']}/customers/",
        json={"name": "Partial Customer", "phone": "01712345678"},
        headers=seller["auth"],
    )
    assert customer.status_code == 201, customer.text
    order = create_order(
        client, seller, unit_price="500.00", customer_id=customer.json()["id"]
    )
    transaction_id = f"MIG-PARTIAL-{uuid.uuid4().hex[:10]}"

    # The candidate is found by matching customer phone; the amount is lower
    # than the order total, so the engine must record a partial settlement.
    response = client.post(
        f"/api/v1/businesses/{seller['business_id']}/payments/intelligence/events/bkash",
        json=_event_payload(
            transaction_id=transaction_id, amount="200.00", sender="01712345678"
        ),
        headers=seller["auth"],
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["decision"] == "PARTIALLY_PAID"

    payment = (
        db.query(Payment)
        .filter(
            Payment.business_id == seller["business_id"],
            Payment.transaction_id == transaction_id,
        )
        .first()
    )
    assert payment is not None
    assert payment.status == PaymentStatus.PENDING

    refreshed = client.get(
        f"/api/v1/businesses/{seller['business_id']}/orders/{order['id']}",
        headers=seller["auth"],
    )
    assert refreshed.json()["payment_status"] == "partially_paid"


def test_overpayment_requires_review_and_never_marks_paid(client, db):
    seller = register_seller(client)
    customer = client.post(
        f"/api/v1/businesses/{seller['business_id']}/customers/",
        json={"name": "Overpaying Customer", "phone": "01712345678"},
        headers=seller["auth"],
    )
    assert customer.status_code == 201, customer.text
    order = create_order(
        client, seller, unit_price="200.00", customer_id=customer.json()["id"]
    )
    transaction_id = f"MIG-OVER-{uuid.uuid4().hex[:10]}"

    # Candidate found via customer phone; amount exceeds the order total.
    response = client.post(
        f"/api/v1/businesses/{seller['business_id']}/payments/intelligence/events/bkash",
        json=_event_payload(
            transaction_id=transaction_id, amount="900.00", sender="01712345678"
        ),
        headers=seller["auth"],
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["decision"] == "REQUIRES_REVIEW"
    assert result["status"] == "OVERPAYMENT"

    payment = (
        db.query(Payment)
        .filter(
            Payment.business_id == seller["business_id"],
            Payment.transaction_id == transaction_id,
        )
        .first()
    )
    assert payment is None

    refreshed = client.get(
        f"/api/v1/businesses/{seller['business_id']}/orders/{order['id']}",
        headers=seller["auth"],
    )
    assert refreshed.json()["payment_status"] == "pending"


def test_unmatched_event_is_stored_for_review(client):
    seller = register_seller(client)
    transaction_id = f"MIG-NOMATCH-{uuid.uuid4().hex[:10]}"
    response = client.post(
        f"/api/v1/businesses/{seller['business_id']}/payments/intelligence/events/bkash",
        json=_event_payload(transaction_id=transaction_id, amount="123.45"),
        headers=seller["auth"],
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["matched_order_id"] is None

    listing = client.get(
        f"/api/v1/businesses/{seller['business_id']}/payments/intelligence/events",
        headers=seller["auth"],
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["total_count"] == 1
    assert body["items"][0]["transaction_id"] == transaction_id


def test_unknown_provider_is_rejected(client):
    seller = register_seller(client)
    response = client.post(
        f"/api/v1/businesses/{seller['business_id']}/payments/intelligence/events/paypal",
        json=_event_payload(transaction_id=f"MIG-BADPROV-{uuid.uuid4().hex[:10]}", amount="10.00"),
        headers=seller["auth"],
    )
    assert response.status_code == 400


# --------------------------------------------------------------- tenant isolation


def test_other_business_cannot_read_or_write_intelligence_data(client):
    seller_a = register_seller(client)
    seller_b = register_seller(client)

    ingest = client.post(
        f"/api/v1/businesses/{seller_a['business_id']}/payments/intelligence/events/bkash",
        json=_event_payload(transaction_id=f"MIG-ISO-{uuid.uuid4().hex[:10]}", amount="55.00"),
        headers=seller_a["auth"],
    )
    assert ingest.status_code == 200

    # B cannot list A's events (membership check fails)
    forbidden = client.get(
        f"/api/v1/businesses/{seller_a['business_id']}/payments/intelligence/events",
        headers=seller_b["auth"],
    )
    assert forbidden.status_code == 403

    # B cannot ingest into A's business either
    forbidden_write = client.post(
        f"/api/v1/businesses/{seller_a['business_id']}/payments/intelligence/events/bkash",
        json=_event_payload(transaction_id=f"MIG-ISO2-{uuid.uuid4().hex[:10]}", amount="55.00"),
        headers=seller_b["auth"],
    )
    assert forbidden_write.status_code == 403

    # B's own summary is empty
    own_summary = client.get(
        f"/api/v1/businesses/{seller_b['business_id']}/payments/intelligence/summary",
        headers=seller_b["auth"],
    )
    assert own_summary.status_code == 200
    assert own_summary.json()["total_events"] == 0


def test_feedback_requires_own_event(client):
    seller_a = register_seller(client)
    seller_b = register_seller(client)

    ingest = client.post(
        f"/api/v1/businesses/{seller_a['business_id']}/payments/intelligence/events/bkash",
        json=_event_payload(transaction_id=f"MIG-FB-{uuid.uuid4().hex[:10]}", amount="77.00"),
        headers=seller_a["auth"],
    )
    event_id = ingest.json()["event_id"]

    response = client.post(
        f"/api/v1/businesses/{seller_b['business_id']}/payments/intelligence/feedback",
        json={
            "payment_event_id": event_id,
            "order_id": 1,
            "from_decision": "REQUIRES_REVIEW",
            "correct_decision": "AUTO_MATCHED",
            "correction_reason": "trying to touch another business's event",
        },
        headers=seller_b["auth"],
    )
    assert response.status_code == 404
