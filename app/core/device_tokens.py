"""HMAC derivation for device-bridge secrets (device tokens and pairing codes).

Migrated from System A (`social-commerce-os/app/config.py`). Design rules:

* The key comes from `DEVICE_TOKEN_SECRET` through `app.core.config`.
  In production the settings validator refuses to start without it.
* Outside production, a random per-process key is generated so local work
  and the test suite can run without configuration. Tokens minted by one
  process do not verify in another, which is the intended development
  trade-off and is documented in `MIGRATION_REPORT.md`.
* The derivation is HMAC-SHA256 hex. The same function hashes at mint time
  and at verify time, so the two can never drift.
* The secret value is never logged or included in exceptions.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading

from app.core.config import settings

_lock = threading.Lock()
_process_secret: str | None = None


def device_token_secret() -> str:
    """The HMAC key for device tokens and pairing codes."""
    configured = (settings.device_token_secret or "").strip()
    if configured:
        return configured

    global _process_secret
    if _process_secret is None:
        with _lock:
            if _process_secret is None:
                _process_secret = secrets.token_urlsafe(48)
    return _process_secret


def hash_device_secret(value: str) -> str:
    """HMAC-SHA256 hex digest of a device secret.

    Raises ValueError on an empty value: that is a programming error, not a
    user input problem, and the callers guard against it before calling.
    """
    if not value:
        raise ValueError("Cannot hash an empty device secret")
    key = device_token_secret()
    return hmac.new(key.encode(), value.encode(), hashlib.sha256).hexdigest()


def new_device_token() -> str:
    """A fresh, high-entropy device token (returned once, stored hashed)."""
    return secrets.token_urlsafe(32)


def new_pairing_code() -> str:
    """A fresh one-time pairing code (returned once, stored hashed)."""
    return secrets.token_urlsafe(12)
