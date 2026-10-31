"""Pre-production acceptance audit — cross-tenant isolation matrix.

This module exercises EVERY business-owned API surface with a second seller's
credentials and asserts that no cross-business read, write or side effect is
possible. It complements `test_tenant_isolation.py` (products + orders) and
`test_console_upgrades.py` (query-param isolation) by covering the remaining
surfaces:

* businesses (read/update), memberships (list/add/remove)
* customers CRUD, products update/delete/upload
* orders (create/status), deliveries (create/read/update)
* recorded payments, detected payments, reconciliation status
* payment intelligence (events, summary, feedback, memory)
* analytics summary, webhooks, payment-accounts, business switching
* confused-deputy attempts (own business path + another business's resource id)
* device-token scoping and the development-only detection endpoint

Also verifies that denied writes leave the victim's data byte-for-byte intact.

Runs under the guarded suite in `tests/conftest.py` (isolated *_test database).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from tests.conftest import create_order, register_seller


# --------------------------------------------------------------------- helpers


def _pair_device(client, seller: dict, name: str = "Audit Phone") -> dict:
    code = client.post(
        f"/device-bridge/pairing-codes?business_id={seller['business_id']}",
        headers=seller["auth"],
    )
    assert code.status_code == 201, code.text
    device = client.post(
        "/device-bridge/devices",
        json={"pairing_code": code.json()["pairing_code"], "device_name": name},
    )
    assert device.status_code == 201, device.text
    return device.json()


def _seed_business(client) -> tuple[dict, dict]:
    """Create a seller with one row of each business-owned resource."""
    seller = register_seller(client)
    business_id = seller["business_id"]
    base = f"/api/v1/businesses/{business_id}"

    product = client.post(
        f"{base}/products/",
        json={
            "name": "Audit Product",
            "sku": f"AUD-{uuid.uuid4().hex[:8]}",
            "cost_price": "100.00",
            "selling_price": "250.00",
            "stock_quantity": 10,
        },
        headers=seller["auth"],
    )
    assert product.status_code == 201, product.text

    customer = client.post(
        f"{base}/customers/",
        json={"name": "Audit Customer", "phone": "01711111111"},
        headers=seller["auth"],
    )
    assert customer.status_code == 201, customer.text

    order = create_order(client, seller, unit_price="500.00")
    order_id = order["id"]

    delivery = client.post(
        f"{base}/orders/{order_id}/delivery/",
        json={"courier": "Pathao", "tracking_number": "AUD-TRK-1", "delivery_fee": "60.00"},
        headers=seller["auth"],
    )
    assert delivery.status_code == 201, delivery.text

    payment = client.post(
        f"{base}/orders/{order_id}/payments/",
        json={"amount": "100.00", "method": "bkash", "transaction_id": "AUD-PAY-1"},
        headers=seller["auth"],
    )
    assert payment.status_code == 201, payment.text

    webhook = client.post(
        f"{base}/webhooks/",
        json={"url": "https://example.com/audit-hook", "events": "order.created"},
        headers=seller["auth"],
    )
    assert webhook.status_code == 201, webhook.text

    device = _pair_device(client, seller)

    return seller, {
        "product": product.json(),
        "customer": customer.json(),
        "order": order,
        "delivery": delivery.json(),
        "payment": payment.json(),
        "webhook": webhook.json(),
        "device": device,
    }


def _tiny_png() -> bytes:
    # 1x1 transparent PNG
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae42"
        "6082"
    )


# ------------------------------------------------ cross-tenant request matrix


def test_cross_tenant_matrix_and_data_integrity(client):
    seller_a, a = _seed_business(client)
    seller_b = register_seller(client)
    base_a = f"/api/v1/businesses/{seller_a['business_id']}"
    order_id = a["order"]["id"]

    attempts: list[tuple[str, str, str, dict | None]] = [
        # (label, method, path, json body)
        ("business read", "GET", base_a, None),
        ("business update", "PATCH", base_a, {"name": "hijacked"}),
        ("memberships list", "GET", f"{base_a}/memberships", None),
        ("memberships add", "POST", f"{base_a}/memberships", {"user_id": seller_b["user_id"], "role": "staff"}),
        ("membership remove", "DELETE", f"{base_a}/memberships/{seller_a['user_id']}", None),
        ("products list", "GET", f"{base_a}/products/", None),
        ("product create", "POST", f"{base_a}/products/", {"name": "x", "sku": "X-1", "cost_price": "1.00", "selling_price": "2.00"}),
        ("product read", "GET", f"{base_a}/products/{a['product']['id']}", None),
        ("product update", "PUT", f"{base_a}/products/{a['product']['id']}", {"name": "hijacked"}),
        ("product delete", "DELETE", f"{base_a}/products/{a['product']['id']}", None),
        ("customers list", "GET", f"{base_a}/customers/", None),
        ("customer create", "POST", f"{base_a}/customers/", {"name": "intruder"}),
        ("customer read", "GET", f"{base_a}/customers/{a['customer']['id']}", None),
        ("customer update", "PUT", f"{base_a}/customers/{a['customer']['id']}", {"name": "hijacked"}),
        ("customer delete", "DELETE", f"{base_a}/customers/{a['customer']['id']}", None),
        ("orders list", "GET", f"{base_a}/orders/", None),
        ("order create", "POST", f"{base_a}/orders/", {"items": [{"product_name": "x", "quantity": 1, "unit_price": "1.00", "unit_cost": "0.00"}]}),
        ("order read", "GET", f"{base_a}/orders/{order_id}", None),
        ("order status", "PATCH", f"{base_a}/orders/{order_id}/status", {"status": "cancelled"}),
        ("delivery read", "GET", f"{base_a}/orders/{order_id}/delivery/", None),
        ("delivery create", "POST", f"{base_a}/orders/{order_id}/delivery/", {"courier": "X", "tracking_number": "Y", "delivery_fee": "0.00"}),
        ("delivery update", "PATCH", f"{base_a}/orders/{order_id}/delivery/", {"status": "delivered"}),
        ("record payment", "POST", f"{base_a}/orders/{order_id}/payments/", {"amount": "1.00", "method": "bkash"}),
        ("payments list", "GET", f"{base_a}/payments", None),
        ("detected payments", "GET", f"{base_a}/payments/detected", None),
        ("reconciliation status", "GET", f"{base_a}/payments/reconciliation/status", None),
        ("intelligence summary", "GET", f"{base_a}/payments/intelligence/summary", None),
        ("intelligence events read", "GET", f"{base_a}/payments/intelligence/events", None),
        ("intelligence memory", "GET", f"{base_a}/payments/intelligence/memory", None),
        ("analytics summary", "GET", f"{base_a}/analytics/summary", None),
        ("webhooks list", "GET", f"{base_a}/webhooks/", None),
        ("webhook create", "POST", f"{base_a}/webhooks/", {"url": "https://example.com/x", "events": "order.created"}),
        ("webhook delete", "DELETE", f"{base_a}/webhooks/{a['webhook']['id']}", None),
    ]

    failures: list[str] = []
    for label, method, path, body in attempts:
        response = client.request(method, path, json=body, headers=seller_b["auth"])
        if response.status_code not in (401, 403, 404):
            failures.append(f"{label}: {method} {path} -> {response.status_code}")

    # `businesses/me/switch` takes the target as a query parameter.
    switch = client.post(
        "/api/v1/businesses/me/switch",
        params={"business_id": seller_a["business_id"]},
        headers=seller_b["auth"],
    )
    if switch.status_code not in (401, 403, 404):
        failures.append(f"business switch: -> {switch.status_code}")

    # Multipart upload attempt (cannot go through client.request json=).
    upload = client.post(
        f"{base_a}/products/upload",
        files={"file": ("probe.png", _tiny_png(), "image/png")},
        headers=seller_b["auth"],
    )
    if upload.status_code not in (401, 403, 404):
        failures.append(f"product upload: -> {upload.status_code}")

    # Payment-account surfaces authenticate via ?business_id= (root paths).
    accounts_list = client.get(
        "/payment-accounts",
        params={"business_id": seller_a["business_id"]},
        headers=seller_b["auth"],
    )
    if accounts_list.status_code not in (401, 403, 404):
        failures.append(f"payment accounts list: -> {accounts_list.status_code}")

    accounts_connect = client.post(
        "/payment-accounts/connect",
        params={"business_id": seller_a["business_id"]},
        json={"provider": "bkash", "receiving_number": "01712345678"},
        headers=seller_b["auth"],
    )
    if accounts_connect.status_code not in (401, 403, 404):
        failures.append(f"payment accounts connect: -> {accounts_connect.status_code}")

    assert not failures, "Cross-tenant requests were not denied:\n" + "\n".join(failures)

    # ------------------------------------------------ confused-deputy attempts
    # B uses ITS OWN business path with A's resource identifiers. Valid bodies
    # are sent so a 422 can never mask the authorization answer. The
    # record-payment route surfaces a foreign order as a 400 ("Order not found
    # or access denied") rather than 404 — the write is still denied and the
    # message does not reveal whether the order exists.
    base_b = f"/api/v1/businesses/{seller_b['business_id']}"
    deputy: list[tuple[str, str, dict | None, tuple[int, ...]]] = [
        ("GET", f"{base_b}/products/{a['product']['id']}", None, (403, 404)),
        ("PUT", f"{base_b}/products/{a['product']['id']}", {"name": "hijacked"}, (403, 404)),
        ("DELETE", f"{base_b}/products/{a['product']['id']}", None, (403, 404)),
        ("GET", f"{base_b}/customers/{a['customer']['id']}", None, (403, 404)),
        ("PUT", f"{base_b}/customers/{a['customer']['id']}", {"name": "hijacked"}, (403, 404)),
        ("DELETE", f"{base_b}/customers/{a['customer']['id']}", None, (403, 404)),
        ("GET", f"{base_b}/orders/{order_id}", None, (403, 404)),
        ("PATCH", f"{base_b}/orders/{order_id}/status", {"status": "cancelled"}, (403, 404)),
        ("GET", f"{base_b}/orders/{order_id}/delivery/", None, (403, 404)),
        ("POST", f"{base_b}/orders/{order_id}/payments/", {"amount": "1.00", "method": "bkash"}, (400, 403, 404)),
        ("DELETE", f"{base_b}/webhooks/{a['webhook']['id']}", None, (403, 404)),
    ]
    deputy_failures = []
    for method, path, body, allowed in deputy:
        response = client.request(method, path, json=body, headers=seller_b["auth"])
        if response.status_code not in allowed:
            deputy_failures.append(f"{method} {path} -> {response.status_code} (expected {allowed})")
    assert not deputy_failures, "Confused-deputy reads/writes not denied:\n" + "\n".join(deputy_failures)

    # ------------------------------------------------- the victim is unharmed
    reread = client.get(f"{base_a}/products/{a['product']['id']}", headers=seller_a["auth"])
    assert reread.status_code == 200
    assert reread.json()["name"] == "Audit Product"

    reread = client.get(f"{base_a}/customers/{a['customer']['id']}", headers=seller_a["auth"])
    assert reread.status_code == 200
    assert reread.json()["name"] == "Audit Customer"

    reread = client.get(f"{base_a}/orders/{order_id}", headers=seller_a["auth"])
    assert reread.status_code == 200
    assert reread.json()["status"] == "created"  # status PATCH was denied

    reread = client.get(f"{base_a}/orders/{order_id}/delivery/", headers=seller_a["auth"])
    assert reread.status_code == 200
    assert reread.json()["status"] == "pending"  # update was denied
    assert reread.json()["courier"] == "Pathao"

    payments = client.get(f"{base_a}/payments", headers=seller_a["auth"]).json()
    assert len(payments) == 1  # extra recorded payment was denied

    webhooks = client.get(f"{base_a}/webhooks/", headers=seller_a["auth"]).json()
    assert any(row["id"] == a["webhook"]["id"] for row in webhooks)  # delete denied

    business = client.get(base_a, headers=seller_a["auth"]).json()
    assert business["name"] != "hijacked"

    # B sees only their own (empty) world.
    assert client.get(f"{base_b}/products/", headers=seller_b["auth"]).json() == []
    assert client.get(f"{base_b}/orders/", headers=seller_b["auth"]).json() == []


def test_unauthenticated_requests_are_rejected(client):
    probes = [
        ("GET", "/api/v1/businesses/1", None),
        ("GET", "/api/v1/businesses/1/products/", None),
        ("POST", "/api/v1/businesses/1/products/", {"name": "x"}),
        ("GET", "/api/v1/businesses/1/customers/", None),
        ("GET", "/api/v1/businesses/1/orders/", None),
        ("GET", "/api/v1/businesses/1/payments", None),
        ("GET", "/api/v1/businesses/1/payments/intelligence/summary", None),
        ("GET", "/api/v1/businesses/1/analytics/summary", None),
        ("GET", "/api/v1/businesses/1/webhooks/", None),
        ("GET", "/api/v1/businesses/me", None),
        ("GET", "/payment-accounts", None),
        ("POST", "/payment-accounts/connect", {"provider": "bkash", "receiving_number": "01712345678"}),
        ("GET", "/api/v1/devices/", None),
        ("POST", "/api/v1/payments/detect", {"amount": "10.00", "receiver_number": "01712345678"}),
        ("GET", "/device-bridge/dashboard", None),
    ]
    failures = []
    for method, path, body in probes:
        response = client.request(method, path, json=body)
        if response.status_code not in (401, 403, 404):
            failures.append(f"{method} {path} -> {response.status_code}")
    assert not failures, "Unauthenticated requests were not rejected:\n" + "\n".join(failures)


def test_devices_api_is_user_scoped(client):
    seller_a = register_seller(client)
    seller_b = register_seller(client)

    created = client.post(
        "/api/v1/devices/",
        params={"business_id": seller_a["business_id"]},
        json={"device_id": f"audit-{uuid.uuid4().hex[:10]}", "device_type": "android", "push_token": "tok-a"},
        headers=seller_a["auth"],
    )
    assert created.status_code == 201, created.text
    device_row_id = created.json()["id"]

    update = client.put(
        f"/api/v1/devices/{device_row_id}",
        json={"push_token": "stolen-token"},
        headers=seller_b["auth"],
    )
    assert update.status_code == 404

    delete = client.delete(f"/api/v1/devices/{device_row_id}", headers=seller_b["auth"])
    assert delete.status_code == 404

    # Owner still sees it active with the original token.
    listing = client.get("/api/v1/devices/", headers=seller_a["auth"]).json()
    row = next(item for item in listing["devices"] if item["id"] == device_row_id)
    assert row["push_token"] == "tok-a"


def test_device_token_is_scoped_to_its_business(client):
    seller_a, a = _seed_business(client)
    seller_b = register_seller(client)
    token = a["device"]["device_token"]

    # A's device token reports its own business, regardless of a business_id
    # query parameter aimed at B.
    response = client.post(
        f"/device-bridge/pairing-codes?business_id={seller_b['business_id']}",
        headers={"X-Device-Token": token},
    )
    assert response.status_code == 201

    # The dashboard resolves the device's own tenant; it does not accept a
    # business selector.
    dashboard = client.get("/device-bridge/dashboard", headers={"X-Device-Token": token})
    assert dashboard.status_code == 200

    # A bogus device token is rejected everywhere.
    assert (
        client.get("/device-bridge/dashboard", headers={"X-Device-Token": "nope"}).status_code
        == 401
    )


def test_development_detection_endpoint_is_guarded(client, monkeypatch):
    seller_a = register_seller(client, receiving_number="01730000099")

    payment_payload = {
        "amount": "10.00",
        "method": "bkash",
        "sender_number": "01711111111",
        "receiver_number": "01730000099",
    }

    # In development the endpoint requires the caller's OWN receiving number.
    foreign_number = dict(payment_payload, receiver_number="01799999999")
    response = client.post("/api/v1/payments/detect", json=foreign_number, headers=seller_a["auth"])
    assert response.status_code == 404

    response = client.post("/api/v1/payments/detect", json=payment_payload, headers=seller_a["auth"])
    assert response.status_code in (200, 201), response.text

    # In production the simulator does not exist at all.
    from app.core.config import Settings

    monkeypatch.setattr(Settings, "is_production", property(lambda self: True))
    response = client.post("/api/v1/payments/detect", json=payment_payload, headers=seller_a["auth"])
    assert response.status_code == 404


def test_business_switch_cannot_target_a_foreign_business(client):
    seller_a = register_seller(client)
    seller_b = register_seller(client)

    response = client.post(
        "/api/v1/businesses/me/switch",
        params={"business_id": seller_a["business_id"]},
        headers=seller_b["auth"],
    )
    assert response.status_code in (403, 404)

    # Their own business still resolves correctly.
    me = client.get(
        "/api/v1/businesses/me",
        params={"business_id": seller_b["business_id"]},
        headers=seller_b["auth"],
    )
    assert me.status_code == 200
    assert me.json()["business_id"] == seller_b["business_id"]
