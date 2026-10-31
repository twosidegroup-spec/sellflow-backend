import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

router = APIRouter(tags=["Health"])
logger = logging.getLogger("sellflow.health")


@router.get("/status")
async def health_status():
    """
    Health check endpoint for monitoring and load balancers.
    Returns basic service status and configuration info.
    """
    return {
        "status": "ok",
        "service": "sellflow-api",
        "version": "0.9.0",
    }


@router.get("/database")
async def database_health():
    """
    Database connectivity check.

    Returns a generic status only. The previous implementation echoed
    `str(e)` to the caller, which could disclose connection details or
    schema fragments; the detail is logged server-side instead.
    """
    from app.db.engine import SessionLocal

    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception:  # noqa: BLE001 - health probe must not raise
        logger.exception("database health check failed")
        return {
            "status": "error",
            "database": "disconnected",
        }
    finally:
        if db is not None:
            db.close()


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe for Kubernetes/container orchestration.

    Unlike the previous hardcoded response, this actually probes the
    database and answers 503 when the API cannot serve traffic.
    """
    from app.db.engine import SessionLocal

    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # noqa: BLE001 - report, do not raise
        logger.exception("readiness check failed")
        database = "error"
    finally:
        if db is not None:
            db.close()

    if database != "ok":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"ready": False, "checks": {"database": database, "api": "ok"}},
        )

    return {
        "ready": True,
        "checks": {
            "database": "ok",
            "api": "ok",
        },
    }
