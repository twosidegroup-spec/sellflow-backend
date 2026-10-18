from fastapi.testclient import TestClient
from app.main import app
from app.db.engine import SessionLocal
from app.db.base import User, Business, Membership, Product, Order, OrderItem
from app.businesses.models import MembershipRole
from app.core.security import get_password_hash

client = TestClient(app)

def _setup_test_environment():
    '''Helper to create a clean test environment with a user, business, and product.'''
    db = SessionLocal()
    
    # Clean up
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
    
    # Extract IDs before closing session
    user_id = user.id
    business_id = business.id
    product_id = product.id
    
    db.close()
    
    # Get auth token
    response = client.post("/api/v1/auth/login", json={"email": "seller@sellflow.com", "password": "password123"})
    token = response.json()["access_token"]
    
    return user_id, business_id, product_id, token


def test_create_order_with_server_side_calculations():
    '''Proves that the server correctly calculates order totals, ignoring any client manipulation.'''
    _, business_id, product_id, token = _setup_test_environment()
    
    # Create an order with 2 items
    order_payload = {
        "items": [
            {
                "product_id": product_id,
                "product_name": "Test Product",
                "quantity": 2,
                "unit_price": "25.00",
                "unit_cost": "10.00"
            },
            {
                "product_id": None, # Custom item without product link
                "product_name": "Custom Service",
                "quantity": 1,
                "unit_price": "50.00",
                "unit_cost": "0.00"
            }
        ],
        "delivery_fee": "5.00",
        "discount": "10.00",
        "notes": "Test order notes"
    }
    
    response = client.post(
        f"/api/v1/businesses/{business_id}/orders/",
        json=order_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify server-side calculations:
    # Item 1: 2 * 25.00 = 50.00 (amount), 2 * 10.00 = 20.00 (cost), profit = 30.00
    # Item 2: 1 * 50.00 = 50.00 (amount), 1 * 0.00 = 0.00 (cost), profit = 50.00
    # Total Amount (before discount/delivery) = 50.00 + 50.00 = 100.00
    # Total Cost = 20.00 + 0.00 = 20.00
    # Gross Profit = (100.00 - 20.00) - 10.00 (discount) = 70.00
    # Final Amount = 100.00 + 5.00 (delivery) - 10.00 (discount) = 95.00
    
    assert float(data["total_amount"]) == 95.00
    assert float(data["total_cost"]) == 20.00
    assert float(data["gross_profit"]) == 70.00
    assert float(data["delivery_fee"]) == 5.00
    assert float(data["discount"]) == 10.00
    assert len(data["items"]) == 2
    
    # Verify individual item calculations
    assert float(data["items"][0]["line_total"]) == 50.00
    assert float(data["items"][0]["cost_total"]) == 20.00
    assert float(data["items"][0]["profit"]) == 30.00
    
    assert float(data["items"][1]["line_total"]) == 50.00
    assert float(data["items"][1]["cost_total"]) == 0.00
    assert float(data["items"][1]["profit"]) == 50.00


def test_create_order_with_negative_profit():
    '''Proves that legitimate loss-leader sales (negative profit) are allowed.'''
    _, business_id, product_id, token = _setup_test_environment()
    
    order_payload = {
        "items": [
            {
                "product_id": product_id,
                "product_name": "Test Product",
                "quantity": 1,
                "unit_price": "5.00",  # Selling below cost (10.00)
                "unit_cost": "10.00"
            }
        ],
        "delivery_fee": "0.00",
        "discount": "0.00"
    }
    
    response = client.post(
        f"/api/v1/businesses/{business_id}/orders/",
        json=order_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Profit should be negative: 5.00 - 10.00 = -5.00
    assert float(data["gross_profit"]) == -5.00
    assert float(data["items"][0]["profit"]) == -5.00


def test_order_tenant_isolation():
    '''Proves that User B cannot access User A's orders.'''
    db = SessionLocal()
    
    # Clean up
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
    db.close()
    
    # Get tokens
    token_a = client.post("/api/v1/auth/login", json={"email": "userA@sellflow.com", "password": "password123"}).json()["access_token"]
    token_b = client.post("/api/v1/auth/login", json={"email": "userB@sellflow.com", "password": "password123"}).json()["access_token"]
    
    # User A creates an order
    response = client.post(
        f"/api/v1/businesses/{business_a_id}/orders/",
        json={
            "items": [{"product_id": None, "product_name": "Secret Order", "quantity": 1, "unit_price": "10.00", "unit_cost": "5.00"}],
            "delivery_fee": "0.00",
            "discount": "0.00"
        },
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert response.status_code == 201
    order_a_id = response.json()["id"]
    
    # CRITICAL: User B tries to list User A's orders (should fail with 403)
    response = client.get(
        f"/api/v1/businesses/{business_a_id}/orders/",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403, "Tenant isolation FAILED: User B could access Business A's orders!"
    
    # CRITICAL: User B tries to get specific order from Business A (should fail with 403)
    response = client.get(
        f"/api/v1/businesses/{business_a_id}/orders/{order_a_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403, "Tenant isolation FAILED: User B could view Business A's order!"
