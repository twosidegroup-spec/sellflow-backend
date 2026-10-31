# SellFlow — Database-Backed Staging Deployment Report

**Executed:** 2026-10-31 · **Branch:** `feature/premium-web-ui` · no production deployment, no
production database access, no production environment variables modified.

| Item | Value |
| --- | --- |
| Code commits | `7303d91` (Inventory Option C) · `12ab8af` (managed-provider DB URLs) — pushed |
| Migration head | `20261031004` (single head; all three databases at head) |
| Local staging DB | `sellflow_staging` (localhost) — migrated 0 → head |
| Hosted staging DB | Neon resource **`sellflow-staging-db`** (Free plan), connected to **preview only** |
| Vercel preview | `https://sellflow-site-mtnu0sz7n-tsg-bfe6.vercel.app` (Ready, Preview, protected) |
| Tests | `pytest tests/ -q` → **149 passed**; live HTTP smoke → **27/27** against the hosted staging DB |
| Production | untouched — old build still served; env list unchanged (2 secrets) |

---

## 1. Inventory Option C — implemented to the approved mechanics (`7303d91`)

| Approved requirement | Implementation |
| --- | --- |
| Backend-generated warnings | `create_order_with_warnings()` compares each line's requested quantity against the product's current stock |
| API warnings field | `OrderCreateResponse.warnings: StockWarning[]` on `POST /orders/` — `{product_id, product_name, quantity_requested, stock_available, message}` |
| Console displays warnings | creation toast lists every warning; the orders table marks the row (“stock warning”); the detail modal shows the full system note |
| Warn when requested exceeds available, **including zero stock** | yes — zero-stock products produce a warning with `stock_available: 0` |
| Server-generated order system notes | new `orders.system_notes` column (migration `20261031004`), written only by the server, never into the seller-editable `notes` |
| Never reject orders solely for stock | verified: zero-stock and short-stock orders return **201** |
| Tests: multiple affected products, sufficient stock | `tests/test_stock_warnings_audit.py` (8 tests): 2-product warning + system notes, seller note preserved, sufficient stock → no warnings/notes, zero stock, `requested == stock` boundary, custom items, totals unchanged, archived guard unchanged, tenant scoping |

## 2. Unchanged behaviours re-verified

- **Order transitions** — matrix suite passes unchanged (created→confirmed 200; created→shipped
  409 with `allowed_transitions`; terminals locked; live-verified).
- **Token-version revocation** — 6-case suite passes (password change revokes old tokens on every
  protected surface including `/payment-accounts`; device tokens unaffected; live-verified).
- **Discount bound, archived products, tenant isolation, idempotent payments** — all suites green.

## 3. Database preparation and migration results

**Hosted staging (Neon, created via the Vercel marketplace CLI, Free plan, *preview* connection):**
`alembic upgrade head` executed from this machine against the hosted staging database —
18 migrations ran from zero, ending at `20261031004`; `current == heads == 20261031004`.
The pooled connection exercised the new managed-provider URL handling (scheme normalisation +
psycopg `prepare_threshold=None`). Identifier: resource `store_w9FAQsviQpLMgcnj`
(“sellflow-staging-db”, external id `fragrant-resonance-15490133`). No URL or credential appears
in this report, the repository, or any commit.

**Local staging (`sellflow_staging`, localhost):** created and migrated 0 → `20261031004`; used for
the first full staging smoke.

**Test DB (`sellflow_audit_test`):** at `20261031004` (guard-enforced; all pytest runs use it).

## 4. Vercel configuration (preview scope only)

Added to **Preview** only (verified by name list; values are unreadable “Hidden/Secret”):

| Variable | Scope | Note |
| --- | --- | --- |
| `DATABASE_URL` (+ `DATABASE_URL_UNPOOLED`, `POSTGRES_*`, `PG*`) | Preview | injected by the Neon integration; fresh staging database |
| `APP_ENV=production`, `APP_DEBUG=false` | Preview | staging runs with production-grade validation |
| `SECRET_KEY`, `DEVICE_TOKEN_SECRET` | Preview | freshly generated for preview (64-char URL-safe); unrelated to any leaked or production value |

**Production environment variables were not modified** — the scope still lists exactly
`DEVICE_TOKEN_SECRET` and `SECRET_KEY` (created 6 h before this task). No production database
credential exists anywhere in the project.

Deployment hygiene: `.env*` files are excluded from Vercel bundles (`.vercelignore`); the only
local env artifact recently written by tooling is `.env.local` (a Vercel OIDC token only, ignored
by git and by `.vercelignore`).

## 5. Live verification against the hosted staging database (task 8)

Local server (production-mode: `APP_ENV=production`, fresh secrets) connected to the **Neon
staging** database — `GET /ready` → `200 {"ready":true,"checks":{"database":"ok","api":"ok"}}` —
then the 27-check end-to-end smoke:

| Area | Result |
| --- | --- |
| Registration / login / `/auth/me` | PASS |
| Password-change revocation (old token 401, fresh login 200) | PASS |
| Products incl. multipart image upload + serving (`image/png`, `nosniff`, random name) | PASS |
| Orders: creation, server-computed totals, **stock warnings (zero stock, 201, system note, totals unchanged)** | PASS |
| Payment reconciliation: engine `AUTO_MATCHED` (0.95, exact amount + customer phone), summary updated | PASS |
| Transitions: created→shipped 409 with allowed set; created→confirmed 200 | PASS |
| Cross-tenant isolation (orders 403, payment accounts 403, own access 200) | PASS |

