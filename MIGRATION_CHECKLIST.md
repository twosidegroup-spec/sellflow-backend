# MIGRATION CHECKLIST — System A → System B

Legend: `[x]` done and verified · `[~]` done but review recommended ·
`[ ]` pending (requires follow-up, usually deployment or product decisions).

---

## A. Repository protection (before any change)

- [x] Recorded System B HEAD: `08a1696a5aa62fc3e076337f7b25de51bc167ff4` (branch `main`), 64 dirty entries
- [x] Recorded System A HEAD: `fb93711ced0ad9de7cc7e3923f650adf2f12297f`, 12 dirty entries
- [x] Created System B safety branch `backup/main-before-system-a-migration` at `08a1696`
- [x] Committed the pre-existing System B working tree as checkpoint `553f9a2` (nothing was discarded)
- [x] Created migration branch `migration/system-a-integration`
- [x] Working-tree backup of System B: `SELLFLOW_MIGRATION_BACKUPS/system_b_backend_wip_20261031.zip` (7.1 MB)
- [x] Git bundle of System B: `system_b_repo_all-refs.bundle` (verified)
- [x] Full backup of System A (incl. uncommitted Phase 1C files + `.git`): `system_a_social-commerce-os_fb93711_20261031.zip`
- [x] Git bundle of System A (complete history): `system_a_repo_all-refs_fb93711.bundle` (verified)
- [x] System A repository never modified
- [x] No secrets staged (verified with `git status` before commit)

## B. Canonical architecture decisions

- [x] System B remains the main project; no second FastAPI app
- [x] One database layer (SQLAlchemy + Alembic); System A's psycopg layer not imported
- [x] One auth architecture: JWT for users (System B) + device tokens for the bridge (migrated)
- [x] One payment ledger (`payment_events`) instead of System A's two (`device_bridge_events` + `payment_events`)
- [x] One migration history with a single head (`20261031001`)
- [x] Compatibility surfaces mounted at root for the Kotlin bridge, documented

## C. Valuable System A functionality migrated

- [x] Provider adapters + registry (bKash) — `app/payments/intelligence/providers.py`
- [x] Normalizer — `.../normalizer.py`
- [x] Confidence engine — `.../confidence.py`
- [x] Anomaly engine — `.../anomalies.py`
- [x] Order matcher — `.../matcher.py` (SQLAlchemy; customer-phone join; format-tolerant phone matching)
- [x] Reconciliation engine — `.../reconciliation.py` (real TrxID; `orders.payment_status`; consistent status/decision)
- [x] Seller payment memory — `.../memory.py`
- [x] Payment dashboard contract — `.../dashboard.py` (Kotlin-compatible JSON)
- [x] Intelligence API (events/summary/feedback/memory) — `.../router.py`
- [x] Device pairing + tokens + status + listing — `app/devices/bridge_*`
- [x] Device event ingestion converging on the engine
- [x] Payment accounts — `app/payments/accounts_router.py`
- [x] Phone utilities — `app/utils/phone.py` (byte-compatible with `BangladeshPhone.kt`)
- [x] HMAC device-secret derivation — `app/core/device_tokens.py`
- [x] Fail-closed config policy — `app/core/config.py`
- [x] Database-backed rate limiting wired to all sensitive endpoints
- [x] Destructive-test safety guard — `tests/conftest.py`
- [x] Database schema (tables/columns/constraints) — Alembic `20261031001`

## D. Security findings resolved

- [x] Unauthenticated payment forgery — resolved (§3.1 of MIGRATION_REPORT)
- [x] Public write endpoints — removed
- [x] Default-business writes — removed
- [x] JWT secret fallback — production fails closed (tested)
- [x] Wildcard CORS + credentials — impossible by construction (tested)
- [x] Broken membership endpoints (TypeError) — fixed (tested)
- [x] Payment duplication/replay — unique event constraint + idempotent responses + real TrxID (tested)
- [x] Rate limiting never invoked — wired (tested: 6th registration → 429)
- [x] Unsigned/never-firing webhooks — HMAC dispatcher + URL validation (tested)
- [x] Upload route conflict + filename injection — distinct path + sanitization (tested)
- [x] Error-detail leakage (`/database`) and fake `/ready` — fixed (tested)
- [x] Inverted `verify` reconciliation logic — fixed
- [x] Overpayment guard that was a no-op — implemented
- [~] Cross-user device `register` mutation — now transfers ownership explicitly under authentication; review the transfer semantics with the mobile team
- [~] Extended SMS-format coverage for bKash parsing — the Kotlin parser was not modified (mobile untouched); recorded as P1 follow-up with the ৳65 incident note

## E. Database migration

- [x] Schema comparison performed; consolidated into one Alembic revision
- [x] Foreign keys added for all new relationships (explicit ON DELETE rules)
- [x] Transaction uniqueness: `payment_events(business_id, provider, transaction_id)`; `payments(business_id, method, transaction_id)`; `payment_accounts(business_id, provider, receiving_number)`
- [x] `orders.payment_status` / `orders.payment_method` added
- [x] No hardcoded default business anywhere
- [x] Migration is additive + idempotent-guarded (re-runnable where possible)
- [x] Fresh-DB reproducibility proven: drop → create → `alembic upgrade head` → full suite (68 passed)
- [x] No production database touched; work done exclusively against `sellflow_migration_test`
- [ ] Apply to staging/production with a backup (deployment task; explicitly NOT performed here)

## F. Testing

- [x] Backend startup/import + OpenAPI generation (69 routes, no duplicate warnings)
- [x] JWT authentication paths (existing tests)
- [x] Authorization + cross-business isolation — read, write, feedback, dashboard, products, orders, analytics, memberships (new + existing tests)
- [x] Payment parsing/normalization — provider + confidence + anomaly unit tests
- [x] Payment matching — auto-match, exact-amount semantics, partial, overpayment, unknown
- [x] Duplicate transaction protection — repeated event returns duplicate, single ledger row
- [x] Device bridge communication — pairing contract, single-use codes, token auth, ingest, dashboard JSON contract
- [x] Database migrations — applied to a fresh DB; single head verified
- [x] Existing System B regression suite — preserved; two expectations updated deliberately (cancelled-order analytics; see diff); all pass
- [x] Full suite on the isolated DB: **68 passed / 0 failed**
- [ ] Kotlin bridge unit tests re-run — not required (no bridge code changed), but a build against the new host is a recommended release step
- [ ] Flutter widget tests re-run — mobile untouched; optional

## G. Deliverables

- [x] `MIGRATION_REPORT.md`
- [x] `CANONICAL_ARCHITECTURE.md`
- [x] `API_COMPATIBILITY.md`
- [x] `MIGRATION_CHECKLIST.md` (this file)
- [x] `SYSTEM_A_COMPONENT_MAPPING.md`

## H. Pending items (not blockers for the branch, blockers for production)

- [ ] Set `SECRET_KEY` and `DEVICE_TOKEN_SECRET` in the deployed environment
- [ ] Run migrations on the target database (with backup)
- [ ] Patch the Flutter simulator to send the Authorization header
- [ ] Product review of the exact-amount auto-match decision semantics
- [ ] Broaden bKash SMS patterns + add parse-failure telemetry (the ৳65 class)
- [ ] Consider RLS migration as defence in depth
- [ ] Rotate any credential that ever appeared in a tracked `.env.production` (policy cleanup)
