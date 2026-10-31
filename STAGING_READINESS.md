# SellFlow — Staging Readiness Dossier

**Audited baseline:** `a549b57` (branch `feature/premium-web-ui`) — the two audit-fix commits
`dbcbdcf` and `a549b57` sit on top of `2123b9e`. Worktree clean; local and `origin` in sync.
**Scope of this document:** verification results, incident scoping, approval-required proposals,
and the staging checklist. Nothing here deploys anything or changes business policy.
**Secret policy:** no credential, token, or connection string is printed in this file or in the
commands below. Fingerprints (SHA-256 prefixes) are used where a comparison is needed.

Labels: **FACT** = verified by execution in this repository. **ASSUMPTION** = believed true but
not verified. **UNKNOWN** = cannot be determined from this environment.

---

## 1. Repository and audit verification

| Check | Result |
| --- | --- |
| Branch / HEAD | **FACT** `feature/premium-web-ui` at `a549b57` |
| Audit commits present | **FACT** `git cat-file -t dbcbdcf` / `a549b57` → `commit` |
| Worktree | **FACT** clean (`git status --porcelain` empty) |
| Remote sync | **FACT** `git rev-list --left-right --count origin/feature/premium-web-ui...HEAD` → `0 0` |
| `.env.production` tracked? | **FACT** No — `git check-ignore` returns it; `git ls-files` returns nothing |
| Primary test database | **FACT** `sellflow_audit_test` at `20261031002 (head)` |
| Legacy test database | **FACT** `sellflow_migration_test` at `20261031002 (head)` |
| Test suite (isolated DB) | **FACT** 132 passed on `sellflow_audit_test` at `a549b57` |

---

## 2. Secret incident — `.env.production`

### 2.1 Facts (values are never printed)

- The file was tracked from `cf0ce5c` (**2026-10-20**) until `dbcbdcf` (**2026-10-31**) removed it
  from the branch tip. It remains in git history of a **PUBLIC** repository
  (`twosidegroup-spec/sellflow-backend`, verified via `gh repo view`), until purged.
- GitHub secret-scanning alerts for the repository: **none** (`gh api .../secret-scanning/alerts`
  → `[]`). This does **not** mean the value is safe — custom keys are frequently not detected.
- Key names in the file: `APP_ENV`, `APP_DEBUG`, `HOST`, `PORT`, `SECRET_KEY`, `DATABASE_URL`.
  `SECRET_KEY` was a non-placeholder value. No `DEVICE_TOKEN_SECRET` was in the file.
- `DATABASE_URL` host was `localhost` (a local development database, not a hosted one).
- Fingerprint comparisons (SHA-256 prefixes):

| Value | Local `.env` | Leaked `.env.production` |
| --- | --- | --- |
| `SECRET_KEY` | `EE109A2E…` | `1BAD0168…` → **different** |
| `DATABASE_URL` | `15BCA46F…` | `24B98584…` → **different** |

- Vercel production environment: `SECRET_KEY` is stored as a **sensitive** value — the CLI
  returns `[SENSITIVE]` and cannot read it back (verified: the pulled fingerprint equals
  `sha256("[SENSITIVE]")`). Whether it equals the leaked value is **UNKNOWN**.

### 2.2 Which environments require rotation

| Environment | Required? | Reason / impact |
| --- | --- | --- |
| Vercel `sellflow-site` production | **Yes, unconditionally** | Cannot verify the value; assume worst case. Rotating `SECRET_KEY` invalidates all issued JWTs (users re-login). Rotate `DEVICE_TOKEN_SECRET` too (paired bridge devices must re-pair). **Impact today ≈ zero:** the deployment has no `DATABASE_URL`, so no sessions exist. |
| Any Render (or other host) service built from `.env.production` | **Yes, if it exists** — UNKNOWN | The file header targeted Render. No `render.yaml` exists in the repo; no Render CLI is available here. If such a service exists, rotate before it serves anyone. |
| Local developer machines that sourced the file | **Yes, low urgency** | Local JWTs would be forgeable by anyone with the leaked key; local data is disposable. |
| Any database whose password equals the leaked `DATABASE_URL` password | **Yes, if reused** — UNKNOWN | The leaked URL was localhost-hosted; rotate the DB password if the same password is reused anywhere hosted. |
| `DEVICE_TOKEN_SECRET` | Rotate alongside `SECRET_KEY` on any host where both were set together | Not leaked directly, but cheap to rotate during the same window; devices re-pair. |

