"""Console upgrade behaviours (server side).

Covers the features the seller console now relies on:

* order list query parameters — search (`q`), status filter, sort modes and
  limit/offset pagination — with the original no-parameter behaviour kept,
* cash-on-delivery classification at creation,
* product archive/restore through the existing `status` column, including the
  order-creation guard that refuses archived products,
* personal / merchant `account_type` on payment accounts.

These run against the isolated test database under the guard in
`tests/conftest.py`.
"""

from __future__ import annotations

import uuid

from tests.conftest import register_seller


def _api(seller: dict, path: str) -> str:
    return f"/api/v1/businesses/{seller['business_id']}{path}"


def _create_customer(client, seller, name: str, phone: str | None = None) -> dict:
    payload: dict = {"name": name}
    if phone:
        payload["phone"] = phone
    response = client.post(_api(seller, "/customers/"), json=payload, headers=seller["auth"])
    assert response.status_code == 201, response.text
    return response.json()


def _create_product(
    client,
    seller,
    *,
    name: str = "Widget",
    selling_price: str = "100.00",
    cost_price: str = "40.00",
    stock: int = 25,
) -> dict:
    response = client.post(
        _api(seller, "/products/"),
        json={
            "name": name,
            "sku": f"SKU-{uuid.uuid4().hex[:8]}",
            "cost_price": cost_price,
            "selling_price": selling_price,
            "stock_quantity": stock,
        },
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_order(
    client,
    seller,
    *,
    price: str = "100.00",
    customer_id: int | None = None,
    product: dict | None = None,
    is_cod: bool | None = None,
) -> dict:
    item: dict = {
        "product_name": (product or {}).get("name", "Widget"),
        "quantity": 1,
        "unit_price": price,
        "unit_cost": "40.00",
    }
    if product is not None:
        item["product_id"] = product["id"]
    payload: dict = {"items": [item]}
    if customer_id is not None:
        payload["customer_id"] = customer_id
    if is_cod is not None:
        payload["is_cod"] = is_cod
    response = client.post(_api(seller, "/orders/"), json=payload, headers=seller["auth"])
    assert response.status_code == 201, response.text
    return response.json()


# ----------------------------------------------------------------- orders list


def test_order_list_defaults_are_unchanged(client):
    seller = register_seller(client)
    first = _create_order(client, seller, price="100.00")
    second = _create_order(client, seller, price="250.00")

    response = client.get(_api(seller, "/orders/"), headers=seller["auth"])
    assert response.status_code == 200, response.text
    ids = [row["id"] for row in response.json()]
    assert ids == [second["id"], first["id"]]  # newest first, everything returned


def test_order_search_matches_customer_name_and_order_id(client):
    seller = register_seller(client)
    asha = _create_customer(client, seller, "Asha Rahman", phone="01711111111")
    bashir = _create_customer(client, seller, "Bashir Khan")
    order_asha = _create_order(client, seller, customer_id=asha["id"], price="120.00")
    order_bashir = _create_order(client, seller, customer_id=bashir["id"], price="220.00")

    by_name = client.get(
        _api(seller, "/orders/"), params={"q": "asha"}, headers=seller["auth"]
    ).json()
    assert [row["id"] for row in by_name] == [order_asha["id"]]

    by_id = client.get(
        _api(seller, "/orders/"), params={"q": str(order_bashir["id"])}, headers=seller["auth"]
    ).json()
    assert [row["id"] for row in by_id] == [order_bashir["id"]]

    no_match = client.get(
        _api(seller, "/orders/"), params={"q": "zzzz-nobody"}, headers=seller["auth"]
    ).json()
    assert no_match == []


def test_order_status_filter_and_sort_modes(client):
    seller = register_seller(client)
    small = _create_order(client, seller, price="50.00")
    large = _create_order(client, seller, price="500.00")
    patch = client.patch(
        _api(seller, f"/orders/{large['id']}/status"),
        json={"status": "confirmed"},
        headers=seller["auth"],
    )
    assert patch.status_code == 200, patch.text

    confirmed = client.get(
        _api(seller, "/orders/"), params={"status": "confirmed"}, headers=seller["auth"]
    ).json()
    assert [row["id"] for row in confirmed] == [large["id"]]

    descending = client.get(
        _api(seller, "/orders/"), params={"sort": "amount_desc"}, headers=seller["auth"]
    ).json()
    assert [row["id"] for row in descending] == [large["id"], small["id"]]

    ascending = client.get(
        _api(seller, "/orders/"), params={"sort": "amount_asc"}, headers=seller["auth"]
    ).json()
    assert [row["id"] for row in ascending] == [small["id"], large["id"]]


def test_order_pagination_walks_the_list(client):
    seller = register_seller(client)
    orders = [_create_order(client, seller, price=f"{10 * (index + 1)}.00") for index in range(5)]

    first_page = client.get(
        _api(seller, "/orders/"),
        params={"limit": 2, "offset": 0, "sort": "oldest"},
        headers=seller["auth"],
    ).json()
    assert [row["id"] for row in first_page] == [orders[0]["id"], orders[1]["id"]]

    second_page = client.get(
        _api(seller, "/orders/"),
        params={"limit": 2, "offset": 2, "sort": "oldest"},
        headers=seller["auth"],
    ).json()
    assert [row["id"] for row in second_page] == [orders[2]["id"], orders[3]["id"]]


def test_order_query_params_are_validated(client):
    seller = register_seller(client)
    for params in ({"sort": "sideways"}, {"limit": 0}, {"limit": 500}, {"offset": -1}):
        response = client.get(_api(seller, "/orders/"), params=params, headers=seller["auth"])
        assert response.status_code == 422, (params, response.status_code)


def test_orders_query_params_keep_tenant_isolation(client):
    seller_a = register_seller(client)
    seller_b = register_seller(client)
    _create_order(client, seller_a)

    response = client.get(
        _api(seller_a, "/orders/"),
        params={"q": "a", "status": "created", "limit": 5},
        headers=seller_b["auth"],
    )
    assert response.status_code == 403


# ------------------------------------------------------------------------ COD


def test_cod_classification_round_trips(client):
    seller = register_seller(client)
    prepaid = _create_order(client, seller, is_cod=False)
    cod = _create_order(client, seller, is_cod=True)

    assert prepaid["is_cod"] is False
    assert cod["is_cod"] is True

    fetched = client.get(_api(seller, f"/orders/{cod['id']}"), headers=seller["auth"]).json()
    assert fetched["is_cod"] is True

    listed = client.get(_api(seller, "/orders/"), headers=seller["auth"]).json()
    by_id = {row["id"]: row for row in listed}
    assert by_id[cod["id"]]["is_cod"] is True
    assert by_id[prepaid["id"]]["is_cod"] is False


# ------------------------------------------------------------ product archive


def test_product_archive_and_restore(client):
    seller = register_seller(client)
    product = _create_product(client, seller, name="Archivable product")
    assert product["status"] == "active"

    archived = client.put(
        _api(seller, f"/products/{product['id']}"),
        json={"status": "inactive"},
        headers=seller["auth"],
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "inactive"

    listed = client.get(_api(seller, "/products/"), headers=seller["auth"]).json()
    assert next(row for row in listed if row["id"] == product["id"])["status"] == "inactive"

    restored = client.put(
        _api(seller, f"/products/{product['id']}"),
        json={"status": "active"},
        headers=seller["auth"],
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_archived_product_cannot_be_ordered(client):
    seller = register_seller(client)
    product = _create_product(client, seller, name="Discontinued model")
    archived = client.put(
        _api(seller, f"/products/{product['id']}"),
        json={"status": "inactive"},
        headers=seller["auth"],
    )
    assert archived.status_code == 200

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
            ]
        },
        headers=seller["auth"],
    )
    assert response.status_code == 400, response.text
    assert "archived" in response.json()["detail"].lower()

    # Restoring makes it orderable again.
    client.put(
        _api(seller, f"/products/{product['id']}"),
        json={"status": "active"},
        headers=seller["auth"],
    )
    retry = client.post(
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
            ]
        },
        headers=seller["auth"],
    )
    assert retry.status_code == 201, retry.text


