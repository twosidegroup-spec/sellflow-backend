from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.base import Delivery, Order
from app.deliveries.schemas import DeliveryCreate, DeliveryUpdate
from app.deliveries.models import DeliveryStatus

def create_delivery(db: Session, business_id: int, order_id: int, delivery_data: DeliveryCreate) -> Delivery:
    # Verify order exists and belongs to this business
    order = db.query(Order).filter(Order.id == order_id, Order.business_id == business_id).first()
    if not order:
        raise ValueError("Order not found or access denied")
    
    # Check if delivery already exists for this order
    existing = db.query(Delivery).filter(Delivery.order_id == order_id).first()
    if existing:
        raise ValueError("Delivery already exists for this order")

    db_delivery = Delivery(
        business_id=business_id,
        order_id=order_id,
        courier=delivery_data.courier,
        tracking_number=delivery_data.tracking_number,
        delivery_fee=float(delivery_data.delivery_fee),
        status=DeliveryStatus.PENDING
    )
    db.add(db_delivery)
    db.commit()
    db.refresh(db_delivery)
    return db_delivery

def get_delivery(db: Session, business_id: int, order_id: int) -> Delivery | None:
    return db.query(Delivery).filter(Delivery.order_id == order_id, Delivery.business_id == business_id).first()

def update_delivery(db: Session, business_id: int, order_id: int, delivery_data: DeliveryUpdate) -> Delivery | None:
    delivery = get_delivery(db, business_id, order_id)
    if not delivery:
        return None
    
    update_data = delivery_data.model_dump(exclude_unset=True)
    
    # Auto-set timestamps based on status changes
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == DeliveryStatus.PICKED_UP and not delivery.shipped_at:
            delivery.shipped_at = datetime.now(timezone.utc)
        elif new_status == DeliveryStatus.DELIVERED and not delivery.delivered_at:
            delivery.delivered_at = datetime.now(timezone.utc)
        elif new_status == DeliveryStatus.RETURNED and not delivery.returned_at:
            delivery.returned_at = datetime.now(timezone.utc)
            
    for field, value in update_data.items():
        setattr(delivery, field, value)
    
    db.commit()
    db.refresh(delivery)
    return delivery
