# Payment Reconciliation System (Local & International)

## Overview

A comprehensive payment reconciliation system supporting **both local and international payment gateways**. Designed for iOS/Android mobile apps and batch processing.

## Supported Payment Gateways

| Gateway | Type | Region | Status |
|---------|------|--------|--------|
| **bKash** | Local | Bangladesh | ✅ Supported |
| **Nagad** | Local | Bangladesh | ✅ Supported |
| **Rocket** | Local | Bangladesh | ✅ Supported |
| **Upay** | Local | Bangladesh | ✅ Supported |
| **PayPal** | International | Global | ✅ Supported |
| **Cash App** | International | USA | ✅ Supported |
| **Stripe** | International | Global | ✅ Supported |
| **Wise** | International | Global | ✅ Supported |

---

## API Endpoints

### 1. Get Supported Gateways

```http
GET /api/v1/businesses/{business_id}/payments/supported-gateways
```

**Response:**
```json
[
  {
    "name": "bKash",
    "code": "bkash",
    "type": "local",
    "country": "Bangladesh",
    "supports_reconciliation": true
  },
  {
    "name": "PayPal",
    "code": "paypal",
    "type": "international",
    "country": "Global",
    "supports_reconciliation": true
  },
  {
    "name": "Stripe",
    "code": "stripe",
    "type": "international",
    "country": "Global",
    "supports_reconciliation": true
  }
]
```

### 2. Mobile Payment Verification (Single Transaction)

```http
POST /api/v1/businesses/{business_id}/orders/{order_id}/payments/reconcile-mobile
Content-Type: application/json

{
  "transaction_id": "TRX123456789",
  "amount": 999.99,
  "method": "bkash"
}
```

**Works for International Payments:**
```json
{
  "transaction_id": "3C679366HH908993F",
  "amount": 99.99,
  "method": "paypal"
}
```

### 3. Batch Reconciliation (Import Gateway Report)

```http
POST /api/v1/businesses/{business_id}/orders/{order_id}/payments/reconcile
Content-Type: application/json

{
  "gateway": "bkash",
  "transactions": [
    {
      "transaction_id": "TRX123456789",
      "amount": 999.99,
      "method": "bkash",
      "status": "completed",
      "paid_at": "2026-10-22T10:30:00Z"
    }
  ]
}
```

**For PayPal:**
```json
{
  "gateway": "paypal",
  "transactions": [
    {
      "id": "3C679366HH908993F",
      "amount": {
        "value": "99.99",
        "currency": "USD"
      },
      "payer": {
        "email_address": "buyer@example.com"
      },
      "create_time": "2026-10-22T10:30:00Z",
      "metadata": {
        "order_id": "123"
      }
    }
  ]
}
```

**For Stripe:**
```json
{
  "gateway": "stripe",
  "transactions": [
    {
      "id": "pi_1234567890",
      "amount": 9999,
      "currency": "usd",
      "customer_email": "buyer@example.com",
      "created": 1698064200,
      "metadata": {
        "order_id": "123"
      }
    }
  ]
}
```

### 4. Reconciliation Status

```http
GET /api/v1/businesses/{business_id}/orders/{order_id}/payments/reconciliation/status
```

**Response:**
```json
{
  "business_id": 1,
  "payment_methods": {
    "bkash": {"total": 10, "verified": 8, "pending": 2},
    "paypal": {"total": 15, "verified": 14, "pending": 1},
    "stripe": {"total": 5, "verified": 5, "pending": 0}
  }
}
```

---

## Gateway-Specific Data Format

| Gateway | Transaction ID Field | Amount Field | Notes |
|---------|----------------------|--------------|-------|
| **bKash** | `trx_id` | `amount` | Local currency |
| **Nagad** | `transaction_id` | `amount` | Local currency |
| **PayPal** | `id` | `amount.value` | USD by default |
| **Cash App** | `id` | `amount` | USD |
| **Stripe** | `id` | `amount` (cents) | Requires `/100 conversion |
| **Wise** | `id` | `amount` | Any currency |

---

## Mobile Integration

### iOS Example

```swift
struct MobilePaymentVerification: Codable {
    let transactionId: String
    let amount: Double
    let method: String // "bkash", "paypal", "stripe"
}

func verifyPayment(transactionId: String, amount: Double, method: String) async throws -> Bool {
    let request = MobilePaymentVerification(
        transactionId: transactionId,
        amount: amount,
        method: method
    )
    
    // ... HTTP request to /reconcile-mobile
    // Handles local AND international payments
}
```

### Android Example

```kotlin
data class MobilePaymentVerification(
    val transaction_id: String,
    val amount: Double,
    val method: String // "bkash", "paypal", "stripe"
)

suspend fun verifyPayment(transactionId: String, amount: Double, method: String) {
    // ... HTTP request to /reconcile-mobile
    // Handles local AND international payments
}
```

---

## Configuration

### Environment Variables

```bash
# Supported payment methods (already defaults to all)
SUPPORTED_METHODS=bkash,nagad,rocket,upay,paypal,cashapp,stripe,wise,cash

# International payment API keys (optional, for real-time verification)
PAYPAL_API_KEY=
STRIPE_API_KEY=
```

---

## Features Summary

✅ **Local Support:** bKash, Nagad, Rocket, Upay
✅ **International Support:** PayPal, Cash App, Stripe, Wise
✅ **Multi-Method:** Single API for all gateways
✅ **Normalization:** Automatically handles different gateway formats
✅ **Discrepancy Detection:** Finds unmatched/mismatched transactions
✅ **Mobile Friendly:** Optimized for iOS/Android apps

---

## Test Results

All backend tests pass with international payment methods added:
```
25 passed, 1 warning
```

---

## Next Steps

1. **Import existing PayPal/Cash App transactions** using `/reconcile`
2. **Update mobile app** to send international payment IDs
3. **Monitor** `/reconciliation/status` for any pending international payments
