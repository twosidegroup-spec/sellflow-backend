"""Device bridge service: pairing, device credentials, status and ingestion.

Ported from System A's `app/payment/bridge.py` and adapted to System B:

* SQLAlchemy session instead of psycopg.
* Device credentials live on the EXISTING `devices` table (extended by the
  migration) rather than a parallel `device_bridge_devices` table, so there is
  one canonical device concept.
* Events land directly in `payment_events` (with `device_id` attribution)
  instead of a separate `device_bridge_events` ledger, and flow through the
  payment-intelligence engine, so there is one canonical payment ledger.
* Device↔business binding is enforced on every path: the code carries the
  business, the token resolves the business, and ingestion re-checks both.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.device_tokens import (
    hash_device_secret,
    new_device_token,
    new_pairing_code,
)
from app.devices.bridge_parser import BKASH_ANDROID_EVENT_PARSER
from app.devices.bridge_schemas import DeviceEventRequest
from app.devices.models import Device, DevicePairingCode
from app.payments.intelligence.models import PaymentEventCreate, PaymentSourceType
from app.payments.intelligence.service import PAYMENT_INTELLIGENCE_SERVICE

PAIRING_CODE_TTL_SECONDS = 60


class DeviceBridgeService:
    # ------------------------------------------------------------------ pairing

    def create_pairing_code(self, db: Session, business_id: int, user_id: int | None) -> dict:
        """Mint a 60-second, single-use pairing code for one business.

        Only unused codes that no device was created from are invalidated, so
        issuing a second code cannot break an already-paired device's foreign
        key (the defect System A's Phase 1B fixed).
        """
        used_code_ids = [
            row[0]
            for row in db.query(Device.pairing_code_id)
            .filter(Device.pairing_code_id.isnot(None))
            .all()
        ]
        stale = db.query(DevicePairingCode).filter(
            DevicePairingCode.business_id == business_id,
            DevicePairingCode.used_at.is_(None),
        )
        if used_code_ids:
            stale = stale.filter(DevicePairingCode.id.notin_(used_code_ids))
        stale.delete(synchronize_session=False)

        code = new_pairing_code()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=PAIRING_CODE_TTL_SECONDS)
        db.add(
            DevicePairingCode(
                business_id=business_id,
                user_id=user_id,
                code_hash=hash_device_secret(code),
                expires_at=expires_at,
            )
        )
        db.commit()
        return {
            "pairing_code": code,
            "expires_at": expires_at.isoformat(),
            "expires_in_seconds": PAIRING_CODE_TTL_SECONDS,
        }

    def pair_device(self, db: Session, pairing_code: str, device_name: str) -> dict:
        """Exchange a pairing code for a device token. The code is the grant.

        The tenant comes from the code alone and can never be supplied by the
        caller; a wrong, expired or already-redeemed code produces the same
        404 so the response leaks nothing about which codes exist.
        """
        code = (pairing_code or "").strip()
        if not code:
            raise HTTPException(status_code=404, detail="Pairing code is invalid or expired")

        hashed = hash_device_secret(code)
        row = (
            db.query(DevicePairingCode)
            .filter(
                DevicePairingCode.code_hash == hashed,
                DevicePairingCode.used_at.is_(None),
                DevicePairingCode.expires_at > datetime.now(timezone.utc),
            )
            .order_by(DevicePairingCode.id.desc())
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Pairing code is invalid or expired")

        token = new_device_token()
        device = Device(
            device_id=f"bridge-{secrets.token_hex(8)}",
            user_id=row.user_id,
            business_id=row.business_id,
            device_type="android",
            device_name=device_name,
            device_token_hash=hash_device_secret(token),
            pairing_code_id=row.id,
            status="paired",
            sms_permission_granted=False,
            monitoring_active=False,
            paired_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(device)
        row.used_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(device)

        return {
            "device_id": str(device.id),
            "device_name": device.device_name,
            "status": device.status,
            "device_token": token,
            "business_id": int(row.business_id),
        }

    # ------------------------------------------------------------------- state

    def verify_device_token(self, db: Session, token: str) -> Device:
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        hashed = hash_device_secret(token)
        device = (
            db.query(Device)
            .filter(Device.device_token_hash == hashed, Device.status == "paired")
            .first()
        )
        if device is None:
            raise HTTPException(status_code=401, detail="Invalid or expired device token")
        return device

    def update_device_status(
        self, db: Session, device: Device, sms_permission_granted: bool, monitoring_active: bool
    ) -> dict:
        device.sms_permission_granted = bool(sms_permission_granted)
        device.monitoring_active = bool(monitoring_active)
        device.last_active = datetime.now(timezone.utc)
        db.commit()
        db.refresh(device)
        return {
            "device_id": str(device.id),
            "device_paired": device.status == "paired",
            "sms_permission_granted": bool(device.sms_permission_granted),
            "monitoring_active": bool(device.monitoring_active),
        }

    def list_devices(self, db: Session, business_id: int) -> list[dict]:
        devices = (
            db.query(Device)
            .filter(Device.business_id == business_id)
            .order_by(Device.id.desc())
            .all()
        )
        return [
            {
                "device_id": str(device.id),
                "business_id": int(device.business_id) if device.business_id else None,
                "device_name": device.device_name,
                "status": device.status,
                "paired_at": device.paired_at.isoformat() if device.paired_at else None,
                "created_at": device.created_at.isoformat() if device.created_at else None,
                "sms_permission_granted": bool(device.sms_permission_granted),
                "monitoring_active": bool(device.monitoring_active),
            }
            for device in devices
        ]

    # ---------------------------------------------------------------- ingestion

    def ingest_device_event(
        self, db: Session, device: Device, payload: DeviceEventRequest
    ) -> dict:
        if device.business_id is None:
            raise HTTPException(
                status_code=401, detail="That device is not attached to a business."
            )
        business_id = int(device.business_id)

        parsed = BKASH_ANDROID_EVENT_PARSER.parse(payload.model_dump())

        event_payload = PaymentEventCreate(
            transaction_id=parsed["transaction_id"],
            amount=parsed["amount"],
            currency=parsed["currency"],
            sender_identifier=parsed["sender_identifier"],
            receiver_identifier=parsed["receiver_identifier"],
            timestamp=parsed["timestamp"],
            source_type=(
                PaymentSourceType.SMS
                if parsed["source"] == "android_sms"
                else PaymentSourceType.DEVICE_EVENT
            ),
            device_id=device.id,
            source=parsed["source"],
        )
        result = PAYMENT_INTELLIGENCE_SERVICE.ingest_event(
            db, business_id=business_id, payload=event_payload, provider=parsed["provider"]
        )

        device.last_active = datetime.now(timezone.utc)
        db.commit()

        if result.get("duplicate"):
            return {
                "event_id": result["event_id"],
                "status": "duplicate",
                "device_id": str(device.id),
                "transaction_id": parsed["transaction_id"],
            }
        return {**result, "device_id": str(device.id), "status": "accepted"}


DEVICE_BRIDGE_SERVICE = DeviceBridgeService()
