from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings

app = FastAPI(
    title="SELLFLOW API",
    description="Seller Execution Engine for social commerce.",
    version="0.8.0",
)

# Add CORS headers to all responses
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

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
