# SELLFLOW Deployment Guide

## Quick Start

### 1. Set Up Render Backend

**Option A: Using render.yaml (Recommended)**
```bash
# Commit the render.yaml file
git add backend/render.yaml
git commit -m "Add Render deployment config"
git push
```

**Option B: Manual Setup**
1. Go to https://dashboard.render.com/
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name:** sellflow-api
   - **Region:** Oregon (or closest to your users)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 2. Set Environment Variables

In Render dashboard → Your Service → **Environment**:

| Key | Value |
|-----|-------|
| SECRET_KEY | Generate a random 32+ char string |
| DATABASE_URL | `postgresql+psycopg://user:pass@host:5432/db` |
| APP_ENV | `production` |
| APP_DEBUG | `false` |

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Get DATABASE_URL:**
- If using Render Database: Copy from database dashboard
- If using external: Get credentials from your provider

### 3. Connect Database

**Option A: Render Database (Easiest)**
1. In Render dashboard → "New +" → "Database"
2. Choose PostgreSQL
3. Copy the `DATABASE_URL` from database settings
4. Add to your web service environment variables

**Option B: External PostgreSQL**
- Use Railway, Supabase, Neon, or your own server
- Get connection string and add to environment

### 4. Deploy

Render will automatically deploy on git push.

**Check deployment:**
1. Go to Service → **Logs**
2. Look for "Application startup complete"
3. Visit your service URL

### 5. Test API

```bash
# Health check
curl https://your-backend.onrender.com/status

# Check docs
curl https://your-backend.onrender.com/docs
```

### 6. Update Flutter App

Edit `sellflow_app/lib/core/config/env.dart`:
```dart
class Env {
  static const String baseUrl = 'https://your-backend.onrender.com/api/v1';
  static const String appTitle = 'SellFlow';
}
```

Then:
```bash
cd sellflow_app
flutter clean
flutter pub get
flutter run
```

## Migration on First Deploy

Add to your build process (render.yaml or manual):

**Option A: In render.yaml**
```yaml
buildCommand: |
  pip install -r requirements.txt
  alembic upgrade head
```

**Option B: After deploy via Render Shell**
1. Go to Service → **Dashboard** → **Console**
2. Run: `alembic upgrade head`

## Verify Everything Works

1. **Backend is up:**
   - Visit: `https://your-backend.onrender.com/status`
   - Should return JSON with status "ok"

2. **Create test user:**
```bash
curl -X POST https://your-backend.onrender.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Test User",
    "phone": "1234567890",
    "business_name": "Test Business",
    "password": "1234"
  }'
```

3. **Login and get token:**
```bash
curl -X POST https://your-backend.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "1234"}'
```

## Common Issues

### 503 Service Unavailable
- Check logs for errors
- Verify environment variables are set
- Database connection may be failing

### Migration Errors
```bash
# Run manually in Render console
alembic upgrade head
```

### Database Connection Failed
- Check DATABASE_URL format
- Verify PostgreSQL is running
- Check credentials

### CORS Errors
Backend already allows all origins. Check frontend URL matches Env.baseUrl

## Security Checklist

- [ ] SECRET_KEY is random and not committed to git
- [ ] APP_DEBUG=false in production
- [ ] DATABASE_URL is in environment (not hardcoded)
- [ ] Database has proper backups enabled
- [ ] Consider adding rate limiting (already implemented)

## Updating Deployment

```bash
# Make changes
git add .
git commit -m "Description of changes"
git push

# Monitor logs for deployment
# Render automatically deploys on push
```

---

Need help? Check the logs in Render dashboard for error messages.