def test_archive_does_not_break_existing_orders(client):
    seller = register_seller(client)
    product = _create_product(client, seller, name="Ordered then archived")
    order = _create_order(client, seller, product=product, price="100.00")

    client.put(
        _api(seller, f"/products/{product['id']}"),
        json={"status": "inactive"},
        headers=seller["auth"],
    )

    fetched = client.get(_api(seller, f"/orders/{order['id']}"), headers=seller["auth"])
    assert fetched.status_code == 200
    assert fetched.json()["items"][0]["product_name"] == product["name"]


# ------------------------------------------------------------ account types


def _connect_account(client, seller, *, provider: str = "bkash", number: str = "01712345678", account_type: str | None = None) -> dict:
    payload: dict = {"provider": provider, "receiving_number": number}
    if account_type is not None:
        payload["account_type"] = account_type
    return client.post(
        "/payment-accounts/connect",
        params={"business_id": seller["business_id"]},
        json=payload,
        headers=seller["auth"],
    )


def test_payment_account_type_defaults_to_personal(client):
    seller = register_seller(client)
    response = _connect_account(client, seller)
    assert response.status_code == 200, response.text
    assert response.json()["account_type"] == "personal"

    listed = client.get(
        "/payment-accounts",
        params={"business_id": seller["business_id"]},
        headers=seller["auth"],
    ).json()
    assert listed[0]["account_type"] == "personal"


