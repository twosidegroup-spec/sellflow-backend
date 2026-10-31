# 🛡️ PRODUCTION CONFIGURATION GUIDE

## ✅ What We Fixed

| Issue | Before | After |
|-------|--------|-------|
| **SECRET_KEY** | Hardcoded weak value | Uses environment variable |
| **DATABASE_URL** | Hardcoded localhost | Uses environment variable |
| **APP_ENV** | Hardcoded development | Uses environment variable |
| **APP_DEBUG** | Hardcoded True | Uses environment variable |
| **CORS_ORIGINS** | Hardcoded `*` | Uses environment variable |
| **.gitignore** | Missing .env | .env now excluded |

---

## 📋 Before Deployment Checklist

### 1. Generate SECRET_KEY
```bash
openssl rand -hex 32
```
**Save this!** You need it for deployment.

### 2. Create Production `.env` File
```bash
cp .env.example .env
```

Edit `.env` with:
```
SECRET_KEY=a3f5c8d9... (your generated key)
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/sellflow_db
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://your-mobile-app.com
```

### 3. Verify .env is in .gitignore
```
✅ Already added: .env
✅ Already added: .env.local
```

### 4. Cloud Storage (Optional)
For file uploads in production:
- **Local storage**: Files deleted on restart ❌
- **Cloud storage**: Files persist ✅

Use Cloudflare R2 or AWS S3 for production.

---

## 🚀 Deploy to Render

### Environment Variables
Add to Render Dashboard → Settings → Environment Variables:
```
SECRET_KEY=a3f5c8d9e2b1f4a7...
DATABASE_URL=postgresql://user:pass@host:5432/sellflow_db
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://your-mobile-app.com
```

### Build & Start Commands
```
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 🔍 Verify Deployment

```bash
# Test health check
curl https://your-app.onrender.com/health

# Test auth endpoint
curl https://your-app.onrender.com/api/v1/auth/test
```

**Expected Response:** `{"status": "ok"}`

---

## ⚠️ Critical Security Notes

| Item | Risk | Status |
|------|------|--------|
| SECRET_KEY | High - Must change before deploy | ✅ Fixed |
| DATABASE_URL | Medium - Uses env var | ✅ Fixed |
| .env in Git | High - Never commit | ✅ Added to .gitignore |
| CORS Origins | Medium - Restrict in prod | ✅ Fixed |
| SSL/TLS | Low - Auto on Render | ✅ Auto |

---

## 📁 Files Modified

| File | Change |
|------|--------|
| `app/core/config.py` | Now uses environment variables |
| `.env.example` | Updated with production guidance |
| `.gitignore` | Added .env exclusions |
| `Dockerfile` | Updated to exclude .env |
| `DEPLOYMENT.md` | Added production checklist |
| `QUICK-SETUP.md` | Added quick start guide |

---

## ✅ Final Verification

Run this before deploying:

```bash
cd backend
# Test app loads
python -c "from app.main import app; print('App: OK')"

# Test models load
python -c "from app.db.base import *; print('Models: OK')"

# Test all tests pass
pytest tests/ -q --tb=no
```

**Expected:** `31 passed`

---

**You're ready to deploy!** 🚀
