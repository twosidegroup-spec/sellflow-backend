# SellFlow — Pilot Readiness Report

**Executed:** 2026-11-01 · **Branch:** `feature/premium-web-ui` · commits `b225c49` (R2 storage),
`9428555` (invite gate tests), report commit follows. No production deployment; no production
environment variables modified; no credentials in this report, the repository, or Git.

| Item | Value |
| --- | --- |
| Regression suite | **161 passed** on the isolated `sellflow_audit_test` database |
| Live staging smoke | **27/27** against the hosted staging database |
| Backup/restore drill | **RESTORE VERIFIED**, twice (revision + all 22 table counts match) |
| Hosted staging DB | Fresh Neon resource `sellflow-staging-db` (Free plan), **preview-only**, at `20261031004` |
| Preview deployments | `https://sellflow-site-aallfgvrl-tsg-bfe6.vercel.app` (latest), protected by Vercel Authentication |
| Production | untouched (env: 2 pre-existing secrets; site serves the old build) |

---

## 1. Durable image storage (Cloudflare R2) — implemented, live check BLOCKED

`app/core/storage.py` adds a pluggable storage layer behind `STORAGE_BACKEND`:

- **`local`** (default): historical disk behaviour — development and hosts with a persistent disk.
- **`r2`**: Cloudflare R2 via the S3 API (boto3 pinned at 1.43.123) — durable on serverless.
  Configuration is fail-closed: selecting `r2` without `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`, `AWS_S3_ENDPOINT` and `STORAGE_PUBLIC_BASE_URL`
  refuses to load settings; unknown backends are rejected; there is **no silent fallback** to
  ephemeral disk.

All existing upload guarantees are preserved (the adapter only moves bytes):
server-side filename generation (128-bit random token), extension derived from the validated
content type, MIME allow-list, 10 MB size cap, tenant-scoped routes, and generic error handling —
storage failures answer **502 "Image storage is temporarily unavailable"** with nothing persisted,
and adapter messages never include bucket names, endpoints or credentials. Product deletion
cleans stored objects best-effort and refuses foreign/traversal URLs.

**Tests** (`tests/test_storage_audit.py`, 11): local round trip; traversal/invalid URL refusal;
R2 request shape via a fake S3 client (bucket, `products/<file>` key, content type, returned URL);
generic failure message; best-effort delete; backend selection + fail-closed settings; 502 on
storage outage with zero side effects; oversized and invalid uploads; upload→delete cleanup;
tenant scoping.

**BLOCKED — live R2 verification:** no R2 credentials exist in this environment, so the adapter
has not been exercised against the real service, and the deployed preview still uses `local`
storage (uploads on Vercel fail with the clear 502 — DB rows are never half-created). To enable
durable uploads when credentials exist (owner action, preview scope only):

```powershell
# 1) Cloudflare dashboard: create bucket (e.g. sellflow-media) + an R2 API token
#    (Object Read & Write) and a public access domain (or custom domain) for the bucket.
# 2) Add preview-only configuration (values never committed):
"r2"                                  | vercel env add STORAGE_BACKEND preview --scope tsg-bfe6 --force
"https://<account>.r2.cloudflarestorage.com" | vercel env add AWS_S3_ENDPOINT preview --scope tsg-bfe6 --force
"<bucket>"                            | vercel env add AWS_S3_BUCKET preview --scope tsg-bfe6 --force
"auto"                                | vercel env add AWS_REGION preview --scope tsg-bfe6 --force
"<access-key-id>"                     | vercel env add AWS_ACCESS_KEY_ID preview --scope tsg-bfe6 --force
"<secret-access-key>"                 | vercel env add AWS_SECRET_ACCESS_KEY preview --scope tsg-bfe6 --force
"https://<public-domain>"             | vercel env add STORAGE_PUBLIC_BASE_URL preview --scope tsg-bfe6 --force
vercel deploy --scope tsg-bfe6      # redeploy; then run the upload test below
```

Post-configuration acceptance check: upload a product image on the preview, fetch the returned
`image_url` (must serve `image/png` with `nosniff`), delete the product, confirm the object is
gone from the bucket.

## 2. `REGISTRATION_INVITE_CODE` — enforcement tested; value is an owner input

