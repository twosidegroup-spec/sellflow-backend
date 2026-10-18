from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business
from app.deliveries.schemas import DeliveryCreate, DeliveryUpdate, DeliveryRead
from app.deliveries import service

router = APIRouter(prefix="/businesses/{business_id}/orders/{order_id}/delivery", tags=["Deliveries"])

@router.post("/", response_model=DeliveryRead, status_code=status.HTTP_201_CREATED)
def create_delivery_endpoint(
    business_id: int,
    order_id: int,
    delivery_data: DeliveryCreate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    try:
        return service.create_delivery(db, business_id, order_id, delivery_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=DeliveryRead)
def get_delivery_endpoint(
    business_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    delivery = service.get_delivery(db, business_id, order_id)
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return delivery

@router.patch("/", response_model=DeliveryRead)
def update_delivery_endpoint(
    business_id: int,
    order_id: int,
    delivery_data: DeliveryUpdate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    delivery = service.update_delivery(db, business_id, order_id, delivery_data)
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return delivery
