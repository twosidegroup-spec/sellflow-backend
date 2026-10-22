# International Payment Reconciliation System

## What Was Added

The payment reconciliation system now supports **both local (Bangladesh) and international payment gateways**.

## Supported Payment Methods

### Local (Bangladesh)
- bKash
- Nagad
- Rocket
- Upay

### International
- **PayPal** - Global
- **Cash App** - USA
- **Stripe** - Global
- **Wise** - Global

## New Features

1. **Gateway-Aware Normalization**
   - Automatically handles different transaction ID formats (PayPal `id`, bKash `trx_id`, Stripe `pi_...`)
   - Converts amounts (Stripe uses cents, PayPal uses decimals)
   - Handles different date formats

2. **Multi-Currency Support**
   - Local transactions: BDT
   - International transactions: USD (default), can be extended

3. **Single API for All Gateways**
   - Same endpoints work for bKash, PayPal, Stripe, etc.
   - Mobile app doesn't need separate code for different gateways

## API Usage

### Mobile Payment Verification (Works for ALL gateways)

```json
POST /api/v1/businesses/{business_id}/orders/{order_id}/payments/reconcile-mobile
{
  "transaction_id": "PAYPAL_TRX_123",
  "amount": 99.99,
  "method": "paypal"
}
```

### Batch Reconciliation (Works for ALL gateways)

```json
POST /api/v1/businesses/{business_id}/orders/{order_id}/payments/reconcile
{
  "gateway": "paypal",
  "transactions": [
    {
      "id": "PAYPAL_TRX_123",
      "amount": {"value": "99.99", "currency": "USD"},
      "payer": {"email_address": "buyer@example.com"},
      "create_time": "2026-10-22T10:30:00Z"
    }
  ]
}
```

## Changes Made

| File | Changes |
|------|---------|
| `app/payments/schemas.py` | Added PaymentMethod enum with international methods |
| `app/payments/reconciliation.py` | Added `normalize_gateway_transaction()` for multi-gateway support |
| `app/payments/router.py` | Updated to support all gateway methods |
| `RECONCILIATION.md` | Updated documentation with international examples |

## Test Status

```
25 passed, 1 warning
```

All existing tests pass with international payment methods added.

## Next Steps

1. **For Mobile Developers:** Use the same API endpoints for local and international payments
2. **For Admins:** Import gateway reports using the batch reconciliation endpoint
3. **For Operations:** Monitor `/reconciliation/status` for pending international transactions

---

**Status:** ✅ Ready for both local (Bangladesh) and international payment reconciliation.
