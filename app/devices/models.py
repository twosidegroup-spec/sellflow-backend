from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.engine import Base


class Device(Base):
    """
    Tracks devices (mobile clients) that connect to the application.
    Used for push notification targeting and device management.
    """
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=True)
    
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)  # android, ios, web
    app_version: Mapped[str] = mapped_column(String(50), nullable=True)
    push_token: Mapped[str] = mapped_column(String(512), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_devices_user_active", "user_id", "is_active"),
        Index("ix_devices_business_active", "business_id", "is_active"),
    )

    user = relationship("User", back_populates="devices")
    business = relationship("Business", back_populates="devices")
