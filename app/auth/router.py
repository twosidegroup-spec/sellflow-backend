from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.db.base import User
from app.auth.schemas import (
    UserCreate, UserRead, UserLogin, Token, RegisterResponse,
    UserUpdate, PasscodeChange,
)
from app.auth.service import get_user_by_email, create_user, authenticate_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/test", response_model=dict)
async def test_connection():
    """Simple test endpoint to verify backend connectivity"""
    return {
        "status": "ok",
        "message": "Backend connection successful!",
        "api_version": "0.8.0"
    }

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user, business = create_user(db, user_data)
    return RegisterResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        business_id=business.id if business else None,
        business_name=business.name if business else None,
    )

@router.post("/login", response_model=Token)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
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
