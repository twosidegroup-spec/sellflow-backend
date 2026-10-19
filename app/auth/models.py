from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.engine import Base
from app.devices.models import Device


def check_membership_role(user_id: int, business_id: int, role: str) -> bool:
    """Check if user has a specific role in a business."""
    from app.db.base import Membership
    from app.db.engine import SessionLocal
    
    db = SessionLocal()
    try:
        membership = db.query(Membership).filter(
            Membership.user_id == user_id,
            Membership.business_id == business_id
        ).first()
        return membership is not None and membership.role.value == role
    finally:
        db.close()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")

    def is_owner(self, business_id: int) -> bool:
        """Check if user is owner of the specified business."""
        return check_membership_role(self.id, business_id, "owner")

    def is_admin(self, business_id: int) -> bool:
        """Check if user is admin or owner of the specified business."""
        return check_membership_role(self.id, business_id, "admin") or check_membership_role(self.id, business_id, "owner")

    def is_member(self, business_id: int) -> bool:
        """Check if user is any type of member of the specified business."""
        from app.db.base import Membership
        from app.db.engine import SessionLocal
        
        db = SessionLocal()
        try:
            membership = db.query(Membership).filter(
                Membership.user_id == self.id,
                Membership.business_id == business_id
            ).first()
            return membership is not None
        finally:
            db.close()