### 2.3 Safe rotation procedure (run these yourself; nothing below has been executed)

Generate values interactively so they never enter shell history or this chat:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Vercel (production) — do not run until you intend to rotate:**

```powershell
vercel env rm SECRET_KEY production --yes --scope tsg-bfe6
vercel env add SECRET_KEY production --sensitive --scope tsg-bfe6   # paste the generated value when prompted
vercel env rm DEVICE_TOKEN_SECRET production --yes --scope tsg-bfe6
vercel env add DEVICE_TOKEN_SECRET production --sensitive --scope tsg-bfe6
# verify names (values remain unreadable by design):
vercel env ls production --scope tsg-bfe6
```

**Staging:** never reuse anything from a production or leaked source. Set fresh values as process
environment variables (see §7) — do not create a committed env file.

**History purge (defence-in-depth, after rotation):** rotation is the actual fix. Purging the file
from public history requires a coordinated rewrite (e.g. `git filter-repo --path .env.production
--invert-paths` on a fresh clone and a force-push, or a GitHub Support request). Treat any clone
made before the purge as still exposed. **ASSUMPTION:** no forks of the repository exist;
**UNKNOWN:** whether GitHub caches/retains the blob after a rewrite.

### 2.4 Verification after rotation

1. An access token issued before rotation must now be rejected: `GET /api/v1/auth/me` → **401**
   (a pre-rotation token is needed as evidence; do not paste it anywhere).
2. A fresh login must work: `POST /api/v1/auth/login` → 200.
3. Device bridge: a device paired before a `DEVICE_TOKEN_SECRET` rotation must get **401** on
   `/device-bridge/dashboard` and must re-pair.

**FACT:** repo is public and the value sat in history for 11 days. **UNKNOWN:** whether anyone
cloned or used it. Rotation is therefore mandatory before any pilot with real sellers.

---

## 3. Startup configuration, database connectivity, migrations

### 3.1 Verified behaviours (executed at `a549b57`)

| Scenario | Endpoint | Observed |
| --- | --- | --- |
| Healthy DB (`sellflow_audit_test`) | `GET /health` | **200** `{"status":"ok"}` |
| | `GET /status` | **200** `{"status":"ok","service":"sellflow-api","version":"0.9.0"}` |
| | `GET /database` | **200** `{"status":"ok","database":"connected"}` |
| | `GET /ready` | **200** `{"ready":true,"checks":{"database":"ok","api":"ok"}}` |
| | `GET /api/v1/info` | **200** (does not touch the DB) |
| Unreachable DB | `GET /health`, `/status`, `/api/v1/info` | **200** — process liveness only |
| | `GET /database` | **200** with body `{"status":"error","database":"disconnected"}` (note: probe on the **body**, not the code) |
| | `GET /ready` | **503** — correct readiness semantics |
| | `POST /api/v1/auth/login` | **500** (DB-backed route) — stack trace logged server-side only, not returned |

**FACT:** the application never auto-creates or auto-migrates schema (no `create_all` call sites);
`alembic upgrade head` must run explicitly before the first boot.
**FACT:** migrations verify from zero: single root `bc178152c42e` → single head `20261031002`,
16 revisions, one merge revision (`20261023001`), downgrade/re-upgrade of `20261031002` verified.

### 3.2 `APP_ENV` semantics — important for staging fidelity

**FACT:** `app/core/config.py` treats only `production`/`prod` as production
(`_PRODUCTION_ENVS`). `APP_ENV=staging` therefore **bypasses** the fail-closed checks
(secret quality enforcement, `APP_DEBUG` refusal, dev payment-simulator disabled).

- **Recommendation (no code change):** run isolated staging with **`APP_ENV=production`** so the
  validation behaviour, secret enforcement, and disabled dev simulator match what production will
  enforce — while pointing `DATABASE_URL` at the **staging** database only. The variable controls
  validation strictness, not which database is used.
- **Alternative (needs approval, small change):** add `staging` to a "strict" tier in config. Not
  implemented; listed here as a future option.

### 3.3 Staging environment variables (names and constraints only)

