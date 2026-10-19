# SELLFLOW Backend

Seller Execution Engine for social commerce.

## Overview

The backend is a FastAPI-based REST API that provides all the core functionality for the SELLFLOW platform. It handles:

- User authentication and authorization (JWT-based)
- Multi-tenant business management
- Product catalog management
- Customer relationship management
- Order processing and tracking
- Payment processing
- Delivery management
- Business analytics

## Tech Stack

- **Framework**: FastAPI 0.115.0
- **Database**: PostgreSQL with SQLAlchemy 2.0 ORM
- **Migrations**: Alembic 1.13.3
- **Authentication**: JWT (python-jose)
- **Password Hashing**: Bcrypt

## API Structure

All API endpoints are prefixed with `/api/v1` and organized by domain:

| Route | Description |
|-------|-------------|
| `/auth/*` | User authentication (register, login) |
| `/businesses/{business_id}/*` | Business-specific resources |
|   `/products` | Product CRUD operations |
|   `/customers` | Customer management |
|   `/orders` | Order processing |
|   `/payments` | Payment transactions |
|   `/deliveries` | Delivery tracking |
|   `/analytics/summary` | Business analytics |

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Docker (optional, for development)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (copy and modify `.env.example`):
```bash
cp .env.example .env
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Documentation

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

Run tests with pytest:
```bash
pytest
```

## Docker

Run with Docker Compose:
```bash
docker-compose up -d
```

## Project Structure

```
backend/
├── app/
│   ├── auth/          # Authentication & user management
│   ├── businesses/    # Business entity & memberships
│   ├── products/      # Product catalog
│   ├── customers/     # Customer management
│   ├── orders/        # Order processing
│   ├── payments/      # Payment processing
│   ├── deliveries/    # Delivery tracking
│   ├── analytics/     # Business analytics
│   ├── core/          # Shared utilities (security, config)
│   ├── db/            # Database models & migrations
│   └── main.py        # Application entry point
├── tests/             # Test suite
├── alembic/           # Database migrations
├── requirements.txt   # Python dependencies
└── docker-compose.yml # Docker configuration
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SECRET_KEY` | JWT signing secret | Yes |
| `APP_ENV` | Environment (development/production) | No |

## License

MIT
