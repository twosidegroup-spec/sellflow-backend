# SYSTEM A COMPONENT MAPPING

Every inspected System A component, its decision, its destination in System B,
the changes required, and the tests that verify the migrated behaviour.

Decisions: **MIGRATE** (compatible, moved) · **ADAPT** (moved with changes) ·
**REWRITE** (behaviour preserved, new implementation) · **REJECT** (not moved)
· **INVESTIGATE** (further evidence needed — none outstanding after this pass).

| System A source | System B destination | Decision | Changes | Tests |
|---|---|---|---|---|
| `app/config.py` (fail-closed secrets, invite code) | `app/core/config.py` + `app/core/device_tokens.py` | ADAPT | Settings now carries `device_token_secret`/`registration_invite_code`; production validator refuses placeholder/short secrets; CORS becomes an explicit list; dev secret random per process | `test_migration_security.py::test_production_requires_real_secret_key`, `::test_production_requires_device_token_secret`, `::test_production_accepts_real_secrets`, `::test_wildcard_cors_disables_credentials` |
| `app/database.py` (psycopg connect) | — | REJECT | System B's SQLAlchemy session/engine is the single DB layer | — |
| `app/dependencies.py` (`require_business`, `require_device_principal`, `require_development`) | `app/devices/bridge_dependencies.py`; `settings.is_production` gate | ADAPT | Device principal retained for bridge routes; admin dependency rejected (no operator surface); dev gate implemented via config | `test_migration_device_bridge.py` (401/404 assertions), `test_migration_security.py::test_detect_is_disabled_in_production` |
| `app/db_safety.py` (destructive-target policy) | `tests/conftest.py` guard | ADAPT | Policy re-implemented for pytest: refuse unless DB name ends `_test` + explicit opt-in | Guard itself; run log "REFUSING TO RUN" reproduced pre-migration |
| `app/db_tenant.py` + `migrations/014_tenant_rls.sql` | — | REJECT (deferred) | RLS requires a non-superuser DB role and per-transaction context; System B authorizes at API layer with mandatory membership checks. Recorded as P2 hardening | Tenant isolation covered by API tests |
| `app/migrations.py` (custom runner) | Alembic chain | REJECT | Alembic is canonical | Fresh-DB migration run |
| `app/ratelimit.py`, `app/ratelimit_store.py` | `app/core/rate_limit.py` (existing) wired into routers | ADAPT | One DB-backed limiter; applied to register, login, pairing create/redeem, device status/events, dev detect | `test_migration_security.py::test_register_rate_limit_fires` |
| `app/logging_config.py` (request-id + redaction) | — | REJECT (deferred P2) | Global logging behaviour change deferred to avoid ops surprises; noted in CANONICAL_ARCHITECTURE | — |
| `app/main.py` (custom validation/exception handlers) | `app/main.py` (System B) | ADAPT (partial) | JSON-safe 422 handling represented by pydantic/FastAPI defaults; global exception handler deferred | Import/OpenAPI checks |
| `app/payment/models.py` (DTOs/enums) | `app/payments/intelligence/models.py` | MIGRATE | `ConfigDict(extra="forbid")` retained; added optional `device_id`/`source` attribution | `test_migration_intelligence.py` (validation via API) |
| `app/payment/providers/base.py`, `providers/bkash.py`, `providers/__init__.py` | `app/payments/intelligence/providers.py` | MIGRATE | Consolidated into one module; registry preserved | `::test_unknown_provider_is_rejected`; normalizer path in auto-match tests |
| `app/payment/normalizer.py` | `.../normalizer.py` | MIGRATE | Import path only | auto-match tests |
| `app/payment/engine.py` | `.../service.py::ingest_event` + `.../reconciliation.py::process_event` | ADAPT | Session-owned transactions; tenant is a parameter | all intelligence tests |
| `app/payment/confidence.py` | `.../confidence.py` | MIGRATE | Unchanged thresholds/weights | pure-logic tests (AUTO_MATCHED; partial capped) |
| `app/payment/anomalies.py` | `.../anomalies.py` | MIGRATE | Unchanged rules; stored in `payment_anomalies` | exercised in intelligence flow |
| `app/payment/matcher.py` | `.../matcher.py` | ADAPT | SQLAlchemy; `orders.total_amount`; customer phone via join; last-10-digits phone comparison (SQL + Python); only CANCELLED excluded (System B status enum) | auto-match (customer phone), partial, overpayment |
| `app/payment/reconciliation.py` | `.../reconciliation.py` | ADAPT | Ledger row uses the REAL provider TrxID; `orders.payment_status`; event status PAID whenever the order is marked paid (decision keeps the nuance); duplicate responses idempotent | duplicate/no-second-payment, partial, overpayment, exact-amount semantics |
| `app/payment/memory.py` | `.../memory.py` | ADAPT | SQLAlchemy aggregates; profile updated on feedback | feedback test path |
| `app/payment/bridge.py` (pairing, devices, queue, ingest) | `app/devices/bridge_service.py` + `app/devices/models.py` (extended `devices`, `device_pairing_codes`) | ADAPT | One canonical devices table; single event ledger; code-carries-tenant; server queue table dropped (device has its own SQLite queue) | device bridge suite (pairing contract, single-use, ingest, isolation) |
| `app/payment/dashboard.py::get_payment_dashboard` | `app/payments/intelligence/dashboard.py` | ADAPT | Same JSON contract (`metrics/system/items/…`); SQLAlchemy; masked receiving numbers | `test_device_dashboard_contract`, `::test_device_dashboard_is_scoped_to_the_device_business` |
| `app/routes/auth.py` (register + invite + capacity + pairing code return) | `app/auth/router.py` + `/device-bridge/pairing-codes` | ADAPT | Invite-code support added (constant-time compare); capacity limits rejected; pairing code issued by the bridge endpoint instead of registration (see API_COMPATIBILITY) | `test_membership_add_and_remove_work`, register tests, pairing tests |
| `app/routes/device_bridge.py` (6 endpoints) | `app/devices/bridge_router.py` (root `/device-bridge/*`) | ADAPT | Device token via canonical `devices`; rate limits added; same response keys | full device bridge suite |
| `app/routes/payment_intelligence.py` | `app/payments/intelligence/router.py` | ADAPT | Tenant-scoped under `/api/v1/businesses/{id}/payments/intelligence`; membership auth replaces device-only | tenant isolation + feedback tests |
| `app/routes/payments.py` (manual confirm) | — | REJECT (duplicate) | System B's `record_payment` now sets `orders.payment_status` and writes the ledger row, achieving the same outcome within one canonical flow | existing payment tests |
| `app/routes/dashboard.py` (payment accounts + dev simulator) | `app/payments/accounts_router.py`; dev-gated `payments/detect` | ADAPT | Accounts model ported; simulator kept dev-only + JWT + own-business only | detect tests (auth, own-business, production-404), account connect tests |
| `app/routes/orders.py`, `customers.py`, `products.py`, `analytics.py` | System B equivalents | REJECT | System B already implements these domains; A's richer order service is future product work | existing suites |
| `app/services/order_service.py`, `customer_service.py`, `product_service.py` | — | REJECT | System B services retained (one implementation per capability) | existing suites |
| `app/routes/tsg*.py` (operator dashboards) | — | REJECT | Product decision: no operator surface in the canonical API; System A copy remains for reference | — |
| `app/push/fcm.py` | — | REJECT (deferred) | Needs a Firebase service account and device-app support; recorded as future work | — |
| `app/platform/capacity.py` (seller ceiling) | — | REJECT | Business/ops decision, not part of this migration | — |
| `app/utils/phone.py` | `app/utils/phone.py` | MIGRATE | Same canonical form `880…`; added `phones_equivalent` + `digits_only` helpers used by the matcher | matcher phone-match tests |
| `app/utils/money.py` | — | REJECT | System B services already use `Decimal`; no consumer needed | — |
| `migrations/001–011`, `012–014` | Alembic `20261031001` (+ System B's own chain) | ADAPT | Consolidated DDL; A's reconstructed `orders` DDL not needed (System B has the table); RLS migration deferred | fresh-DB migration run |
| `android-bridge/` (Kotlin app + 18 unit tests) | unchanged (System A repo) | PRESERVE | Not modified; backend keeps its contract; rebuild pointer documented | Backend-side contract tests; Kotlin tests already 18/18 (previous audit run) |
| `docs/SCHEMA-INVENTORY.md` | referenced in MIGRATION_REPORT | PRESERVE (reference) | Analysis informs the consolidation; file stays in System A | — |
| System A test suite | `tests/test_migration_*.py` | ADAPT | Behaviours re-expressed as isolated-DB tests (System A's suite depends on its Supabase DB) | 38 new tests, all passing |
| `.env` keys (`DEVICE_TOKEN_SECRET`, `REGISTRATION_INVITE_CODE`, `APP_ENV`) | `app/core/config.py` + `.env.example` | ADAPT | Documented; production fail-closed | config tests |

## Notes

* "PRESERVE" items live in System A, which remains untouched and recoverable.
* No component was copied verbatim; every port was rewritten against System B's
  session-based data layer and its authorization model, so there is exactly one
  implementation of every capability in the running product.
* The Android bridge is the one client that speaks the migrated surface; its
  contract is pinned by `tests/test_migration_device_bridge.py`.