| Variable | Value/constraint | Notes |
| --- | --- | --- |
| `APP_ENV` | `production` (recommended, see §3.2) | Controls fail-closed validation only |
| `APP_DEBUG` | `false` | `true` is refused when `APP_ENV=production` |
| `SECRET_KEY` | ≥32 chars, not a known placeholder | Fresh value generated for staging |
| `DEVICE_TOKEN_SECRET` | ≥32 chars | Required when `APP_ENV=production` |
| `DATABASE_URL` | staging DB, `postgresql+psycopg://…` | **Never** the production cluster |
| `CORS_ORIGINS` | explicit comma-separated staging origins | Wildcard + credentials is impossible by design |
| `REGISTRATION_INVITE_CODE` | non-empty during pilot | Gates open registration |
| `HOST` / `PORT` | bind address for the staging host | Defaults are fine |
| `MAX_UPLOAD_SIZE` / `ALLOWED_UPLOAD_TYPES` | defaults | image/jpeg, image/png, ≤10 MB |
| `AWS_*` | **leave unset** | **FACT:** settings exist but no code uses them yet (see §6) |

---

## 4. PROPOSAL — order status transitions and inventory behaviour (approval required, NOT implemented)

Current behaviour (**FACT**): `PATCH /orders/{id}/status` accepts any enum value
(`created, confirmed, packed, shipped, delivered, cancelled`) from any current state; the console
menu offers every status except the current one. Only enum validation (422) applies.

### 4.1 Proposed transition matrix (for approval)

| From \ To | created | confirmed | packed | shipped | delivered | cancelled |
| --- | :-: | :-: | :-: | :-: | :-: | :-: |
| **created** | no-op | ✅ | — | — | — | ✅ |
| **confirmed** | — | no-op | ✅ | ✅ | — | ✅ |
| **packed** | — | — | no-op | ✅ | — | ✅ |
| **shipped** | — | — | — | no-op | ✅ | ✅ |
| **delivered** | — | — | — | — | no-op | ⚠️ see note |
| **cancelled** | — | — | — | — | — | no-op |

- **no-op** (same status) returns 200 without side effects; the webhook/notification fire only on
  true changes (current behaviour, preserved).
- Disallowed transitions → **409 Conflict** with the allowed set in the detail.
- ⚠️ **Delivered → cancelled** is proposed as **disallowed**. Returns/refunds after delivery need
  a dedicated workflow (a future `returned` order status or a refund record), not a cancellation
  that would silently remove recorded revenue. **Decision requested.**
- Compressing the flow (e.g. `created → shipped` directly): allowed via the `confirmed` shortcut
  column above (`confirmed → shipped` without `packed`); direct `created → shipped` is proposed
  **disallowed** — confirm.
- Console change required when approved: the row menu filters to allowed-next-states (one small
  edit in `webapp/js/pages/orders.js`). Tests to update: `test_business_ops_audit.py`
  (`test_order_status_transitions_are_currently_unrestricted` becomes the matrix test).

### 4.2 Inventory behaviour — options (for approval)

Current behaviour (**FACT**): stock is seller-maintained (`PUT products.stock_quantity`, `ge=0` →
negative rejected). Order creation does **not** decrement stock; an audit test pins this.

| Option | Description | Pros | Cons / risks |
| --- | --- | --- | --- |
| **A. Keep manual (status quo)** | Sellers adjust stock by hand | Simple, matches how many SMS-first sellers already work; no ledger needed | Overselling relies on the seller noticing the ≤5 low-stock badge |
| **B. Auto-decrement** | Deduct at order creation, restore on cancellation (row lock `SELECT … FOR UPDATE`) | Stock reflects reality without manual work | Returns/exchanges/edits need a stock-movement ledger to stay correct; historical orders would not be back-deducted; concurrency needs locking |
| **C. Manual + guardrails (recommended for pilot)** | Keep manual stock; when ordering more than available, show a **non-blocking** warning and record it in the order note; add a stock-adjustment audit trail later | Zero risk of corrupting counts; adds safety where it helps most | Still manual |

**Recommendation:** Option **C** for the pilot, with Option **B** revisited only after a
stock-movement ledger (reason codes: sale, cancellation, manual adjust, return) is designed.
**No code changes will be made until this is approved.**

---

