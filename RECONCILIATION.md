# Payment Reconciliation System

## Overview

A comprehensive payment reconciliation system for mobile platforms (iOS/Android) that verifies and matches mobile payment transactions against gateway reports.

## Features

- **Mobile Payment Verification**: Verify single transactions from mobile apps
- **Batch Reconciliation**: Reconcile entire gateway reports against local records
- **Discrepancy Detection**: Automatically identify unmatched transactions
- **Auto-Reconciliation**: Create missing payment records from gateway data
- **Status Tracking**: Track payment status (pending, verified, failed)
- **Multi-Gateway Support**: bKash, Nagad, Rocket, Upay

## API Endpoints

### Mobile Payment Verification

Verify a single payment from iOS/Android app:

```http
POST /api/v1/businesses/{business_id}/orders/{order_id}/payments/reconcile-mobile
Content-Type: application/json

{
  "transaction_id": "TRX123456789",
  "amount": 999.99,
  "method": "bkash",
  "order_id": 123
}
```

**Response:**
```json
{
  "verified": true,
  "status": "verified",
  "amount": 999.99,
  "order_id": 123,
  "paid_at": "2026-10-22T10:30:00Z"
}
```

### Batch Reconciliation

Reconcile a gateway report against local records:

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
      "paid_at": "2026-10-22T10:30:00Z",
      "order_id": 123
    }
  ]
}
```

**Response:**
```json
{
  "total_transactions": 1,
  "matched": 1,
  "unmatched_remote": [],
  "unmatched_local": [],
  "amount_mismatches": [],
  "status_mismatches": [],
  "processed_at": "2026-10-22T12:00:00Z"
}
```

### Process Unmatched Transactions

Auto-create missing payment records:

```http
POST /api/v1/businesses/{business_id}/orders/{order_id}/payments/process-unmatched?gateway=bkash&auto_verify=true
```

### Reconciliation Status

Get current status for all payment methods:

```http
GET /api/v1/businesses/{business_id}/orders/{order_id}/payments/reconciliation/status
```

### Reconciliation Report

Generate a full reconciliation report:

```http
GET /api/v1/businesses/{business_id}/orders/{order_id}/payments/reconciliation-report?gateway=bkash&days=30
```

## Mobile Integration

### iOS Example

```swift
import Foundation

struct PaymentVerification: Codable {
    let transactionId: String
    let amount: Decimal
    let method: String
    let orderId: Int?
}

func verifyPayment(transactionId: String, amount: Decimal, method: String) async throws -> Bool {
    let request = PaymentVerification(
        transactionId: transactionId,
        amount: amount,
        method: method,
        orderId: nil
    )
    
    let url = URL(string: "https://api.sellflow.com/api/v1/businesses/\(businessId)/orders/\(orderId)/payments/reconcile-mobile")!
    var urlRequest = URLRequest(url: url)
    urlRequest.httpMethod = "POST"
    urlRequest.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
    urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
    urlRequest.httpBody = try JSONEncoder().encode(request)
    
    let (data, response) = try await URLSession.shared.data(for: urlRequest)
    
    if let httpResponse = response as? HTTPURLResponse,
       (200...299).contains(httpResponse.statusCode) {
        let result = try JSONDecoder().decode(PaymentVerificationResponse.self, from: data)
        return result.verified
    }
    
    throw URLError(.badServerResponse)
}
```

### Android Example

```kotlin
data class PaymentVerification(
    val transaction_id: String,
    val amount: BigDecimal,
    val method: String,
    val order_id: Int?
)

data class PaymentVerificationResponse(
    val verified: Boolean,
    val status: String,
    val amount: Double?,
    val order_id: Int?,
    val paid_at: String?
)

suspend fun verifyPayment(
    transactionId: String,
    amount: BigDecimal,
    method: String
): Boolean {
    val request = PaymentVerification(
        transaction_id = transactionId,
        amount = amount,
        method = method,
        order_id = null
    )
    
    val client = OkHttpClient()
    val json = Gson().toJson(request)
    
    val body = RequestBody.create(
        MediaType.parse("application/json"),
        json
    )
    
    val request = Request.Builder()
        .url("https://api.sellflow.com/api/v1/businesses/$businessId/orders/$orderId/payments/reconcile-mobile")
        .post(body)
        .addHeader("Authorization", "Bearer $accessToken")
        .addHeader("Content-Type", "application/json")
        .build()
    
    client.newCall(request).execute().use { response ->
        if (response.isSuccessful) {
            val responseData = response.body?.string()
            val result = Gson().fromJson(responseData, PaymentVerificationResponse::class.java)
            return result.verified
        }
    }
    
    throw IOException("Network request failed")
}
```

## Payment Status Workflow

```
PENDING (created) → VERIFIED (reconciled) → COMPLETED (order fulfilled)
                    ↓
                 FAILED (rejected)
```

## Gateway Report Format

Expected JSON format for gateway reports:

```json
{
  "transactions": [
    {
      "transaction_id": "TRX123456789",
      "amount": "999.99",
      "method": "bkash",
      "status": "completed",
      "paid_at": "2026-10-22T10:30:00Z",
      "order_id": 123
    }
  ]
}
```

## Database Schema

### Payment Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| business_id | INTEGER | Business identifier |
| order_id | INTEGER | Order identifier |
| amount | NUMERIC(12,2) | Payment amount |
| method | VARCHAR(50) | Payment method |
| transaction_id | VARCHAR(255) | Gateway transaction ID |
| status | ENUM | PENDING, VERIFIED, FAILED, REFUNDED |
| paid_at | TIMESTAMP | Payment timestamp |
| verified_at | TIMESTAMP | Reconciliation timestamp |

### Reconciliation Runs Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| business_id | INTEGER | Business identifier |
| gateway | VARCHAR(50) | Gateway name |
| status | VARCHAR(20) | pending, completed, failed |
| total_transactions | INTEGER | Total transactions processed |
| matched | INTEGER | Matched transactions |
| unmatched_count | INTEGER | Unmatched transactions |
| discrepancy_amount | NUMERIC(12,2) | Total discrepancy |

## Error Handling

| Error | Status | Description |
|-------|--------|-------------|
| Order not found | 404 | Invalid order ID |
| Transaction not found | 404 | Transaction ID doesn't exist |
| Amount mismatch | 400 | Payment amount doesn't match |
| Duplicate transaction | 409 | Transaction already recorded |
