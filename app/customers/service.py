from sqlalchemy.orm import Session
from app.db.base import Customer
from app.customers.schemas import CustomerCreate, CustomerUpdate

def get_customers(db: Session, business_id: int) -> list[Customer]:
    return db.query(Customer).filter(Customer.business_id == business_id).all()

def get_customer(db: Session, business_id: int, customer_id: int) -> Customer | None:
    return db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == business_id).first()

def create_customer(db: Session, business_id: int, customer_data: CustomerCreate) -> Customer:
    db_customer = Customer(business_id=business_id, name=customer_data.name, phone=customer_data.phone, email=customer_data.email, address=customer_data.address)
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

def update_customer(db: Session, business_id: int, customer_id: int, customer_data: CustomerUpdate) -> Customer | None:
    customer = get_customer(db, business_id, customer_id)
    if not customer: return None
    for field, value in customer_data.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer

def delete_customer(db: Session, business_id: int, customer_id: int) -> bool:
    customer = get_customer(db, business_id, customer_id)
    if not customer: return False
    db.delete(customer)
    db.commit()
    return True
