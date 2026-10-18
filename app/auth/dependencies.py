from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.db.base import User
from app.core.security import decode_access_token

# This tells FastAPI to expect a "Bearer <token>" in the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. Decode and verify the token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    # 2. Extract the user ID from the token payload
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    # 3. Fetch the user from the database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
        
    return user
