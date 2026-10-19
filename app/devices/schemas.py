from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class DeviceBase(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=255)
    device_type: str = Field(..., min_length=1, max_length=50)  # android, ios, web
    app_version: Optional[str] = Field(None, max_length=50)
    push_token: Optional[str] = Field(None, max_length=512)


class DeviceCreate(DeviceBase):
    user_id: Optional[int] = None
    business_id: Optional[int] = None


class DeviceUpdate(BaseModel):
    app_version: Optional[str] = Field(None, max_length=50)
    push_token: Optional[str] = Field(None, max_length=512)
    is_active: Optional[bool] = None


class DeviceRead(BaseModel):
    id: int
    device_id: str
    device_type: str
    app_version: Optional[str]
    push_token: Optional[str]
    is_active: bool
    created_at: datetime
    last_active: datetime

    model_config = ConfigDict(from_attributes=True)


class ActiveDevicesResponse(BaseModel):
    count: int
    devices: list[DeviceRead] = []

    model_config = ConfigDict(from_attributes=True)
