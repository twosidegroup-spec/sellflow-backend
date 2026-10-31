# MIGRATION REPORT — System A → System B

**Date:** 2026-10-31
**Branch:** `migration/system-a-integration` (System B repo: `SELLFLOW/backend`)
**Source:** System A = `Desktop/social-commerce-os/social-commerce-os` (commit `fb93711`, untouched)
**Destination:** System B = `SELLFLOW/backend` (main project, GitHub `twosidegroup-spec/sellflow-backend`)

---

## 1. Executive summary

System A's valuable functionality — the bKash SMS payment-intelligence pipeline,
the Android device bridge, payment accounts, the payment dashboard contract and
the device/security configuration policies — has been migrated **into** System B
under System B's architecture. System B remains the canonical project: its JWT
authentication, its SQLAlchemy/Alembic database layer, its URL conventions and
its existing mobile-facing APIs are unchanged except where they were insecure
or broken.

All five companion documents were produced:
`CANONICAL_ARCHITECTURE.md`, `API_COMPATIBILITY.md`, `MIGRATION_CHECKLIST.md`,
`SYSTEM_A_COMPONENT_MAPPING.md`, and this report.

**Evidence (executed in this migration, not claimed):**

| Check | Result |
|---|---|
| `alembic upgrade head` on a freshly created `sellflow_migration_test` database | **PASS** — single head `20261031001`, 15 revisions applied |
| Full test suite on the clean isolated database | **68 passed, 0 failed** (30 pre-existing + 38 new migration tests) |
| `python -c "from app.main import app"` (import + OpenAPI generation) | **PASS** — 69 endpoints, no duplicate-operation warnings |
| Secret scan of the staged diff | no `.env`/secret files staged |

## 2. What was migrated (short form)

* **Payment intelligence engine** — normalizer, provider adapters (bKash),
  confidence scoring, anomaly detection, order matcher, reconciliation engine,
  seller payment memory, decision/match/anomaly/feedback audit tables.
* **Device bridge** — pairing codes (60 s, single-use, HMAC-hashed), device
  tokens (HMAC-hashed, stored on the canonical `devices` table), status
  heartbeat, event ingestion, device listing, tenant scoping.
* **Payment accounts** — `/payment-accounts` + `/payment-accounts/connect`,
  unique per business/provider/number.
* **Payment dashboard contract** — the exact JSON the Kotlin bridge parses.
* **Safety and configuration policies** — fail-closed secrets, destructive-test
  guard, registration invite option, database-backed rate limiting wired in.
* **Phone normalization** — byte-compatible with the Kotlin `BangladeshPhone`.

## 3. Security fixes applied to System B

All previously reported critical/high findings were addressed in code (details
and tests in `MIGRATION_CHECKLIST.md` and `tests/test_migration_security.py`):

1. **Unauthenticated payment forgery** (`POST /api/v1/payments/detect`):
   now disabled in production (404), JWT-required elsewhere, rate-limited, and
   the receiving number must belong to the caller's own business.
2. **Public write endpoints** (`POST /api/orders`, `/api/products`,
   `/api/customers`): **removed**.
3. **Hardcoded default-business behaviour:** removed with the public endpoints;
   the dev simulator derives the business from the caller's membership.
4. **Insecure JWT secret fallback:** production now refuses to start unless a
   real `SECRET_KEY` (≥32 chars, non-placeholder) is configured.
5. **Wildcard CORS with credentials:** origins come from configuration; `*`
   forces `allow_credentials=False`, so the unsafe combination is impossible.
6. **Broken membership endpoints:** the `is_owner(business_id, db)` signature
   mismatch was fixed; roles are validated; owners/admins enforced.
7. **Payment duplication/replay:** payment events are unique per
   `(business_id, provider, transaction_id)`; the ledger row written by the
   engine uses the **real provider TrxID** (System A used a synthetic value
   that could collide on repeat settlements); duplicates return idempotent
   results and never create a second payment.
8. **Rate limiting that never ran:** `check_rate_limit` is now called on
   registration, login, pairing-code creation, pairing redemption, device
   events/status, and the dev simulator.
9. **Webhooks that never fired & were unsigned:** an HMAC-SHA256 dispatcher
   (`X-Webhook-Signature: sha256=…`) fires from payment recording and order
   status changes; URLs are validated (no loopback/private literals) and the
   signing secret is returned once at creation.
10. **Upload route conflict & unsafe filenames:** the multipart route moved to
    the distinct path `/products/upload`, is reachable, sanitizes filenames and
    enforces size/type limits.
11. **Error-detail leakage:** `/database` logs detail server-side; `/ready`
    actually probes the database and returns 503 when it is down.

Additional correctness fixes discovered while migrating (each covered by tests):

* Matcher/reconciliation integration defect (evaluated-candidate reuse) —
  fixed during test development.
* Phone comparison across canonical (`880…`) and local (`01…`) formats — the
  matcher now compares the last 10 digits, in SQL and in Python.
* Analytics no longer counts **cancelled** orders in revenue/profit
  (`tests/test_analytics.py` updated accordingly).

## 4. Behavioural decisions worth review

1. **Exact-amount match still marks the order paid** (System A behaviour,
   preserved intentionally — it is the product's core promise). Consolidation
   change: the event **status** is now `PAID` when the order is marked paid,
   while the confidence engine's **decision** (which can be
   `UNKNOWN_TRANSACTION` when only the amount matched) is stored alongside.
   Previously the status and the order state contradicted each other.