The gate is implemented (`app/auth/router.py`, constant-time comparison) and now has a regression
test (`tests/test_auth_lifecycle.py::test_registration_invite_code_gate`): missing/wrong code →
**403**, correct code → 201. The value itself must be chosen by the operator (it has to be shared
with invited sellers) and is added to **preview only**:

```powershell
"<pilot-invite-code>" | vercel env add REGISTRATION_INVITE_CODE preview --scope tsg-bfe6 --force
vercel deploy --scope tsg-bfe6
```

Until set, registration is open on the preview (reachable only behind Vercel Authentication).
**BLOCKED (owner input)** for seller onboarding.

## 3. Backup and restore (staging PostgreSQL) — procedure executed and verified

Neon Free has no point-in-time restore, so backups are explicit dumps. The procedure below was
**executed twice today** (before and after the smoke data) with full verification.

```powershell
# DUMP (unpooled URL preferred; never paste the URL into committed files)
vercel env pull $env:TEMP\preview-env.tmp --environment=preview --scope tsg-bfe6 --yes
$line = Get-Content $env:TEMP\preview-env.tmp | Where-Object { $_ -match '^DATABASE_URL_UNPOOLED=' } | Select-Object -First 1
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" --format=custom --no-owner --no-privileges `
  --file="staging-$(Get-Date -Format yyyyMMdd-HHmm).dump" $line.Substring(27).Trim('"')
Remove-Item $env:TEMP\preview-env.tmp -Force      # never leave credentials on disk

# RESTORE (always into a fresh scratch database; local names end _test)
& "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -h localhost -U postgres sellflow_restore_test
& "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" --no-owner --no-privileges --exit-on-error `
  -h localhost -U postgres -d sellflow_restore_test staging-<timestamp>.dump
```

**Verification of a successful restore** (all three must hold):
1. `alembic current` on the restored database equals the source (observed: `20261031004` both).
2. Row counts match for every business table (observed: all 22 tables identical, including
   `users`, `orders`, `payments`, `payment_events`, `payment_decisions`, `rate_limit_events`).
3. A read-only sanity check against the restored copy (e.g. login of a known smoke account, or
   the drill script `drill_backup_restore.py` used today) — counts passed, so step 3 is optional
   but recommended for milestone backups.

Cadence recommendation: dump before every pilot milestone and weekly while sellers are active;
keep dumps outside the repository; delete local dumps after verification from shared machines.
**PASS** (procedure + verification executed; evidence above).

## 4. Monitoring recommendations (low cost)

| Concern | Recommendation |
| --- | --- |
| Uptime / readiness | Free keyword monitor (Better Stack or UptimeRobot) on `GET /ready` expecting `"ready":true`; alert after 2 consecutive failures. **Note:** the preview sits behind Vercel Authentication — enable *Protection Bypass for Automation* in the Vercel project settings and send the bypass header from the monitor (both tools support custom headers on free tiers), or monitor the eventual public production domain instead. |
| Application errors | Sentry free tier (5k errors/month) with `sentry-sdk[fastapi]`; initialise only when `SENTRY_DSN` is set, with `send_default_pii=False` and traces off; add `SENTRY_DSN` to **preview only** first. Vercel's own function logs remain useful for ad-hoc debugging but have short retention. |
| Database | Neon dashboard metrics (connections, compute wake-ups); alert on connection saturation. With `pool_pre_ping` and `prepare_threshold=None`, pooled staging is safe from idle-pooler drops. |
| Business signals | The Home dashboard already surfaces the review queue; no external alerting needed for the pilot. |

These are documentation-only (no code or dependencies added), matching the low-cost constraint.

## 5. Environment-variable separation audit — PASS

| Scope | Variables (names only) | Assessment |
| --- | --- | --- |
| **Production** | `SECRET_KEY`, `DEVICE_TOKEN_SECRET` (unchanged today) | No database credentials; site serves the old static build. The historical-key rotation remains deferred (production env must not be modified here); required before any **production** launch, not for this staging pilot. |
| **Preview** | `DATABASE_URL` + full Neon set (`DATABASE_URL_UNPOOLED`, `POSTGRES_*`, `PG*`), `APP_ENV=production`, `APP_DEBUG=false`, `SECRET_KEY`, `DEVICE_TOKEN_SECRET` (all fresh) | Staging-only credentials; fresh secrets unrelated to any leaked value. `STORAGE_*`/`AWS_*` (R2) not yet set — see §1. |
| **Development** | none | Clean. |
| Local files | `.env` (gitignored), `.env.local` (Vercel OIDC token, gitignored); `.vercelignore` excludes `.env`/`.env.*` from bundles | No secrets in Git. |

