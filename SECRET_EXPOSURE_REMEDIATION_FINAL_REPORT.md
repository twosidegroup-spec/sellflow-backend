# Secret Exposure Remediation — FINAL Report

**2026-11-01 · Branch `feature/premium-web-ui` @ `4c2fd93` (report commit follows)**
**SECURITY GATE: OPEN** — one owner decision boundary reached (Phase 4), with a material new
finding that makes the previously planned promotion unsafe as intended. No secret values appear
anywhere in this report; SHA-256 prefixes only.

Labels: **VERIFIED** = direct evidence this pass · **REPORTED** = prior claim, re-checked where
possible · **BLOCKED** = access/approval boundary · **NOT DONE** = not executed.

---

## 1. Repository and commit evidence — VERIFIED

| Item | Evidence |
| --- | --- |
| Canonical remote | `https://github.com/twosidegroup-spec/sellflow-backend.git` (fetch+push) |
| Branch / HEAD / tree | `feature/premium-web-ui`, HEAD `4c2fd93`, worktree clean |
| `origin/main` | `b0862a1` — unchanged since 2026-10-20 |
| Containment | `origin/security/remove-env-production` = `7171a42` = `origin/main` **+ exactly 1 commit**; `git merge-base --is-ancestor origin/main <branch>` → true (fast-forward lineage, no commits overwritten by a promotion) |
| Containment tree diff | `D .env.production`, `M .gitignore` — **nothing else** (no app source, migrations, deps or config touched). `.gitignore` adds `.env`, `.env.*`, `!.env.example` |
| `.env.production` at tips | PRESENT at `origin/main`; absent at containment, feature, `origin/master` |
| Tags / forks | No tags; **0 forks**; default branch `main`; public; secret scanning + push protection enabled; no branch protection on `main` |
| Blob history scope | The leaked blob is in the history of `origin/main`, `origin/feature/premium-web-ui` and `origin/security/remove-env-production`; **not** in `origin/master` |

## 2. The decisive deployment-consequence finding — VERIFIED

`origin/main` is **not** the codebase that is live. It is a backend-only, pre-console tree:

- `main:vercel.json` builds `app/main.py` with the old `@vercel/python` style and routes everything
  to it; there is **no `api/index.py`, no `webapp/` console, no `assets/`, no marketing site**.
- The string “Operations Console” used by the live site exists **only on the feature branch** —
  so today’s production deployment did not come from `main`.

**Therefore `git push origin refs/heads/security/remove-env-production:refs/heads/main` would —
if `main` is the Vercel production branch — replace the live console-shell site with the old
backend-only build.** That is an unintended, unrelated production regression. It would also push a
tree that still contains `render.yaml`, which (if the dormant Render GitHub link exists) could
trigger a failed Render build attempting `alembic upgrade head` against a database that likely no
longer exists. A fresh Vercel production deployment of the promoted commit would additionally
**fail `/ready`** (see §7). Phase 3\'s safety gate is therefore **not met for this promotion as
previously planned**.

## 3. Render verification — BLOCKED (owner dashboard required)

- Render CLI: **not installed**; no Render API token in this environment.
- `sellflow-backend-0nyn.onrender.com/health`: this pass returned **no response** (previous pass:
  edge 404). Service state is **UNKNOWN** — 404/timeout does not prove deletion and I do not claim
  the account is clean.
- The leaked file is Render-formatted and `render.yaml` (Oct 20–21) declared
  `SECRET_KEY`/`DATABASE_URL` as manually set — **ownership assumption**: if the service still
  exists, its `SECRET_KEY` may be the leaked one.
- **Owner action:** sign in to dashboard.render.com and confirm whether `sellflow-api` (or any
  service whose env was copied from `.env.production`) still exists; delete or rotate it.

## 4. Vercel configuration status — VERIFIED (scope), fingerprints only

| Item | Status |
| --- | --- |
| Linkage | project `prj_y99ZUQfX…`, team `team_enJge1c…` (`sellflow-site`) |
| Production env | exactly two secrets: `SECRET_KEY`, `DEVICE_TOKEN_SECRET` (stored as non-readable Secrets); **no `DATABASE_URL`** |
| Rotation | Performed in the previous pass via CLI (`vercel env add … production --sensitive --force`; CLI confirmed `Overrode … Type Secret` for both). Re-verified today: both exist, scope unchanged, values unreadable |
| Preview credentials | Separate scope (Neon `DATABASE_URL` + distinct 64-char secrets generated in this session’s earlier work) — production does not consume them |
| Leaked-value fingerprints (for comparison) | `SECRET_KEY` = `1bad01689915` (40 chars) · `DATABASE_URL` = `24b98584b588` · DB password = `5e884898da28` (literally the placeholder word “password”) |

## 5. Production deployment state — VERIFIED; activation NOT DONE

- Current (and only live) production deployment: `sellflow-site-6n3e46oa5-tsg-bfe6.vercel.app`,
  id `dpl_AcJgc689tUyBduehTJ2VDC6UkRPy`, created **Oct 31 15:17** — **predates the secret
  rotation**, so the running build still carries the pre-rotation env snapshot.
- **No production deployment has occurred since the rotation** (deployment list verified).
- **Activation = NOT DONE** and cannot be honestly claimed with the current plan (§2/§6).

## 6. Why the planned promotion was stopped (Phase 4 boundary)

The mission requires all six completion criteria for CLOSED. Independently sufficient blockers:

1. **Unsafe deployment consequence** (§2): promoting the containment commit alone deploys the old
   backend-only code to production — an unintended regression, and `main` pushes may also touch
   Render. “Never trigger an unrelated Production deployment” applies.
