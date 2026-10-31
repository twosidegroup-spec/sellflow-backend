"""Regression suite — per-user JWT token-version revocation.

Implements the test plan in STAGING_READINESS.md section 5.3:

1. A token minted at login carries `ver` and works.
2. After a password change the old token is rejected on protected surfaces
   while a fresh login works.
3. A forged token with a stale `ver` is rejected.
4. A token with no `ver` claim is rejected (hard cutover).
5. The device-bridge user-JWT path (`/payment-accounts`) enforces the same.
6. Device-token (HMAC) flows are untouched, including when a stale bearer
   token is also present.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.security import ALGORITHM, SECRET_KEY
from tests.conftest import create_order, register_seller


def _api(seller: dict, path: str) -> str:
    return f"/api/v1/businesses/{seller['business_id']}{path}"


def _decode(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def _forge(user_id: int, *, ver=None, expires_minutes: int = 30) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    if ver is not None:
        payload["ver"] = ver
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def test_login_token_carries_version_zero_and_works(client):
    seller = register_seller(client)
    assert _decode(seller["token"])["ver"] == 0
    assert client.get("/api/v1/auth/me", headers=seller["auth"]).status_code == 200


def test_password_change_revokes_old_token_on_every_protected_surface(client):
    seller = register_seller(client)
    create_order(client, seller)

    protected = [
        "/api/v1/auth/me",
        _api(seller, "/orders/"),
        _api(seller, "/payments/intelligence/summary"),
        _api(seller, "/analytics/summary"),
    ]
    for path in protected:
        assert client.get(path, headers=seller["auth"]).status_code == 200, path

    changed = client.post(
        "/api/v1/auth/passcode/change",
        json={"current_password": seller["password"], "new_password": "pass12345"},
        headers=seller["auth"],
    )
    assert changed.status_code == 200, changed.text

    for path in protected:
        assert client.get(path, headers=seller["auth"]).status_code == 401, path

    # Fresh login works and carries the bumped version.
    login = client.post(
        "/api/v1/auth/login",
        json={"email": seller["email"], "password": "pass12345"},
    )
    assert login.status_code == 200, login.text
    fresh_token = login.json()["access_token"]
    assert _decode(fresh_token)["ver"] == 1
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {fresh_token}"},
        ).status_code
        == 200
    )


def test_forged_token_with_stale_version_is_rejected(client):
    seller = register_seller(client)
    client.post(
        "/api/v1/auth/passcode/change",
        json={"current_password": seller["password"], "new_password": "pass12345"},
        headers=seller["auth"],
    )

    stale = _forge(seller["user_id"], ver=0)  # correct subject, superseded version
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {stale}"}).status_code
        == 401
    )


def test_token_without_version_claim_is_rejected(client):
    """Hard cutover: pre-migration tokens (no `ver`) never authenticate."""
    seller = register_seller(client)
    legacy = _forge(seller["user_id"], ver=None)
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {legacy}"}).status_code
        == 401
    )


def test_payment_accounts_user_jwt_path_enforces_version(client):
    """The device-bridge dependency resolves user JWTs too — it must check."""
    seller = register_seller(client)
    params = {"business_id": seller["business_id"]}
    assert client.get("/payment-accounts", params=params, headers=seller["auth"]).status_code == 200

    client.post(
        "/api/v1/auth/passcode/change",
        json={"current_password": seller["password"], "new_password": "pass12345"},
        headers=seller["auth"],
    )
    assert client.get("/payment-accounts", params=params, headers=seller["auth"]).status_code == 401


def test_device_token_flows_unaffected_by_user_token_revocation(client):
    seller = register_seller(client)

    # Pair a device (HMAC device token, no JWT involved).
    code = client.post(
        f"/device-bridge/pairing-codes?business_id={seller['business_id']}",
        headers=seller["auth"],
    ).json()["pairing_code"]
    device = client.post(
        "/device-bridge/devices",
        json={"pairing_code": code, "device_name": "Revocation Test Phone"},
    ).json()
    device_headers = {"X-Device-Token": device["device_token"]}
    assert client.get("/device-bridge/dashboard", headers=device_headers).status_code == 200

    # Revoke the user's tokens…
    client.post(
        "/api/v1/auth/passcode/change",
        json={"current_password": seller["password"], "new_password": "pass12345"},
        headers=seller["auth"],
    )

    # …the device token still works, even when a stale bearer is also sent.
    both = {**device_headers, "Authorization": f"Bearer {seller['token']}"}
    assert client.get("/device-bridge/dashboard", headers=both).status_code == 200
    assert (
        client.post(
            "/payment-accounts/connect",
            json={"provider": "bkash", "receiving_number": "01712345678"},
            headers=both,
        ).status_code
        == 200
    )
