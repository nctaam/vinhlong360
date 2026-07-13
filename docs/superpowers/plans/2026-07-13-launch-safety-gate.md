# Launch Safety Gate Implementation Plan

> STATUS: proposed; awaiting implementation-plan review; implementation must not start; global `noindex` and all external launch blockers remain active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify one fail-closed indexing and AI-image-disclosure boundary while every real environment remains globally `noindex,follow`.

**Architecture:** Canonical root JSON artifacts feed matching Python and TypeScript policy loaders. FastAPI owns entity/ward indexability and immutable sitemap bundles; Nuxt owns the public launch decision, HTML/robots/root-sitemap responses, cache isolation, readiness, and disclosure rendering; Nginx is the only public ingress. Selective-open is exercised only in tests, and every missing dependency fails the affected request closed without changing live configuration.

**Tech Stack:** Python 3.14, FastAPI, PostgreSQL 16, pytest, Nuxt 4, Vue 3, TypeScript 6, Nitro/H3, Vitest, `@nuxt/test-utils`, Docker Compose, Nginx, systemd, Bash, and the existing Chrome smoke harness.

---

## Plan Authority and Execution Rules

- Approved design: `docs/superpowers/specs/2026-07-13-launch-safety-gate-design.md` at or after commit `9147d138494b15166781b3d9037555f161652370`.
- Execution worktree: `C:\Users\Administrator\.config\superpowers\worktrees\vinhlong360\codex-launch-safety-gate` on branch `codex/launch-safety-gate`.
- No task may push, merge, deploy, edit a real environment file, rotate a secret, mutate production data, or enable indexing on a live target.
- Every numbered task starts with a fresh implementer agent. The implementer records RED, makes the smallest GREEN change, runs focused checks, self-reviews, and commits.
- A fresh spec-compliance reviewer checks the task against this plan and the approved design. The implementer fixes every Critical or Important finding and requests re-review.
- Only after spec compliance passes does a separate fresh quality reviewer run. The implementer fixes every Critical or Important finding and requests re-review before the next task starts.
- Backend and frontend test commands run serially unless a task explicitly exercises concurrency. The known concurrent frontend/backend resource timeout is evidence, not permission to weaken assertions.
- If implementation reveals a cross-task contract change, stop and update this plan before editing outside the current task boundary.

## Locked File Structure

### Canonical policy and backend authority

- Create `config/launch-indexing-policy.json`: canonical route schema, inventory, revisions, normalization, and backend-ingress classification.
- Create `config/ai-disclosure.json`: canonical Vietnamese AI/placeholder/UGC copy and revision.
- Create `agent/launch_artifacts.py`: release-root resolution, exact-byte artifact loading, schema validation, and SHA-256 evidence.
- Create `agent/route_manifest.py`: Python normalization, classification, and static-sitemap route extraction.
- Create `agent/ai_disclosure.py`: Python disclosure loader.
- Create `agent/image_descriptor.py`: backend `ImageDescriptor` producers for entity, placeholder, review, and post media.
- Create `agent/launch_evidence.py`: reviewed semantic revision constants and policy fingerprint computation.
- Create `agent/index_policy.py`: the only entity/ward/itinerary indexability authority.
- Create `agent/policy_http.py`: exact policy-bearing endpoint registry and no-store/no-validator response enforcement.
- Create `agent/launch_policy_api.py`: internal attestation and sitemap-document router.
- Create `agent/sitemap_snapshot.py`: one PostgreSQL `REPEATABLE READ, READ ONLY` sitemap input snapshot.
- Create `agent/sitemap_render.py`: deterministic main/media/index XML and content-addressed batch revision.
- Create `agent/sitemap_store.py`: immutable bundle publication, locking, retention, and active-pointer loading.
- Create `agent/sitemap_bundle.py`: refresh orchestration and `python -m agent.sitemap_bundle refresh` CLI.
- Modify `agent/public_api.py`: entity/ward decision serialization, exact HTTP no-store contract, descriptor-shaped gallery payloads, and fresh policy-input handling.
- Modify `agent/server.py`: register internal launch routes and preserve exact cache/error headers.
- Modify `agent/seo.py`: remove duplicate quality/sitemap authority and delegate to the new policy/bundle modules.

### Nuxt launch boundary and disclosure consumers

- Create `web-nuxt/types/launch.ts`: shared decision, attestation, entity-policy, and evidence types.
- Create `web-nuxt/server/utils/launch/launchRouteManifest.ts`: build-only canonical route artifact loading and classification.
- Create `web-nuxt/utils/aiDisclosure.ts`: canonical disclosure artifact loading.
- Create `web-nuxt/server/utils/launch/launchIntent.ts`: exact two-key parser.
- Create `web-nuxt/server/utils/launch/backendAttestation.ts`: internal attestation client.
- Create `web-nuxt/server/utils/launch/launchSafetyDecision.ts`: base and request-scoped decision transitions.
- Create `web-nuxt/server/utils/launch/entityPolicy.ts`: exact entity/ward carrier validation.
- Create `web-nuxt/server/utils/launch/launchHeaders.ts`: exact policy/evidence/no-store header writer.
- Create `web-nuxt/server/utils/launch/guardedSitemapProxy.ts`: pinned internal sitemap proxy and evidence validation.
- Create `web-nuxt/server/utils/launch/rootSeoBodies.ts`: closed robots and endpoint-specific empty XML.
- Create `web-nuxt/server/utils/launch/readinessManifest.ts`: generated manifest validation and safe-closed/safe-open readiness checks.
- Create `web-nuxt/server/routes/_internal/launch-readiness.get.ts`: process-local readiness endpoint.
- Create `web-nuxt/server/routes/robots.txt.ts`, `web-nuxt/server/routes/sitemap.xml.ts`, `web-nuxt/server/routes/sitemap-media.xml.ts`, and `web-nuxt/server/routes/sitemap-index.xml.ts`: Nuxt-owned root SEO endpoints.
- Create `web-nuxt/plugins/launch-safety.server.ts` and `web-nuxt/composables/useLaunchSafety.ts`: request decision bridge for page meta and the conditional sitemap link.
- Create `web-nuxt/types/image.ts` and `web-nuxt/utils/imageDescriptors.ts`: frontend descriptor contracts and conversion helpers.
- Create `web-nuxt/components/ImageDisclosure.vue`: dense/full disclosure presentation shared by public, authenticated, and admin renderers.
- Create `web-nuxt/config/entity-image-renderers.json`: machine-readable renderer inventory used by the source guard.
- Modify `web-nuxt/nuxt.config.ts`, `web-nuxt/server/middleware/noindex.ts`, `web-nuxt/public/sw.js`, and the listed image-consuming pages/components without adding a second indexability predicate.

### Packaging, ingress, operations, and evidence

- Modify `web-nuxt/Dockerfile`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, and `docker-compose.prod.yml`; create `docker-compose.dev.yml` and `docker-compose.systemd-deps.yml` for audited loopback-only auxiliary topologies.
- Create `ops/systemd/vl-agent.service`, `ops/systemd/vl-nuxt.service`, `ops/systemd/vl-bot.service`, `ops/systemd/vl-watchdog.service`, and `ops/systemd/vl-watchdog.timer` as tracked loopback-bound production authorities.
- Modify `nginx.conf` and `nginx-ssl.conf`; create `ops/nginx/maintenance/` plus `scripts/ops/maintenance_mode.sh` in Task 31 as the reusable deploy/rollback drain authority.
- Modify `scripts/deploy.sh`; extend `scripts/package_launch_release.py` with the combined manifest+digest archive; add focused source/config validation helpers under `scripts/checks/`.
- Add backend tests under `agent/tests/`, Nuxt tests under `web-nuxt/tests/`, source/config tests under `tests/`, and local-only harnesses under `scripts/tests/`.

## Phase 1: Canonical Artifacts and Shared Policy Loaders

### Task 1: Establish the canonical packaging boundary

**Files:**
- Create: `config/README.md`
- Create: `scripts/package_launch_release.py`
- Create: `tests/launch_safety/test_artifact_packaging.py`
- Create: `tests/launch_safety/test_release_package.py`
- Modify: `.dockerignore`
- Modify: `web-nuxt/Dockerfile`
- Modify: `Dockerfile`
- Modify: `docker-compose.yml:77-90`
- Modify: `scripts/deploy.sh:82-113`
- Modify: `tests/test_release_quality_gates.py:221`

- [ ] **Step 1: Write failing packaging and duplicate-artifact tests**

```python
from pathlib import Path
import tarfile

from scripts.package_launch_release import (
    CANONICAL_ARTIFACTS,
    build_backend_archive,
    find_duplicate_artifacts,
)


def test_canonical_artifacts_may_exist_only_under_root_config(tmp_path: Path):
    root = tmp_path
    (root / "config").mkdir()
    (root / "web-nuxt").mkdir()
    for name in CANONICAL_ARTIFACTS:
        (root / "config" / name).write_text("{}", encoding="utf-8")
    (root / "web-nuxt" / "launch-indexing-policy.json").write_text("{}", encoding="utf-8")

    assert find_duplicate_artifacts(root) == [
        root / "web-nuxt" / "launch-indexing-policy.json",
    ]


def test_backend_archive_includes_root_config_unchanged(tmp_path: Path):
    root = tmp_path / "source"
    (root / "agent").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "requirements.txt").write_bytes(b"fastapi\n")
    (root / "init.sql").write_bytes(b"-- schema\n")
    route_bytes = b'{"revision":"launch-indexing-policy-v1"}\n'
    disclosure_bytes = b'{"revision":"ai-disclosure-v1"}\n'
    (root / "config" / "launch-indexing-policy.json").write_bytes(route_bytes)
    (root / "config" / "ai-disclosure.json").write_bytes(disclosure_bytes)

    archive = build_backend_archive(root, tmp_path / "backend.tar.gz")

    with tarfile.open(archive, "r:gz") as bundle:
        assert bundle.extractfile("config/launch-indexing-policy.json").read() == route_bytes
        assert bundle.extractfile("config/ai-disclosure.json").read() == disclosure_bytes
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_artifact_packaging.py tests/launch_safety/test_release_package.py -q`

Expected: FAIL because `scripts.package_launch_release`, root-context Nuxt packaging, and canonical config packaging do not exist.

- [ ] **Step 3: Implement the packaging authority and harden the root context**

```python
# scripts/package_launch_release.py
from pathlib import Path
import tarfile

CANONICAL_ARTIFACTS = (
    "launch-indexing-policy.json",
    "ai-disclosure.json",
)


def find_duplicate_artifacts(root: Path) -> list[Path]:
    canonical = {(root / "config" / name).resolve() for name in CANONICAL_ARTIFACTS}
    return sorted(
        path
        for name in CANONICAL_ARTIFACTS
        for path in root.rglob(name)
        if path.resolve() not in canonical
    )


def build_backend_archive(root: Path, destination: Path) -> Path:
    members = ["agent", "requirements.txt", "init.sql", "config"]
    if (root / "web/data.json").exists():
        members.append("web/data.json")
    with tarfile.open(destination, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        for member in members:
            source = root / member
            if not source.exists():
                raise FileNotFoundError(source)
            archive.add(source, arcname=member, recursive=True)
    return destination
```

Use repository root as the Nuxt Docker context:

```yaml
# docker-compose.yml
nuxt:
  build:
    context: .
    dockerfile: web-nuxt/Dockerfile
```

Use `/app/web-nuxt` as the Nuxt project directory and copy root config separately:

```dockerfile
# web-nuxt/Dockerfile
WORKDIR /app/web-nuxt
COPY web-nuxt/package*.json ./
RUN npm ci
COPY web-nuxt/ ./
COPY config/ /app/config/
RUN npm run build
```

Add `.env`, `**/.env`, `web-nuxt/.nuxt`, `web-nuxt/.output`, `.git`, and worktree-local caches to `.dockerignore`. Include `config/` unchanged in the backend archive and pre-deploy snapshot in `scripts/deploy.sh`.

- [ ] **Step 4: Run GREEN and syntax checks**

Run: `python -m pytest tests/launch_safety/test_artifact_packaging.py tests/launch_safety/test_release_package.py tests/test_release_quality_gates.py -q`

Run: `& 'C:\Program Files\Git\bin\bash.exe' -n scripts/deploy.sh`

Expected: packaging tests pass and Bash syntax exits 0. If Docker is available, additionally run `docker build -f web-nuxt/Dockerfile -t vl360-nuxt:launch-packaging .` and expect a successful build.

- [ ] **Step 5: Commit**

```bash
git add config/README.md scripts/package_launch_release.py tests/launch_safety/test_artifact_packaging.py tests/launch_safety/test_release_package.py .dockerignore web-nuxt/Dockerfile Dockerfile docker-compose.yml scripts/deploy.sh tests/test_release_quality_gates.py
git commit -m "build: establish launch artifact packaging"
```

### Task 2: Create the canonical route-manifest artifact

**Files:**
- Create: `config/launch-indexing-policy.json`
- Create: `tests/launch_safety/test_route_manifest_artifact.py`

- [ ] **Step 1: Write the failing artifact-shape test**

```python
import json
from pathlib import Path


def test_route_manifest_contains_reviewed_schema_and_inventory():
    manifest = json.loads(Path("config/launch-indexing-policy.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["revision"] == "launch-indexing-policy-v1"
    assert manifest["canonical_origin"] == "https://vinhlong360.vn"
    assert manifest["unknown_policy"] == "noindex-follow-public"
    assert {item["prefix"] for item in manifest["sensitive_prefixes"]} >= {
        "/_internal", "/admin", "/analytics", "/api", "/system", "/webhook", "/welcome"
    }
    assert manifest["backend_ingress_exceptions"] == []
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_route_manifest_artifact.py -q`

Expected: FAIL because the canonical manifest does not exist.

- [ ] **Step 3: Add the exact reviewed artifact**

Create `config/launch-indexing-policy.json` with these exact top-level values and the full approved inventory:

```json
{
  "schema_version": 1,
  "revision": "launch-indexing-policy-v1",
  "canonical_origin": "https://vinhlong360.vn",
  "unknown_policy": "noindex-follow-public",
  "normalization": {
    "percent_decode": "utf8-once",
    "encoded_separator_policy": "reject",
    "dot_segment_policy": "reject",
    "repeated_slash_policy": "redirect-canonical",
    "trailing_slash_policy": "redirect-except-root",
    "query_policy": "noindex-except-sitemap-batch"
  },
  "exact_routes": [
    {"path": "/", "classification": "indexable-public", "sitemap": true},
    {"path": "/du-lich", "classification": "indexable-public", "sitemap": true},
    {"path": "/dia-diem", "classification": "indexable-public", "sitemap": true},
    {"path": "/san-pham", "classification": "indexable-public", "sitemap": true},
    {"path": "/ocop", "classification": "indexable-public", "sitemap": true},
    {"path": "/luu-tru", "classification": "indexable-public", "sitemap": true},
    {"path": "/le-hoi", "classification": "indexable-public", "sitemap": true},
    {"path": "/su-kien", "classification": "indexable-public", "sitemap": true},
    {"path": "/theo-mua", "classification": "indexable-public", "sitemap": true},
    {"path": "/ban-do", "classification": "indexable-public", "sitemap": true},
    {"path": "/tuyen-duong", "classification": "indexable-public", "sitemap": true},
    {"path": "/danh-ba", "classification": "indexable-public", "sitemap": true},
    {"path": "/gioi-thieu", "classification": "indexable-public", "sitemap": true},
    {"path": "/huong-dan", "classification": "indexable-public", "sitemap": true},
    {"path": "/huong-dan-thanh-vien", "classification": "indexable-public", "sitemap": true},
    {"path": "/lien-he", "classification": "indexable-public", "sitemap": true},
    {"path": "/chinh-sach-bao-mat", "classification": "indexable-public", "sitemap": true},
    {"path": "/dieu-khoan-su-dung", "classification": "indexable-public", "sitemap": true},
    {"path": "/kham-pha/am-thuc", "classification": "indexable-public", "sitemap": true},
    {"path": "/kham-pha/thien-nhien", "classification": "indexable-public", "sitemap": true},
    {"path": "/kham-pha/van-hoa", "classification": "indexable-public", "sitemap": true},
    {"path": "/kham-pha/lang-nghe", "classification": "indexable-public", "sitemap": true},
    {"path": "/kham-pha/mua-sam", "classification": "indexable-public", "sitemap": true},
    {"path": "/khu-vuc/vinh-long", "classification": "indexable-public", "sitemap": true},
    {"path": "/khu-vuc/ben-tre", "classification": "indexable-public", "sitemap": true},
    {"path": "/khu-vuc/tra-vinh", "classification": "indexable-public", "sitemap": true},
    {"path": "/tim-kiem", "classification": "noindex-follow-public", "sitemap": false},
    {"path": "/lich-trinh", "classification": "noindex-follow-public", "sitemap": false},
    {"path": "/tao-lich-trinh", "classification": "noindex-follow-public", "sitemap": false},
    {"path": "/cong-dong", "classification": "noindex-follow-public", "sitemap": false},
    {"path": "/bang-xep-hang", "classification": "noindex-follow-public", "sitemap": false}
  ],
  "sensitive_prefixes": [
    {"prefix": "/_internal", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/admin", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/admin-api", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/analytics", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/api", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/auth", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/chat", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/events", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/feedback", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/freshness", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/health", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/reload", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/recommend", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/seo", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/system", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/weather", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/webhook", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/welcome", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/cai-dat", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/tai-khoan", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/da-luu", "classification": "crawl-blocked-sensitive"},
    {"prefix": "/thong-bao", "classification": "crawl-blocked-sensitive"}
  ],
  "backend_ingress_exceptions": [],
  "dynamic_templates": [
    {"template": "/dia-diem/{entity_id}", "authority": "backend-entity", "sitemap": "backend"},
    {"template": "/xa-phuong/{ward_id}", "authority": "backend-ward", "sitemap": "backend"},
    {"template": "/bai-viet/{id}", "authority": "fixed-noindex", "sitemap": false},
    {"template": "/nguoi-dung/{id}", "authority": "fixed-noindex", "sitemap": false},
    {"template": "/lich-trinh/{id}", "authority": "fixed-noindex", "sitemap": false},
    {"template": "/lich-trinh-chia-se/{id}", "authority": "fixed-noindex", "sitemap": false}
  ]
}
```

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest tests/launch_safety/test_route_manifest_artifact.py -q`

Expected: PASS with the exact reviewed inventory and no duplicate paths.

- [ ] **Step 5: Commit**

```bash
git add config/launch-indexing-policy.json tests/launch_safety/test_route_manifest_artifact.py
git commit -m "feat: add canonical launch route manifest"
```

### Task 3: Add the TypeScript route-manifest loader

**Files:**
- Create: `web-nuxt/server/utils/launch/launchRouteManifest.ts`
- Create: `web-nuxt/tests/launch-route-manifest.test.ts`
- Modify: `web-nuxt/nuxt.config.ts`

- [ ] **Step 1: Write failing TypeScript validation tests**

```ts
import { describe, expect, it } from 'vitest'
import { parseLaunchRouteManifest } from '../server/utils/launch/launchRouteManifest'

describe('parseLaunchRouteManifest', () => {
  it('accepts the canonical placeholder grammar', () => {
    const parsed = parseLaunchRouteManifest(validManifest)
    expect(parsed.dynamic_templates.map(item => item.template)).toContain('/dia-diem/{entity_id}')
  })

  it.each([
    ['missing normalization key', { normalization: { percent_decode: 'utf8-once' } }],
    ['unknown top-level key', { extra: true }],
    ['invalid exact classification', { exact_routes: [{ path: '/', classification: 'public', sitemap: true }] }],
    ['invalid sensitive path', { sensitive_prefixes: [{ prefix: '/admin/', classification: 'crawl-blocked-sensitive' }] }],
    ['empty ingress review', { backend_ingress_exceptions: [{ prefix: '/hook', upstream: 'agent', review_reason: ' ' }] }],
    ['ambiguous template', { dynamic_templates: [
      { template: '/dia-diem/{entity_id}', authority: 'backend-entity', sitemap: 'backend' },
      { template: '/dia-diem/{id}', authority: 'backend-entity', sitemap: 'backend' },
    ] }],
  ])('rejects %s', (_name, override) => {
    expect(() => parseLaunchRouteManifest({ ...validManifest, ...override }))
      .toThrow(/route manifest/i)
  })

  it.each([
    '/dia-diem/{entity_id',
    '/dia-diem/entity_id}',
    '/dia-diem/{}',
    '/dia-diem/{EntityId}',
    '/dia-diem/prefix-{entity_id}',
    '/dia-diem/{entity_id}-suffix',
    '/dia-diem/{entity_id}/{entity_id}',
  ])('rejects malformed or duplicate placeholder grammar: %s', (template) => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      dynamic_templates: [{ template, authority: 'backend-entity', sitemap: 'backend' }],
    })).toThrow(/dynamic template/i)
  })

  it('rejects duplicate exact routes and exact/exception duplicates', () => {
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      exact_routes: [validManifest.exact_routes[0], validManifest.exact_routes[0]],
    })).toThrow(/duplicate exact route/i)
    expect(() => parseLaunchRouteManifest({
      ...validManifest,
      backend_ingress_exceptions: [
        { prefix: '/webhook', upstream: 'bot-gateway', review_reason: 'reviewed alias' },
        { prefix: '/webhook', upstream: 'bot-gateway', review_reason: 'reviewed alias' },
      ],
    })).toThrow(/duplicate ingress exception/i)
  })
})
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-route-manifest.test.ts`

Expected: FAIL because the loader and parser do not exist.

- [ ] **Step 3: Implement strict parsing and one root artifact import**

```ts
// web-nuxt/server/utils/launch/launchRouteManifest.ts
import manifestJson from '#launch-config/launch-indexing-policy.json'

const EXPECTED_REVISION = 'launch-indexing-policy-v1'
const NORMALIZATION = Object.freeze({
  percent_decode: 'utf8-once',
  encoded_separator_policy: 'reject',
  dot_segment_policy: 'reject',
  repeated_slash_policy: 'redirect-canonical',
  trailing_slash_policy: 'redirect-except-root',
  query_policy: 'noindex-except-sitemap-batch',
})
const TOP_LEVEL_KEYS = ['backend_ingress_exceptions', 'canonical_origin', 'dynamic_templates', 'exact_routes', 'normalization', 'revision', 'schema_version', 'sensitive_prefixes', 'unknown_policy']
const EXACT_KEYS = ['classification', 'path', 'sitemap']
const PREFIX_KEYS = ['classification', 'prefix']
const INGRESS_KEYS = ['prefix', 'review_reason', 'upstream']
const TEMPLATE_KEYS = ['authority', 'sitemap', 'template']

export interface LaunchRouteManifest {
  schema_version: 1
  revision: string
  canonical_origin: 'https://vinhlong360.vn'
  unknown_policy: 'noindex-follow-public'
  normalization: typeof NORMALIZATION
  exact_routes: Array<{ path: string; classification: 'indexable-public' | 'noindex-follow-public'; sitemap: boolean }>
  sensitive_prefixes: Array<{ prefix: string; classification: 'crawl-blocked-sensitive' }>
  backend_ingress_exceptions: Array<{ prefix: string; upstream: 'agent' | 'bot-gateway'; review_reason: string }>
  dynamic_templates: Array<{ template: string; authority: 'backend-entity' | 'backend-ward' | 'fixed-noindex'; sitemap: 'backend' | false }>
}

function record(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`route manifest ${label} must be an object`)
  return value as Record<string, unknown>
}

function exactKeys(value: Record<string, unknown>, keys: string[], label: string) {
  const actual = Object.keys(value).sort()
  if (actual.join('\0') !== [...keys].sort().join('\0')) throw new Error(`route manifest ${label} keys mismatch`)
}

function canonicalPath(value: unknown, label: string): string {
  if (typeof value !== 'string' || !value.startsWith('/') || value.includes('?') || value.includes('#') ||
      value.includes('//') || value.includes('%') || value.includes('\\') || (value !== '/' && value.endsWith('/')) ||
      value.split('/').some(segment => segment === '.' || segment === '..')) {
    throw new Error(`route manifest ${label} is not canonical`)
  }
  return value
}

function templateSignature(template: unknown): string {
  if (typeof template !== 'string') throw new Error('route manifest dynamic template is invalid')
  const names: string[] = []
  const concreteSegments = template.split('/').map((segment) => {
    if (!segment.includes('{') && !segment.includes('}')) return segment
    const match = /^\{([a-z_][a-z0-9_]*)\}$/.exec(segment)
    if (!match || names.includes(match[1]!)) throw new Error('route manifest dynamic template is invalid')
    names.push(match[1]!)
    return 'value'
  })
  if (names.length === 0) throw new Error('route manifest dynamic template is invalid')
  canonicalPath(concreteSegments.join('/'), 'dynamic template')
  return template.split('/').map(segment => /^\{[a-z_][a-z0-9_]*\}$/.test(segment) ? '{}' : segment).join('/')
}

function array(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`route manifest ${label} must be an array`)
  return value
}

function assertUnique(values: string[], message: string) {
  if (new Set(values).size !== values.length) throw new Error(`route manifest ${message}`)
}

function matchesTemplate(path: string, template: string): boolean {
  const pathSegments = path.split('/').slice(1)
  const templateSegments = template.split('/').slice(1)
  return pathSegments.length === templateSegments.length && templateSegments.every((segment, index) =>
    /^\{[a-z_][a-z0-9_]*\}$/.test(segment) || segment === pathSegments[index])
}

function deepFreeze<T>(value: T): Readonly<T> {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value)
    for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child)
  }
  return value
}

export function parseLaunchRouteManifest(value: unknown, expectedRevision = EXPECTED_REVISION): LaunchRouteManifest {
  const manifest = record(value, 'root')
  exactKeys(manifest, TOP_LEVEL_KEYS, 'root')
  if (manifest.schema_version !== 1 || manifest.revision !== expectedRevision ||
      manifest.canonical_origin !== 'https://vinhlong360.vn' || manifest.unknown_policy !== 'noindex-follow-public') {
    throw new Error('route manifest fixed fields mismatch')
  }
  const normalization = record(manifest.normalization, 'normalization')
  exactKeys(normalization, Object.keys(NORMALIZATION), 'normalization')
  if (Object.entries(NORMALIZATION).some(([key, expected]) => normalization[key] !== expected)) throw new Error('route manifest normalization mismatch')

  const exactRoutes = array(manifest.exact_routes, 'exact_routes').map((raw, index) => {
    const item = record(raw, `exact_routes[${index}]`); exactKeys(item, EXACT_KEYS, `exact_routes[${index}]`)
    const path = canonicalPath(item.path, 'exact path')
    if (!['indexable-public', 'noindex-follow-public'].includes(String(item.classification)) || typeof item.sitemap !== 'boolean') throw new Error('route manifest exact route values mismatch')
    return { path, classification: item.classification, sitemap: item.sitemap }
  })
  const sensitive = array(manifest.sensitive_prefixes, 'sensitive_prefixes').map((raw, index) => {
    const item = record(raw, `sensitive_prefixes[${index}]`); exactKeys(item, PREFIX_KEYS, `sensitive_prefixes[${index}]`)
    if (item.classification !== 'crawl-blocked-sensitive') throw new Error('route manifest sensitive classification mismatch')
    const prefix = canonicalPath(item.prefix, 'sensitive prefix')
    if (prefix === '/') throw new Error('route manifest sensitive prefix cannot be root')
    return { prefix, classification: item.classification }
  })
  const ingress = array(manifest.backend_ingress_exceptions, 'backend_ingress_exceptions').map((raw, index) => {
    const item = record(raw, `backend_ingress_exceptions[${index}]`); exactKeys(item, INGRESS_KEYS, `backend_ingress_exceptions[${index}]`)
    if (!['agent', 'bot-gateway'].includes(String(item.upstream)) || typeof item.review_reason !== 'string' || !item.review_reason.trim()) throw new Error('route manifest ingress exception mismatch')
    const prefix = canonicalPath(item.prefix, 'ingress prefix')
    if (prefix === '/') throw new Error('route manifest ingress prefix cannot be root')
    return { prefix, upstream: item.upstream, review_reason: item.review_reason }
  })
  const templates = array(manifest.dynamic_templates, 'dynamic_templates').map((raw, index) => {
    const item = record(raw, `dynamic_templates[${index}]`); exactKeys(item, TEMPLATE_KEYS, `dynamic_templates[${index}]`)
    const template = String(item.template); const signature = templateSignature(template)
    const authority = item.authority
    if (!['backend-entity', 'backend-ward', 'fixed-noindex'].includes(String(authority)) ||
        ((authority === 'fixed-noindex') !== (item.sitemap === false)) ||
        ((authority !== 'fixed-noindex') !== (item.sitemap === 'backend'))) throw new Error('route manifest dynamic authority mismatch')
    return { template, signature, authority, sitemap: item.sitemap }
  })

  assertUnique(exactRoutes.map(item => item.path), 'duplicate exact route')
  assertUnique(sensitive.map(item => item.prefix), 'duplicate sensitive prefix')
  assertUnique(ingress.map(item => item.prefix), 'duplicate ingress exception')
  assertUnique(templates.map(item => item.signature), 'ambiguous dynamic template')
  if (ingress.some(item => sensitive.some(rule => item.prefix === rule.prefix || item.prefix.startsWith(rule.prefix + '/') || rule.prefix.startsWith(item.prefix + '/')))) throw new Error('route manifest ingress/sensitive ambiguity')
  if (exactRoutes.some(item => templates.some(template => matchesTemplate(item.path, template.template)))) throw new Error('route manifest exact/template ambiguity')
  return deepFreeze({ ...manifest, exact_routes: exactRoutes, sensitive_prefixes: sensitive, backend_ingress_exceptions: ingress, dynamic_templates: templates.map(({ signature, ...item }) => item) }) as LaunchRouteManifest
}

export const launchRouteManifest = parseLaunchRouteManifest(manifestJson)
```

The invalid-fixture matrix in Task 5 exercises every helper, so neither runtime can silently accept a partial schema, extra key, malformed template, unresolved exact/template ambiguity, or ingress exception without a non-empty review reason.

Add a Nuxt alias that resolves `../config` from the repository root without copying a second source artifact:

```ts
alias: {
  '#launch-config': fileURLToPath(new URL('../config', import.meta.url)),
},
```

- [ ] **Step 4: Run GREEN and typecheck**

Run: `cd web-nuxt && npm test -- --run tests/launch-route-manifest.test.ts && npm run typecheck`

Expected: focused tests and typecheck pass.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/server/utils/launch/launchRouteManifest.ts web-nuxt/tests/launch-route-manifest.test.ts web-nuxt/nuxt.config.ts
git commit -m "feat: load launch route manifest in Nuxt"
```

### Task 4: Add the Python route-manifest loader

**Files:**
- Create: `agent/launch_artifacts.py`
- Create: `agent/route_manifest.py`
- Create: `agent/tests/test_launch_artifacts.py`
- Create: `agent/tests/test_route_manifest.py`

- [ ] **Step 1: Write failing release-root and schema tests**

```python
import json
from pathlib import Path

import pytest

from launch_artifacts import load_artifact
from route_manifest import load_route_manifest


def test_fixture_path_is_explicit_and_production_has_no_fallback(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_artifact("launch-indexing-policy.json", release_root=tmp_path)


def test_release_root_and_fixture_path_are_mutually_exclusive(tmp_path: Path):
    with pytest.raises(ValueError, match="mutually exclusive"):
        load_route_manifest(release_root=tmp_path, fixture_path=tmp_path / "manifest.json")


def test_route_manifest_rejects_duplicate_paths(valid_manifest, tmp_path: Path):
    fixture = tmp_path / "manifest.json"
    valid_manifest["exact_routes"].append(valid_manifest["exact_routes"][0].copy())
    fixture.write_text(json.dumps(valid_manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate exact route"):
        load_route_manifest(fixture_path=fixture)


@pytest.mark.parametrize("mutation", [
    lambda data: data["normalization"].pop("query_policy"),
    lambda data: data.update(extra=True),
    lambda data: data["dynamic_templates"].append({"template": "/dia-diem/{id}", "authority": "backend-entity", "sitemap": "backend"}),
    lambda data: data["backend_ingress_exceptions"].append({"prefix": "/hook", "upstream": "agent", "review_reason": ""}),
])
def test_python_validator_rejects_the_same_strict_schema_failures(valid_manifest, mutation, tmp_path):
    mutation(valid_manifest)
    fixture = tmp_path / "manifest.json"
    fixture.write_text(json.dumps(valid_manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="route manifest"):
        load_route_manifest(fixture_path=fixture)
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_launch_artifacts.py agent/tests/test_route_manifest.py -q`

Expected: FAIL because the Python artifact and manifest loaders do not exist.

- [ ] **Step 3: Implement exact-byte loading and typed parsing**

```python
# agent/launch_artifacts.py
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path


@dataclass(frozen=True)
class LoadedArtifact:
    path: Path
    raw: bytes
    data: dict
    sha256: str


def load_artifact(name: str, *, release_root: Path | None = None, fixture_path: Path | None = None) -> LoadedArtifact:
    if release_root is not None and fixture_path is not None:
        raise ValueError("release_root and fixture_path are mutually exclusive")
    root = release_root if release_root is not None else Path(__file__).resolve().parents[1]
    path = fixture_path if fixture_path is not None else root / "config" / name
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{name} must contain an object")
    return LoadedArtifact(path=path, raw=raw, data=data, sha256=sha256(raw).hexdigest())
```

