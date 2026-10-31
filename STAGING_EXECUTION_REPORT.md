# SellFlow — Staging Execution Report

**Executed:** 2026-10-31 · **Branch:** `feature/premium-web-ui` · **Constraints honored:** no
production deployment, no production database access, destructive operations only against
`*_test` databases, no credentials in source/commits/reports, no architecture changes.

| Item | Value |
| --- | --- |
| Baseline before this execution | `1012a0f` |
| Transition-matrix commit | `31afed2` — `feat(orders): enforce the approved status-transition matrix (409 on violations)` |
| Token-version commit | `89c76c6` — `feat(auth): per-user JWT token-version revocation (STAGING_READINESS.md 5)` |
| Remote | pushed to `origin/feature/premium-web-ui` (`1012a0f..89c76c6`) |
| Migration head | `20261031003` (single head) |
| Test database | `sellflow_audit_test` (name ends `_test`); `sellflow_migration_test` also migrated |
| Final suite | **138 passed** (85 s) |
| Live smoke | **22/22 checks passed** (real HTTP against a local server) |
| Vercel | Preview deployment Ready (URL below); production untouched |

---

## 1. Repository integrity

- Branch `feature/premium-web-ui`; worktree clean before and after; both audit commits
  (`dbcbdcf`, `a549b57`) and the dossier (`1012a0f`) preserved.
- All commands in this execution ran against `sellflow_audit_test` (or a scratch name ending
  `_test`). No production resource was read or written; production URL was only probed once with a
  GET and still serves the pre-existing build (`<title>SellFlow - Operations Console</title>`).

## 2. Order status transition policy — IMPLEMENTED (`31afed2`)

Implemented exactly as proposed in `STAGING_READINESS.md` §4.1 (the two previously flagged points
were adopted as proposed; both are single-constant adjustable):

| From \ To | created | confirmed | packed | shipped | delivered | cancelled |
| --- | :-: | :-: | :-: | :-: | :-: | :-: |
| created | no-op | ✅ | — | — | — | ✅ |
| confirmed | — | no-op | ✅ | ✅ | — | ✅ |
| packed | — | — | no-op | ✅ | — | ✅ |
| shipped | — | — | — | no-op | ✅ | ✅ |
| delivered | — | — | — | — | no-op | ❌ (as proposed) |
| cancelled | — | — | — | — | — | no-op |

- Disallowed transitions → **HTTP 409** with `detail: {message, current_status,
  requested_status, allowed_transitions}`; the row is unchanged (verified by re-read).
- Same-status → 200 no-op, no webhook/notification (previous behaviour preserved; verified by the
  background-task test).
- Unknown enum values → 422 (schema validation precedes the matrix).
- Console (`webapp/js/pages/orders.js`) offers only allowed next states; `api.js` surfaces the
  structured 409 message; terminal orders show no status section and keep only
  View / Record-payment actions.

## 3. Inventory Option C — REPORTED, NOT IMPLEMENTED (clarification required)

Task instruction: report its exact behaviour before implementing; do not invent rules. The
documented Option C text (`STAGING_READINESS.md` §4.2, verbatim behaviour list):

1. **“Keep manual stock”** — no automatic decrement on orders; sellers edit `stock_quantity`
   through the product form; the API rejects negative stock (`ge=0`). This is already the current,
   tested behaviour (pinned by `test_inventory_cannot_go_negative`).
2. **“when ordering more than available, show a non-blocking warning”** — mechanics unspecified.
3. **“and record it in the order note”** — mechanics unspecified.
4. **“add a stock-adjustment audit trail later”** — explicitly deferred to a future design.

Undefined mechanics (these are the reasons no code was written):

- **Where does the warning live?** Console-only (JS comparing line quantity to stock) or
  API-surfaced (e.g. a `warnings: []` field on order creation) so every client sees it?
- **What is “more than available”?** `quantity > stock_quantity`, or also stock == 0, or a
  low-stock threshold? (Archived products are already blocked outright by the archived guard.)
- **Who writes the note and how?** Server-appended system note to `orders.notes` (mixes machine
  text with seller text; format?), or the console includes it in the seller-visible note?
