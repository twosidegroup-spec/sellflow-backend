from fastapi import APIRouter, Depends
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
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business)
):
    '''
    Returns a high-level summary of the business's performance.
    Tenant isolation is enforced by get_current_business.
    '''
    return service.get_dashboard_summary(db, business_id)
