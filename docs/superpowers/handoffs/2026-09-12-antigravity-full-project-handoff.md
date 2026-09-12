# Handoff To Antigravity - Full vinhlong360 Project

> STATUS: active - authoritative technical handoff for the demo phase
> Handoff date: 2026-09-12
> Owner: NCTaam
> Mode: full technical ownership with guarded release and data authority

## 1. Mission

Antigravity is taking over the complete vinhlong360 codebase, not only the frontend. The target is a maintainable, testable and deployable system for the Vinh Long province tourism, local-product and community platform.

This handoff authorizes Antigravity to inspect and change tracked application code, tests, documentation, contracts and operational scripts through normal branches and review. It does not place passwords, private keys, database credentials or owner signatures in Git. Those items remain in the owner's offline or separately approved channel.

The VPS currently hosts a **demo**, not an official public release. Keep the demo noindex and preserve the public launch `NO_GO` decision until the owner changes the authority records.

## 2. Immutable baseline

| Item | Current value |
|---|---|
| Repository | `C:\\Users\\NCTaam\\Documents\\vinhlong360-correction-case-pilot` |
| Branch | `codex/correction-case-pilot` |
| HEAD | `873d39be50175474110e6e5e10fc5cfdc4fbe596` |
| Integrated frontend branch | `frontend/lead/foundation` (ancestor of HEAD) |
| Frontend lead handoff commit | `e2af0a7451583986174de12bfb9324cbc368c40d` |
| Authority check | `python scripts/check_release_authority.py --root .` -> `PASS tracked=8 stale=0 mismatches=0` |
| Demo build revision | `873d39be50175474110e6e5e10fc5cfdc4fbe596` |
| Demo bundle SHA-256 | `887a0e59439fce328d95c2252986a09bba2a6ba22e8bb13f400c6e8d3f3194a8` |

The tracked working tree is unchanged. The shared checkout also contains generated and untracked test/research artifacts. Do not delete, stage globally, stash globally or clean those artifacts without a separate owner instruction.

## 3. Architecture map

### 3.1 Backend: FastAPI modular monolith

Composition and cross-cutting controls:

- `agent/server.py` - application composition and runtime startup.
- `agent/public_api.py` - public HTTP surface.
- `agent/admin.py` and `agent/admin_common.py` - AdminCP composition and shared guards.
- `agent/database.py` - persistence composition and database helpers.
- `agent/auth_middleware.py`, `agent/identity/` and `agent/middleware.py` - authentication, authorization and request safety.
- `agent/config.py`, `agent/feature_flags.py`, `agent/launch_policy_api.py` - runtime configuration and release policy.
- `agent/control_plane/` - authority, evidence, lifecycle, concurrency, saga and snapshot controls.

Domain modules:

- `agent/entities/` - entity schemas, read/write paths and public/admin APIs.
- `agent/cases/` - correction-case domain, validation, lifecycle, audit, publication, outbox, rate limits and wiring.
- `agent/community/` - posts, social APIs and community contracts.
- `agent/identity/` - identity and account APIs.
- `agent/itineraries/` - itinerary generation, scheduling, optimization and multi-day allocation.
- `agent/reports/` - report models, repository and service.
- `agent/chat/` and `agent/llmops/` - chat and bounded LLM operations.
- `agent/notifications.py`, `agent/saved.py`, `agent/analytics.py`, `agent/metrics.py` - supporting platform capabilities.
- `agent/crawler.py`, `agent/pinned_http.py`, `agent/policy_http.py`, `agent/geocode.py` - bounded external HTTP and data acquisition.
- `agent/erasure.py`, `agent/privacy_boundary.py`, `agent/data_lifecycle.py` - privacy and lifecycle controls.

### 3.2 Frontend: one Nuxt 4 SSR application

- `web-nuxt/pages/` - route-level pages and page recipes.
- `web-nuxt/components/` - shared UI, admin and presentation components.
- `web-nuxt/composables/` - stateful client/server interaction units.
- `web-nuxt/utils/` - API transport, request deadlines, route and presentation helpers.
- `web-nuxt/server/` - Nitro middleware and internal readiness/SEO routes.
- `web-nuxt/types/` - shared TypeScript contracts.
- `web-nuxt/tests/` - Vitest architecture, accessibility, contract and smoke tests.
- `web-nuxt/nuxt.config.ts` - SSR, runtime config and API proxy route rules.

