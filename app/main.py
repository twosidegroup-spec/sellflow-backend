"""SellFlow API entry point.

Consolidated after the System A -> System B migration:

* One FastAPI application, one authentication architecture, one database.
* The three legacy PUBLIC write endpoints (`POST /api/orders`,
  `/api/products`, `/api/customers`) have been removed. They wrote into
  "the first business row" with no credential and no tenant.
* CORS comes from configuration; the unsafe wildcard+credentials combination
  is impossible (`app/core/config.py`).
* The device bridge (`/device-bridge/*`) and payment accounts
  (`/payment-accounts/*`) are mounted at the ROOT, byte-compatible with
  System A, because the Kotlin Payment Bridge bakes its URLs at build time.
  Every other route stays under `/api/v1`.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings

app = FastAPI(
    title="SELLFLOW API",
    description="Seller Execution Engine for social commerce.",
    version="0.9.0",
)

# CORS from configuration. `*` is only possible when credentials are disabled.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint (kept for backwards compatibility with probes)
@app.get("/health")
async def health():
    return {"status": "ok"}


# --- API routers -------------------------------------------------------------

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
from app.payments.intelligence.router import router as payment_intelligence_router
from app.deliveries.router import router as deliveries_router
from app.analytics.router import router as analytics_router
from app.businesses.router import router as businesses_router
from app.devices.router import router as devices_router
from app.health.router import router as health_router
from app.api.v1.router import router as v1_router
from app.webhooks.router import router as webhooks_router

# Compatibility surfaces (root paths, matching System A's device bridge API).
from app.devices.bridge_router import router as device_bridge_router
from app.payments.accounts_router import router as payment_accounts_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(products_upload_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(business_payments_router, prefix="/api/v1")
app.include_router(payments_detect_router, prefix="/api/v1")
app.include_router(payment_intelligence_router, prefix="/api/v1")
app.include_router(deliveries_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(businesses_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")
app.include_router(health_router)
app.include_router(v1_router)
app.include_router(webhooks_router, prefix="/api/v1")

# Root-mounted device bridge / payment accounts (Kotlin bridge compatibility).
app.include_router(device_bridge_router)
app.include_router(payment_accounts_router)

# --- Static assets: premium web console + shared mobile assets ----------------
#
# The web console is dependency-free static assets served by this app
# (no build step). Files live in `webapp/`; the shared Inter font files and
# provider logos live in the Flutter app's `assets/` directory.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_WEBAPP_DIR = _BACKEND_ROOT / "webapp"
_ASSETS_DIR = _BACKEND_ROOT / "assets"
_UPLOADS_DIR = _BACKEND_ROOT / "uploads"

if _WEBAPP_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=_WEBAPP_DIR, html=True), name="webapp")

if _ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

if _UPLOADS_DIR.is_dir():
    app.mount("/uploads", StaticFiles(directory=_UPLOADS_DIR), name="uploads")


@app.get("/console", include_in_schema=False)
async def console_redirect():
    """Convenience redirect to the web console."""
    return RedirectResponse(url="/app/")

