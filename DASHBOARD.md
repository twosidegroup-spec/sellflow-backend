# SELLFLOW Dashboard

## 🚀 Quick Start

### Run Dashboard
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Dashboard URL:** http://localhost:8000/dashboard

---

## 📱 Pages

| Page | URL | Features |
|------|-----|----------|
| **Dashboard** | `/dashboard/` | Stats overview, app info |
| **Orders** | `/dashboard/orders` | View all orders |
| **Products** | `/dashboard/products` | View all products |
| **Customers** | `/dashboard/customers` | View all customers |
| **Payments** | `/dashboard/payments` | View all payments |
| **Settings** | `/dashboard/settings` | App settings |

---

## 🎨 Features

### Light/Dark Mode
- Built-in theme toggle
- Saves preference in localStorage
- System preferences respected

### Dashboard Info
- **App Name:** SELLFLOW
- **Version:** 1.0.0
- **Bio:** E-commerce management platform for social commerce
- **Stats:** Real-time counts for users, businesses, products, orders, payments

---

## 🛠️ Technical

**Framework:** FastAPI  
**Templates:** Jinja2  
**Styling:** CSS Variables (dark/light mode)  
**Database:** PostgreSQL with SQLAlchemy  

---

## 📊 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/auth/register` | User registration |
| `GET /api/v1/auth/login` | User login |
| `GET /dashboard/` | Dashboard HTML |
| `GET /dashboard/orders` | Orders page |
| `GET /dashboard/products` | Products page |
| `GET /dashboard/customers` | Customers page |
| `GET /dashboard/payments` | Payments page |
| `GET /dashboard/settings` | Settings page |

---

## ✅ Status

- [x] All pages created
- [x] Dark/light mode toggle
- [x] Statistics displayed
- [x] App version & bio shown
- [x] Tests passing (31/31)

---

**Dashboard is ready to use!** 🎉
