"""Regression suite — approved Inventory Option C (stock warnings).

Approved behaviour (staging brief):

* the API returns a `warnings` field on order creation;
* a warning is produced when the requested quantity exceeds the product's
  current stock — **including zero stock**;
* warnings never reject the order;
* the server records the warnings in `orders.system_notes` (never in the
  seller-editable `notes`);
* sufficient stock produces no warnings and no system notes.
"""

from __future__ import annotations

import uuid

from tests.conftest import register_seller


def _api(seller: dict, path: str) -> str:
    return f"/api/v1/businesses/{seller['business_id']}{path}"


def _create_product(client, seller, *, name: str = "Stock Product", stock: int = 10, price: str = "100.00") -> dict:
    response = client.post(
        _api(seller, "/products/"),
        json={
            "name": name,
            "sku": f"STK-{uuid.uuid4().hex[:8]}",
            "cost_price": "40.00",
            "selling_price": price,
            "stock_quantity": stock,
        },
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    return response.json()


def _order_payload(items: list[dict], *, notes: str | None = None) -> dict:
    payload = {"items": items}
    if notes is not None:
        payload["notes"] = notes
    return payload


def _item(product: dict, quantity: int, unit_price: str = "100.00") -> dict:
    return {
        "product_id": product["id"],
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": unit_price,
        "unit_cost": "40.00",
    }


def test_multiple_products_warned_and_system_notes_recorded(client):
    seller = register_seller(client)
    almost_out = _create_product(client, seller, name="Almost Out", stock=1)
    out_of_stock = _create_product(client, seller, name="Out Of Stock", stock=0)

    response = client.post(
        _api(seller, "/orders/"),
        json=_order_payload(
            [_item(almost_out, 3), _item(out_of_stock, 1)],
            notes="Call before delivery",
        ),
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text  # warnings never reject
    body = response.json()

    warnings = body["warnings"]
    assert len(warnings) == 2, warnings
    by_name = {warning["product_name"]: warning for warning in warnings}

    assert by_name["Almost Out"]["product_id"] == almost_out["id"]
    assert by_name["Almost Out"]["quantity_requested"] == 3
    assert by_name["Almost Out"]["stock_available"] == 1
    assert "3" in by_name["Almost Out"]["message"]

    assert by_name["Out Of Stock"]["quantity_requested"] == 1
    assert by_name["Out Of Stock"]["stock_available"] == 0

    # The server-generated system note is persisted on the order…
    assert body["system_notes"], "system_notes missing from the creation response"
    assert "Stock warnings at order creation" in body["system_notes"]
    assert "Almost Out" in body["system_notes"]
    assert "Out Of Stock" in body["system_notes"]

    # …the seller's own note is untouched, and both survive a re-read.
    assert body["notes"] == "Call before delivery"
    assert "Stock warnings" not in (body["notes"] or "")

    reread = client.get(_api(seller, f"/orders/{body['id']}"), headers=seller["auth"]).json()
    assert reread["notes"] == "Call before delivery"
    assert reread["system_notes"] == body["system_notes"]

    # The list endpoint exposes it too (the console marks those rows).
    listed = client.get(_api(seller, "/orders/"), headers=seller["auth"]).json()
    row = next(order for order in listed if order["id"] == body["id"])
    assert row["system_notes"] == body["system_notes"]


def test_sufficient_stock_has_no_warnings_or_system_notes(client):
    seller = register_seller(client)
    plenty = _create_product(client, seller, name="Plenty", stock=10)

    response = client.post(
        _api(seller, "/orders/"),
        json=_order_payload([_item(plenty, 2)]),
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["warnings"] == []
    assert body["system_notes"] is None


def test_zero_stock_warns_but_never_rejects(client):
    seller = register_seller(client)
    empty = _create_product(client, seller, name="Empty Shelf", stock=0)

    response = client.post(
        _api(seller, "/orders/"),
        json=_order_payload([_item(empty, 1)]),
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["warnings"]) == 1
    warning = body["warnings"][0]
    assert warning["stock_available"] == 0
    assert warning["quantity_requested"] == 1
    assert body["system_notes"] and "Empty Shelf" in body["system_notes"]


def test_requesting_exactly_stock_does_not_warn(client):
    seller = register_seller(client)
    exact = _create_product(client, seller, name="Exact Fit", stock=4)

    response = client.post(
        _api(seller, "/orders/"),
        json=_order_payload([_item(exact, 4)]),
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    assert response.json()["warnings"] == []


def test_custom_items_without_product_never_warn(client):
    seller = register_seller(client)

    response = client.post(
        _api(seller, "/orders/"),
        json=_order_payload(
            [
                {
                    "product_id": None,
                    "product_name": "Custom tailoring",
                    "quantity": 99,
                    "unit_price": "50.00",
                    "unit_cost": "0.00",
                }
            ]
        ),
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    assert response.json()["warnings"] == []


def test_warnings_do_not_change_order_totals(client):
    seller = register_seller(client)
    scarce = _create_product(client, seller, name="Scarce", stock=1)

    response = client.post(
        _api(seller, "/orders/"),
        json=_order_payload(
            [_item(scarce, 3, unit_price="100.00")],
        )
        | {"delivery_fee": "60.00", "discount": "30.00"},
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["warnings"], "expected a warning for the shortfall"
    # 3 × 100 + 60 − 30 = 330 — identical formula as without warnings.
    assert float(body["total_amount"]) == 330.00
    assert float(body["total_cost"]) == 120.00
    assert float(body["gross_profit"]) == 150.00  # (300 − 120) − 30


def test_archived_products_are_still_rejected(client):
    seller = register_seller(client)
    product = _create_product(client, seller, name="Discontinued", stock=5)
    archived = client.put(
        _api(seller, f"/products/{product['id']}"),
        json={"status": "inactive"},
        headers=seller["auth"],
    )
    assert archived.status_code == 200

    response = client.post(
        _api(seller, "/orders/"),
        json=_order_payload([_item(product, 1)]),
        headers=seller["auth"],
    )
    assert response.status_code == 400  # guard unchanged: archive rejects
    assert "archived" in response.json()["detail"].lower()


def test_system_notes_are_tenant_scoped(client):
    seller_a = register_seller(client)
    seller_b = register_seller(client)
    scarce = _create_product(client, seller_a, name="A-only stock", stock=0)
    created = client.post(
        _api(seller_a, "/orders/"),
        json=_order_payload([_item(scarce, 1)]),
        headers=seller_a["auth"],
    ).json()

    # B never sees A's order (path isolation) and has no rows of its own.
    assert client.get(_api(seller_a, f"/orders/{created['id']}"), headers=seller_b["auth"]).status_code == 403
    assert client.get(_api(seller_b, "/orders/"), headers=seller_b["auth"]).json() == []
