from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.auth.router import router as auth_router
from app.products.router import router as products_router
from app.customers.router import router as customers_router
from app.orders.router import router as orders_router
from app.payments.router import router as payments_router
from app.deliveries.router import router as deliveries_router
from app.analytics.router import router as analytics_router
from app.businesses.router import router as businesses_router
from app.devices.router import router as devices_router
from app.health.router import router as health_router
from app.api.v1.router import router as v1_router

app = FastAPI(
    title="SELLFLOW API",
    description="Seller Execution Engine for social commerce.",
    version="0.8.0",
)

# Updated CORS: Allow all origins including localhost variants
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:60704",
        "http://localhost:60000",
        "http://127.0.0.1:*",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(deliveries_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(businesses_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(v1_router)
app.include_router(health_router)
