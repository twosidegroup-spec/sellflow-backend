# SellFlow API Documentation

## Overview

Base URL: `http://localhost:8000/api/v1`

All endpoints return JSON. Protected endpoints require JWT authentication.

## Authentication

### POST /auth/register

Create a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe",
  "phone": "+1234567890",
  "business_name": "My Business"
}
```

**Response (201):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "business_id": 1,
  "business_name": "My Business"
}
```

### POST /auth/login

Authenticate user and receive JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIU...",
  "token_type": "bearer"
}
```

### GET /auth/me

Get current user profile (requires auth).

**Response (200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "phone": "+1234567890"
}
```

## Businesses

### GET /businesses/

List businesses accessible by current user.

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "My Business",
    "slug": "my-business-abc123"
  }
]
```

### GET /businesses/{id}

Get business details.

## Products

### GET /businesses/{business_id}/products

List all products for a business.

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "Product Name",
    "sku": "SKU001",
    "stock": 100,
    "unit_price": 99.99,
    "cost_price": 50.00
  }
]
```

### POST /businesses/{business_id}/products

Create a new product.

**Request:**
```json
{
  "name": "New Product",
  "sku": "SKU002",
  "stock": 50,
  "unit_price": 149.99,
  "cost_price": 75.00
}
```

### PUT /businesses/{business_id}/products/{id}

Update product.

### DELETE /businesses/{business_id}/products/{id}

Delete product.

## Customers

### GET /businesses/{business_id}/customers

List customers for a business.

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "Customer Name",
    "phone": "+1234567890",
    "email": "customer@example.com"
  }
]
```

### POST /businesses/{business_id}/customers

Create a customer.

**Request:**
```json
{
  "name": "New Customer",
  "phone": "+1987654321",
  "email": "new@example.com"
}
```

## Orders

### GET /businesses/{business_id}/orders

List orders.

**Response (200):**
```json
[
  {
    "id": 1,
    "status": "pending",
    "total": 299.97,
    "items": [
      {
        "product_id": 1,
        "quantity": 3,
        "unit_price": 99.99,
        "cost_price": 50.00
      }
    ],
    "customer": {
      "id": 1,
      "name": "Customer Name"
    }
  }
]
```

### POST /businesses/{business_id}/orders

Create an order.

**Request:**
```json
{
  "customer_id": 1,
  "items": [
    {
      "product_id": 1,
      "quantity": 3,
      "unit_price": 99.99,
      "cost_price": 50.00
    }
  ]
}
```

### PATCH /businesses/{business_id}/orders/{id}/status

Update order status.

**Request:**
```json
{
  "status": "completed"
}
```

**Status values:** `pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled`

## Payments

### GET /businesses/{business_id}/payments

List payments.

**Response (200):**
```json
[
  {
    "id": 1,
    "order_id": 1,
    "amount": 299.97,
    "method": "bkash",
    "transaction_ref": "BKASH123456",
    "created_at": "2026-10-22T10:30:00Z"
  }
]
```

### POST /businesses/{business_id}/payments

Record a payment.

**Request:**
```json
{
  "order_id": 1,
  "amount": 299.97,
  "method": "bkash",
  "transaction_ref": "BKASH123456"
}
```

**Payment methods:** `bkash`, `nagad`, `rocket`, `upay`, `cash`

## Deliveries

### GET /businesses/{business_id}/deliveries

List deliveries.

**Response (200):**
```json
[
  {
    "id": 1,
    "order_id": 1,
    "address": "123 Main St",
    "city": "Dhaka",
    "postal_code": "1200",
    "phone": "+1234567890"
  }
]
```

### POST /businesses/{business_id}/deliveries

Create a delivery.

**Request:**
```json
{
  "order_id": 1,
  "address": "456 Park Ave",
  "city": "Dhaka",
  "postal_code": "1215",
  "phone": "+1234567890"
}
```

## Analytics

### GET /businesses/{business_id}/analytics/summary

Get dashboard summary.

**Response (200):**
```json
{
  "total_revenue": 5000.00,
  "total_orders": 150,
  "total_customers": 75,
  "total_products": 50,
  "total_profit": 1500.00
}
```

## Error Responses

All errors return consistent JSON:

```json
{
  "detail": "Error message here"
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `204` - No Content (delete)
- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (no access)
- `404` - Not Found
- `429` - Too Many Requests (rate limit)
- `500` - Internal Server Error

## Rate Limiting

- **Login:** 10 requests per 15 minutes
- **Register:** 5 requests per hour

## Tenant Isolation

All business-scoped endpoints enforce multi-tenancy. Users can only access data from businesses they belong to (owner/admin/member).
