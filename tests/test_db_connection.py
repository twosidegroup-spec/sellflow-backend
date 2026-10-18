from sqlalchemy import text
from app.db.engine import SessionLocal

def test_database_connection():
    '''Verify that the application can connect to the Docker PostgreSQL database.'''
    with SessionLocal() as session:
        # Execute a simple SQL query
        result = session.execute(text('SELECT 1'))
        assert result.scalar() == 1
