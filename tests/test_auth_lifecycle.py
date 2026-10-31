"""Pre-production acceptance audit — authentication lifecycle.

Covers the paths not already pinned by `test_auth.py`:

* duplicate registration, login for unknown emails
* expired and malformed JWTs, tokens for deleted users
* JWT payload hygiene (no secrets, sane expiry)
* stateless-token semantics (there is no server-side logout/revocation list —
  documented behaviour, asserted explicitly so a change is noticed)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.security import ALGORITHM, SECRET_KEY
from app.db.engine import SessionLocal
from app.db.base import User
from tests.conftest import register_seller


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


def test_tokens_are_stateless_no_logout_revocation_endpoint(client):
    """Documents the current security model (24h bearer tokens).

    There is no server-side logout endpoint and no revocation list: a token
    remains valid until it expires even after a password change. The UI
    "logout" discards the token client-side. If this ever becomes a hard
    requirement, add a per-user token version and bump it on password change.
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

    # The old token still authenticates — stateless JWT semantics.
    still_valid = client.get("/api/v1/auth/me", headers=seller["auth"])
    assert still_valid.status_code == 200
