from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business
from app.analytics.schemas import DashboardSummary
from app.analytics import service

router = APIRouter(prefix="/businesses/{business_id}/analytics", tags=["Analytics"])

@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary_endpoint(
    business_id: int,
    days: int = Query(
        7,
        ge=7,
        le=90,
        description="Length of the daily series (and 'today' window) in days.",
    ),
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    '''
    Returns a high-level summary of the business's performance.

    Lifetime figures (revenue, profit, orders) are unaffected by `days`; the
    daily series and the "today" figures always cover the most recent window.

    Tenant isolation is enforced by get_current_business.
    '''
    return service.get_dashboard_summary(db, business_id, days=days)
