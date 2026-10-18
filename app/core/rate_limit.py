from datetime import datetime, timedelta, timezone
from sqlalchemy import String, DateTime, func, delete
from sqlalchemy.orm import Mapped, mapped_column
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.engine import Base

class RateLimitEvent(Base):
    __tablename__ = "rate_limit_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    hit_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

def check_rate_limit(db: Session, identifier: str, endpoint: str, max_requests: int, window_seconds: int):
    window_start = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    
    db.execute(
        delete(RateLimitEvent).where(
            RateLimitEvent.identifier == identifier,
            RateLimitEvent.endpoint == endpoint,
            RateLimitEvent.hit_at < window_start
        )
    )
    db.commit()
    
    count = db.query(RateLimitEvent).filter(
        RateLimitEvent.identifier == identifier,
        RateLimitEvent.endpoint == endpoint,
        RateLimitEvent.hit_at >= window_start
    ).count()
    
    if count >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."
        )
    
    new_event = RateLimitEvent(identifier=identifier, endpoint=endpoint)
    db.add(new_event)
    db.commit()
