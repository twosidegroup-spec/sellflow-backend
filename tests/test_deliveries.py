from fastapi.testclient import TestClient
from app.main import app
from app.db.engine import SessionLocal
from app.db.base import User, Business, Membership, Product, Order, OrderItem, Delivery
from app.businesses.models import MembershipRole
from app.core.security import get_password_hash
from app.deliveries.models import DeliveryStatus

client = TestClient(app)

def _setup_test_environment():
    '''Helper to create a clean test environment with a user, business, and order.'''
    db = SessionLocal()
    
    # Clean up
    db.query(Delivery).delete()
    db.query(OrderItem).delete()
    db.query(Order).delete()
    db.query(Product).delete()
    db.query(Membership).delete()
    db.query(Business).delete()
    db.query(User).delete()
    db.commit()
    
    # Create user and business
    user = User(email="seller@sellflow.com", full_name="Seller", hashed_password=get_password_hash("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    business = Business(name="Test Business", slug="test-business")
    db.add(business)
    db.commit()
    db.refresh(business)
    
    # Create membership
    db.add(Membership(user_id=user.id, business_id=business.id, role=MembershipRole.OWNER))
    db.commit()
    
    # Create an order
    order = Order(
        business_id=business.id,
        total_amount=100.00,
        total_cost=40.00,
        gross_profit=60.00,
        delivery_fee=0.00,
        discount=0.00
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Extract IDs before closing session
    user_id = user.id
    business_id = business.id
    order_id = order.id
    
    db.close()
    
    # Get auth token
    response = client.post("/api/v1/auth/login", json={"email": "seller@sellflow.com", "password": "password123"})
    token = response.json()["access_token"]
    
    return user_id, business_id, order_id, token


def test_create_and_update_delivery():
    '''Proves that a delivery can be created and its status updated with auto-timestamps.'''
    _, business_id, order_id, token = _setup_test_environment()
    
    # 1. Create delivery
    delivery_payload = {
        "courier": "Pathao",
        "tracking_number": "PT-123456789",
        "delivery_fee": "60.00"
    }
    
    response = client.post(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/delivery/",
        json=delivery_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["courier"] == "Pathao"
    assert data["tracking_number"] == "PT-123456789"
    assert float(data["delivery_fee"]) == 60.00
    assert data["status"] == "pending"
    assert data["order_id"] == order_id
    
    delivery_id = data["id"]
    
    # 2. Update delivery status to 'picked_up'
    update_payload = {"status": "picked_up"}
    response = client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/delivery/",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "picked_up"
    assert response.json()["shipped_at"] is not None
    
    # 3. Update delivery status to 'delivered'
    update_payload = {"status": "delivered"}
    response = client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/delivery/",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"
    assert response.json()["delivered_at"] is not None


def test_prevent_duplicate_delivery():
    '''Proves that an order can only have one delivery record.'''
    _, business_id, order_id, token = _setup_test_environment()
    
    # Create first delivery
    response1 = client.post(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/delivery/",
        json={"courier": "Pathao", "tracking_number": "PT-111", "delivery_fee": "60.00"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response1.status_code == 201
    
    # Try to create second delivery for the same order
    response2 = client.post(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/delivery/",
        json={"courier": "Steadfast", "tracking_number": "SF-222", "delivery_fee": "50.00"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


def test_delivery_tenant_isolation():
    '''Proves that User B cannot access or modify User A's deliveries.'''
    db = SessionLocal()
    
    # Clean up
    db.query(Delivery).delete()
    db.query(OrderItem).delete()
    db.query(Order).delete()
    db.query(Product).delete()
    db.query(Membership).delete()
    db.query(Business).delete()
    db.query(User).delete()
    db.commit()
    
    # Create User A and Business A
    user_a = User(email="userA@sellflow.com", full_name="User A", hashed_password=get_password_hash("password123"))
    db.add(user_a)
    db.commit()
    db.refresh(user_a)
    
    business_a = Business(name="Business A", slug="business-a")
    db.add(business_a)
    db.commit()
    db.refresh(business_a)
    
    db.add(Membership(user_id=user_a.id, business_id=business_a.id, role=MembershipRole.OWNER))
    
    order_a = Order(business_id=business_a.id, total_amount=100.00, total_cost=40.00, gross_profit=60.00)
    db.add(order_a)
    db.commit()
    db.refresh(order_a)
    
    # Create User B and Business B
    user_b = User(email="userB@sellflow.com", full_name="User B", hashed_password=get_password_hash("password123"))
    db.add(user_b)
    db.commit()
    db.refresh(user_b)
    
    business_b = Business(name="Business B", slug="business-b")
    db.add(business_b)
    db.commit()
    db.refresh(business_b)
    
    db.add(Membership(user_id=user_b.id, business_id=business_b.id, role=MembershipRole.OWNER))
    db.commit()
    
    business_a_id = business_a.id
    business_b_id = business_b.id
    order_a_id = order_a.id
    db.close()
    
    # Get tokens
    token_a = client.post("/api/v1/auth/login", json={"email": "userA@sellflow.com", "password": "password123"}).json()["access_token"]
    token_b = client.post("/api/v1/auth/login", json={"email": "userB@sellflow.com", "password": "password123"}).json()["access_token"]
    
    # User A creates a delivery
    response = client.post(
        f"/api/v1/businesses/{business_a_id}/orders/{order_a_id}/delivery/",
        json={"courier": "Pathao", "tracking_number": "PT-999", "delivery_fee": "60.00"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert response.status_code == 201
    
    # CRITICAL: User B tries to get User A's delivery (should fail with 403)
    response = client.get(
        f"/api/v1/businesses/{business_a_id}/orders/{order_a_id}/delivery/",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403, "Tenant isolation FAILED: User B could access Business A's delivery!"
    
    # CRITICAL: User B tries to update User A's delivery (should fail with 403)
    response = client.patch(
        f"/api/v1/businesses/{business_a_id}/orders/{order_a_id}/delivery/",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403, "Tenant isolation FAILED: User B could update Business A's delivery!"
