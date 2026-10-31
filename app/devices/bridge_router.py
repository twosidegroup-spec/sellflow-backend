"""Device bridge routes.

Mounted at the repository ROOT (`/device-bridge/...`) with no `/api/v1`
prefix, byte-compatible with System A, because the Kotlin Payment Bridge bakes
its backend URL at build time and calls these exact paths. This is a
documented compatibility surface (`API_COMPATIBILITY.md`), not a second API:

* The tenant always comes from the verified device credential or the
  membership-checked user credential — never from a request body.
* Every handler is thin; all logic lives in `bridge_service` and the payment
  intelligence service.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.rate_limit import check_rate_limit
from app.db.dependencies import get_db
from app.devices.bridge_dependencies import (
    DevicePrincipal,
    require_device_principal,
    require_user_or_device_business,
)
from app.devices.bridge_schemas import (
    DeviceEventRequest,
    DeviceStatusRequest,
    PairDeviceRequest,
    PairingCodeRequest,
)
from app.devices.bridge_service import DEVICE_BRIDGE_SERVICE
from app.payments.intelligence.dashboard import get_payment_dashboard

router = APIRouter(prefix="/device-bridge", tags=["Device Bridge"])


@router.post("/pairing-codes", status_code=status.HTTP_201_CREATED)
def create_pairing_code_route(
    payload: PairingCodeRequest | None = None,
    business_id: int = Depends(require_user_or_device_business),
    db: Session = Depends(get_db),
):
    """Mint a pairing code for the CALLER'S OWN business.

    A seller with no paired device at all cannot use this path; the intended
    first-device flow is registration (any future registration endpoint can
    return a code) or a user JWT with `?business_id=`.
    """
    check_rate_limit(db, f"business:{business_id}", "pairing-create", 10, 300)
    result = DEVICE_BRIDGE_SERVICE.create_pairing_code(db, business_id, user_id=None)
    return result


@router.post("/devices", status_code=status.HTTP_201_CREATED)
def pair_device_route(payload: PairDeviceRequest, request: Request, db: Session = Depends(get_db)):
    """Exchange a pairing code for a device token.

    Deliberately unauthenticated: the one-time 60-second code IS the grant.
    Rate limited per client because this is the endpoint an attacker would
    brute-force; all failure modes return the same 404.
    """
    check_rate_limit(
        db,
        f"ip:{request.client.host if request.client else 'unknown'}",
        "pairing-redeem",
        30,
        60,
    )
    return DEVICE_BRIDGE_SERVICE.pair_device(db, payload.pairing_code, payload.device_name)


@router.post("/status")
def update_device_status_route(
    payload: DeviceStatusRequest,
    principal: DevicePrincipal = Depends(require_device_principal),
    db: Session = Depends(get_db),
):
    check_rate_limit(db, f"device:{principal.device.id}", "bridge-status", 60, 60)
    return DEVICE_BRIDGE_SERVICE.update_device_status(
        db, principal.device, payload.sms_permission_granted, payload.monitoring_active
    )


@router.get("/dashboard")
def payment_dashboard_route(
    principal: DevicePrincipal = Depends(require_device_principal),
    db: Session = Depends(get_db),
    timezone_name: str = Query("Asia/Dhaka", alias="timezone", min_length=1, max_length=64),
    search: str | None = Query(None, max_length=128),
    provider: str | None = Query(None, pattern=r"^(bkash|nagad|rocket|upay)$"),
    payment_status: str | None = Query(None, alias="status", max_length=32),
    from_timestamp: datetime | None = Query(None, alias="from"),
    to_timestamp: datetime | None = Query(None, alias="to"),
    sort: str = Query("newest", pattern=r"^(newest|oldest)$"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return get_payment_dashboard(
        db,
        business_id=principal.business_id,
        device=principal.device,
        timezone_name=timezone_name,
        search=search,
        provider=provider,
        payment_status=payment_status,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
def ingest_event_route(
    payload: DeviceEventRequest,
    principal: DevicePrincipal = Depends(require_device_principal),
    db: Session = Depends(get_db),
):
    check_rate_limit(db, f"device:{principal.device.id}", "bridge-events", 240, 60)
    result = DEVICE_BRIDGE_SERVICE.ingest_device_event(db, principal.device, payload)
    if result.get("status") == "duplicate":
        return JSONResponse(status_code=200, content=result)
    return JSONResponse(status_code=202, content=result)


@router.get("/devices")
def list_devices_route(
    business_id: int = Depends(require_user_or_device_business),
    db: Session = Depends(get_db),
):
    return DEVICE_BRIDGE_SERVICE.list_devices(db, business_id)
