"""Request schemas for the device bridge (contract-compatible with System A)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PairingCodeRequest(BaseModel):
    """Intentionally has no fields.

    The tenant is derived from the caller's credential, never from the body.
    `extra="forbid"` makes a client that still sends `business_id` receive an
    explicit 422 rather than a silently ignored value.
    """

    model_config = ConfigDict(extra="forbid")


class PairDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pairing_code: str = Field(max_length=128)
    device_name: str = Field(min_length=1, max_length=128)


class DeviceStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sms_permission_granted: bool
    monitoring_active: bool


class DeviceEventRequest(BaseModel):
    """A normalized payment event produced by the Android bridge.

    Note: `message_text` may be sent by clients but is never stored; only the
    fact that a message body was present is recorded (`message_text_present`).
    """

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(pattern=r"^bkash$")
    amount: str
    transaction_id: str = Field(min_length=1, max_length=255)
    sender_identifier: str | None = None
    receiver_identifier: str | None = None
    currency: str = "BDT"
    timestamp: str
    source: str = "android_notification"
    notification_package: str | None = None
    message_text: str | None = None


class PaymentAccountConnectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=32)
    receiving_number: str = Field(min_length=3, max_length=50)
    account_type: str = Field(default="personal", pattern=r"^(personal|merchant)$")