```python
# agent/route_manifest.py
from dataclasses import dataclass
from pathlib import Path
import re

from launch_artifacts import LoadedArtifact, load_artifact

EXPECTED_REVISION = "launch-indexing-policy-v1"
NORMALIZATION = {
    "percent_decode": "utf8-once",
    "encoded_separator_policy": "reject",
    "dot_segment_policy": "reject",
    "repeated_slash_policy": "redirect-canonical",
    "trailing_slash_policy": "redirect-except-root",
    "query_policy": "noindex-except-sitemap-batch",
}
TOP_LEVEL_KEYS = {
    "schema_version", "revision", "canonical_origin", "unknown_policy", "normalization",
    "exact_routes", "sensitive_prefixes", "backend_ingress_exceptions", "dynamic_templates",
}


@dataclass(frozen=True)
class LoadedRouteManifest:
    artifact: LoadedArtifact
    revision: str
    data: dict


def _exact_keys(value: dict, expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"route manifest {label} keys mismatch")


def _canonical_path(value: object, label: str) -> str:
    if (
        not isinstance(value, str) or not value.startswith("/") or "?" in value or "#" in value
        or "//" in value or "%" in value or "\\" in value
        or (value != "/" and value.endswith("/"))
        or any(segment in {".", ".."} for segment in value.split("/"))
    ):
        raise ValueError(f"route manifest {label} is not canonical")
    return value


def _template_signature(template: object) -> str:
    if not isinstance(template, str):
        raise ValueError("route manifest dynamic template is invalid")
    names: list[str] = []
    concrete_segments: list[str] = []
    signature_segments: list[str] = []
    for segment in template.split("/"):
        if "{" not in segment and "}" not in segment:
            concrete_segments.append(segment)
            signature_segments.append(segment)
            continue
        match = re.fullmatch(r"\{([a-z_][a-z0-9_]*)\}", segment)
        if match is None or match.group(1) in names:
            raise ValueError("route manifest dynamic template is invalid")
        names.append(match.group(1))
        concrete_segments.append("value")
        signature_segments.append("{}")
    if not names:
        raise ValueError("route manifest dynamic template is invalid")
    _canonical_path("/".join(concrete_segments), "dynamic template")
    return "/".join(signature_segments)


def _matches_template(path: str, template: str) -> bool:
    path_segments = path.split("/")[1:]
    template_segments = template.split("/")[1:]
    return len(path_segments) == len(template_segments) and all(
        re.fullmatch(r"\{[a-z_][a-z0-9_]*\}", rule) or rule == actual
        for actual, rule in zip(path_segments, template_segments, strict=True)
    )


def validate_route_manifest_data(data: dict, *, expected_revision: str = EXPECTED_REVISION) -> None:
    _exact_keys(data, TOP_LEVEL_KEYS, "root")
    if data["schema_version"] != 1 or data["revision"] != expected_revision:
        raise ValueError("route manifest fixed fields mismatch")
    if data["canonical_origin"] != "https://vinhlong360.vn" or data["unknown_policy"] != "noindex-follow-public":
        raise ValueError("route manifest fixed fields mismatch")
    if not isinstance(data["normalization"], dict):
        raise ValueError("route manifest normalization must be an object")
    _exact_keys(data["normalization"], set(NORMALIZATION), "normalization")
    if data["normalization"] != NORMALIZATION:
        raise ValueError("route manifest normalization mismatch")

    for key in ("exact_routes", "sensitive_prefixes", "backend_ingress_exceptions", "dynamic_templates"):
        if not isinstance(data[key], list):
            raise ValueError(f"route manifest {key} must be an array")
    exact_paths: list[str] = []
    for item in data["exact_routes"]:
        if not isinstance(item, dict):
            raise ValueError("route manifest exact route must be an object")
        _exact_keys(item, {"path", "classification", "sitemap"}, "exact route")
        exact_paths.append(_canonical_path(item["path"], "exact path"))
        if item["classification"] not in {"indexable-public", "noindex-follow-public"} or not isinstance(item["sitemap"], bool):
            raise ValueError("route manifest exact route values mismatch")
    sensitive: list[str] = []
    for item in data["sensitive_prefixes"]:
        if not isinstance(item, dict):
            raise ValueError("route manifest sensitive prefix must be an object")
        _exact_keys(item, {"prefix", "classification"}, "sensitive prefix")
        prefix = _canonical_path(item["prefix"], "sensitive prefix")
        if prefix == "/":
            raise ValueError("route manifest sensitive prefix cannot be root")
        sensitive.append(prefix)
        if item["classification"] != "crawl-blocked-sensitive":
            raise ValueError("route manifest sensitive classification mismatch")
    ingress: list[str] = []
    for item in data["backend_ingress_exceptions"]:
        if not isinstance(item, dict):
            raise ValueError("route manifest ingress exception must be an object")
        _exact_keys(item, {"prefix", "upstream", "review_reason"}, "ingress exception")
        prefix = _canonical_path(item["prefix"], "ingress prefix")
        if prefix == "/":
            raise ValueError("route manifest ingress prefix cannot be root")
        ingress.append(prefix)
        if item["upstream"] not in {"agent", "bot-gateway"} or not isinstance(item["review_reason"], str) or not item["review_reason"].strip():
            raise ValueError("route manifest ingress exception mismatch")
    signatures: list[str] = []
    templates: list[str] = []
    for item in data["dynamic_templates"]:
        if not isinstance(item, dict):
            raise ValueError("route manifest dynamic template must be an object")
        _exact_keys(item, {"template", "authority", "sitemap"}, "dynamic template")
        templates.append(item["template"])
        signatures.append(_template_signature(item["template"]))
        authority = item["authority"]
        if authority not in {"backend-entity", "backend-ward", "fixed-noindex"}:
            raise ValueError("route manifest dynamic authority mismatch")
        if (authority == "fixed-noindex" and item["sitemap"] is not False) or (authority != "fixed-noindex" and item["sitemap"] != "backend"):
            raise ValueError("route manifest dynamic authority mismatch")

    for values, label in ((exact_paths, "duplicate exact route"), (sensitive, "duplicate sensitive prefix"), (ingress, "duplicate ingress exception"), (signatures, "ambiguous dynamic template")):
        if len(values) != len(set(values)):
            raise ValueError(f"route manifest {label}")
    if any(a == b or a.startswith(b + "/") or b.startswith(a + "/") for a in ingress for b in sensitive):
        raise ValueError("route manifest ingress/sensitive ambiguity")
    if any(_matches_template(path, template) for path in exact_paths for template in templates):
        raise ValueError("route manifest exact/template ambiguity")


def load_route_manifest(*, release_root: Path | None = None, fixture_path: Path | None = None) -> LoadedRouteManifest:
    artifact = load_artifact(
        "launch-indexing-policy.json",
        release_root=release_root,
        fixture_path=fixture_path,
    )
    data = artifact.data
    validate_route_manifest_data(data)
    return LoadedRouteManifest(artifact=artifact, revision=data["revision"], data=data)
```

- [ ] **Step 4: Run GREEN and Ruff**

Run: `python -m pytest agent/tests/test_launch_artifacts.py agent/tests/test_route_manifest.py -q`

Run: `python -m ruff check agent/launch_artifacts.py agent/route_manifest.py agent/tests/test_launch_artifacts.py agent/tests/test_route_manifest.py`

Expected: tests and Ruff pass.

- [ ] **Step 5: Commit**

```bash
git add agent/launch_artifacts.py agent/route_manifest.py agent/tests/test_launch_artifacts.py agent/tests/test_route_manifest.py
git commit -m "feat: load launch route manifest in Python"
```

### Task 5: Implement route normalization, classification, and parity

**Files:**
- Modify: `agent/route_manifest.py`
- Modify: `web-nuxt/server/utils/launch/launchRouteManifest.ts`
- Create: `tests/fixtures/launch-route-parity-corpus.json`
- Create: `tests/fixtures/launch-route-validator-corpus.json`
- Create: `agent/tests/test_route_manifest_parity.py`
- Create: `web-nuxt/tests/launch-route-parity.test.ts`
- Modify: `nginx.conf`
- Modify: `nginx-ssl.conf`

- [ ] **Step 1: Write the shared failing corpus and classifier assertions**

```json
[
  {"target": "/", "method": "GET", "classification": "indexable-public", "canonical": "/"},
  {"target": "/admin", "method": "GET", "classification": "crawl-blocked-sensitive", "canonical": "/admin"},
  {"target": "/%61dmin/users", "method": "GET", "classification": "crawl-blocked-sensitive", "canonical": "/admin/users"},
  {"target": "/administrator", "method": "GET", "classification": "noindex-follow-public", "canonical": "/administrator"},
  {"target": "/system/x?debug=1", "method": "GET", "classification": "crawl-blocked-sensitive", "canonical": "/system/x"},
  {"target": "/systematic", "method": "GET", "classification": "noindex-follow-public", "canonical": "/systematic"},
  {"target": "/apiary", "method": "GET", "classification": "noindex-follow-public", "canonical": "/apiary"},
  {"target": "/webhooks", "method": "GET", "classification": "noindex-follow-public", "canonical": "/webhooks"},
  {"target": "/dia-diem/a", "method": "GET", "classification": "backend-entity", "canonical": "/dia-diem/a"},
  {"target": "/bai-viet/a", "method": "GET", "classification": "fixed-noindex", "canonical": "/bai-viet/a"},
  {"target": "/dia-diem//a", "method": "GET", "classification": "redirect-canonical", "canonical": "/dia-diem/a"},
  {"target": "/du-lich/", "method": "HEAD", "classification": "redirect-canonical", "canonical": "/du-lich"},
  {"target": "/du-lich?campaign=1", "method": "GET", "classification": "noindex-follow-public", "canonical": "/du-lich"},
  {"target": "/api%2Fsecret", "method": "GET", "classification": "reject", "canonical": null},
  {"target": "/api%255csecret", "method": "GET", "classification": "reject", "canonical": null},
  {"target": "/a/%2e%2e/admin", "method": "GET", "classification": "reject", "canonical": null},
  {"target": "/%FF", "method": "GET", "classification": "reject", "canonical": null},
  {"target": "/unknown", "method": "GET", "classification": "noindex-follow-public", "canonical": "/unknown"}
]
```

The validator corpus applies the same JSON mutations in both runtimes:

```json
[
  {"name": "missing-normalization-key", "operation": "delete", "pointer": "/normalization/query_policy", "error": "normalization"},
  {"name": "unknown-root-key", "operation": "set", "pointer": "/extra", "value": true, "error": "keys mismatch"},
  {"name": "invalid-exact-classification", "operation": "set", "pointer": "/exact_routes/0/classification", "value": "public", "error": "exact route"},
  {"name": "duplicate-sensitive-prefix", "operation": "append-copy", "pointer": "/sensitive_prefixes/0", "error": "duplicate sensitive prefix"},
  {"name": "empty-ingress-review", "operation": "append", "pointer": "/backend_ingress_exceptions", "value": {"prefix": "/hook", "upstream": "agent", "review_reason": ""}, "error": "ingress exception"},
  {"name": "ambiguous-dynamic-template", "operation": "append", "pointer": "/dynamic_templates", "value": {"template": "/dia-diem/{id}", "authority": "backend-entity", "sitemap": "backend"}, "error": "ambiguous dynamic template"},
  {"name": "unclosed-dynamic-placeholder", "operation": "set", "pointer": "/dynamic_templates/0/template", "value": "/dia-diem/{entity_id", "error": "dynamic template"},
  {"name": "embedded-dynamic-placeholder", "operation": "set", "pointer": "/dynamic_templates/0/template", "value": "/dia-diem/prefix-{entity_id}", "error": "dynamic template"},
  {"name": "uppercase-dynamic-placeholder", "operation": "set", "pointer": "/dynamic_templates/0/template", "value": "/dia-diem/{EntityId}", "error": "dynamic template"},
  {"name": "duplicate-placeholder-name", "operation": "set", "pointer": "/dynamic_templates/0/template", "value": "/dia-diem/{entity_id}/{entity_id}", "error": "dynamic template"},
  {"name": "fixed-noindex-with-backend-sitemap", "operation": "set", "pointer": "/dynamic_templates/2/sitemap", "value": "backend", "error": "dynamic authority"}
]
```

Both test suites first prove the unmodified canonical templates parse successfully, then apply every mutation and assert the matching error class. The shared invalid corpus covers missing/extra braces, embedded placeholders, duplicate placeholder names, and the exact lowercase snake-case full-segment grammar, so Python and TypeScript cannot drift. They also iterate the route corpus and compare classification plus canonical target, the exact `sitemap=true` extraction, and the normalized backend-ingress exception model.

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_route_manifest_parity.py -q`

Run: `cd web-nuxt && npm test -- --run tests/launch-route-parity.test.ts`

Expected: FAIL because normalization/classification functions do not exist.

- [ ] **Step 3: Implement identical precedence and static extraction**

```python
from urllib.parse import unquote_to_bytes


@dataclass(frozen=True)
class RouteDecision:
    classification: str
    canonical_path: str | None


def _decode_once(raw_path: str) -> str | None:
    if re.search(r"%(?![0-9A-Fa-f]{2})", raw_path) or re.search(r"%2f|%5c", raw_path, re.I):
        return None
    try:
        decoded = unquote_to_bytes(raw_path).decode("utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError):
        return None
    if "\x00" in decoded or re.search(r"%[0-9A-Fa-f]{2}", decoded):
        return None
    if any(segment in {".", ".."} for segment in decoded.split("/")):
        return None
    return decoded


def _segment_match(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def classify_request_target(target: str, manifest: LoadedRouteManifest, *, method: str = "GET") -> RouteDecision:
    if not target.startswith("/") or "#" in target:
        return RouteDecision("reject", None)
    raw_path, separator, query = target.partition("?")
    decoded = _decode_once(raw_path)
    if decoded is None:
        return RouteDecision("reject", None)
    raw_without_empty = "/" + "/".join(segment for segment in raw_path.split("/") if segment)
    normalized = "/" + "/".join(segment for segment in decoded.split("/") if segment)
    normalized = normalized if normalized == "/" else normalized.rstrip("/")
    for item in manifest.data["sensitive_prefixes"]:
        prefix = item["prefix"]
        if _segment_match(raw_without_empty, prefix) or _segment_match(normalized, prefix):
            return RouteDecision("crawl-blocked-sensitive", normalized)
    needs_redirect = raw_path != normalized
    if needs_redirect and method in {"GET", "HEAD"}:
        return RouteDecision("redirect-canonical", normalized)
    if needs_redirect:
        return RouteDecision("noindex-follow-public", normalized)
    if separator and query:
        return RouteDecision("noindex-follow-public", normalized)
    exact = next((item for item in manifest.data["exact_routes"] if item["path"] == normalized), None)
    if exact:
        return RouteDecision(exact["classification"], normalized)
    for item in manifest.data["dynamic_templates"]:
        if _matches_template(normalized, item["template"]):
            return RouteDecision(item["authority"], normalized)
    return RouteDecision(manifest.data["unknown_policy"], normalized)


def extract_static_sitemap_paths(manifest: LoadedRouteManifest) -> tuple[str, ...]:
    return tuple(sorted(
        item["path"] for item in manifest.data["exact_routes"]
        if item["classification"] == "indexable-public" and item["sitemap"] is True
    ))
```

```ts
function decodeOnce(rawPath: string): string | null {
  if (/%(?![0-9A-Fa-f]{2})/.test(rawPath) || /%2f|%5c/i.test(rawPath)) return null
  let decoded: string
  try { decoded = decodeURIComponent(rawPath) } catch { return null }
  if (decoded.includes('\0') || /%[0-9A-Fa-f]{2}/.test(decoded)) return null
  if (decoded.split('/').some(segment => segment === '.' || segment === '..')) return null
  return decoded
}

function segmentMatch(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`)
}

export function classifyRequestTarget(
  target: string,
  manifest: LaunchRouteManifest,
  method: 'GET' | 'HEAD' | string = 'GET',
): RouteDecision {
  if (!target.startsWith('/') || target.includes('#')) return { classification: 'reject', canonical_path: null }
  const question = target.indexOf('?')
  const rawPath = question === -1 ? target : target.slice(0, question)
  const query = question === -1 ? '' : target.slice(question + 1)
  const decoded = decodeOnce(rawPath)
  if (decoded === null) return { classification: 'reject', canonical_path: null }
  const rawWithoutEmpty = `/${rawPath.split('/').filter(Boolean).join('/')}`
  const collapsed = `/${decoded.split('/').filter(Boolean).join('/')}`
  const normalized = collapsed === '/' ? collapsed : collapsed.replace(/\/+$/, '')
  for (const item of manifest.sensitive_prefixes) {
    if (segmentMatch(rawWithoutEmpty, item.prefix) || segmentMatch(normalized, item.prefix)) {
      return { classification: 'crawl-blocked-sensitive', canonical_path: normalized }
    }
  }
  if (rawPath !== normalized) {
    return { classification: method === 'GET' || method === 'HEAD' ? 'redirect-canonical' : 'noindex-follow-public', canonical_path: normalized }
  }
  if (question !== -1 && query !== '') return { classification: 'noindex-follow-public', canonical_path: normalized }
  const exact = manifest.exact_routes.find(item => item.path === normalized)
  if (exact) return { classification: exact.classification, canonical_path: normalized }
  const dynamic = manifest.dynamic_templates.find(item => matchesTemplate(normalized, item.template))
  if (dynamic) return { classification: dynamic.authority, canonical_path: normalized }
  return { classification: manifest.unknown_policy, canonical_path: normalized }
}

export function extractStaticSitemapPaths(manifest: LaunchRouteManifest): string[] {
  return manifest.exact_routes
    .filter(item => item.classification === 'indexable-public' && item.sitemap === true)
    .map(item => item.path)
    .sort()
}
```

The TypeScript test imports both JSON corpora and checks every row; the Python test invokes a small Node runner over those same corpora and compares the serialized decisions byte-for-byte. Update Nginx backend-route regexes to use end-or-slash boundaries; detailed ingress ownership remains Task 32.

- [ ] **Step 4: Run GREEN and parity checks**

Run: `python -m pytest agent/tests/test_route_manifest.py agent/tests/test_route_manifest_parity.py -q`

Run: `cd web-nuxt && npm test -- --run tests/launch-route-manifest.test.ts tests/launch-route-parity.test.ts`

Expected: both implementations return identical corpus results and exact static sitemap paths.

- [ ] **Step 5: Commit**

```bash
git add agent/route_manifest.py web-nuxt/server/utils/launch/launchRouteManifest.ts tests/fixtures/launch-route-parity-corpus.json tests/fixtures/launch-route-validator-corpus.json agent/tests/test_route_manifest_parity.py web-nuxt/tests/launch-route-parity.test.ts nginx.conf nginx-ssl.conf
git commit -m "feat: classify launch routes consistently"
```

### Task 6: Create the canonical AI-disclosure artifact

**Files:**
- Create: `config/ai-disclosure.json`
- Create: `tests/launch_safety/test_ai_disclosure_artifact.py`

- [ ] **Step 1: Write the failing exact-copy test**

```python
import json
from pathlib import Path


def test_ai_disclosure_copy_is_exact():
    data = json.loads(Path("config/ai-disclosure.json").read_text(encoding="utf-8"))
    assert data["revision"] == "ai-disclosure-v1"
    assert data["entity_ai"]["short_label"] == "Minh họa AI"
    assert data["entity_ai"]["full_disclosure"] == "Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ."
    assert data["placeholder"]["full_disclosure"] == "Minh họa đồ họa — chưa có ảnh riêng cho địa điểm."
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_ai_disclosure_artifact.py -q`

Expected: FAIL because the canonical disclosure artifact does not exist.

- [ ] **Step 3: Add the exact reviewed disclosure data**

```json
{
  "schema_version": 1,
  "revision": "ai-disclosure-v1",
  "entity_ai": {
    "short_label": "Minh họa AI",
    "full_disclosure": "Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.",
    "accessible_description_key": "entity-ai-full"
  },
  "placeholder": {
    "short_label": null,
    "full_disclosure": "Minh họa đồ họa — chưa có ảnh riêng cho địa điểm.",
    "accessible_description_key": "entity-placeholder-full"
  },
  "ugc_photo": {
    "short_label": "Ảnh người dùng",
    "full_disclosure": "Ảnh do người dùng cung cấp.",
    "accessible_description_key": "ugc-photo-full"
  },
  "forbidden_entity_image_claims": [
    "ảnh thật",
    "real photo",
    "documentary photo",
    "on-site photo",
    "ảnh chụp tại chỗ"
  ]
}
```

The UGC sentence is intentionally distinct from the AI and placeholder copy and always appears with the available user credit.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest tests/launch_safety/test_ai_disclosure_artifact.py -q`

Expected: PASS with exact UTF-8 copy.

- [ ] **Step 5: Commit**

```bash
git add config/ai-disclosure.json tests/launch_safety/test_ai_disclosure_artifact.py
git commit -m "feat: add canonical AI disclosure copy"
```

### Task 7: Add the TypeScript disclosure loader

**Files:**
- Create: `web-nuxt/utils/aiDisclosure.ts`
- Create: `web-nuxt/tests/ai-disclosure.test.ts`
- Create: `tests/fixtures/ai-disclosure-validator-corpus.json`

- [ ] **Step 1: Write failing strict-loader tests**

```ts
import { describe, expect, it } from 'vitest'
import { parseAiDisclosure } from '../utils/aiDisclosure'

it('rejects altered canonical AI copy', () => {
  expect(() => parseAiDisclosure({
    schema_version: 1,
    revision: 'ai-disclosure-v1',
    entity_ai: { short_label: 'AI', full_disclosure: 'altered' },
  })).toThrow(/canonical AI disclosure/i)
})

it.each(loadDisclosureMutations())('rejects $name identically to Python', ({ apply, error }) => {
  const candidate = structuredClone(validDisclosure)
  apply(candidate)
  expect(() => parseAiDisclosure(candidate)).toThrow(error)
})
```

Create `tests/fixtures/ai-disclosure-validator-corpus.json` with these exact mutations:

```json
[
  {"name": "wrong-revision", "operation": "set", "pointer": "/revision", "value": "ai-disclosure-v0", "error": "revision"},
  {"name": "extra-root-key", "operation": "set", "pointer": "/extra", "value": true, "error": "root keys"},
  {"name": "missing-ugc", "operation": "delete", "pointer": "/ugc_photo", "error": "root keys"},
  {"name": "altered-ai-short", "operation": "set", "pointer": "/entity_ai/short_label", "value": "AI", "error": "entity_ai"},
  {"name": "altered-ai-full", "operation": "set", "pointer": "/entity_ai/full_disclosure", "value": "altered", "error": "entity_ai"},
  {"name": "altered-placeholder-full", "operation": "set", "pointer": "/placeholder/full_disclosure", "value": "altered", "error": "placeholder"},
  {"name": "altered-ugc-short", "operation": "set", "pointer": "/ugc_photo/short_label", "value": "photo", "error": "ugc_photo"},
  {"name": "altered-ugc-full", "operation": "set", "pointer": "/ugc_photo/full_disclosure", "value": "altered", "error": "ugc_photo"},
  {"name": "altered-accessibility-key", "operation": "set", "pointer": "/entity_ai/accessible_description_key", "value": "wrong", "error": "entity_ai"},
  {"name": "reordered-forbidden-claims", "operation": "reverse", "pointer": "/forbidden_entity_image_claims", "error": "forbidden claims"},
  {"name": "wrong-forbidden-type", "operation": "set", "pointer": "/forbidden_entity_image_claims", "value": "real photo", "error": "forbidden claims"}
]
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/ai-disclosure.test.ts`

Expected: FAIL because the loader does not exist.

- [ ] **Step 3: Implement immutable validated copy access**

```ts
import disclosureJson from '#launch-config/ai-disclosure.json'

const AI_FULL = 'Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.'
const PLACEHOLDER_FULL = 'Minh họa đồ họa — chưa có ảnh riêng cho địa điểm.'

const aiDisclosureCanonicalCopy = Object.freeze({
  entity_ai: Object.freeze({
    short_label: '\u004d\u0069\u006e\u0068\u0020\u0068\u1ecda\u0020\u0041\u0049',
    full_disclosure: '\u1ea2nh minh h\u1ecda do AI d\u1ef1ng \u2014 kh\u00f4ng ph\u1ea3i \u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7.',
    accessible_description_key: 'entity-ai-full',
  }),
  placeholder: Object.freeze({
    short_label: null,
    full_disclosure: 'Minh h\u1ecda \u0111\u1ed3 h\u1ecda \u2014 ch\u01b0a c\u00f3 \u1ea3nh ri\u00eang cho \u0111\u1ecba \u0111i\u1ec3m.',
    accessible_description_key: 'entity-placeholder-full',
  }),
  ugc_photo: Object.freeze({
    short_label: '\u1ea2nh ng\u01b0\u1eddi d\u00f9ng',
    full_disclosure: '\u1ea2nh do ng\u01b0\u1eddi d\u00f9ng cung c\u1ea5p.',
    accessible_description_key: 'ugc-photo-full',
  }),
  forbidden_entity_image_claims: Object.freeze([
    '\u1ea3nh th\u1eadt', 'real photo', 'documentary photo', 'on-site photo', '\u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7',
  ]),
})
const UGC_FULL = aiDisclosureCanonicalCopy.ugc_photo.full_disclosure
const EXPECTED_REVISION = 'ai-disclosure-v1'
const EXPECTED_FORBIDDEN = aiDisclosureCanonicalCopy.forbidden_entity_image_claims

function asRecord(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`canonical AI disclosure ${label} mismatch`)
  return value as Record<string, unknown>
}

function assertExactKeys(value: Record<string, unknown>, expected: string[], label: string) {
  const actual = Object.keys(value).sort()
  if (actual.join('\0') !== [...expected].sort().join('\0')) throw new Error(`canonical AI disclosure ${label} keys mismatch`)
}

function parseExactCopy(value: unknown, expected: Readonly<Record<string, unknown>>, label: string) {
  const copy = asRecord(value, label)
  assertExactKeys(copy, ['short_label', 'full_disclosure', 'accessible_description_key'], label)
  if (Object.entries(expected).some(([key, expectedValue]) => copy[key] !== expectedValue)) {
    throw new Error(`canonical AI disclosure ${label} mismatch`)
  }
  return { ...copy }
}

function deepFreeze<T>(value: T): Readonly<T> {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value)
    for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child)
  }
  return value
}

export interface AiDisclosureArtifact {
  schema_version: 1
  revision: string
  entity_ai: { short_label: 'Minh họa AI'; full_disclosure: typeof AI_FULL; accessible_description_key: string }
  placeholder: { short_label: null; full_disclosure: typeof PLACEHOLDER_FULL; accessible_description_key: string }
  ugc_photo: { short_label: string; full_disclosure: string; accessible_description_key: string }
  forbidden_entity_image_claims: string[]
}

export function parseAiDisclosure(value: unknown): Readonly<AiDisclosureArtifact> {
  const data = asRecord(value, 'root')
  assertExactKeys(data, ['schema_version', 'revision', 'entity_ai', 'placeholder', 'ugc_photo', 'forbidden_entity_image_claims'], 'root')
  if (data.schema_version !== 1 || data.revision !== EXPECTED_REVISION) throw new Error('canonical AI disclosure revision mismatch')
  const entity = parseExactCopy(data.entity_ai, {
    short_label: aiDisclosureCanonicalCopy.entity_ai.short_label,
    full_disclosure: AI_FULL,
    accessible_description_key: 'entity-ai-full',
  }, 'entity_ai')
  const placeholder = parseExactCopy(data.placeholder, {
    short_label: null,
    full_disclosure: PLACEHOLDER_FULL,
    accessible_description_key: 'entity-placeholder-full',
  }, 'placeholder')
  const ugc = parseExactCopy(data.ugc_photo, {
    short_label: aiDisclosureCanonicalCopy.ugc_photo.short_label,
    full_disclosure: UGC_FULL,
    accessible_description_key: 'ugc-photo-full',
  }, 'ugc_photo')
  if (!Array.isArray(data.forbidden_entity_image_claims) ||
      JSON.stringify(data.forbidden_entity_image_claims) !== JSON.stringify(EXPECTED_FORBIDDEN)) {
    throw new Error('canonical AI disclosure forbidden claims mismatch')
  }
  return deepFreeze({
    schema_version: 1,
    revision: EXPECTED_REVISION,
    entity_ai: entity,
    placeholder,
    ugc_photo: ugc,
    forbidden_entity_image_claims: [...EXPECTED_FORBIDDEN],
  }) as Readonly<AiDisclosureArtifact>
}

export const aiDisclosure = parseAiDisclosure(disclosureJson)
```

The shared JSON mutation corpus covers missing/extra root keys, wrong revision, altered AI/placeholder/UGC short and full copy, altered accessibility keys, reordered/added forbidden claims, and wrong scalar/array types. Task 8 applies the same corpus in Python.

- [ ] **Step 4: Run GREEN and typecheck**

Run: `cd web-nuxt && npm test -- --run tests/ai-disclosure.test.ts && npm run typecheck`

Expected: tests and typecheck pass.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/utils/aiDisclosure.ts web-nuxt/tests/ai-disclosure.test.ts tests/fixtures/ai-disclosure-validator-corpus.json
git commit -m "feat: load AI disclosure copy in Nuxt"
```

### Task 8: Add the Python disclosure loader

**Files:**
- Create: `agent/ai_disclosure.py`
- Create: `agent/tests/test_ai_disclosure.py`
- Modify: `tests/launch_safety/test_release_package.py`

- [ ] **Step 1: Write failing exact-copy and fixture tests**

```python
import copy
import json
from pathlib import Path
import tarfile

import pytest

from ai_disclosure import load_ai_disclosure
from route_manifest import load_route_manifest
from scripts.package_launch_release import build_backend_archive


def test_loads_exact_canonical_copy():
    disclosure = load_ai_disclosure()
    assert disclosure.entity_ai.full_disclosure == "Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ."


def test_rejects_altered_copy(tmp_path: Path):
    fixture = tmp_path / "ai.json"
    fixture.write_text('{"schema_version":1,"revision":"r","entity_ai":{"full_disclosure":"altered"}}')
    with pytest.raises(ValueError, match="canonical AI disclosure"):
        load_ai_disclosure(fixture_path=fixture)


def test_disclosure_release_root_and_fixture_path_are_mutually_exclusive(tmp_path: Path):
    with pytest.raises(ValueError, match="mutually exclusive"):
        load_ai_disclosure(release_root=tmp_path, fixture_path=tmp_path / "ai.json")


def test_python_applies_the_shared_strict_disclosure_corpus(valid_disclosure, disclosure_mutations, tmp_path: Path):
    for mutation in disclosure_mutations:
        candidate = copy.deepcopy(valid_disclosure)
        apply_json_mutation(candidate, mutation)
        fixture = tmp_path / f"{mutation['name']}.json"
        fixture.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(ValueError, match=mutation["error"]):
            load_ai_disclosure(fixture_path=fixture)


def test_unpacked_release_loaders_read_exact_packaged_bytes(tmp_path: Path):
    archive = build_backend_archive(REPO_ROOT, tmp_path / "backend.tar.gz")
    release_root = tmp_path / "release"
    with tarfile.open(archive, "r:gz") as bundle:
        bundle.extractall(release_root, filter="data")

    route = load_route_manifest(release_root=release_root)
    disclosure = load_ai_disclosure(release_root=release_root)

    assert route.artifact.path == release_root / "config/launch-indexing-policy.json"
    assert disclosure.artifact.path == release_root / "config/ai-disclosure.json"
    assert route.artifact.raw == (REPO_ROOT / "config/launch-indexing-policy.json").read_bytes()
    assert disclosure.artifact.raw == (REPO_ROOT / "config/ai-disclosure.json").read_bytes()


def test_low_level_artifact_loader_has_no_domain_import_cycle():
    source = Path("agent/launch_artifacts.py").read_text(encoding="utf-8")
    assert "import route_manifest" not in source
    assert "from route_manifest" not in source
    assert "import ai_disclosure" not in source
    assert "from ai_disclosure" not in source
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_ai_disclosure.py tests/launch_safety/test_release_package.py -q`

Expected: FAIL because the Python disclosure loader does not exist.

- [ ] **Step 3: Implement frozen disclosure records**

