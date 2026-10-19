from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.businesses.dependencies import get_current_business
from app.db.base import Business, Membership
from app.businesses.schemas import BusinessRead, BusinessUpdate
from app.auth.dependencies import get_current_user
from app.auth.models import User

router = APIRouter(prefix="/businesses", tags=["Businesses"])


@router.get("/{business_id}", response_model=BusinessRead)
def get_business(
    business_id: int,
    current_business: Business = Depends(get_current_business),
):
    """
    Get business details.
    Tenant isolation is enforced by get_current_business.
    """
    return current_business


@router.patch("/{business_id}", response_model=BusinessRead)
def update_business(
    business_id: int,
    business_data: BusinessUpdate,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """
    Update business information.
    Only members can update their business.
    """
    if business_data.name is not None:
        current_business.name = business_data.name
        db.commit()
        db.refresh(current_business)
    return current_business


@router.get("/{business_id}/memberships", response_model=list[dict])
def list_business_memberships(
    business_id: int,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all members of the business.
    Shows role information for each member.
    """
    memberships = db.query(Membership).filter(
        Membership.business_id == business_id
    ).all()

    result = []
    for membership in memberships:
        member = db.query(User).filter(User.id == membership.user_id).first()
        result.append({
            "user_id": membership.user_id,
            "email": member.email if member else "unknown",
            "full_name": member.full_name if member else "unknown",
            "role": membership.role.value,
            "created_at": membership.created_at.isoformat(),
        })
    return result


@router.post("/{business_id}/memberships", response_model=dict, status_code=status.HTTP_201_CREATED)
def add_business_membership(
    business_id: int,
    membership_data: dict,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a member to the business.
    Only owners and admins can add members.
    """
    if current_user.is_owner(current_business.id, db):
        role = membership_data.get("role", "staff")
        user_id = membership_data.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required"
            )
        
        # Check if membership already exists
        existing = db.query(Membership).filter(
            Membership.user_id == user_id,
            Membership.business_id == business_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this business"
            )
        
        membership = Membership(
            user_id=user_id,
            business_id=business_id,
            role=role
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
        
        return {
            "user_id": membership.user_id,
            "business_id": membership.business_id,
            "role": membership.role.value,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can add members"
        )


@router.delete("/{business_id}/memberships/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_business_membership(
    business_id: int,
    user_id: int,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a member from the business.
    Only owners and admins can remove members.
    """
    if current_user.is_owner(current_business.id, db):
        membership = db.query(Membership).filter(
            Membership.user_id == user_id,
            Membership.business_id == business_id
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership not found"
            )
        
        db.delete(membership)
        db.commit()
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can remove members"
        )
