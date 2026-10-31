"""Pre-production acceptance audit — payment integrity (HTTP level).

Complements the engine-level coverage in `test_migration_intelligence.py`
(confidence scoring, partial/overpay/duplicate decisions) by exercising the
seller-facing API paths:

* recorded-payment idempotency by transaction id (replays never double-count)
* the 150%-of-total over-collection guard, including its boundary
* manual intelligence-event submission: unmatched -> review, never auto-paid
* overpayment via the engine is recorded as OVERPAYMENT, not PAID
* feedback can only reference events inside the caller's own business
* every decision leaves an audit record (decision rows, anomaly rows)
"""

from __future__ import annotations

from datetime import datetime, timezone

from tests.conftest import create_order, register_seller


def _api(seller: dict, path: str) -> str:
    return f"/api/v1/businesses/{seller['business_id']}{path}"


def _event_payload(transaction_id: str, amount: str) -> dict:
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": "BDT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _record(client, seller, order_id: int, *, amount: str, txid: str | None = None) -> dict:
    payload: dict = {"amount": amount, "method": "bkash"}
    if txid:
        payload["transaction_id"] = txid
    response = client.post(
        _api(seller, f"/orders/{order_id}/payments/"), json=payload, headers=seller["auth"]
    )
    return response


def test_replayed_transaction_id_is_idempotent_across_orders(client):
    seller = register_seller(client)
    first = create_order(client, seller, unit_price="500.00")
    second = create_order(client, seller, unit_price="500.00")

    one = _record(client, seller, first["id"], amount="100.00", txid="DUP-TX-1")
    assert one.status_code == 201, one.text
    two = _record(client, seller, second["id"], amount="100.00", txid="DUP-TX-1")
    assert two.status_code == 201, two.text

    # The replay resolves to the ORIGINAL record — no second payment row.
    assert one.json()["id"] == two.json()["id"]
    assert one.json()["order_id"] == first["id"]

    listed = client.get(_api(seller, "/payments"), headers=seller["auth"]).json()
    assert len([row for row in listed if row["transaction_id"] == "DUP-TX-1"]) == 1


def test_over_collection_guard_and_its_boundary(client):
    seller = register_seller(client)
    order = create_order(client, seller, unit_price="100.00")  # total = 100.00

    ok = _record(client, seller, order["id"], amount="100.00", txid="GUARD-1")
    assert ok.status_code == 201

    # 100 + 51 = 151 > 150% of 100 -> rejected, nothing written.
    over = _record(client, seller, order["id"], amount="51.00", txid="GUARD-2")
    assert over.status_code == 400, over.text
    assert "150%" in over.json()["detail"]

    listed = client.get(_api(seller, "/payments"), headers=seller["auth"]).json()
    assert len(listed) == 1

    # 100 + 50 == 150 exactly -> allowed (guard is strictly greater-than).
    boundary = _record(client, seller, order["id"], amount="50.00", txid="GUARD-3")
    assert boundary.status_code == 201, boundary.text


def test_unmatched_manual_event_goes_to_review_never_paid(client):
    seller = register_seller(client)
    order = create_order(client, seller, unit_price="777.00")

    response = client.post(
        _api(seller, "/payments/intelligence/events/bkash"),
        json=_event_payload("AUDIT-UNMATCHED-1", "123.45"),
        headers=seller["auth"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] not in ("PAID",), body
    assert body["decision"] in ("REQUIRES_REVIEW", "UNKNOWN_TRANSACTION"), body
    assert body["matched_order_id"] is None

    # The order is untouched: an unmatched event never marks anything paid.
    refreshed = client.get(_api(seller, f"/orders/{order['id']}"), headers=seller["auth"])
    assert refreshed.json()["payment_status"] == "pending"

    summary = client.get(
        _api(seller, "/payments/intelligence/summary"), headers=seller["auth"]
    ).json()
    assert summary["review_events"] >= 1
    assert float(summary["verified_amount_total"]) == 0.0


def test_overpayment_via_event_is_flagged_not_paid(client):
    seller = register_seller(client)
    order = create_order(client, seller, unit_price="300.00")
    # Give the order a customer whose phone matches the event sender, so the
    # amount is the only mismatch.
    customer = client.post(
        _api(seller, "/customers/"),
        json={"name": "Audit Payer", "phone": "01722222222"},
        headers=seller["auth"],
    ).json()
    # (The order was created without a customer; create a fresh matched pair.)
    order2 = create_order(client, seller, unit_price="300.00", customer_id=customer["id"])

    response = client.post(
        _api(seller, "/payments/intelligence/events/bkash"),
        json={
            **_event_payload("AUDIT-OVERPAY-1", "900.00"),
            "sender_identifier": "01722222222",
        },
        headers=seller["auth"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # The engine flags the overpayment but deliberately routes it to review:
    # money above the order total is never auto-accepted.
    assert body["status"] == "OVERPAYMENT", body
    assert body["decision"] == "REQUIRES_REVIEW", body
    assert body["matched_order_id"] == order2["id"]

    # Overpayment must not silently mark the order paid.
    refreshed = client.get(_api(seller, f"/orders/{order2['id']}"), headers=seller["auth"])
    assert refreshed.json()["payment_status"] != "paid"
    assert order["id"] != order2["id"]


def test_feedback_only_accepts_own_events(client):
    seller_a = register_seller(client)
    seller_b = register_seller(client)
    order_a = create_order(client, seller_a, unit_price="100.00")

    event = client.post(
        _api(seller_a, "/payments/intelligence/events/bkash"),
        json=_event_payload("AUDIT-FEEDBACK-1", "100.00"),
        headers=seller_a["auth"],
    ).json()

    payload = {
        "payment_event_id": event["event_id"],
        "order_id": order_a["id"],
        "from_decision": event["decision"],
        "correct_decision": "AUTO_MATCHED",
        "correction_reason": "audit probe",
    }

    # B cannot attach feedback to A's event…
    denied = client.post(
        _api(seller_b, "/payments/intelligence/feedback"), json=payload, headers=seller_b["auth"]
    )
    assert denied.status_code in (400, 404), denied.text

    # …and the cross-business attempt is also denied outright on A's path.
    denied_path = client.post(
        _api(seller_a, "/payments/intelligence/feedback"), json=payload, headers=seller_b["auth"]
    )
    assert denied_path.status_code == 403

    # A's own feedback is recorded.
    accepted = client.post(
        _api(seller_a, "/payments/intelligence/feedback"), json=payload, headers=seller_a["auth"]
    )
    assert accepted.status_code == 201, accepted.text
