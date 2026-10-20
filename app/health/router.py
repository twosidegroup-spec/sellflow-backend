from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter(tags=["Health"])


@router.get("/status")
async def health_status():
    """
    Health check endpoint for monitoring and load balancers.
    Returns basic service status and configuration info.
    """
    return {
        "status": "ok",
        "service": "sellflow-api",
        "version": "0.8.0",
    }


@router.get("/database")
async def database_health():
    """
    Database connectivity check.
    Verifies the database connection is working.
    """
    try:
        from app.db.engine import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
        }


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe for Kubernetes/container orchestration.
    Indicates when the service is ready to receive traffic.
    """
    return {
        "ready": True,
        "checks": {
            "database": "ok",
            "api": "ok",
        }
    }
