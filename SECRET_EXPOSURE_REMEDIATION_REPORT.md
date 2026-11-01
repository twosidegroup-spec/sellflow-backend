# Secret Exposure Remediation Report — `.env.production`

**Investigated:** 2026-11-01 · **Branch:** `feature/premium-web-ui` @ `44ede4d` (+ this report)
**Status: SECURITY GATE REMAINS OPEN** — rotation is owner action (production env must not be
modified here) and the live default-branch copy can only be merged away with a deploy. No secret
values appear in this file; fingerprints (SHA-256 prefixes) are used for verification.

## 1. What the evidence confirms (FACT)

| Fact | Detail |
| --- | --- |
| File and commits | `.env.production` added in **`cf0ce5c` (2026-10-20)** (“Fix CORS for localhost connections”); removed from the **feature branch** in **`dbcbdcf` (2026-10-31)** |
| Blob identity | A single 483-byte blob, unchanged across every revision (`cf0ce5c`, `dbcbdcf^`, `main`, `origin/main` all fingerprint identically) |
| Keys in the file | `APP_ENV`, `APP_DEBUG`, `HOST`, `PORT`, `SECRET_KEY` (len 40), `DATABASE_URL` (len 58). **No `DEVICE_TOKEN_SECRET`** |
| **LIVE on the default branch** | `git cat-file -e main:.env.production` and `origin/main:.env.production` (and `main`, `migration/system-a-integration`, `backup/…`, `checkpoint/…` locally) → **present at tip**. New clones still receive the file; the exposure is **ongoing**, not historical |
| Repository | `twosidegroup-spec/sellflow-backend` is **PUBLIC**; secret scanning **enabled**, push protection **enabled**, alerts: none (custom pattern not flagged) |
| Signed-off window | Exposure began with the first push containing `cf0ce5c` (2026-10-20, public) and continues **on `origin/main` at this moment** |
| Leaked DB credential is placeholder-grade | The `DATABASE_URL` password component fingerprint equals `sha256("password")` (len 8); host was `localhost`. It is the project’s own default literal, not a production credential |
| Other env files ever committed | Only `.env.example` (placeholders — fingerprints differ). No other env/secret/pem/key file in any history path |
| Benign history matches | `sellflow_app/lib/core/config/env.dart` (public Render API base URL only), `device_tokens.py`, alembic `env.py`, `tokens.css`, token-version migration/tests — all contain no secrets |
| Render era | `render.yaml` (2026-10-20 → deleted 2026-10-21) declared service `sellflow-api` with `SECRET_KEY`/`DATABASE_URL` as `sync: false` (set manually in the dashboard) — exactly what the Render-formatted `.env.production` is for. The old Flutter app pointed at `sellflow-backend-0nyn.onrender.com`, which now answers **edge HTTP 404** for `/` and `/health` → the service appears **deleted/suspended** |

### Application usage of each secret (FACT — code inspection)

| Secret | Used by | Rotation effect |
| --- | --- | --- |
| `SECRET_KEY` | `app/core/security.py` only — HS256 signing/verification of 24-hour access JWTs; enforced through `auth/dependencies.py` and `devices/bridge_dependencies.py`. Front-ends contain no secret usage. | **All issued JWTs become invalid → every session signs out.** The token-version revocation channel (`ver` claim vs `users.token_version`) continues to work unchanged; new logins are unaffected. |
| `DEVICE_TOKEN_SECRET` | `app/core/device_tokens.py` — HMAC-SHA256 key for pairing codes and device tokens (`bridge_service`). Production refuses to start without it; dev uses a per-process random fallback. | **All paired bridge devices fail verification and must re-pair** (stored hashes become stale; no schema change, no data loss). |
| `DATABASE_URL` | `app/db/engine.py` (normalised scheme) and `alembic/env.py`. | Connectivity only — no token/session semantics. |

## 2. Environment attribution (fingerprint comparison; values never printed)

| Candidate | `SECRET_KEY` vs leaked | `DATABASE_URL` / DB password vs leaked |
| --- | --- | --- |
| Local dev `backend/.env` | **DIFFER** (len 41) | **DIFFER** / password **DIFFER** |
| `backend/.env.production` (on-disk copy) | **MATCH** (this is the leaked file) | **MATCH** (localhost, password “password”) |
| `.env.example`, `DEPLOYMENT.md`, `PRODUCTION-CONFIG.md`, `QUICK-SETUP.md`, `README.md` | DIFFER (placeholders) | DIFFER; password “password” only where the placeholder literal is shown |
| **Vercel Preview** (`DATABASE_URL` = Neon staging) | UNKNOWN by value (stored non-readable) — but generated fresh in this session with `token_urlsafe(48)` (len 64 vs leaked 40) → **cannot match** | **DIFFER** (Neon credential; password **DIFFER**) |
| **Vercel Production** | **UNKNOWN** — stored `[SENSITIVE]`, not readable via CLI | No `DATABASE_URL` in Production at all |
| Render `sellflow-api` | **UNKNOWN** (dashboard values unreadable; service appears gone) | UNKNOWN (manually set; the leaked localhost URL could never have worked there) |
| `.database_notes.txt` | file does not exist | — |

## 3. Assumptions

