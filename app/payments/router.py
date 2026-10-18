from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business
from app.payments.schemas import PaymentCreate, PaymentRead
from app.payments import service

router = APIRouter(prefix="/businesses/{business_id}/orders/{order_id}/payments", tags=["Payments"])

@router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def record_payment_endpoint(
    business_id: int,
    order_id: int,
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    try:
        return service.record_payment(db, business_id, order_id, payment_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
