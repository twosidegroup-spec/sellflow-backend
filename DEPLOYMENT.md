# SELLFLOW Deployment Checklist

## Pre-Deployment

### Backend (Render)

- [ ] Verify `requirements.txt` includes all dependencies
- [ ] Set environment variables in Render dashboard:
  - `SECRET_KEY` - Random secure string (min 32 chars)
  - `DATABASE_URL` - PostgreSQL connection string
  - `APP_ENV` = `production`
  - `APP_DEBUG` = `false`
  - `PORT` = `8000`
  - `HOST` = `0.0.0.0`

- [ ] Check `render.yaml` is committed to repository
- [ ] Verify database migrations exist
- [ ] Test API endpoints locally with `uvicorn app.main:app --reload`

### Database (PostgreSQL)

- [ ] Database provisioned (Render managed DB or external)
- [ ] Database credentials in DATABASE_URL
- [ ] Database accepts connections
- [ ] Alembic migrations will run on deploy (add to build script if needed)

## Post-Deployment

### Verification Tests

- [ ] `GET /status` returns `{"status": "ok", "service": "sellflow-api", "version": "0.8.0"}`
- [ ] `GET /docs` loads Swagger UI
- [ ] `POST /api/v1/auth/register` creates user
- [ ] `POST /api/v1/auth/login` returns JWT token
- [ ] `GET /api/v1/auth/me` returns user data

### Flutter App

- [ ] `lib/core/config/env.dart` has correct backend URL
- [ ] Test registration flow
- [ ] Test login flow
- [ ] Verify JWT token is stored and used in requests

## Troubleshooting

### Backend 503 Error
- Check Render logs for crash messages
- Verify DATABASE_URL is correct
- Check SECRET_KEY is set

### Database Connection Errors
- Verify PostgreSQL is running
- Check connection string format
- Ensure credentials are correct

### CORS Issues
- Backend already allows all origins (`allow_origins=["*"]`)
- Check browser console for errors

## Maintenance

### Running Migrations
```bash
# In Render: Add to buildCommand or create deploy hook
alembic upgrade head
```

### Monitoring
- Check Render dashboard for errors
- Monitor database connections
- Review access logs

---
Last Updated: 2026-10-20
