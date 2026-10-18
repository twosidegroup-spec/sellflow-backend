from fastapi.testclient import TestClient
from app.main import app
from app.db.engine import SessionLocal
from app.db.base import User, Business, Membership, Product
from app.businesses.models import MembershipRole
from app.core.security import get_password_hash

client = TestClient(app)

def test_tenant_isolation_user_cannot_access_other_business():
    '''CRITICAL TEST: Proves Business A cannot see Business B's products.'''
    db = SessionLocal()
    
    # 1. Clean up first
    db.query(Product).delete()
    db.query(Membership).delete()
    db.query(Business).delete()
    db.query(User).delete()
    db.commit()
    
    # 2. Create User A and User B
    user_a = User(email="userA@sellflow.com", full_name="User A", hashed_password=get_password_hash("password123"))
    user_b = User(email="userB@sellflow.com", full_name="User B", hashed_password=get_password_hash("password123"))
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)
    
    # 3. Create Business A and Business B
    business_a = Business(name="Business A", slug="business-a")
    business_b = Business(name="Business B", slug="business-b")
    db.add_all([business_a, business_b])
    db.commit()
    db.refresh(business_a)
    db.refresh(business_b)
    
    # 4. CRITICAL: Extract IDs to local variables BEFORE closing the session
    user_a_id = user_a.id
    user_b_id = user_b.id
    business_a_id = business_a.id
    business_b_id = business_b.id
    
    # 5. Create Memberships
    db.add_all([
        Membership(user_id=user_a_id, business_id=business_a_id, role=MembershipRole.OWNER),
        Membership(user_id=user_b_id, business_id=business_b_id, role=MembershipRole.OWNER)
    ])
    db.commit()
    db.close()
    
    # 6. Get tokens for both users
    response_a = client.post("/api/v1/auth/login", json={"email": "userA@sellflow.com", "password": "password123"})
    token_a = response_a.json()["access_token"]
    
    response_b = client.post("/api/v1/auth/login", json={"email": "userB@sellflow.com", "password": "password123"})
    token_b = response_b.json()["access_token"]
    
    # 7. User A creates a product in Business A
    response = client.post(
        f"/api/v1/businesses/{business_a_id}/products/",
        json={"name": "Secret Product A", "sku": "SKU-A-001", "cost_price": "10.00", "selling_price": "20.00"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert response.status_code == 201
    product_a_id = response.json()["id"]
    
    # 8. CRITICAL: User B tries to list User A's products (should fail with 403)
    response = client.get(
        f"/api/v1/businesses/{business_a_id}/products/",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403, "Tenant isolation FAILED: User B could access Business A's products!"
    
    # 9. CRITICAL: User B tries to get specific product from Business A (should fail with 403)
    response = client.get(
        f"/api/v1/businesses/{business_a_id}/products/{product_a_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403, "Tenant isolation FAILED: User B could view Business A's product!"
    
    # 10. CRITICAL: User B tries to create a product in Business A (should fail with 403)
    response = client.post(
        f"/api/v1/businesses/{business_a_id}/products/",
        json={"name": "Malicious Product", "sku": "SKU-MAL", "cost_price": "1.00", "selling_price": "2.00"},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403, "Tenant isolation FAILED: User B could create in Business A!"
    
    # 11. User B CAN access their own Business B (should succeed)
    response = client.get(
        f"/api/v1/businesses/{business_b_id}/products/",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 200
    assert response.json() == []  # Empty because User B hasn't created anything


def test_user_can_access_own_business_products():
    '''Proves a user can successfully manage their own business data.'''
    db = SessionLocal()
    
    # Clean up first
    db.query(Product).delete()
    db.query(Membership).delete()
    db.query(Business).delete()
    db.query(User).delete()
    db.commit()
    
    # Create user, business, and membership
    user = User(email="owner@sellflow.com", full_name="Owner", hashed_password=get_password_hash("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    business = Business(name="Owner Business", slug="owner-business")
    db.add(business)
    db.commit()
    db.refresh(business)
    
    # CRITICAL: Extract IDs to local variables BEFORE closing the session
    user_id = user.id
    business_id = business.id
    
    db.add(Membership(user_id=user_id, business_id=business_id, role=MembershipRole.OWNER))
    db.commit()
    db.close()
    
    # Get token
    response = client.post("/api/v1/auth/login", json={"email": "owner@sellflow.com", "password": "password123"})
    token = response.json()["access_token"]
    
    # Create a product
    response = client.post(
        f"/api/v1/businesses/{business_id}/products/",
        json={"name": "My Product", "sku": "SKU-OWN-001", "cost_price": "5.50", "selling_price": "15.00", "stock_quantity": 100},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    product_id = response.json()["id"]
    
    # List products
    response = client.get(f"/api/v1/businesses/{business_id}/products/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # Update product
    response = client.put(
        f"/api/v1/businesses/{business_id}/products/{product_id}",
        json={"selling_price": "18.00"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert str(response.json()["selling_price"]) == "18.00"
    
    # Delete product
    response = client.delete(f"/api/v1/businesses/{business_id}/products/{product_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204


def test_unauthenticated_access_rejected():
    '''Proves that requests without a token are rejected.'''
    response = client.get("/api/v1/businesses/1/products/")
    assert response.status_code == 401
