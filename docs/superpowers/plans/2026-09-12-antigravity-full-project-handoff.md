# Antigravity Full Project Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> STATUS: active - handoff package is being prepared for owner review

**Goal:** Produce a complete, truthful handoff package that lets Antigravity take over the vinhlong360 codebase and demo operations without exposing secrets or confusing demo status with public release authority.

**Architecture:** Treat the repository as one Nuxt 4 frontend plus a FastAPI modular monolith. PostgreSQL remains the source of truth for production entities and UGC; the frontend is deployed as an immutable `.output` artifact; release authority, data mutation, credentials and public indexing remain explicit control boundaries.

**Tech Stack:** Python/FastAPI, PostgreSQL, Nuxt 4 SSR, Vue/TypeScript, Vitest, pytest, systemd, Nginx, tarball deployment.

## Global Constraints

- Use `codex/correction-case-pilot` at commit `873d39be50175474110e6e5e10fc5cfdc4fbe596` as the current integrated baseline.
- `frontend/lead/foundation` is already integrated; do not resurrect `web-astro/` or legacy `web/` frontends.
- PostgreSQL is the production source of truth; do not replace it from stale `web/data.json`.
- UGC/auth is PostgreSQL-only; SQLite is for the knowledge layer only.
- Do not place passwords, DSNs, API keys, owner keys or countersignatures in Git, prompts or handoff files.
- Keep the demo `noindex, follow`; public launch remains `NO_GO` until the owner changes the authority records.
- Do not delete existing untracked/generated artifacts in the shared worktree.
- Every implementation change requires a focused verification command and an explicit rollback note.

---

### Task 1: Freeze and describe the baseline

**Files:**
- Create: `docs/superpowers/handoffs/2026-09-12-antigravity-full-project-handoff.md`
- Read: `CLAUDE.md`, `config/release-authority.json`, `config/decision-records.json`, `docs/HANDOFF.md`, `docs/architecture-decisions.md`

**Interfaces:**
- Consumes: current Git refs, active authority files, current demo deployment evidence.
- Produces: one authoritative handoff file with revision, ownership, architecture and verification commands.

- [ ] **Step 1: Record the exact repository revision and branch.**

Run:

```powershell
git rev-parse HEAD
git branch --show-current
git merge-base --is-ancestor frontend/lead/foundation HEAD
```

Expected: `873d39be50175474110e6e5e10fc5cfdc4fbe596`, `codex/correction-case-pilot`, and exit code `0` for the ancestor check.

- [ ] **Step 2: Record the current authority state without changing it.**

Run:

```powershell
python scripts/check_release_authority.py --root .
```

Expected: `PASS tracked=8 stale=0 mismatches=0`; decision records remain human-controlled and must not be signed by an agent.

- [ ] **Step 3: Write the baseline and ownership sections in the handoff file.**

Include exact paths, branch names, commit ids, tracked/untracked status, and the rule that generated artifacts are preserved rather than deleted.

- [ ] **Step 4: Verify the handoff file is readable and contains no secret-shaped values.**

Run:

```powershell
rg -n "password|secret|token|api[_-]?key|dsn|BEGIN .*PRIVATE KEY|J\]m7" docs/superpowers/handoffs/2026-09-12-antigravity-full-project-handoff.md
```

Expected: only policy words and redaction instructions; no credential value, DSN or private key.

- [ ] **Step 5: Commit only the handoff artifact when the owner requests a commit.**

```powershell
git add docs/superpowers/handoffs/2026-09-12-antigravity-full-project-handoff.md
git commit -m "docs: hand off full project to antigravity"
```

Do not stage unrelated generated files.

---

### Task 2: Define the full-project module map

**Files:**
- Modify: `docs/superpowers/handoffs/2026-09-12-antigravity-full-project-handoff.md`
- Read: `agent/`, `web-nuxt/`, `scripts/ops/`, `contracts/`, `ops/`

**Interfaces:**
- Consumes: module directories and existing API/deployment contracts.
- Produces: a map of backend domains, frontend boundaries, persistence, operations and test ownership.

- [ ] **Step 1: Document backend domains.**