All 27 checks also passed identically against the local `sellflow_staging` database.

## 6. Preview protection and production safety

- The new preview is protected by **Vercel Authentication**: an anonymous `GET /ready` returns
  Vercel’s login wall (HTTP 200, `<title>Login - Vercel</title>`) — protection **remains enabled**
  (task 9 PASS). Consequence: HTTP verification of the preview must be done from a signed-in
  browser; the equivalent automated verification ran against the same staging database from this
  machine (§5).
- Deployment list confirms the artifact is **Preview** (not Production); the production URL still
  serves the pre-existing build (`<title>SellFlow - Operations Console</title>`, verified read-only).

## 7. Operational limitations (honest list)

1. **Uploads do not persist on serverless**: product images are written to the local filesystem;
   on Vercel that filesystem is read-only/ephemeral, so image upload through the *preview* is
   expected to fail or vanish (the code documents the clear-500 path). Uploads work on any host
   with a persistent disk and were fully verified locally. Durable object storage (R2) remains the
   documented follow-up (dossier §6).
2. **Preview HTTP is behind Vercel Authentication** — no anonymous probes; the DB-backed proof in
   §5 used the identical staging database and environment shape.
3. **Neon Free plan** — limited compute/storage; adequate for staging, not for pilot traffic.
4. **Secrets added via stdin are stored as sensitive (unreadable)** — rotation requires re-add
   (documented), by design.
5. **No monitoring/alerting and no backup drill** yet; Neon Free provides limited history
   (point-in-time restore is a paid feature) — not sufficient for pilot.
6. `REGISTRATION_INVITE_CODE` is unset on preview: registration is open, but only reachable behind
   Vercel Authentication. Set it before any wider pilot.
7. The leaked historical `SECRET_KEY` rotation (dossier §2) remains an owner action — unrelated to
   staging, but still blocks pilot.

## 8. Staging gates

| Gate | Status | Basis |
| --- | --- | --- |
| G1 Repository/baseline preserved | **PASS** | commits pushed; worktree clean; audit history intact |
| G2 Option C implemented to approved mechanics | **PASS** | §1 + tests + live checks |
| G3 Transition rules unchanged | **PASS** | matrix suite + live 409/200 checks |
| G4 Token-version revocation intact | **PASS** | suite + live revocation checks |
| G5 Dedicated PostgreSQL staging database | **PASS** | Neon `sellflow-staging-db` (preview-only) + local `sellflow_staging` |
| G6 Vercel preview env vars only; no production credentials | **PASS** | preview-scope list; production scope unchanged |
| G7 Migrations against staging + `/ready` | **PASS** | 0 → `20261031004` on hosted staging; `/ready` 200 |
| G8 Registration/login/products/orders/payments/reconciliation/uploads/isolation | **PASS** | 27/27 live checks (hosted staging) |
| G9 Preview protection remains enabled | **PASS** | Vercel login wall on anonymous access |
| G10 No production deployment / production untouched | **PASS** | deployment list = Preview; prod URL + env unchanged |
| G11 Durable uploads on the deployed preview | **BLOCKED (known)** | serverless filesystem; R2 plan documented |
| G12 Leaked-key rotation (dossier §2) | **BLOCKED (owner action)** | required before pilot |

## 9. Exact commands (owner runbook)

```powershell
# Present the preview (signed in to the tsg-bfe6 team in a browser)
#   https://sellflow-site-mtnu0sz7n-tsg-bfe6.vercel.app
# Re-deploy a preview after changes (never --prod until approved):
cd C:\Users\Sajidul Haque Sajid\Desktop\SELLFLOW\backend
vercel deploy --scope tsg-bfe6

# Migrate the hosted staging database from this machine (URL comes from the
# preview env; never paste it into a file or a shell history you keep):
vercel env pull $env:TEMP\preview-env.tmp --environment=preview --scope tsg-bfe6 --yes
$line = Get-Content $env:TEMP\preview-env.tmp | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
$env:DATABASE_URL = $line.Substring('DATABASE_URL='.Length).Trim().Trim('"')
.\.venv\Scripts\python.exe -m alembic upgrade head
Remove-Item $env:TEMP\preview-env.tmp -Force

# Full local staging run (production-mode validation, local staging DB):
$env:APP_ENV="production"; $env:APP_DEBUG="false"
$env:SECRET_KEY=...; $env:DEVICE_TOKEN_SECRET=...      # fresh, ≥32 chars, never committed
$env:DATABASE_URL="postgresql+psycopg://.../sellflow_staging"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8021

# Destructive test suite — only ever against a database ending in _test:
$env:DATABASE_URL="postgresql+psycopg://.../sellflow_audit_test"
$env:SELLFLOW_ALLOW_DESTRUCTIVE_TESTS="1"; $env:APP_DEBUG="false"
.\.venv\Scripts\python.exe -m pytest tests/ -q      # expect: 149 passed
```
