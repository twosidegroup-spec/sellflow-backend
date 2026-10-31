"""Authentication dependencies for the device bridge.

One coherent strategy (documented in `CANONICAL_ARCHITECTURE.md`):

* Users authenticate with JWT and act on their own businesses (membership).
* Paired devices authenticate with `X-Device-Token`; the token resolves to the
  device row and to exactly one business. Device tokens are only issued by
  redeeming a 60-second, single-use pairing code created by an authenticated
  user (or an already-paired device) of that business.

Both fail closed: a missing or invalid credential is a 401, never a default
tenant.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.security import decode_access_token
from app.db.base import Membership
from app.db.dependencies import get_db
from app.devices.bridge_service import DEVICE_BRIDGE_SERVICE
from app.devices.models import Device

_oauth2_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False
)


@dataclass(frozen=True)
class DevicePrincipal:
    device: Device
    business_id: int


def _optional_user(
    token: str | None = Depends(_oauth2_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """The JWT user when a valid Bearer token is present, else None."""
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == int(user_id)).first()


def require_device_principal(
    x_device_token: str | None = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db),
) -> DevicePrincipal:
    """A paired device and its tenant. Fails closed on any missing/invalid token."""
    if not x_device_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This request needs a device token.",
        )
    device = DEVICE_BRIDGE_SERVICE.verify_device_token(db, x_device_token)
    if device.business_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That device is not attached to a business.",
        )
    return DevicePrincipal(device=device, business_id=int(device.business_id))


def require_user_or_device_business(
    business_id: int | None = Query(
        None,
        description=(
            "Required when authenticating with a user JWT instead of a paired "
            "device token; must be a business the user is a member of."
        ),
    ),
    x_device_token: str | None = Header(None, alias="X-Device-Token"),
    current_user: User | None = Depends(_optional_user),
    db: Session = Depends(get_db),
) -> int:
    """The tenant for endpoints both seller users and paired devices call.

    Device token wins (tenant from the device row). Otherwise the caller must
    be a JWT user AND a member of the explicit `business_id`.
    """
    if x_device_token:
        device = DEVICE_BRIDGE_SERVICE.verify_device_token(db, x_device_token)
        if device.business_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="That device is not attached to a business.",
            )
        return int(device.business_id)

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    if business_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="business_id is required when authenticating as a user.",
        )
    membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == current_user.id,
            Membership.business_id == business_id,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this business",
        )
    return int(business_id)
