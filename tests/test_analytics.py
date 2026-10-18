from fastapi.testclient import TestClient
from app.main import app
from app.db.engine import SessionLocal
from app.db.base import User, Business, Membership, Order, Delivery
from app.businesses.models import MembershipRole
from app.core.security import get_password_hash
from app.orders.models import OrderStatus
from app.deliveries.models import DeliveryStatus

client = TestClient(app)

def _setup_analytics_test():
    db = SessionLocal()
    
    # Clean up
    db.query(Delivery).delete()
    db.query(Order).delete()
    db.query(Membership).delete()
    db.query(Business).delete()
    db.query(User).delete()
    db.commit()
    
    # Create User and Business
    user = User(email="analytics@sellflow.com", full_name="Analytics User", hashed_password=get_password_hash("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    business = Business(name="Analytics Business", slug="analytics-business")
    db.add(business)
    db.commit()
    db.refresh(business)
    
    db.add(Membership(user_id=user.id, business_id=business.id, role=MembershipRole.OWNER))
    
    # Create 3 orders with specific values
    order1 = Order(business_id=business.id, total_amount=100.00, gross_profit=40.00, status=OrderStatus.DELIVERED)
    order2 = Order(business_id=business.id, total_amount=250.00, gross_profit=100.00, status=OrderStatus.CONFIRMED)
    order3 = Order(business_id=business.id, total_amount=50.00, gross_profit=-10.00, status=OrderStatus.CANCELLED)
    
    db.add_all([order1, order2, order3])
    
    # CRITICAL FIX: Flush the session to generate the order IDs before using them
    db.flush()
    
    # Create 1 pending delivery linked to order1
    delivery = Delivery(business_id=business.id, order_id=order1.id, status=DeliveryStatus.PENDING, delivery_fee=60.00)
    db.add(delivery)
    
    db.commit()
    
    business_id = business.id
    db.close()
    
    token = client.post("/api/v1/auth/login", json={"email": "analytics@sellflow.com", "password": "password123"}).json()["access_token"]
    
    return business_id, token

def test_dashboard_summary_calculations():
    '''Proves that the analytics service correctly aggregates order and delivery data.'''
    business_id, token = _setup_analytics_test()
    
    response = client.get(
        f"/api/v1/businesses/{business_id}/analytics/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Total Revenue: 100 + 250 + 50 = 400
    assert float(data["total_revenue"]) == 400.00
    
    # Total Profit: 40 + 100 + (-10) = 130
    assert float(data["total_profit"]) == 130.00
    
    # Total Orders: 3
    assert data["total_orders"] == 3
    
    # Pending Deliveries: 1
    assert data["pending_deliveries"] == 1
    
    # Orders by Status
    assert data["orders_by_status"]["delivered"] == 1
    assert data["orders_by_status"]["confirmed"] == 1
    assert data["orders_by_status"]["cancelled"] == 1
    assert data["orders_by_status"]["created"] == 0


def test_analytics_tenant_isolation():
    '''Proves that User B cannot access User A's analytics summary.'''
    db = SessionLocal()
    
    # Clean up
    db.query(Delivery).delete()
    db.query(Order).delete()
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
    
    token_a = client.post("/api/v1/auth/login", json={"email": "userA@sellflow.com", "password": "password123"}).json()["access_token"]
    token_b = client.post("/api/v1/auth/login", json={"email": "userB@sellflow.com", "password": "password123"}).json()["access_token"]
    
    # CRITICAL: User B tries to get User A's analytics (should fail with 403)
    response = client.get(
        f"/api/v1/businesses/{business_a_id}/analytics/summary",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403, "Tenant isolation FAILED: User B could access Business A's analytics!"
