"""Webhook delivery with HMAC-SHA256 signing.

Replaces System B's previous `trigger_webhooks` (never called; signed with a
random token, not an HMAC). Design:

* Delivery happens in a FastAPI background task with its OWN database session,
  so it never touches the request's session after the response is sent.
* Each request body is the exact JSON bytes that are signed:
  `X-Webhook-Signature: sha256=<hex(HMAC_SHA256(secret, body))>`.
* `X-Webhook-Event` names the event; subscribers can reject unknown events.
* URL safety: only http/https; obvious loopback/private/link-local literal
  hosts are refused at subscription time AND at delivery time (defence in
  depth against SSRF). DNS-based rebinding is out of scope and documented in
  SECURITY notes; the residual risk is accepted for the pilot because
  subscriptions are created by authenticated business owners.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
from urllib.parse import urlsplit

import httpx

from app.db.engine import SessionLocal
from app.webhooks.models import WebhookSubscription

logger = logging.getLogger("sellflow.webhooks")

_TIMEOUT_SECONDS = 10.0


def is_safe_webhook_url(url: str) -> tuple[bool, str]:
    """True when the URL is an http(s) URL whose literal host is not private."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False, "URL could not be parsed"

    if parts.scheme not in {"http", "https"}:
        return False, "URL must use http or https"

    hostname = (parts.hostname or "").strip().lower()
    if not hostname:
        return False, "URL must include a host"

    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        return False, "Local addresses are not allowed"

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        # A DNS name: allowed. (Full DNS-rebinding protection needs resolver
        # pinning, which is out of scope; see module docstring.)
        return True, ""

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return False, "Private, loopback and link-local addresses are not allowed"

    return True, ""


def dispatch_event(business_id: int, event_type: str, payload: dict) -> list[int]:
    """Deliver `event_type` to every active subscriber of `business_id`.

    Returns the response status codes observed (for logging/tests). Never
    raises: a failing subscriber must not break the request that produced the
    event.
    """
    db = SessionLocal()
    try:
        subscriptions = (
            db.query(WebhookSubscription)
            .filter(
                WebhookSubscription.business_id == business_id,
                WebhookSubscription.is_active == True,  # noqa: E712 - SQLA boolean column
                WebhookSubscription.events.like(f"%{event_type}%"),
            )
            .all()
        )
        targets = [
            (sub.url, sub.secret_key, sub.id) for sub in subscriptions
        ]
    finally:
        db.close()

    results: list[int] = []
    for url, secret, subscription_id in targets:
        status_code = _deliver(url, secret, event_type, payload)
        if status_code is not None:
            results.append(status_code)
        else:
            logger.warning(
                "webhook delivery failed subscription_id=%s event=%s",
                subscription_id,
                event_type,
            )
    return results


def _deliver(url: str, secret: str, event_type: str, payload: dict) -> int | None:
    safe, reason = is_safe_webhook_url(url)
    if not safe:
        logger.warning("webhook blocked url_reason=%s", reason)
        return None

    body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    signature = hmac.new((secret or "").encode("utf-8"), body, hashlib.sha256).hexdigest()

    try:
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            response = client.post(
                url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Event": event_type,
                    "X-Webhook-Signature": f"sha256={signature}",
                },
            )
        return response.status_code
    except Exception:  # noqa: BLE001 - delivery must never raise into the task runner
        logger.exception("webhook delivery error event=%s", event_type)
        return None