```python
from dataclasses import dataclass
from pathlib import Path

from launch_artifacts import LoadedArtifact, load_artifact


@dataclass(frozen=True)
class DisclosureCopy:
    short_label: str | None
    full_disclosure: str
    accessible_description_key: str


@dataclass(frozen=True)
class LoadedAiDisclosure:
    artifact: LoadedArtifact
    revision: str
    entity_ai: DisclosureCopy
    placeholder: DisclosureCopy
    ugc_photo: DisclosureCopy
    forbidden_entity_image_claims: tuple[str, ...]


def canonical_disclosure_copy() -> dict:
    return {
        "entity_ai": {
            "short_label": "\u004d\u0069\u006e\u0068\u0020\u0068\u1ecda\u0020\u0041\u0049",
            "full_disclosure": "\u1ea2nh minh h\u1ecda do AI d\u1ef1ng \u2014 kh\u00f4ng ph\u1ea3i \u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7.",
            "accessible_description_key": "entity-ai-full",
        },
        "placeholder": {
            "short_label": None,
            "full_disclosure": "Minh h\u1ecda \u0111\u1ed3 h\u1ecda \u2014 ch\u01b0a c\u00f3 \u1ea3nh ri\u00eang cho \u0111\u1ecba \u0111i\u1ec3m.",
            "accessible_description_key": "entity-placeholder-full",
        },
        "ugc_photo": {
            "short_label": "\u1ea2nh ng\u01b0\u1eddi d\u00f9ng",
            "full_disclosure": "\u1ea2nh do ng\u01b0\u1eddi d\u00f9ng cung c\u1ea5p.",
            "accessible_description_key": "ugc-photo-full",
        },
        "forbidden_entity_image_claims": [
            "\u1ea3nh th\u1eadt", "real photo", "documentary photo", "on-site photo", "\u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7",
        ],
    }


def load_ai_disclosure(*, release_root: Path | None = None, fixture_path: Path | None = None) -> LoadedAiDisclosure:
    artifact = load_artifact(
        "ai-disclosure.json",
        release_root=release_root,
        fixture_path=fixture_path,
    )
    data = artifact.data
    expected_copy = canonical_disclosure_copy()
    if set(data) != {"schema_version", "revision", "entity_ai", "placeholder", "ugc_photo", "forbidden_entity_image_claims"}:
        raise ValueError("canonical AI disclosure root keys mismatch")
    if data.get("schema_version") != 1 or data.get("revision") != "ai-disclosure-v1":
        raise ValueError("canonical AI disclosure revision mismatch")
    for name in ("entity_ai", "placeholder", "ugc_photo"):
        value = data.get(name)
        if not isinstance(value, dict) or set(value) != {"short_label", "full_disclosure", "accessible_description_key"}:
            raise ValueError(f"canonical AI disclosure {name} keys mismatch")
        if value != expected_copy[name]:
            raise ValueError(f"canonical AI disclosure {name} mismatch")
    if data.get("forbidden_entity_image_claims") != expected_copy["forbidden_entity_image_claims"]:
        raise ValueError("canonical AI disclosure forbidden claims mismatch")
    if data.get("schema_version") != 1:
        raise ValueError("unsupported AI disclosure schema")
    if data.get("entity_ai", {}).get("full_disclosure") != "Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.":
        raise ValueError("canonical AI disclosure mismatch")
    return LoadedAiDisclosure(
        artifact=artifact,
        revision=data["revision"],
        entity_ai=DisclosureCopy(**data["entity_ai"]),
        placeholder=DisclosureCopy(**data["placeholder"]),
        ugc_photo=DisclosureCopy(**data["ugc_photo"]),
        forbidden_entity_image_claims=tuple(data["forbidden_entity_image_claims"]),
    )
```

- [ ] **Step 4: Run GREEN and Ruff**

Run: `python -m pytest agent/tests/test_ai_disclosure.py tests/launch_safety/test_release_package.py -q`

Run: `python -m ruff check agent/ai_disclosure.py agent/tests/test_ai_disclosure.py`

Expected: strict AI/placeholder/UGC/revision parity, mutual-exclusive path injection, exact unpacked release bytes for both loaders, and Ruff all pass. Importing `launch_artifacts` alone does not import `route_manifest` or `ai_disclosure`, proving the low-level loader has no circular dependency.

- [ ] **Step 5: Commit**

```bash
git add agent/ai_disclosure.py agent/tests/test_ai_disclosure.py tests/launch_safety/test_release_package.py
git commit -m "feat: load AI disclosure copy in Python"
```

## Phase 2: Backend Indexability and HTTP Policy Authority

### Task 9: Implement the non-place entity indexability authority

**Files:**
- Create: `agent/launch_evidence.py`
- Create: `agent/index_policy.py`
- Create: `agent/tests/test_index_policy.py`
- Create: `tests/fixtures/launch-policy-fingerprint.json`
- Modify: `agent/seo.py:1178-1215`
- Modify: `scripts/checks/check_data_schema.py:139`
- Modify: `tests/checks/test_hard_checks.py:123`

- [ ] **Step 1: Write failing entity-policy tests**

```python
from index_policy import decide_entity
from launch_evidence import PolicyEvidence

EVIDENCE = PolicyEvidence(
    policy_fingerprint="a" * 64,
    route_manifest_revision="launch-indexing-policy-v1",
    backend_policy_revision="index-policy-v1",
)


def test_entity_requires_public_eligibility_and_130_words():
    entity = {
        "id": "thin",
        "type": "attraction",
        "status": "published",
        "verified": True,
        "summary": " ".join(["word"] * 129),
        "description": "",
        "images": ["/img/ai.webp"],
    }
    decision = decide_entity(entity, EVIDENCE)
    assert decision.indexable is False
    assert "description-below-130-words" in decision.reasons

    entity["summary"] += " word"
    assert decide_entity(entity, EVIDENCE).indexable is True


def test_ai_images_never_restore_the_old_100_word_branch():
    entity = {
        "id": "ai-only",
        "type": "attraction",
        "status": "published",
        "verified": True,
        "summary": " ".join(["word"] * 100),
        "images": ["/img/ai-1.webp", "/img/ai-2.webp"],
    }
    assert decide_entity(entity, EVIDENCE).indexable is False


@pytest.mark.parametrize("entity", [
    {},
    {"status": "published", "verified": None},
    {"status": "provisional", "verified": True},
    {"status": "private", "verified": True},
    {"status": "draft", "verified": True},
    {"status": "unpublished", "verified": True},
    {"status": "published", "verified": False},
    {"status": "published", "verified": True, "is_private": True},
    {"status": "published", "verified": True, "is_public": False},
    {"status": "published", "verified": True, "published": False},
])
def test_missing_private_draft_unpublished_and_unverified_entities_are_ineligible(entity):
    entity.update(summary=" ".join(["word"] * 130), description="")
    decision = decide_entity(entity, EVIDENCE)
    assert decision.indexable is False
    assert any(reason.startswith("public-") for reason in decision.reasons)


def test_fingerprint_hashes_both_artifact_revisions_digests_and_semantic_revisions(fingerprint_fixture):
    assert build_policy_fingerprint(**fingerprint_fixture["inputs"]) == fingerprint_fixture["expected_sha256"]
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_index_policy.py tests/checks/test_hard_checks.py -q`

Expected: FAIL because `index_policy` does not exist and hard check R10.8 still imports `seo.is_index_worthy`.

- [ ] **Step 3: Implement reviewed evidence and the sole entity predicate**

```python
# agent/launch_evidence.py
from dataclasses import dataclass
from hashlib import sha256
import json

from ai_disclosure import load_ai_disclosure
from route_manifest import load_route_manifest

INDEX_POLICY_REVISION = "index-policy-v1"
RESPONSE_MATRIX_REVISION = "launch-safety-matrix-v1"
CACHE_ISOLATION_REVISION = "launch-cache-isolation-v1"
SITEMAP_PROTOCOL_REVISION = "pinned-sitemap-bundle-v1"


def build_policy_fingerprint(
    *,
    route_revision: str,
    route_digest: str,
    disclosure_revision: str,
    disclosure_digest: str,
) -> str:
    payload = {
        "index_policy": INDEX_POLICY_REVISION,
        "response_matrix": RESPONSE_MATRIX_REVISION,
        "cache_isolation": CACHE_ISOLATION_REVISION,
        "sitemap_protocol": SITEMAP_PROTOCOL_REVISION,
        "route_artifact": {"revision": route_revision, "sha256": route_digest},
        "disclosure_artifact": {"revision": disclosure_revision, "sha256": disclosure_digest},
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class PolicyEvidence:
    policy_fingerprint: str
    route_manifest_revision: str
    backend_policy_revision: str


def current_policy_evidence() -> PolicyEvidence:
    route = load_route_manifest()
    disclosure = load_ai_disclosure()
    return PolicyEvidence(
        policy_fingerprint=build_policy_fingerprint(
            route_revision=route.revision,
            route_digest=route.artifact.sha256,
            disclosure_revision=disclosure.revision,
            disclosure_digest=disclosure.artifact.sha256,
        ),
        route_manifest_revision=route.revision,
        backend_policy_revision=INDEX_POLICY_REVISION,
    )
```

```python
# agent/index_policy.py
from dataclasses import dataclass
import re
from typing import Mapping

from launch_evidence import PolicyEvidence


@dataclass(frozen=True)
class IndexPolicyDecision:
    kind: str
    indexable: bool
    reasons: tuple[str, ...]
    policy_fingerprint: str
    policy_revision: str


PUBLIC_STATUSES = frozenset({"published", "verified"})


def public_eligibility_reasons(entity: Mapping[str, object]) -> tuple[str, ...]:
    reasons: list[str] = []
    status = entity.get("status")
    if status is None:
        reasons.append("public-status-missing")
    elif status not in PUBLIC_STATUSES:
        reasons.append("public-status-not-allowlisted")
    verified = entity.get("verified")
    if verified is None:
        reasons.append("public-verification-missing")
    elif verified not in (True, 1):
        reasons.append("public-explicitly-unverified")
    if entity.get("is_private") is True or entity.get("visibility") == "private":
        reasons.append("public-private-content")
    if entity.get("is_public") is False or entity.get("published") is False:
        reasons.append("public-unpublished-content")
    return tuple(reasons)


def is_publicly_eligible(entity: Mapping[str, object]) -> bool:
    return not public_eligibility_reasons(entity)


def _descriptive_word_count(entity: Mapping[str, object]) -> int:
    summary = str(entity.get("summary") or "").strip()
    description = str(entity.get("description") or "").strip()
    parts = [summary]
    if description.casefold() != summary.casefold():
        parts.append(description)
    return len(re.findall(r"\b\w+\b", " ".join(parts), flags=re.UNICODE))


def decide_entity(entity: Mapping[str, object], evidence: PolicyEvidence) -> IndexPolicyDecision:
    reasons = list(public_eligibility_reasons(entity))
    if _descriptive_word_count(entity) < 130:
        reasons.append("description-below-130-words")
    return IndexPolicyDecision("entity", not reasons, tuple(reasons), evidence.policy_fingerprint, evidence.backend_policy_revision)
```

Create the shared fingerprint fixture with exact content:

```json
{
  "inputs": {
    "route_revision": "launch-indexing-policy-v1",
    "route_digest": "1111111111111111111111111111111111111111111111111111111111111111",
    "disclosure_revision": "ai-disclosure-v1",
    "disclosure_digest": "2222222222222222222222222222222222222222222222222222222222222222"
  },
  "semantic_revisions": {
    "index_policy": "index-policy-v1",
    "response_matrix": "launch-safety-matrix-v1",
    "cache_isolation": "launch-cache-isolation-v1",
    "sitemap_protocol": "pinned-sitemap-bundle-v1"
  },
  "expected_sha256": "6397813fbaafc0800f0d1cadb87214b3d250c72bc03b5a15a7386ba979b2926e"
}
```

Delete the old 100-words-plus-image branch and every legacy permissive `_is_public`/`is_index_worthy` quality decision from `agent/seo.py`; retarget the data-schema hard check to `index_policy.decide_entity`. Listing visibility may retain a separately named compatibility filter, but entity/ward indexability and sitemap child eligibility may call only `is_publicly_eligible()`, `decide_entity()`, or `decide_ward()` from `index_policy`.

- [ ] **Step 4: Run GREEN and focused SEO regressions**

Run: `python -m pytest agent/tests/test_index_policy.py tests/checks/test_hard_checks.py agent/tests/test_seo.py -q`

Run: `python -m ruff check agent/launch_evidence.py agent/index_policy.py scripts/checks/check_data_schema.py agent/tests/test_index_policy.py`

Expected: tests pass with the obsolete image-credit assertions replaced by zero-credit AI assertions.

- [ ] **Step 5: Commit**

```bash
git add agent/launch_evidence.py agent/index_policy.py agent/tests/test_index_policy.py tests/fixtures/launch-policy-fingerprint.json agent/seo.py scripts/checks/check_data_schema.py tests/checks/test_hard_checks.py agent/tests/test_seo.py
git commit -m "feat: centralize entity index policy"
```

### Task 10: Add ward policy and fixed itinerary/share exclusions

**Files:**
- Modify: `agent/index_policy.py`
- Modify: `agent/tests/test_index_policy.py`
- Modify: `agent/seo.py:1322-1405`

- [ ] **Step 1: Write failing ward and fixed-negative tests**

```python
from index_policy import decide_itinerary, decide_ward


def test_ward_requires_two_public_children_or_60_summary_words():
    ward = {"id": "ward", "type": "place", "status": "published", "verified": True, "summary": "short"}
    assert decide_ward(ward, public_child_count=1, evidence=EVIDENCE).indexable is False
    assert decide_ward(ward, public_child_count=2, evidence=EVIDENCE).indexable is True
    ward["summary"] = " ".join(["word"] * 60)
    assert decide_ward(ward, public_child_count=0, evidence=EVIDENCE).indexable is True


def test_itinerary_and_shared_plan_are_fixed_negative():
    assert decide_itinerary(shared_plan=False, evidence=EVIDENCE).indexable is False
    assert decide_itinerary(shared_plan=True, evidence=EVIDENCE).indexable is False
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_index_policy.py -q`

Expected: FAIL because ward and itinerary decision functions do not exist.

- [ ] **Step 3: Implement the per-kind rules and remove unconditional itinerary sitemap emission**

```python
def decide_ward(ward: Mapping[str, object], *, public_child_count: int, evidence: PolicyEvidence) -> IndexPolicyDecision:
    reasons = list(public_eligibility_reasons(ward))
    summary_words = len(re.findall(r"\b\w+\b", str(ward.get("summary") or ""), flags=re.UNICODE))
    if public_child_count <= 1 and summary_words < 60:
        reasons.append("ward-below-child-and-summary-threshold")
    return IndexPolicyDecision("ward", not reasons, tuple(reasons), evidence.policy_fingerprint, evidence.backend_policy_revision)


def decide_itinerary(*, shared_plan: bool, evidence: PolicyEvidence) -> IndexPolicyDecision:
    reason = "shared-plan-fixed-noindex" if shared_plan else "itinerary-fixed-noindex"
    return IndexPolicyDecision("itinerary", False, (reason,), evidence.policy_fingerprint, evidence.backend_policy_revision)
```

Remove existing unconditional itinerary URLs from legacy sitemap construction; Tasks 17–19 will replace the remaining sitemap implementation.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_index_policy.py agent/tests/test_seo.py -q`

Expected: ward thresholds pass and itinerary/share URLs are no longer eligible.

- [ ] **Step 5: Commit**

```bash
git add agent/index_policy.py agent/tests/test_index_policy.py agent/seo.py
git commit -m "feat: add ward and fixed noindex policy"
```

### Task 11: Serialize mandatory entity/ward policy decisions

**Files:**
- Modify: `agent/api_schemas.py:107-220`
- Modify: `agent/public_api.py:1212-1265`
- Create: `agent/tests/test_public_index_policy.py`

- [ ] **Step 1: Write failing response-contract tests**

```python
from fastapi.testclient import TestClient


def test_entity_detail_contains_mandatory_boolean_policy(client: TestClient):
    response = client.get("/api/entities/public-entity")
    assert response.status_code == 200
    policy = response.json()["index_policy"]
    assert isinstance(policy["indexable"], bool)
    assert policy["kind"] == "entity"
    assert len(policy["policy_fingerprint"]) == 64
    assert policy["policy_revision"] == "index-policy-v1"


def test_place_entity_uses_ward_policy(client: TestClient):
    response = client.get("/api/entities/public-ward")
    assert response.json()["index_policy"]["kind"] == "ward"
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_public_index_policy.py -q`

Expected: FAIL because entity responses do not include `index_policy`.

- [ ] **Step 3: Add strict response models and compute the decision once**

```python
# agent/api_schemas.py
class IndexPolicyDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["entity", "ward", "itinerary"]
    indexable: bool
    reasons: list[str]
    policy_fingerprint: str
    policy_revision: str


class EntityDetailResponse(ApiModel):
    id: str | None = None
    type: str | None = None
    name: str | None = None
    summary: str | None = None
    description: str | None = None
    relationship_total: int | None = None
    index_policy: IndexPolicyDecisionResponse
```

In `get_entity()`, load current route/disclosure evidence, choose `decide_ward()` when `entity["type"] == "place"`, otherwise choose `decide_entity()`, and serialize the dataclass under `index_policy`. Count only public-eligible ward children through one database helper.

- [ ] **Step 4: Run GREEN and nearby API tests**

Run: `python -m pytest agent/tests/test_public_index_policy.py agent/tests/test_integration_api.py agent/tests/test_session_be.py -q`

Expected: policy fields are mandatory and existing public response fields remain compatible.

- [ ] **Step 5: Commit**

```bash
git add agent/api_schemas.py agent/public_api.py agent/tests/test_public_index_policy.py
git commit -m "feat: expose entity index policy decisions"
```

### Task 12: Enforce the exact FastAPI no-store endpoint registry

**Files:**
- Create: `agent/policy_http.py`
- Create: `agent/tests/test_policy_http.py`
- Create: `scripts/checks/check_policy_http_registry.py`
- Create: `tests/launch_safety/test_policy_http_registry_guard.py`
- Modify: `scripts/checks/run_hard.py`
- Modify: `agent/public_api.py:68-80`
- Modify: `agent/public_api.py:1212-1265`
- Modify: `agent/server.py:1085-1330`
- Modify: `agent/tests/test_gap_fixes.py:1862`

- [ ] **Step 1: Write failing no-store, no-validator, and fresh-input tests**

```python
def test_entity_detail_never_returns_304(client):
    first = client.get("/api/entities/public-entity")
    second = client.get("/api/entities/public-entity", headers={"If-None-Match": first.headers.get("etag", "legacy")})
    assert first.headers["cache-control"] == "no-store"
    assert "etag" not in first.headers
    assert "last-modified" not in first.headers
    assert second.status_code == 200
    assert second.headers["cache-control"] == "no-store"


def test_direct_database_change_is_visible_without_invalidation_hook(client, db):
    before = client.get("/api/entities/public-entity").json()["index_policy"]
    db.execute_direct("UPDATE entities SET summary = '' WHERE id = %s", ("public-entity",))
    after = client.get("/api/entities/public-entity").json()["index_policy"]
    assert before["indexable"] is True
    assert after["indexable"] is False


@pytest.mark.parametrize("case,expected_status", [
    ("success", 200),
    ("not-found", 404),
    ("validation", 422),
    ("dependency-failure", 503),
])
def test_registered_route_contract_covers_every_response_path(policy_test_client, case, expected_status):
    response = policy_test_client.get(policy_case_url(case), headers={"If-None-Match": '"legacy"'})
    assert response.status_code == expected_status
    assert response.status_code != 304
    assert response.headers["cache-control"] == "no-store"
    assert not ({"etag", "last-modified", "expires"} & {name.lower() for name in response.headers})


def test_policy_route_scanner_rejects_unregistered_evidence_route(tmp_path):
    source = tmp_path / "unregistered.py"
    source.write_text('''
@router.get("/new-policy")
def new_policy():
    return {"indexable": False, "policy_fingerprint": "a" * 64, "policy_revision": "index-policy-v1"}
''', encoding="utf-8")
    assert scan_policy_routes([source], POLICY_ENDPOINTS)[0].code == "UNREGISTERED_POLICY_ROUTE"
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_policy_http.py agent/tests/test_gap_fixes.py -q`

Expected: FAIL because `/api/entities/{entity_id}` still emits public cache headers, ETag, and 304, can replay a full cached entity, and no scanner proves every policy/evidence route is registered.

- [ ] **Step 3: Implement resolved-route registry enforcement and remove policy-input memoization**

```python
# agent/policy_http.py
from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyEndpoint:
    method: str
    path: str
    route_name: str
    exposure: str
    cache_contract: str = "no-store-no-validator"


POLICY_ENDPOINTS = (
    PolicyEndpoint("GET", "/api/entities/{entity_id}", "get_entity", "public"),
    PolicyEndpoint("GET", "/_internal/launch-policy-attestation", "launch_policy_attestation", "internal"),
    PolicyEndpoint("GET", "/_internal/launch-sitemaps/{document}", "launch_sitemap_document", "internal"),
)


def enforce_policy_http_headers(response):
    response.headers["Cache-Control"] = "no-store"
    for name in ("ETag", "Last-Modified", "Expires"):
        response.headers.pop(name, None)
    return response
```

Install an ASGI response-start wrapper after all FastAPI routers are mounted. It reads the resolved `scope["route"].path`, method, and route name; only an exact `PolicyEndpoint` identity receives `Cache-Control: no-store` and validator removal. This covers handler success, handler-raised 404/503, request validation 422, and application error responses because headers are normalized at `http.response.start`, not only inside successful handlers. A focused test app mounts the exact registered identities with an integer path parameter to force 422 and explicit 404/503 branches. The production handler removes its ETag/`If-None-Match` branch, so 304 cannot be emitted; the wrapper raises a test-visible contract error if a registered response attempts status 304.

`scripts/checks/check_policy_http_registry.py` parses every FastAPI-decorated function under `agent/` and marks a route policy-bearing when its AST contains `IndexPolicyDecision`, `current_policy_evidence`, `policy_fingerprint`, `policy_revision`, `route_manifest_revision`, `backend_policy_revision`, `index_policy`, or sitemap evidence/header names. It joins router prefixes from `include_router()` declarations, compares method/path/function name with `POLICY_ENDPOINTS`, and emits `UNREGISTERED_POLICY_ROUTE`, `STALE_POLICY_REGISTRY_ENTRY`, or `POLICY_ROUTE_CONTRACT_MISMATCH`. Until Tasks 13 and 17 create the two internal routes, their registry rows are allowed only as declared future entries; the scanner still requires every currently discovered policy route to be registered. Task 13 and Task 17 each remove one future allowance, and Task 17's GREEN command requires zero future entries.

Match the resolved FastAPI route template, not the lexical URL, so `/api/entities/map` and other static routes keep their existing reviewed cache behavior. Remove `_entity_cache` from the policy-bearing detail handler; load policy-input fields from the database on every request. If presentation-only memoization remains, exclude `status`, `verified`, summary, description, type, relationships, ward-child counts, and every policy/evidence field.

- [ ] **Step 4: Run GREEN and registry source scan**

Run: `python -m pytest agent/tests/test_policy_http.py agent/tests/test_public_index_policy.py agent/tests/test_gap_fixes.py tests/launch_safety/test_policy_http_registry_guard.py -q`

Run: `python scripts/checks/check_policy_http_registry.py --allow-future launch_policy_attestation --allow-future launch_sitemap_document`

Expected: every success/error/validation/not-found status from the registered detail route is `no-store`, has no validator, never returns 304, observes direct DB policy-input changes, and every discovered policy/evidence route matches the exact registry.

- [ ] **Step 5: Commit**

```bash
git add agent/policy_http.py agent/tests/test_policy_http.py agent/public_api.py agent/server.py agent/tests/test_gap_fixes.py scripts/checks/check_policy_http_registry.py tests/launch_safety/test_policy_http_registry_guard.py scripts/checks/run_hard.py
git commit -m "fix: prevent caching policy-bearing API responses"
```

### Task 13: Add the internal policy-attestation endpoint

**Files:**
- Create: `agent/launch_policy_api.py`
- Create: `agent/tests/test_launch_policy_api.py`
- Create: `tests/launch_safety/test_nginx_contract.py`
- Modify: `agent/server.py:990-1140`
- Modify: `nginx.conf`
- Modify: `nginx-ssl.conf`
- Modify: `docs/api-contract.md:215`

- [ ] **Step 1: Write failing attestation and non-exposure tests**

```python
def test_internal_attestation_returns_exact_evidence(client):
    response = client.get("/_internal/launch-policy-attestation")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "etag" not in response.headers
    assert response.json() == {
        "policy_fingerprint": EXPECTED_FINGERPRINT,
        "route_manifest_revision": "launch-indexing-policy-v1",
        "backend_policy_revision": "index-policy-v1",
    }
```

Add a static Nginx assertion that no location proxies `/_internal/launch-policy-attestation` publicly.

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_launch_policy_api.py tests/launch_safety/test_nginx_contract.py -q`

Expected: FAIL because the internal router and deny contract do not exist.

- [ ] **Step 3: Implement the internal router and register it**

```python
from fastapi import APIRouter

from launch_evidence import current_policy_evidence

router = APIRouter(prefix="/_internal", include_in_schema=False)


@router.get("/launch-policy-attestation")
def launch_policy_attestation() -> dict[str, str]:
    evidence = current_policy_evidence()
    return {
        "policy_fingerprint": evidence.policy_fingerprint,
        "route_manifest_revision": evidence.route_manifest_revision,
        "backend_policy_revision": evidence.backend_policy_revision,
    }
```

Mount the router near the other FastAPI routers and ensure `policy_http` applies the internal no-store registry to validation and error responses.

Add an exact public boundary in both Nginx configs before every catch-all/backend regex:

```nginx
location ^~ /_internal/ {
    return 404;
}
```

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_launch_policy_api.py agent/tests/test_policy_http.py -q`

Run: `python scripts/checks/check_policy_http_registry.py --allow-future launch_sitemap_document`

Expected: attestation returns exact evidence with no cache validators, is absent from public API docs, and its previously future registry row now resolves to the exact mounted FastAPI route identity.

- [ ] **Step 5: Commit**

```bash
git add agent/launch_policy_api.py agent/tests/test_launch_policy_api.py agent/server.py nginx.conf nginx-ssl.conf docs/api-contract.md tests/launch_safety/test_nginx_contract.py
git commit -m "feat: expose internal launch policy attestation"
```

## Phase 3: Authoritative Snapshot and Immutable Sitemap Bundles

### Task 14: Read one authoritative sitemap snapshot

**Files:**
- Create: `agent/sitemap_snapshot.py`
- Create: `agent/tests/test_sitemap_snapshot.py`
- Modify: `agent/database.py:400-1015`

- [ ] **Step 1: Write failing same-transaction tests**

```python
def test_snapshot_uses_one_repeatable_read_connection(fake_db):
    snapshot = load_sitemap_snapshot(fake_db)
    assert fake_db.executed[0] == "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    assert snapshot.connection_ids == (fake_db.connection_id,)
    assert snapshot.entities
    assert snapshot.relationships
    assert snapshot.wards
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_sitemap_snapshot.py -q`

Expected: FAIL because current entity, relationship, and itinerary reads use separate connections.

- [ ] **Step 3: Implement one snapshot context and typed data**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class SitemapSnapshot:
    entities: tuple[dict, ...]
    relationships: tuple[dict, ...]
    wards: tuple[dict, ...]


def load_sitemap_snapshot(database) -> SitemapSnapshot:
    with database._conn(autocommit=False) as conn:
        database._execute(conn, "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY", ())
        entities = tuple(database._row_to_dict(row) for row in database._fetchall(conn, "SELECT * FROM entities", ()))
        relationships = tuple(database._row_to_dict(row) for row in database._fetchall(conn, "SELECT * FROM relationships", ()))
        wards = tuple(entity for entity in entities if entity.get("type") == "place")
        conn.rollback()
    return SitemapSnapshot(entities, relationships, wards)
```

Add the minimum database connection option needed to suppress the current auto-commit behavior without changing unrelated callers.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_sitemap_snapshot.py agent/tests/test_database.py -q`

Expected: focused snapshot and database regressions pass.

- [ ] **Step 5: Commit**

```bash
git add agent/sitemap_snapshot.py agent/tests/test_sitemap_snapshot.py agent/database.py
git commit -m "feat: read one sitemap database snapshot"
```

### Task 15: Publish immutable sitemap bundles atomically

**Files:**
- Create: `agent/sitemap_store.py`
- Create: `agent/tests/test_sitemap_store.py`
- Reuse: `agent/versioned_json_store.py:33-128`

- [ ] **Step 1: Write failing atomic-publication and retention tests**

```python
def test_failed_publish_keeps_previous_active_bundle(tmp_path):
    store = SitemapBundleStore(tmp_path)
    store.publish(bundle("a" * 64))
    store._write_active_pointer = lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk failure"))
    with pytest.raises(OSError):
        store.publish(bundle("b" * 64))
    assert store.load_active().batch_revision == "a" * 64


def test_cleanup_keeps_active_and_previous(tmp_path, clock):
    store = SitemapBundleStore(tmp_path, now=clock.now)
    store.publish(bundle("a" * 64))
    clock.advance(hours=25)
    store.publish(bundle("b" * 64))
    store.cleanup()
    assert store.list_batches() == ("a" * 64, "b" * 64)


def test_production_defaults_and_restart_protocol(release_root, clock):
    store = SitemapBundleStore.from_release_root(release_root, now=clock.now)
    assert store.root == release_root / "agent/data/sitemap-bundles"
    assert store.retention == timedelta(hours=24)
    store.publish(bundle("a" * 64))

    restarted = SitemapBundleStore.from_release_root(release_root, now=clock.now)
    assert restarted.load_active_on_startup().batch_revision == "a" * 64
    assert not hasattr(restarted, "refresh")


def test_cleanup_keeps_active_previous_and_every_bundle_inside_retention(tmp_path, clock):
    store = SitemapBundleStore(tmp_path, retention=timedelta(hours=24), now=clock.now)
    store.publish(bundle("a" * 64)); clock.advance(hours=1)
    store.publish(bundle("b" * 64)); clock.advance(hours=1)
    store.publish(bundle("c" * 64)); store.cleanup()
    assert store.list_batches() == ("a" * 64, "b" * 64, "c" * 64)
    clock.advance(hours=23); store.cleanup()
    assert store.list_batches() == ("b" * 64, "c" * 64)


def test_repeated_identical_publish_reuses_completed_directory(tmp_path, clock, monkeypatch):
    candidate = bundle("b" * 64)
    store = SitemapBundleStore(tmp_path, now=clock.now)
    store.publish(candidate)
    first_pointer = read_and_validate_active_pointer(tmp_path / "active.json")
    clock.advance(minutes=1)
    write_spy = Mock(wraps=write_bundle_and_fsync)
    monkeypatch.setattr("agent.sitemap_store.write_bundle_and_fsync", write_spy)

    store.publish(candidate)

    write_spy.assert_not_called()
    assert store.load_active() == candidate
    assert read_and_validate_active_pointer(tmp_path / "active.json")["published_at"] != first_pointer["published_at"]


def test_retry_after_post_rename_pre_pointer_failure_reuses_completed_directory(tmp_path):
    previous = bundle("a" * 64)
    candidate = bundle("b" * 64)
    store = SitemapBundleStore(tmp_path, fail_after_directory_rename_for_test=True)
    SitemapBundleStore(tmp_path).publish(previous)

    with pytest.raises(InjectedPublicationFailure):
        store.publish(candidate)

    assert SitemapBundleStore(tmp_path).load_active() == previous
    with pytest.raises(SitemapStateUnavailable):
        SitemapBundleStore(tmp_path).load_batch(candidate.batch_revision)
    assert (tmp_path / candidate.batch_revision).is_dir()
    restarted = SitemapBundleStore(tmp_path)
    restarted.publish(candidate)
    assert restarted.load_active() == candidate
    assert not any(path.name.endswith(".staging") for path in tmp_path.iterdir())


def test_existing_content_address_with_conflicting_bytes_is_rejected(tmp_path):
    candidate = bundle("b" * 64)
    target = tmp_path / candidate.batch_revision
    write_bundle_and_fsync(target, bundle_with_changed_document(candidate))

    with pytest.raises(SitemapBundleConflict):
        SitemapBundleStore(tmp_path).publish(candidate)
    assert not (tmp_path / "active.json").exists()
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_sitemap_store.py -q`

Expected: FAIL because immutable storage and active-pointer publication do not exist.

- [ ] **Step 3: Implement staging, fsync, atomic rename, and active pointer**

```python
@dataclass(frozen=True)
class StoredBundle:
    batch_revision: str
    metadata: dict
    documents: dict[str, bytes]


class SitemapBundleStore:
    DEFAULT_RETENTION = timedelta(hours=24)

    def __init__(
        self,
        root: Path,
        *,
        retention: timedelta = DEFAULT_RETENTION,
        now=lambda: datetime.now(timezone.utc),
        fail_after_directory_rename_for_test: bool = False,
    ):
        self.root = root
        self.retention = retention
        self.now = now
        self._fail_after_directory_rename_for_test = fail_after_directory_rename_for_test

    @classmethod
    def from_release_root(cls, release_root: Path | None = None, **kwargs):
        root = release_root if release_root is not None else Path(__file__).resolve().parents[1]
        return cls(root / "agent" / "data" / "sitemap-bundles", **kwargs)

    def publish(self, bundle: StoredBundle) -> None:
        with cross_process_lock(self.root / ".publish.lock"):
            target = self.root / bundle.batch_revision
            if target.exists():
                validate_completed_bundle_matches(target, bundle)
            else:
                staging = self.root / f".{bundle.batch_revision}.{uuid4().hex}.staging"
                write_bundle_and_fsync(staging, bundle)
                os.replace(staging, target)
                fsync_directory(self.root)
                if self._fail_after_directory_rename_for_test:
                    raise InjectedPublicationFailure("after-directory-rename-before-active-pointer")
            pointer = read_active_pointer_or_empty(self.root / "active.json")
            published_at = self.now().isoformat()
            history = upsert_successful_publication(
                pointer.get("published_batches", []), bundle.batch_revision, published_at,
            )
            atomic_write_json(self.root / "active.json", {
                "batch_revision": bundle.batch_revision,
                "published_at": published_at,
                "published_batches": history,
            })

    def load_active_on_startup(self) -> StoredBundle:
        pointer = read_and_validate_active_pointer(self.root / "active.json")
        return read_and_validate_immutable_bundle(self.root / pointer["batch_revision"])

    def cleanup(self) -> None:
        with cross_process_lock(self.root / ".publish.lock"):
            pointer = read_and_validate_active_pointer(self.root / "active.json")
            active = pointer["batch_revision"]
            bundles = sorted(pointer["published_batches"], key=lambda item: item["published_at"], reverse=True)
            previous = next((item["batch_revision"] for item in bundles if item["batch_revision"] != active), None)
            keep = {active, previous} - {None}
            cutoff = self.now() - self.retention
            keep.update(item["batch_revision"] for item in bundles if parse_utc(item["published_at"]) >= cutoff)
            for item in bundles:
                if item["batch_revision"] not in keep:
                    remove_validated_bundle_directory(self.root, item["batch_revision"])
            atomic_write_json(self.root / "active.json", {
                **pointer,
                "published_batches": [item for item in bundles if item["batch_revision"] in keep],
            })
