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

app = FastAPI(
    title="SELLFLOW API",
    description="Seller Execution Engine for social commerce.",
    version="0.8.0",
)

# FOOLPROOF CORS: Allows ALL origins (perfect for local Chrome testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(deliveries_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "sellflow-api", "environment": settings.app_env}
