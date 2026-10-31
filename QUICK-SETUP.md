# Quick Setup Guide

## 1️⃣ Generate SECRET_KEY

```bash
# Run this in terminal:
openssl rand -hex 32
```

**Output example:** `a3f5c8d9e2b1f4a7c3e6d9b2f5a8c1e4d7b0f3a6c9e2b5d8f1a4c7e0d3b6f9a2`

---

## 2️⃣ Set Up Environment Variables

```bash
# Copy to .env
cp .env.example .env

# Edit .env and add:
SECRET_KEY=a3f5c8d9e2b1f4a7...  # Paste generated key above
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/sellflow_db
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://your-mobile-app.com
```

---

## 3️⃣ Start Server

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

---

## 4️⃣ Verify

```bash
# Test app
curl http://localhost:8000/api/v1/auth/test

# Test health
curl http://localhost:8000/health
```

**Expected:** `{"status": "ok", "message": "Backend connection successful!"}`

---

## ✅ Checklist

- [ ] Generated SECRET_KEY
- [ ] Created .env file
- [ ] Set DATABASE_URL
- [ ] Added .env to .gitignore
- [ ] Ran migrations
- [ ] Server starts successfully

---

**For Production:**
- See `DEPLOYMENT.md`
- Set environment variables in your hosting platform
- Never commit .env to Git
