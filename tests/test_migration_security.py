"""Regression tests for the security fixes applied during the migration.

Covers:
* public write endpoints removed
* payment "detect" is authenticated, tenant-scoped and disabled in production
* membership endpoints work and enforce roles (the TypeError fix)
* registration rate limiting actually fires
* configuration fails closed in production (JWT secret + device secret)
* CORS never combines wildcard with credentials
* webhook URLs are validated (SSRF guard) and the signing secret is returned
* product upload route is reachable at its distinct path and sanitizes names
* health endpoints no longer leak error detail and /ready really probes the DB
"""

from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from tests.conftest import create_order, register_seller

from app.core.config import Settings, settings


# ------------------------------------------------------------------ public routes


def test_legacy_public_write_endpoints_are_gone(client):
    assert client.post("/api/orders", json={"total_amount": 1, "customer_name": "x"}).status_code == 404
    assert client.post("/api/products", json={"name": "x"}).status_code == 404
    assert client.post("/api/customers", json={"name": "x"}).status_code == 404


# ----------------------------------------------------------------- payment detect


def test_detect_requires_authentication(client):
    response = client.post(
        "/api/v1/payments/detect",
        json={"receiver_number": "01711111111", "amount": 100, "method": "bkash"},
    )
    assert response.status_code == 401


def test_detect_matches_only_own_business(client):
    seller = register_seller(client, receiving_number="01711111111")
    order = create_order(client, seller, unit_price="100.00")

    # Own receiving number: matched (development simulator)
    own = client.post(
        "/api/v1/payments/detect",
        json={
            "receiver_number": "01711111111",
            "amount": 100,
            "method": "bkash",
            "transaction_id": "SEC-DETECT-OWN-1",
        },
        headers=seller["auth"],
    )
    assert own.status_code == 200, own.text
    assert own.json()["matched"] is True
    assert own.json()["order_id"] == order["id"]

    # Somebody else's receiving number: refused
    other = client.post(
        "/api/v1/payments/detect",
        json={
            "receiver_number": "01799999999",
            "amount": 100,
            "method": "bkash",
        },
        headers=seller["auth"],
    )
    assert other.status_code == 404


def test_detect_is_disabled_in_production(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    seller = register_seller(client, receiving_number="01711111111")
    response = client.post(
        "/api/v1/payments/detect",
        json={"receiver_number": "01711111111", "amount": 100, "method": "bkash"},
        headers=seller["auth"],
    )
    assert response.status_code == 404


# ------------------------------------------------------------------- memberships


def test_membership_add_and_remove_work(client):
    owner = register_seller(client)
    member = register_seller(client)

    added = client.post(
        f"/api/v1/businesses/{owner['business_id']}/memberships",
        json={"user_id": member["user_id"], "role": "staff"},
        headers=owner["auth"],
    )
    assert added.status_code == 201, added.text
    assert added.json()["role"] == "staff"

    # The member now sees the owner's business membership list
    listing = client.get(
        f"/api/v1/businesses/{owner['business_id']}/memberships",
        headers=member["auth"],
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 2

    removed = client.delete(
        f"/api/v1/businesses/{owner['business_id']}/memberships/{member['user_id']}",
        headers=owner["auth"],
    )
    assert removed.status_code == 204

    # The member can no longer access the business
    denied = client.get(
        f"/api/v1/businesses/{owner['business_id']}/memberships",
        headers=member["auth"],
    )
    assert denied.status_code == 403


def test_non_member_cannot_add_members(client):
    owner = register_seller(client)
    outsider = register_seller(client)
    response = client.post(
        f"/api/v1/businesses/{owner['business_id']}/memberships",
        json={"user_id": outsider["user_id"], "role": "staff"},
        headers=outsider["auth"],
    )
    assert response.status_code == 403


def test_invalid_role_is_rejected(client):
    owner = register_seller(client)
    other = register_seller(client)
    response = client.post(
        f"/api/v1/businesses/{owner['business_id']}/memberships",
        json={"user_id": other["user_id"], "role": "superuser"},
        headers=owner["auth"],
    )
    assert response.status_code == 400


# ----------------------------------------------------------------- rate limiting


def test_register_rate_limit_fires(client):
    statuses = []
    for index in range(6):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"ratelimit-{index}-{os.urandom(4).hex()}@example.com",
                "full_name": "Rate Limit",
                "password": "pass1234",
            },
        )
        statuses.append(response.status_code)
    assert statuses[:5] == [201] * 5
    assert statuses[5] == 429