- **Per line or per order?** Multiple lines exceeding stock — one warning, or one per item?

Nothing was implemented (no endpoint, UI, or schema change), per “do not invent inventory rules”.
The three questions above are the clarification needed; the recommendation (Option C now, Option B
only after a stock-movement ledger) is unchanged from the dossier.

## 4. Token-version revocation — IMPLEMENTED (`89c76c6`)

Per `STAGING_READINESS.md` §5, including the **hard cutover** choice (missing `ver` → rejected):

- Migration `20261031003_add_token_version`: `users.token_version INTEGER NOT NULL DEFAULT 0`,
  idempotent guard, `down_revision = 20261031002`.
- JWTs minted at login carry `ver`; `get_current_user` and the device bridge `_optional_user`
  both enforce it via one shared helper (`app/core/security.py::token_version_matches`).
- `POST /api/v1/auth/passcode/change` bumps `token_version`, revoking every existing session.
- Console: password change signs the current session out with an accurate message; the Security
  card text now states that all sessions end.
- Device bridge (HMAC `X-Device-Token`) is untouched — verified even when a stale bearer token is
  sent alongside a valid device token.

## 5. Migration results (isolated databases)

| Step | Result |
| --- | --- |
| `alembic upgrade head` on `sellflow_audit_test` | `20261031002 -> 20261031003` applied |
| `alembic current` / `alembic heads` | both `20261031003 (head)` — **single head** |
| Round trip `downgrade 20261031002` | `token_version` **ABSENT** |
| Re-`upgrade head` | `token_version` present, `integer`, `NOT NULL`, default `0` |
| `sellflow_migration_test` | at `20261031003 (head)` (in sync) |
| Revision graph | single root `bc178152c42e` → single head, no new branches |

## 6. Test results

**Focused suites (during implementation):** 46 passed — token-version audit (6), business ops
(incl. the new matrix test), background tasks, auth lifecycle, isolation matrix, console upgrades.

**Full suite (final tree, isolated `_test` DB):**
`python -m pytest tests/ -q` → **138 passed, 6 warnings in 85 s**
(96 at audit baseline → 132 after audit fixes → 138 now; +6 token-version cases.)

**Live smoke — 22/22 checks passed** against a locally running server (`uvicorn`, port 8021,
`sellflow_audit_test`), covering the task-9 list:

| Area | Live evidence |
| --- | --- |
| Authentication | register → login → `/auth/me`; password change → old token 401; fresh login 200 |
| Uploads | multipart upload 201; `/uploads/...` URL with 128-bit random token; image serves `image/png` + `nosniff` |
| Payment reconciliation | exact amount + customer phone → engine `PAID` / `AUTO_MATCHED` (confidence 0.95, `EXACT_AMOUNT_MATCH` + `CUSTOMER_MATCH`); summary `paid_events ≥ 1`; order marked paid with a recorded payment |
| Transitions | created → shipped **409** with allowed set; created → confirmed 200 |
| Isolation | cross-tenant order read 403; cross-tenant `/payment-accounts` 403; own-business reads 200 |
| Health | `/health` 200 and `/ready` 200 `{"ready":true}` |

## 7. Staging configuration review and local launch commands

Reviewed (details in `STAGING_READINESS.md` §3): `APP_ENV`, `APP_DEBUG`, `SECRET_KEY`,
`DEVICE_TOKEN_SECRET`, `DATABASE_URL`, `CORS_ORIGINS`, `REGISTRATION_INVITE_CODE`, upload
limits; `AWS_*` remains reserved (no code uses it). For staging fidelity run
`APP_ENV=production` (this only controls validation strictness — never which database is used).

**Launch the backend and the PWA locally (Windows PowerShell):**

