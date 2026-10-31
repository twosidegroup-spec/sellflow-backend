# API COMPATIBILITY — after the System A → System B migration

System B remains the main API. This document states exactly what works for each
existing client, what changed, and what (if anything) a client must update.

---

## 1. Flutter seller app ("sfm", source in `SELLFLOW/backend/lib`)

**Status: unchanged and compatible**, except one development-only button.

| App feature | Endpoint | Status |
|---|---|---|
| Login (email + 4-digit PIN → `password`) | `POST /api/v1/auth/login` | unchanged |
| Registration (+ `payment_provider`, `receiving_number`) | `POST /api/v1/auth/register` | unchanged request shape; now also creates the canonical `payment_accounts` row for local providers, and is rate limited (5/hour/IP; the app's own retry path is unaffected in normal use) |
| Profile / passkey change | `GET/PUT /api/v1/auth/me`, `POST /api/v1/auth/passcode/change` | unchanged; `PUT /me` now keeps `payment_accounts` in sync |
| Overview / analytics | `GET /api/v1/businesses/{id}/analytics/summary` | unchanged shape; **change**: cancelled orders are no longer counted in `total_revenue`/`total_profit` |
| Products / customers / orders | `/api/v1/businesses/{id}/...` | unchanged |
| Payments list | `GET /api/v1/businesses/{id}/payments` | unchanged |
| Detected payments list | `GET /api/v1/businesses/{id}/payments/detected` | unchanged |
| Reconciliation status | `GET /api/v1/businesses/{id}/payments/reconciliation/status` | unchanged |
| Mobile verify | `POST /api/v1/businesses/{id}/payments/verify-mobile` | unchanged (still reads back the local record) |
| **Settings → "Test incoming payment"** | `POST /api/v1/payments/detect` | **requires an app patch** (below) |

### Required app patch (small)

The simulator call in `lib/features/shared/api_service.dart`
(`simulateIncomingPayment`) must add the JWT header:

```dart
headers: {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer $_token',   // <-- add this line
},
```

Without it the simulator returns 401. The endpoint is also:
* 404 in production (by design — it was a payment-forgery vulnerability),
* limited to the caller's own receiving numbers.

No other app change is required. The app never used the removed endpoints
(`POST /api/orders`, `/api/products`, `/api/customers` — those were only
referenced by the dead mock service `lib/api_service.dart`).

## 2. Kotlin Payment Bridge (`social-commerce-os/.../android-bridge`)

**Status: contract-compatible.** The bridge app is intentionally NOT modified;
the backend exposes the exact paths, methods, request bodies and response keys
it uses. Verified by `tests/test_migration_device_bridge.py` (which encodes the
bridge's own expectations) and by comparing the JSON keys parsed by
`DashboardModels.kt`.

| Bridge call | Backend handling | Notes |
|---|---|---|
| `GET /health` | same path (root) | returns `{"status":"ok"}` |
| `POST /device-bridge/pairing-codes` | accepts `X-Device-Token` (paired device) or user JWT + `?business_id=` | 201; body: `pairing_code`, `expires_at`, `expires_in_seconds` (=60) |
| `POST /device-bridge/devices` | unauthenticated (the one-time code IS the grant) | 201; body: `device_id`, `device_token`, `device_name`, `status`, `business_id` |
| `POST /device-bridge/status` | device token | 200; `device_paired`, `sms_permission_granted`, `monitoring_active` |
| `POST /device-bridge/events` | device token | 202 accepted / 200 duplicate; `matched_order_id`, `decision`, `status`, … |
| `GET /device-bridge/dashboard` | device token; `timezone, search, provider, status, from, to, sort, limit, offset` | 200; `metrics` / `system` / `items` keys exactly as `DashboardModels.kt` parses |
| `POST /payment-accounts/connect` | device token; `{provider, receiving_number}` | 200; number stored canonical (`880…`) |
| `GET /payment-accounts` | device token or JWT+business_id | own accounts only |

Behavioral notes:

* Device tokens are HMAC-hashed server-side (plaintext shown once at pairing).
* A pairing code is single-use and expires after 60 seconds; a wrong code is a
  404 identical to an expired one.
* Ingest is idempotent per `(business, provider, transaction_id)`.
* **Set `DEVICE_TOKEN_SECRET` in the deployment**, otherwise production refuses
  to start (development generates a random per-process key, so tokens do not
  survive restarts — expected outside production).
* The bridge's backend URL is baked in at build time; rebuild pointing at the
  System B host, e.g.
  `.\gradlew.bat assembleDebug -PbackendUrl=https://<sellflow-host>`.

## 3. Removed endpoints (breaking, intentional)

| Endpoint | Was | Now | Why |
|---|---|---|---|
| `POST /api/orders` | anonymous order creation into the first business | **404** | unauthenticated tenant data injection |
| `POST /api/products` | anonymous product creation | **404** | same |
| `POST /api/customers` | anonymous customer creation | **404** | same |
| `POST /api/v1/payments/detect` | anonymous payment-forgery ingest | JWT + own-business + non-production only | critical fraud vector |

No other endpoint was removed. Nothing under `/api/v1/businesses/{id}/...`
changed its request/response contract except the documented additions
(`payment_status`, `payment_method` on orders; `image_url` on products).

## 4. New endpoints (additive)

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /api/v1/businesses/{id}/payments/intelligence/events/{provider}` | JWT + membership | ingest a normalized event |
| `GET  /api/v1/businesses/{id}/payments/intelligence/events` | JWT + membership | list/filter events (search, provider, status, from/to, sort, limit, offset) |
| `GET  /api/v1/businesses/{id}/payments/intelligence/summary` | JWT + membership | counts + verified amounts |
| `POST /api/v1/businesses/{id}/payments/intelligence/feedback` | JWT + membership | record a correction |
| `GET  /api/v1/businesses/{id}/payments/intelligence/memory` | JWT + membership | own payment profile |
| `POST /api/v1/businesses/{id}/products/upload` | JWT + membership | multipart product + image (distinct path; previously unreachable duplicate) |
| `/device-bridge/*`, `/payment-accounts/*` (root) | device token / JWT | see §2 |

## 5. Versioning and rollout

* API surface is versioned at `/api/v1` as before; the root-level device
  bridge paths are deliberately unversioned compatibility surfaces.
* Deploy order: (1) apply migrations (`alembic upgrade head`), (2) deploy the
  backend, (3) update the Flutter simulator header at next app build. The
  Kotlin bridge can be rebuilt/pointed at the new host at any time.
