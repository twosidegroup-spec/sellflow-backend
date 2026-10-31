"""Regression tests for the migrated device bridge (Kotlin Payment Bridge API).

These verify the exact contract the Android bridge app uses:

* `POST /device-bridge/pairing-codes` -> pairing_code + expires_in_seconds=60
* `POST /device-bridge/devices`      -> device_id + device_token + status
* `POST /device-bridge/status`       -> sms_permission_granted/monitoring_active
* `POST /device-bridge/events`       -> 202 accepted / 200 duplicate
* `GET  /device-bridge/dashboard`    -> metrics/system/items JSON keys that
  `DashboardModels.kt` parses
* `POST /payment-accounts/connect`   -> connects the receiving number

Cross-business isolation and credential requirements are asserted throughout.
"""

from __future__ import annotations

import uuid

from datetime import datetime, timezone

from tests.conftest import create_order, register_seller


def _event_payload(transaction_id: str, amount: str, sender: str | None = "01700000017") -> dict:
    return {
        "provider": "bkash",
        "amount": amount,
        "transaction_id": transaction_id,
        "sender_identifier": sender,
        "receiver_identifier": "01700000000",
        "currency": "BDT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "android_sms",
        "notification_package": "com.bkash.android",
    }


def _pair_device(client, seller: dict, name: str = "Test Phone") -> dict:
    code = client.post(
        f"/device-bridge/pairing-codes?business_id={seller['business_id']}",
        headers=seller["auth"],
    )
    assert code.status_code == 201, code.text
    assert code.json()["expires_in_seconds"] == 60

    device = client.post(
        "/device-bridge/devices",
        json={"pairing_code": code.json()["pairing_code"], "device_name": name},
    )
    assert device.status_code == 201, device.text
    body = device.json()
    assert body["business_id"] == seller["business_id"]
    assert body["status"] == "paired"
    assert body["device_token"]
    return body


def test_pairing_contract_matches_kotlin_bridge(client):
    seller = register_seller(client)
    code = client.post(
        f"/device-bridge/pairing-codes?business_id={seller['business_id']}",
        headers=seller["auth"],
    )
    assert code.status_code == 201
    payload = code.json()
    # Keys the Kotlin BridgeApiTest asserts:
    assert isinstance(payload["pairing_code"], str) and payload["pairing_code"]
    assert payload["expires_in_seconds"] == 60
    assert payload["expires_at"]

    device = client.post(
        "/device-bridge/devices",
        json={"pairing_code": payload["pairing_code"], "device_name": "Seller Phone"},
    )
    assert device.status_code == 201
    body = device.json()
    assert body["device_id"]
    assert body["device_token"]
    assert body["status"] == "paired"
    assert body["device_name"] == "Seller Phone"


def test_pairing_code_is_single_use_and_wrong_codes_are_404(client):
    seller = register_seller(client)
    code = client.post(
        f"/device-bridge/pairing-codes?business_id={seller['business_id']}",
        headers=seller["auth"],
    ).json()["pairing_code"]

    first = client.post(
        "/device-bridge/devices",
        json={"pairing_code": code, "device_name": "First"},
    )
    assert first.status_code == 201

    second = client.post(
        "/device-bridge/devices",
        json={"pairing_code": code, "device_name": "Second"},
    )
    assert second.status_code == 404

    bogus = client.post(
        "/device-bridge/devices",
        json={"pairing_code": "not-a-real-code", "device_name": "Bogus"},
    )
    assert bogus.status_code == 404


def test_pairing_codes_require_authentication(client):
    response = client.post("/device-bridge/pairing-codes")
    assert response.status_code == 401


