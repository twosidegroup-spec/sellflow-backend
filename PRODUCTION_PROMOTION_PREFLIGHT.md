# Production Promotion Pre-Flight

**2026-11-01 · Evidence-only pass — nothing was executed (no push to `main`, no merge, no
deployment, no environment changes, no database actions, no history rewrite).**
Baseline: `feature/premium-web-ui` @ `58cba9e` · `origin/main` @ `b0862a1` · report commit follows.

---

## 1. Recommendation

# ✅ APPROVE PROMOTION — conditional on the three pre-flight checks in §12

The release is a **fast-forward of 26 commits** that replaces the stale backend-only `main` with the
complete current product; its build/packaging was **verified green** by the automated Preview
deployments of the exact tip (§4). The conditions are configuration confirmations (production
branch, legacy-project side effect, production database), all answerable in the Vercel dashboard —
none of them is a defect in the release itself.

---

## 2. Proposed source and target

| | |
| --- | --- |
| Source | `origin/feature/premium-web-ui` @ `58cba9e` |
| Target | `origin/main` @ `b0862a1` |
| Relationship | **Fast-forward** — `git merge-base --is-ancestor origin/main feature` = true; merge-base = `b0862a1`; no divergent work, no commits lost or overwritten |
| Suggested mechanism | PR `feature/premium-web-ui` → `main`, merge (FF or merge commit; either deploys the tree) — **not executed** |

## 3. What enters the release (verified)

- **26 commits**, including: the System A→B payment-intelligence integration (`4aeb5a1`), the web
  console (`b3f1f6f`), Vercel serverless config (`07d7582`), the marketing site + PWA (`2123b9e`),
  the full audit (`dbcbdcf`, `a549b57`), transitions (`31afed2`), token-version revocation
  (`89c76c6`), Inventory Option C (`7303d91`), managed-provider DB URLs (`12ab8af`), R2 storage
  (`b225c49`), and the security/staging/pilot reports (`9345e28`, `4c2fd93`, `58cba9e`, …).
- **283 files changed, +33,348 / −585** — `A: 234`, `M: 43`, `D: 6`.
- **Deleted files (all intentional, none application code):** `.env.production` (the containment),
  `render.yaml`, `build.sh`, `docker-compose.yml`, `docker-compose.prod.yml`,
  `tests/test_rate_limit.py` (superseded by `test_migration_security.py`).
- **Migrations entering:** 10 new versions (`20261022001`…`20261031004`, single head
  `20261031004`) + 2 modified migration files. **Vercel builds do not run migrations** (no
  build step in `vercel.json`) — they only run when executed explicitly against a database.
- **Dependency delta:** fastapi 0.162.0, psycopg[binary] 3.2.3, python-jose[cryptography] 3.5.0,
  python-multipart 0.0.32, boto3 1.43.123, jinja2 — already exercised by 161 passing tests.
- *Note:* the inventory above is pinned to baseline `58cba9e`. Any pre-flight/report commits made
  on this branch (including the commit that introduces this document) also ride along with the
  promotion and are **documentation-only** — they change no application code, migrations,
  dependencies or deployment configuration.
- **No application replacement:** `app/main.py` and core modules are `M` (evolved), not delete+add
  of a different product; the six deletions above are old deployment/ops files only.

## 4. Actual Vercel Production configuration (as far as the tooling can read)

