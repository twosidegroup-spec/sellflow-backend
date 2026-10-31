from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.engine import Base


class Device(Base):
    """
    Tracks devices (mobile clients) that connect to the application.

    Extended by the System A -> System B migration with device-bridge fields:
    paired devices authenticate the payment bridge with an HMAC-hashed token
    (`device_token_hash`), report SMS permission/monitoring state, and are
    tied to the seller (`user_id`) and tenant (`business_id`).
    """

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=True)

    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    app_version: Mapped[str] = mapped_column(String(50), nullable=True)
    push_token: Mapped[str] = mapped_column(String(512), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- device bridge (migrated from System A) ---
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    pairing_code_id: Mapped[int | None] = mapped_column(
        ForeignKey("device_pairing_codes.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="paired", nullable=False)
    sms_permission_granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    monitoring_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_devices_user_active", "user_id", "is_active"),
        Index("ix_devices_business_active", "business_id", "is_active"),
    )

    user = relationship("User", back_populates="devices")
    business = relationship("Business", back_populates="devices")


class DevicePairingCode(Base):
    """One-time pairing codes (60-second expiry) for the Android payment bridge.

    Migrated from System A's `device_pairing_codes` table. The code is stored
    only as an HMAC hash; the plaintext is returned once to the seller.
    """

    __tablename__ = "device_pairing_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    code_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_device_pairing_codes_business", "business_id", "expires_at"),
    )
