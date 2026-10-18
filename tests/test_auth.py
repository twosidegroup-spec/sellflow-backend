from fastapi.testclient import TestClient
from app.main import app
from app.db.engine import SessionLocal
from app.db.base import User

client = TestClient(app)

def test_register_user():
    # Clean up first to avoid duplicate email errors
    db = SessionLocal()
    db.query(User).filter(User.email == "register@sellflow.com").delete()
    db.commit()
    db.close()

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "register@sellflow.com", "full_name": "Register Test", "password": "secretpass123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "register@sellflow.com"
    assert "id" in data

def test_login_user():
    # Ensure user exists
    db = SessionLocal()
    db.query(User).filter(User.email == "login@sellflow.com").delete()
    db.commit()
    
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@sellflow.com", "full_name": "Login Test", "password": "secretpass123"}
    )
    db.close()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@sellflow.com", "password": "secretpass123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@sellflow.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_get_current_user_protected_route():
    # 1. Register and login to get a valid token
    client.post(
        "/api/v1/auth/register",
        json={"email": "protected@sellflow.com", "full_name": "Protected Test", "password": "secretpass123"}
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "protected@sellflow.com", "password": "secretpass123"}
    )
    token = login_response.json()["access_token"]

    # 2. Access protected route WITH valid token (Should succeed)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "protected@sellflow.com"

    # 3. Access protected route WITHOUT token (Should fail with 401)
    response_no_auth = client.get("/api/v1/auth/me")
    assert response_no_auth.status_code == 401

    # 4. Access protected route WITH invalid token (Should fail with 401)
    response_bad_auth = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"}
    )
    assert response_bad_auth.status_code == 401