2. **Criterion 4 is unsatisfiable today**: production has **no `DATABASE_URL`**, so `/ready`
   returns **503** and no authentication path can pass (§7). Even the intended deploy would leave
   the gate OPEN while regressing the live surface.
3. **Authorization**: the prior report explicitly marked this production promotion as requiring
   explicit owner authorization; that authorization has not been given for a deploy whose
   consequence is now known to be a surface replacement.
4. **Render** (§3) remains an access-boundary item.

**Recommended owner path (replaces the bare promotion command):** promote the **current release**
when the owner is ready to publish the product — i.e., open/merge a PR `feature/premium-web-ui` →
`main`. That single, intentional release (a) removes `.env.production` from the default branch,
(b) deploys the current product — not the old backend-only tree, (c) activates the rotated
Production secrets, and (d) avoids the Render auto-deploy side effect only if the Render link is
first confirmed/removed (§3). A production database decision (§7) should accompany it if login
must work at launch. **This requires explicit owner approval; nothing was pushed to `main`.**

## 7. Health and critical-path results — VERIFIED (read-only)

| Target | Result |
| --- | --- |
| Production `/health` | **200** `{"status":"ok"}` |
| Production `/ready` | **503** — no `DATABASE_URL` configured; readiness cannot pass (criterion-4 blocker) |
| Production `/api/v1/info` | 200 (old API version string) |
| Production JWT/device/auth paths | **Not testable** — no database in production; login cannot succeed (pre-existing condition, by design) |
| Preview | behind Vercel Authentication (`Login - Vercel`) — no anonymous verification |
| Local/staging (isolated) | full suite green (§8); earlier staging runs verified `/ready` 200 with the Neon staging DB |

## 8. Tests executed this pass (isolated `sellflow_audit_test` only)

```powershell
$env:DATABASE_URL="<…>/sellflow_audit_test"; $env:SELLFLOW_ALLOW_DESTRUCTIVE_TESTS="1"; $env:APP_DEBUG="false"
python -m pytest tests/test_migration_security.py tests/test_auth_lifecycle.py tests/test_token_version_audit.py tests/test_migration_device_bridge.py -q
# 41 passed
python -m pytest tests/ -q
# 161 passed
```

Covers configuration fail-closed, CORS, rate-limit, JWT lifecycle + token-version revocation,
device-token authentication, tenant isolation, storage, and the full application suite.
No failures. No destructive test touched any non-`_test` database.

## 9. Git history cleanup — NOT DONE (approval-gated); plan prepared

- **Affected refs**: `origin/main`, `origin/feature/premium-web-ui`, `origin/security/remove-env-production`
  (all carry the blob in history). `origin/master` is clean. **0 forks**; unknown number of clones.
- **Plan** (do not execute without explicit approval): mirror-clone → `git filter-repo --path
  .env.production --invert-paths --force` → coordinated force-push of the three refs → contributors
  re-clone; deployment integrations re-link if needed; GitHub caches/support may retain the blob;
  keep a secure offline recovery bundle before rewriting.
- **Residual-risk position (recommended)**: the leaked `SECRET_KEY` is **dead in Vercel**
  (rotated; production promoted builds will use the new value) and the leaked DB URL was a
  localhost placeholder (“password”). With 0 forks, the practical value of rewriting the **active**
  feature branch’s entire public history is low versus the disruption. Recommended: accept the
  historical blob as a documented residual risk after the Render check, revisit only if the owner
  requires zero-blob presence. This requires the owner’s explicit sign-off to count as criterion 6.

## 10. Remaining owner actions (exact)

| # | Action | Why |
| --- | --- | --- |
| 1 | **Render dashboard**: confirm whether `sellflow-api` (or any service env copied from `.env.production`) exists; delete or rotate `SECRET_KEY` there | Only unverified credential environment (BLOCKED here) |
| 2 | **Approve the recommended release promotion** (`feature/premium-web-ui` → `main` via PR) at a time the production deploy is acceptable — or explicitly approve/deny the legacy containment-only push and the Render-link cleanup | Phase-4 authorization; the bare containment push regresses the live surface (§2) |
| 3 | Decide the **production database** question (set `DATABASE_URL` for production when the product should actually run) | Without it `/ready` stays 503 and auth cannot pass (criterion 4) |
| 4 | Optional sign-off on the **residual-risk decision** for the historical blob (vs. the coordinated history purge, plan in §9) | Closes completion criterion 6 |

## 11. Completion-criteria scorecard

| Criterion | Status | Note |
| --- | --- | --- |
| 1. Render verified clean / remediated | **BLOCKED** | Dashboard access required |
| 2. `.env.production` absent from default branch | **NOT DONE** | Removal prepared (`7171a42`); safe promotion awaits owner decision (§2/§6) |
| 3. Rotated secrets activated by verified deployment | **NOT DONE** | No deployment since rotation; activation path corrected in §6 |
| 4. Production health + critical auth pass | **BLOCKED** | `/health` 200 ✓ but `/ready` 503 (no production DB); auth untestable |
| 5. Security + full suites pass | **VERIFIED** | 41 + 161 passed |
| 6. Historical exposure purged or documented residual risk | **PARTIAL** | Purge NOT DONE (approval-gated); documented justified position in §9 awaiting owner sign-off |

**SECURITY GATE: OPEN** — exact blockers: (1) Render confirmation, (2) owner decision on the safe
promotion path, (3) production database decision, (4) residual-risk sign-off. All safe, reversible
work required for closure has been completed or prepared; nothing was deployed, no credentials
were exposed, and no history was rewritten.
