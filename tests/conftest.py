"""Test configuration with a destructive-target safety guard.

The suite writes and DELETES rows. A previous iteration of this project
(System A) destroyed real data because its suite had no guard. This file
adopts the same fail-closed policy:

    pytest only runs when BOTH are true:
      1. SELLFLOW_ALLOW_DESTRUCTIVE_TESTS is a true value, and
      2. DATABASE_URL names a database ending in `_test` that contains no
         production-ish token.

When either is false the suite exits before touching any database and prints
what is missing (never the URL itself). Create the isolated database with:

    python scripts/create_test_db.py

and run tests with, for example:

    $env:DATABASE_URL = "postgresql+psycopg://user:pass@localhost:5432/sellflow_migration_test"
    $env:SELLFLOW_ALLOW_DESTRUCTIVE_TESTS = "1"
    pytest tests/ -q
"""

from __future__ import annotations

import os
import uuid
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

_TRUE_VALUES = {"1", "true", "yes", "on"}
_PRODUCTION_TOKENS = ("prod", "production", "live", "primary", "main", "master")


def _assert_isolated_test_database() -> None:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        pytest.exit(
            "REFUSING TO RUN: DATABASE_URL is not set. Point it at a disposable "
            "database whose name ends in '_test'. Nothing was executed.",
            returncode=1,
        )
    if os.getenv("SELLFLOW_ALLOW_DESTRUCTIVE_TESTS", "").strip().lower() not in _TRUE_VALUES:
        pytest.exit(
            "REFUSING TO RUN: SELLFLOW_ALLOW_DESTRUCTIVE_TESTS is not set to a true "
            "value. This suite deletes rows. Nothing was executed.",
            returncode=1,
        )
    try:
        database = urlsplit(url).path.lstrip("/").lower()
    except ValueError:
        pytest.exit("REFUSING TO RUN: DATABASE_URL could not be parsed.", returncode=1)

    if not database.endswith("_test"):
        pytest.exit(
            "REFUSING TO RUN: the configured database name does not end in "
            "'_test'. Nothing was executed.",
            returncode=1,
        )
    if any(token in database for token in _PRODUCTION_TOKENS):
        pytest.exit(
            "REFUSING TO RUN: the configured database name looks like a "
            "production database. Nothing was executed.",
            returncode=1,
        )


_assert_isolated_test_database()


@pytest.fixture(scope="session")
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Clear shared (database-backed) state between tests.

    Purges every business-data table in FK-safe order so the pre-existing
    suites (which wipe rows ad hoc) and the migration tests never collide with
    leftovers, and clears the database-backed rate-limit state.
    """
    from sqlalchemy import text

    from app.payments.intelligence.db_models import (
        PaymentAnomaly,
        PaymentDecision,
        PaymentEvent,
        PaymentFeedback,
        PaymentMatch,
    )
    from app.db.base import (
        Business,
        Customer,
        Delivery,
        DetectedPayment,
        Device,
        DevicePairingCode,
        Membership,
        Order,
        OrderItem,
        Payment,
        Product,
        ProductImage,
        User,
        WebhookSubscription,
    )
    from app.db.engine import SessionLocal

    with SessionLocal() as session:
        # FK-safe order: children before parents.
        session.query(PaymentFeedback).delete()
        session.query(PaymentAnomaly).delete()
        session.query(PaymentMatch).delete()
        session.query(PaymentDecision).delete()
        session.query(PaymentEvent).delete()
        session.query(DetectedPayment).delete()
        session.query(Payment).delete()
        session.query(OrderItem).delete()
        session.query(Delivery).delete()
        session.query(Order).delete()
        session.query(ProductImage).delete()
        session.query(Product).delete()
        session.query(Customer).delete()
        session.query(Device).delete()
        session.query(DevicePairingCode).delete()
        session.query(Membership).delete()
        session.query(WebhookSubscription).delete()
        session.query(User).delete()
        session.query(Business).delete()
        session.execute(text("DELETE FROM rate_limit_events"))
        session.commit()
    yield


@pytest.fixture()
def db():
    from app.db.engine import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def register_seller(client: TestClient, *, receiving_number: str | None = None) -> dict:
    """Create a fresh user+business and log in. Returns the session bundle."""
    suffix = uuid.uuid4().hex[:10]
    email = f"seller-{suffix}@example.com"
    payload = {
        "email": email,
        "full_name": f"Seller {suffix}",
        "password": "pass1234",
        "business_name": f"Shop {suffix}",
        "phone": "01700000000",
    }
    if receiving_number:
        payload["receiving_number"] = receiving_number
        payload["payment_provider"] = "bkash"

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()

    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass1234"}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    user_id = me.json()["id"]

    return {
        "email": email,
        "password": "pass1234",
        "user_id": user_id,
        "business_id": body["business_id"],
        "token": token,
        "auth": {"Authorization": f"Bearer {token}"},
    }


def create_order(
    client: TestClient,
    seller: dict,
    *,
    unit_price: str = "500.00",
    quantity: int = 1,
    customer_id: int | None = None,
) -> dict:
    payload: dict = {
        "items": [
            {
                "product_name": "Migration Test Item",
                "quantity": quantity,
                "unit_price": unit_price,
                "unit_cost": "100.00",
            }
        ],
    }
    if customer_id is not None:
        payload["customer_id"] = customer_id
    response = client.post(
        f"/api/v1/businesses/{seller['business_id']}/orders/",
        json=payload,
        headers=seller["auth"],
    )
    assert response.status_code == 201, response.text
    return response.json()