List the current domains using their real paths: `agent/cases/`, `agent/community/`, `agent/entities/`, `agent/identity/`, `agent/itineraries/`, `agent/reports/`, `agent/control_plane/`, `agent/chat/`, `agent/llmops/`, plus composition in `agent/server.py`, `agent/public_api.py`, `agent/database.py`, `agent/auth*.py` and `agent/middleware.py`.

- [ ] **Step 2: Document frontend boundaries.**

Describe `web-nuxt/pages/`, `web-nuxt/components/`, `web-nuxt/composables/`, `web-nuxt/utils/`, `web-nuxt/server/`, `web-nuxt/types/` and `web-nuxt/tests/`. State that SSR API calls use `web-nuxt/utils/apiFetch.ts`.

- [ ] **Step 3: Document data and operations boundaries.**

State that PostgreSQL is authoritative for production data and UGC, migrations are explicit, systemd runs `vl-agent`, `vl-nuxt` and `vl-bot`, and the deployed frontend path is `/opt/vinhlong360/web-nuxt/.output`.

- [ ] **Step 4: Document contract and quality entry points.**

Reference `contracts/frontend-endpoints.json`, `docs/api-contract.md`, `scripts/checks/run_hard.py`, `scripts/ops/run_backend_regression.py`, frontend Vitest, Nuxt typecheck and build commands.

---

### Task 3: Define guarded Antigravity operating access

**Files:**
- Modify: `docs/superpowers/handoffs/2026-09-12-antigravity-full-project-handoff.md`
- Read: `docs/security-hardening.md`, `docs/deployment-guide.md`, `docs/runbooks/launch-safety-rollback.md`

**Interfaces:**
- Consumes: current systemd/tarball deployment model and owner authority rules.
- Produces: explicit permissions matrix and safe operating protocol.

- [ ] **Step 1: Grant codebase ownership through branch/worktree, not shared destructive Git commands.**

Antigravity may create branches, modify code and run tests. It must not run `git reset --hard`, `git checkout --`, `git clean`, global stash or `add -A` in the shared worktree.

- [ ] **Step 2: Grant demo deployment through a restricted path.**

Use a dedicated deploy identity or owner-run CI upload restricted to the demo frontend service. Do not provide root credentials, production `.env`, database credentials, signing keys or countersignature keys in the handoff.

- [ ] **Step 3: Reserve owner-only actions.**

Require owner approval for PostgreSQL migrations, data replacement, secret changes, public indexing, legal decisions, release signatures and any production/public deployment.

- [ ] **Step 4: Record rollback evidence.**

Reference the current frontend backup `/opt/vinhlong360/backups/nuxt-demo-pre-20260912T045546Z.tar.gz` and require a fresh backup plus health checks for every subsequent demo swap.

---

### Task 4: Define acceptance and continuation protocol

**Files:**
- Modify: `docs/superpowers/handoffs/2026-09-12-antigravity-full-project-handoff.md`
- Read: `CLAUDE.md`, `docs/standards/00-INDEX.md`, `docs/ROADMAP.md`

**Interfaces:**
- Consumes: project gates and known environment caveats.
- Produces: a copy/paste continuation prompt and a release-readiness checklist.

- [ ] **Step 1: Add baseline gates.**

```powershell
python scripts/checks/run_hard.py --all
python -m pytest tests/launch_safety/ -m "" -n0
Set-Location web-nuxt
npm run typecheck
npx vitest run
npm run build
```

Run backend regression with the documented temporary root before making claims about the full suite.

- [ ] **Step 2: Add live demo smoke gates.**

Verify `vl-nuxt` is active, local `:3000/` and `:3000/api/homepage` return `200`, public homepage and API return `200`, and the homepage remains `noindex, follow`.

- [ ] **Step 3: Add the Antigravity continuation prompt.**

The prompt must tell Antigravity to read `CLAUDE.md` first, inspect the handoff, preserve ownership boundaries, run focused tests before edits and report evidence rather than declaring completion from assumptions.

- [ ] **Step 4: Review the package against this plan.**

Confirm every section has an exact path, command, expected evidence and rollback rule; mark the handoff ready only after the owner approves the access channel.
