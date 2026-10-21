# Database Setup for Render

## Current Issue

Your backend is running (returns 200 on /status) but returns **500 Internal Server Error** on /api/v1/auth/register

This means the application is running but **database connection is failing**.

---

## Fix: Add Database

### Option 1: Render Database (Recommended)

1. Go to https://dashboard.render.com/
2. Click **New +** → **Database**
3. Select **PostgreSQL**
4. Choose plan (starter is free)
5. Click **Create**

6. After database is created, copy the **DATABASE_URL** from database settings

7. In your web service (sellflow-api):
   - Go to **Environment** tab
   - Add variable: `DATABASE_URL`
   - Value: The connection string from step 6

8. Add this to environment variables:
   ```
   DATABASE_URL=postgresql://user:password@host:port/database
   ```

### Option 2: External PostgreSQL

Use a free PostgreSQL provider:
- https://neon.tech/ (free tier available)
- https://www.supabase.com/ (free tier available)
- https://railway.app/ (free tier available)

Then add DATABASE_URL to Render environment variables.

---

## After Adding Database

1. **Run migrations** in Render console:
   - Go to your service dashboard
   - Click **Console**
   - Run: `alembic upgrade head`

2. **Redeploy** to trigger restart

3. **Test** registration again

---

## Environment Variables Needed

| Variable | Value |
|----------|-------|
| SECRET_KEY | `python -c "import secrets; print(secrets.token_hex(32))"` |
| DATABASE_URL | From Render Database or provider |
| APP_ENV | production |
| APP_DEBUG | false |

---

## Verify Database Connection

After setup, check logs in Render for:
- ✅ "Connection established"
- ✅ "Database migrations applied"
- ❌ "Connection refused" → DATABASE_URL incorrect

---

**Without a database, your backend cannot function properly!** Add a database to complete the setup.