The Neon resource is connected to `sellflow-site` **preview only** (verified via
`vercel integration resource inspect`), and production env variables were not touched.

### Credential-handling incident during this task (full disclosure)

- A failed `pg_dump` invocation echoed **a fragment of the staging database URL** (old
  credentials) into terminal output. No production credentials were involved.
- Remediation was attempted by rotating the database password and updating the preview env vars.
  During that rotation the new password was not persisted before the old one was invalidated
  (sequencing error), which made the staging database credential-inaccessible from the CLI.
- Recovery: the disposable staging resource (containing only synthetic smoke data) was deleted and
  **recreated fresh**; the staging database was re-migrated to `20261031004`, re-seeded with the
  live smoke (27/27), and the backup/restore drill re-verified. Both the leaked fragment and the
  transient password belonged to the deleted project and are defunct.
- Current staging credentials exist only in the preview environment. For future rotations use the
  Neon console **Reset password** (Vercel SSO link) and update the preview env in the same
  operation — the CLI has no rotate command and a disconnect/reconnect re-serves the cached
  (stale) credential.
- The same failed command also echoed the **local development** database password; local-only
  (localhost Postgres) — rotate it if this machine's logs are shared.

## 6. Test results

| Suite | Result |
| --- | --- |
| `pytest tests/ -q` (`sellflow_audit_test`) | **161 passed** (149 → +11 storage, +1 invite) |
| Live smoke, hosted staging DB (production-mode app) | **27/27** (auth, revocation, products, uploads, orders, stock warnings, reconciliation, transitions, isolation) |
| Backup/restore drill | **RESTORE VERIFIED** ×2 |
| JS syntax checks | pass (console modules) |

## 7. Gates

| Gate | Status | Basis |
| --- | --- | --- |
| G1 Repo integrity / architecture preserved | **PASS** | commits pushed, worktree clean, no unrelated features |
| G2 R2 adapter implemented (validation, keys, errors preserved) | **PASS** | §1 + 11 tests |
| G3 Live R2 verification | **BLOCKED (no credentials)** | never claimed successful; enablement steps in §1 |
| G4 Upload/retrieval/deletion/invalid/oversized/failure/tenant tests | **PASS** | `tests/test_storage_audit.py` |
| G5 `REGISTRATION_INVITE_CODE` enforcement | **PASS** (value = owner input) | §2 |
| G6 Backup/restore procedure + verified restore | **PASS** | §3, executed twice |
| G7 Monitoring recommendations (low cost) | **PASS** | §4 |
| G8 Preview/Production env separation audit | **PASS** | §5 |
| G9 Full regression suite on `_test` database | **PASS** | 161 passed |
| G10 Staging DB operational (fresh, migrated, smoke-tested) | **PASS** | §5, §6 |
| G11 Durable uploads on the deployed preview | **BLOCKED** | needs R2 credentials (§1) or a persistent-disk host |
| G12 Production secret rotation (historical key) | **DEFERRED** | production env must not be modified in this task; required before production use, not before this staging pilot |

## 8. Recommendation

# READY FOR CONTROLLED PILOT

…with two operator-supplied configuration items before sellers are onboarded, both prepared and
documented above:

1. **Set `REGISTRATION_INVITE_CODE` (preview)** and share the code with invited sellers (§2).
2. **Add R2 credentials (preview)** so product images persist (§1). If R2 credentials cannot be
   provided immediately, run the controlled pilot on a host with a persistent disk (image uploads
   are fully functional there) or accept image-less products on the preview — every other flow is
   verified working, and uploads fail *safely* (clear 502, no partial records).

Optional but recommended before scaling beyond the controlled group: Sentry + uptime monitoring
(§4) and the production secret rotation (§5, before any production launch).
