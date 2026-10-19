from datetime import datetime
from sqlalchemy.orm import Session
from app.db.base import Device


def get_device(db: Session, device_id: int) -> Device | None:
    """Get a device by ID."""
    return db.query(Device).filter(Device.id == device_id).first()


def get_device_by_id(db: Session, device_id: str) -> Device | None:
    """Get a device by its device_id string."""
    return db.query(Device).filter(Device.device_id == device_id).first()


def create_device(db: Session, user_id: int | None, business_id: int | None, 
                  device_id: str, device_type: str,
                  app_version: str | None = None, 
                  push_token: str | None = None) -> Device:
    """Create a new device record."""
    device = Device(
        device_id=device_id,
        device_type=device_type,
        app_version=app_version,
        push_token=push_token,
        user_id=user_id,
        business_id=business_id,
        is_active=True,
        last_active=datetime.now(),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def update_device(db: Session, device_id: int, **kwargs) -> Device | None:
    """Update device information."""
    device = get_device(db, device_id)
    if not device:
        return None
    
    for key, value in kwargs.items():
        if hasattr(device, key):
            setattr(device, key, value)
    
    db.commit()
    db.refresh(device)
    return device


def deactivate_device(db: Session, device_id: int) -> bool:
    """Deactivate a device (soft delete)."""
    device = get_device(db, device_id)
    if not device:
        return False
    
    device.is_active = False
    db.commit()
    return True


def get_active_devices_for_user(db: Session, user_id: int) -> list[Device]:
    """Get all active devices for a user."""
    return db.query(Device).filter(
        Device.user_id == user_id,
        Device.is_active == True
    ).all()


def get_active_devices_for_business(db: Session, business_id: int) -> list[Device]:
    """Get all active devices for a business."""
    return db.query(Device).filter(
        Device.business_id == business_id,
        Device.is_active == True
    ).all()


def update_push_token(db: Session, device_id: str, push_token: str) -> bool:
    """Update the push token for a device."""
    device = get_device_by_id(db, device_id)
    if not device:
        return False
    
    device.push_token = push_token
    db.commit()
    return True