## 5. PLAN — per-user JWT token-version revocation (designed, NOT implemented)

**Why:** access tokens live 24 h and there is no server-side revocation; a password change does
not invalidate existing tokens. **FACT:** there is no logout endpoint; the console discards the
token client-side.

### 5.1 Design

1. New column: `users.token_version INTEGER NOT NULL DEFAULT 0`.
2. New claim: JWTs include `ver` (`create_access_token`); login (`app/auth/router.py:120`) embeds
   the current value.
3. Enforcement in **both** token-resolution sites (**FACT:** these are the only two):
   - `app/auth/dependencies.py::get_current_user`
   - `app/devices/bridge_dependencies.py::_optional_user` (used by `/payment-accounts` and the
     pairing-codes path for user JWTs)
   Mismatch or missing `ver` → 401 (hard cutover; all existing sessions end once, which is
   acceptable pre-pilot — alternatively accept a missing `ver` as `0` for a staged rollout; pick
   one at approval time).
4. Bump `token_version` on password change (`POST /api/v1/auth/passcode/change`). Optional later:
   a "sign out everywhere" action and bump on membership-sensitive events.
5. Device bridge **devices** are unaffected (they authenticate with `X-Device-Token`, HMAC —
   **FACT**: no JWT involved on that path).

### 5.2 Migration plan (idempotent, mirrors `20261031002` practices)

- Revision `20261031003_add_token_version`, `down_revision = "20261031002"`.
- `upgrade()`: add column with `server_default="0"`, `nullable=False`, guarded by an
  `_has_column` check. `downgrade()`: drop column.
- Single-head invariant preserved; downgrade/re-upgrade round trip to be tested on `_test` DBs.

### 5.3 Regression-test plan

1. Token minted before the change remains valid until the version is bumped.
2. After password change: old token → 401 on `/api/v1/auth/me`, `/api/v1/businesses/{id}/orders/`
   and `/businesses/{id}/payments/intelligence/summary`; fresh login → 200 everywhere.
3. Forged token with the correct `sub` but stale `ver` → 401 (signed with the test secret).
4. Token with no `ver` → per the chosen cutover policy (assert the chosen behaviour).
5. `/payment-accounts` with a user JWT and stale version → 401 (proves the bridge-dependency site
   enforces too).
6. Device-token flows (`/device-bridge/*`, `/payment-accounts/connect` via device token) unchanged.

### 5.4 Touch points (5 files + migration + tests) — all small, no architecture change

`app/auth/models.py` · `app/core/security.py` · `app/auth/router.py` ·
`app/auth/dependencies.py` · `app/devices/bridge_dependencies.py` · new migration ·
new `tests/test_token_version_audit.py`.

---

## 6. REVIEW — durable uploads

**FACTS:** uploads are written to the local `uploads/` directory and served by the unauthenticated
`/uploads` static mount (mitigated in the audit: 128-bit random names, content-type-derived
extensions, `nosniff`). On Vercel the bundle filesystem is read-only/ephemeral — the code itself
documents this and uploads will fail or vanish there. `AWS_*` settings exist in config but **no
code references them**; `boto3` is not in `requirements.txt`.

Options under the free/low-cost constraint (**pricing figures are ASSUMPTIONS — re-check before
deciding**):

| Option | Shape | Fit |
| --- | --- | --- |
| **Persistent disk host** (Render disk, Fly volume, Railway volume) | Keep the current code; mount `uploads/` on a volume | Simplest for **staging**; typically needs a paid instance tier |
| **Cloudflare R2** | S3-compatible API, free tier ~10 GB storage, no egress fees | Best **production** candidate; needs a thin storage adapter and `boto3` |
| **Backblaze B2** | S3-compatible, free tier ~10 GB, egress billed low | Comparable to R2; slightly smaller ecosystem |
| **Vercel Blob** | Native to the current deploy target; minimal free allowance | Smoothest if staying serverless; pricing/reliance to verify |
| **AWS S3** | Free tier ~5 GB for 12 months | Heaviest IAM/ops burden of the set |

**Recommendation:** staging on a persistent-disk host (or accept non-durable images for staging
only, documented), and R2 as the production storage path with a `STORAGE_BACKEND=local|r2`
adapter. Migration outline (for a future approval): add `boto3`, write-through from the upload
route, keep the existing URL shape, backfill historical files with a one-off script, retain the
local mount for development. **Not implemented now** — no architecture changes in this pass.

