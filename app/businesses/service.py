from sqlalchemy.orm import Session
from app.db.base import Business
from app.businesses.schemas import BusinessCreate, BusinessUpdate


def get_business(db: Session, business_id: int) -> Business | None:
    """Get a business by ID."""
    return db.query(Business).filter(Business.id == business_id).first()


def get_business_by_slug(db: Session, slug: str) -> Business | None:
    """Get a business by slug."""
    return db.query(Business).filter(Business.slug == slug).first()


def create_business(db: Session, business_data: BusinessCreate) -> Business:
    """Create a new business."""
    import re
    # Generate slug from name
    slug = re.sub(r'[^a-z0-9]+', '-', business_data.name.lower()).strip('-')
    
    business = Business(
        name=business_data.name,
        slug=slug,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def update_business(db: Session, business_id: int, business_data: BusinessUpdate) -> Business | None:
    """Update a business."""
    business = get_business(db, business_id)
    if not business:
        return None
    
    if business_data.name is not None:
        business.name = business_data.name
    
    db.commit()
    db.refresh(business)
    return business


def delete_business(db: Session, business_id: int) -> bool:
    """Delete a business."""
    business = get_business(db, business_id)
    if not business:
        return False
    
    db.delete(business)
    db.commit()
    return True
