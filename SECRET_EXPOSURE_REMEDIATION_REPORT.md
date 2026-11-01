# Secret Exposure Remediation Report

**Version 2 — 2026-11-01 (autonomous security/release pass)** · Branch `feature/premium-web-ui`
**Status: SECURITY GATE OPEN — production secrets ROTATED this pass; repository containment and
Render confirmation remain (owner-authorised actions only).** No secret values appear anywhere in
this report; SHA-256 prefixes are used for verification.

---

## 1. Current-state assessment (verified fresh, not inherited)

| Check | Evidence (2026-11-01) |
| --- | --- |
| Repo baseline | `feature/premium-web-ui` @ `9345e28`; worktree clean; `origin` reachable |
| `.env.production` at tips | **PRESENT** at `main` and `origin/main` (public default branch); **absent** at `origin/security/remove-env-production`, `feature/premium-web-ui`, `origin/master` |
| Containment branch | `origin/security/remove-env-production` = `origin/main` + 1 commit (`7171a42`): removes the file, hardens `.gitignore` (`.env`, `.env.*`, keeps `!.env.example`). Diff: 2 files, +6/−17. Ancestry verified; no other changes |
| Main movement | `origin/main` unchanged since 2026-10-20 (`b0862a1`) — the last production deployment (Oct 31 15:17) does **not** correlate with any main push |
| Production-deploy trigger | **Not provable from the CLI.** Default branch = `main`, git integration active (feature pushes → Preview builds, verified again). Safe assumption retained: a `main` push may deploy Production → main untouched |
| Repo security settings | Public; secret scanning **enabled**; push protection **enabled**; alerts: none |
| Env files ever committed (all refs) | only `.env.example` and `.env.production` |
| Source-tree scan (tracked files) | flags on docs/tests are placeholders; every `SECRET_KEY`-shaped value in `.env.example`, `README.md`, `QUICK-SETUP.md`, `PRODUCTION-CONFIG.md`, `DEPLOYMENT.md`, `tests/test_migration_security.py` fingerprints **differ** from the leaked key. The only match is the literal password `password` in placeholder URLs |
| CLI access | GitHub CLI: authenticated (`twosidegroup-spec`); Vercel CLI: authenticated (team `tsg-bfe6`); **Render CLI: not installed** |
| Deployment config | `vercel.json` (build/routes only, no secrets); `render.yaml` exists at `origin/main`/containment tip (no secret values; `SECRET_KEY`/`DATABASE_URL` are `sync: false`) |

## 2. Credential exposure — final attribution

- **Leaked material**: one 483-byte blob (unchanged since `cf0ce5c`, 2026-10-20) containing a
  40-char `SECRET_KEY` (fingerprint `1bad01689915`) and a `localhost` `DATABASE_URL`
  (fingerprint `24b98584b588`) whose password component fingerprints as `5e884898da28` —
  verified to equal `sha256("password")`, i.e. the project's own placeholder, **not a production
  credential**. No `DEVICE_TOKEN_SECRET` was ever in the file.
- **Environments that could have used the leaked SECRET_KEY**:
  - Render `sellflow-api` — **UNKNOWN/dormant**: the file is Render-formatted and `render.yaml`
    (Oct 20–21) declared those variables as manually set; the service now returns edge-404 for all
    paths. Cannot read its dashboard (no CLI access).
  - Vercel Production — previously UNKNOWN; **resolved by rotation this pass** (below).
  - Vercel Preview / local dev / Neon staging — fingerprints differ (or constructed fresh).
- **Database reuse**: no real reuse found. Local `.env`, Neon staging, and all docs differ from
  the leaked password; the leaked password only matches placeholder literals (`password`) in
  `.env.example`/`README.md`. No database was touched.

## 3. Remote operations completed this pass (production secrets rotated)

Executed with the authorised Vercel CLI (team keyring), values generated locally
(`secrets.token_urlsafe(48)`, 64 chars, distinct for each variable and **not reused from
Preview**), piped via stdin, never printed, never written to disk:

```
vercel env add SECRET_KEY          production --sensitive --force --non-interactive
vercel env add DEVICE_TOKEN_SECRET production --sensitive --force --non-interactive
```

- CLI confirmation (both): `Overrode SECRET_KEY / DEVICE_TOKEN_SECRET · Environments Production ·
  Type Secret`.