---

## 7. Staging checklist (Windows PowerShell)

**Golden rules**

- Tests run **only** against a database whose name ends in `_test`
  (`SELLFLOW_ALLOW_DESTRUCTIVE_TESTS=1` is required by the guard in `tests/conftest.py`).
- The staging application database is `sellflow_staging` (no suffix) — never run the destructive
  suite against it; migrations and reads/writes from the app only.
- Never point `DATABASE_URL` at production. Keep staging secrets distinct from every other
  environment; set them as process environment variables, not in a committed file.
- `.env.staging` is ignored by the repo's `.env.*` rule — safe to keep locally for reference, but
  the commands below set variables directly.

### Step-by-step

```powershell
# 0) Preconditions
cd C:\Users\Sajidul Haque Sajid\Desktop\SELLFLOW\backend
git fetch origin; git switch feature/premium-web-ui; git pull --ff-only
git log --oneline -1                      # EXPECT: a549b57 (or later audit commits)
python --version                          # EXPECT: 3.11+ (venv used below)

# 1) Fresh staging secrets for THIS window (interactive; nothing is echoed to history)
python -c "import secrets; print('SECRET_KEY:', secrets.token_urlsafe(48))"
python -c "import secrets; print('DEVICE_TOKEN_SECRET:', secrets.token_urlsafe(48))"
# Copy each value into the environment below when prompted — do not store them in files.

# 2) Create the staging database and the isolated test database (replace HOST/USER as needed)
psql -h <staging-host> -U <admin> -c "CREATE DATABASE sellflow_staging;"
psql -h <staging-host> -U <admin> -c "CREATE DATABASE sellflow_staging_test;"

# 3) Staging application environment (per-session; APP_ENV=production gives production-grade
#    validation — see section 3.2; DATABASE_URL must be the STAGING database)
$env:APP_ENV="production"
$env:APP_DEBUG="false"
$env:SECRET_KEY="<paste staging secret>"
$env:DEVICE_TOKEN_SECRET="<paste staging secret>"
$env:DATABASE_URL="postgresql+psycopg://<user>:<pass>@<staging-host>:5432/sellflow_staging"
$env:CORS_ORIGINS="http://127.0.0.1:8021"
$env:REGISTRATION_INVITE_CODE="<pilot invite code>"

# 4) Migrate to the single head — EXPECT: "Running upgrade ... -> 20261031002"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current   # EXPECT: 20261031002 (head)
.\.venv\Scripts\python.exe -m alembic heads     # EXPECT: exactly one head

# 5) Boot staging (background)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8021 --log-level warning

# 6) Readiness probes — EXPECT as observed in section 3.1
Invoke-WebRequest http://127.0.0.1:8021/health   -UseBasicParsing   # 200
Invoke-WebRequest http://127.0.0.1:8021/status   -UseBasicParsing   # 200
Invoke-WebRequest http://127.0.0.1:8021/database -UseBasicParsing   # 200 {"status":"ok","database":"connected"}
Invoke-WebRequest http://127.0.0.1:8021/ready    -UseBasicParsing   # 200 {"ready":true,...}
Invoke-WebRequest http://127.0.0.1:8021/          -UseBasicParsing  # 200 marketing site
Invoke-WebRequest http://127.0.0.1:8021/app/      -UseBasicParsing  # 200 console shell

# 7) Guardrails in place — EXPECT: no-store + nosniff on API responses
(Invoke-WebRequest http://127.0.0.1:8021/api/v1/info -UseBasicParsing).Headers  # Cache-Control: no-store

# 8) Invite-gated registration smoke (EXPECT 201 with the code, 4xx without)
Invoke-WebRequest http://127.0.0.1:8021/api/v1/auth/register -Method POST -ContentType "application/json" `
  -Body '{"email":"staging-smoke@example.com","full_name":"Staging Smoke","password":"pass1234","business_name":"Staging Shop","invite_code":"<pilot invite code>"}'

# 9) Destructive test suite — ONLY against the isolated *_test database
$env:DATABASE_URL="postgresql+psycopg://<user>:<pass>@<staging-host>:5432/sellflow_staging_test"
$env:SELLFLOW_ALLOW_DESTRUCTIVE_TESTS="1"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest tests/ -q     # EXPECT: 132 passed

