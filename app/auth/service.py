from uuid import uuid4
from sqlalchemy.orm import Session
from app.db.base import User, Business, Membership
from app.businesses.models import MembershipRole
from app.auth.schemas import UserCreate
from app.core.security import get_password_hash, verify_password

def _slugify(name: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")[:40]
    return slug or "business"

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_data: UserCreate) -> tuple[User, Business | None]:
    db_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        phone=user_data.phone,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(db_user)
    db.flush()

    business = None
    if user_data.business_name:
        business = Business(
            name=user_data.business_name,
            slug=f"{_slugify(user_data.business_name)}-{uuid4().hex[:6]}",
        )
        db.add(business)
        db.flush()
        db.add(Membership(user_id=db_user.id, business_id=business.id, role=MembershipRole.OWNER))

    db.commit()
    db.refresh(db_user)
    return db_user, business

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
