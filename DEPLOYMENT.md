# Production Deployment Checklist

## ✅ STEP 1: Generate SECRET_KEY (REQUIRED)

```bash
# On Windows (PowerShell):
openssl rand -hex 32

# On Mac/Linux:
openssl rand -hex 32
```

**Save this key - you'll need it for deployment!**

---

## ✅ STEP 2: Update `.env` File

```bash
# Copy example file
cp .env.example .env

# Edit .env with your values
# - Update SECRET_KEY with the generated key above
# - Update DATABASE_URL with your production database
# - Update CORS_ORIGINS with your mobile app URL
```

**⚠️ IMPORTANT:** Add `.env` to `.gitignore` so you don't commit secrets to GitHub!

---

## ✅ STEP 3: Configure Production Database

### Option A: Use Supabase (Recommended)
1. Create project at [supabase.com](https://supabase.com)
2. Get connection string from Settings → Database
3. Set `DATABASE_URL` in your hosting platform

### Option B: Use Render PostgreSQL
1. Add PostgreSQL addon to your Render service
2. Render auto-sets `DATABASE_URL` environment variable
3. No changes needed to your code

---

## ✅ STEP 4: Configure Cloud Storage (Optional but Recommended)

### Local (Development Only)
Files are stored in `backend/uploads/` folder
- ❌ Files disappear on server restart
- ❌ Not available to multiple servers

### Cloud Storage (Production)
#### Option A: Cloudflare R2 (Free tier available)
1. Create account at [cloudflare.com](https://cloudflare.com/r2)
2. Create bucket
3. Get access keys from Settings → API Tokens
4. Update `.env`:
```
AWS_ACCESS_KEY_ID=your-key-id
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=auto
AWS_S3_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
```

#### Option B: AWS S3
1. Create bucket
2. Get access keys from IAM
3. Update `.env`:
```
AWS_ACCESS_KEY_ID=your-key-id
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1
```

**Note:** Full R2/S3 integration needs to be added to upload_router.py
(See `docs/CLOUD-STORAGE.md` for implementation)

---

## ✅ STEP 5: Deploy to Render

### Environment Variables (in Render Dashboard)
```
SECRET_KEY=a3f5c8d9... (your generated key)
DATABASE_URL=postgresql://user:pass@host:5432/db
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://your-mobile-app.com
```

### Build Command
```
pip install -r requirements.txt
```

### Start Command
```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## ✅ STEP 6: Run Migrations (After First Deploy)

In Render Dashboard → Deployments → Access Shell
```bash
alembic upgrade head
```

---

## ✅ STEP 7: Verify Deployment

1. Check health endpoint: `https://your-app.onrender.com/health`
2. Test registration: `https://your-app.onrender.com/api/v1/auth/register`
3. Verify database connection in logs
4. Test file upload if using local storage

---

## 🔒 Security Checklist

- [ ] SECRET_KEY is unique and strong (32+ chars)
- [ ] DATABASE_URL not committed to Git
- [ ] .env file is in .gitignore
- [ ] APP_DEBUG=false in production
- [ ] CORS_ORIGINS restricted to your domains
- [ ] SSL enabled (Render provides this automatically)

---

## 📝 Post-Deployment

1. **Monitor Logs**: Watch for errors in Render dashboard
2. **Test Mobile App**: Connect your Flutter app to new URL
3. **Set Up Monitoring**: Consider adding Sentry or similar
4. **Database Backups**: Enable automatic backups
5. **Plan Scaling**: Monitor usage and adjust resources

---

## 🚨 Before Going Live

| Item | Status |
|------|--------|
| SECRET_KEY changed | [ ] |
| DATABASE_URL configured | [ ] |
| CORS restricted | [ ] |
| APP_DEBUG=false | [ ] |
| Cloud storage configured | [ ] |
| Migrations run | [ ] |

---

**Need Help?**
- See `DEPLOYMENT.md` for platform-specific guides
- See `CLOUD-STORAGE.md` for file storage options
