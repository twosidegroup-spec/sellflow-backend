from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business, Order
from app.orders.schemas import (
    OrderCreate,
    OrderCreateResponse,
    OrderRead,
    OrderStatusUpdate,
    StockWarning,
)
from app.orders.models import OrderStatus, allowed_next_statuses
from app.orders import service
from app.notifications.service import send_order_notification
from app.webhooks.dispatcher import dispatch_event

router = APIRouter(prefix="/businesses/{business_id}/orders", tags=["Orders"])

@router.get("/", response_model=list[OrderRead])
def list_orders(
    business_id: int,
    q: str | None = Query(None, max_length=120, description="Search by order id or customer name"),
    order_status: OrderStatus | None = Query(None, alias="status"),
    sort: str = Query("newest", pattern=r"^(newest|oldest|amount_desc|amount_asc)$"),
    limit: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    return service.get_orders(
        db,
        business_id,
        q=q,
        status=order_status,
        sort=sort,
        limit=limit,
        offset=offset,
    )

@router.post("/", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
def create_order_endpoint(
    business_id: int,
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    try:
        order, warnings = service.create_order_with_warnings(db, business_id, order_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Non-blocking stock warnings (approved Inventory Option C): the order is
    # always created; the client receives the warnings and the server records
    # them in orders.system_notes (done inside the service).
    response = OrderCreateResponse.model_validate(order)
    response.warnings = [StockWarning(**warning) for warning in warnings]
    return response

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
    new_status = status_update.status

    # Transition policy (STAGING_READINESS.md 4.1). Same-status requests are
    # no-ops; anything else must be an explicitly allowed transition.
    if new_status != old_status:
        allowed = allowed_next_statuses(old_status)
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        f"Cannot change status from {old_status.value} to "
                        f"{new_status.value}"
                    ),
                    "current_status": old_status.value,
                    "requested_status": new_status.value,
                    "allowed_transitions": sorted(s.value for s in allowed),
                },
            )

    order.status = new_status
    db.commit()
    db.refresh(order)
    
    # Trigger background notification ONLY if the status actually changed
    if old_status != new_status:
        # In a real app, we would fetch the actual customer email from order.customer.email
        mock_customer_email = "customer@example.com"
        background_tasks.add_task(
            send_order_notification,
            order_id=order.id,
            status=new_status.value,
            customer_email=mock_customer_email
        )
        background_tasks.add_task(
            dispatch_event,
            business_id,
            "order.status_changed",
            {
                "order_id": order.id,
                "business_id": business_id,
                "old_status": old_status.value if hasattr(old_status, "value") else str(old_status),
                "new_status": new_status.value,
            },
        )
        
    return order