```

`read_and_validate_immutable_bundle()` verifies metadata schema, all three filenames, per-document SHA-256 values, the batch revision, and the directory name before returning bytes. `validate_completed_bundle_matches()` additionally requires the exact expected filename set, metadata bytes, and document bytes for the supplied `StoredBundle`; a content-addressed directory that differs in any byte, contains an extra entry, or is a symlink raises `SitemapBundleConflict`. The immutable bundle metadata contains no publication timestamp. Replaceable `active.json` owns `published_at` plus a deduplicated `published_batches` ledger of successfully pointer-published revisions and timestamps; cleanup derives active, previous, and retention exclusively from that ledger, and `load_batch()` refuses an orphan directory not present in it. An identical publish validates/reuses the completed directory and atomically refreshes/upserts the pointer ledger. A retry after the test-only post-rename/pre-pointer injection follows that same reuse path, while the orphan remains unreachable before retry. Corrupt or missing `active.json` raises `SitemapStateUnavailable` and never triggers generation. `remove_validated_bundle_directory()` resolves the candidate under `self.root`, rejects symlinks/staging/active/previous paths, deletes only a validated immutable batch, and fsyncs the parent. Promote or reuse the lock and atomic JSON replacement primitives from `versioned_json_store.py`; do not duplicate a weaker implementation.

The CLI protocol consumed by Task 17 is fixed here: production opens `SitemapBundleStore.from_release_root()`, backend startup calls only `load_active_on_startup()`, `python -m agent.sitemap_bundle refresh` is the only generation entry point, and public GET handlers call only `load_active()`/`load_batch()`. Tests monkeypatch the refresh function and prove import, startup load, and public reads never invoke it.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_sitemap_store.py -q`

Expected: the production default path, configurable 24-hour clock, active-plus-previous retention algorithm, first publication, identical idempotent publication, retry after post-rename/pre-pointer failure, conflicting-directory rejection, restart validation, corrupt-state rejection, and no-refresh startup/public-read protocol pass.

- [ ] **Step 5: Commit**

```bash
git add agent/sitemap_store.py agent/tests/test_sitemap_store.py agent/versioned_json_store.py
git commit -m "feat: publish immutable sitemap bundles"
```

### Task 16: Verify PostgreSQL snapshot isolation and concurrent publication

**Files:**
- Create: `agent/tests/test_sitemap_bundle_postgres.py`
- Create: `tests/launch_safety/harness/docker-compose.postgres.yml`
- Modify: `agent/sitemap_snapshot.py`
- Modify: `agent/sitemap_store.py`

- [ ] **Step 1: Write the opt-in integration test**

```python
@pytest.mark.integration
def test_all_three_documents_use_the_original_repeatable_read_snapshot(disposable_pg, tmp_path):
    with open_snapshot(disposable_pg) as snapshot:
        mutate_entity_from_second_connection(disposable_pg, "entity-1", summary="changed", images=["changed.webp"])
        documents = build_snapshot_probe_documents(snapshot)

    assert b"original-summary" in documents["sitemap.xml"]
    assert b"original.webp" in documents["sitemap-media.xml"]
    assert b"original-snapshot" in documents["sitemap-index.xml"]
    assert all(b"changed" not in body for body in documents.values())


@pytest.mark.integration
def test_concurrent_refresh_exposes_only_complete_bundle(disposable_pg, tmp_path):
    revisions = publish_concurrently(disposable_pg, tmp_path)
    active = SitemapBundleStore(tmp_path).load_active()
    assert active.batch_revision in revisions
    assert set(active.documents) == {"sitemap.xml", "sitemap-media.xml", "sitemap-index.xml"}


@pytest.mark.integration
def test_failed_publication_preserves_previous_complete_bundle(disposable_pg, tmp_path):
    store = SitemapBundleStore(tmp_path)
    previous = complete_probe_bundle(disposable_pg, label="previous")
    store.publish(previous)
    store.fail_after_directory_rename_for_test = True

    with pytest.raises(InjectedPublicationFailure):
        store.publish(complete_probe_bundle(disposable_pg, label="candidate"))

    restarted = SitemapBundleStore(tmp_path).load_active_on_startup()
    assert restarted.batch_revision == previous.batch_revision
    assert restarted.documents == previous.documents
    assert set(restarted.documents) == {"sitemap.xml", "sitemap-media.xml", "sitemap-index.xml"}
```

Use the guarded disposable PostgreSQL fixture pattern from `agent/tests/test_account_control_plane_postgres.py:25`; reject non-loopback database URLs unless an exact test-only override is supplied.

- [ ] **Step 2: Provision disposable PostgreSQL and record a genuine RED**

Run: `docker compose -f tests/launch_safety/harness/docker-compose.postgres.yml up -d --wait`

Run: `$env:SITEMAP_BUNDLE_TEST_DATABASE_URL='postgresql://vl360:vl360_launch_test@127.0.0.1:55432/vl360_launch_test'; python -m pytest agent/tests/test_sitemap_bundle_postgres.py -m integration -q`

Expected: FAIL after connecting to the disposable loopback database because the snapshot callback/probe-document contract, concurrent publication harness, and injected post-rename/pre-pointer failure hook do not exist. A SKIP does not count as RED; if Docker is unavailable, record the missing local dependency and do not mark Task 16 complete until the test has produced a real failing assertion against a provisioned disposable PostgreSQL.

- [ ] **Step 3: Implement the disposable database fixture and concurrency harness**

```python
url = os.getenv("SITEMAP_BUNDLE_TEST_DATABASE_URL")
if not url:
    pytest.skip("disposable PostgreSQL URL not configured")
parsed = urlparse(url)
if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and os.getenv("ALLOW_REMOTE_DISPOSABLE_PG") != "true":
    pytest.fail("PostgreSQL integration target must be loopback")
```

The Compose harness publishes PostgreSQL only on `127.0.0.1:55432`, uses a dedicated disposable database, and has no production credentials or volumes. The fixture creates a unique schema, opens the production `REPEATABLE READ, READ ONLY` snapshot, pauses after the first read, commits changed summary/image/relationship data through a second connection, then builds three deterministic probe documents from the still-open snapshot. `sitemap-index.xml` includes a snapshot marker derived inside that transaction, so the test proves main, media, and index inputs are all original rather than checking one entity object only.

Reuse the Task 15 test-only `fail_after_directory_rename_for_test` injection immediately after the complete candidate directory is fsynced/renamed and before `active.json` replacement. Its production default remains immutable `False`. The failed-publication test reconstructs a new store instance, loads the prior active pointer and all three prior document bytes, asserts no staging or candidate directory is reachable through public load methods, and leaves the completed candidate available only for a later validated idempotent publish.

- [ ] **Step 4: Run GREEN against a disposable local PostgreSQL**

Run: `$env:SITEMAP_BUNDLE_TEST_DATABASE_URL='postgresql://vl360:vl360_launch_test@127.0.0.1:55432/vl360_launch_test'; python -m pytest agent/tests/test_sitemap_bundle_postgres.py -m integration -q`

Run: `Remove-Item Env:SITEMAP_BUNDLE_TEST_DATABASE_URL; python -m pytest agent/tests/test_sitemap_bundle_postgres.py -m integration -q`

Run: `docker compose -f tests/launch_safety/harness/docker-compose.postgres.yml down -v`

Expected: the provisioned run passes all original-snapshot/all-three-document, concurrent complete-publication, and failed-publication preservation assertions; the unconfigured run safely skips; teardown removes the disposable volume.

- [ ] **Step 5: Commit**

```bash
git add agent/tests/test_sitemap_bundle_postgres.py tests/launch_safety/harness/docker-compose.postgres.yml agent/sitemap_snapshot.py agent/sitemap_store.py
git commit -m "test: verify sitemap PostgreSQL isolation"
```

### Task 17: Render and serve the main sitemap document

**Files:**
- Create: `agent/sitemap_render.py`
- Create: `agent/sitemap_bundle.py`
- Create: `agent/tests/test_sitemap_render.py`
- Create: `agent/tests/test_sitemap_bundle.py`
- Modify: `agent/launch_policy_api.py`
- Modify: `agent/server.py:990-1140`
- Modify: `agent/seo.py:1411-1493`

- [ ] **Step 1: Write failing deterministic main-sitemap tests**

```python
def test_main_sitemap_contains_manifest_and_policy_positive_details(snapshot, manifest, evidence):
    xml = render_main_sitemap(snapshot, manifest, evidence)
    assert b"https://vinhlong360.vn/du-lich" in xml
    assert b"https://vinhlong360.vn/dia-diem/rich" in xml
    assert b"/dia-diem/thin" not in xml
    assert b"/lich-trinh/" not in xml


def test_internal_main_document_requires_pinned_batch(client, published_store):
    response = client.get(f"/_internal/launch-sitemaps/sitemap.xml?batch={published_store.active_revision}")
    assert response.status_code == 200
    assert response.headers["x-launch-sitemap-batch-revision"] == published_store.active_revision


def test_ward_child_counts_use_the_index_policy_public_allowlist(snapshot_with_children):
    counts = public_ward_child_counts(snapshot_with_children)
    assert counts["ward-1"] == 2
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_sitemap_render.py agent/tests/test_sitemap_bundle.py -q`

Expected: FAIL because deterministic rendering, refresh orchestration, and the internal document route do not exist.

- [ ] **Step 3: Implement main rendering and CLI orchestration**

```python
def render_main_sitemap(snapshot, manifest, evidence) -> bytes:
    urls = set(extract_static_sitemap_paths(manifest))
    child_counts = public_ward_child_counts(snapshot)
    for entity in snapshot.entities:
        decision = (
            decide_ward(entity, public_child_count=child_counts.get(entity["id"], 0), evidence=evidence)
            if entity.get("type") == "place"
            else decide_entity(entity, evidence)
        )
        if decision.indexable:
            urls.add(canonical_detail_url(entity))
    return serialize_urlset(sorted(urls))


def public_ward_child_counts(snapshot) -> dict[str, int]:
    public_ids = {
        entity["id"]
        for entity in snapshot.entities
        if is_publicly_eligible(entity)
    }
    counts: dict[str, int] = {}
    for relationship in snapshot.relationships:
        if relationship.get("type") == "located_in" and relationship.get("source_id") in public_ids:
            parent = relationship.get("target_id")
            counts[parent] = counts.get(parent, 0) + 1
    return counts


def canonical_detail_url(entity: dict) -> str:
    prefix = "xa-phuong" if entity.get("type") == "place" else "dia-diem"
    return f"https://vinhlong360.vn/{prefix}/{quote(str(entity['id']), safe='')}"


def serialize_urlset(urls: list[str]) -> bytes:
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for url in urls:
        node = SubElement(root, "url")
        SubElement(node, "loc").text = url
    return tostring(root, encoding="utf-8", xml_declaration=True)
```

Import the exact Task 5 function `extract_static_sitemap_paths` from `route_manifest`, plus `is_publicly_eligible`, `decide_entity`, and `decide_ward` from `index_policy`; do not define a sitemap-local status/verification rule. `python -m agent.sitemap_bundle refresh` loads one snapshot, renders all current document types, validates them, and publishes through `SitemapBundleStore`. Backend startup validates `active.json` but never refreshes inside a GET.

Because existing agent modules use top-level imports, `agent/sitemap_bundle.py` must use the same direct-execution/module bootstrap pattern as `agent/mcp_server.py:35` so both `python agent/sitemap_bundle.py refresh` and the required module command resolve imports consistently without adding a repository-wide package refactor.

- [ ] **Step 4: Run GREEN and retire mutable main-sitemap ownership**

Run: `python -m pytest agent/tests/test_sitemap_snapshot.py agent/tests/test_sitemap_render.py agent/tests/test_sitemap_store.py agent/tests/test_sitemap_bundle.py agent/tests/test_launch_policy_api.py -q`

Run: `python scripts/checks/check_policy_http_registry.py`

Expected: exact main XML and pinned internal response pass; all three registry rows resolve with zero future allowance; every policy/evidence route is registered; legacy `web/data.json` fallback tests are removed.

- [ ] **Step 5: Commit**

```bash
git add agent/sitemap_render.py agent/sitemap_bundle.py agent/tests/test_sitemap_render.py agent/tests/test_sitemap_bundle.py agent/launch_policy_api.py agent/server.py agent/seo.py
git commit -m "feat: render immutable main sitemap"
```

### Task 18: Render the media sitemap with AI disclosure

**Files:**
- Create: `agent/image_descriptor.py`
- Create: `agent/tests/test_image_descriptor.py`
- Modify: `agent/sitemap_render.py`
- Modify: `agent/sitemap_bundle.py`
- Modify: `agent/tests/test_sitemap_render.py`
- Create: `agent/tests/fixtures/sitemap/expected-sitemap-media.xml`

- [ ] **Step 1: Write failing media inclusion/exclusion tests**

```python
def test_media_sitemap_includes_only_entity_ai_images(snapshot, manifest, evidence, disclosure):
    xml = render_media_sitemap(snapshot, manifest, evidence, disclosure)
    assert "Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.".encode() in xml
    assert b"review-user-photo.jpg" not in xml
    assert b"generated-placeholder.svg" not in xml
    assert b"thin-entity-ai.webp" not in xml
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_sitemap_render.py -q`

Expected: FAIL because the immutable bundle has no media document and legacy code lacks source classification.

- [ ] **Step 3: Add descriptor-backed media rendering**

```python
def normalize_renderable_image_url(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    url = raw.strip()
    if not url or any(ord(char) <= 0x20 or ord(char) == 0x7F for char in url) or "\\" in url or "#" in url:
        return None
    if url.startswith("//"):
        return None
    parsed = urlsplit(url)
    try:
        parsed.port
    except ValueError:
        return None
    if url.startswith("/"):
        return url if not parsed.scheme and not parsed.netloc and parsed.path.startswith("/") else None
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return url


@dataclass(frozen=True)
class ImageDescriptor:
    url: str | None
    alt: str
    source_class: str
    source_kind: str
    disclosure_key: str
    short_label: str | None
    full_disclosure: str
    credit: str | None
    width: int | None
    height: int | None
def describe_entity_images(entity, *, disclosure):
    descriptors = []
    for index, raw in enumerate(entity.get("images") or []):
        url = normalize_renderable_image_url(raw)
        if url:
            descriptors.append(ImageDescriptor(
                url=url,
                alt=f"{entity['name']} — ảnh minh họa {index + 1}",
                source_class="ai-generated",
                source_kind="entity-editorial",
                disclosure_key="entity-ai",
                short_label=disclosure.entity_ai.short_label,
                full_disclosure=disclosure.entity_ai.full_disclosure,
                credit=None,
                width=None,
                height=None,
            ))
    return tuple(descriptors)


def decide_entity_or_ward(entity, snapshot, evidence):
    if entity.get("type") == "place":
        return decide_ward(entity, public_child_count=public_ward_child_counts(snapshot).get(entity["id"], 0), evidence=evidence)
    return decide_entity(entity, evidence)


def render_media_sitemap(snapshot, manifest, evidence, disclosure) -> bytes:
    entries = []
    for entity in snapshot.entities:
        if decide_entity_or_ward(entity, snapshot, evidence).indexable:
            for descriptor in describe_entity_images(entity, disclosure=disclosure):
                if descriptor.source_class == "ai-generated" and descriptor.url:
                    entries.append((canonical_detail_url(entity), descriptor))
    return serialize_image_urlset(entries)


def serialize_image_urlset(entries) -> bytes:
    root = Element("urlset", {
        "xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "xmlns:image": "http://www.google.com/schemas/sitemap-image/1.1",
    })
    for page_url, descriptor in entries:
        url = SubElement(root, "url")
        SubElement(url, "loc").text = page_url
        image = SubElement(url, "image:image")
        SubElement(image, "image:loc").text = descriptor.url
        SubElement(image, "image:caption").text = descriptor.full_disclosure
    return tostring(root, encoding="utf-8", xml_declaration=True)
```

Placeholders, malformed URLs, review UGC, and post UGC never enter the media sitemap.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_sitemap_render.py agent/tests/test_sitemap_bundle.py -q`

Expected: deterministic media XML matches the fixture and disclosure text exactly.

- [ ] **Step 5: Commit**

```bash
git add agent/image_descriptor.py agent/tests/test_image_descriptor.py agent/sitemap_render.py agent/sitemap_bundle.py agent/tests/test_sitemap_render.py agent/tests/fixtures/sitemap/expected-sitemap-media.xml
git commit -m "feat: render disclosed media sitemap"
```

### Task 19: Add the pinned sitemap-index protocol

**Files:**
- Modify: `agent/sitemap_render.py`
- Modify: `agent/sitemap_store.py`
- Modify: `agent/sitemap_bundle.py`
- Modify: `agent/launch_policy_api.py`
- Modify: `agent/tests/test_sitemap_render.py`
- Modify: `agent/tests/test_sitemap_store.py`
- Modify: `agent/tests/test_launch_policy_api.py`

- [ ] **Step 1: Write failing pinned-index and invalid-batch tests**

```python
def test_index_pins_both_children_to_one_batch(published_bundle):
    xml = published_bundle.documents["sitemap-index.xml"].decode()
    batch = published_bundle.batch_revision
    assert f"/sitemap.xml?batch={batch}" in xml
    assert f"/sitemap-media.xml?batch={batch}" in xml


