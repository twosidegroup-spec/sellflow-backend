"""Pre-production acceptance audit — business operations.

Pins the server-side behaviour sellers rely on:

* order totals recomputed on the server (deltas included)
* discount bounds (a discount may not push an order total below zero)
* foreign product ids rejected at order creation
* search terms are parameterized (no SQL injection, no 500s) and behave
  predictably for LIKE metacharacters
* pagination boundaries and malformed input handling
* inventory cannot be driven negative through the API
* delivery status validation
* order status transitions (current behaviour is documented explicitly)
"""

from __future__ import annotations

from tests.conftest import create_order, register_seller


def _api(seller: dict, path: str) -> str:
    return f"/api/v1/businesses/{seller['business_id']}{path}"


def _create_product(client, seller, *, price="100.00", cost="40.00", stock=10) -> dict:
    response = client.post(
        _api(seller, "/products/"),
        json={
            "name": "Ops Product",
            "sku": f"OPS-{__import__('uuid').uuid4().hex[:8]}",
            "cost_price": cost,
            "selling_price": price,
            "stock_quantity": stock,
        },
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_product_image_upload_round_trip(client):
    import os
    import re as _re

    from app.products.upload_router import UPLOAD_DIR

    seller = register_seller(client)
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae42"
        "6082"
    )
    upload_dir = f"/api/v1/businesses/{seller['business_id']}/products/upload"
    created = client.post(
        upload_dir,
        data={
            "name": "Photo Product",
            "sku": "PHOTO-1",
            "cost_price": "10.00",
            "selling_price": "20.00",
            "stock_quantity": "1",
        },
        files={"file": ("photo.png", png, "image/png")},
        headers=seller["auth"],
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["image_url"], "the uploaded image was dropped"
    assert body["image_url"].startswith("/uploads/")
    # 128 bits of randomness in the name: not guessable from business id.
    assert _re.search(r"_[0-9a-f]{32}_", body["image_url"]), body["image_url"]

    # The product read returns the same URL and the file is servable.
    read = client.get(
        f"/api/v1/businesses/{seller['business_id']}/products/{body['id']}",
        headers=seller["auth"],
    )
    assert read.json()["image_url"] == body["image_url"]
    assert client.get(body["image_url"]).status_code == 200

    # A second upload never collides with the first.
    second = client.post(
        upload_dir,
        data={
            "name": "Photo Product 2",
            "sku": "PHOTO-2",
            "cost_price": "10.00",
            "selling_price": "20.00",
            "stock_quantity": "1",
        },
        files={"file": ("photo.png", png, "image/png")},
        headers=seller["auth"],
    )
    assert second.status_code == 201
    assert second.json()["image_url"] != body["image_url"]

    # Disallowed content types are rejected before anything is created.
    rejected = client.post(
        upload_dir,
        data={
            "name": "Bad",
            "sku": "PHOTO-3",
            "cost_price": "1.00",
            "selling_price": "1.00",
            "stock_quantity": "0",
        },
        files={"file": ("payload.exe", b"MZ..", "application/x-msdownload")},
        headers=seller["auth"],
    )
    assert rejected.status_code == 400

    # Clean up the two files this test wrote to the shared uploads directory.
    for url in (body["image_url"], second.json()["image_url"]):
        path = os.path.join(UPLOAD_DIR, url.rsplit("/", 1)[-1])
        if os.path.exists(path):
            os.remove(path)


def test_order_totals_are_server_computed(client):
    seller = register_seller(client)
    product = _create_product(client, seller, price="100.00", cost="40.00")
    response = client.post(
        _api(seller, "/orders/"),
        json={
            "items": [
                {
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "quantity": 2,
                    "unit_price": "100.00",
                    "unit_cost": "40.00",
                }
            ],
            "delivery_fee": "60.00",
            "discount": "30.00",
        },
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert float(body["total_amount"]) == 230.00  # 200 + 60 - 30
    assert float(body["total_cost"]) == 80.00
    assert float(body["gross_profit"]) == 90.00  # (200 - 80) - 30


def test_discount_cannot_drive_order_total_negative(client):
    seller = register_seller(client)
    product = _create_product(client, seller, price="100.00")

    response = client.post(
        _api(seller, "/orders/"),
        json={
            "items": [
                {
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "quantity": 1,
                    "unit_price": "100.00",
                    "unit_cost": "40.00",
                }
            ],
            "delivery_fee": "0.00",
            "discount": "5000.00",  # far beyond the order value
        },
        headers=seller["auth"],
    )
    assert response.status_code in (400, 422), response.text
    if response.status_code == 400:
        assert "discount" in response.json()["detail"].lower()

    # The rejected order must not be persisted (no shell row, no items).
    listed = client.get(_api(seller, "/orders/"), headers=seller["auth"]).json()
    assert listed == []


def test_order_rejects_foreign_product_id(client):
    seller_a = register_seller(client)
    seller_b = register_seller(client)
    product_a = _create_product(client, seller_a)

    response = client.post(
        _api(seller_b, "/orders/"),
        json={
            "items": [
                {
                    "product_id": product_a["id"],
                    "product_name": "stolen",
                    "quantity": 1,
                    "unit_price": "1.00",
                    "unit_cost": "0.00",
                }
            ]
        },
        headers=seller_b["auth"],
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_order_item_bounds_are_validated(client):
    seller = register_seller(client)
    bad_items = [
        {"product_name": "x", "quantity": 0, "unit_price": "10.00", "unit_cost": "0.00"},
        {"product_name": "x", "quantity": -2, "unit_price": "10.00", "unit_cost": "0.00"},
        {"product_name": "x", "quantity": 1, "unit_price": "-1.00", "unit_cost": "0.00"},
        {"product_name": "", "quantity": 1, "unit_price": "10.00", "unit_cost": "0.00"},
    ]
    for item in bad_items:
        response = client.post(
            _api(seller, "/orders/"),
            json={"items": [item]},
            headers=seller["auth"],
        )
        assert response.status_code == 422, (item, response.status_code)

    negative_fee = client.post(
        _api(seller, "/orders/"),
        json={
            "items": [{"product_name": "x", "quantity": 1, "unit_price": "10.00", "unit_cost": "0.00"}],
            "delivery_fee": "-5.00",
        },
        headers=seller["auth"],
    )
    assert negative_fee.status_code == 422


def test_search_terms_are_parameterized_and_safe(client):
    seller = register_seller(client)
    customer = client.post(
        _api(seller, "/customers/"),
        json={"name": "Percent Tester"},
        headers=seller["auth"],
    ).json()
    create_order(client, seller, unit_price="100.00", customer_id=customer["id"])

    hostile = [
        "'; DROP TABLE orders; --",
        "100% OR 1=1",
        "\\",
        "_",
        "%",
        "a" * 120,
    ]
    for term in hostile:
        response = client.get(_api(seller, "/orders/"), params={"q": term}, headers=seller["auth"])
        assert response.status_code == 200, (term, response.status_code)
        # The orders table still exists and answers subsequent queries.
    assert client.get(_api(seller, "/orders/"), headers=seller["auth"]).status_code == 200

    # LIKE metacharacters are treated as wildcards (not escaped). They cannot
    # inject SQL; they simply widen the match. Pinned so a change is noticed.
    everything = client.get(_api(seller, "/orders/"), params={"q": "%"}, headers=seller["auth"])
    assert everything.status_code == 200
    assert len(everything.json()) == 1


def test_pagination_boundaries(client):
    seller = register_seller(client)
    for index in range(3):
        create_order(client, seller, unit_price=f"{10 * (index + 1)}.00")

    ok_min = client.get(
        _api(seller, "/orders/"), params={"limit": 1, "sort": "oldest"}, headers=seller["auth"]
    )
    assert ok_min.status_code == 200 and len(ok_min.json()) == 1

    ok_max = client.get(
        _api(seller, "/orders/"), params={"limit": 200}, headers=seller["auth"]
    )
    assert ok_max.status_code == 200 and len(ok_max.json()) == 3

    for params in ({"limit": 0}, {"limit": 201}, {"offset": -1}, {"sort": "newest; DROP"}):
        response = client.get(_api(seller, "/orders/"), params=params, headers=seller["auth"])
        assert response.status_code == 422, (params, response.status_code)

    beyond = client.get(
        _api(seller, "/orders/"), params={"offset": 10000}, headers=seller["auth"]
    )
    assert beyond.status_code == 200 and beyond.json() == []


def test_inventory_cannot_go_negative(client):
    seller = register_seller(client)
    product = _create_product(client, seller, stock=5)

    response = client.put(
        _api(seller, f"/products/{product['id']}"),
        json={"stock_quantity": -1},
        headers=seller["auth"],
    )
    assert response.status_code == 422

    # Stock is seller-maintained: creating an order does not decrement it.
    # Pinned so an inventory-automation change is a deliberate, tested change.
    create_order(client, seller, unit_price="100.00")
    refreshed = client.get(
        _api(seller, f"/products/{product['id']}"), headers=seller["auth"]
    ).json()
    assert refreshed["stock_quantity"] == 5


def test_delivery_status_is_validated(client):
    seller = register_seller(client)
    order = create_order(client, seller)
    client.post(
        _api(seller, f"/orders/{order['id']}/delivery/"),
        json={"courier": "Pathao", "tracking_number": "T-1", "delivery_fee": "60.00"},
        headers=seller["auth"],
    )
    response = client.patch(
        _api(seller, f"/orders/{order['id']}/delivery/"),
        json={"status": "teleported"},
        headers=seller["auth"],
    )
    assert response.status_code == 422

    duplicate = client.post(
        _api(seller, f"/orders/{order['id']}/delivery/"),
        json={"courier": "X", "tracking_number": "T-2", "delivery_fee": "0.00"},
        headers=seller["auth"],
    )
    assert duplicate.status_code == 400  # one delivery per order


def test_order_status_transitions_are_currently_unrestricted(client):
    """Documents current behaviour (any status -> any status).

    There is no transition matrix: a delivered order can be set back to
    `created`. Sellers occasionally need to correct mistakes, so this is a
    product decision; it is pinned here so an accidental change is visible and
    so the audit report can flag it as a pending product decision.
    """
    seller = register_seller(client)
    order = create_order(client, seller)

    for status in ("delivered", "created", "cancelled"):
        response = client.patch(
            _api(seller, f"/orders/{order['id']}/status"),
            json={"status": status},
            headers=seller["auth"],
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status

    invalid = client.patch(
        _api(seller, f"/orders/{order['id']}/status"),
        json={"status": "shipped_out"},
        headers=seller["auth"],
    )
    assert invalid.status_code == 422


def test_cancelled_orders_excluded_from_revenue_and_daily_series(client):
    seller = register_seller(client)
    kept = create_order(client, seller, unit_price="100.00")
    cancelled = create_order(client, seller, unit_price="50.00")
    client.patch(
        _api(seller, f"/orders/{cancelled['id']}/status"),
        json={"status": "cancelled"},
        headers=seller["auth"],
    )

    summary = client.get(_api(seller, "/analytics/summary"), headers=seller["auth"]).json()
    assert float(summary["total_revenue"]) == 100.00  # cancelled 50 excluded
    assert summary["orders_by_status"]["cancelled"] == 1
    assert summary["total_orders"] == 2  # still counted in the pipeline

    daily_today = summary["daily"][-1]
    assert float(daily_today["revenue"]) == 100.00
