from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.db.base import User
from app.auth.schemas import UserCreate, UserRead, UserLogin, Token, RegisterResponse
from app.auth.service import get_user_by_email, create_user, authenticate_user
from app.core.security import create_access_token
from app.auth.dependencies import get_current_user
from app.core.rate_limit import check_rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/test", response_model=dict)
async def test_connection():
    """Simple test endpoint to verify backend connectivity"""
    return {
        "status": "ok",
        "message": "Backend connection successful!",
        "api_version": "0.8.0"
    }

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_user(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    client_ip = get_client_ip(request)
    check_rate_limit(db, identifier=client_ip, endpoint="register", max_requests=5, window_seconds=3600)

    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user, business = create_user(db, user_data)
    return RegisterResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        business_id=business.id if business else None,
        business_name=business.name if business else None,
    )

@router.post("/login", response_model=Token)
def login_user(request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    check_rate_limit(db, identifier=user_data.email, endpoint="login", max_requests=10, window_seconds=900)

    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect passcode",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(data={"sub": str(user.id)}), "token_type": "bearer"}

@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