2. **Partial/overpayment classification requires the candidate order to be
   findable** — an amount-exact match or a customer-phone match. This matches
   System A; an unrelated smaller amount is `UNKNOWN_TRANSACTION`
   (review queue), not a partial payment of a random order.
3. **Device tokens are a second credential type, not a second user-auth
   system** — devices authenticate the bridge; users authenticate everything
   else. See `CANONICAL_ARCHITECTURE.md` §3.
4. **RLS was not migrated** (System A's migration 014 + `db_tenant.py`). System
   B enforces tenancy at the API layer with mandatory membership checks; RLS is
   recorded as future hardening because it requires a non-superuser database
   role and per-transaction context wiring.
5. **The dev simulator (`/api/v1/payments/detect`)** remains available outside
   production for the Flutter app's "Test incoming payment" button. It now
   requires a JWT; the app must send its `Authorization` header (see
   `API_COMPATIBILITY.md`).

## 5. Database consolidation

One canonical schema, one migration history (Alembic), single head
`20261031001`. New tables: `payment_accounts`, `payment_events`,
`payment_decisions`, `payment_matches`, `payment_anomalies`,
`payment_feedback`, `seller_payment_profiles`, `device_pairing_codes`.
Extended tables: `devices` (bridge columns), `orders`
(`payment_status`, `payment_method`).

* System A's missing-`orders`-table problem does not apply here: System B's
  `orders` table is created by its own migration chain (`45564165c6c7`), so the
  consolidated history builds a complete database on an empty server. This was
  proven by dropping and rebuilding the test database from scratch.
* System A's `device_bridge_events` ledger was consolidated into
  `payment_events` (with `device_id`/`source` attribution) so there is exactly
  one payment ledger.
* No production database was touched. No destructive migration was applied
  anywhere except the isolated `sellflow_migration_test` database.
* Unique constraints preserved: `payment_events (business_id, provider,
  transaction_id)`, `payments (business_id, method, transaction_id)`,
  `payment_accounts (business_id, provider, receiving_number)`.

## 6. Testing — actual results (never fabricated)

```
Environment: DATABASE_URL -> sellflow_migration_test (isolated, local)
             SELLFLOW_ALLOW_DESTRUCTIVE_TESTS=1

pytest tests/ -q
68 passed, 7 warnings in 31.57s
```

Breakdown: 30 pre-existing System B tests + 38 new migration tests
(`test_migration_intelligence.py` 15, `test_migration_device_bridge.py` 10,
`test_migration_security.py` 13). The new tests cover: confidence/anomaly pure
logic, auto-match with/without customer phone, duplicate idempotency, partial
settlements, overpayment review, tenant isolation (read + write + feedback),
pairing single-use/expiry, device token auth, the Kotlin dashboard contract,
payment-account connect, security regressions, config fail-closed behaviour,
CORS policy, webhook HMAC/URL validation, upload reachability/sanitization.

Also executed:
* `pytest --collect-only` after changes — no collection errors in `tests/`.
  (`test_api.py` at the repo root still cannot be collected: it imports
  `requests`, which is not installed. It is a manual production-script and is
  left untouched; see "Known issues".)
* Fresh-DB reproducibility: `DROP DATABASE … WITH (FORCE)` →
  `scripts/create_test_db.py` → `alembic upgrade head` → full suite again →
  **68 passed**.
* App import + OpenAPI: 69 routes, no duplicate-operation warnings.

Not run (and why): the Android bridge unit tests (unmodified — no changes to the
Kotlin client); Flutter widget tests (mobile app intentionally untouched);
System A's own suite (would require its Supabase database; System A repo must
remain untouched).

## 7. Operational actions required before deploying this branch

1. Set `DEVICE_TOKEN_SECRET` (≥32 chars) in the deployed environment —
   production refuses to start without it.
2. Set a real `SECRET_KEY` if the deployed environment still carries the
   placeholder.
3. Run `alembic upgrade head` against the target database **after taking a
   backup** (additive migration: new tables + new nullable columns only).
4. Optionally set `REGISTRATION_INVITE_CODE` to make registration
   invitation-only.
5. Review `CORS_ORIGINS` for the real mobile/web origins.
6. Update the Flutter app so the dev simulator and any direct callers send the
   `Authorization` header (only affects the simulator button; see
   `API_COMPATIBILITY.md`).

## 8. Known issues / deliberately not done

* `tests/test_smoke.py` returns values from test functions (pytest warning, not
  a failure) — preserved as-is.
* Root `test_api.py` references a Render URL and requires `requests`; left
  untouched (it is a manual connectivity script, not part of the suite).
* System A's operator (TSG) dashboards, FCM push, seller-capacity limits and
  the risk of complaints/priority trade-offs were **not** migrated; see the
  mapping document for the rationale of each rejection.
* RLS remains a future hardening item (see §4.4).
* The two backends still exist on disk: System A is untouched and recoverable;
  it is **not** an active second backend of the main project.

## 9. Recovery

* System B pre-migration state: branch `backup/main-before-system-a-migration`
  (commit `08a1696`) plus checkpoint commit `553f9a2` capturing the working
  tree exactly as it was before the migration.
* System A: **not modified**. Backups exist in
  `Desktop/SELLFLOW_MIGRATION_BACKUPS/`:
  `system_a_social-commerce-os_fb93711_20261031.zip` (working tree incl. Phase
  1C files + .git) and `system_a_repo_all-refs_fb93711.bundle` (verified
  complete history).
* System B working-tree backup: `system_b_backend_wip_20261031.zip` + git
  bundle.
