# SELLFLOW Backend Deployment

> **Post-migration docs (System A → System B):** see `MIGRATION_REPORT.md`,
> `CANONICAL_ARCHITECTURE.md`, `API_COMPATIBILITY.md`, `MIGRATION_CHECKLIST.md`
> and `SYSTEM_A_COMPONENT_MAPPING.md`. The payment-intelligence engine, device
> bridge (`/device-bridge/*`) and payment accounts (`/payment-accounts/*`) now
> run in this backend. The legacy public endpoints `POST /api/orders`,
> `POST /api/products`, `POST /api/customers` were removed (unauthenticated),
> and `POST /api/v1/payments/detect` is a JWT-authenticated, non-production
> development simulator. Production now requires `SECRET_KEY` and
> `DEVICE_TOKEN_SECRET` (the app refuses to start without them).

## Quick Deploy to Render (Recommended)


### 1. Prepare Environment Variables
```bash
# Generate secret key
openssl rand -hex 32

# In PostgreSQL (Supabase/Render):
CREATE DATABASE sellflow_db;
```

### 2. Configure Render
1. Go to [render.com](https://render.com)
2. Click **New** → **Web Service**
3. Connect your GitHub repository
4. Configure:

| Setting | Value |
|---------|-------|
| Name | `sellflow-backend` |
| Branch | `main` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4` |
| Environment | `Python 3.11` |

### 3. Add Environment Variables
```
DATABASE_URL=postgresql://user:password@host:5432/sellflow_db
SECRET_KEY=your-32-character-secret-key
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://your-app.vercel.app
```

### 4. Run Migrations
After first deploy, run in Render dashboard:
```bash
alembic upgrade head
```

---

## Local Development

### Start Server
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### API Documentation
```
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
```

---

## Cloud Storage (For File Uploads)

**Current Issue:** Files stored locally in `uploads/` directory

**Solution:** Use Cloudflare R2 (free) or AWS S3

### Cloudflare R2 Setup
```env
AWS_ACCESS_KEY_ID=your-r2-key-id
AWS_SECRET_ACCESS_KEY=your-r2-key-secret
AWS_S3_BUCKET_NAME=your-bucket
AWS_REGION=auto
AWS_S3_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
```

---

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py -v

# Check migrations
alembic history
alembic current
```

---

## Troubleshooting

### Connection Issues
```bash
# Check database connection
.venv\Scripts\python.exe -c "from sqlalchemy import create_engine; print(create_engine(DATABASE_URL).connect())"
```

### Migration Issues
```bash
# Reset migration history
alembic downgrade base
alembic upgrade head
```

---

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/login` | User login |
| GET | `/api/v1/businesses/{id}/products` | List products |
| POST | `/api/v1/businesses/{id}/products` | Create product (with upload) |
| POST | `/api/v1/businesses/{id}/payments/reconcile-mobile` | Payment reconciliation |
| POST | `/api/v1/businesses/{id}/webhooks` | Register webhook |
| GET | `/health` | Health check |

---

## Status

- [x] 25/25 tests passing
- [x] Database migrations ready
- [x] API endpoints working
- [x] File upload functionality
- [x] Webhook support
- [ ] Cloud storage integration (S3/R2)
