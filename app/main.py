from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from app.db.dependencies import get_db
from app.db.base import User, Business, Product, Order, Payment, Customer
from app.products.models import ProductStatus
from app.orders.models import OrderStatus
from datetime import datetime

app = FastAPI(
    title="SELLFLOW API",
    description="Seller Execution Engine for social commerce.",
    version="0.9.0",
)

# CORS Configuration for Flutter Web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple schemas for public API endpoints
class SimpleOrderCreate(BaseModel):
    total_amount: float
    customer_name: str

class SimpleProductCreate(BaseModel):
    name: str
    sku: Optional[str] = None
    cost_price: float = 0.0
    selling_price: float = 0.0
    stock_quantity: int = 0

class SimpleCustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

def get_stats(db: Session):
    return {
        "users": db.query(User).count(),
        "businesses": db.query(Business).count(),
        "products": db.query(Product).count(),
        "orders": db.query(Order).count(),
        "payments": db.query(Payment).count(),
        "customers": db.query(Customer).count()
    }

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}

# --- Public API Endpoints for Mobile App ---
@app.post("/api/orders")
async def create_order(order: SimpleOrderCreate, db: Session = Depends(get_db)):
    # Get or create a default business
    default_business = db.query(Business).first()
    if not default_business:
        default_business = Business(name="Default Business", slug="default")
        db.add(default_business)
        db.commit()
    
    # Check if customer exists by name
    customer = db.query(Customer).filter(Customer.name == order.customer_name).first()
    if not customer:
        # Create new customer
        customer = Customer(
            business_id=default_business.id,
            name=order.customer_name,
            email="",
            created_at=datetime.utcnow()
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
    
    # Create order
    order_db = Order(
        business_id=default_business.id,
        customer_id=customer.id,
        total_amount=order.total_amount,
        status=OrderStatus.CREATED,
        total_cost=0.0,
        created_at=datetime.utcnow()
    )
    db.add(order_db)
    db.commit()
    db.refresh(order_db)
    
    return {"success": True, "order_id": order_db.id, "customer_id": customer.id, "message": "Order created successfully"}

@app.post("/api/products")
async def create_product(product: SimpleProductCreate, db: Session = Depends(get_db)):
    # Get or create a default business
    default_business = db.query(Business).first()
    if not default_business:
        default_business = Business(name="Default Business", slug="default")
        db.add(default_business)
        db.commit()
    
    # Create product
    product_db = Product(
        business_id=default_business.id,
        name=product.name,
        sku=product.sku or f"SKU-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        cost_price=product.cost_price,
        selling_price=product.selling_price,
        stock_quantity=product.stock_quantity,
        status=ProductStatus.ACTIVE,
        created_at=datetime.utcnow()
    )
    db.add(product_db)
    db.commit()
    db.refresh(product_db)
    
    return {"success": True, "product_id": product_db.id, "message": "Product created successfully"}

@app.post("/api/customers")
async def create_customer(customer: SimpleCustomerCreate, db: Session = Depends(get_db)):
    # Get or create a default business
    default_business = db.query(Business).first()
    if not default_business:
        default_business = Business(name="Default Business", slug="default")
        db.add(default_business)
        db.commit()
    
    # Create customer
    customer_db = Customer(
        business_id=default_business.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        created_at=datetime.utcnow()
    )
    db.add(customer_db)
    db.commit()
    db.refresh(customer_db)
    
    return {"success": True, "customer_id": customer_db.id, "message": "Customer created successfully"}



# Include existing API routers
from app.auth.router import router as auth_router
from app.products.router import router as products_router
from app.products.upload_router import router as products_upload_router
from app.customers.router import router as customers_router
from app.orders.router import router as orders_router
from app.payments.router import (
    router as payments_router,
    business_router as business_payments_router,
    detect_router as payments_detect_router,
)
from app.deliveries.router import router as deliveries_router
from app.analytics.router import router as analytics_router
from app.businesses.router import router as businesses_router
from app.devices.router import router as devices_router
from app.health.router import router as health_router
from app.api.v1.router import router as v1_router
from app.webhooks.router import router as webhooks_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(products_upload_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(business_payments_router, prefix="/api/v1")
app.include_router(payments_detect_router, prefix="/api/v1")
app.include_router(deliveries_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(businesses_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(health_router)
app.include_router(v1_router)
app.include_router(webhooks_router, prefix="/api/v1")