- **A1.** The Render service `sellflow-api` was configured with the leaked `SECRET_KEY` (the file is
  Render-formatted, was pushed the same day as the Render setup commits, and `sync: false` means the
  values came from outside `render.yaml`). Circumstantial, not proven.
- **A2.** Any clone/fork made while the file sat in the public default branch may retain the blob,
  even if the repository later removes or purges it.
- **A3.** The Vercel secrets set ~10 h before this investigation were freshly generated (project
  practice: values were generated for the Vercel deployment); this is not fingerprint-provable.

## 4. Unknowns (cannot be resolved from here)

- Whether Vercel **Production** `SECRET_KEY`/`DEVICE_TOKEN_SECRET` equal the leaked value (stored
  `[SENSITIVE]`; no read path).
- Whether the Render dashboard still holds the service or its environment values.
- Whether any third party cloned or scraped the repository during the exposure window.

## 5. Containment performed in this investigation (FACT)

- **Prepared and pushed** branch **`origin/security/remove-env-production`** (`7171a42`, based on
  `origin/main`): removes `.env.production` from the tree and hardens `.gitignore`
  (`.env`, `.env.*`, keeps `!.env.example`). Diff: `2 files changed, 6 insertions(+), 17 deletions(-)`;
  verified `.env.production` is **absent at the branch tip**.
- **Deliberately NOT merged into `main` and no PR opened**: the repository default branch is `main`
  with an active Vercel git integration — a push would deploy to production, which this task
  forbids; a PR would also re-display the secret in a public diff while it is still valid.
- The on-disk `.env.production` on this machine has been left in place (it is the leaked artifact;
  the application never loads it — `env_file=".env"`).

## 6. Rotations required (owner actions — NOT performed here)

| # | Credential | Environment | Why | Effect |
| --- | --- | --- | --- | --- |
| 1 | `SECRET_KEY` | **Vercel Production** (team `tsg-bfe6`, project `sellflow-site`) | Value non-readable → assume the publicly exposed one may have been used | All production JWTs invalidated; no live sessions exist today |
| 2 | `DEVICE_TOKEN_SECRET` | **Vercel Production** | Same reasoning; protects pairing codes/device tokens | Any paired production device must re-pair (none expected today) |
| 3 | `SECRET_KEY` (+ service itself) | **Render** account, service `sellflow-api` | Leaked file was Render-formatted; service now 404s but the account may persist | Delete the service or rotate; service is unreachable today |
| 4 | DB password **“password”** | any reachable PostgreSQL actually using the literal `password` | Trivially guessable default, independent of the leak | Change password; update that environment’s `DATABASE_URL` |
| — | Vercel Preview values | not required | Fingerprinted/constructed as fresh (Neon credential; 64-char secrets generated this session) | — |

Commands (run by the owner; values are generated locally and never echoed):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"   # generate, paste when prompted
vercel env rm SECRET_KEY production --yes --scope tsg-bfe6
vercel env add SECRET_KEY production --sensitive --scope tsg-bfe6
vercel env rm DEVICE_TOKEN_SECRET production --yes --scope tsg-bfe6
vercel env add DEVICE_TOKEN_SECRET production --sensitive --scope tsg-bfe6
# Production env changes apply at the next production deploy (none needed until launch).
```

**Verification after rotation** — confirm the new values do **not** fingerprint as the leaked ones
(safe to compute; never paste values into chat or files):

```powershell
python -c "import hashlib,getpass; v=getpass.getpass('new value: '); print('fingerprint:', hashlib.sha256(v.encode()).hexdigest()[:12])"
```

Leaked fingerprints for comparison: `SECRET_KEY` = `1bad01689915` (len 40) ·
`DATABASE_URL` = `24b98584b588` (len 58) · DB password = `5e884898da28` (len 8,
i.e. the literal “password”).

## 7. Remaining Git actions

1. After rotation, **merge `security/remove-env-production` into `main`** at a moment the resulting
   production deploy is acceptable (the merge is the deploy trigger), **or** purge the blob from
   history (`git filter-repo --path .env.production --invert-paths` on a coordinated clone +
   force-push) — purging removes it from clones entirely; the merge only fixes future trees.
   Rotation is what neutralises the blob either way.
2. Re-check GitHub secret-scanning after the merge (dashboard), and treat A2 (existing clones) as
   accepted residual risk once values are rotated.

## 8. Test results (executed against the isolated `sellflow_audit_test` database)

| Suite | Result |
| --- | --- |
| `tests/test_migration_security.py` + `test_auth_lifecycle.py` + `test_token_version_audit.py` + `test_migration_device_bridge.py` | **41 passed** (config fail-closed, CORS, rate limits, detect guards, JWT lifecycle, token-version revocation, device-token auth) |
| Full suite `pytest tests/ -q` | **161 passed** |

## 9. Gate status

**OPEN** — until (a) Production `SECRET_KEY`/`DEVICE_TOKEN_SECRET` are rotated (owner), (b) the
Render account is confirmed clean (owner), and (c) the default-branch copy is merged away or the
history purged (owner, post-rotation). Nothing else in the codebase is blocked: all application
security controls (tenant isolation, token-version revocation, device HMAC, rate limits) were
re-verified green.
