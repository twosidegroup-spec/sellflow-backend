from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.engine import Base, SessionLocal
from app.devices.models import Device

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sqlalchemy.orm import Session


def _has_role(user_id: int, business_id: int, role: str, db: "Session | None" = None) -> bool:
    """True when the user has exactly `role` in the business.

    Uses the caller's session when provided (the route handlers pass theirs);
    otherwise opens a short-lived session. The previous signature mismatch
    (`is_owner(business_id, db)` called with two positional arguments against a
    one-argument method) crashed every membership-management endpoint; the
    optional `db` parameter now matches both call styles.
    """
    from app.db.base import Membership

    owns_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        membership = (
            db.query(Membership)
            .filter(
                Membership.user_id == user_id,
                Membership.business_id == business_id,
            )
            .first()
        )
        if membership is None:
            return False
        raw_role = getattr(membership.role, "value", membership.role)
        return str(raw_role) == role
    finally:
        if owns_session:
            db.close()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    receiving_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")

    def is_owner(self, business_id: int, db: "Session | None" = None) -> bool:
        """Check if user is owner of the specified business."""
        return _has_role(self.id, business_id, "owner", db)

    def is_admin(self, business_id: int, db: "Session | None" = None) -> bool:
        """Check if user is admin or owner of the specified business."""
        return _has_role(self.id, business_id, "admin", db) or _has_role(
            self.id, business_id, "owner", db
        )

    def is_member(self, business_id: int, db: "Session | None" = None) -> bool:
        """Check if user is any type of member of the specified business."""
        from app.db.base import Membership

        owns_session = db is None
        if db is None:
            db = SessionLocal()
        try:
            membership = (
                db.query(Membership)
                .filter(
                    Membership.user_id == self.id,
                    Membership.business_id == business_id,
                )
                .first()
            )
            return membership is not None
        finally:
            if owns_session:
                db.close()