```powershell
cd C:\Users\Sajidul Haque Sajid\Desktop\SELLFLOW\backend

# 1) Fresh per-session secrets (paste into the variables below; never commit them)
python -c "import secrets; print('SECRET_KEY:', secrets.token_urlsafe(48))"
python -c "import secrets; print('DEVICE_TOKEN_SECRET:', secrets.token_urlsafe(48))"

# 2) Staging-grade environment (point DATABASE_URL at a *_staging / *_test database only)
$env:APP_ENV="production"
$env:APP_DEBUG="false"
$env:SECRET_KEY="<paste>"
$env:DEVICE_TOKEN_SECRET="<paste>"
$env:DATABASE_URL="postgresql+psycopg://<user>:<pass>@<host>:5432/sellflow_audit_test"

# 3) Migrate, then serve BOTH surfaces from the one FastAPI app
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8021

# Marketing site + PWA:  http://127.0.0.1:8021/       (manifest, /sw.js, offline page)
# Seller console:        http://127.0.0.1:8021/app/
# Readiness check:       http://127.0.0.1:8021/ready   -> {"ready":true,...}
```

PWA install check (localhost counts as a secure context): open `http://127.0.0.1:8021/` in
Chrome/Edge → DevTools ▸ Application ▸ Manifest (icons, `start_url=/app/`) and ▸ Service Workers
(activated; `/api/*` cache entries must be absent) → address-bar “Install”. Offline check:
DevTools ▸ Network ▸ Offline → reload → offline page (site) / shell (console).

Deterministic cleanup after a session: stop uvicorn (`Ctrl+C`) — no background state remains.

## 8. Vercel (preview only — production untouched)

- `vercel deploy --scope tsg-bfe6` (no `--prod`) → **Preview** deployment Ready:
  `https://sellflow-site-g55ftuma8-tsg-bfe6.vercel.app` (plus the equivalent auto-preview from the
  push: `https://sellflow-site-iipf9rl1g-tsg-bfe6.vercel.app`).
- Previews are behind **Vercel Authentication** (anonymous requests get the Vercel login page —
  verified by page title `Login - Vercel`). View them signed in to the `tsg-bfe6` team for staging
  validation. They host the static surfaces only: the project has no `DATABASE_URL`, so DB-backed
  endpoints cannot authenticate/function there (by design — no production or staging database was
  attached).
- **Production is unchanged:** `https://sellflow-site.vercel.app/` still serves the pre-existing
  build (verified read-only). Promoting a preview (`vercel deploy --prod`) is left to the owner
  after approval.
- Deployment hygiene: `.vercelignore` now excludes `.env` / `.env.*` so local values can never
  enter a build; the only tracked env file remains the value-free `.env.example`.

## 9. Readiness gates

| Gate | Status | Basis |
| --- | --- | --- |
| G1 Repository & audit baseline preserved | **PASS** | clean tree, synced, audit commits intact |
| G2 Order status transition policy | **PASS** | implemented per §4.1; matrix + 409 edge cases tested; live-verified |
| G3 Inventory Option C | **PASS (report) / BLOCKED (implementation)** | exact behaviour + 3 clarification questions in §3; nothing invented |
| G4 Token-version revocation | **PASS** | migration + both enforcement sites + UX; 6 regression cases; live-verified |
| G5 Regression tests | **PASS** | new/updated suites; 46 focused, 138 full |
| G6 Single-head migrations | **PASS** | `20261031003` sole head; downgrade/re-upgrade round trip verified |
| G7 Tests on isolated `_test` DB | **PASS** | `sellflow_audit_test`; guard active (`SELLFLOW_ALLOW_DESTRUCTIVE_TESTS=1`) |
| G8 Staging config + launch commands | **PASS** | §7; verified by actually launching and probing |
| G9 Uploads / reconciliation / auth / isolation | **PASS** | 22/22 live checks + suite coverage |
| G10 Execution report | **PASS** | this file |
| G11 Secret rotation (dossier §2) | **BLOCKED (owner action)** | the leaked-key rotation on Vercel/other hosts is still pending; staging itself uses fresh keys and is unaffected |

## 10. Remaining blockers and actions

1. **Clarify Inventory Option C mechanics** (the four questions in §3) before any implementation.
2. **Rotate the leaked `SECRET_KEY`** (Vercel + any host that ever used `.env.production`), then
   verify per the dossier §2.4 — required before any pilot with real sellers.
3. Decide whether `delivered → cancelled` and `created → shipped` (adopted as disallowed) should
   differ; both are one-line constant changes if the product decision goes the other way.
4. Optional: attach a staging database to the Vercel preview project if DB-backed preview testing
   is desired (never the production cluster).
