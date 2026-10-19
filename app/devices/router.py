from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business
from app.devices.models import Device
from app.devices.schemas import DeviceCreate, DeviceUpdate, DeviceRead, ActiveDevicesResponse
from app.auth.dependencies import get_current_user
from app.auth.models import User
from datetime import datetime

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def register_device(
    device_data: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
    current_business: Business | None = Depends(get_current_business),
):
    """
    Register a new device for push notifications and tracking.
    Device is automatically associated with current user/business if authenticated.
    """
    # Check if device already exists
    existing = db.query(Device).filter(
        Device.device_id == device_data.device_id
    ).first()

    if existing:
        # Update last_active and push_token if provided
        existing.last_active = datetime.now()
        if device_data.push_token:
            existing.push_token = device_data.push_token
        if device_data.app_version:
            existing.app_version = device_data.app_version
        db.commit()
        db.refresh(existing)
        return existing

    device = Device(
        device_id=device_data.device_id,
        device_type=device_data.device_type,
        app_version=device_data.app_version,
        push_token=device_data.push_token,
        user_id=current_user.id if current_user else None,
        business_id=current_business.id if current_business else None,
        is_active=True,
    )

    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/", response_model=ActiveDevicesResponse)
def list_active_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all active devices for the current user.
    Used for device management and push notification targeting.
    """
    devices = db.query(Device).filter(
        Device.user_id == current_user.id,
        Device.is_active == True
    ).all()

    return ActiveDevicesResponse(
        count=len(devices),
        devices=devices,
    )


@router.put("/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: int,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update device information.
    Used for updating push tokens and app versions.
    """
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.user_id == current_user.id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    if device_data.app_version is not None:
        device.app_version = device_data.app_version
    if device_data.push_token is not None:
        device.push_token = device_data.push_token
    if device_data.is_active is not None:
        device.is_active = device_data.is_active

    db.commit()
    db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deactivate a device (soft delete).
    Used when user logs out or switches devices.
    """
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.user_id == current_user.id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    device.is_active = False
    db.commit()
