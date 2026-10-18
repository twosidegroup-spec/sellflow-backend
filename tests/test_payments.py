from fastapi.testclient import TestClient
from app.main import app
from app.db.engine import SessionLocal
from app.db.base import User, Business, Membership, Product, Order, OrderItem, Payment
from app.businesses.models import MembershipRole
from app.core.security import get_password_hash

client = TestClient(app)

def _setup_test_environment():
    '''Helper to create a clean test environment with a user, business, product, and order.'''
    db = SessionLocal()
    
    # Clean up
    db.query(Payment).delete()
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
    
    # Create a product
    product = Product(
        business_id=business.id,
        name="Test Product",
        sku="TEST-001",
        cost_price=10.00,
        selling_price=25.00,
        stock_quantity=100
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Create an order
    order = Order(
        business_id=business.id,
        total_amount=100.00,
        total_cost=40.00,
        gross_profit=60.00,
        delivery_fee=5.00,
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


def test_record_payment_successfully():
    '''Proves that a payment can be recorded for an order.'''
    _, business_id, order_id, token = _setup_test_environment()
    
    payment_payload = {
        "amount": "100.00",
        "method": "bkash",
        "transaction_id": "TXN123456",
        "notes": "Payment received via bKash"
    }
    
    response = client.post(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/payments/",
        json=payment_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    assert float(data["amount"]) == 100.00
    assert data["method"] == "bkash"
    assert data["transaction_id"] == "TXN123456"
    assert data["status"] == "verified"
    assert data["order_id"] == order_id
    assert data["business_id"] == business_id


def test_payment_idempotency():
    '''Proves that recording the same payment twice (same transaction_id) only creates one record.'''
    _, business_id, order_id, token = _setup_test_environment()
    
    payment_payload = {
        "amount": "100.00",
        "method": "nagad",
        "transaction_id": "TXN789012",
        "notes": "First attempt"
    }
    
    # First payment
    response1 = client.post(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/payments/",
        json=payment_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response1.status_code == 201
    payment1_id = response1.json()["id"]
    
    # Second payment with SAME transaction_id (idempotent)
    response2 = client.post(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/payments/",
        json=payment_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response2.status_code == 201
    payment2_id = response2.json()["id"]
    
    # CRITICAL: Both responses should return the SAME payment ID
    assert payment1_id == payment2_id, "Idempotency FAILED: Duplicate payment was created!"
    
    # Verify only one payment exists in database
    db = SessionLocal()
    count = db.query(Payment).filter(Payment.transaction_id == "TXN789012").count()
    db.close()
    assert count == 1, f"Expected 1 payment, but found {count}"


def test_payment_tenant_isolation():
    '''Proves that User B cannot record payments for User A's orders.'''
    db = SessionLocal()
    
    # Clean up
    db.query(Payment).delete()
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
    
    # Create an order for Business A
    order_a = Order(
        business_id=business_a.id,
        total_amount=100.00,
        total_cost=40.00,
        gross_profit=60.00
    )
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
    
    # CRITICAL: User B tries to record a payment for User A's order (should fail with 403)
    response = client.post(
        f"/api/v1/businesses/{business_a_id}/orders/{order_a_id}/payments/",
        json={"amount": "100.00", "method": "cash"},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403, "Tenant isolation FAILED: User B could record payment for Business A's order!"


def test_payment_for_nonexistent_order():
    '''Proves that recording a payment for a non-existent order fails gracefully.'''
    _, business_id, _, token = _setup_test_environment()
    
    response = client.post(
        f"/api/v1/businesses/{business_id}/orders/99999/payments/",
        json={"amount": "100.00", "method": "cash"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 400
    assert "Order not found" in response.json()["detail"]