def test_device_event_flow_matches_order_and_is_idempotent(client):
    seller = register_seller(client)
    order = create_order(client, seller, unit_price="250.00")
    device = _pair_device(client, seller)
    headers = {"X-Device-Token": device["device_token"]}

    status_response = client.post(
        "/device-bridge/status",
        json={"sms_permission_granted": True, "monitoring_active": True},
        headers=headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()["sms_permission_granted"] is True

    transaction_id = f"BRIDGE-{uuid.uuid4().hex[:10]}"
    first = client.post(
        "/device-bridge/events",
        json=_event_payload(transaction_id, str(order["total_amount"])),
        headers=headers,
    )
    assert first.status_code == 202, first.text
    body = first.json()
    assert body["status"] == "accepted"
    assert body["matched_order_id"] == order["id"]

    duplicate = client.post(
        "/device-bridge/events",
        json=_event_payload(transaction_id, str(order["total_amount"])),
        headers=headers,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "duplicate"


def test_device_events_require_a_device_token(client):
    response = client.post(
        "/device-bridge/events",
        json=_event_payload("BRIDGE-TXN-ANON", "10.00"),
    )
    assert response.status_code == 401


def test_invalid_device_token_is_rejected(client):
    response = client.post(
        "/device-bridge/events",
        json=_event_payload("BRIDGE-TXN-BADTOKEN", "10.00"),
        headers={"X-Device-Token": "definitely-not-a-token"},
    )
    assert response.status_code == 401


def test_payment_account_connect_and_dashboard_contract(client):
    seller = register_seller(client)
    order = create_order(client, seller, unit_price="120.00")
    device = _pair_device(client, seller)
    headers = {"X-Device-Token": device["device_token"]}

    connect = client.post(
        "/payment-accounts/connect",
        json={"provider": "bkash", "receiving_number": "01700000000"},
        headers=headers,
    )
    assert connect.status_code == 200, connect.text
    assert connect.json()["provider"] == "bkash"
    assert connect.json()["receiving_number"] == "8801700000000"

    client.post(
        "/device-bridge/events",
        json=_event_payload(f"BRIDGE-DASH-{uuid.uuid4().hex[:10]}", str(order["total_amount"])),
        headers=headers,
    )

    dashboard = client.get("/device-bridge/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()

    # Keys parsed by DashboardModels.kt:
    assert set(body.keys()) >= {"metrics", "system", "items", "total_count", "limit", "offset", "has_more"}
    assert set(body["metrics"].keys()) >= {
        "today_verified_amount",
        "month_verified_amount",
        "today_verified_transactions",
        "latest_verified_amount",
        "latest_verified_at",
    }
    assert set(body["system"].keys()) >= {
        "device_name",
        "device_paired",
        "sms_permission_granted",
        "monitoring_active",
        "account_provider",
        "receiving_number_masked",
        "last_accepted_event_at",
        "last_verified_payment_at",
        "last_verified_processed_at",
        "recent_unverified_events",
    }
    assert body["system"]["device_paired"] is True
    assert body["system"]["account_provider"] == "bkash"
    assert body["system"]["receiving_number_masked"] == "****0000"
    assert body["metrics"]["latest_verified_amount"] == "120.00"
    assert body["total_count"] == 1
    item = body["items"][0]
    assert set(item.keys()) >= {
        "event_id",
        "provider",
        "transaction_id",
        "amount",
        "currency",
        "event_timestamp",
        "status",
        "verification_status",
        "decision",
        "order_id",
    }
    assert item["verification_status"] == "verified"


def test_device_dashboard_is_scoped_to_the_device_business(client):
    seller_a = register_seller(client)
    seller_b = register_seller(client)

    order_a = create_order(client, seller_a, unit_price="80.00")
    device_a = _pair_device(client, seller_a, "Phone A")
    device_b = _pair_device(client, seller_b, "Phone B")

    client.post(
        "/device-bridge/events",
        json=_event_payload(f"BRIDGE-ISO-{uuid.uuid4().hex[:10]}", str(order_a["total_amount"])),
        headers={"X-Device-Token": device_a["device_token"]},
    )

    dashboard_b = client.get(
        "/device-bridge/dashboard",
        headers={"X-Device-Token": device_b["device_token"]},
    )
    assert dashboard_b.status_code == 200
    assert dashboard_b.json()["total_count"] == 0


def test_devices_list_requires_auth_and_lists_own_devices(client):
    seller = register_seller(client)
    _pair_device(client, seller, "Listed Phone")

    anonymous = client.get("/device-bridge/devices")
    assert anonymous.status_code == 401

    listing = client.get(
        f"/device-bridge/devices?business_id={seller['business_id']}",
        headers=seller["auth"],
    )
    assert listing.status_code == 200
    names = [device["device_name"] for device in listing.json()]
    assert "Listed Phone" in names


def test_payment_account_connect_requires_auth(client):
    response = client.post(
        "/payment-accounts/connect",
        json={"provider": "bkash", "receiving_number": "01700000000"},
    )
    assert response.status_code == 401
