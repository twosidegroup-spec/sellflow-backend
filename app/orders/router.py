from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business, Order
from app.orders.schemas import OrderCreate, OrderRead, OrderStatusUpdate
from app.orders.models import OrderStatus
from app.orders import service
from app.notifications.service import send_order_notification

router = APIRouter(prefix="/businesses/{business_id}/orders", tags=["Orders"])

@router.get("/", response_model=list[OrderRead])
def list_orders(
    business_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    return service.get_orders(db, business_id)

@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order_endpoint(
    business_id: int,
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    try:
        return service.create_order(db, business_id, order_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{order_id}", response_model=OrderRead)
def get_order_endpoint(
    business_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    order = service.get_order(db, business_id, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order

@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status_endpoint(
    business_id: int,
    order_id: int,
    status_update: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    order = db.query(Order).filter(Order.id == order_id, Order.business_id == business_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    old_status = order.status
    order.status = status_update.status
    db.commit()
    db.refresh(order)
    
    # Trigger background notification ONLY if the status actually changed
    if old_status != status_update.status:
        # In a real app, we would fetch the actual customer email from order.customer.email
        mock_customer_email = "customer@example.com"
        background_tasks.add_task(
            send_order_notification,
            order_id=order.id,
            status=status_update.status.value,
            customer_email=mock_customer_email
        )
        
    return order
