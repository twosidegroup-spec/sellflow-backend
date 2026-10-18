from fastapi.testclient import TestClient
from app.main import app
from app.db.engine import SessionLocal
from app.db.base import User, RateLimitEvent
from app.core.security import get_password_hash
from sqlalchemy import delete

client = TestClient(app)

def test_login_rate_limit():
    db = SessionLocal()
    
    db.execute(delete(RateLimitEvent).where(RateLimitEvent.endpoint == "login"))
    db.commit()
    
    db.query(User).filter(User.email == "ratelimit@sellflow.com").delete()
    db.commit()
    
    user = User(email="ratelimit@sellflow.com", full_name="Rate Limit User", hashed_password=get_password_hash("correctpassword"))
    db.add(user)
    db.commit()
    db.close()
    
    for i in range(10):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "ratelimit@sellflow.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401, f"Attempt {i+1} should be 401"
    
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit@sellflow.com", "password": "wrongpassword"}
    )
    assert response.status_code == 429, "11th attempt should be rate limited (429)"
    assert "Rate limit exceeded" in response.json()["detail"]
    
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit@sellflow.com", "password": "correctpassword"}
    )
    assert response.status_code == 429, "Correct password should still be blocked by rate limit"
