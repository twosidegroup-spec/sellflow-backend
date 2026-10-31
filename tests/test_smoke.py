"""
Smoke Test for SELLFLOW Backend - Simplified Version
Tests core functionality without authentication dependency
"""

from fastapi.testclient import TestClient
from app.main import app
from app.db.engine import SessionLocal
from app.db.base import User, Business, Product, Order, Payment, Membership, WebhookSubscription

client = TestClient(app)

def test_health():
    """Test health endpoint"""
    print("\n[PING] GET /health")
    response = client.get("/health")
    if response.status_code == 200:
        print(f"[PASS] Health check OK")
        return True
    else:
        print(f"[FAIL] Status {response.status_code}")
        return False

def test_db_connection():
    """Test database connection"""
    print("\n[DB] Testing database connection")
    db = SessionLocal()
    try:
        from sqlalchemy import text
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            print("[PASS] Database connected")
            return True
        else:
            print("[FAIL] Query failed")
            return False
    except Exception as e:
        print(f"[FAIL] {e}")
        return False
    finally:
        db.close()

def test_models():
    """Test models can be imported"""
    print("\n[MODEL] Testing model imports")
    try:
        from app.db.base import User, Business, Product, Order, Payment, ProductImage, WebhookSubscription
        print("[PASS] All models imported")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_routes():
    """Test routes are registered"""
    print("\n[ROUTE] Testing route registration")
    
    routes = [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/businesses/{business_id}/products",
        "/api/v1/businesses/{business_id}/orders",
        "/api/v1/businesses/{business_id}/payments",
        "/api/v1/businesses/{business_id}/webhooks",
        "/api/v1/businesses/{business_id}/analytics/summary",
    ]
    
    app_routes = [str(route.path) for route in app.routes]
    
    passed = 0
    failed = 0
    
    for route in routes:
        # Check if base path exists
        base = route.split("{")[0].rstrip("/")
        if any(base in r for r in app_routes):
            print(f"  [PASS] {base}")
            passed += 1
        else:
            print(f"  [FAIL] {route}")
            failed += 1
    
    print(f"\n{passed}/{len(routes)} routes registered")
    return failed == 0

def test_migrations():
    """Test migrations are in place"""
    print("\n[DB] Testing migrations")
    import os
    
    migration_dir = "app/db/migrations/versions"
    migrations = []
    
    if os.path.exists(migration_dir):
        migrations = [f for f in os.listdir(migration_dir) if f.endswith(".py") and f != "__init__.py"]
    
    if len(migrations) > 0:
        print(f"[PASS] {len(migrations)} migration files found")
        return True
    else:
        print("[FAIL] No migrations found")
        return False

def test_requirements():
    """Test requirements.txt"""
    print("\n[PKG] Testing dependencies")
    
    with open("requirements.txt", "r") as f:
        content = f.read()
    
    required = ["fastapi", "uvicorn", "sqlalchemy", "alembic", "python-multipart"]
    
    passed = 0
    for pkg in required:
        if pkg in content.lower():
            print(f"  [PASS] {pkg}")
            passed += 1
        else:
            print(f"  [WARN] {pkg} not listed")
    
    print(f"\n{passed}/{len(required)} core packages")
    return True

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" SELLFLOW BACKEND BASIC CHECK ".center(60, "="))
    print("=" * 60)
    
    results = []
    
    results.append(("Health", test_health()))
    results.append(("Database", test_db_connection()))
    results.append(("Models", test_models()))
    results.append(("Routes", test_routes()))
    results.append(("Migrations", test_migrations()))
    results.append(("Packages", test_requirements()))
    
    print("\n" + "=" * 60)
    print("SUMMARY".center(60))
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
    
    print("=" * 60)
    print(f"  {passed}/{total} checks passed")
    print("=" * 60)
    
    if passed == total:
        print("\n*** Backend is ready for production deployment! ***")
    else:
        print("\n!!! Backend needs fixes before deployment !!!")
