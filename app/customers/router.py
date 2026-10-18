from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business
from app.customers.schemas import CustomerCreate, CustomerRead, CustomerUpdate
from app.customers import service

router = APIRouter(prefix="/businesses/{business_id}/customers", tags=["Customers"])

@router.get("/", response_model=list[CustomerRead])
def list_customers(business_id: int, db: Session = Depends(get_db), current_business: Business = Depends(get_current_business)):
    return service.get_customers(db, business_id)

@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer_endpoint(business_id: int, customer_data: CustomerCreate, db: Session = Depends(get_db), current_business: Business = Depends(get_current_business)):
    return service.create_customer(db, business_id, customer_data)

@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer_endpoint(business_id: int, customer_id: int, db: Session = Depends(get_db), current_business: Business = Depends(get_current_business)):
    customer = service.get_customer(db, business_id, customer_id)
    if not customer: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer

@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer_endpoint(business_id: int, customer_id: int, customer_data: CustomerUpdate, db: Session = Depends(get_db), current_business: Business = Depends(get_current_business)):
    customer = service.update_customer(db, business_id, customer_id, customer_data)
    if not customer: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_endpoint(business_id: int, customer_id: int, db: Session = Depends(get_db), current_business: Business = Depends(get_current_business)):
    if not service.delete_customer(db, business_id, customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
