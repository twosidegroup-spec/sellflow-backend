# Payment Transaction Format Quick Reference

## Mobile App Sends (All Gateways - Unified)

```json
POST /api/v1/businesses/{business_id}/payments/reconcile-mobile
{
  "transaction_id": "PAYPAL_TRX_123",
  "amount": 99.99,
  "method": "paypal"
}
```

**Works for:**
- `transaction_id`: Any gateway's transaction ID
- `amount`: Final amount in decimal (not cents)
- `method`: `bkash`, `nagad`, `paypal`, `stripe`, `cashapp`, `wise`

---

## Gateway Returns (Raw - Different Formats)

| Gateway | Transaction ID Field | Amount Field |
|---------|---------------------|--------------|
| bKash | `trx_id` | `amount` |
| PayPal | `id` | `transactions[0].amount.total` |
| Stripe | `id` | `amount` (cents) |
| Cash App | `id` | `amount` |
| Wise | `id` | `amount.amount` |

---

## Backend Normalizes (Internal Format)

```json
{
  "transaction_id": "UNIFIED_TRX_ID",
  "amount": 99.99,
  "method": "gateway_code",
  "status": "completed",
  "paid_at": "ISO_TIMESTAMP"
}
```

**All gateways are converted to this format before reconciliation.**

---

## For Developers

**Mobile App:** Just send the transaction ID and amount. No gateway-specific logic needed.

**Backend:** Uses `normalize_gateway_transaction()` to handle all gateway formats automatically.