def test_payment_account_type_merchant_round_trips(client):
    seller = register_seller(client)
    response = _connect_account(client, seller, account_type="merchant")
    assert response.status_code == 200, response.text
    assert response.json()["account_type"] == "merchant"

    # Re-connecting the same provider switches the type without duplicating.
    switched = _connect_account(client, seller, account_type="personal")
    assert switched.status_code == 200
    assert switched.json()["account_type"] == "personal"

    listed = client.get(
        "/payment-accounts",
        params={"business_id": seller["business_id"]},
        headers=seller["auth"],
    ).json()
    assert len(listed) == 1
    assert listed[0]["account_type"] == "personal"


def test_payment_account_type_is_validated(client):
    seller = register_seller(client)
    response = _connect_account(client, seller, account_type="business-plus")
    assert response.status_code == 422


# ------------------------------------------------------------ analytics range


def test_analytics_summary_range_parameter(client):
    seller = register_seller(client)
    _create_order(client, seller)

    default = client.get(_api(seller, "/analytics/summary"), headers=seller["auth"]).json()
    assert len(default["daily"]) == 7  # unchanged default window

    month = client.get(
        _api(seller, "/analytics/summary"), params={"days": 30}, headers=seller["auth"]
    ).json()
    assert len(month["daily"]) == 30
    # Lifetime figures are independent of the daily-series window.
    assert month["total_revenue"] == default["total_revenue"]
    assert month["total_orders"] == default["total_orders"]

    for bad in ({"days": 3}, {"days": 365}, {"days": "lots"}):
        response = client.get(
            _api(seller, "/analytics/summary"), params=bad, headers=seller["auth"]
        )
        assert response.status_code == 422, (bad, response.status_code)


def test_analytics_range_keeps_tenant_isolation(client):
    seller_a = register_seller(client)
    seller_b = register_seller(client)

    response = client.get(
        _api(seller_a, "/analytics/summary"), params={"days": 30}, headers=seller_b["auth"]
    )
    assert response.status_code == 403