# --------------------------------------------------------------- configuration


def test_production_requires_real_secret_key():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            secret_key="your-32-character-secret-key-generate-with-openssl",
            device_token_secret="x" * 40,
        )


def test_production_requires_device_token_secret():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            secret_key="a-real-secret-value-of-sufficient-length-1234567890",
            device_token_secret="",
        )


def test_production_accepts_real_secrets():
    created = Settings(
        app_env="production",
        secret_key="a-real-secret-value-of-sufficient-length-1234567890",
        device_token_secret="another-real-secret-value-1234567890abcdef",
    )
    assert created.is_production is True


def test_wildcard_cors_disables_credentials():
    wildcard = Settings(cors_origins="*")
    assert "*" in wildcard.cors_origin_list
    assert wildcard.cors_allow_credentials is False

    # The shipped default is an explicit list, not a wildcard
    assert "*" not in settings.cors_origin_list
    assert settings.cors_allow_credentials is True


def test_cors_preflight_reflects_explicit_origin(client):
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin == "http://localhost:3000"


# --------------------------------------------------------------------- webhooks


def test_webhook_url_validation_rejects_private_hosts(client):
    seller = register_seller(client)
    response = client.post(
        f"/api/v1/businesses/{seller['business_id']}/webhooks/",
        json={"url": "http://127.0.0.1:8000/steal", "events": "payment.recorded"},
        headers=seller["auth"],
    )
    assert response.status_code == 400


def test_webhook_creation_returns_signing_secret(client):
    seller = register_seller(client)
    created = client.post(
        f"/api/v1/businesses/{seller['business_id']}/webhooks/",
        json={"url": "http://example.com/hooks", "events": "payment.recorded"},
        headers=seller["auth"],
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["secret_key"]

    webhook_id = body["id"]
    deleted = client.delete(
        f"/api/v1/businesses/{seller['business_id']}/webhooks/{webhook_id}",
        headers=seller["auth"],
    )
    assert deleted.status_code == 204


# ------------------------------------------------------------------- upload path


def test_product_upload_route_is_reachable_and_sanitizes_names(client):
    from app.products.upload_router import UPLOAD_DIR

    seller = register_seller(client)
    response = client.post(
        f"/api/v1/businesses/{seller['business_id']}/products/upload",
        data={
            "name": "Uploaded Product",
            "sku": f"UP-{os.urandom(4).hex()}",
            "cost_price": "10.00",
            "selling_price": "20.00",
            "stock_quantity": "5",
        },
        files={"file": ("../../../evil.png", b"not-really-a-png", "image/png")},
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    image_url = response.json()["image_url"]
    assert image_url.startswith("/uploads/")
    assert ".." not in image_url
    assert "/" not in image_url.replace("/uploads/", "", 1)

    stored = os.path.join(UPLOAD_DIR, image_url.replace("/uploads/", "", 1))
    try:
        assert os.path.exists(stored)
    finally:
        if os.path.exists(stored):
            os.remove(stored)


# ---------------------------------------------------------------------- health


def test_health_endpoints_are_safe(client):
    status_response = client.get("/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "ok"

    database_response = client.get("/database")
    assert database_response.status_code == 200
    assert database_response.json() == {"status": "ok", "database": "connected"}
    assert "error" not in database_response.json()

    ready_response = client.get("/ready")
    assert ready_response.status_code == 200
    assert ready_response.json()["ready"] is True