| Item | Evidence |
| --- | --- |
| Project | `sellflow-site` (id `prj_y99ZUQfX…`, team `tsg-bfe6`) |
| Domains | Production: `https://sellflow-site.vercel.app` (public, reachable anonymously); Previews: behind Vercel Authentication |
| Repository link | **Proven**: commit `58cba9e` carries statuses *“Vercel – sellflow-site”* + *“Vercel – sellflow-backend”*; Vercel built both as **Preview** deployments in ~24 s (`dpl_EgPH366HxY7ZzWRV56bxM24GX7s2` → `sellflow-site-qtzlua6o8…`) |
| **Production branch** | **Not readable via CLI** (no dashboard/API read path with available tooling). Evidence: every git-triggered deployment observed is a **Preview** ⇒ the production branch is *not* the feature branch; `main` is the repository default ⇒ most likely production branch. **Dashboard confirmation required** (Settings → Git → Production Branch) |
| Build config | Repo-root **`vercel.json`** (the project’s dashboard build settings are explicitly superseded — Vercel warning observed): builds `api/index.py` with `@vercel/python`, `includeFiles: {app,webapp,assets,uploads}/**`, routes `/(.*)` → `/api/index.py`. No build command, no output directory (FastAPI serves the UI + API itself); root directory = repo root |
| Exclusions | `.vercelignore` keeps `.env*`, tests, scripts, tool sources, venv out of the bundle |
| Second project watching this repo | **`sellflow-backend`** (production `sellflow-backend.vercel.app`, currently **500 / broken**, last updated ~12 d ago): it also built `58cba9e` as a Preview. If its production branch is `main`, a merge would **production-deploy the current code into that legacy project too** |

## 5. Expected deployment behavior on merge (if `main` = production branch of `sellflow-site`)

- A Production build is triggered from the merge commit of `main` (≈25 s, as measured).
- The **rotated Production secrets apply** (Production-scope variables are injected into any new
  production deployment — §8).
- Surface served: `/` marketing site + PWA (manifest, service worker, offline page), `/app/`
  seller console, `/api/v1/*` API, `/health` 200. `/ready` returns **503 until `DATABASE_URL`
  is configured**; login is impossible without a database (§7). `/uploads/*` serves from the
  function filesystem (ephemeral — uploads need the R2 variables, §9).
- Preview protection does **not** apply to Production (verified public).
- Side effect to control first: the legacy `sellflow-backend` project (§4) and any Render link (§11).

## 6. Why Production has no `DATABASE_URL` (exact reason, verified)

Production-scope environment variables are exactly `SECRET_KEY` + `DEVICE_TOKEN_SECRET` (created
Oct 31). The project’s only database integration (Neon resource `sellflow-staging-db`) is connected
to the **preview** environment only (verified via `vercel integration resource inspect`), and no
production database was ever provisioned. Conclusion: production has deliberately run in
“shell mode” (marketing/console surface, no database); the absence is a **pending owner decision**,
not a misconfiguration. `/ready` on the live deployment returns 503 accordingly.

## 7. Production database architecture (documentation only — nothing created)

1. **Dedicated database**: provision a separate Postgres (e.g., a new Neon resource
   `sellflow-production-db`) and connect it to the **Production environment only**. Never attach
   the staging resource to Production and never point Testing at either.
2. **Connection**: pooled `DATABASE_URL` (`postgresql+psycopg://…` or plain `postgresql://` — the
   engine normalises schemes and disables prepared statements for poolers, already shipped).
3. **Migrations**: run `alembic upgrade head` **explicitly** (trusted machine or CI) before the
   first functional deploy; release head is `20261031004`; downgrade/re-upgrade verified on test
   databases. Vercel deploys do not migrate.
4. **Backups**: Neon PITR (paid) or scheduled `pg_dump` + restore drill (free-tier procedure was
   executed and verified in `STAGING_DEPLOYMENT_REPORT.md`); take a dump immediately after the
   first migration run.
5. **Separation**: production credentials only in Production scope; preview keeps the staging
   database; tests only ever touch `*_test` databases.

## 8. Rotated Production secrets — availability

`SECRET_KEY` and `DEVICE_TOKEN_SECRET` exist in the Production scope as non-readable Secrets (both
overridden with fresh, independent 64-char values in the prior pass; CLI confirmed). **Any new
Production deployment receives them** — including the proposed promotion. Verification limits,
stated honestly: the values cannot be read back, so activation is evidenced by “new production
deployment created after the rotation” plus `/health` boot, not by value inspection. A **Preview**
deployment would receive the *preview* secrets instead — the promotion must go through the
Production target (git merge into the production branch, or an explicit `--prod` deploy).