- Scope check after: Production still contains **exactly** `SECRET_KEY` and
  `DEVICE_TOKEN_SECRET` (no `DATABASE_URL`), both stored as non-readable secrets.
- **No deployment was triggered** by the rotation (deployment list unchanged; newest entry is a
  Preview from the prior pass).
- Note: `vercel env ls` keeps the original creation timestamp on `--force` overwrite; rotation
  evidence is the CLI `Overrode` confirmation above, not the timestamp.
- **Activation nuance**: the currently-running Production deployment predates the rotation, so its
  function snapshot still holds the old secrets until the next authorised production deploy. Its
  practical exposure is nil today — Production has no `DATABASE_URL` (login cannot succeed), and
  any forged token fails the DB user lookup. The next production deploy activates the fresh values.

Consequences (as designed): all Production JWTs would be invalidated at activation (none exist);
paired devices would need re-pairing (none exist).

## 4. Repository containment (prepared earlier, unchanged)

- `origin/security/remove-env-production` (`7171a42`) remains the no-history-rewrite containment:
  merging it into `main` removes the file from future clones **and triggers a production
  deployment** (why it is not merged here). Feature branch already excludes the file and ignores
  `.env*`; `SECRET_EXPOSURE` safety rules followed (no PR opened to avoid re-displaying a
  still-valid secret in a public diff at the time of creation).

**Coordinated history-cleanup plan (prepared, NOT executed — needs explicit authorisation):**

```bash
# after rotation is fully activated and a fresh backup of main exists
git clone --mirror https://github.com/twosidegroup-spec/sellflow-backend.git sf-mirror.git
cd sf-mirror.git
git filter-repo --path .env.production --invert-paths --force
git push --force   # rewrites public history — coordinate with all collaborators/forks
```

Rotation (done) is what neutralises the blob; the purge only removes it from clones.

## 5. Remaining risks

1. **Live default branch still ships `.env.production`** (values now dead in Vercel; Render
   unconfirmed). Anyone cloning `main` receives the historical values.
2. **Running Production deployment uses the pre-rotation snapshot** until a redeploy — near-zero
   practical impact (no DB), but not yet the rotated state.
3. **Render `sellflow-api`** — service unreachable; cannot confirm the account/dashboard is clean.
4. Historical clones/forks may retain the blob (accepted residual risk post-rotation).

## 6. Exact actions requiring the owner (one is mandatory next)

1. **Confirm/clean the Render account** (only remaining credential environment we cannot inspect):
   sign in at dashboard.render.com → if `sellflow-api` (or any service using an env var copied from
   `.env.production`) still exists: delete it or rotate its `SECRET_KEY`; if the account is empty,
   nothing to do.
2. **Contain the default branch** — when a production deployment is acceptable:
   `git push origin refs/heads/security/remove-env-production:refs/heads/main` (or open/merge the
   branch as a PR). This deploys Production **and** activates the rotated secrets — the intended
   combined step. *(Requires explicit authorisation; not done here.)*
3. Optional, post-rotation: run the history purge in §4 and re-check GitHub secret scanning.

## 7. Tests executed (isolated `sellflow_audit_test` only)

| Suite | Result |
| --- | --- |
| Security subset: `test_migration_security` + `test_auth_lifecycle` + `test_token_version_audit` + `test_migration_device_bridge` | **41 passed** |
| Full suite `pytest tests/ -q` | **161 passed** |

Source-code checks vs deployed checks are separated deliberately: all application verification is
source/local; the running Production service was only probed read-only (`/` → 200, pre-rotation
build) and the latest Preview remains behind Vercel Authentication (`Login - Vercel`).

## 8. Security gate status: **OPEN**

Closed when all of the following are true:

- [x] Production `SECRET_KEY` + `DEVICE_TOKEN_SECRET` rotated with fresh, independent values
      (done this pass; verified by CLI confirmation and scope check)
- [ ] Render account confirmed clean / service removed (owner dashboard action)
- [ ] Default-branch containment merged (or history purged) and the rotated secrets activated by
      the resulting production deploy (owner-authorised action)
- [ ] (Recommended) GitHub secret-scanning re-checked after the merge

Until then the repository remains a public distributor of dead credentials and one environment
(Render) is unverified — hence OPEN, not CLOSED.
