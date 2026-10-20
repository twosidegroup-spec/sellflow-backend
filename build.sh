#!/bin/bash
set -e

# Force Python 3.13 compatibility
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Build requirements
pip install -r requirements.txt

# Check database connection and run migrations
echo "Checking database connection..."
python -c "
from app.db.engine import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    result = db.execute(text('SELECT 1')).fetchone()
    print(f'Database connected: {result}')
except Exception as e:
    print(f'Database error: {e}')
    exit(1)
finally:
    db.close()
"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Verify tables exist
echo "Verifying tables..."
python -c "
from app.db.engine import SessionLocal
from sqlalchemy import inspect
db = SessionLocal()
try:
    inspector = inspect(db)
    tables = inspector.get_table_names()
    print(f'Tables found: {tables}')
    if 'users' not in tables:
        print('ERROR: users table not found!')
        exit(1)
finally:
    db.close()
"
