"""Server-side validation of a normalized bKash event from the Android bridge.

Ported from System A's `BkashAndroidEventParser`. The bridge client parses the
SMS on-device; this parser re-validates and canonicalizes everything before it
enters the intelligence pipeline. It deliberately does NOT accept or persist
SMS bodies.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.utils.phone import normalize_phone


class BkashAndroidEventParser:
    @staticmethod
    def parse(payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("provider") != "bkash":
            raise HTTPException(status_code=422, detail="Provider must be bkash")

        amount = str(payload.get("amount", "")).strip()
        transaction_id = str(payload.get("transaction_id", "")).strip()
        timestamp = str(payload.get("timestamp", "")).strip()
        if not amount or not transaction_id or not timestamp:
            raise HTTPException(
                status_code=422,
                detail="amount, transaction_id, and timestamp are required",
            )

        try:
            decimal_amount = Decimal(amount)
        except Exception as exc:
            raise HTTPException(
                status_code=422, detail="amount must be a valid decimal number"
            ) from exc

        if decimal_amount <= 0:
            raise HTTPException(status_code=422, detail="amount must be greater than zero")

        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="timestamp must be ISO-8601"
            ) from exc

        sender = payload.get("sender_identifier")
        receiver = payload.get("receiver_identifier")
        if sender is not None:
            try:
                sender = normalize_phone(str(sender))
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail="sender_identifier must be a valid Bangladesh mobile number",
                ) from exc
        if receiver is not None:
            try:
                receiver = normalize_phone(str(receiver))
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail="receiver_identifier must be a valid Bangladesh mobile number",
                ) from exc

        source = str(payload.get("source", "android_notification")).strip() or "android_notification"
        return {
            "provider": "bkash",
            "amount": amount,
            "transaction_id": transaction_id,
            "currency": str(payload.get("currency", "BDT")).strip().upper() or "BDT",
            "sender_identifier": sender,
            "receiver_identifier": receiver,
            "timestamp": timestamp,
            "source": source,
            "source_type": "sms" if source == "android_sms" else "device_event",
            "raw_metadata": {
                "notification_package": payload.get("notification_package"),
                "message_text_present": bool(payload.get("message_text")),
                "provider_detected_from": (
                    "sms_sender_and_message_structure"
                    if source == "android_sms"
                    else "structured_device_payload"
                ),
            },
        }


BKASH_ANDROID_EVENT_PARSER = BkashAndroidEventParser()
