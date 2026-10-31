from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.db.base import User, Business, Membership

def get_current_business(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Business:
    '''
    Dependency that verifies the authenticated user is a member of the requested business.
    This enforces tenant isolation: users can only access businesses they belong to.
    '''
    # 1. Verify the business exists
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # 2. Verify the user is a member of this business
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.business_id == business_id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this business"
        )
    
    return business


def get_user_primary_business(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Business:
    """The requesting user's first business (lowest id).

    Used by dev-only tooling (the payment simulator) where the client does not
    send a business id. Production routes always take an explicit
    `business_id` through `get_current_business`.
    """
    membership = (
        db.query(Membership)
        .filter(Membership.user_id == current_user.id)
        .order_by(Membership.business_id.asc())
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to any business"
        )
    business = db.query(Business).filter(Business.id == membership.business_id).first()
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    return business
