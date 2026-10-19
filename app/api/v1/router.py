from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business
from typing import Any

router = APIRouter(prefix="/api/v1", tags=["API v1"])


@router.get("/info", response_model=dict[str, Any])
async def get_api_info():
    """
    Returns API version and basic information.
    """
    return {
        "name": "SELLFLOW API",
        "version": "0.8.0",
        "description": "Seller Execution Engine for social commerce",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/businesses/me", response_model=dict[str, Any])
def get_user_businesses(
    current_business: Business = Depends(get_current_business),
):
    """
    Returns information about the current business context.
    This endpoint is useful for clients to verify which business they're operating in.
    """
    return {
        "business_id": current_business.id,
        "business_name": current_business.name,
        "business_slug": current_business.slug,
    }


@router.post("/businesses/me/switch", response_model=dict[str, Any])
def switch_business(
    business_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """
    Verify the user has access to the specified business.
    This can be used by clients to validate business switching.
    """
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    return {
        "business_id": business.id,
        "business_name": business.name,
        "business_slug": business.slug,
    }


@router.get("/version")
async def get_version():
    """
    Returns the current API version.
    """
    return {"version": "0.8.0"}
