from app.db.engine import SessionLocal
from app.db.base import User, Business, Membership
from app.businesses.models import MembershipRole

def test_create_user_and_business():
    '''Verify that we can insert and query users, businesses, and memberships.'''
    with SessionLocal() as session:
        # 1. Create a User
        user = User(
            email="test@sellflow.com",
            full_name="Test User",
            hashed_password="fake_hashed_password_for_now"
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        
        # 2. Create a Business
        business = Business(
            name="Test Business",
            slug="test-business"
        )
        session.add(business)
        session.commit()
        session.refresh(business)
        
        # 3. Link them with a Membership
        membership = Membership(
            user_id=user.id,
            business_id=business.id,
            role=MembershipRole.OWNER
        )
        session.add(membership)
        session.commit()
        
        # 4. Query back to verify the data was saved correctly
        db_user = session.query(User).filter_by(email="test@sellflow.com").first()
        assert db_user is not None
        assert db_user.full_name == "Test User"
        
        db_business = session.query(Business).filter_by(slug="test-business").first()
        assert db_business is not None
        
        db_membership = session.query(Membership).filter_by(
            user_id=db_user.id, 
            business_id=db_business.id
        ).first()
        assert db_membership is not None
        assert db_membership.role == MembershipRole.OWNER
        
        # 5. Cleanup: delete the test data so the database stays clean for future tests
        session.delete(db_membership)
        session.delete(db_business)
        session.delete(db_user)
        session.commit()
