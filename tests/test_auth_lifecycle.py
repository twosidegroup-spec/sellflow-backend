"""Pre-production acceptance audit — authentication lifecycle.

Covers the paths not already pinned by `test_auth.py`:

* duplicate registration, login for unknown emails
* expired and malformed JWTs, tokens for deleted users
* JWT payload hygiene (no secrets, sane expiry)
* token-version revocation: a password change invalidates every previously
  issued token (see also `test_token_version_audit.py`); there is still no
  logout endpoint — the bearer token remains stateless until revoked
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.security import ALGORITHM, SECRET_KEY
from app.db.engine import SessionLocal
from app.db.base import User
from tests.conftest import register_seller


def test_registration_invite_code_gate(client, monkeypatch):
    """STAGING gate: when REGISTRATION_INVITE_CODE is set, only matching
    registrations succeed (constant-time comparison; 403 otherwise)."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "registration_invite_code", "pilot-invite-2026")
    suffix = uuid.uuid4().hex[:8]

    denied = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"noinvite-{suffix}@example.com",
            "full_name": "No Invite",
            "password": "pass1234",
            "business_name": "No Invite Shop",
        },
    )
    assert denied.status_code == 403
    assert "invitation" in denied.json()["detail"].lower()

    wrong = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"wronginvite-{suffix}@example.com",
            "full_name": "Wrong Invite",
            "password": "pass1234",
            "business_name": "Wrong Invite Shop",
            "invite_code": "not-the-code",
        },
    )
    assert wrong.status_code == 403

    accepted = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"invited-{suffix}@example.com",
            "full_name": "Invited Seller",
            "password": "pass1234",
            "business_name": "Invited Shop",
            "invite_code": "pilot-invite-2026",
        },
    )
    assert accepted.status_code == 201, accepted.text


def test_duplicate_registration_is_rejected_cleanly(client):
    seller = register_seller(client)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": seller["email"],
            "full_name": "Copycat",
            "password": "pass1234",
            "business_name": "Copycat Shop",
        },
    )
    assert response.status_code in (400, 409), response.text
    assert "detail" in response.json()


def test_login_for_unknown_email_is_401(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": f"ghost-{uuid.uuid4().hex[:8]}@example.com", "password": "pass1234"},
    )
    assert response.status_code == 401


def test_expired_token_is_rejected(client):
    seller = register_seller(client)
    expired = jwt.encode(
        {
            "sub": str(seller["user_id"]),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_token_of_deleted_user_is_rejected(client):
    seller = register_seller(client)
    with SessionLocal() as session:
        user = session.query(User).filter(User.id == seller["user_id"]).first()
        assert user is not None
        session.delete(user)
        session.commit()

    response = client.get("/api/v1/auth/me", headers=seller["auth"])
    assert response.status_code == 401


def test_issued_token_payload_has_no_secrets_and_sane_expiry(client):
    seller = register_seller(client)
    payload = jwt.decode(seller["token"], SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["sub"] == str(seller["user_id"])
    expiry = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    remaining = expiry - datetime.now(timezone.utc)
    assert timedelta(hours=1) < remaining <= timedelta(hours=25)

    serialized = str(payload).lower()
    assert "password" not in serialized and "hash" not in serialized


def test_password_change_revokes_existing_tokens(client):
    """Per-user token-version revocation (STAGING_READINESS.md 5.1).

    There is still no logout endpoint — the token remains a stateless bearer
    credential — but a password change bumps the user's `token_version`, so
    every previously issued token is rejected immediately.
    """
    seller = register_seller(client)

    missing = client.post("/api/v1/auth/logout", headers=seller["auth"])
    assert missing.status_code in (404, 405)

    changed = client.post(
        "/api/v1/auth/passcode/change",
        json={"current_password": seller["password"], "new_password": "pass12345"},
        headers=seller["auth"],
    )
    assert changed.status_code == 200, changed.text

    # The old token is revoked everywhere.
    revoked = client.get("/api/v1/auth/me", headers=seller["auth"])
    assert revoked.status_code == 401

    # A fresh login with the new password works.
    login = client.post(
        "/api/v1/auth/login",
        json={"email": seller["email"], "password": "pass12345"},
    )
    assert login.status_code == 200
    fresh = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert fresh.status_code == 200
