import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.db.base import User, Business
from app.auth.schemas import (
    UserCreate, UserRead, UserLogin, Token, RegisterResponse,
    UserUpdate, PasscodeChange,
)
from app.auth.service import get_user_by_email, create_user, authenticate_user
from app.core.config import settings
from app.core.rate_limit import check_rate_limit
from app.core.security import create_access_token, get_password_hash, verify_password
from app.auth.dependencies import get_current_user
from app.payments.models import PaymentAccount
from app.utils.phone import normalize_phone

router = APIRouter(prefix="/auth", tags=["Authentication"])

LOCAL_PAYMENT_PROVIDERS = {"bkash", "nagad", "rocket", "upay"}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _upsert_payment_account(
    db: Session, business: Business | None, provider: str | None, receiving_number: str | None
) -> None:
    """Keep `payment_accounts` in sync with the registration/profile fields.

    This is the bridge between the mobile client's simple fields and the
    canonical receiving-account model used by payment detection.
    """
    if business is None or not receiving_number:
        return
    provider_value = (provider or "").strip().lower()
    if provider_value not in LOCAL_PAYMENT_PROVIDERS:
        return
    try:
        number = normalize_phone(receiving_number)
    except ValueError:
        return
    if not number:
        return

    account = (
        db.query(PaymentAccount)
        .filter(
            PaymentAccount.business_id == business.id,
            PaymentAccount.provider == provider_value,
        )
        .first()
    )
    if account is None:
        db.add(
            PaymentAccount(
                business_id=business.id,
                provider=provider_value,
                receiving_number=number,
                status="configured",
                mode="live",
            )
        )
    else:
        account.receiving_number = number
        account.status = "configured"
    db.commit()


@router.get("/test", response_model=dict)
async def test_connection():
    """Simple test endpoint to verify backend connectivity"""
    return {
        "status": "ok",
        "message": "Backend connection successful!",
        "api_version": "0.8.0"
    }

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    # Rate limit first: unauthenticated endpoint.
    check_rate_limit(db, f"ip:{_client_ip(request)}", "register", 5, 3600)

    # Optional invite gate. When the server has REGISTRATION_INVITE_CODE set,
    # a matching code is required; comparison is constant-time.
    expected_invite = (settings.registration_invite_code or "").strip()
    if expected_invite:
        provided = (user_data.invite_code or "").strip()
        if not hmac.compare_digest(provided.encode(), expected_invite.encode()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is invitation-only.",
            )

    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user, business = create_user(db, user_data)
    _upsert_payment_account(db, business, user_data.payment_provider, user_data.receiving_number)
    return RegisterResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        business_id=business.id if business else None,
        business_name=business.name if business else None,
    )

@router.post("/login", response_model=Token)
def login_user(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(
        db, f"login:{_client_ip(request)}:{user_data.email.lower()}", "login", 10, 900
    )
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect passcode",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(data={"sub": str(user.id)}), "token_type": "bearer"}

def _user_read(current_user: User) -> UserRead:
    business = None
    if current_user.memberships:
        business = current_user.memberships[0].business
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        payment_provider=current_user.payment_provider,
        receiving_number=current_user.receiving_number,
        business=business,
    )

@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    return _user_read(current_user)

@router.put("/me", response_model=UserRead)
def update_users_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.phone is not None:
        current_user.phone = user_data.phone
    if user_data.payment_provider is not None:
        current_user.payment_provider = user_data.payment_provider
    if user_data.receiving_number is not None:
        current_user.receiving_number = user_data.receiving_number

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    business = current_user.memberships[0].business if current_user.memberships else None
    _upsert_payment_account(
        db, business, current_user.payment_provider, current_user.receiving_number
    )
    return _user_read(current_user)

@router.post("/passcode/change", response_model=dict)
def change_passcode(
    user_data: PasscodeChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(user_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current passcode is incorrect",
        )
    current_user.hashed_password = get_password_hash(user_data.new_password)
    db.add(current_user)
    db.commit()
    return {"status": "ok", "message": "Passcode updated"}