## 9. Missing Production variables (names only — values never needed here)

| Variable | Status | Impact if absent |
| --- | --- | --- |
| `DATABASE_URL` | **missing** | `/ready` 503; no login/API data |
| `APP_ENV` | missing | runs in development-mode validation (loose) — recommend `production` |
| `APP_DEBUG` | missing | recommend `false` (required off when `APP_ENV=production`) |
| `CORS_ORIGINS` | missing | defaults to localhost list — same-origin console unaffected; set for other clients |
| `REGISTRATION_INVITE_CODE` | missing | open registration (reachable publicly in production) |
| `STORAGE_BACKEND` + `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_S3_BUCKET` / `AWS_S3_ENDPOINT` / `AWS_REGION` + `STORAGE_PUBLIC_BASE_URL` | missing | product-image uploads answer 502 on serverless (fail-safe, no partial records) |
| `SECRET_KEY`, `DEVICE_TOKEN_SECRET` | **present (rotated)** | — |

## 10. Rollback strategy

| Layer | Procedure |
| --- | --- |
| Deployment | Vercel **instant rollback**: promote the previous production deployment `6n3e46oa5` (`dpl_AcJgc689tUyB…`) from the dashboard, or `vercel rollback`/`vercel promote` via CLI. Sub-minute, no rebuild |
| Environment | Secret rotation **persists** through a rollback (env is not versioned with deployments) |
| Database | Deploys run no migrations; if migrations were applied and must be reverted, restore the pre-release dump (documented drill) |
| Impact on today’s live console | The current production build is the **old console-only surface** (root → `/app/` redirect). After promotion, `/` serves the marketing site and the console stays at the same `/app/` URL. A rollback restores the old behavior instantly |

## 11. Outstanding risks

1. **Production-branch setting unverified** (dashboard-only read) — the single conditional that
   decides whether the merge auto-deploys Production for `sellflow-site`.
2. **Legacy `sellflow-backend` project** watches the repo (previews on every push; its production
   is currently broken). If `main` is its production branch, the merge deploys the current code
   there too — confirm its branch setting or disconnect it from the repo first.
3. **Render status UNKNOWN** (no CLI/API access; a 404/no-response is not proof of deletion). Note
   the release **deletes `render.yaml`** — if a blueprint-linked service still exists, its next
   build would treat the blueprint differently. Owner dashboard check remains required.
4. **No production database** ⇒ a promoted deployment is bootable but not functional (`/ready` 503,
   no auth) until `DATABASE_URL` is set (owner decision, §7).
5. **Uploads** need the R2 variables for durability (§9); otherwise 502 with a clear message.
6. The leaked `.env.production` remains in git **history** (values dead in Vercel; Render link
   unknown) — history purge still an optional, approval-gated cleanup.

## 12. Pre-flight checklist (owner, before merging)

1. **Vercel dashboard → `sellflow-site` → Settings → Git → Production Branch** — confirm it is
   `main` (or note the actual branch and target that branch instead).
2. **Vercel dashboard → `sellflow-backend` → Settings → Git** — confirm its production branch; if
   it is `main` and the project is obsolete, disconnect it from the repository (or accept that it
   will also receive the release).
3. **Set the production `DATABASE_URL`** (dedicated database, §7) — otherwise the promoted site
   boots but `/ready` stays 503.
4. *(Recommended)* Add `APP_ENV=production`, `APP_DEBUG=false`, `REGISTRATION_INVITE_CODE`, and the
   R2/`STORAGE_*` variables for a fully functional launch; check the Render dashboard once (risk 3).

**After an authorized merge:** verify the new Production deployment id/target, `/health` 200,
`/ready` 200 (with DB), login + one order/product round-trip on a disposable account, then re-run
the two verification suites (41 security + 161 full) against an isolated `_test` database.

---

*Compliance note: this pass produced evidence only. No push to `main`, no merge/PR merge, no
production deployment, no Production environment changes, no database creation, no history
rewrite, no force-push, no Render action. Secrets never printed; values referenced only by name.*
