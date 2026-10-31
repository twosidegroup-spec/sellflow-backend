# Payment Gateway Transaction Formats

## Overview

Different payment gateways return transaction data in different formats. This document shows the actual JSON structures you'll receive from each gateway.

---

## PayPal

### Webhook/Payment Data
```json
{
  "id": "3C679366HH908993F",
  "intent": "SALE",
  "state": "approved",
  "payer": {
    "payment_method": "paypal",
    "payer_info": {
      "email": "buyer@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "payer_id": "PAYERID123",
      "country_code": "US"
    }
  },
  "transactions": [{
    "amount": {
      "total": "99.99",
      "currency": "USD",
      "details": {
        "subtotal": "89.99",
        "tax": "10.00"
      }
    },
    "description": "Order #123",
    "item_list": {
      "items": [{
        "name": "Product Name",
        "sku": "SKU123",
        "price": "89.99",
        "currency": "USD",
        "quantity": 1
      }]
    }
  }],
  "create_time": "2026-10-22T10:30:00Z",
  "update_time": "2026-10-22T10:30:15Z"
}
```

### Fields to Extract
| Field | Path | Value |
|-------|------|-------|
| transaction_id | `id` | `3C679366HH908993F` |
| amount | `transactions[0].amount.total` | `99.99` |
| method | (static) | `paypal` |
| status | `state` | `approved` |
| paid_at | `create_time` | `2026-10-22T10:30:00Z` |
| payer_email | `payer.payer_info.email` | `buyer@example.com` |

---

## Stripe

### Webhook Event (payment_intent.succeeded)
```json
{
  "id": "evt_1234567890",
  "type": "payment_intent.succeeded",
  "data": {
    "object": {
      "id": "pi_1234567890abcdef",
      "amount": 9999,
      "amount_received": 9999,
      "currency": "usd",
      "status": "succeeded",
      "customer": "cus_1234567890",
      "receipt_email": "buyer@example.com",
      "created": 1698064200,
      "metadata": {
        "order_id": "123"
      }
    }
  },
  "created": 1698064200
}
```

### Fields to Extract
| Field | Path | Value |
|-------|------|-------|
| transaction_id | `data.object.id` | `pi_1234567890abcdef` |
| amount | `data.object.amount` (cents) | `9999` → `99.99` |
| method | (static) | `stripe` |
| status | `data.object.status` | `succeeded` |
| paid_at | `data.object.created` (unix timestamp) | `1698064200` |
| payer_email | `data.object.receipt_email` | `buyer@example.com` |

**Note:** Stripe stores amounts in cents. Divide by 100 for dollar amount.

---

## Cash App

### Webhook/Payment Data
```json
{
  "id": "CASHPAY123456789",
  "amount": "99.99",
  "currency": "USD",
  "status": "COMPLETED",
  "created_at": "2026-10-22T10:30:00Z",
  "completed_at": "2026-10-22T10:30:15Z",
  "merchant_note": "Order #123",
  "payer": {
    "cashtag": "$buyername",
    "display_name": "John Doe"
  },
  "metadata": {
    "order_id": "123"
  }
}
```

### Fields to Extract
| Field | Path | Value |
|-------|------|-------|
| transaction_id | `id` | `CASHPAY123456789` |
| amount | `amount` | `99.99` |
| method | (static) | `cashapp` |
| status | `status` | `COMPLETED` |
| paid_at | `completed_at` | `2026-10-22T10:30:15Z` |

---

## Wise (TransferWise)

### Webhook/Payment Data
```json
{
  "id": "1234567890",
  "type": "TRANSFER",
  "status": "COMPLETED",
  "amount": {
    "amount": "99.99",
    "currency": "USD"
  },
  "sourceCurrency": "USD",
  "targetCurrency": "BDT",
  "created": "2026-10-22T10:30:00Z",
  "finished": "2026-10-22T10:35:00Z",
  "sourceAccount": {
    "id": "123456",
    "accountHolder": "John Doe"
  },
  "targetAccount": {
    "id": "654321",
    "accountHolder": "Merchant Name"
  },
  "reference": "Order #123"
}
```

### Fields to Extract
| Field | Path | Value |
|-------|------|-------|
| transaction_id | `id` | `1234567890` |
| amount | `amount.amount` | `99.99` |
| method | (static) | `wise` |
| status | `status` | `COMPLETED` |
| paid_at | `finished` | `2026-10-22T10:35:00Z` |

---

## Local Gateways (Bangladesh)

### bKash (Webhook/Payment Data)
```json
{
  "trx_id": "TRX123456789",
  "status": "Success",
  "amount": "999.99",
  "merchant_txn": "ORD123",
  "payer_ref": "01712345678",
  "payer_id": "1712345678",
  "created_at": "2026-10-22T10:30:00Z"
}
```

### Nagad (Webhook/Payment Data)
```json
{
  "transaction_id": "NAGAD123456789",
  "transaction_status": "Success",
  "amount": "999.99",
  "order_id": "ORD123",
  "mobile": "01712345678",
  "transaction_date": "2026-10-22T10:30:00Z"
}
```

---

## Summary: What Each Gateway Calls Transaction ID

| Gateway | Field Name | Example |
|---------|------------|---------|
| **bKash** | `trx_id` | `TRX123456789` |
| **Nagad** | `transaction_id` | `NAGAD123456789` |
| **Rocket** | `transaction_id` | `ROCKET123456789` |
| **Upay** | `transaction_id` | `UPAY123456789` |
| **PayPal** | `id` | `3C679366HH908993F` |
| **Cash App** | `id` | `CASHPAY123456789` |
| **Stripe** | `id` | `pi_1234567890abcdef` |
| **Wise** | `id` | `1234567890` |

---

## Summary: What Each Gateway Calls Amount

| Gateway | Field Name | Unit |
|---------|------------|------|
| **bKash** | `amount` | BDT (decimal) |
| **Nagad** | `amount` | BDT (decimal) |
| **PayPal** | `amount.total` | USD (decimal) |
| **Cash App** | `amount` | USD (decimal) |
| **Stripe** | `amount` | USD (cents) |
| **Wise** | `amount.amount` | Any currency |

---

## Implementation Notes

### In `reconciliation.py`, all formats are normalized to:
```json
{
  "transaction_id": "TRX123456789",
  "amount": 999.99,
  "method": "bkash",
  "status": "completed",
  "paid_at": "2026-10-22T10:30:00Z"
}
```

The `normalize_gateway_transaction()` function automatically handles:
- Different field names
- Stripe's cent-based amounts
- Different date formats
- Currency conversion markers