@pytest.mark.parametrize("query", ["", "batch=", "batch=ABC", "batch=0", "batch=" + "a" * 64 + "&x=1"])
def test_pinned_children_reject_invalid_queries(client, query):
    response = client.get(f"/_internal/launch-sitemaps/sitemap.xml?{query}")
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-launch-indexing-policy"] == "failed-open"
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_sitemap_render.py agent/tests/test_sitemap_store.py agent/tests/test_launch_policy_api.py -q`

Expected: FAIL because the index is not content-addressed and invalid requests can fall back to mutable/current output.

- [ ] **Step 3: Compute the batch from completed bytes and enforce exact retrieval**

```python
def compute_batch_revision(*, fingerprint: str, route_revision: str, policy_revision: str, main: bytes, media: bytes) -> str:
    digest = sha256()
    for value in (fingerprint.encode(), route_revision.encode(), policy_revision.encode(), main, media):
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def render_sitemap_index(origin: str, batch: str) -> bytes:
    root = Element("sitemapindex", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for location in (
        f"{origin}/sitemap.xml?batch={batch}",
        f"{origin}/sitemap-media.xml?batch={batch}",
    ):
        node = SubElement(root, "sitemap")
        SubElement(node, "loc").text = location
    return tostring(root, encoding="utf-8", xml_declaration=True)
```

Validate lowercase 64-character SHA-256 input, exact single `batch` query, active/pinned bundle existence, document digest, all evidence headers, and `X-Launch-Sitemap-Requested-Batch`. Never fall back from an invalid pinned request to active.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_sitemap_render.py agent/tests/test_sitemap_store.py agent/tests/test_sitemap_bundle.py agent/tests/test_launch_policy_api.py -q`

Expected: active index and pinned index/children all serve one immutable batch; invalid/expired/corrupt cases return 503.

- [ ] **Step 5: Commit**

```bash
git add agent/sitemap_render.py agent/sitemap_store.py agent/sitemap_bundle.py agent/launch_policy_api.py agent/tests/test_sitemap_render.py agent/tests/test_sitemap_store.py agent/tests/test_launch_policy_api.py
git commit -m "feat: pin sitemap documents to immutable batches"
```

## Phase 4: Nuxt Launch Decision, Headers, and Root SEO

### Task 20: Implement the Nuxt two-key base decision and attestation client

**Files:**
- Create: `web-nuxt/types/launch.ts`
- Create: `web-nuxt/server/utils/launch/launchEvidence.ts`
- Create: `web-nuxt/server/utils/launch/launchIntent.ts`
- Create: `web-nuxt/server/utils/launch/backendAttestation.ts`
- Create: `web-nuxt/server/utils/launch/launchSafetyDecision.ts`
- Create: `web-nuxt/tests/launch-safety-decision.test.ts`
- Create: `web-nuxt/tests/launch-attestation.test.ts`
- Modify: `web-nuxt/nuxt.config.ts:128-137`
- Modify: `web-nuxt/utils/apiFetch.ts:12`

- [ ] **Step 1: Write the exact truth-table and attestation mismatch tests**

```ts
it.each([
  [{}, 'closed', 'closed-default'],
  [{ LAUNCH_INDEXING_MODE: 'selective-open' }, 'closed', 'owner-approval-missing'],
  [{ LAUNCH_INDEXING_OWNER_APPROVED: 'true' }, 'closed', 'invalid-configuration'],
  [{ LAUNCH_INDEXING_MODE: ' selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' }, 'closed', 'invalid-configuration'],
  [{ LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'TRUE' }, 'closed', 'owner-approval-missing'],
  [{ LAUNCH_INDEXING_MODE: 'selective-open', LAUNCH_INDEXING_OWNER_APPROVED: 'true' }, 'selective-open', 'valid-two-key-unlock'],
])('enforces exact two-key intent', async (env, state, reason) => {
  const decision = await resolveBaseLaunchSafetyDecision({
    env,
    build: matchingBuild,
    fetchAttestation: vi.fn().mockResolvedValue(matchingAttestation),
  })
  expect(decision.operational_state).toBe(state)
  expect(decision.reason).toBe(reason)
})
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-safety-decision.test.ts tests/launch-attestation.test.ts`

Expected: FAIL because the private two-key contract and attestation client do not exist.

- [ ] **Step 3: Add immutable decision types and the private internal client**

```ts
export type OperationalState = 'closed' | 'selective-open' | 'failed-open'
export type IndexingPosture = 'closed' | 'selective-open'
export type SitemapAction = 'closed-empty' | 'guarded-proxy' | 'unavailable'
export type LaunchSafetyReason =
  | 'closed-default'
  | 'valid-two-key-unlock'
  | 'invalid-configuration'
  | 'owner-approval-missing'
  | 'policy-attestation-unavailable'
  | 'policy-mismatch'
  | 'build-isolation-unsafe'
  | 'entity-policy-unavailable'
  | 'entity-policy-mismatch'
  | 'sitemap-batch-unavailable'
  | 'sitemap-evidence-mismatch'

export interface LaunchSafetyDecision {
  operational_state: OperationalState
  indexing_posture: IndexingPosture
  policy_fingerprint: string | null
  route_manifest_revision: string | null
  backend_policy_revision: string | null
  sitemap_batch_revision: string | null
  sitemap_action: SitemapAction
  reason: LaunchSafetyReason
}

export interface LaunchPageDecision extends LaunchSafetyDecision {
  robots: 'index, follow' | 'noindex, follow'
  sitemapDiscovery: boolean
}
```

```ts
// web-nuxt/server/utils/launch/launchEvidence.ts
export const INDEX_POLICY_REVISION = 'index-policy-v1'
export const RESPONSE_MATRIX_REVISION = 'launch-safety-matrix-v1'
export const CACHE_ISOLATION_REVISION = 'launch-cache-isolation-v1'
export const SITEMAP_PROTOCOL_REVISION = 'pinned-sitemap-bundle-v1'

export function buildPolicyFingerprint(input: {
  routeRevision: string
  routeDigest: string
  disclosureRevision: string
  disclosureDigest: string
}): string {
  const canonicalPayload = JSON.stringify({
    cache_isolation: CACHE_ISOLATION_REVISION,
    disclosure_artifact: { revision: input.disclosureRevision, sha256: input.disclosureDigest },
    index_policy: INDEX_POLICY_REVISION,
    response_matrix: RESPONSE_MATRIX_REVISION,
    route_artifact: { revision: input.routeRevision, sha256: input.routeDigest },
    sitemap_protocol: SITEMAP_PROTOCOL_REVISION,
  })
  return createHash('sha256').update(canonicalPayload, 'utf8').digest('hex')
}
```

Load `tests/fixtures/launch-policy-fingerprint.json` and assert TypeScript produces `6397813fbaafc0800f0d1cadb87214b3d250c72bc03b5a15a7386ba979b2926e` for the same two artifact revisions/digests and semantic revisions as Python. Add one mutation assertion per input: changing only the route revision, route digest, disclosure revision, disclosure digest, index-policy revision, response-matrix revision, cache/service-worker isolation revision, or sitemap-protocol revision must change the fingerprint. The readiness build evidence passes all four artifact inputs rather than reconstructing or omitting either revision.

```ts
export function readLaunchIntent(env: NodeJS.ProcessEnv) {
  const mode = env.LAUNCH_INDEXING_MODE
  const owner = env.LAUNCH_INDEXING_OWNER_APPROVED
  if (mode === undefined && owner === undefined) return { openIntent: false, reason: 'closed-default' as const }
  if (mode !== 'selective-open') return { openIntent: false, reason: 'invalid-configuration' as const }
  if (owner !== 'true') return { openIntent: false, reason: 'owner-approval-missing' as const }
  return { openIntent: true, reason: 'valid-two-key-unlock' as const }
}
```

Move `apiBase` into private runtime config for SSR/internal calls. Browser data calls remain relative through Nginx; unlock keys and internal backend URLs never enter `runtimeConfig.public`.

- [ ] **Step 4: Run GREEN and typecheck**

Run: `cd web-nuxt && npm test -- --run tests/launch-safety-decision.test.ts tests/launch-attestation.test.ts && npm run typecheck`

Expected: exact truth table, backend-error, stale-revision, and matching-attestation cases pass.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/types/launch.ts web-nuxt/server/utils/launch/launchEvidence.ts web-nuxt/server/utils/launch/launchIntent.ts web-nuxt/server/utils/launch/backendAttestation.ts web-nuxt/server/utils/launch/launchSafetyDecision.ts web-nuxt/tests/launch-safety-decision.test.ts web-nuxt/tests/launch-attestation.test.ts web-nuxt/nuxt.config.ts web-nuxt/utils/apiFetch.ts
git commit -m "feat: resolve Nuxt launch safety decisions"
```

### Task 21: Add the guarded Nuxt sitemap proxy

**Files:**
- Create: `web-nuxt/server/utils/launch/guardedSitemapProxy.ts`
- Create: `web-nuxt/tests/launch-guarded-sitemap.test.ts`

- [ ] **Step 1: Write failing query and evidence-validation tests**

```ts
it.each([
  ['sitemap.xml', '?batch=' + 'a'.repeat(64), 200],
  ['sitemap.xml', '', 503],
  ['sitemap.xml', '?batch=ABC', 503],
  ['sitemap.xml', '?batch=' + 'a'.repeat(64) + '&x=1', 503],
  ['sitemap-index.xml', '', 200],
])('guards %s %s', async (document, query, expected) => {
  const response = await runGuardedProxy({ document, query, upstream: matchingUpstream })
  expect(response.status).toBe(expected)
  if (expected === 200) {
    expect(response.decision).toMatchObject({
      operational_state: 'selective-open',
      sitemap_batch_revision: 'a'.repeat(64),
    })
  } else {
    expect(response.decision).toMatchObject({
      operational_state: 'failed-open',
      policy_fingerprint: null,
      route_manifest_revision: null,
      backend_policy_revision: null,
      sitemap_batch_revision: null,
    })
  }
})
```

```ts
it.each([
  ['x-launch-policy-fingerprint', 'f'.repeat(64)],
  ['x-launch-route-manifest-revision', 'stale-route-v0'],
  ['x-launch-backend-policy-revision', 'stale-policy-v0'],
  ['x-launch-sitemap-batch-revision', 'b'.repeat(64)],
  ['x-launch-sitemap-requested-batch', 'b'.repeat(64)],
])('fails closed when %s mismatches', async (header, value) => {
  const upstream = matchingUpstream.withHeader(header, value)
  expect(await runGuardedProxy({
    document: 'sitemap.xml',
    query: '?batch=' + 'a'.repeat(64),
    upstream,
  })).toMatchObject({
    status: 503,
    decision: {
      operational_state: 'failed-open',
      policy_fingerprint: null,
      route_manifest_revision: null,
      backend_policy_revision: null,
      sitemap_batch_revision: null,
    },
  })
})
```

Add a pinned-response regression where `X-Launch-Sitemap-Requested-Batch` correctly echoes the requested `a...a` value but `X-Launch-Sitemap-Batch-Revision` reports a different valid `b...b` value; it must return 503. This proves the served immutable bundle itself, not only the echo header, is pinned to the request.

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-guarded-sitemap.test.ts`

Expected: FAIL because the proxy and exact query validation do not exist.

- [ ] **Step 3: Implement raw internal fetch and all-evidence checks**

```ts
export type RootSitemapDocument = 'sitemap.xml' | 'sitemap-media.xml' | 'sitemap-index.xml'

export function validateSitemapQuery(document: RootSitemapDocument, url: URL) {
  const keys = [...url.searchParams.keys()]
  if (keys.length === 0 && document === 'sitemap-index.xml') return { requestedBatch: null }
  if (keys.length !== 1 || keys[0] !== 'batch') throw createError({ statusCode: 503 })
  const batch = url.searchParams.get('batch') || ''
  if (!/^[a-f0-9]{64}$/.test(batch)) throw createError({ statusCode: 503 })
  return { requestedBatch: batch }
}

interface GuardedSitemapInput {
  event: H3Event
  document: RootSitemapDocument
  decision: Readonly<LaunchSafetyDecision>
  url: URL
  fetchRaw: InternalRawFetcher
}

type InternalRawFetcher = (
  document: RootSitemapDocument,
  requestedBatch: string | null,
) => Promise<{ body: string; headers: Record<string, string> }>

interface GuardedSitemapResult {
  status: 200 | 503
  body: string
  contentType: string
  decision: Readonly<LaunchSafetyDecision>
  requestedBatch: string | null
}

function failedOpenSitemap(reason: 'sitemap-batch-unavailable' | 'sitemap-evidence-mismatch'): GuardedSitemapResult {
  return {
    status: 503,
    body: '',
    contentType: 'application/xml; charset=utf-8',
    requestedBatch: null,
    decision: {
      operational_state: 'failed-open',
      indexing_posture: 'closed',
      policy_fingerprint: null,
      route_manifest_revision: null,
      backend_policy_revision: null,
      sitemap_batch_revision: null,
      sitemap_action: 'unavailable',
      reason,
    },
  }
}

function validateAllLaunchEvidence(
  headers: Record<string, string>,
  decision: LaunchSafetyDecision,
  requestedBatch: string | null,
): string {
  if (headers['x-launch-policy-fingerprint'] !== decision.policy_fingerprint) throw createError({ statusCode: 503 })
  if (headers['x-launch-route-manifest-revision'] !== decision.route_manifest_revision) throw createError({ statusCode: 503 })
  if (headers['x-launch-backend-policy-revision'] !== decision.backend_policy_revision) throw createError({ statusCode: 503 })
  const servedBatch = headers['x-launch-sitemap-batch-revision'] || ''
  if (!/^[a-f0-9]{64}$/.test(servedBatch)) throw createError({ statusCode: 503 })
  if (requestedBatch && headers['x-launch-sitemap-requested-batch'] !== requestedBatch) throw createError({ statusCode: 503 })
  if (requestedBatch && servedBatch !== requestedBatch) throw createError({ statusCode: 503 })
  if (!requestedBatch && headers['x-launch-sitemap-requested-batch']) throw createError({ statusCode: 503 })
  return servedBatch
}

export async function proxyGuardedSitemap(input: GuardedSitemapInput): Promise<GuardedSitemapResult> {
  if (input.decision.sitemap_action !== 'guarded-proxy') return failedOpenSitemap('sitemap-batch-unavailable')
  try {
    const query = validateSitemapQuery(input.document, input.url)
    const upstream = await input.fetchRaw(input.document, query.requestedBatch)
    const servedBatch = validateAllLaunchEvidence(upstream.headers, input.decision, query.requestedBatch)
    return {
      status: 200,
      body: upstream.body,
      contentType: 'application/xml; charset=utf-8',
      requestedBatch: query.requestedBatch,
      decision: Object.freeze({ ...input.decision, sitemap_batch_revision: servedBatch }),
    }
  } catch {
    return failedOpenSitemap('sitemap-evidence-mismatch')
  }
}

export async function fetchAndValidateActiveSitemapIndex(event: H3Event, decision: LaunchSafetyDecision) {
  const result = await proxyGuardedSitemap({
    event,
    document: 'sitemap-index.xml',
    decision,
    url: new URL('/sitemap-index.xml', 'http://internal'),
    fetchRaw: createInternalSitemapFetcher(event),
  })
  return {
    decision: result.decision,
    batchRevision: result.decision.sitemap_batch_revision,
    body: result.body,
  }
}
```

The internal fetch targets only `/_internal/launch-sitemaps/{document}` over the private backend URL and never follows redirects. Upstream launch headers are validation input only and are never forwarded directly. A successful proxy returns a refined immutable request decision carrying the validated `sitemap_batch_revision`; every query, transport, or evidence failure returns a failed-open decision with all evidence cleared. Task 22 is the only public launch-header writer.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/launch-guarded-sitemap.test.ts`

Expected: valid active/pinned responses pass; every malformed query or evidence mismatch becomes 503 failed-open with no evidence headers.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/server/utils/launch/guardedSitemapProxy.ts web-nuxt/tests/launch-guarded-sitemap.test.ts
git commit -m "feat: guard Nuxt sitemap proxy responses"
```

### Task 22: Finalize exact policy and evidence response headers

**Files:**
- Create: `web-nuxt/server/utils/launch/launchHeaders.ts`
- Create: `web-nuxt/server/middleware/launch-safety.ts`
- Create: `web-nuxt/server/plugins/launch-response.ts`
- Create: `web-nuxt/tests/launch-headers.test.ts`
- Delete: `web-nuxt/server/middleware/noindex.ts`

- [ ] **Step 1: Write failing exactly-once header tests**

```ts
it.each([
  [closedDecision, 'closed', false],
  [selectiveOpenDecision, 'selective-open', true],
  [failedOpenDecision, 'failed-open', false],
])('writes exact policy headers', (decision, policy, hasEvidence) => {
  const headers = buildBaseLaunchResponseHeaders({ decision })
  expect(headers['X-Launch-Indexing-Policy']).toBe(policy)
  expect(headers['Cache-Control']).toBe('no-store')
  expect(Boolean(headers['X-Launch-Policy-Fingerprint'])).toBe(hasEvidence)
})

it('emits sitemap batch evidence only from the validated final decision', () => {
  const decision = { ...selectiveOpenDecision, sitemap_batch_revision: 'a'.repeat(64) }
  expect(buildBaseLaunchResponseHeaders({ decision, sitemap: true })).toMatchObject({
    'X-Launch-Sitemap-Batch-Revision': 'a'.repeat(64),
  })
  expect(() => buildBaseLaunchResponseHeaders({
    decision: { ...decision, sitemap_batch_revision: null },
    sitemap: true,
  })).toThrow(/validated sitemap batch/i)
})

it('clears stale evidence before writing failed-open headers', () => {
  const event = responseEventWithHeaders({
    'X-Launch-Policy-Fingerprint': 'stale',
    'X-Launch-Sitemap-Batch-Revision': 'b'.repeat(64),
  })
  writeLaunchResponseHeaders(event, { decision: failedOpenDecision, sitemap: true })
  expect(readHeaders(event)).toMatchObject({
    'X-Launch-Indexing-Policy': 'failed-open',
    'Cache-Control': 'no-store',
  })
  expect(readHeaders(event)).not.toHaveProperty('X-Launch-Policy-Fingerprint')
  expect(readHeaders(event)).not.toHaveProperty('X-Launch-Sitemap-Batch-Revision')
})
```

Test error/404 HTML and all four root SEO handlers so the policy header appears exactly once.

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-headers.test.ts`

Expected: FAIL because legacy middleware writes only a conditional robots header.

- [ ] **Step 3: Store one request decision and finalize headers after page refinement**

```ts
const LAUNCH_HEADER_NAMES = [
  'X-Launch-Indexing-Policy',
  'X-Launch-Policy-Fingerprint',
  'X-Launch-Route-Manifest-Revision',
  'X-Launch-Backend-Policy-Revision',
  'X-Launch-Sitemap-Batch-Revision',
  'X-Launch-Sitemap-Requested-Batch',
]

export function buildBaseLaunchResponseHeaders(input: {
  decision: Readonly<LaunchSafetyDecision>
  sitemap?: boolean
  requestedBatch?: string | null
}): Record<string, string> {
  const headers: Record<string, string> = {
    'Cache-Control': 'no-store',
    'X-Launch-Indexing-Policy': input.decision.operational_state,
  }
  if (input.decision.operational_state === 'selective-open') {
    headers['X-Launch-Policy-Fingerprint'] = input.decision.policy_fingerprint!
    headers['X-Launch-Route-Manifest-Revision'] = input.decision.route_manifest_revision!
    headers['X-Launch-Backend-Policy-Revision'] = input.decision.backend_policy_revision!
    if (input.sitemap) {
      const batch = input.decision.sitemap_batch_revision || ''
      if (!/^[a-f0-9]{64}$/.test(batch)) throw new Error('validated sitemap batch revision is required')
      headers['X-Launch-Sitemap-Batch-Revision'] = batch
      if (input.requestedBatch) {
        if (input.requestedBatch !== batch) throw new Error('requested sitemap batch must match the served batch')
        headers['X-Launch-Sitemap-Requested-Batch'] = input.requestedBatch
      }
    }
  }
  return headers
}

export function writeLaunchResponseHeaders(
  event: H3Event,
  input: Parameters<typeof buildBaseLaunchResponseHeaders>[0],
): void {
  for (const name of LAUNCH_HEADER_NAMES) removeResponseHeader(event, name)
  setResponseHeaders(event, buildBaseLaunchResponseHeaders(input))
}
```

The middleware resolves the base decision into `event.context.launchSafety`. The response plugin reads the final request-scoped value after entity refinement and calls `writeLaunchResponseHeaders()`. Root SEO handlers use that same writer after their own final sitemap refinement. No handler forwards upstream launch headers or writes an evidence header directly: the writer first removes all launch evidence/echo names and then derives the exact public set from the final request decision. A successful sitemap decision must carry a validated lowercase 64-hex `sitemap_batch_revision`; failed-open and closed decisions clear/omit all evidence even if an earlier layer populated headers.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/launch-headers.test.ts && npm run typecheck`

Expected: closed/selective/failed headers are exact on success, error, and 404 responses.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/server/utils/launch/launchHeaders.ts web-nuxt/server/middleware/launch-safety.ts web-nuxt/server/plugins/launch-response.ts web-nuxt/tests/launch-headers.test.ts web-nuxt/server/middleware/noindex.ts
git commit -m "feat: finalize launch response headers"
```

### Task 23: Refine entity and ward requests without global state

**Files:**
- Create: `web-nuxt/server/utils/launch/entityPolicy.ts`
- Create: `web-nuxt/composables/useLaunchSafety.ts`
- Create: `web-nuxt/plugins/launch-safety.server.ts`
- Create: `web-nuxt/tests/launch-entity-policy.test.ts`
- Modify: `web-nuxt/pages/dia-diem/[id].vue:590-625`
- Modify: `web-nuxt/pages/xa-phuong/[id].vue:179-245`

- [ ] **Step 1: Write failing valid-negative and concurrent-failure tests**

```ts
const [failed, valid] = await Promise.all([
  Promise.resolve(refineEntityLaunchDecision({ base: selectiveOpen, carrier: { index_policy: { indexable: true } }, expectedKind: 'entity', canonicalPath: true })),
  Promise.resolve(refineEntityLaunchDecision({ base: selectiveOpen, carrier: matchingEntityPolicy(false, 'entity'), expectedKind: 'entity', canonicalPath: true })),
])

expect(failed.operational_state).toBe('failed-open')
expect(failed.policy_fingerprint).toBeNull()
expect(valid.operational_state).toBe('selective-open')
expect(valid.robots).toBe('noindex, follow')
expect(valid.sitemapDiscovery).toBe(true)

it.each([
  ['missing policy', {}],
  ['extra policy key', matchingEntityPolicy(false, 'entity', { extra: true })],
  ['wrong route kind', matchingEntityPolicy(false, 'ward')],
  ['non-boolean indexable', matchingEntityPolicy(false, 'entity', { indexable: 'false' })],
  ['non-string reason', matchingEntityPolicy(false, 'entity', { reasons: ['thin', 1] })],
  ['invalid fingerprint shape', matchingEntityPolicy(false, 'entity', { policy_fingerprint: 'not-a-digest' })],
  ['contradictory positive reasons', matchingEntityPolicy(true, 'entity', { reasons: ['description-below-130-words'] })],
  ['contradictory negative reasons', matchingEntityPolicy(false, 'entity', { reasons: [] })],
])('fails only the request for %s', (_name, carrier) => {
  const decision = refineEntityLaunchDecision({ base: selectiveOpen, carrier, expectedKind: 'entity', canonicalPath: true })
  expect(decision).toMatchObject({
    operational_state: 'failed-open',
    policy_fingerprint: null,
    route_manifest_revision: null,
    backend_policy_revision: null,
    sitemap_batch_revision: null,
    sitemapDiscovery: false,
  })
})
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-entity-policy.test.ts`

Expected: FAIL because carrier validation and request-scoped refinement do not exist.

- [ ] **Step 3: Validate the mandatory carrier and update only the current event context**

```ts
export function refineEntityLaunchDecision(input: {
  base: Readonly<LaunchSafetyDecision>
  carrier: unknown
  expectedKind: 'entity' | 'ward'
  canonicalPath: boolean
}): LaunchPageDecision {
  if (input.base.operational_state !== 'selective-open') return closedPageDecision(input.base)
  const policy = parseMatchingEntityPolicy(input.carrier, input.base, input.expectedKind)
  if (!policy) return failedOpenPageDecision('entity-policy-mismatch')
  return {
    ...input.base,
    robots: policy.indexable && input.canonicalPath ? 'index, follow' : 'noindex, follow',
    sitemapDiscovery: true,
  }
}

const INDEX_POLICY_KEYS = [
  'indexable', 'kind', 'policy_fingerprint', 'policy_revision', 'reasons',
]

export function parseMatchingEntityPolicy(
  carrier: unknown,
  base: Readonly<LaunchSafetyDecision>,
  expectedKind: 'entity' | 'ward',
): IndexPolicyDecision | null {
  if (!carrier || typeof carrier !== 'object' || Array.isArray(carrier)) return null
  const policy = (carrier as Record<string, unknown>).index_policy
  if (!policy || typeof policy !== 'object' || Array.isArray(policy)) return null
  const record = policy as Record<string, unknown>
  if (Object.keys(record).sort().join('\0') !== [...INDEX_POLICY_KEYS].sort().join('\0')) return null
  if (record.kind !== expectedKind || typeof record.indexable !== 'boolean') return null
  if (!Array.isArray(record.reasons) || record.reasons.some(reason => typeof reason !== 'string' || !reason.trim())) return null
  if (typeof record.policy_fingerprint !== 'string' || !/^[a-f0-9]{64}$/.test(record.policy_fingerprint) || record.policy_fingerprint !== base.policy_fingerprint) return null
  if (typeof record.policy_revision !== 'string' || !record.policy_revision || record.policy_revision !== base.backend_policy_revision) return null
  if ((record.indexable && record.reasons.length !== 0) || (!record.indexable && record.reasons.length === 0)) return null
  return {
    kind: expectedKind,
    indexable: record.indexable,
    reasons: [...record.reasons] as string[],
    policy_fingerprint: record.policy_fingerprint,
    policy_revision: record.policy_revision,
  }
}

function failedOpenPageDecision(reason: 'entity-policy-unavailable' | 'entity-policy-mismatch'): LaunchPageDecision {
  return {
    operational_state: 'failed-open',
    indexing_posture: 'closed',
    policy_fingerprint: null,
    route_manifest_revision: null,
    backend_policy_revision: null,
    sitemap_batch_revision: null,
    sitemap_action: 'unavailable',
    reason,
    robots: 'noindex, follow',
    sitemapDiscovery: false,
  }
}

function closedPageDecision(base: LaunchSafetyDecision): LaunchPageDecision {
  return { ...base, robots: 'noindex, follow', sitemapDiscovery: false }
}
```

Entity detail refines from its existing `/api/entities/{id}` response with `expectedKind='entity'`. Ward detail additionally fetches that same exact policy carrier for the ward ID with `expectedKind='ward'`; it does not infer eligibility from `/api/places/{id}/overview`. The strict parser accepts exactly the five `IndexPolicyDecision` keys, rejects missing/extra keys, requires a boolean `indexable`, a non-empty-string `reasons` array, a lowercase 64-hex matching fingerprint, the exact backend policy revision, route-kind agreement, and non-contradictory reason/indexable semantics. Every rejection replaces only `useRequestEvent().context.launchSafety` with a failed-open decision whose evidence fields are cleared; the server composable serializes that final page state for hydration.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/launch-entity-policy.test.ts && npm run typecheck`

Expected: valid false remains selective-open/noindex; malformed, timeout, or mismatch fails only that request.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/server/utils/launch/entityPolicy.ts web-nuxt/composables/useLaunchSafety.ts web-nuxt/plugins/launch-safety.server.ts web-nuxt/tests/launch-entity-policy.test.ts 'web-nuxt/pages/dia-diem/[id].vue' 'web-nuxt/pages/xa-phuong/[id].vue'
git commit -m "feat: refine entity launch decisions per request"
```

### Task 24: Align HTML head, robots meta, and sitemap discovery

**Files:**
- Create: `web-nuxt/tests/launch-head.test.ts`
- Modify: `web-nuxt/server/utils/launch/launchHeaders.ts`
- Modify: `web-nuxt/server/plugins/launch-response.ts`
- Modify: `web-nuxt/tests/launch-headers.test.ts`
- Modify: `web-nuxt/nuxt.config.ts:44-94`
- Modify: `web-nuxt/composables/useLaunchSafety.ts`
- Modify: `web-nuxt/pages/[...slug].vue:25`
- Modify: `web-nuxt/pages/xa-phuong/[id].vue:236`
- Modify: `web-nuxt/pages/tao-lich-trinh.vue:719`
- Modify: `web-nuxt/pages/nguoi-dung/[id].vue:488,926`
- Modify: `web-nuxt/pages/lich-trinh-chia-se/[id].vue:50`
- Modify: `web-nuxt/pages/bai-viet/[id].vue:452`
- Modify: `web-nuxt/pages/tim-kiem.vue:425`
- Modify: `web-nuxt/pages/thong-bao.vue:204`
- Modify: `web-nuxt/pages/tai-khoan.vue:175`
- Modify: `web-nuxt/pages/da-luu.vue:163`
- Modify: `web-nuxt/pages/cai-dat.vue:449`
- Modify: `web-nuxt/layouts/admin.vue:208`

- [ ] **Step 1: Write failing head-deduplication tests**

```ts
it.each([
  [closedDecision, 'noindex, follow', 0],
  [selectiveStaticDecision, 'index, follow', 1],
  [selectiveNegativeEntityDecision, 'noindex, follow', 1],
  [failedOpenDecision, 'noindex, follow', 0],
])('emits one robots meta and conditional sitemap link', (decision, robots, sitemapLinks) => {
    const head = buildLaunchHead(decision)
    expect(head.meta.filter(item => item.name === 'robots')).toEqual([{ name: 'robots', content: robots }])
    expect(head.link.filter(item => item.rel === 'sitemap')).toHaveLength(sitemapLinks)
    expect(buildLaunchResponseHeaders({ decision, html: true })['X-Robots-Tag']).toBe(robots)
})

it.each([
  ['/missing', 404, selectiveUnknownDecision, 'noindex, follow'],
  ['/dia-diem/missing', 404, entityPolicyUnavailableDecision, 'noindex, follow'],
  ['/error', 500, failedOpenDecision, 'noindex, follow'],
])('final response hook keeps error meta/header parity for %s', async (path, status, decision, robots) => {
  const response = await renderHtmlThroughFinalHook({ path, status, decision })
  expect(response.headers.get('x-robots-tag')).toBe(robots)
  expect(extractRobotsMeta(response.body)).toEqual([robots])
  expect(response.headerValues('x-robots-tag')).toEqual([robots])
})
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-head.test.ts`

Expected: FAIL because global head is indexable and always advertises `/sitemap.xml`, while pages add independent robots tags.

- [ ] **Step 3: Remove independent launch declarations and use one composable**

```ts
export function buildLaunchHead(decision: LaunchPageDecision) {
  return {
    meta: [{ name: 'robots', content: decision.robots }],
    link: decision.sitemapDiscovery
      ? [{ rel: 'sitemap', type: 'application/xml', href: '/sitemap-index.xml' }]
      : [],
  }
}

export function buildLaunchResponseHeaders(input: {
  decision: Readonly<LaunchPageDecision>
  html?: boolean
  sitemap?: boolean
  requestedBatch?: string | null
}): Record<string, string> {
  const headers = buildBaseLaunchResponseHeaders({
    decision: input.decision,
    sitemap: input.sitemap,
    requestedBatch: input.requestedBatch,
  })
  if (input.html) headers['X-Robots-Tag'] = input.decision.robots
  return headers
}

export function writeLaunchResponseHeaders(
  event: H3Event,
  input: Parameters<typeof buildLaunchResponseHeaders>[0],
): void {
  for (const name of [...LAUNCH_HEADER_NAMES, 'X-Robots-Tag']) removeResponseHeader(event, name)
  setResponseHeaders(event, buildLaunchResponseHeaders(input))
}
```

Remove the global index robots meta and unconditional sitemap link from `nuxt.config.ts`. Replace page-local launch robots declarations with `useLaunchSafety()` while keeping non-launch SEO metadata intact. Sensitive/admin pages remain noindex through route classification, not a page-owned quality predicate.

Keep Task 22's `buildBaseLaunchResponseHeaders()` as the sole state/evidence builder and make the new HTML-aware `buildLaunchResponseHeaders()` above its HTML wrapper; update tests/imports in this same commit so there is no second implementation or stale signature. Both wrappers continue to reach the response through Task 22's single `writeLaunchResponseHeaders()` authority.

The legacy `server/middleware/noindex.ts` is already deleted in Task 22. Extend the single final `beforeResponse`/`render:response` path in `server/plugins/launch-response.ts`: after entity/ward refinement and after Nuxt has selected an error/404 status, read `event.context.launchSafety` as the final `LaunchPageDecision`; force `robots='noindex, follow'` for every status `>=400` without changing a valid selective-open evidence state; replace any pre-existing case-insensitive `X-Robots-Tag`; then write exactly one header from `decision.robots`. The same final decision is serialized to `useLaunchSafety()` and passed to `buildLaunchHead()`, so meta and header cannot be computed from different base/page states. Non-HTML root SEO/API responses do not receive `X-Robots-Tag` from this hook. Add a source scan rejecting any other `X-Robots-Tag` writer or page-local launch robots predicate.

- [ ] **Step 4: Run GREEN and source scan**

Run: `cd web-nuxt && npm test -- --run tests/launch-head.test.ts tests/smoke.test.ts && npm run typecheck`

Expected: success, valid-negative, error, and 404 HTML each have one robots meta and exactly one matching final `X-Robots-Tag`; entity refinement is visible to both; the sitemap-index link appears only on fully attested selective-open HTML.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/nuxt.config.ts web-nuxt/composables/useLaunchSafety.ts web-nuxt/server/utils/launch/launchHeaders.ts web-nuxt/server/plugins/launch-response.ts web-nuxt/tests/launch-headers.test.ts web-nuxt/tests/launch-head.test.ts 'web-nuxt/pages/[...slug].vue' 'web-nuxt/pages/xa-phuong/[id].vue' web-nuxt/pages/tao-lich-trinh.vue 'web-nuxt/pages/nguoi-dung/[id].vue' 'web-nuxt/pages/lich-trinh-chia-se/[id].vue' 'web-nuxt/pages/bai-viet/[id].vue' web-nuxt/pages/tim-kiem.vue web-nuxt/pages/thong-bao.vue web-nuxt/pages/tai-khoan.vue web-nuxt/pages/da-luu.vue web-nuxt/pages/cai-dat.vue web-nuxt/layouts/admin.vue
git commit -m "feat: align launch HTML indexing signals"
```

### Task 25: Add closed robots and root sitemap handlers

**Files:**
- Create: `web-nuxt/server/utils/launch/rootSeoBodies.ts`
- Create: `web-nuxt/server/routes/robots.txt.ts`
- Create: `web-nuxt/server/routes/sitemap.xml.ts`
- Create: `web-nuxt/server/routes/sitemap-media.xml.ts`
- Create: `web-nuxt/server/routes/sitemap-index.xml.ts`
- Create: `web-nuxt/tests/launch-root-seo.test.ts`

- [ ] **Step 1: Write failing closed, open, and failed-open endpoint tests**

```ts
it('serves backend-independent closed XML shapes', async () => {
  expect(await request('/sitemap.xml')).toMatchObject({ status: 200, body: EMPTY_URLSET })
  expect(await request('/sitemap-media.xml')).toMatchObject({ status: 200, body: EMPTY_MEDIA_URLSET })
  expect(await request('/sitemap-index.xml')).toMatchObject({ status: 200, body: EMPTY_SITEMAP_INDEX })
  expect(fetchAttestation).not.toHaveBeenCalled()
})

it('returns 503 rather than empty success after failed open intent', async () => {
  setExactOpenIntent()
  fetchAttestation.mockRejectedValue(new Error('offline'))
  const response = await request('/sitemap.xml')
  expect(response.status).toBe(503)
  expect(response.headers['x-launch-indexing-policy']).toBe('failed-open')
  expect(response.headers).not.toHaveProperty('x-launch-policy-fingerprint')
  expect(response.headers).not.toHaveProperty('x-launch-sitemap-batch-revision')
})

it('writes the fourth evidence header from the validated final sitemap decision', async () => {
  setExactOpenIntent()
  const response = await request('/sitemap.xml?batch=' + 'a'.repeat(64))
  expect(response.headers).toMatchObject({
    'x-launch-indexing-policy': 'selective-open',
    'x-launch-sitemap-batch-revision': 'a'.repeat(64),
    'x-launch-sitemap-requested-batch': 'a'.repeat(64),
  })
})
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-root-seo.test.ts`

Expected: FAIL because root SEO is still proxied to FastAPI and no Nuxt handlers exist.

- [ ] **Step 3: Implement endpoint-specific bodies and decision branching**

```ts
export const EMPTY_URLSET = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
export const EMPTY_MEDIA_URLSET = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"></urlset>'
export const EMPTY_SITEMAP_INDEX = '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>'
```

Robots always permits public route groups and blocks every manifest-sensitive prefix. Closed/failed-open robots omit `Sitemap:`; selective-open robots advertises exactly `/sitemap-index.xml`. Closed sitemap handlers make zero backend calls. A selective-open sitemap handler delegates to Task 21, stores `result.decision` back into `event.context.launchSafety`, sets the returned status/body/content type, and invokes the sole Task 22 writer with `{ sitemap: true, requestedBatch: result.requestedBatch }`. The writer therefore emits the fourth evidence header only from the validated `sitemap_batch_revision` carried by the final request decision. Any query, transport, or evidence failure replaces the event decision with Task 21's evidence-cleared failed-open decision before the same writer runs, returns 503, and cannot leak base or upstream evidence. Robots and closed empty sitemap responses call the same writer with no sitemap batch flag.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/launch-root-seo.test.ts tests/launch-headers.test.ts`

Expected: all endpoint-specific shapes, policy headers, evidence, and zero-backend closed assertions pass.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/server/utils/launch/rootSeoBodies.ts web-nuxt/server/routes/robots.txt.ts web-nuxt/server/routes/sitemap.xml.ts web-nuxt/server/routes/sitemap-media.xml.ts web-nuxt/server/routes/sitemap-index.xml.ts web-nuxt/tests/launch-root-seo.test.ts
git commit -m "feat: own root SEO endpoints in Nuxt"
```

## Phase 5: Build Isolation, Readiness, and Exclusive Ingress

### Task 26: Remove policy-bearing SWR and prerender output

**Files:**
- Modify: `web-nuxt/nuxt.config.ts:141-238`
- Modify: `scripts/build-prerender.sh`
- Create: `web-nuxt/tests/launch-cache-isolation.test.ts`

- [ ] **Step 1: Write failing source/output audit tests**

```ts
it('contains no policy-bearing SWR or prerender routes', () => {
  const config = readFileSync('nuxt.config.ts', 'utf8')
  for (const path of ['/dia-diem/**', '/api/entities/**', '/sitemap.xml', 'prerender:']) {
    expect(config).not.toContain(path)
  }
})
```

Add a built-output fixture test that fails when a public HTML file or cache rule is injected into the audit input.

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-cache-isolation.test.ts`

Expected: FAIL because current route rules use SWR and Nitro prerenders public routes.

- [ ] **Step 3: Remove all policy-bearing caching and retire the backend-gated prerender path**

Keep only content-addressed asset caching:

```ts
routeRules: {
  '/_nuxt/**': { headers: { 'cache-control': 'public, max-age=31536000, immutable' } },
  '/**': { headers: SECURITY_HEADERS },
}
```

Remove `nitro.prerender.routes`, `nuxt generate` use from launch/release scripts, root SEO proxy rules, and every SWR/ISR rule for public HTML/API. Repurpose `scripts/build-prerender.sh` into a launch-compatible build wrapper or remove all call sites and delete it.

- [ ] **Step 4: Run GREEN and build**

Run: `cd web-nuxt && npm test -- --run tests/launch-cache-isolation.test.ts && npm run build`

Expected: no policy-bearing prerender/cache artifact and build exits 0.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/nuxt.config.ts web-nuxt/tests/launch-cache-isolation.test.ts scripts/build-prerender.sh web-nuxt/package.json scripts
git commit -m "fix: remove policy-bearing Nuxt caches"
```

### Task 27: Restrict the service worker to policy-neutral assets

**Files:**
- Modify: `web-nuxt/public/sw.js`
- Create: `web-nuxt/tests/service-worker-policy.test.ts`

- [ ] **Step 1: Write failing bypass and purge tests**

```ts
for (const request of [
  new Request('https://vinhlong360.vn/', { mode: 'navigate' }),
  new Request('https://vinhlong360.vn/robots.txt'),
  new Request('https://vinhlong360.vn/api/entities/a'),
  new Request('https://vinhlong360.vn/events'),
  new Request('https://vinhlong360.vn/seo/jsonld/a'),
]) {
  const respondWith = vi.fn()
  dispatchFetch(request, respondWith)
  expect(respondWith).not.toHaveBeenCalled()
}

expect(await activateWithCaches(['vl360-v3-html', 'vl360-v3-assets', 'vl360-launch-assets-v1']))
  .toEqual(['vl360-launch-assets-v1'])
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/service-worker-policy.test.ts`

Expected: FAIL because the current worker caches navigation/HTML and retains `vl360-v3-html`.

- [ ] **Step 3: Implement an explicit asset allowlist and response no-store check**

```js
const CACHE_VERSION = 'vl360-launch-v1'
const ASSET_CACHE = `${CACHE_VERSION}-assets`
const PRECACHE = ['/manifest.json', '/favicon.svg']

function mustBypass(request, url) {
  const accept = request.headers.get('accept') || ''
  return request.method !== 'GET' || request.mode === 'navigate' || accept.includes('text/html') ||
    url.pathname === '/robots.txt' || url.pathname.startsWith('/sitemap') ||
    url.pathname.startsWith('/_internal/') || url.pathname.startsWith('/api/') ||
    ['/events', '/recommend'].includes(url.pathname) || url.pathname.startsWith('/seo/') ||
    request.cache === 'no-store'
}
```

Cache only `/_nuxt/**`, reviewed fonts/icons, and `PRECACHE`. Before every `cache.put`, reject a response whose `Cache-Control` contains `no-store`. Activation deletes every cache except the new asset cache.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/service-worker-policy.test.ts`

Expected: navigation, API, SEO, and no-store requests are never intercepted; legacy caches are deleted.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/public/sw.js web-nuxt/tests/service-worker-policy.test.ts
git commit -m "fix: isolate the service worker asset cache"
```

### Task 28: Generate and validate the launch readiness manifest

**Files:**
- Create: `web-nuxt/scripts/generate-launch-readiness-manifest.mjs`
- Create: `web-nuxt/server/utils/launch/readinessManifest.ts`
- Create: `web-nuxt/tests/launch-readiness-manifest.test.ts`
- Modify: `web-nuxt/public/sw.js`
- Modify: `web-nuxt/tests/service-worker-policy.test.ts`
- Modify: `web-nuxt/package.json`

- [ ] **Step 1: Write failing generated-manifest tests**

```ts
it('rejects a policy-bearing prerender artifact', () => {
  expect(() => validateReadinessManifest({
    ...validManifest,
    public_prerender_files: ['public/index.html'],
  })).toThrow(/policy-bearing prerender/i)
})

it('requires the final service-worker digest', () => {
  expect(validateReadinessManifest(validManifest).service_worker.rule_digest).toMatch(/^[a-f0-9]{64}$/)
})

it('requires both artifact revisions as well as digests', () => {
  expect(validateReadinessManifest(validManifest).artifacts).toMatchObject({
    route_manifest: { revision: 'launch-indexing-policy-v1', sha256: expect.stringMatching(/^[a-f0-9]{64}$/) },
    ai_disclosure: { revision: 'ai-disclosure-v1', sha256: expect.stringMatching(/^[a-f0-9]{64}$/) },
  })
  expect(() => validateReadinessManifest({
    ...validManifest,
    artifacts: { ...validManifest.artifacts, route_manifest: { ...validManifest.artifacts.route_manifest, revision: '' } },
  })).toThrow(/artifact revision/i)
})

it.each(['missing', 'wrong-retained-cache', 'unverified'])('rejects %s cache-purge declaration', mutation => {
  expect(() => validateReadinessManifest(mutateCachePurge(validManifest, mutation)))
    .toThrow(/cache purge/i)
})
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-readiness-manifest.test.ts`

Expected: FAIL because no post-build audit or strict manifest loader exists.

- [ ] **Step 3: Generate one evidence manifest after `nuxt build`**

```json
{
  "schema_version": 1,
  "build_revision": "source-revision",
  "artifacts": {
    "route_manifest": {"revision": "launch-indexing-policy-v1", "sha256": "64-hex"},
    "ai_disclosure": {"revision": "ai-disclosure-v1", "sha256": "64-hex"},
    "policy_fingerprint": "64-hex"
  },
  "policy_route_classes": ["public-html", "public-api", "root-seo", "internal-readiness"],
  "compiled_cache_rules": [],
  "public_prerender_files": [],
  "service_worker": {
    "version": "vl360-launch-v1",
    "rule_digest": "64-hex",
    "cache_purge": {
      "revision": "launch-cache-purge-v1",
      "strategy": "delete-all-except",
      "retained_cache_names": ["vl360-launch-v1-assets"],
      "forbidden_cache_classes": ["navigation", "html", "root-seo", "internal", "api", "selective-open", "failed-open"],
      "activation_verified": true
    }
  }
}
```

Add the same exact `CACHE_PURGE_DECLARATION` object to `public/sw.js`; activation computes the retained set from `retained_cache_names` and deletes every other cache. The generator scans `.output`, compiled route rules, and `public/sw.js`, executes the worker activation in the existing fake-cache harness with caches representing every forbidden class, and sets `activation_verified=true` only when all forbidden caches are deleted and exactly `vl360-launch-v1-assets` remains. It recomputes both root artifact SHA-256 values, reads both artifact revisions through the strict loaders, recomputes the full Task 9/20 fingerprint, hashes the final worker rule source, writes `.output/server/launch-readiness-manifest.json`, and exits non-zero on any revision/digest/purge mismatch or unsafe artifact. The runtime validator repeats the exact declaration comparison and treats a missing, false, stale, or altered cache-purge declaration as readiness 503. Add the generator after `nuxt build` in the build script.

- [ ] **Step 4: Run GREEN and build audit**

Run: `cd web-nuxt && npm test -- --run tests/launch-readiness-manifest.test.ts && npm run build`

Expected: generated manifest exists, validates both artifact revision+digest pairs, records the final worker version/rule digest, and proves the exact cache-purge declaration against a controlled activation.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/scripts/generate-launch-readiness-manifest.mjs web-nuxt/server/utils/launch/readinessManifest.ts web-nuxt/tests/launch-readiness-manifest.test.ts web-nuxt/public/sw.js web-nuxt/tests/service-worker-policy.test.ts web-nuxt/package.json
git commit -m "build: generate launch readiness evidence"
```

### Task 29: Add the process-local launch readiness endpoint

**Files:**
- Create: `web-nuxt/server/routes/_internal/launch-readiness.get.ts`
- Create: `web-nuxt/tests/launch-readiness.test.ts`
- Modify: `web-nuxt/server/utils/launch/readinessManifest.ts`

- [ ] **Step 1: Write failing safe-closed/safe-open/unsafe tests**

```ts
it('returns safe closed without a backend call', async () => {
  const response = await readiness({ env: {}, fetchAttestation: vi.fn() })
  expect(response.status).toBe(200)
  expect(response.body.state).toBe('closed')
  expect(response.fetchAttestation).not.toHaveBeenCalled()
})

it('returns 503 for exact open intent without an active bundle', async () => {
  const response = await readiness({ env: exactOpenEnv, fetchAttestation: matchingWithoutBundle })
  expect(response.status).toBe(503)
  expect(response.body.reason).toBe('sitemap-batch-unavailable')
})

it('preserves the guarded sitemap evidence-mismatch reason', async () => {
  const response = await readiness({
    env: exactOpenEnv,
    fetchAttestation: matchingAttestation,
    fetchSitemap: sitemapWithMismatchedEvidence,
  })
  expect(response.status).toBe(503)
  expect(response.body.reason).toBe('sitemap-evidence-mismatch')
})
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-readiness.test.ts`

Expected: FAIL because the endpoint does not exist.

- [ ] **Step 3: Implement stable machine-readable checks**

```ts
export default defineEventHandler(async (event) => {
  setHeader(event, 'Cache-Control', 'no-store')
  const build = loadAndValidateReadinessManifest()
  const intent = readLaunchIntent(process.env)
  if (!intent.openIntent) return { ok: true, state: 'closed', checks: build.checks }
  const decision = await resolveBaseLaunchSafetyDecision({
    env: process.env,
    build: build.evidence,
    fetchAttestation: () => fetchBackendAttestation(event),
  })
  if (decision.operational_state !== 'selective-open') {
    throw createError({ statusCode: 503, data: { ok: false, reason: decision.reason } })
  }
  const active = await fetchAndValidateActiveSitemapIndex(event, decision)
  if (active.decision.reason === 'sitemap-evidence-mismatch') {
    throw createError({ statusCode: 503, data: { ok: false, reason: active.decision.reason } })
  }
  if (!active.batchRevision) {
    const reason = active.decision.reason === 'sitemap-batch-unavailable'
      ? active.decision.reason
      : 'sitemap-batch-unavailable'
    throw createError({ statusCode: 503, data: { ok: false, reason } })
  }
  return { ok: true, state: 'selective-open', active_batch: active.batchRevision, checks: build.checks }
})
```

Do not return unlock values, backend URLs, free-form errors, or legal/owner evidence.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/launch-readiness.test.ts tests/launch-readiness-manifest.test.ts`

Expected: safe closed is backend-independent; safe open requires matching attestation and active bundle; every unsafe check is 503; guarded sitemap failures preserve the exact `sitemap-batch-unavailable` versus `sitemap-evidence-mismatch` reason.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/server/routes/_internal/launch-readiness.get.ts web-nuxt/tests/launch-readiness.test.ts web-nuxt/server/utils/launch/readinessManifest.ts
git commit -m "feat: expose internal launch readiness"
```

### Task 30: Enforce exclusive production network topology

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docker-compose.prod.yml`
- Create: `docker-compose.dev.yml`
- Create: `docker-compose.systemd-deps.yml`
- Create: `ops/systemd/vl-agent.service`
- Create: `ops/systemd/vl-nuxt.service`
- Create: `ops/systemd/vl-bot.service`
- Create: `ops/systemd/vl-watchdog.service`
- Create: `ops/systemd/vl-watchdog.timer`
- Modify: `agent/server.py:4363`
- Modify: `agent/bot_gateway.py:1042`
- Create: `scripts/ops/compose_network_audit.py`
- Create: `scripts/ops/socket_boundary_probe.py`
- Create: `tests/launch_safety/test_compose_contract.py`
- Create: `tests/launch_safety/test_systemd_contract.py`
- Create: `tests/launch_safety/integration/test_compose_cold_start.py`
- Create: `tests/launch_safety/integration/test_network_boundary.py`

- [ ] **Step 1: Write failing rendered-topology and cold-start tests**

```python
def test_production_compose_publishes_only_nginx(rendered_compose):
    published = published_ports(rendered_compose)
    assert published == {("nginx", 80), ("nginx", 443)}
    assert rendered_compose["services"]["nginx"]["depends_on"] == {
        "nuxt": {"condition": "service_healthy"},
    }


@pytest.mark.integration
def test_agent_absent_closed_cold_start(compose_harness):
    result = compose_harness.start_nuxt_only(open_intent=False, include_agent=False)
    assert result.nuxt_readiness == (200, "closed")
    assert result.nuxt_internal_listener is True
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_compose_contract.py tests/launch_safety/test_systemd_contract.py -q`

Expected: FAIL because base Compose publishes all service ports, Nuxt depends on agent, and tracked systemd units do not exist.

- [ ] **Step 3: Split full-container, developer, and hybrid-systemd topologies**

Production full-container Compose uses `expose` for internal ports and only Nginx `ports`. `docker-compose.dev.yml` contains explicit loopback publications. `docker-compose.systemd-deps.yml` is a separately audited hybrid-host dependency model with only `127.0.0.1:5432` and `127.0.0.1:6379` for systemd applications; it is never merged into the exclusive full-container production audit.

```yaml
nuxt:
  expose: ["3000"]
  healthcheck:
    test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:3000/_internal/launch-readiness >/dev/null"]
nginx:
  depends_on:
    nuxt:
      condition: service_healthy
```

Add secure bind-host environment support: agent/bot default to `127.0.0.1`; their container services explicitly set `BIND_HOST=0.0.0.0`. Nuxt systemd sets `HOST=127.0.0.1`, `NITRO_HOST=127.0.0.1`.

Materialize the watchdog service/timer examples currently documented in `scripts/ops/systemd-units.md`; Task 44 later changes their probe/maintenance ordering but must not invent the unit files from scratch.

- [ ] **Step 4: Run GREEN and opt-in cold-start integration**

Run: `python -m pytest tests/launch_safety/test_compose_contract.py tests/launch_safety/test_systemd_contract.py -q`

Run when Docker is available: `python -m pytest tests/launch_safety/integration/test_compose_cold_start.py tests/launch_safety/integration/test_network_boundary.py -m integration -q`

Expected: closed/agent-absent Nuxt is healthy on the private network; exact-open/agent-absent Nuxt is unhealthy and admits no listener; the live socket probe proves only Nginx owns non-loopback 80/443 while agent, Nuxt, bot, PostgreSQL, and Redis remain private or loopback-only. Task 32 adds optional-upstream rendering before any integration test starts Nginx with agent absent.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml docker-compose.prod.yml docker-compose.dev.yml docker-compose.systemd-deps.yml ops/systemd agent/server.py agent/bot_gateway.py scripts/ops/compose_network_audit.py scripts/ops/socket_boundary_probe.py tests/launch_safety/test_compose_contract.py tests/launch_safety/test_systemd_contract.py tests/launch_safety/integration/test_compose_cold_start.py tests/launch_safety/integration/test_network_boundary.py
git commit -m "ops: enforce exclusive launch ingress topology"
```

### Task 31: Wire readiness into build and local deploy admission

**Files:**
- Modify: `scripts/package_launch_release.py`
- Modify: `scripts/deploy.sh:94-199`
- Modify: `web-nuxt/Dockerfile`
- Modify: `Dockerfile`
- Modify: `tests/test_release_quality_gates.py`
- Modify: `tests/launch_safety/test_release_package.py`
- Create: `ops/nginx/maintenance/http-context.conf.template`
- Create: `ops/nginx/maintenance/server-enabled.conf`
- Create: `ops/nginx/maintenance/server-disabled.conf`
- Create: `scripts/ops/maintenance_mode.sh`
- Create: `scripts/ops/deploy_launch_admission.sh`
- Create: `scripts/ops/probe_launch_boundary.py`
- Create: `tests/launch_safety/test_deploy_readiness.py`

- [ ] **Step 1: Write failing combined-package and deploy-admission tests**

```python
def test_build_launch_release_has_exact_payload_manifest_and_archive_digest(release_source, tmp_path):
    result = build_launch_release(
        release_source,
        tmp_path / "vl360-launch-release.tar.gz",
        compose_network_audit=release_source / "build/compose-network-audit.json",
        source_revision="reviewed-source-revision",
    )
    members = read_tar_members(result.archive)
    manifest = read_tar_json(result.archive, "launch-release-manifest.json")

    assert members == expected_launch_release_members(release_source)
    assert not any(name == "agent/data" or name.startswith("agent/data/") for name in members)
    assert "docker-compose.dev.yml" not in members
    assert manifest["package_kind"] == "vl360-launch-release"
    assert manifest["launch_posture"] == "closed"
    assert manifest["developer_override"] == {"path": "docker-compose.dev.yml", "included": False}
    assert manifest["persistent_paths"] == ["agent/data", "agent/data/sitemap-bundles"]
    assert manifest["members"] == sha256_size_map(result.archive, exclude={"launch-release-manifest.json"})
    assert result.digest_file.read_text(encoding="ascii") == (
        f"{sha256_file(result.archive)}  {result.archive.name}\n"
    )


def test_deploy_uses_internal_readiness_not_homepage():
    script = Path("scripts/deploy.sh").read_text(encoding="utf-8")
    assert "_internal/launch-readiness" in script
    assert "curl -f http://localhost:3000/" not in script
    assert "systemctl restart vl-agent vl-nuxt" not in script


def test_release_contains_config_ingress_units_and_network_audit(release_members):
    assert {"config", "nginx.conf", "nginx-ssl.conf", "ops/systemd", "compose-network-audit.json"} <= release_members


def test_deploy_closes_traffic_before_install_and_reopens_only_after_readiness(deploy_stub):
    result = deploy_stub.run_closed_release()
    assert result.exit_code == 0
    assert result.commands == [
        "maintenance-enable", "nginx-test-closed", "nginx-reload-closed", "maintenance-probe",
        "verify-archive", "install-release", "restart-services",
        "process-local-readiness", "listener-boundary",
        "maintenance-disable", "nginx-test-open", "nginx-reload-open", "post-reopen-closed-probe",
    ]


@pytest.mark.parametrize("failure", ["install-release", "restart-services", "process-local-readiness", "listener-boundary"])
def test_deploy_failure_never_reopens_traffic(deploy_stub, failure):
    result = deploy_stub.fail_at(failure)
    assert result.maintenance_enabled is True
    assert "maintenance-disable" not in result.commands
    assert "nginx-reload-open" not in result.commands
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_release_package.py tests/launch_safety/test_deploy_readiness.py tests/test_release_quality_gates.py -q`

Expected: FAIL because `build_launch_release`, the combined archive manifest/digest, the tracked maintenance/admission primitive, and command-order enforcement do not exist.

- [ ] **Step 3: Build one combined archive and add a fail-closed admission primitive**

`build_launch_release()` is the only launch-compatible release/rehearsal archive authority. Its exact signature and result are:

```python
@dataclass(frozen=True)
class LaunchReleasePackage:
    archive: Path
    digest_file: Path
    manifest: Mapping[str, object]


def build_launch_release(
    root: Path,
    destination: Path,
    *,
    compose_network_audit: Path,
    source_revision: str,
) -> LaunchReleasePackage:
    payload = collect_launch_release_payload(root, compose_network_audit)
    manifest = build_launch_release_manifest(root, payload, source_revision)
    write_deterministic_tar_gz(destination, payload, {"launch-release-manifest.json": canonical_json_bytes(manifest)})
    digest_file = destination.with_name(destination.name + ".sha256")
    digest_file.write_text(f"{sha256_file(destination)}  {destination.name}\n", encoding="ascii")
    return LaunchReleasePackage(destination, digest_file, MappingProxyType(manifest))
```

The archive has these exact top-level authorities: `agent/` excluding all `agent/data/**`; `web-nuxt/.output/`, `web-nuxt/package.json`, and the production lockfile; root `config/`; `requirements.txt`; `init.sql`; `nginx.conf`; `nginx-ssl.conf`; `ops/systemd/`; `ops/nginx/maintenance/`; production `scripts/ops/`; `compose-network-audit.json`; and `launch-release-manifest.json`. It contains no `.git`, tests, docs, developer Compose override, environment file, secret, unlock key, runtime cache, or persistent data. Tar member order, uid/gid, names, modes, and timestamps are normalized.

`launch-release-manifest.json` has exact keys `schema_version`, `package_kind`, `source_revision`, `launch_posture`, `canonical_artifacts`, `readiness_manifest`, `network_audit`, `developer_override`, `persistent_paths`, and `members`. `canonical_artifacts` records both canonical revisions and SHA-256 digests; `readiness_manifest` and `network_audit` record path+digest; `members` records SHA-256 and byte length for every payload member except the manifest itself. The manifest fixes `launch_posture="closed"`, `developer_override={"path":"docker-compose.dev.yml","included":false}`, and `persistent_paths=["agent/data","agent/data/sitemap-bundles"]`. The adjacent `.sha256` file authenticates the complete archive bytes without a circular in-archive digest.

The local build command is deterministic and never deploys:

```bash
python scripts/ops/compose_network_audit.py --compose docker-compose.yml --production docker-compose.prod.yml --output build/compose-network-audit.json
python scripts/package_launch_release.py launch-release --root . --destination dist/vl360-launch-release.tar.gz --compose-network-audit build/compose-network-audit.json --source-revision "$(git rev-parse HEAD)"
```

Update the build to run the Task 28 output audit before packaging. `scripts/deploy.sh` sources `scripts/ops/deploy_launch_admission.sh`; the reusable primitive owns the order below and accepts an injectable `RUNNER` for deterministic tests:

```bash
close_launch_admission() {
  "$RUNNER" scripts/ops/maintenance_mode.sh enable --operator-cidr "${OPERATOR_CIDR:?}"
  "$RUNNER" nginx -t
  "$RUNNER" systemctl reload nginx
  "$RUNNER" python scripts/ops/probe_launch_boundary.py --expect maintenance --operator-source
}

verify_before_reopen() {
  "$RUNNER" curl --fail --silent --show-error \
    http://127.0.0.1:3000/_internal/launch-readiness >"${READINESS_EVIDENCE:?}"
  "$RUNNER" python scripts/ops/socket_boundary_probe.py \
    --expect-nginx-public-only --expect-loopback 3000 8360
}

reopen_launch_admission() {
  verify_before_reopen
  "$RUNNER" scripts/ops/maintenance_mode.sh disable --operator-cidr "${OPERATOR_CIDR:?}"
  "$RUNNER" nginx -t
  "$RUNNER" systemctl reload nginx
  if ! "$RUNNER" python scripts/ops/probe_launch_boundary.py --expect closed --require-public-post-reopen-matrix; then
    "$RUNNER" scripts/ops/maintenance_mode.sh enable --operator-cidr "${OPERATOR_CIDR:?}"
    "$RUNNER" nginx -t
    "$RUNNER" systemctl reload nginx
    return 1
  fi
}
```

`maintenance_mode.sh` atomically selects the tracked enabled/disabled include, runs `nginx -t`, and never reloads an invalid configuration. The deploy sequence calls `close_launch_admission` before archive verification, install, or service restart; any failure from that boundary onward leaves maintenance enabled. Only `reopen_launch_admission` may disable maintenance, and it runs process-local readiness and listener isolation first. Backend/Nuxt/config/units/rendered-ingress bytes must match the combined manifest. Do not execute a real deploy in this task.

Task 31 creates the minimal `probe_launch_boundary.py` authority with exact `--expect maintenance --operator-source` and `--expect closed --require-public-post-reopen-matrix` modes. It checks status, policy/meta/header `noindex`, robots without discovery, three empty sitemap shapes, `no-store`, and absent launch evidence for the closed matrix. Task 43 later modifies this same file to add the selective-open and browser-matrix modes; no Task 31 command references a file created by a later task.

- [ ] **Step 4: Run GREEN and syntax/build verification**

Run: `python -m pytest tests/launch_safety/test_release_package.py tests/launch_safety/test_deploy_readiness.py tests/test_release_quality_gates.py -q`

Run: `& 'C:\Program Files\Git\bin\bash.exe' -n scripts/deploy.sh`

Run: `& 'C:\Program Files\Git\bin\bash.exe' -n scripts/ops/maintenance_mode.sh`

Run: `& 'C:\Program Files\Git\bin\bash.exe' -n scripts/ops/deploy_launch_admission.sh`

Run when Docker is available: `docker build -f web-nuxt/Dockerfile -t vl360-nuxt:launch-safety .`

Expected: tests and syntax pass; the build contains canonical digests and readiness evidence; the combined archive and sidecar digest validate; stub logs prove maintenance closes before install/restart and cannot reopen until readiness plus listener isolation pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/package_launch_release.py scripts/deploy.sh web-nuxt/Dockerfile Dockerfile ops/nginx/maintenance scripts/ops/maintenance_mode.sh scripts/ops/deploy_launch_admission.sh scripts/ops/probe_launch_boundary.py tests/test_release_quality_gates.py tests/launch_safety/test_release_package.py tests/launch_safety/test_deploy_readiness.py
git commit -m "ops: gate launch packages on readiness"
```

### Task 32: Make Nginx the exclusive launch-aware ingress

**Files:**
- Modify: `nginx.conf`
- Modify: `nginx-ssl.conf`
- Create: `scripts/ops/render_nginx_config.py`
- Modify: `tests/launch_safety/test_nginx_contract.py`
- Create: `tests/launch_safety/harness/docker-compose.yml`
- Create: `tests/launch_safety/harness/stub_upstream.py`
- Create: `tests/launch_safety/integration/test_nginx_boundary.py`
- Modify: `docs/api-contract.md`

- [ ] **Step 1: Write failing routing, denial, boundary, and optional-upstream tests**

```python
def test_root_seo_is_nuxt_owned(nginx_configs):
    for config in nginx_configs:
        assert_exact_upstream(config, "/robots.txt", "nuxt")
        assert_exact_upstream(config, "/sitemap.xml", "nuxt")
        assert_exact_upstream(config, "/sitemap-media.xml", "nuxt")
        assert_exact_upstream(config, "/sitemap-index.xml", "nuxt")
        assert_public_not_found(config, "/_internal/launch-readiness")
        assert_public_not_found(config, "/_internal/launch-policy-attestation")


def test_backend_prefixes_use_segment_boundaries(nginx_configs):
    assert_backend_route(nginx_configs, "/system")
    assert_backend_route(nginx_configs, "/system/x")
    assert_not_backend_route(nginx_configs, "/systematic")
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_nginx_contract.py -q`

Expected: FAIL because root SEO goes to FastAPI, cache is enabled in SSL config, internal paths are exposed, and locations lack end-or-slash boundaries.

- [ ] **Step 3: Render topology-specific upstreams and preserve query/header contracts**

Compose rendering uses Docker DNS request-time resolution for optional agent/bot upstreams:

```nginx
resolver 127.0.0.11 valid=5s ipv6=off;
set $agent_upstream http://agent:8360;
location ~ ^/(api|auth|chat)(?:/|$) {
    proxy_pass $agent_upstream$request_uri;
}
```

Systemd rendering uses literal loopback targets. Do not use a URI suffix with variable `proxy_pass`; preserve raw path/query and keep `/admin-api` rewrite behavior covered by integration tests. Add exact root SEO locations to Nuxt, disable proxy caching, preserve policy/evidence headers, deny all launch-internal paths, and parity-check every agent/bot alias against the route manifest. The disposable `tests/launch_safety/harness/docker-compose.yml` publishes only its test Nginx service at `127.0.0.1:18080`; its internal agent/Nuxt ports remain unpublished, and teardown always uses `down -v --remove-orphans`.

- [ ] **Step 4: Run GREEN and opt-in Nginx harness**

Run: `python -m pytest tests/launch_safety/test_nginx_contract.py -q`

Run when Docker/Nginx is available: `python -m pytest tests/launch_safety/integration/test_nginx_boundary.py -m integration -q`

Expected: query-pinned sitemap paths arrive intact, internal paths return 404, headers are preserved, no proxy cache replays policy responses, and optional absent upstreams do not prevent closed Nginx startup.

- [ ] **Step 5: Commit**

```bash
git add nginx.conf nginx-ssl.conf scripts/ops/render_nginx_config.py tests/launch_safety/test_nginx_contract.py tests/launch_safety/harness tests/launch_safety/integration/test_nginx_boundary.py docs/api-contract.md
git commit -m "ops: route launch traffic through guarded ingress"
```

## Phase 6: Shared Image Descriptors and Point-of-Use Disclosure

### Task 33: Introduce the shared image descriptor and mixed gallery API

**Files:**
- Modify: `agent/image_descriptor.py`
- Modify: `agent/tests/test_image_descriptor.py`
- Modify: `agent/api_schemas.py`
- Modify: `agent/public_api.py:2532-2585`
- Create: `web-nuxt/types/image.ts`
- Create: `web-nuxt/utils/imageDescriptors.ts`
- Modify: `web-nuxt/types/api.ts`
- Create: `web-nuxt/tests/image-descriptors.test.ts`

- [ ] **Step 1: Write failing Python and TypeScript descriptor tests**

```python
def test_entity_and_review_images_have_distinct_source_classes(disclosure):
    entity = describe_entity_image("/img/entity.webp", entity_name="Chùa Vàm Ray", index=0, disclosure=disclosure)
    review = describe_review_image("/img/review.jpg", entity_name="Chùa Vàm Ray", credit="Lan", disclosure=disclosure)
    assert entity.source_class == "ai-generated"
    assert entity.source_kind == "entity-editorial"
    assert review.source_class == "user-uploaded"
    assert review.source_kind == "review-ugc"


@pytest.mark.parametrize("url", ["/img/entity.webp", "/media/entity.webp?v=2", "https://cdn.example/entity.webp"])
def test_backend_accepts_only_canonical_local_paths_or_https(url):
    assert normalize_renderable_image_url(url) == url


@pytest.mark.parametrize("url", [
    "//cdn.example/entity.webp", "http://cdn.example/entity.webp", "data:image/png;base64,AA==",
    "javascript:alert(1)", "ftp://cdn.example/entity.webp", "/img\\entity.webp",
])
def test_backend_rejects_unsafe_image_urls(url):
    assert normalize_renderable_image_url(url) is None
```

```ts
expect(parseGalleryDescriptor(apiEntityImage)!.source_class).toBe('ai-generated')
expect(parseGalleryDescriptor(apiReviewImage)!.source_class).toBe('user-uploaded')

it.each(['/img/entity.webp', '/media/entity.webp?v=2', 'https://cdn.example/entity.webp'])(
  'accepts the same renderable URL forms as the backend: %s',
  (url) => expect(parseGalleryDescriptor({ ...apiEntityImage, url })?.url).toBe(url),
)

it.each([
  '//cdn.example/entity.webp', 'http://cdn.example/entity.webp', 'data:image/png;base64,AA==',
  'javascript:alert(1)', 'ftp://cdn.example/entity.webp', '/img\\entity.webp',
])('rejects unsafe URL form %s', (url) => {
  expect(parseGalleryDescriptor({ ...apiEntityImage, url })).toBeNull()
})

it.each([
  ['extra key', { ...apiReviewImage, extra: true }],
  ['unclassified UGC', { ...apiReviewImage, source_class: 'user-uploaded', source_kind: 'entity-editorial' }],
  ['AI copy on UGC', { ...apiReviewImage, full_disclosure: aiDisclosure.entity_ai.full_disclosure }],
  ['blank alt', { ...apiReviewImage, alt: ' ' }],
  ['blank credit', { ...apiReviewImage, credit: ' ' }],
  ['fractional width', { ...apiReviewImage, width: 640.5, height: 480 }],
  ['partial dimensions', { ...apiReviewImage, width: 640, height: null }],
])('rejects %s', (_name, value) => {
  expect(parseGalleryDescriptor(value)).toBeNull()
})
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_image_descriptor.py -q`

Run: `cd web-nuxt && npm test -- --run tests/image-descriptors.test.ts`

Expected: FAIL because gallery responses are untyped dictionaries and frontend types contain only bare URLs.

- [ ] **Step 3: Add strict descriptor producers and API models**

```python
@dataclass(frozen=True)
class ImageDescriptor:
    url: str | None
    alt: str
    source_class: str
    source_kind: str
    disclosure_key: str
    short_label: str | None
    full_disclosure: str
    credit: str | None
    width: int | None
    height: int | None


def describe_entity_image(raw, *, entity_name: str, index: int, disclosure) -> ImageDescriptor | None:
    url = normalize_renderable_image_url(raw)
    if not url:
        return None
    return ImageDescriptor(
        url=url,
        alt=f"{entity_name} — ảnh minh họa {index + 1}",
        source_class="ai-generated",
        source_kind="entity-editorial",
        disclosure_key="entity-ai",
        short_label=disclosure.entity_ai.short_label,
        full_disclosure=disclosure.entity_ai.full_disclosure,
        credit=None,
        width=None,
        height=None,
    )


def describe_review_image(raw, *, entity_name: str, credit: str | None, disclosure) -> ImageDescriptor | None:
    url = normalize_renderable_image_url(raw)
    if not url:
        return None
    return ImageDescriptor(
        url=url,
        alt=f"{entity_name} — ảnh đánh giá",
        source_class="user-uploaded",
        source_kind="review-ugc",
        disclosure_key="ugc-photo",
        short_label=disclosure.ugc_photo.short_label,
        full_disclosure=disclosure.ugc_photo.full_disclosure,
        credit=credit,
        width=None,
        height=None,
    )
```

Entity images always use `ai-generated/entity-editorial`; generated graphics use `placeholder/generated-placeholder`; review/post media use `user-uploaded`. Update `/api/entities/{entity_id}/gallery` to return `{ images: ImageDescriptor[] }` with entity images first and review images second.

```ts
export interface ImageDescriptor {
  url: string | null
  alt: string
  source_class: 'ai-generated' | 'placeholder' | 'user-uploaded'
  source_kind: 'entity-editorial' | 'generated-placeholder' | 'review-ugc' | 'post-ugc'
  disclosure_key: 'entity-ai' | 'entity-placeholder' | 'ugc-photo'
  short_label: string | null
  full_disclosure: string
  credit: string | null
  width: number | null
  height: number | null
}

const DESCRIPTOR_KEYS = [
  'alt', 'credit', 'disclosure_key', 'full_disclosure', 'height',
  'short_label', 'source_class', 'source_kind', 'url', 'width',
]

const ALLOWED_SOURCE_COMBINATIONS = new Set([
  'ai-generated|entity-editorial|entity-ai',
  'placeholder|generated-placeholder|entity-placeholder',
  'user-uploaded|review-ugc|ugc-photo',
  'user-uploaded|post-ugc|ugc-photo',
])

export function normalizeRenderableImageUrl(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const url = value.trim()
  if (!url || /[\u0000-\u0020\u007f\\]/.test(url) || url.includes('#')) return null
  if (url.startsWith('//')) return null
  if (url.startsWith('/')) return url
  try {
    const parsed = new URL(url)
    if (parsed.protocol !== 'https:' || !parsed.hostname || parsed.username || parsed.password) return null
    return url
  } catch {
    return null
  }
}

export function parseGalleryDescriptor(value: unknown): ImageDescriptor | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const descriptor = value as Record<string, unknown>
  if (Object.keys(descriptor).sort().join('\0') !== [...DESCRIPTOR_KEYS].sort().join('\0')) return null
  const normalizedUrl = descriptor.url === null ? null : normalizeRenderableImageUrl(descriptor.url)
  if (descriptor.url !== null && normalizedUrl === null) return null
  if (typeof descriptor.alt !== 'string' || !descriptor.alt.trim()) return null
  if (descriptor.credit !== null && (typeof descriptor.credit !== 'string' || !descriptor.credit.trim())) return null
  if (descriptor.short_label !== null && (typeof descriptor.short_label !== 'string' || !descriptor.short_label.trim())) return null
  if (typeof descriptor.full_disclosure !== 'string' || !descriptor.full_disclosure.trim()) return null
  const combination = `${descriptor.source_class}|${descriptor.source_kind}|${descriptor.disclosure_key}`
  if (!ALLOWED_SOURCE_COMBINATIONS.has(combination)) return null

  const canonical = descriptor.disclosure_key === 'entity-ai'
    ? aiDisclosure.entity_ai
    : descriptor.disclosure_key === 'entity-placeholder'
      ? aiDisclosure.placeholder
      : aiDisclosure.ugc_photo
  if (descriptor.short_label !== canonical.short_label || descriptor.full_disclosure !== canonical.full_disclosure) return null
  if (descriptor.source_class !== 'placeholder' && descriptor.url === null) return null
  if (descriptor.source_class !== 'user-uploaded' && descriptor.credit !== null) return null

  const dimensions = [descriptor.width, descriptor.height]
  if (dimensions.some(dimension => dimension !== null && (typeof dimension !== 'number' || !Number.isInteger(dimension) || dimension <= 0))) return null
  if ((descriptor.width === null) !== (descriptor.height === null)) return null
  return Object.freeze({ ...descriptor, url: normalizedUrl }) as ImageDescriptor
}

export function normalizeReviewPhoto(input: { url: string; alt: string; credit?: string | null }): ImageDescriptor {
  return {
    url: input.url,
    alt: input.alt,
    source_class: 'user-uploaded',
    source_kind: 'review-ugc',
    disclosure_key: 'ugc-photo',
    short_label: aiDisclosure.ugc_photo.short_label,
    full_disclosure: aiDisclosure.ugc_photo.full_disclosure,
    credit: input.credit ?? null,
    width: null,
    height: null,
  }
}
```

Use the same source-combination and URL tables in the backend Pydantic response model with `extra='forbid'`: `ai-generated/entity-editorial/entity-ai`, `placeholder/generated-placeholder/entity-placeholder`, and `user-uploaded/(review-ugc|post-ugc)/ugc-photo` are the only valid triples. `normalize_renderable_image_url()` and `normalizeRenderableImageUrl()` accept only a single-leading-slash local canonical path or an absolute `https:` URL with a host and no credentials, fragment, whitespace/control character, or backslash. They reject protocol-relative URLs and every other scheme. Backend and frontend both require exact canonical short/full copy for the disclosure key, non-blank alt text, null-or-non-blank credit, null dimensions or a positive-integer width/height pair, no credit on AI/placeholder descriptors, and a non-null valid URL for non-placeholder media. Unclassified UGC, contradictory source triples, partial dimensions, altered copy, unsafe URLs, and extra fields are rejected rather than normalized into a different class.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_image_descriptor.py agent/tests/test_public_index_policy.py -q`

Run: `cd web-nuxt && npm test -- --run tests/image-descriptors.test.ts && npm run typecheck`

Expected: backend/frontend descriptor shapes and URL acceptance agree; only canonical local paths and credential-free HTTPS render; review photos are never labeled AI.

- [ ] **Step 5: Commit**

```bash
git add agent/image_descriptor.py agent/tests/test_image_descriptor.py agent/api_schemas.py agent/public_api.py web-nuxt/types/image.ts web-nuxt/utils/imageDescriptors.ts web-nuxt/types/api.ts web-nuxt/tests/image-descriptors.test.ts
git commit -m "feat: add classified image descriptors"
```

### Task 34: Disclose AI and placeholder media in the detail hero and rail

**Files:**
- Create: `web-nuxt/components/ImageDisclosure.vue`
- Create: `web-nuxt/tests/entity-image-detail.test.ts`
- Modify: `web-nuxt/pages/dia-diem/[id].vue:17-100`
- Modify: `web-nuxt/pages/dia-diem/[id].vue:622`
- Modify: `web-nuxt/components/EntityHeroPlaceholder.vue`
- Modify: `web-nuxt/assets/css/detail-shared.css`

- [ ] **Step 1: Write failing point-of-use and accessibility tests**

```ts
const wrapper = await mountSuspended(ImageDisclosure, {
  props: { descriptor: aiDescriptor, presentation: 'short' },
})
const descriptionId = wrapper.get('[data-full-disclosure]').attributes('id')
expect(wrapper.get('[data-short-label]').text()).toBe('Minh họa AI')
expect(wrapper.get('[data-disclosure-target]').attributes('aria-describedby')).toBe(descriptionId)

const detail = await mountEntityDetail({ images: [aiDescriptor] })
expect(detail.get('[data-entity-hero]').attributes('aria-describedby')).toBeTruthy()
expect(detail.text()).toContain('Minh họa AI')
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/entity-image-detail.test.ts`

Expected: FAIL because the hero/rail use bare URLs and “real photo” wording.

- [ ] **Step 3: Render the descriptor at every hero/rail point**

```vue
<figure class="entity-media" data-entity-hero>
  <NuxtImg v-if="hero.url" :src="hero.url" :alt="hero.alt" :aria-describedby="disclosureId" />
  <EntityHeroPlaceholder v-else :descriptor="hero" />
  <ImageDisclosure :id="disclosureId" :descriptor="hero" presentation="short" />
</figure>
```

Replace the descriptor-losing `string[]` computed value with `ImageDescriptor[]`. Every rail thumbnail retains its own descriptor and full accessible association. Placeholder surfaces show only the exact placeholder copy.

- [ ] **Step 4: Run GREEN and accessibility checks**

Run: `cd web-nuxt && npm test -- --run tests/entity-image-detail.test.ts tests/image-descriptors.test.ts && npm run typecheck`

Expected: hero, placeholder, and every thumbnail expose correct copy and no real/documentary claims.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/ImageDisclosure.vue web-nuxt/tests/entity-image-detail.test.ts 'web-nuxt/pages/dia-diem/[id].vue' web-nuxt/components/EntityHeroPlaceholder.vue web-nuxt/assets/css/detail-shared.css
git commit -m "feat: disclose entity detail imagery"
```

### Task 35: Preserve disclosure through gallery and lightbox navigation

**Files:**
- Modify: `web-nuxt/components/PhotoGallery.vue`
- Modify: `web-nuxt/components/ImageLightbox.vue`
- Create: `web-nuxt/tests/gallery-disclosure.test.ts`
- Modify: `web-nuxt/pages/dia-diem/[id].vue`

- [ ] **Step 1: Write failing slide-change and reopen tests**

```ts
const wrapper = await mountSuspended(ImageLightbox, {
  props: { modelValue: true, images: [aiDescriptor, reviewDescriptor], startIndex: 0 },
})
expect(wrapper.get('[role="dialog"]').text()).toContain(aiDescriptor.full_disclosure)
await wrapper.get('[data-next]').trigger('click')
expect(wrapper.get('[role="dialog"]').text()).toContain(reviewDescriptor.full_disclosure)
expect(wrapper.text()).not.toContain('Minh họa AI')
await wrapper.setProps({ modelValue: false })
await wrapper.setProps({ modelValue: true, startIndex: 0 })
expect(wrapper.text()).toContain(aiDescriptor.full_disclosure)
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/gallery-disclosure.test.ts`

Expected: FAIL because both components accept `string[]` and have no caption association.

- [ ] **Step 3: Change component props to `ImageDescriptor[]` and render captions**

```ts
const props = defineProps<{
  images: ImageDescriptor[]
  startIndex?: number
}>()

const active = computed(() => props.images[currentIndex.value])
const captionId = computed(() => `lightbox-disclosure-${currentIndex.value}`)
```

The active image references `captionId`; the visible caption renders `active.full_disclosure` and available credit. Keyboard controls, focus trap, slide changes, and reopen preserve association.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/gallery-disclosure.test.ts tests/entity-image-detail.test.ts && npm run typecheck`

Expected: AI, placeholder, and UGC slides retain correct captions and keyboard behavior.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/PhotoGallery.vue web-nuxt/components/ImageLightbox.vue web-nuxt/tests/gallery-disclosure.test.ts 'web-nuxt/pages/dia-diem/[id].vue'
git commit -m "feat: preserve gallery image disclosure"
```

### Task 36: Disclose home, listing, ward, nearby, and recommendation cards

**Files:**
- Modify: `web-nuxt/components/EntityCard.vue`
- Modify: `web-nuxt/components/home/EntityFeature.vue`
- Modify: `web-nuxt/pages/index.vue:289-475`
- Modify: `web-nuxt/components/NearbyEntities.vue`
- Modify: `web-nuxt/components/SmartRecommendations.vue`
- Modify: `web-nuxt/components/AIRecommendations.vue`
- Create: `web-nuxt/tests/entity-card-disclosure.test.ts`

- [ ] **Step 1: Write failing dense-card and background-image tests**

```ts
const card = await mountSuspended(EntityCard, { props: { entity: entityWithAiDescriptor } })
expect(card.get('[data-image-disclosure]').text()).toBe('Minh họa AI')
expect(card.get('img').attributes('aria-describedby')).toBeTruthy()

const feature = await mountSuspended(EntityFeature, { props: { entity: entityWithAiDescriptor } })
expect(feature.get('[data-background-image]').attributes('aria-describedby')).toBeTruthy()
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/entity-card-disclosure.test.ts`

Expected: FAIL because cards and home backgrounds derive bare `images[0]` values.

- [ ] **Step 3: Require descriptors at card boundaries**

```ts
const props = defineProps<{ entity: Entity & { image_descriptor?: ImageDescriptor | null } }>()
const descriptor = computed(() => props.entity.image_descriptor ?? describeEntityImages(props.entity)[0] ?? describeEntityPlaceholder(props.entity))
```

`EntityCard` becomes the shared disclosure implementation for all its listing consumers. Bespoke home feature/spotlight backgrounds, nearby cards, and recommendation chips consume descriptors without reclassifying URLs.

- [ ] **Step 4: Run GREEN across representative consumers**

Run: `cd web-nuxt && npm test -- --run tests/entity-card-disclosure.test.ts tests/smoke.test.ts && npm run typecheck`

Expected: home, listings, search, ward children, nearby, and recommendation surfaces show accessible short disclosure.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/EntityCard.vue web-nuxt/components/home/EntityFeature.vue web-nuxt/pages/index.vue web-nuxt/components/NearbyEntities.vue web-nuxt/components/SmartRecommendations.vue web-nuxt/components/AIRecommendations.vue web-nuxt/tests/entity-card-disclosure.test.ts
git commit -m "feat: disclose entity card imagery"
```

### Task 37: Preserve descriptors through favorites, recent items, and saved cards

**Files:**
- Modify: `web-nuxt/composables/useFavorites.ts:94`
- Modify: `web-nuxt/composables/useRecentlyViewed.ts:41`
- Modify: `web-nuxt/composables/useContextualRecommendations.ts:19`
- Modify: `web-nuxt/components/SavedEntityCard.vue`
- Modify: `web-nuxt/pages/da-luu.vue`
- Modify: `web-nuxt/pages/lich-trinh/index.vue`
- Modify: `web-nuxt/pages/nguoi-dung/[id].vue`
- Modify: `web-nuxt/pages/tim-kiem.vue:142`
- Create: `web-nuxt/tests/image-adapters.test.ts`

- [ ] **Step 1: Write failing persistence/migration tests**

```ts
it('migrates legacy saved image URLs to AI descriptors', () => {
  const migrated = migrateSavedEntity({ id: 'e1', name: 'Entity', image: '/img/entity.webp' })
  expect(migrated.image_descriptor?.source_class).toBe('ai-generated')
  expect(migrated.image).toBeUndefined()
})

it('preserves remote descriptor provenance', () => {
  expect(normalizeSavedEntity({ id: 'e1', image_descriptor: reviewDescriptor }).image_descriptor)
    .toEqual(reviewDescriptor)
})
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/image-adapters.test.ts`

Expected: FAIL because adapters persist only bare `image` strings.

- [ ] **Step 3: Store descriptor snapshots and migrate legacy entity URLs deterministically**

```ts
export interface SavedEntityImageSnapshot {
  image_descriptor: ImageDescriptor
  descriptor_revision: 'ai-disclosure-v1'
}

function describeKnownEntityImage(url: string | undefined, name: string): ImageDescriptor {
  if (!url || isGeneratedPlaceholderUrl(url)) return describeEntityPlaceholder({ name, type: 'unknown' })
  return describeEntityImages({ name, images: [url], image_credits: [] })[0]
}

export function migrateLegacyEntityImage(item: LegacySavedItem): SavedItem {
  const descriptor = item.image_descriptor ?? describeKnownEntityImage(item.image, item.name)
  return { ...item, image: undefined, image_descriptor: descriptor, descriptor_revision: 'ai-disclosure-v1' }
}
```

Legacy saved/recent entity URLs are known `entity.images` snapshots and therefore migrate to AI descriptors; unknown/non-entity media is not guessed and falls back to the generated placeholder. Remote saved records preserve provided descriptors.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/image-adapters.test.ts && npm run typecheck`

Expected: saved, itinerary, profile, recent-search, and contextual recommendation data retains classification.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/composables/useFavorites.ts web-nuxt/composables/useRecentlyViewed.ts web-nuxt/composables/useContextualRecommendations.ts web-nuxt/components/SavedEntityCard.vue web-nuxt/pages/da-luu.vue web-nuxt/pages/lich-trinh/index.vue 'web-nuxt/pages/nguoi-dung/[id].vue' web-nuxt/pages/tim-kiem.vue web-nuxt/tests/image-adapters.test.ts
git commit -m "feat: preserve saved image provenance"
```

### Task 38: Cover event thumbnails, related places, and the map invariant

**Files:**
- Modify: `web-nuxt/pages/le-hoi.vue:216`
- Modify: `web-nuxt/pages/su-kien.vue:197`
- Modify: `web-nuxt/pages/ban-do.vue:217-390`
- Create: `web-nuxt/tests/event-image-disclosure.test.ts`

- [ ] **Step 1: Write failing event and map guard tests**

```ts
it.each(['le-hoi', 'su-kien'])('%s event cards disclose entity thumbnails', async page => {
  const wrapper = await mountEventPage(page, entityEventFixture)
  expect(wrapper.get('[data-event-image]').attributes('aria-describedby')).toBeTruthy()
  expect(wrapper.text()).toContain('Minh họa AI')
})

it('keeps map popup image-free unless registered', () => {
  const source = readFileSync('pages/ban-do.vue', 'utf8')
  expect(source).not.toMatch(/popup[\s\S]*<(img|NuxtImg)/)
})
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/event-image-disclosure.test.ts`

Expected: event cards fail because they use direct thumbnails; map invariant test establishes the current image-free boundary.

- [ ] **Step 3: Use descriptors for event/related-place images and register the map invariant**

Event thumbnails use `ImageDisclosure` short presentation. Related/nearby place cards are already covered by Task 36 through `NearbyEntities` and `EntityCard`. Add a stable `data-entity-image-policy="no-image-invariant"` marker to the map popup builder; Task 40 registers that marker, and a future image addition must first add a descriptor producer and disclosure.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/event-image-disclosure.test.ts tests/entity-card-disclosure.test.ts && npm run typecheck`

Expected: event surfaces disclose correctly and the map remains guarded against raw image additions.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/pages/le-hoi.vue web-nuxt/pages/su-kien.vue web-nuxt/pages/ban-do.vue web-nuxt/tests/event-image-disclosure.test.ts
git commit -m "feat: disclose event imagery and guard map popups"
```

### Task 39: Cover admin entity/media/self-learning image surfaces

**Files:**
- Modify: `web-nuxt/pages/admin/entities.vue:133-350`
- Modify: `web-nuxt/pages/admin/entities.vue:1110`
- Modify: `web-nuxt/pages/admin/media.vue:55-170`
- Modify: `web-nuxt/pages/admin/duyet-tu-hoc.vue:91-275`
- Create: `web-nuxt/tests/admin-image-disclosure.test.ts`

- [ ] **Step 1: Write failing dense-grid, expanded-preview, and authoring-boundary tests**

```ts
it('uses short disclosure in admin grids and full copy in previews', async () => {
  const wrapper = await mountAdminMedia({ descriptors: [aiDescriptor] })
  expect(wrapper.get('[data-admin-media-grid]').text()).toContain('Minh họa AI')
  await wrapper.get('[data-open-preview]').trigger('click')
  expect(wrapper.get('[data-expanded-preview]').text()).toContain(aiDescriptor.full_disclosure)
})

it('does not save review/user photos into entity.images', async () => {
  expect(() => normalizeEntityEditorialUpload({ source_class: 'user-uploaded' }))
    .toThrow(/entity.images accepts AI editorial media only/i)
})
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/admin-image-disclosure.test.ts`

Expected: FAIL because admin surfaces render raw URLs and the editor does not state the `entity.images` source boundary.

- [ ] **Step 3: Add admin disclosure and keep UGC in its separate reviewed paths**

Dense rows/grids render the short accessible label; expanded editors/previews render full copy. The entity image editor submits only `entity-editorial/ai-generated` descriptors into `entity.images`; review/post photos remain in their existing UGC stores and cannot be copied into the entity editorial array without a separately reviewed provenance change.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/admin-image-disclosure.test.ts tests/admin-provisional-review.test.ts && npm run typecheck`

Expected: all three admin pages disclose correctly and source boundaries are explicit.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/pages/admin/entities.vue web-nuxt/pages/admin/media.vue web-nuxt/pages/admin/duyet-tu-hoc.vue web-nuxt/tests/admin-image-disclosure.test.ts
git commit -m "feat: disclose admin entity imagery"
```

### Task 40: Enforce the renderer registry and repository-wide source guard

**Files:**
- Create: `web-nuxt/config/entity-image-renderers.json`
- Create: `scripts/checks/check_entity_image_renderers.py`
- Create: `web-nuxt/tests/image-renderer-inventory.test.ts`
- Create: `tests/launch_safety/test_entity_image_renderer_guard.py`
- Modify: `scripts/checks/run_hard.py`

- [ ] **Step 1: Write failing unregistered-renderer tests**

```python
def test_unregistered_raw_entity_image_access_fails(tmp_path):
    page = tmp_path / "pages" / "new.vue"
    page.parent.mkdir(parents=True)
    page.write_text('<NuxtImg :src="entity.images[0]" />', encoding="utf-8")
    findings = scan_entity_image_renderers(tmp_path, registry=[])
    assert findings[0].code == "UNREGISTERED_ENTITY_IMAGE_RENDERER"


def test_registration_does_not_exempt_a_raw_renderer(tmp_path):
    page = tmp_path / "pages" / "registered.vue"
    page.parent.mkdir(parents=True)
    page.write_text('<NuxtImg :src="entity.images[0]" />', encoding="utf-8")
    registry = [{
        "file": "pages/registered.vue",
        "surface": "synthetic",
        "access_path": "entity.images",
        "source_class": "ai-generated",
        "descriptor_producer": "describeEntityImages",
        "presentation": "short",
        "accessibility": "aria-describedby-full-copy",
        "test_file": "tests/registered.test.ts",
    }]
    assert {item.code for item in scan_entity_image_renderers(tmp_path, registry)} >= {
        "RAW_DESCRIPTOR_BYPASS",
        "MISSING_DESCRIPTOR_PRODUCER",
        "MISSING_DISCLOSURE_PRESENTATION",
        "MISSING_ACCESSIBLE_ASSOCIATION",
    }


@pytest.mark.parametrize("source", [
    '<NuxtImg :src="entity[\'images\'][0]" />',
    '<script setup>const { images } = entity</script><NuxtImg :src="images[0]" />',
    '<script setup>const pics = entity.images</script><NuxtImg :src="pics?.[0]" />',
    '<div :style="{ backgroundImage: `url(${entity?.images?.[0]})` }" />',
])
def test_adversarial_raw_access_forms_cannot_bypass_the_guard(tmp_path, source):
    page = tmp_path / "pages" / "adversarial.vue"
    page.parent.mkdir(parents=True)
    page.write_text(source, encoding="utf-8")
    codes = {item.code for item in scan_entity_image_renderers(tmp_path, registry=[])}
    assert "UNREGISTERED_ENTITY_IMAGE_RENDERER" in codes
    assert "RAW_DESCRIPTOR_BYPASS" in codes
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_entity_image_renderer_guard.py -q`

Run: `cd web-nuxt && npm test -- --run tests/image-renderer-inventory.test.ts`

Expected: FAIL because the registry and scanner do not exist.

- [ ] **Step 3: Register all approved public/auth/admin surfaces and scan raw access**

```json
{
  "schema_version": 1,
  "renderers": [
    {"file": "components/EntityCard.vue", "surface": "entity-card", "access_path": "entity.images", "source_class": "ai-generated", "descriptor_producer": "describeEntityImages", "presentation": "short", "accessibility": "aria-describedby-full-copy", "test_file": "tests/entity-card-disclosure.test.ts"},
    {"file": "pages/dia-diem/[id].vue", "surface": "mixed-gallery", "access_path": "gallery.images", "source_class": "ai-generated", "descriptor_producer": "parseGalleryDescriptor", "presentation": "full", "accessibility": "visible-full-copy", "test_file": "tests/gallery-disclosure.test.ts"},
    {"file": "pages/dia-diem/[id].vue", "surface": "mixed-gallery-ugc", "access_path": "gallery.images", "source_class": "user-uploaded", "descriptor_producer": "parseGalleryDescriptor", "presentation": "full", "accessibility": "visible-full-copy", "test_file": "tests/gallery-disclosure.test.ts"},
    {"file": "pages/admin/media.vue", "surface": "admin-media", "access_path": "entity.images", "source_class": "ai-generated", "descriptor_producer": "describeEntityImages", "presentation": "short-and-full", "accessibility": "aria-and-visible-full-copy", "test_file": "tests/admin-image-disclosure.test.ts"},
    {"file": "pages/ban-do.vue", "surface": "map-popup", "access_path": "popup", "source_class": "none", "descriptor_producer": "no-image-invariant", "presentation": "none", "accessibility": "no-image-invariant", "test_file": "tests/event-image-disclosure.test.ts"}
  ]
}
```

The required initial rows cover these exact implementation boundaries: detail hero/rail in `pages/dia-diem/[id].vue`; `PhotoGallery.vue`; `ImageLightbox.vue`; `EntityCard.vue`; `home/EntityFeature.vue`; entity feature/spotlight and community UGC thumbnails in `pages/index.vue`; `NearbyEntities.vue`; `SmartRecommendations.vue`; `AIRecommendations.vue`; descriptor adapters in `useFavorites.ts`, `useRecentlyViewed.ts`, and `useContextualRecommendations.ts`; `SavedEntityCard.vue` and its saved/itinerary/profile/search consumers; event thumbnails in `pages/le-hoi.vue` and `pages/su-kien.vue`; the `pages/ban-do.vue` no-image invariant; admin entity/media/self-learning surfaces; `ReviewCard.vue`; `PostCard.vue`; `EntityFeed.vue`; post detail/related post/JSON-LD in `pages/bai-viet/[id].vue`; admin post moderation; and native-share/OG/Twitter/JSON-LD consumers. Each file with multiple source classes or short/full modes receives separate rows, not a combined undocumented exemption.

The committed registry contains rows for every exact boundary in the preceding list, and the inventory test compares that required `(file, surface, source_class)` set for equality rather than a subset. Every row has exactly the eight shown keys; `source_class` is required and is one of `ai-generated`, `placeholder`, `user-uploaded`, or `none`. Mixed surfaces use separate rows per source class. The scanner covers Vue templates/scripts, composables, adapters, background styles, and raw `image/images/image_urls` props; registration documents the expected contract but never exempts a renderer from descriptor conversion, short/full presentation, or accessibility proof.

```python
RAW_PATTERNS = (
    re.compile(r"\bentity(?:(?:\?\.|\.)images|\[['\"]images['\"]\])"),
    re.compile(r"\b(?:entity|event|saved|item)(?:(?:\?\.|\.)images|\[['\"]images['\"]\])(?:\?\.)?\[\s*0\s*\]"),
    re.compile(r"\b(?:entity|event|saved|item)(?:(?:\?\.|\.)(?:image|image_url|image_urls)|\[['\"](?:image|image_url|image_urls)['\"]\])"),
)


def scan_entity_image_renderers(root: Path, registry: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    entries_by_file = group_validated_registry_entries(registry)
    for path in iter_frontend_source_files(root):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()
        entries = entries_by_file.get(relative, ())
        raw_aliases = trace_raw_image_aliases(text)
        render_sinks = find_image_render_sinks(text)
        raw_render_sinks = find_image_render_sinks(text, require_raw_source=True, raw_aliases=raw_aliases)
        for pattern in RAW_PATTERNS:
            for match in pattern.finditer(text):
                access = match.group(0)
                if not any(entry["access_path"] in access or access in entry["access_path"] for entry in entries):
                    findings.append(Finding("UNREGISTERED_ENTITY_IMAGE_RENDERER", path, access))
        if raw_render_sinks:
            findings.append(Finding("RAW_DESCRIPTOR_BYPASS", path, raw_render_sinks[0]))
        for entry in entries:
            producer = entry["descriptor_producer"]
            if producer == "no-image-invariant":
                if render_sinks or 'data-entity-image-policy="no-image-invariant"' not in text:
                    findings.append(Finding("BROKEN_NO_IMAGE_INVARIANT", path, entry["surface"]))
                continue
            if producer not in text:
                findings.append(Finding("MISSING_DESCRIPTOR_PRODUCER", path, producer))
            if not has_required_presentation(text, entry["presentation"], entry["source_class"]):
                findings.append(Finding("MISSING_DISCLOSURE_PRESENTATION", path, entry["surface"]))
            if not has_accessibility_proof(text, entry["accessibility"]):
                findings.append(Finding("MISSING_ACCESSIBLE_ASSOCIATION", path, entry["surface"]))
    return findings
```

`group_validated_registry_entries()` rejects missing/extra keys, duplicate `(file,surface,source_class)` rows, invalid source/presentation/accessibility combinations, missing test files, and `source_class=none` unless all three invariant fields are `none`/`no-image-invariant`. `trace_raw_image_aliases()` iterates to a fixed point over dot access, bracket access, optional chaining, `const { images } = entity`, renamed destructuring, and direct/derived aliases; it returns every identifier whose value can still be a raw image or image array. `find_image_render_sinks()` covers `<img>`, `<NuxtImg>`, CSS `background`/`background-image` static and bound styles, lightbox/gallery props, native-share/metadata image use, representative thumbnail props, and optional-chained alias indexing. A sink counts as raw when its expression contains a raw access or a traced alias. `has_required_presentation()` requires `ImageDisclosure presentation="short"` plus full-copy association for short, visible `full_disclosure` for full, and both for `short-and-full`; `has_accessibility_proof()` requires the registered `aria-describedby`/visible-caption pattern. Descriptor producer modules may access raw arrays only when they contain no render sink; every consumer still needs its own registry row and checks.

- [ ] **Step 4: Run GREEN and hard gate**

Run: `python -m pytest tests/launch_safety/test_entity_image_renderer_guard.py tests/checks/test_hard_checks.py -q`

Run: `cd web-nuxt && npm test -- --run tests/image-renderer-inventory.test.ts`

Expected: all current public/auth/admin renderers have a required source class, descriptor producer, short/full presentation, accessibility proof, and focused test; unregistered, registered-but-raw, bracket-access, destructured, aliased, optional-chained, and CSS-background synthetic renderers all fail the guard.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/config/entity-image-renderers.json scripts/checks/check_entity_image_renderers.py web-nuxt/tests/image-renderer-inventory.test.ts tests/launch_safety/test_entity_image_renderer_guard.py scripts/checks/run_hard.py tests/checks/test_hard_checks.py
git commit -m "test: guard entity image renderers"
```

### Task 41: Preserve UGC classification and exclude it from quality/media evidence

**Files:**
- Modify: `web-nuxt/components/ReviewCard.vue`
- Modify: `web-nuxt/components/PostCard.vue`
- Modify: `web-nuxt/components/EntityFeed.vue`
- Modify: `web-nuxt/pages/index.vue`
- Modify: `web-nuxt/pages/bai-viet/[id].vue`
- Modify: `web-nuxt/pages/admin/kiem-duyet.vue`
- Modify: `agent/public_api.py:2550-2585`
- Modify: `agent/index_policy.py`
- Modify: `agent/sitemap_render.py`
- Create: `web-nuxt/tests/ugc-image-classification.test.ts`
- Modify: `agent/tests/test_image_descriptor.py`
- Modify: `agent/tests/test_index_policy.py`
- Modify: `agent/tests/test_sitemap_render.py`

- [ ] **Step 1: Write failing mixed-UGC and zero-quality-credit tests**

```ts
expect(normalizeReviewPhoto(reviewPhoto)).toMatchObject({
  source_class: 'user-uploaded',
  source_kind: 'review-ugc',
  disclosure_key: 'ugc-photo',
})
expect(normalizeReviewPhoto(reviewPhoto).full_disclosure).not.toContain('AI')

const home = await mountHomeCommunity({ posts: [postWithUserThumbnail] })
expect(home.get('[data-community-thumbnail]').attributes('data-source-class')).toBe('user-uploaded')
expect(home.get('[data-community-thumbnail]').text()).not.toContain('Minh họa AI')

const post = await mountPostDetail({ post: postWithUserThumbnail, related: [relatedPostWithUserThumbnail] })
expect(post.get('[data-related-post-thumbnail]').attributes('data-source-class')).toBe('user-uploaded')
expect(postJsonLd(post).image.caption).toBe(aiDisclosure.ugc_photo.full_disclosure)
expect(JSON.stringify(postJsonLd(post))).not.toContain('Minh họa AI')
```

```python
def test_ugc_does_not_change_indexability_or_media_sitemap(public_thin_entity, evidence, disclosure):
    public_thin_entity["review_images"] = ["/img/review.jpg"]
    assert decide_entity(public_thin_entity, evidence).indexable is False
    assert b"review.jpg" not in render_media_sitemap(snapshot_with(public_thin_entity), manifest, evidence, disclosure)
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/ugc-image-classification.test.ts`

Run: `python -m pytest agent/tests/test_image_descriptor.py agent/tests/test_index_policy.py agent/tests/test_sitemap_render.py -q`

Expected: FAIL because UGC surfaces use bare URLs and mixed gallery rows have no source class.

- [ ] **Step 3: Convert UGC renderers without changing the entity quality predicate**

`pages/index.vue` converts every community-feed thumbnail with the post-UGC producer before rendering and associates the truthful UGC sentence at `data-community-thumbnail`. `pages/bai-viet/[id].vue` converts the hero and every related-post thumbnail to `user-uploaded/post-ugc`, renders UGC disclosure/credit, and builds post JSON-LD `ImageObject.caption`/`description` from that same descriptor; it never invokes the entity-AI helper for post media.

Review/post/admin moderation surfaces use `user-uploaded` descriptors with available credit. PostCard’s bespoke lightbox and share path retain UGC classification. Backend decision and media rendering explicitly ignore review/post descriptors for real-image credit and image-sitemap membership.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/ugc-image-classification.test.ts tests/gallery-disclosure.test.ts && npm run typecheck`

Run: `python -m pytest agent/tests/test_image_descriptor.py agent/tests/test_index_policy.py agent/tests/test_sitemap_render.py -q`

Expected: review cards, post cards, home community thumbnails, post-detail related thumbnails/JSON-LD, feed, and admin moderation are truthful, credited, never labeled AI, and never change current quality/sitemap output.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/ReviewCard.vue web-nuxt/components/PostCard.vue web-nuxt/components/EntityFeed.vue web-nuxt/pages/index.vue 'web-nuxt/pages/bai-viet/[id].vue' web-nuxt/pages/admin/kiem-duyet.vue agent/public_api.py agent/index_policy.py agent/sitemap_render.py web-nuxt/tests/ugc-image-classification.test.ts agent/tests/test_image_descriptor.py agent/tests/test_index_policy.py agent/tests/test_sitemap_render.py
git commit -m "feat: preserve UGC image provenance"
```

### Task 42: Align native share, OG/Twitter, JSON-LD, and media metadata

**Files:**
- Modify: `web-nuxt/components/ShareButton.vue`
- Modify: `web-nuxt/composables/useSeoHelpers.ts`
- Modify: `web-nuxt/pages/dia-diem/[id].vue:963-1140`
- Modify: `web-nuxt/pages/xa-phuong/[id].vue:248`
- Modify: `agent/seo.py` JSON-LD route
- Modify: `agent/sitemap_render.py`
- Create: `web-nuxt/tests/image-metadata-disclosure.test.ts`
- Create: `agent/tests/test_image_metadata_disclosure.py`

- [ ] **Step 1: Write failing share/metadata parity tests**

```ts
expect(appendImageDisclosureToShareText('Khám phá địa điểm', aiDescriptor))
  .toBe('Khám phá địa điểm\n\nẢnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.')

const meta = buildImageMeta(aiDescriptor)
expect(meta.ogImageAlt).toContain(aiDescriptor.full_disclosure)
expect(meta.twitterImageAlt).toContain(aiDescriptor.full_disclosure)

const jsonLd = descriptorToImageObject(aiDescriptor)
expect(jsonLd.caption).toBe(aiDescriptor.full_disclosure)
expect(jsonLd).not.toHaveProperty('photographer')
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/image-metadata-disclosure.test.ts`

Run: `python -m pytest agent/tests/test_image_metadata_disclosure.py -q`

Expected: FAIL because metadata helpers discard classification and backend JSON-LD can override the frontend with raw image arrays.

- [ ] **Step 3: Make descriptors the single metadata input**

```ts
export function appendImageDisclosureToShareText(text: string, descriptor?: ImageDescriptor | null): string {
  return descriptor?.url ? `${text}\n\n${descriptor.full_disclosure}` : text
}

export function buildImageMeta(descriptor?: ImageDescriptor | null) {
  if (!descriptor?.url) return {}
  const alt = `${descriptor.alt} — ${descriptor.full_disclosure}`
  return {
    ogImage: descriptor.url,
    ogImageAlt: alt,
    twitterImage: descriptor.url,
    twitterImageAlt: alt,
  }
}

export function descriptorToImageObject(descriptor: ImageDescriptor) {
  if (!descriptor.url || descriptor.source_class === 'placeholder') return null
  return {
    '@type': 'ImageObject',
    contentUrl: descriptor.url,
    caption: descriptor.full_disclosure,
    description: `${descriptor.alt} — ${descriptor.full_disclosure}`,
  }
}
```

Native-share text appends disclosure only when it references a descriptor image; copy-link remains URL-only. OG/Twitter alt appends the exact applicable disclosure. JSON-LD uses `ImageObject.caption`/`description`, never fabricates photographer/EXIF/capture location, and omits placeholders as evidence. Replace or align the backend `/seo/jsonld/{id}` response so it cannot override the page with unclassified images.

- [ ] **Step 4: Run GREEN and forbidden-claim scan**

Run: `cd web-nuxt && npm test -- --run tests/image-metadata-disclosure.test.ts && npm run typecheck`

Run: `python -m pytest agent/tests/test_image_metadata_disclosure.py agent/tests/test_sitemap_render.py -q`

Expected: native share, OG/Twitter, JSON-LD, and media sitemap use the same source classification and exact copy.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/ShareButton.vue web-nuxt/composables/useSeoHelpers.ts 'web-nuxt/pages/dia-diem/[id].vue' 'web-nuxt/pages/xa-phuong/[id].vue' agent/seo.py agent/sitemap_render.py web-nuxt/tests/image-metadata-disclosure.test.ts agent/tests/test_image_metadata_disclosure.py
git commit -m "feat: align image disclosure metadata"
```

## Phase 7: End-to-End Evidence, Rollback Rehearsal, and Regression

### Task 43: Exercise the browser, Nginx, and network launch matrix

**Files:**
- Modify: `scripts/ops/probe_launch_boundary.py`
- Create: `scripts/launch_safety_browser_e2e.mjs`
- Create: `tests/launch_safety/test_launch_matrix_contract.py`
- Create: `tests/launch_safety/integration/test_launch_matrix.py`
- Modify: `scripts/smoke_e2e_chrome.mjs` only if extracting a shared CDP helper
- Modify: `web-nuxt/package.json`

- [ ] **Step 1: Write a prerequisite-independent failing contract test plus the integration matrix**

```python
import pytest

from scripts.ops.probe_launch_boundary import load_launch_matrix_contract


REQUIRED_CASES = {
    "closed",
    "selective-static",
    "selective-entity-positive",
    "selective-entity-negative",
    "entity-request-failed-open",
    "sitemap-pinned",
    "agent-absent-closed",
}


def test_launch_matrix_contract_is_complete_without_docker_or_chrome():
    contract = load_launch_matrix_contract()
    assert set(contract) == REQUIRED_CASES
    assert contract["closed"]["evidence_headers"] == "absent"
    assert contract["selective-entity-negative"]["sitemap_discovery"] is True
    assert contract["entity-request-failed-open"]["evidence_headers"] == "absent"
    assert contract["sitemap-pinned"]["requires_matching_batch_revision"] is True


@pytest.mark.integration
@pytest.mark.parametrize("case", [
    "closed",
    "selective-static",
    "selective-entity-positive",
    "selective-entity-negative",
    "entity-request-failed-open",
    "sitemap-pinned",
    "agent-absent-closed",
])
def test_launch_matrix(case, launch_harness):
    result = launch_harness.run(case)
    assert result.matches_expected_contract(case)
```

The browser test first installs a legacy worker/cache, then launches the new build using the same Chrome user-data directory and proves activation purges legacy policy-bearing entries.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_launch_matrix_contract.py -q`

Expected: FAIL on every machine because `load_launch_matrix_contract()` and its complete deterministic contract do not exist. This non-integration failure is the required RED evidence and cannot be replaced by a skip.

Run: `python -m pytest tests/launch_safety/integration/test_launch_matrix.py -m integration -q`

Expected: after recording the deterministic RED above, this optional command may FAIL because the HTTP/browser harness does not exist or explicitly SKIP only when Docker/Nginx/Chrome prerequisites are unavailable. A SKIP here is dependency evidence, never RED evidence.

- [ ] **Step 3: Implement reusable probes without adding Playwright**

```python
EXPECTED = {
    "closed": {"policy": "closed", "robots": "noindex, follow", "sitemap_status": 200},
    "selective-entity-negative": {"policy": "selective-open", "robots": "noindex, follow", "discovery": True},
    "entity-request-failed-open": {"policy": "failed-open", "robots": "noindex, follow", "evidence": False},
}


def assert_launch_response(response, expected):
    assert response.headers["X-Launch-Indexing-Policy"] == expected["policy"]
    assert response.headers["Cache-Control"] == "no-store"
```

`load_launch_matrix_contract()` returns an immutable exact-key mapping for all `REQUIRED_CASES`, validates policy/robots/evidence/discovery/batch expectations without network access, and drives both the probe harness and integration parametrization so they cannot drift. Use the existing Chrome CDP approach. Keep one profile across old/new worker phases, inspect Cache Storage through CDP, test offline replay denial, and record that direct host 3000/8360/internal endpoint probes fail.

- [ ] **Step 4: Run GREEN locally where dependencies exist**

Run: `python -m pytest tests/launch_safety/test_launch_matrix_contract.py -q`

Run when Docker/Nginx/Chrome prerequisites exist: `python -m pytest tests/launch_safety/integration/test_launch_matrix.py tests/launch_safety/integration/test_nginx_boundary.py tests/launch_safety/integration/test_network_boundary.py -m integration -q`

Run when Chrome exists: `cd web-nuxt && npm run smoke:launch-safety`

Expected: the deterministic contract test always passes; provisioned HTTP/browser checks pass; unavailable Docker/Chrome dependencies produce explicit skips only in optional commands, not false passes and not RED evidence.

- [ ] **Step 5: Commit**

```bash
git add scripts/ops/probe_launch_boundary.py scripts/launch_safety_browser_e2e.mjs tests/launch_safety/test_launch_matrix_contract.py tests/launch_safety/integration/test_launch_matrix.py scripts/smoke_e2e_chrome.mjs web-nuxt/package.json
git commit -m "test: exercise the launch safety matrix"
```

### Task 44: Add and rehearse the single-host rollback runbook

**Files:**
- Modify: `ops/nginx/maintenance/http-context.conf.template`
- Modify: `ops/nginx/maintenance/server-enabled.conf`
- Modify: `ops/nginx/maintenance/server-disabled.conf`
- Create: `ops/launch-safety/cache-purge-paths.json`
- Modify: `scripts/ops/maintenance_mode.sh`
- Reuse: `scripts/ops/deploy_launch_admission.sh`
- Reuse: `scripts/package_launch_release.py`
- Create: `scripts/ops/verify_closed_release.py`
- Create: `scripts/ops/purge_launch_runtime.py`
- Create: `scripts/ops/install_closed_release.sh`
- Create: `scripts/ops/record_rollback_phase.py`
- Create: `scripts/ops/rehearse_launch_rollback.sh`
- Create: `scripts/ops/local_command_stub.py`
- Create: `docs/runbooks/launch-safety-rollback.md`
- Modify: `scripts/ops/watchdog.sh`
- Modify: `ops/systemd/vl-watchdog.service`
- Modify: `ops/systemd/vl-watchdog.timer`
- Create: `tests/launch_safety/test_watchdog_contract.py`
- Create: `tests/launch_safety/test_rollback_runbook.py`

- [ ] **Step 1: Write failing phase, evidence, purge, recovery, and no-live-claim tests**

```python
EXPECTED_PHASES = [
    "record-and-verify-evidence",
    "suspend-watchdog",
    "enable-maintenance",
    "stop-vl-nuxt",
    "purge-runtime-caches",
    "install-known-good-closed",
    "verify-dependencies-units-daemon-reload",
    "verify-readiness-and-listeners",
    "verify-nginx-closed-boundary",
    "verify-browser-worker-cache",
    "reopen-and-recover-watchdog",
]


def test_runbook_executes_every_design_phase_in_order(runbook_steps):
    assert runbook_steps == EXPECTED_PHASES


def test_known_good_package_is_verified_before_maintenance(package_verifier):
    evidence = package_verifier.verify(KNOWN_GOOD_CLOSED_ARCHIVE)
    assert evidence.required_members >= {
        "config/launch-indexing-policy.json",
        "config/ai-disclosure.json",
        "web-nuxt/.output/server/launch-readiness-manifest.json",
        "nginx.conf",
        "nginx-ssl.conf",
        "ops/systemd/vl-agent.service",
        "ops/systemd/vl-nuxt.service",
        "compose-network-audit.json",
    }
    assert evidence.package_kind == "vl360-launch-release"
    assert evidence.archive_sha256 == read_archive_sidecar(KNOWN_GOOD_CLOSED_ARCHIVE)
    assert evidence.member_digests_match_manifest is True
    assert evidence.persistent_paths == ["agent/data", "agent/data/sitemap-bundles"]
    assert evidence.dev_override_selected is False
    assert evidence.unlock_keys_present is False


def test_cache_purge_is_explicit_and_preserves_sitemap_evidence(purge_plan):
    assert purge_plan.required_paths == {
        "web-nuxt/.output", "web-nuxt/.nuxt", "web-nuxt/.cache",
    }
    assert "agent/data/sitemap-bundles" in purge_plan.protected_paths
    assert purge_plan.rejects_outside_release_root is True
    assert purge_plan.rejects_symlinks is True


def test_recovery_keeps_or_restores_closed_maintenance_state(rehearsal):
    result = rehearsal.fail_at("verify-browser-worker-cache")
    assert result.maintenance_enabled is True
    assert result.old_open_release_restored is False
    assert result.recovery_action in {"corrected-closed-roll-forward", "known-good-closed-restore"}


def test_initial_package_verification_failure_leaves_existing_state_unchanged(rehearsal):
    before = rehearsal.snapshot_host_state()
    result = rehearsal.fail_at("record-and-verify-evidence")
    assert result.host_state == before
    assert result.recovery_trap_armed is False
    assert result.commands_after_failure == []


def test_recovery_repeats_install_through_browser_before_any_reopen(rehearsal):
    result = rehearsal.fail_at("verify-browser-worker-cache")
    assert result.recovery_commands == [
        "verify-recovery-package",
        "install-closed-release",
        "verify-dependencies-units-daemon-reload",
        "verify-readiness-and-listeners",
        "verify-nginx-closed-boundary",
        "verify-browser-worker-cache",
    ]
    assert result.maintenance_enabled is True
    assert "disable-maintenance" not in result.recovery_commands
    assert result.traffic_reopened is False


def test_post_reopen_failure_redrains_before_any_other_recovery_action(rehearsal):
    result = rehearsal.fail_at("post-reopen-closed-probe")
    assert result.recovery_commands[:4] == [
        "maintenance-enable", "nginx-test-closed", "nginx-reload-closed", "maintenance-probe",
    ]
    assert result.traffic_reopened is False


def test_recovery_records_every_result_and_preserves_original_exit_status(rehearsal):
    result = rehearsal.fail_at("verify-readiness-and-listeners", status=37)
    assert result.exit_code == 37
    assert result.recovery_results.keys() >= {
        "verify-recovery-package", "install-closed-release", "verify-dependencies-units-daemon-reload",
        "verify-readiness-and-listeners", "verify-nginx-closed-boundary", "verify-browser-worker-cache",
    }
    assert set(result.recovery_results.values()) <= {"passed", "failed", "skipped"}
    assert result.summary["closed_verified"] is False


@pytest.mark.parametrize("path", ["agent/data/app.db", "agent/data/uploads/photo.jpg", "agent/data/sitemap-bundles/a/metadata.json"])
def test_primary_and_recovery_whole_tree_installs_preserve_persistent_bytes(rehearsal, path):
    before = rehearsal.hash_and_read(path)
    primary = rehearsal.install_known_good_closed()
    after_primary = rehearsal.hash_and_read(path)
    recovery = rehearsal.fail_at("verify-browser-worker-cache")
    after_recovery = rehearsal.hash_and_read(path)
    assert after_primary == before
    assert after_recovery == before
    assert primary.persistent_events == ["detach-agent-data", "swap-release-root", "restore-bind-agent-data", "verify-agent-data-mount"]
    assert recovery.persistent_events[-4:] == primary.persistent_events


def test_failure_after_persistent_detach_restores_old_tree_and_mount(rehearsal):
    before = rehearsal.snapshot_release_and_persistent_state()
    result = rehearsal.fail_at("swap-release-root")
    assert result.release_and_persistent_state == before
    assert result.maintenance_enabled is True


def test_listener_browser_and_nginx_proofs_are_required(evidence_schema):
    assert evidence_schema.required_checks >= {
        "process-local-readiness",
        "loopback-internal-listeners",
        "nginx-only-public-80-443",
        "nginx-closed-html-robots-empty-sitemaps",
        "public-internal-route-not-found",
        "direct-3000-8360-fastapi-bypass-denied",
        "controlled-worker-activated",
        "policy-cache-storage-empty",
        "offline-policy-replay-denied",
        "post-reopen-closed-probes",
    }


def test_rehearsal_never_claims_stage3_sla(script_text):
    assert '"stage3_claim": false' in script_text
    assert '"live_sla_proven": false' in script_text
    assert '"observed_local_elapsed_seconds"' in script_text
    assert '"live_sla_proven": true' not in script_text
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_watchdog_contract.py tests/launch_safety/test_rollback_runbook.py -q`

Expected: FAIL because Task 44 has not yet upgraded the Task 31 drain for rollback, consumed the combined manifest+sidecar package, implemented persistent-safe whole-tree installation, added the exact package verifier/purge authority/dependency-unit installer, or built the inherited-ERR best-effort recovery/evidence state machine.

- [ ] **Step 3: Implement every Section 12 phase and the local-only recovery rehearsal**

```bash
set -Eeuo pipefail
MODE=${1:---local-rehearsal}
RELEASE_ROOT=${RELEASE_ROOT:-/opt/vinhlong360}
KNOWN_GOOD_CLOSED=${KNOWN_GOOD_CLOSED:?known-good closed package is required}
PERSISTENT_AGENT_DATA_ROOT=${PERSISTENT_AGENT_DATA_ROOT:?external persistent agent data root is required}
EVIDENCE_DIR=${EVIDENCE_DIR:?evidence directory is required}
OPERATOR=${OPERATOR:?operator identity is required}
OPERATOR_CIDR=${OPERATOR_CIDR:?operator probe CIDR is required}
STAGE3_CLAIM=false
LIVE_SLA_PROVEN=false
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
STARTED_EPOCH=$(date +%s)
CURRENT_PHASE=initialization
REOPENED=false
RECOVERY_TRAP_ARMED=false

if [ "$MODE" = "--execute-on-host" ]; then
  [ "${ACKNOWLEDGE_MAINTENANCE:-}" = "launch-safety-rollback" ] || exit 64
  RUNNER=run_host
else
  [ "$MODE" = "--local-rehearsal" ] || exit 64
  RELEASE_ROOT=${LOCAL_RELEASE_ROOT:?local rehearsal root is required}
  RUNNER=run_local_stub
fi

record_phase() {
  python scripts/ops/record_rollback_phase.py \
    --evidence-dir "$EVIDENCE_DIR" --phase "$CURRENT_PHASE" --status "$1" \
    --operator "$OPERATOR" --started-at "$STARTED_AT" --stage3-claim false --live-sla-proven false
}

install_closed_package() {
  package=$1
  evidence_dir=$2
  "$RUNNER" scripts/ops/install_closed_release.sh \
    --archive "$package" --archive-digest-file "$package.sha256" \
    --release-root "$RELEASE_ROOT" --persistent-agent-data-root "$PERSISTENT_AGENT_DATA_ROOT" \
    --require-closed --evidence-dir "$evidence_dir/install"
  "$RUNNER" python scripts/ops/verify_closed_release.py \
    --installed-root "$RELEASE_ROOT" --verify-config-ingress-unit-digests \
    --verify-persistent-agent-data-mount "$PERSISTENT_AGENT_DATA_ROOT" \
    --require-closed --evidence-dir "$evidence_dir/installed"
}

verify_dependencies_units_daemon_reload() {
  "$RUNNER" python -m pip check
  "$RUNNER" npm --prefix "$RELEASE_ROOT/web-nuxt" ls --omit=dev
  "$RUNNER" systemd-analyze verify \
    "$RELEASE_ROOT/ops/systemd/vl-agent.service" \
    "$RELEASE_ROOT/ops/systemd/vl-nuxt.service" \
    "$RELEASE_ROOT/ops/systemd/vl-bot.service"
  "$RUNNER" systemctl daemon-reload
  "$RUNNER" systemctl start vl-nuxt
}

verify_readiness_and_listeners() {
  evidence_dir=$1
  "$RUNNER" python scripts/ops/probe_launch_boundary.py \
    --process-local-readiness http://127.0.0.1:3000/_internal/launch-readiness \
    --expect closed --require-complete-check-set
  "$RUNNER" python scripts/ops/socket_boundary_probe.py \
    --expect-nginx-public-only --expect-loopback 3000 8360 \
    --evidence "$evidence_dir/listeners.json"
}

verify_nginx_closed_boundary() {
  "$RUNNER" python scripts/ops/probe_launch_boundary.py \
    --expect closed --maintenance-probe --operator-source \
    --require-rich-thin-html --require-meta-header-noindex --require-robots-without-sitemap \
    --require-three-empty-sitemap-shapes --require-no-store --require-no-evidence \
    --require-no-discovery --require-public-internal-404 --require-direct-bypass-denied
}

verify_browser_worker_cache() {
  evidence_dir=$1
  "$RUNNER" node scripts/launch_safety_browser_e2e.mjs \
    --base-url "${NGINX_PROBE_URL:?}" --profile "$evidence_dir/chrome-profile" \
    --install-legacy-worker-first --activate-current-worker \
    --assert-policy-cache-storage-empty --assert-offline-policy-replay-denied \
    --evidence "$evidence_dir/browser.json"
}

record_recovery_result() {
  name=$1
  status=$2
  code=$3
  python scripts/ops/record_rollback_phase.py \
    --evidence-dir "$EVIDENCE_DIR" --phase "recovery:$name" --status "$status" \
    --exit-code "$code" --stage3-claim false --live-sla-proven false
}

best_effort_recovery_step() {
  name=$1
  shift
  "$@"
  code=$?
  if [ "$code" -eq 0 ]; then
    record_recovery_result "$name" passed 0
  else
    record_recovery_result "$name" failed "$code"
    RECOVERY_CHAIN_OK=false
  fi
  return 0
}

skip_recovery_step() {
  record_recovery_result "$1" skipped 0
  return 0
}

keep_maintenance_and_recover() {
  original_status=${1:-1}
  trap - ERR
  set +e
  RECOVERY_CHAIN_OK=true
  if [ "$REOPENED" = true ]; then
    best_effort_recovery_step immediate-redrain-enable "$RUNNER" scripts/ops/maintenance_mode.sh enable --operator-cidr "$OPERATOR_CIDR"
    best_effort_recovery_step immediate-redrain-nginx-test "$RUNNER" nginx -t
    best_effort_recovery_step immediate-redrain-nginx-reload "$RUNNER" systemctl reload nginx
    best_effort_recovery_step immediate-redrain-probe "$RUNNER" python scripts/ops/probe_launch_boundary.py --expect maintenance --operator-source
    REOPENED=false
  fi
  record_phase failed
  primary_record_status=$?
  if [ "$primary_record_status" -eq 0 ]; then
    record_recovery_result record-primary-failure passed 0
  else
    record_recovery_result record-primary-failure failed "$primary_record_status"
  fi
  if [ -n "${CORRECTED_CLOSED_PACKAGE:-}" ]; then
    recovery_package=$CORRECTED_CLOSED_PACKAGE
    recovery_action=corrected-closed-roll-forward
  else
    recovery_package=$KNOWN_GOOD_CLOSED
    recovery_action=known-good-closed-restore
  fi

  best_effort_recovery_step verify-recovery-package "$RUNNER" python scripts/ops/verify_closed_release.py \
    --archive "$recovery_package" --archive-digest-file "$recovery_package.sha256" \
    --require-closed --evidence-dir "$EVIDENCE_DIR/recovery/package"
  if [ "$RECOVERY_CHAIN_OK" = true ]; then
    best_effort_recovery_step install-closed-release install_closed_package "$recovery_package" "$EVIDENCE_DIR/recovery"
  else
    skip_recovery_step install-closed-release
  fi
  if [ "$RECOVERY_CHAIN_OK" = true ]; then
    best_effort_recovery_step verify-dependencies-units-daemon-reload verify_dependencies_units_daemon_reload
  else
    skip_recovery_step verify-dependencies-units-daemon-reload
  fi
  if [ "$RECOVERY_CHAIN_OK" = true ]; then
    best_effort_recovery_step verify-readiness-and-listeners verify_readiness_and_listeners "$EVIDENCE_DIR/recovery"
  else
    skip_recovery_step verify-readiness-and-listeners
  fi
  if [ "$RECOVERY_CHAIN_OK" = true ]; then
    best_effort_recovery_step verify-nginx-closed-boundary verify_nginx_closed_boundary
  else
    skip_recovery_step verify-nginx-closed-boundary
  fi
  if [ "$RECOVERY_CHAIN_OK" = true ]; then
    best_effort_recovery_step verify-browser-worker-cache verify_browser_worker_cache "$EVIDENCE_DIR/recovery"
  else
    skip_recovery_step verify-browser-worker-cache
  fi

  if [ "$RECOVERY_CHAIN_OK" = true ]; then
    recovery_status=closed-verified-maintenance-retained
  else
    recovery_status=failed-maintenance-retained
  fi
  python scripts/ops/record_rollback_phase.py \
    --evidence-dir "$EVIDENCE_DIR" --phase recovery --status "$recovery_status" \
    --recovery-action "$recovery_action" --old-open-restored false \
    --traffic-reopened false --steps-replayed install,dependencies-units,readiness-listeners,nginx-boundary,browser-cache
  exit "$original_status"
}

CURRENT_PHASE=record-and-verify-evidence
"$RUNNER" python scripts/ops/verify_closed_release.py \
  --archive "$KNOWN_GOOD_CLOSED" --require-closed --operator "$OPERATOR" \
  --candidate-id "${CANDIDATE_RELEASE_ID:?}" --rollback-id "${ROLLBACK_RELEASE_ID:?}" \
  --evidence-dir "$EVIDENCE_DIR/package"
record_phase passed

CURRENT_PHASE=suspend-watchdog
if ! "$RUNNER" systemctl stop vl-watchdog.timer; then
  exit 1
fi
if ! "$RUNNER" systemctl stop vl-watchdog.service; then
  "$RUNNER" systemctl start vl-watchdog.timer
  exit 1
fi
record_phase passed

CURRENT_PHASE=enable-maintenance
if ! "$RUNNER" scripts/ops/maintenance_mode.sh enable --operator-cidr "$OPERATOR_CIDR" || \
   ! "$RUNNER" nginx -t || \
   ! "$RUNNER" systemctl reload nginx || \
   ! "$RUNNER" python scripts/ops/probe_launch_boundary.py --expect maintenance --operator-source; then
  "$RUNNER" scripts/ops/maintenance_mode.sh disable --operator-cidr "$OPERATOR_CIDR"
  "$RUNNER" nginx -t
  "$RUNNER" systemctl reload nginx
  "$RUNNER" systemctl start vl-watchdog.timer
  exit 1
fi
record_phase passed
RECOVERY_TRAP_ARMED=true
trap 'keep_maintenance_and_recover "$?"' ERR

CURRENT_PHASE=stop-vl-nuxt
"$RUNNER" systemctl stop vl-nuxt
record_phase passed

CURRENT_PHASE=purge-runtime-caches
"$RUNNER" python scripts/ops/purge_launch_runtime.py \
  --release-root "$RELEASE_ROOT" \
  --readiness-manifest "$RELEASE_ROOT/web-nuxt/.output/server/launch-readiness-manifest.json" \
  --policy ops/launch-safety/cache-purge-paths.json \
  --evidence "$EVIDENCE_DIR/cache-purge.json"
record_phase passed

CURRENT_PHASE=install-known-good-closed
install_closed_package "$KNOWN_GOOD_CLOSED" "$EVIDENCE_DIR"
record_phase passed

CURRENT_PHASE=verify-dependencies-units-daemon-reload
verify_dependencies_units_daemon_reload
record_phase passed

CURRENT_PHASE=verify-readiness-and-listeners
verify_readiness_and_listeners "$EVIDENCE_DIR"
record_phase passed

CURRENT_PHASE=verify-nginx-closed-boundary
verify_nginx_closed_boundary
record_phase passed

CURRENT_PHASE=verify-browser-worker-cache
verify_browser_worker_cache "$EVIDENCE_DIR"
record_phase passed

CURRENT_PHASE=reopen-and-recover-watchdog
"$RUNNER" scripts/ops/maintenance_mode.sh disable --operator-cidr "$OPERATOR_CIDR"
"$RUNNER" nginx -t
"$RUNNER" systemctl reload nginx
REOPENED=true
"$RUNNER" python scripts/ops/probe_launch_boundary.py --expect closed --require-public-post-reopen-matrix
"$RUNNER" systemctl start vl-watchdog.timer
record_phase passed

trap - ERR
FINISHED_EPOCH=$(date +%s)
python scripts/ops/record_rollback_phase.py \
  --evidence-dir "$EVIDENCE_DIR" --phase complete --status passed \
  --observed-local-elapsed-seconds "$((FINISHED_EPOCH - STARTED_EPOCH))" \
  --stage3-claim false --live-sla-proven false
```

The operational authorities are exact:

- `verify_closed_release.py` consumes only the Task 31 `build_launch_release()` format. It verifies the adjacent whole-archive SHA-256 sidecar first, then rejects an archive/installed root unless every member digest/length, both canonical artifact bytes and revisions, readiness manifest, Nginx configs, loopback systemd units/wrappers, rendered Compose network audit, persistent-path declaration, and excluded developer override identity match `launch-release-manifest.json`. It rejects any `agent/data/**` archive member, either unlock key in packaged environment material, or a non-closed package and writes SHA-256 evidence before maintenance begins.
- `cache-purge-paths.json` requires `web-nuxt/.output`, `web-nuxt/.nuxt`, and `web-nuxt/.cache`; permits only additional cache/output paths enumerated by the old readiness manifest; protects `agent/data/sitemap-bundles`; and rejects absolute escape, `..`, symlink, release-root deletion, and protected descendants. `purge_launch_runtime.py` resolves every path before deletion and records each removed/absent/protected result.
- `install_closed_release.sh` verifies the combined archive and sidecar again, extracts to a sibling staging directory, installs backend requirements and Nuxt production dependencies, verifies `pip check` and `npm ls --omit=dev`, atomically installs the known-good closed tree, copies only digest-matched tracked systemd units, and never copies a developer override or unlock values. Its persistent-data algorithm is exact: resolve `RELEASE_ROOT`, its sibling staging/old roots, and `PERSISTENT_AGENT_DATA_ROOT`; reject symlinks, path escape, archive `agent/data/**`, or an unexpected mount source; snapshot SHA-256+length for every existing `agent/data/**` regular file; if `agent/data` is already the expected bind mount, record it with `findmnt --json` and detach it, otherwise atomically move the existing directory to the empty external persistent root; swap the complete release tree; create the new empty `agent/data` mountpoint; bind-mount the same external root; verify source/options with `findmnt`; and compare the complete byte snapshot including `agent/data/sitemap-bundles/**`. If failure occurs after detach and before verified remount, the install trap restores the previous tree and the same bind mount before returning failure. Primary and recovery installs call this identical function, so neither path copies, replaces, or regenerates persistent bytes.
- `http-context.conf.template` defines the named operator CIDR allowlist. `server-enabled.conf` returns 503 to every non-operator request; `server-disabled.conf` contains no drain rule. `maintenance_mode.sh` atomically selects the include, runs `nginx -t`, and refuses to reload on invalid configuration.
- `local_command_stub.py` executes this identical state machine against a temporary release root and stubbed systemctl/Nginx/listener commands, while the real Task 32 Nginx harness and Task 43 controlled Chrome worker run the HTTP/cache proofs. The local rehearsal is not allowed to replace the browser step with a stub.
- Initial archive/evidence verification runs before any watchdog, Nginx, service, live-release, or release-root mutation and before the recovery trap is armed; apart from its append-only evidence attempt, failure exits with the exact prior operational host state and no recovery command. Watchdog suspension and maintenance admission have explicit local restoration paths. The script uses `set -Eeuo pipefail`, and the `ERR` recovery trap is armed only after maintenance has passed config test, reload, and maintenance probe, so failures inherited through shell functions reach the same handler.
- Pre-reopen failure leaves maintenance enabled and first rolls forward to an explicitly supplied corrected closed package; otherwise it restores the recorded known-good closed package. Recovery calls the same package verifier, persistent-safe install, dependency/unit/daemon-reload, process-local readiness, listener, Nginx boundary, and controlled browser/cache helpers used by the primary path, in that order. It records `traffic-reopened=false` and leaves maintenance enabled after verification; no recovery path may jump directly from package install to reopen. On post-reopen failure the handler's first operational sequence is maintenance enable, `nginx -t`, reload, and maintenance probe; only then may package recovery begin. The candidate/open artifact is never a recovery source.
- The recovery handler receives and later exits with the original failing status, disables `errexit` after removing the `ERR` trap, and treats recovery as best-effort. Every required recovery phase is appended as `passed`, `failed`, or `skipped`; one failed command cannot abort evidence recording for later phases, while unsafe dependent phases are recorded skipped instead of executed. `record_rollback_phase.py` writes append-only JSONL plus a final summary containing candidate/rollback identifiers, operator, package/config/ingress/unit/persistent-tree digests, every phase command/result, listener and browser evidence paths, recovery action, `stage3_claim=false`, `live_sla_proven=false`, and observed local elapsed seconds only. It sets `closed_verified=true` only when every required recovery command exited zero and its evidence file validates; missing/failed/skipped proof can never be summarized as passed.

This workstream invokes only `--local-rehearsal`. `--execute-on-host` remains an approval-gated runbook path and is not executed, deployed, or claimed as live evidence.

- [ ] **Step 4: Run GREEN and Bash syntax checks**

Run: `python -m pytest tests/launch_safety/test_watchdog_contract.py tests/launch_safety/test_rollback_runbook.py -q`

Run: `& 'C:\Program Files\Git\bin\bash.exe' -n scripts/ops/maintenance_mode.sh`

Run: `& 'C:\Program Files\Git\bin\bash.exe' -n scripts/ops/install_closed_release.sh`

Run: `& 'C:\Program Files\Git\bin\bash.exe' -n scripts/ops/rehearse_launch_rollback.sh`

Run: `& 'C:\Program Files\Git\bin\bash.exe' scripts/ops/rehearse_launch_rollback.sh --local-rehearsal` with `KNOWN_GOOD_CLOSED` plus its `.sha256` sidecar, `LOCAL_RELEASE_ROOT`, `PERSISTENT_AGENT_DATA_ROOT`, `EVIDENCE_DIR`, `OPERATOR`, `OPERATOR_CIDR`, `CANDIDATE_RELEASE_ID`, `ROLLBACK_RELEASE_ID`, and `NGINX_PROBE_URL` set to the disposable Task 43/44 harness values.

Expected: every Section 12 phase passes against the local harness; the Task 31 combined archive, sidecar, package/dependency/systemd-unit/daemon-reload evidence is recorded; purge paths are explicit and all `agent/data` including sitemap bundles remain byte-for-byte identical through primary and recovery whole-tree swaps; readiness/listener/Nginx/browser/cache proofs pass before reopen; initial verification failure leaves the simulated host byte-for-byte/state-for-state unchanged with no armed recovery; every post-boundary failure preserves its original status, immediately re-drains when needed, records every best-effort result, keeps maintenance, and never overstates closed proof or bypasses reopen gates; the observed local duration is recorded without a live five-minute SLA claim.

- [ ] **Step 5: Commit**

```bash
git add ops/nginx/maintenance ops/launch-safety/cache-purge-paths.json scripts/ops/maintenance_mode.sh scripts/ops/verify_closed_release.py scripts/ops/purge_launch_runtime.py scripts/ops/install_closed_release.sh scripts/ops/record_rollback_phase.py scripts/ops/rehearse_launch_rollback.sh scripts/ops/local_command_stub.py docs/runbooks/launch-safety-rollback.md scripts/ops/watchdog.sh ops/systemd/vl-watchdog.service ops/systemd/vl-watchdog.timer tests/launch_safety/test_watchdog_contract.py tests/launch_safety/test_rollback_runbook.py
git commit -m "ops: add launch safety rollback rehearsal"
```

### Task 45: Record full regression and final source evidence

**Files:**
- Create: `scripts/ops/record_launch_evidence.py`
- Create: `docs/superpowers/results/2026-07-13-launch-safety-gate-evidence.md`
- Create: `tests/launch_safety/test_evidence_record.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `scripts/release_gate.ps1`
- Verify: all files changed by Tasks 1–44

- [ ] **Step 1: Write the failing evidence completeness test**

```python
def test_evidence_requires_all_gate_sections(evidence_document):
    assert evidence_document.sections == {
        "artifacts",
        "backend-focused",
        "frontend-focused",
        "postgres-opt-in",
        "compose-nginx-opt-in",
        "browser-opt-in",
        "rollback-local-rehearsal",
        "backend-full-regression",
        "frontend-serial-regression",
        "source-scans",
        "known-resource-timeout",
        "external-gates",
    }
    assert evidence_document.external_gates == {"H1": "blocked", "H2": "blocked", "owner": "not-authorized"}
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_evidence_record.py -q`

Expected: FAIL because the evidence recorder/document does not exist and CI does not run the new focused gates.

- [ ] **Step 3: Add deterministic evidence recording and CI/release wiring**

```python
@dataclass(frozen=True)
class CommandEvidence:
    command: str
    exit_code: int
    summary: str
    status: Literal["pass", "fail", "skip"]


def record_section(name: str, evidence: CommandEvidence) -> None:
    if name not in REQUIRED_SECTIONS:
        raise ValueError(f"unknown evidence section: {name}")
    append_markdown_row(EVIDENCE_PATH, name, evidence)
```

CI runs unit/static launch gates by default and opt-in jobs only when their dependencies are provisioned. The release gate runs the full serial frontend suite, typecheck, build/output audit, backend policy tests, artifact/renderer/source checks, and diff-check.

- [ ] **Step 4: Run the final verification matrix serially**

Run backend focused tests:

```powershell
python -m pytest tests/launch_safety agent/tests/test_launch_artifacts.py agent/tests/test_route_manifest.py agent/tests/test_ai_disclosure.py agent/tests/test_index_policy.py agent/tests/test_public_index_policy.py agent/tests/test_policy_http.py agent/tests/test_launch_policy_api.py agent/tests/test_sitemap_snapshot.py agent/tests/test_sitemap_render.py agent/tests/test_sitemap_store.py agent/tests/test_sitemap_bundle.py agent/tests/test_image_descriptor.py agent/tests/test_image_metadata_disclosure.py -q
```

Run backend full regression:

```powershell
python -m pytest -q
```

Expected: no new failure relative to `6168 passed, 47 skipped, 78 deselected, 1 xfailed, 1 warning`; new tests increase totals.

Run frontend focused and full serial regression:

```powershell
cd web-nuxt
npm test -- --run tests/launch-route-manifest.test.ts tests/launch-safety-decision.test.ts tests/launch-root-seo.test.ts tests/launch-readiness.test.ts tests/image-renderer-inventory.test.ts tests/image-metadata-disclosure.test.ts
npm test -- --no-file-parallelism --maxWorkers=1 --testTimeout=30000 --hookTimeout=30000
npm run typecheck
npm run build
```

Expected: no new failure relative to `8 files / 125 tests`; build/output audit and typecheck exit 0.

Run source/config gates:

```powershell
python scripts/checks/run_hard.py
python -m pytest tests/checks/test_hard_checks.py tests/test_release_quality_gates.py -q
git diff --check
```

Run and record opt-in tests where available:

```powershell
$pgCompose = 'tests/launch_safety/harness/docker-compose.postgres.yml'
try {
  docker compose -f $pgCompose up -d --wait
  if ($LASTEXITCODE -ne 0) { throw 'failed to provision disposable PostgreSQL harness' }
  $env:SITEMAP_BUNDLE_TEST_DATABASE_URL = 'postgresql://vl360:vl360_launch_test@127.0.0.1:55432/vl360_launch_test'
  python -m pytest agent/tests/test_sitemap_bundle_postgres.py -m integration -q
  if ($LASTEXITCODE -ne 0) { throw "PostgreSQL sitemap integration failed with exit $LASTEXITCODE" }
}
finally {
  Remove-Item Env:SITEMAP_BUNDLE_TEST_DATABASE_URL -ErrorAction SilentlyContinue
  docker compose -f $pgCompose down -v --remove-orphans
  if ($LASTEXITCODE -ne 0) { Write-Error 'disposable PostgreSQL cleanup failed' }
}

$launchCompose = 'tests/launch_safety/harness/docker-compose.yml'
try {
  docker compose -f $launchCompose up -d --build --wait
  if ($LASTEXITCODE -ne 0) { throw 'failed to provision launch HTTP harness' }
  $env:LAUNCH_SAFETY_BASE_URL = 'http://127.0.0.1:18080'
  $env:NGINX_PROBE_URL = 'http://127.0.0.1:18080'
  python -m pytest tests/launch_safety/integration/test_launch_matrix.py tests/launch_safety/integration/test_nginx_boundary.py tests/launch_safety/integration/test_network_boundary.py -m integration -q
  if ($LASTEXITCODE -ne 0) { throw "launch integration failed with exit $LASTEXITCODE" }
  Push-Location web-nuxt
  try {
    npm run smoke:launch-safety
    if ($LASTEXITCODE -ne 0) { throw "Chrome launch smoke failed with exit $LASTEXITCODE" }
  }
  finally {
    Pop-Location
  }
}
finally {
  Remove-Item Env:LAUNCH_SAFETY_BASE_URL -ErrorAction SilentlyContinue
  Remove-Item Env:NGINX_PROBE_URL -ErrorAction SilentlyContinue
  docker compose -f $launchCompose down -v --remove-orphans
  if ($LASTEXITCODE -ne 0) { Write-Error 'launch HTTP harness cleanup failed' }
}
```

The Task 16 PostgreSQL harness owns exact credentials/database and publishes only `127.0.0.1:55432`; Task 45 never connects to port 5432 or any pre-existing database. Both `finally` blocks always remove environment variables and run `down -v --remove-orphans`, including after a failing test. The Task 32 launch harness publishes its test-only Nginx boundary at `127.0.0.1:18080`. Expected: provisioned opt-in checks pass; unavailable Docker/Chrome dependencies are recorded as explicit skips before setup rather than by silently targeting another service. The known parallel resource timeout is recorded separately and never changes functional expectations.

- [ ] **Step 5: Commit the final evidence only after every required command is recorded**

```bash
git add scripts/ops/record_launch_evidence.py docs/superpowers/results/2026-07-13-launch-safety-gate-evidence.md .github/workflows/ci.yml scripts/release_gate.ps1 tests/launch_safety/test_evidence_record.py
git commit -m "test: record launch safety gate evidence"
```

## Implementation Handoff

The owner has already selected **Subagent-Driven execution**. After this plan is reviewed and explicitly approved:

1. Invoke `superpowers:subagent-driven-development`.
2. Extract all 45 tasks and their full text into the controller checklist.
3. Dispatch a fresh implementer for Task 1 only.
4. Require RED, GREEN, focused verification, self-review, and a task commit.
5. Dispatch a fresh spec-compliance reviewer; fix and re-review every Critical/Important finding.
6. Dispatch a separate fresh quality reviewer only after spec compliance passes; fix and re-review every Critical/Important finding.
7. Mark the task complete, then dispatch a new implementer for the next task.
8. After Task 45, dispatch a final whole-workstream reviewer and invoke `superpowers:finishing-a-development-branch`.

No implementation begins merely because this plan file exists. Global `noindex`, H1, H2, and separate owner authorization remain unchanged.

## Plan Self-Review Coverage

| Approved design area | Implementation tasks |
| --- | --- |
| Canonical artifacts, packaging, and fingerprint inputs | 1–8, 20, 28, 31 |
| Backend entity/ward authority and exact API cache contract | 9–13 |
| Authoritative PostgreSQL snapshot and immutable sitemap protocol | 14–19 |
| Nuxt two-key gate, entity-scoped failure, HTML/header/root SEO alignment | 20–25 |
| SWR/prerender/service-worker isolation and readiness | 26–29 |
| Exclusive Compose/systemd/Nginx ingress and deploy admission | 30–32 |
| AI/placeholder/UGC descriptors across public/auth/admin surfaces | 33–42 |
| Browser/network matrix, rollback rehearsal, and full evidence | 43–45 |

The type locks used across tasks are `PolicyEvidence`, `IndexPolicyDecision`, `LaunchSafetyDecision`, `LaunchPageDecision`, `ImageDescriptor`, and the four exact public evidence headers. Task 20 mirrors the fingerprint algorithm from Task 9; Task 28 records its result; Tasks 13 and 21 validate the same backend evidence. Task 18 introduces the entity-only backend descriptor needed by media sitemap generation, and Task 33 extends that module for placeholders and UGC without changing the earlier AI classification.

The plan contains 45 continuous tasks, and each task contains exactly five checkbox steps: failing test, RED command, minimal implementation, GREEN verification, and commit. No task authorizes a live deployment or a live indexing change.