# 10) Optional demo data for UI review — TEST database only, the seeder refuses other names
.\.venv\Scripts\python.exe scripts\seed_demo_data.py   # refuses anything not ending _test
```

### Expected results summary

| Step | Pass criterion |
| --- | --- |
| 0 | HEAD is the expected commit; worktree clean |
| 3 | App boots without configuration errors (any missing/placeholder secret aborts startup with a clear message) |
| 4 | `current` == `heads` == `20261031002` (single head) |
| 5–6 | `/ready` 200; with the DB stopped it must turn **503** while `/health` stays 200 |
| 8 | Invite enforcement works; new business visible only to its own login |
| 9 | `132 passed` on `sellflow_staging_test` |

### Rollback

| Layer | Action |
| --- | --- |
| Application | `git switch` back to the previous known-good commit; restart uvicorn. The app is stateless (no server-side sessions). |
| Schema (staging only) | `alembic downgrade <previous-revision>` — e.g. `20261031001`; then `alembic upgrade head` again. Never migrate a production database downward without a snapshot. |
| Staging data | Restore from the staging snapshot/backup (routine backup is a prerequisite — see gates). |
| Secrets | Keep the previous staging secret aside for one deploy window only if a rotation caused a regression; **never** restore the leaked value anywhere. |
| Uploads | Local files under `uploads/` (staging host); restore from the volume snapshot if applicable. |

### Staging vs production separation

| Aspect | Staging | Production |
| --- | --- | --- |
| Database | `sellflow_staging` (+ `sellflow_staging_test` for the suite) | fully separate cluster; never referenced in staging commands |
| `DATABASE_URL` owner | staging user, staging host | production secret store only |
| Secrets | freshly generated per rotation; distinct from all others | rotated after §2; stored as sensitive env vars |
| `APP_ENV` | `production` (for validation fidelity) | `production` |
| Domain / CORS | staging origin(s) only | real origin(s) only |
| Data | synthetic seed or manual smoke accounts; no real customer data | real seller data |
| Registration | invite code enabled | policy decision at launch |
| Payment simulator `/payments/detect` | disabled (404) because `APP_ENV=production` | disabled (404) |
| Uploads | volume/disk acceptable for validation | durable object storage (§6) |

---

## 8. Readiness gates

| Gate | Status | Basis |
| --- | --- | --- |
| G1 Repository & audit integrity | **PASS** | clean tree, in sync, both audit commits present |
| G2 Secret containment | **PASS for staging / FAIL for pilot** | staging rule: fresh, unique staging secrets (never reused from any other environment); pilot blocked until the Vercel + any-host rotation in §2 is executed and verified |
| G3 Configuration, DB connectivity, migrations, env list | **PASS** | §3 executed: readiness semantics verified; single head `20261031002`; fresh-install migration verified in the audit |
| G4 Business-policy proposals (transitions, inventory) | **BLOCKED (approval required)** | §4 documented; implementation intentionally deferred |
| G5 Token-version revocation | **PASS (design) / BLOCKED (implementation)** | §5 plan ready; awaiting approval |
| G6 Durable uploads | **PASS for local/volume staging / BLOCKED for serverless staging** | §6 review; Vercel cannot persist uploads |
| G7 Staging validation run | **READY — not yet executed** | §7 checklist provides exact commands, expected results and rollback |

**Isolated staging validation can start now** under G2's staging rule and locally/on a
persistent-disk host (G6). **Pilot remains blocked** on G2 rotation, G4 approval, and — strongly
recommended — G5 implementation.

## 9. Exact remaining actions

1. Approve §4 (transition matrix; delivered→cancelled decision; inventory Option C).
2. Rotate `SECRET_KEY` + `DEVICE_TOKEN_SECRET` on Vercel and any host that used the leaked file;
   rotate the reused DB password if applicable (§2.3), then verify per §2.4.
3. Execute the §7 staging checklist on the chosen staging host and record results here.
4. Approve and schedule §5 (token-version revocation) before pilot.
5. Choose the durable upload path (§6) before any hosted staging that must retain images.
6. Keep the audit suite green (`pytest tests/ -q`, 132 passed) as the standing regression gate.