SSR requests to `/api/**` must use `web-nuxt/utils/apiFetch.ts`; direct server-side `$fetch` is not an accepted substitute because it can bypass the intended proxy behavior.

The old Astro and legacy HTML frontends are not part of the architecture and must not be restored.

### 3.3 Data and runtime

- PostgreSQL is the production source of truth for entities, relationships, itineraries, users and UGC.
- UGC and auth are PostgreSQL-only. SQLite is limited to the knowledge layer.
- `web/data.json` is an export/build input and may be divergent from production PostgreSQL. Never use it to overwrite production data without an explicit owner-approved, backed-up operation.
- Systemd services on the demo VPS: `vl-agent`, `vl-nuxt`, `vl-bot`, `postgres`, `nginx`.
- Live Nuxt output: `/opt/vinhlong360/web-nuxt/.output`.
- Frontend deployment is an immutable tarball swap with a retained rollback output.

### 3.4 Contracts, quality and operations

- API contract: `contracts/frontend-endpoints.json` and `docs/api-contract.md`.
- Project constitution: `CLAUDE.md`.
- Current release authority: `config/release-authority.json`.
- Decision index: `config/decision-records.json`.
- Quality standards: `docs/standards/00-INDEX.md`.
- Deployment reference: `docs/deployment-guide.md` and `docs/HANDOFF.md`.
- Launch rollback runbook: `docs/runbooks/launch-safety-rollback.md`.
- Hard quality gate: `scripts/checks/run_hard.py`.
- Backend regression runner: `scripts/ops/run_backend_regression.py`.
- Closed-release and evidence tooling: `scripts/ops/verify_closed_release.py`, `scripts/ops/verify_release_bundle.py`, `scripts/ops/run_pilot_acceptance.py`.

## 4. Current demo deployment

