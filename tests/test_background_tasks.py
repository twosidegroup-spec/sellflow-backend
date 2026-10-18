from fastapi.testclient import TestClient
from app.main import app
from app.db.engine import SessionLocal
from app.db.base import User, Business, Membership, Order
from app.businesses.models import MembershipRole
from app.core.security import get_password_hash
from app.orders.models import OrderStatus
from unittest.mock import patch

client = TestClient(app)

def _setup_order_test():
    db = SessionLocal()
    db.query(Order).delete()
    db.query(Membership).delete()
    db.query(Business).delete()
    db.query(User).delete()
    db.commit()
    
    user = User(email="bguser@sellflow.com", full_name="BG User", hashed_password=get_password_hash("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    business = Business(name="BG Business", slug="bg-business")
    db.add(business)
    db.commit()
    db.refresh(business)
    
    db.add(Membership(user_id=user.id, business_id=business.id, role=MembershipRole.OWNER))
    db.commit()
    
    order = Order(business_id=business.id, total_amount=100.00, total_cost=40.00, gross_profit=60.00, status=OrderStatus.CREATED)
    db.add(order)
    db.commit()
    db.refresh(order)
    
    business_id = business.id
    order_id = order.id
    db.close()
    
    token = client.post("/api/v1/auth/login", json={"email": "bguser@sellflow.com", "password": "password123"}).json()["access_token"]
    return business_id, order_id, token

@patch("app.orders.router.send_order_notification")
def test_background_task_triggered_on_status_change(mock_send_notification):
    '''Proves that updating order status queues a background task without blocking the response.'''
    business_id, order_id, token = _setup_order_test()
    
    # Update status to SHIPPED
    response = client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/status",
        json={"status": "shipped"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "shipped"
    
    # Verify the background task was queued with correct arguments
    mock_send_notification.assert_called_once_with(
        order_id=order_id,
        status="shipped",
        customer_email="customer@example.com"
    )

@patch("app.orders.router.send_order_notification")
def test_background_task_not_triggered_if_status_unchanged(mock_send_notification):
    '''Proves that no background task is queued if the status is updated to the same value.'''
    business_id, order_id, token = _setup_order_test()
    
    # Order is already CREATED. Update to CREATED.
    response = client.patch(
        f"/api/v1/businesses/{business_id}/orders/{order_id}/status",
        json={"status": "created"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "created"
    
    # Verify the background task was NOT called
    mock_send_notification.assert_not_called()
