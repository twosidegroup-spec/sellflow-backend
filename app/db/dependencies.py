from collections.abc import Generator
from sqlalchemy.orm import Session
from app.db.engine import SessionLocal

def get_db() -> Generator[Session, None, None]:
    '''
    FastAPI dependency to get a database session.
    Yields a session and ensures it is closed after the request.
    '''
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