The demo site is live at [https://vinhlong360.vn/](https://vinhlong360.vn/). It is not an official launch.

Verified after deployment:

- `vl-nuxt` is active.
- Local `http://127.0.0.1:3000/` returns `200`.
- Local `http://127.0.0.1:3000/api/homepage` returns `200`.
- Public homepage and `/api/homepage` return `200`.
- Homepage sends `X-Robots-Tag: noindex, follow`.
- Live DOM contains the new homepage recipe, hero content and schema graph markers.
- Direct comparison of the uploaded bundle with the deployed `.output` returned `diff_count=0`.

Rollback artifact retained on the VPS:

```text
/opt/vinhlong360/backups/nuxt-demo-pre-20260912T045546Z.tar.gz
```

The VPS has a legacy TLS configuration that can intermittently produce `dh key too small` for strict OpenSSL clients. This was not changed as part of the frontend demo swap. Do not use a TLS compatibility probe as evidence that the application is broken; verify both local service endpoints and browser/public behavior.

## 5. Ownership and authority matrix

| Area | Antigravity may do | Owner approval still required |
|---|---|---|
| Tracked code, tests and docs | Modify on a dedicated branch/worktree | Merge to the release branch when risk is material |
| Frontend demo artifact | Build, package and prepare a swap | Approve each demo deployment window |
| Backend implementation | Refactor and extend through tests and API contracts | Changes affecting data, auth, migrations or release policy |
| PostgreSQL/data | Read documented contracts and use disposable test databases | Any production migration, import, replacement, deletion or restore |
| Secrets | Use variable names and redacted examples | Setting, rotating or viewing real values |
| VPS access | Use a restricted deploy identity or owner-run CI | Root access, system-wide changes and production service changes |
| Release authority | Produce evidence and reports | Signatures, countersignatures, legal decisions and public indexing |

No password, private key, DSN, owner signing key, countersignature key or CI secret belongs in this file or any commit. The owner supplies an approved access channel separately when necessary.

## 6. Non-negotiable project rules

1. Read `CLAUDE.md` before making changes; it overrides older documents.
2. Preserve PostgreSQL as the source of truth and back up before data operations.
3. Keep UGC/auth PostgreSQL-only.
4. Use additive-first changes and small commits with focused verification.
5. Do not run `database.py --replace`, `deploy.sh --replace`, `/reload` or destructive admin data actions without explicit owner direction and a backup.
6. Do not re-host copyrighted text or images. Images follow the project's AI-generated-only policy and must retain disclosure labels when illustrative.
7. Keep the site noindex during demo and do not change `public_launch_verdict` without owner decisions.
8. Do not use global stash, reset, checkout, clean or `add -A` in the shared worktree.
9. Do not claim a test, deployment or release is complete without fresh command output and an evidence path.
10. Do not treat historical snapshots in `docs/HANDOFF.md` or `docs/ROADMAP.md` as current facts without checking the current branch and authority files.

## 7. Required first session for Antigravity

Run these read-only checks first:

```powershell
git status --short --branch
git rev-parse HEAD
git branch --show-current
python scripts/check_release_authority.py --root .
```

Then read:

```text
CLAUDE.md
docs/README.md
docs/architecture-decisions.md
docs/standards/00-INDEX.md
config/release-authority.json
config/decision-records.json
this handoff file
```

For a code change, create a dedicated branch/worktree, write or update the focused test first, run the smallest relevant test, implement one change, run the full affected gate and report the commit plus evidence. Do not start by cleaning the shared checkout.

## 8. Acceptance gates before any release claim

Run the gates appropriate to the change; do not substitute a partial gate for a full one:

```powershell
python scripts/checks/run_hard.py --all
python -m pytest tests/launch_safety/ -m "" -n0
Set-Location web-nuxt
npm run typecheck
npx vitest run
npm run build
```

For the backend baseline, follow the temporary-root requirement in `CLAUDE.md` and use `scripts/ops/run_backend_regression.py` for the documented full runner. A narrow suite is evidence only for the narrow scope.

For a demo frontend deployment, verify all of the following after the swap:

```text
systemctl is-active vl-nuxt
http://127.0.0.1:3000/
http://127.0.0.1:3000/api/homepage
https://vinhlong360.vn/
https://vinhlong360.vn/api/homepage
X-Robots-Tag: noindex, follow
launch-readiness-manifest.json build_revision matches the admitted commit
```

## 9. Release status that must remain visible

`config/decision-records.json` currently has six `unsigned` records. `config/release-authority.json` currently declares:

- closed pilot: `GO_CONDITIONAL`
- public launch: `NO_GO`
- required decision items: legal, provider, residency and public indexing

This is compatible with a controlled demo and is not permission to present the site as an official release.

## 10. Copy/paste continuation prompt for Antigravity

```text
You are taking full technical ownership of the vinhlong360 repository for the demo phase. Start by reading CLAUDE.md, docs/README.md, docs/architecture-decisions.md, docs/standards/00-INDEX.md, config/release-authority.json, config/decision-records.json, and docs/superpowers/handoffs/2026-09-12-antigravity-full-project-handoff.md.

Current baseline: branch codex/correction-case-pilot, HEAD 873d39be50175474110e6e5e10fc5cfdc4fbe596. The Nuxt frontend foundation is already integrated. The demo VPS is serving the frontend build with this same revision and remains noindex.

You own implementation across frontend, backend, tests, contracts, docs and operational scripts. Work in a dedicated branch/worktree, keep commits small, test before refactoring, and report exact evidence. Preserve PostgreSQL as the production source of truth; UGC/auth is PostgreSQL-only. Use web-nuxt/utils/apiFetch.ts for SSR API requests.

Do not put passwords, DSNs, API keys, owner keys, countersignatures or production .env values in Git or chat. Do not run destructive data commands, production migrations, public indexing changes or public-release actions without explicit owner approval. Do not clean or stash the shared worktree globally. Preserve generated/untracked artifacts unless the owner gives a precise cleanup scope.

Before the first implementation task, report: current Git status, current branch/HEAD, authority-check output, the affected modules, the focused test command and the rollback plan. At the end of every task report changed paths, commit id, command output, known gaps and whether the result is demo-only or release-eligible.
```

## 11. Handoff completion condition

The handoff is technically complete when Antigravity acknowledges this file, reproduces the baseline checks, creates its own work branch/worktree and returns a first evidence-backed task plan. It is not complete merely because an agent has access to the repository or because the demo homepage is reachable.
