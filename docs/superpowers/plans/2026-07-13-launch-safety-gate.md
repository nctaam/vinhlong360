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
- Modify `nginx.conf` and `nginx-ssl.conf`; create `ops/nginx/maintenance/` templates for the rehearsed single-host drain.
- Modify `scripts/deploy.sh` and add focused source/config validation helpers under `scripts/checks/`.
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

from scripts.package_launch_release import (
    CANONICAL_ARTIFACTS,
    backend_archive_members,
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
    members = backend_archive_members(tmp_path)
    assert "config/launch-indexing-policy.json" in members
    assert "config/ai-disclosure.json" in members
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_artifact_packaging.py tests/launch_safety/test_release_package.py -q`

Expected: FAIL because `scripts.package_launch_release`, root-context Nuxt packaging, and canonical config packaging do not exist.

- [ ] **Step 3: Implement the packaging authority and harden the root context**

```python
# scripts/package_launch_release.py
from pathlib import Path

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


def backend_archive_members(root: Path) -> tuple[str, ...]:
    return tuple(
        ["agent", "requirements.txt", "init.sql", "config"]
        + (["web/data.json"] if (root / "web/data.json").exists() else [])
    )
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
  it('rejects duplicate exact routes', () => {
    expect(() => parseLaunchRouteManifest({
      schema_version: 1,
      revision: 'r1',
      canonical_origin: 'https://vinhlong360.vn',
      unknown_policy: 'noindex-follow-public',
      normalization: {},
      exact_routes: [
        { path: '/', classification: 'indexable-public', sitemap: true },
        { path: '/', classification: 'indexable-public', sitemap: true },
      ],
      sensitive_prefixes: [],
      backend_ingress_exceptions: [],
      dynamic_templates: [],
    })).toThrow(/duplicate exact route/i)
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

export type RouteClassification = 'indexable-public' | 'noindex-follow-public' | 'crawl-blocked-sensitive'

export interface LaunchRouteManifest {
  schema_version: 1
  revision: string
  canonical_origin: 'https://vinhlong360.vn'
  unknown_policy: 'noindex-follow-public'
  normalization: Record<string, string>
  exact_routes: Array<{ path: string; classification: Exclude<RouteClassification, 'crawl-blocked-sensitive'>; sitemap: boolean }>
  sensitive_prefixes: Array<{ prefix: string; classification: 'crawl-blocked-sensitive' }>
  backend_ingress_exceptions: Array<{ prefix: string; upstream: 'agent' | 'bot-gateway'; review_reason: string }>
  dynamic_templates: Array<{ template: string; authority: 'backend-entity' | 'backend-ward' | 'fixed-noindex'; sitemap: 'backend' | false }>
}

export function parseLaunchRouteManifest(value: unknown): LaunchRouteManifest {
  if (!value || typeof value !== 'object') throw new Error('route manifest must be an object')
  const manifest = value as LaunchRouteManifest
  if (manifest.schema_version !== 1 || !manifest.revision) throw new Error('unsupported route manifest')
  const exact = manifest.exact_routes.map(item => item.path)
  if (new Set(exact).size !== exact.length) throw new Error('duplicate exact route')
  const prefixes = manifest.sensitive_prefixes.map(item => item.prefix)
  if (new Set(prefixes).size !== prefixes.length) throw new Error('duplicate sensitive prefix')
  return Object.freeze(manifest)
}

export const launchRouteManifest = parseLaunchRouteManifest(manifestJson)
```

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
from pathlib import Path

import pytest

from launch_artifacts import load_artifact
from route_manifest import load_route_manifest


def test_fixture_path_is_explicit_and_production_has_no_fallback(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_artifact("launch-indexing-policy.json", release_root=tmp_path)


def test_route_manifest_rejects_duplicate_paths(tmp_path: Path):
    fixture = tmp_path / "manifest.json"
    fixture.write_text('{"schema_version":1,"revision":"r","exact_routes":[{"path":"/"},{"path":"/"}]}')
    with pytest.raises(ValueError, match="duplicate exact route"):
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

from ai_disclosure import load_ai_disclosure
from route_manifest import load_route_manifest
from pathlib import Path


@dataclass(frozen=True)
class LoadedArtifact:
    path: Path
    raw: bytes
    data: dict
    sha256: str


def load_artifact(name: str, *, release_root: Path | None = None, fixture_path: Path | None = None) -> LoadedArtifact:
    root = release_root or Path(__file__).resolve().parents[1]
    path = fixture_path or root / "config" / name
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

from launch_artifacts import LoadedArtifact, load_artifact


@dataclass(frozen=True)
class LoadedRouteManifest:
    artifact: LoadedArtifact
    revision: str
    data: dict


def load_route_manifest(*, fixture_path: Path | None = None) -> LoadedRouteManifest:
    artifact = load_artifact("launch-indexing-policy.json", fixture_path=fixture_path)
    data = artifact.data
    if data.get("schema_version") != 1 or not data.get("revision"):
        raise ValueError("unsupported route manifest")
    exact = [item["path"] for item in data.get("exact_routes", [])]
    if len(exact) != len(set(exact)):
        raise ValueError("duplicate exact route")
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
- Create: `agent/tests/test_route_manifest_parity.py`
- Create: `web-nuxt/tests/launch-route-parity.test.ts`
- Modify: `nginx.conf`
- Modify: `nginx-ssl.conf`

- [ ] **Step 1: Write the shared failing corpus and classifier assertions**

```json
[
  {"target": "/", "classification": "indexable-public", "canonical": "/"},
  {"target": "/admin", "classification": "crawl-blocked-sensitive", "canonical": "/admin"},
  {"target": "/administrator", "classification": "noindex-follow-public", "canonical": "/administrator"},
  {"target": "/system/x?debug=1", "classification": "crawl-blocked-sensitive", "canonical": "/system/x"},
  {"target": "/systematic", "classification": "noindex-follow-public", "canonical": "/systematic"},
  {"target": "/dia-diem/a", "classification": "backend-entity", "canonical": "/dia-diem/a"},
  {"target": "/dia-diem//a", "classification": "redirect-canonical", "canonical": "/dia-diem/a"},
  {"target": "/api%2Fsecret", "classification": "reject", "canonical": null}
]
```

Both test suites iterate the same corpus and compare classification plus canonical target.

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_route_manifest_parity.py -q`

Run: `cd web-nuxt && npm test -- --run tests/launch-route-parity.test.ts`

Expected: FAIL because normalization/classification functions do not exist.

- [ ] **Step 3: Implement identical precedence and static extraction**

```python
@dataclass(frozen=True)
class RouteDecision:
    classification: str
    canonical_path: str | None


def classify_request_target(target: str, manifest: LoadedRouteManifest) -> RouteDecision:
    path = target.split("?", 1)[0]
    if "%2f" in path.lower() or "%5c" in path.lower() or "\x00" in path:
        return RouteDecision("reject", None)
    normalized = "/" + "/".join(segment for segment in path.split("/") if segment)
    normalized = normalized if normalized == "/" else normalized.rstrip("/")
    for item in manifest.data["sensitive_prefixes"]:
        prefix = item["prefix"]
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return RouteDecision("crawl-blocked-sensitive", normalized)
    # Then exact routes, dynamic templates, and unknown noindex in that order.
```

Implement the equivalent TypeScript function and `extractStaticSitemapPaths()` in both languages. Update Nginx backend-route regexes to use end-or-slash boundaries; detailed ingress ownership remains Task 32.

- [ ] **Step 4: Run GREEN and parity checks**

Run: `python -m pytest agent/tests/test_route_manifest.py agent/tests/test_route_manifest_parity.py -q`

Run: `cd web-nuxt && npm test -- --run tests/launch-route-manifest.test.ts tests/launch-route-parity.test.ts`

Expected: both implementations return identical corpus results and exact static sitemap paths.

- [ ] **Step 5: Commit**

```bash
git add agent/route_manifest.py web-nuxt/server/utils/launch/launchRouteManifest.ts tests/fixtures/launch-route-parity-corpus.json agent/tests/test_route_manifest_parity.py web-nuxt/tests/launch-route-parity.test.ts nginx.conf nginx-ssl.conf
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
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/ai-disclosure.test.ts`

Expected: FAIL because the loader does not exist.

- [ ] **Step 3: Implement immutable validated copy access**

```ts
import disclosureJson from '#launch-config/ai-disclosure.json'

const AI_FULL = 'Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.'
const PLACEHOLDER_FULL = 'Minh họa đồ họa — chưa có ảnh riêng cho địa điểm.'

export interface AiDisclosureArtifact {
  schema_version: 1
  revision: string
  entity_ai: { short_label: 'Minh họa AI'; full_disclosure: typeof AI_FULL; accessible_description_key: string }
  placeholder: { short_label: null; full_disclosure: typeof PLACEHOLDER_FULL; accessible_description_key: string }
  ugc_photo: { short_label: string; full_disclosure: string; accessible_description_key: string }
  forbidden_entity_image_claims: string[]
}

export function parseAiDisclosure(value: unknown): Readonly<AiDisclosureArtifact> {
  const data = value as AiDisclosureArtifact
  if (data?.schema_version !== 1 || data.entity_ai?.full_disclosure !== AI_FULL || data.placeholder?.full_disclosure !== PLACEHOLDER_FULL) {
    throw new Error('canonical AI disclosure mismatch')
  }
  return Object.freeze(data)
}

export const aiDisclosure = parseAiDisclosure(disclosureJson)
```

- [ ] **Step 4: Run GREEN and typecheck**

Run: `cd web-nuxt && npm test -- --run tests/ai-disclosure.test.ts && npm run typecheck`

Expected: tests and typecheck pass.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/utils/aiDisclosure.ts web-nuxt/tests/ai-disclosure.test.ts
git commit -m "feat: load AI disclosure copy in Nuxt"
```

### Task 8: Add the Python disclosure loader

**Files:**
- Create: `agent/ai_disclosure.py`
- Create: `agent/tests/test_ai_disclosure.py`

- [ ] **Step 1: Write failing exact-copy and fixture tests**

```python
from pathlib import Path

import pytest

from ai_disclosure import load_ai_disclosure


def test_loads_exact_canonical_copy():
    disclosure = load_ai_disclosure()
    assert disclosure.entity_ai.full_disclosure == "Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ."


def test_rejects_altered_copy(tmp_path: Path):
    fixture = tmp_path / "ai.json"
    fixture.write_text('{"schema_version":1,"revision":"r","entity_ai":{"full_disclosure":"altered"}}')
    with pytest.raises(ValueError, match="canonical AI disclosure"):
        load_ai_disclosure(fixture_path=fixture)
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_ai_disclosure.py -q`

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


def load_ai_disclosure(*, fixture_path: Path | None = None) -> LoadedAiDisclosure:
    artifact = load_artifact("ai-disclosure.json", fixture_path=fixture_path)
    data = artifact.data
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

Run: `python -m pytest agent/tests/test_ai_disclosure.py -q`

Run: `python -m ruff check agent/ai_disclosure.py agent/tests/test_ai_disclosure.py`

Expected: tests and Ruff pass.

- [ ] **Step 5: Commit**

```bash
git add agent/ai_disclosure.py agent/tests/test_ai_disclosure.py
git commit -m "feat: load AI disclosure copy in Python"
```

## Phase 2: Backend Indexability and HTTP Policy Authority

### Task 9: Implement the non-place entity indexability authority

**Files:**
- Create: `agent/launch_evidence.py`
- Create: `agent/index_policy.py`
- Create: `agent/tests/test_index_policy.py`
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

INDEX_POLICY_REVISION = "index-policy-v1"
RESPONSE_MATRIX_REVISION = "launch-safety-matrix-v1"
CACHE_ISOLATION_REVISION = "launch-cache-isolation-v1"
SITEMAP_PROTOCOL_REVISION = "pinned-sitemap-bundle-v1"


def build_policy_fingerprint(*, route_digest: str, disclosure_digest: str) -> str:
    payload = {
        "index_policy": INDEX_POLICY_REVISION,
        "response_matrix": RESPONSE_MATRIX_REVISION,
        "cache_isolation": CACHE_ISOLATION_REVISION,
        "sitemap_protocol": SITEMAP_PROTOCOL_REVISION,
        "route_digest": route_digest,
        "disclosure_digest": disclosure_digest,
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
            route_digest=route.artifact.sha256,
            disclosure_digest=disclosure.artifact.sha256,
        ),
        route_manifest_revision=route.revision,
        backend_policy_revision=INDEX_POLICY_REVISION,
    )
```

```python
# agent/index_policy.py
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


def _public(entity: Mapping[str, object]) -> bool:
    return entity.get("status") != "provisional" and entity.get("verified") not in (False, 0)


def _descriptive_word_count(entity: Mapping[str, object]) -> int:
    summary = str(entity.get("summary") or "").strip()
    description = str(entity.get("description") or "").strip()
    parts = [summary]
    if description.casefold() != summary.casefold():
        parts.append(description)
    return len(re.findall(r"\b\w+\b", " ".join(parts), flags=re.UNICODE))


def decide_entity(entity: Mapping[str, object], evidence: PolicyEvidence) -> IndexPolicyDecision:
    reasons: list[str] = []
    if not _public(entity):
        reasons.append("not-publicly-eligible")
    if _descriptive_word_count(entity) < 130:
        reasons.append("description-below-130-words")
    return IndexPolicyDecision("entity", not reasons, tuple(reasons), evidence.policy_fingerprint, evidence.backend_policy_revision)
```

Delete the old 100-words-plus-image branch from `agent/seo.py` and retarget the data-schema hard check to `index_policy.decide_entity`.

- [ ] **Step 4: Run GREEN and focused SEO regressions**

Run: `python -m pytest agent/tests/test_index_policy.py tests/checks/test_hard_checks.py agent/tests/test_seo.py -q`

Run: `python -m ruff check agent/launch_evidence.py agent/index_policy.py scripts/checks/check_data_schema.py agent/tests/test_index_policy.py`

Expected: tests pass with the obsolete image-credit assertions replaced by zero-credit AI assertions.

- [ ] **Step 5: Commit**

```bash
git add agent/launch_evidence.py agent/index_policy.py agent/tests/test_index_policy.py agent/seo.py scripts/checks/check_data_schema.py tests/checks/test_hard_checks.py agent/tests/test_seo.py
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
    reasons: list[str] = []
    if not _public(ward):
        reasons.append("not-publicly-eligible")
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


class EntityDetailResponse(BaseModel):
    # Keep existing fields.
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
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_policy_http.py agent/tests/test_gap_fixes.py -q`

Expected: FAIL because `/api/entities/{entity_id}` still emits public cache headers, ETag, and 304 and can replay a full cached entity.

- [ ] **Step 3: Implement resolved-route registry enforcement and remove policy-input memoization**

```python
# agent/policy_http.py
from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyEndpoint:
    method: str
    path: str
    exposure: str


POLICY_ENDPOINTS = (
    PolicyEndpoint("GET", "/api/entities/{entity_id}", "public"),
    PolicyEndpoint("GET", "/_internal/launch-policy-attestation", "internal"),
    PolicyEndpoint("GET", "/_internal/launch-sitemaps/{document}", "internal"),
)


def enforce_policy_http_headers(response):
    response.headers["Cache-Control"] = "no-store"
    for name in ("ETag", "Last-Modified", "Expires"):
        response.headers.pop(name, None)
    return response
```

Match the resolved FastAPI route template, not the lexical URL, so `/api/entities/map` and other static routes keep their existing reviewed cache behavior. Remove `_entity_cache` from the policy-bearing detail handler; load policy-input fields from the database on every request. If presentation-only memoization remains, exclude `status`, `verified`, summary, description, type, relationships, ward-child counts, and every policy/evidence field.

- [ ] **Step 4: Run GREEN and registry source scan**

Run: `python -m pytest agent/tests/test_policy_http.py agent/tests/test_public_index_policy.py agent/tests/test_gap_fixes.py -q`

Expected: every status from the registered detail route is `no-store`, has no validator, never returns 304, and observes direct DB policy-input changes.

- [ ] **Step 5: Commit**

```bash
git add agent/policy_http.py agent/tests/test_policy_http.py agent/public_api.py agent/server.py agent/tests/test_gap_fixes.py
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

Expected: attestation returns exact evidence with no cache validators and is absent from public API docs.

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
    def __init__(self, root: Path, *, now=lambda: datetime.now(timezone.utc)):
        self.root = root
        self.now = now

    def publish(self, bundle: StoredBundle) -> None:
        with cross_process_lock(self.root / ".publish.lock"):
            staging = self.root / f".{bundle.batch_revision}.staging"
            write_bundle_and_fsync(staging, bundle)
            os.replace(staging, self.root / bundle.batch_revision)
            atomic_write_json(self.root / "active.json", {
                "batch_revision": bundle.batch_revision,
                "published_at": self.now().isoformat(),
            })
```

Promote or reuse the lock and atomic JSON replacement primitives from `versioned_json_store.py`; do not duplicate a weaker implementation.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_sitemap_store.py -q`

Expected: atomic publication, restart validation, corruption rejection, and retention tests pass.

- [ ] **Step 5: Commit**

```bash
git add agent/sitemap_store.py agent/tests/test_sitemap_store.py agent/versioned_json_store.py
git commit -m "feat: publish immutable sitemap bundles"
```

### Task 16: Verify PostgreSQL snapshot isolation and concurrent publication

**Files:**
- Create: `agent/tests/test_sitemap_bundle_postgres.py`

- [ ] **Step 1: Write the opt-in integration test**

```python
@pytest.mark.integration
def test_repeatable_read_ignores_second_connection_commit(disposable_pg):
    with open_snapshot(disposable_pg) as snapshot:
        mutate_entity_from_second_connection(disposable_pg, "entity-1", summary="changed")
        assert snapshot.entity("entity-1")["summary"] == "original"


@pytest.mark.integration
def test_concurrent_refresh_exposes_only_complete_bundle(disposable_pg, tmp_path):
    revisions = publish_concurrently(disposable_pg, tmp_path)
    active = SitemapBundleStore(tmp_path).load_active()
    assert active.batch_revision in revisions
    assert set(active.documents) == {"sitemap.xml", "sitemap-media.xml", "sitemap-index.xml"}
```

Use the guarded disposable PostgreSQL fixture pattern from `agent/tests/test_account_control_plane_postgres.py:25`; reject non-loopback database URLs unless an exact test-only override is supplied.

- [ ] **Step 2: Run the default safe-skip check**

Run: `python -m pytest agent/tests/test_sitemap_bundle_postgres.py -m integration -q`

Expected: SKIP when `SITEMAP_BUNDLE_TEST_DATABASE_URL` is absent.

- [ ] **Step 3: Implement the disposable database fixture and concurrency harness**

```python
url = os.getenv("SITEMAP_BUNDLE_TEST_DATABASE_URL")
if not url:
    pytest.skip("disposable PostgreSQL URL not configured")
parsed = urlparse(url)
if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and os.getenv("ALLOW_REMOTE_DISPOSABLE_PG") != "true":
    pytest.fail("PostgreSQL integration target must be loopback")
```

The fixture creates isolated tables, runs one refresh transaction and one concurrent mutation connection, then drops the isolated schema.

- [ ] **Step 4: Run GREEN against a disposable local PostgreSQL**

Run: `$env:SITEMAP_BUNDLE_TEST_DATABASE_URL='postgresql://vl360:vl360_dev_password@127.0.0.1:5432/vl360_launch_test'; python -m pytest agent/tests/test_sitemap_bundle_postgres.py -m integration -q`

Expected: real `REPEATABLE READ`, concurrent mutation, and atomic publication tests pass.

- [ ] **Step 5: Commit**

```bash
git add agent/tests/test_sitemap_bundle_postgres.py
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
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_sitemap_render.py agent/tests/test_sitemap_bundle.py -q`

Expected: FAIL because deterministic rendering, refresh orchestration, and the internal document route do not exist.

- [ ] **Step 3: Implement main rendering and CLI orchestration**

```python
def render_main_sitemap(snapshot, manifest, evidence) -> bytes:
    urls = set(static_sitemap_paths(manifest))
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
    public_ids = {entity["id"] for entity in snapshot.entities if entity.get("status") != "provisional" and entity.get("verified") not in (False, 0)}
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

`python -m agent.sitemap_bundle refresh` loads one snapshot, renders all current document types, validates them, and publishes through `SitemapBundleStore`. Backend startup validates `active.json` but never refreshes inside a GET.

Because existing agent modules use top-level imports, `agent/sitemap_bundle.py` must use the same direct-execution/module bootstrap pattern as `agent/mcp_server.py:35` so both `python agent/sitemap_bundle.py refresh` and the required module command resolve imports consistently without adding a repository-wide package refactor.

- [ ] **Step 4: Run GREEN and retire mutable main-sitemap ownership**

Run: `python -m pytest agent/tests/test_sitemap_snapshot.py agent/tests/test_sitemap_render.py agent/tests/test_sitemap_store.py agent/tests/test_sitemap_bundle.py agent/tests/test_launch_policy_api.py -q`

Expected: exact main XML and pinned internal response pass; legacy `web/data.json` fallback tests are removed.

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
def test_media_sitemap_includes_only_entity_ai_images(snapshot, manifest, evidence):
    xml = render_media_sitemap(snapshot, manifest, evidence)
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


def normalize_renderable_image_url(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    return value if value.startswith(("/", "https://", "http://")) else None


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

export function buildPolicyFingerprint(routeDigest: string, disclosureDigest: string): string {
  return createHash('sha256').update(JSON.stringify({
    cache_isolation: CACHE_ISOLATION_REVISION,
    disclosure_digest: disclosureDigest,
    index_policy: INDEX_POLICY_REVISION,
    response_matrix: RESPONSE_MATRIX_REVISION,
    route_digest: routeDigest,
    sitemap_protocol: SITEMAP_PROTOCOL_REVISION,
  })).digest('hex')
}
```

Add a shared fixture assertion that Python and TypeScript compute the same known fingerprint for fixed artifact digests.

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
})
```

Add separate tests for each fingerprint, route revision, backend revision, batch revision, and requested-batch echo mismatch.

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
  headers: Record<string, string>
}

function failedOpenSitemap(): GuardedSitemapResult {
  return {
    status: 503,
    body: '',
    headers: { 'cache-control': 'no-store', 'x-launch-indexing-policy': 'failed-open' },
  }
}

function validateAllLaunchEvidence(
  headers: Record<string, string>,
  decision: LaunchSafetyDecision,
  requestedBatch: string | null,
) {
  if (headers['x-launch-policy-fingerprint'] !== decision.policy_fingerprint) throw createError({ statusCode: 503 })
  if (headers['x-launch-route-manifest-revision'] !== decision.route_manifest_revision) throw createError({ statusCode: 503 })
  if (headers['x-launch-backend-policy-revision'] !== decision.backend_policy_revision) throw createError({ statusCode: 503 })
  if (!/^[a-f0-9]{64}$/.test(headers['x-launch-sitemap-batch-revision'] || '')) throw createError({ statusCode: 503 })
  if (requestedBatch && headers['x-launch-sitemap-requested-batch'] !== requestedBatch) throw createError({ statusCode: 503 })
}

export async function proxyGuardedSitemap(input: GuardedSitemapInput): Promise<GuardedSitemapResult> {
  if (input.decision.sitemap_action !== 'guarded-proxy') return failedOpenSitemap()
  const query = validateSitemapQuery(input.document, input.url)
  const upstream = await input.fetchRaw(input.document, query.requestedBatch)
  validateAllLaunchEvidence(upstream.headers, input.decision, query.requestedBatch)
  return { status: 200, body: upstream.body, headers: upstream.headers }
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
    batchRevision: result.headers['x-launch-sitemap-batch-revision'],
    body: result.body,
  }
}
```

The internal fetch targets only `/_internal/launch-sitemaps/{document}` over the private backend URL and never follows redirects.

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
  const headers = buildLaunchResponseHeaders({ decision })
  expect(headers['X-Launch-Indexing-Policy']).toBe(policy)
  expect(headers['Cache-Control']).toBe('no-store')
  expect(Boolean(headers['X-Launch-Policy-Fingerprint'])).toBe(hasEvidence)
})
```

Test error/404 HTML and all four root SEO handlers so the policy header appears exactly once.

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-headers.test.ts`

Expected: FAIL because legacy middleware writes only a conditional robots header.

- [ ] **Step 3: Store one request decision and finalize headers after page refinement**

```ts
export function buildLaunchResponseHeaders(input: {
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
    if (input.sitemap) headers['X-Launch-Sitemap-Batch-Revision'] = input.decision.sitemap_batch_revision!
    if (input.requestedBatch) headers['X-Launch-Sitemap-Requested-Batch'] = input.requestedBatch
  }
  return headers
}
```

The middleware resolves the base decision into `event.context.launchSafety`. The response plugin reads the final request-scoped value after entity refinement and overwrites/removes all launch headers in one place.

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
  Promise.resolve(refineEntityLaunchDecision({ base: selectiveOpen, carrier: { index_policy: { indexable: true } }, canonicalPath: true })),
  Promise.resolve(refineEntityLaunchDecision({ base: selectiveOpen, carrier: matchingEntityPolicy(false), canonicalPath: true })),
])

expect(failed.operational_state).toBe('failed-open')
expect(failed.policy_fingerprint).toBeNull()
expect(valid.operational_state).toBe('selective-open')
expect(valid.robots).toBe('noindex, follow')
expect(valid.sitemapDiscovery).toBe(true)
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/launch-entity-policy.test.ts`

Expected: FAIL because carrier validation and request-scoped refinement do not exist.

- [ ] **Step 3: Validate the mandatory carrier and update only the current event context**

```ts
export function refineEntityLaunchDecision(input: {
  base: Readonly<LaunchSafetyDecision>
  carrier: unknown
  canonicalPath: boolean
}): LaunchPageDecision {
  if (input.base.operational_state !== 'selective-open') return closedPageDecision(input.base)
  const policy = parseMatchingEntityPolicy(input.carrier, input.base)
  if (!policy) return failedOpenPageDecision('entity-policy-mismatch')
  return {
    ...input.base,
    robots: policy.indexable && input.canonicalPath ? 'index, follow' : 'noindex, follow',
    sitemapDiscovery: true,
  }
}

function parseMatchingEntityPolicy(carrier: unknown, base: LaunchSafetyDecision): IndexPolicyDecision | null {
  if (!carrier || typeof carrier !== 'object') return null
  const policy = (carrier as EntityPolicyCarrier).index_policy
  if (!policy || typeof policy.indexable !== 'boolean') return null
  if (policy.policy_fingerprint !== base.policy_fingerprint || policy.policy_revision !== base.backend_policy_revision) return null
  return policy
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

Entity detail refines from its existing `/api/entities/{id}` response. Ward detail additionally fetches that same exact policy carrier for the ward ID; it does not infer eligibility from `/api/places/{id}/overview`. The server composable mutates only `useRequestEvent().context.launchSafety` and serializes the final page state for hydration.

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
```

Remove the global index robots meta and unconditional sitemap link from `nuxt.config.ts`. Replace page-local launch robots declarations with `useLaunchSafety()` while keeping non-launch SEO metadata intact. Sensitive/admin pages remain noindex through route classification, not a page-owned quality predicate.

- [ ] **Step 4: Run GREEN and source scan**

Run: `cd web-nuxt && npm test -- --run tests/launch-head.test.ts tests/smoke.test.ts && npm run typecheck`

Expected: one robots meta, matching `X-Robots-Tag`, and the sitemap-index link only on fully attested selective-open HTML.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/nuxt.config.ts web-nuxt/composables/useLaunchSafety.ts web-nuxt/tests/launch-head.test.ts 'web-nuxt/pages/[...slug].vue' 'web-nuxt/pages/xa-phuong/[id].vue' web-nuxt/pages/tao-lich-trinh.vue 'web-nuxt/pages/nguoi-dung/[id].vue' 'web-nuxt/pages/lich-trinh-chia-se/[id].vue' 'web-nuxt/pages/bai-viet/[id].vue' web-nuxt/pages/tim-kiem.vue web-nuxt/pages/thong-bao.vue web-nuxt/pages/tai-khoan.vue web-nuxt/pages/da-luu.vue web-nuxt/pages/cai-dat.vue web-nuxt/layouts/admin.vue
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
  expect((await request('/sitemap.xml')).status).toBe(503)
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

Robots always permits public route groups and blocks every manifest-sensitive prefix. Closed/failed-open robots omit `Sitemap:`; selective-open robots advertises exactly `/sitemap-index.xml`. Closed sitemap handlers make zero backend calls, selective-open delegates to Task 21, and failed-open returns 503.

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
    "route_manifest_sha256": "64-hex",
    "disclosure_sha256": "64-hex",
    "policy_fingerprint": "64-hex"
  },
  "policy_route_classes": ["public-html", "public-api", "root-seo", "internal-readiness"],
  "compiled_cache_rules": [],
  "public_prerender_files": [],
  "service_worker": {"version": "vl360-launch-v1", "rule_digest": "64-hex"}
}
```

The generator scans `.output`, compiled route rules, and `public/sw.js`, writes `.output/server/launch-readiness-manifest.json`, and exits non-zero on any unsafe artifact. Add it after `nuxt build` in the build script.

- [ ] **Step 4: Run GREEN and build audit**

Run: `cd web-nuxt && npm test -- --run tests/launch-readiness-manifest.test.ts && npm run build`

Expected: generated manifest exists, validates, and records the final worker version/digest.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/scripts/generate-launch-readiness-manifest.mjs web-nuxt/server/utils/launch/readinessManifest.ts web-nuxt/tests/launch-readiness-manifest.test.ts web-nuxt/package.json
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
  if (!active.batchRevision) {
    throw createError({ statusCode: 503, data: { ok: false, reason: 'sitemap-batch-unavailable' } })
  }
  return { ok: true, state: 'selective-open', active_batch: active.batchRevision, checks: build.checks }
})
```

Do not return unlock values, backend URLs, free-form errors, or legal/owner evidence.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/launch-readiness.test.ts tests/launch-readiness-manifest.test.ts`

Expected: safe closed is backend-independent; safe open requires matching attestation and active bundle; every unsafe check is 503.

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

Run when Docker is available: `python -m pytest tests/launch_safety/integration/test_compose_cold_start.py -m integration -q`

Expected: closed/agent-absent Nuxt is healthy on the private network; exact-open/agent-absent Nuxt is unhealthy. Task 32 adds optional-upstream rendering before any integration test starts Nginx with agent absent.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml docker-compose.prod.yml docker-compose.dev.yml docker-compose.systemd-deps.yml ops/systemd agent/server.py agent/bot_gateway.py scripts/ops/compose_network_audit.py scripts/ops/socket_boundary_probe.py tests/launch_safety/test_compose_contract.py tests/launch_safety/test_systemd_contract.py tests/launch_safety/integration/test_compose_cold_start.py tests/launch_safety/integration/test_network_boundary.py
git commit -m "ops: enforce exclusive launch ingress topology"
```

### Task 31: Wire readiness into build and local deploy admission

**Files:**
- Modify: `scripts/deploy.sh:94-199`
- Modify: `web-nuxt/Dockerfile`
- Modify: `Dockerfile`
- Modify: `tests/test_release_quality_gates.py`
- Create: `tests/launch_safety/test_deploy_readiness.py`

- [ ] **Step 1: Write failing deploy-source contract tests**

```python
def test_deploy_uses_internal_readiness_not_homepage():
    script = Path("scripts/deploy.sh").read_text(encoding="utf-8")
    assert "_internal/launch-readiness" in script
    assert "curl -f http://localhost:3000/" not in script
    assert "systemctl restart vl-agent vl-nuxt" not in script


def test_release_contains_config_ingress_units_and_network_audit(release_members):
    assert {"config", "nginx.conf", "nginx-ssl.conf", "ops/systemd", "compose-network-audit.json"} <= release_members
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_deploy_readiness.py tests/test_release_quality_gates.py -q`

Expected: FAIL because current deploy packaging omits the reviewed artifacts and healthchecks the wrong surfaces.

- [ ] **Step 3: Package reviewed bytes and gate traffic on local readiness**

Update the build to run the Task 28 output audit. Update `scripts/deploy.sh` so its source path:

```bash
curl --fail --silent --show-error \
  http://127.0.0.1:3000/_internal/launch-readiness >/tmp/vl360-launch-readiness.json
```

occurs after installing the candidate and before Nginx is reopened. Backend/Nuxt/config/units/rendered-ingress must be revision-aligned in the launch package. Do not execute a real deploy in this task.

- [ ] **Step 4: Run GREEN and syntax/build verification**

Run: `python -m pytest tests/launch_safety/test_deploy_readiness.py tests/test_release_quality_gates.py -q`

Run: `& 'C:\Program Files\Git\bin\bash.exe' -n scripts/deploy.sh`

Run when Docker is available: `docker build -f web-nuxt/Dockerfile -t vl360-nuxt:launch-safety .`

Expected: tests and syntax pass; the build contains canonical digests and readiness evidence.

- [ ] **Step 5: Commit**

```bash
git add scripts/deploy.sh web-nuxt/Dockerfile Dockerfile tests/test_release_quality_gates.py tests/launch_safety/test_deploy_readiness.py
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

Systemd rendering uses literal loopback targets. Do not use a URI suffix with variable `proxy_pass`; preserve raw path/query and keep `/admin-api` rewrite behavior covered by integration tests. Add exact root SEO locations to Nuxt, disable proxy caching, preserve policy/evidence headers, deny all launch-internal paths, and parity-check every agent/bot alias against the route manifest.

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
```

```ts
expect(parseGalleryDescriptor(apiEntityImage).source_class).toBe('ai-generated')
expect(parseGalleryDescriptor(apiReviewImage).source_class).toBe('user-uploaded')
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

export function parseGalleryDescriptor(value: unknown): ImageDescriptor | null {
  if (!value || typeof value !== 'object') return null
  const descriptor = value as ImageDescriptor
  if (!descriptor.url || !['ai-generated', 'placeholder', 'user-uploaded'].includes(descriptor.source_class)) return null
  if (!descriptor.full_disclosure || !descriptor.disclosure_key) return null
  return descriptor
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

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_image_descriptor.py agent/tests/test_public_index_policy.py -q`

Run: `cd web-nuxt && npm test -- --run tests/image-descriptors.test.ts && npm run typecheck`

Expected: backend/frontend descriptor shapes agree and review photos are never labeled AI.

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
    {"file": "components/EntityCard.vue", "access_path": "entity.images", "producer": "describeEntityImages", "presentation": "short"},
    {"file": "pages/dia-diem/[id].vue", "access_path": "gallery.images", "producer": "parseGalleryDescriptor", "presentation": "full"},
    {"file": "pages/admin/media.vue", "access_path": "entity.images", "producer": "describeEntityImages", "presentation": "short-and-full"},
    {"file": "pages/ban-do.vue", "access_path": "popup", "producer": "no-image-invariant", "presentation": "none"}
  ]
}
```

Populate the complete approved inventory, not only these examples. The scanner covers Vue templates/scripts, composables, adapters, background styles, and raw `image/images/image_urls` props; registration never exempts a renderer from descriptor conversion.

```python
RAW_PATTERNS = (
    re.compile(r"\bentity\.images\b"),
    re.compile(r"\b(?:entity|event|saved|item)\.images\s*\[\s*0\s*\]"),
    re.compile(r"\b(?:entity|event|saved|item)\.(?:image|image_url|image_urls)\b"),
)


def scan_entity_image_renderers(root: Path, registry: list[dict]) -> list[Finding]:
    registered = {(item["file"], item["access_path"]) for item in registry}
    findings: list[Finding] = []
    for path in iter_frontend_source_files(root):
        text = path.read_text(encoding="utf-8")
        for pattern in RAW_PATTERNS:
            for match in pattern.finditer(text):
                access = match.group(0)
                if (path.as_posix(), access) not in registered and "data-entity-image-policy=\"no-image-invariant\"" not in text:
                    findings.append(Finding("UNREGISTERED_ENTITY_IMAGE_RENDERER", path, access))
    return findings
```

- [ ] **Step 4: Run GREEN and hard gate**

Run: `python -m pytest tests/launch_safety/test_entity_image_renderer_guard.py tests/checks/test_hard_checks.py -q`

Run: `cd web-nuxt && npm test -- --run tests/image-renderer-inventory.test.ts`

Expected: all current renderers are registered and a synthetic raw renderer fails the guard.

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
```

```python
def test_ugc_does_not_change_indexability_or_media_sitemap(public_thin_entity, evidence):
    public_thin_entity["review_images"] = ["/img/review.jpg"]
    assert decide_entity(public_thin_entity, evidence).indexable is False
    assert b"review.jpg" not in render_media_sitemap(snapshot_with(public_thin_entity), manifest, evidence)
```

- [ ] **Step 2: Run RED**

Run: `cd web-nuxt && npm test -- --run tests/ugc-image-classification.test.ts`

Run: `python -m pytest agent/tests/test_image_descriptor.py agent/tests/test_index_policy.py agent/tests/test_sitemap_render.py -q`

Expected: FAIL because UGC surfaces use bare URLs and mixed gallery rows have no source class.

- [ ] **Step 3: Convert UGC renderers without changing the entity quality predicate**

Review/post/admin moderation surfaces use `user-uploaded` descriptors with available credit. PostCard’s bespoke lightbox and share path retain UGC classification. Backend decision and media rendering explicitly ignore review/post descriptors for real-image credit and image-sitemap membership.

- [ ] **Step 4: Run GREEN**

Run: `cd web-nuxt && npm test -- --run tests/ugc-image-classification.test.ts tests/gallery-disclosure.test.ts && npm run typecheck`

Run: `python -m pytest agent/tests/test_image_descriptor.py agent/tests/test_index_policy.py agent/tests/test_sitemap_render.py -q`

Expected: UGC is truthful, credited, never labeled AI, and never changes current quality/sitemap output.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/ReviewCard.vue web-nuxt/components/PostCard.vue web-nuxt/components/EntityFeed.vue web-nuxt/pages/admin/kiem-duyet.vue agent/public_api.py agent/index_policy.py agent/sitemap_render.py web-nuxt/tests/ugc-image-classification.test.ts agent/tests/test_image_descriptor.py agent/tests/test_index_policy.py agent/tests/test_sitemap_render.py
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
- Create: `scripts/ops/probe_launch_boundary.py`
- Create: `scripts/launch_safety_browser_e2e.mjs`
- Create: `tests/launch_safety/integration/test_launch_matrix.py`
- Modify: `scripts/smoke_e2e_chrome.mjs` only if extracting a shared CDP helper
- Modify: `web-nuxt/package.json`

- [ ] **Step 1: Write the failing matrix and persistent-browser-profile tests**

```python
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

Run: `python -m pytest tests/launch_safety/integration/test_launch_matrix.py -m integration -q`

Expected: FAIL or safe SKIP because the HTTP/browser harness does not exist.

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

Use the existing Chrome CDP approach. Keep one profile across old/new worker phases, inspect Cache Storage through CDP, test offline replay denial, and record that direct host 3000/8360/internal endpoint probes fail.

- [ ] **Step 4: Run GREEN locally where dependencies exist**

Run: `python -m pytest tests/launch_safety/integration/test_launch_matrix.py tests/launch_safety/integration/test_nginx_boundary.py tests/launch_safety/integration/test_network_boundary.py -m integration -q`

Run: `cd web-nuxt && npm run smoke:launch-safety`

Expected: the full matrix passes; unavailable Docker/Chrome dependencies produce explicit skips, not false passes.

- [ ] **Step 5: Commit**

```bash
git add scripts/ops/probe_launch_boundary.py scripts/launch_safety_browser_e2e.mjs tests/launch_safety/integration/test_launch_matrix.py scripts/smoke_e2e_chrome.mjs web-nuxt/package.json
git commit -m "test: exercise the launch safety matrix"
```

### Task 44: Add and rehearse the single-host rollback runbook

**Files:**
- Create: `ops/nginx/maintenance/http-context.conf.template`
- Create: `ops/nginx/maintenance/server-enabled.conf`
- Create: `ops/nginx/maintenance/server-disabled.conf`
- Create: `scripts/ops/maintenance_mode.sh`
- Create: `scripts/ops/rehearse_launch_rollback.sh`
- Create: `scripts/ops/local_command_stub.py`
- Create: `docs/runbooks/launch-safety-rollback.md`
- Modify: `scripts/ops/watchdog.sh`
- Modify: `ops/systemd/vl-watchdog.service`
- Modify: `ops/systemd/vl-watchdog.timer`
- Create: `tests/launch_safety/test_watchdog_contract.py`
- Create: `tests/launch_safety/test_rollback_runbook.py`

- [ ] **Step 1: Write failing ordering and no-live-claim tests**

```python
def test_runbook_orders_drain_before_process_stop(runbook_steps):
    assert runbook_steps.index("suspend-watchdog") < runbook_steps.index("enable-maintenance")
    assert runbook_steps.index("enable-maintenance") < runbook_steps.index("stop-vl-nuxt")
    assert runbook_steps.index("closed-readiness") < runbook_steps.index("reopen-nginx")
    assert runbook_steps.index("reopen-probe") < runbook_steps.index("enable-watchdog")


def test_rehearsal_never_claims_stage3_sla(script_text):
    assert "stage3_claim=false" in script_text
    assert "live_sla_proven=true" not in script_text
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/launch_safety/test_watchdog_contract.py tests/launch_safety/test_rollback_runbook.py -q`

Expected: FAIL because tracked maintenance artifacts, executable rehearsal, and ordering tests do not exist.

- [ ] **Step 3: Implement the exact single-host sequence**

```bash
set -euo pipefail
MODE=${1:---local-rehearsal}
STAGE3_CLAIM=false

if [ "$MODE" = "--execute-on-host" ]; then
  [ "${ACKNOWLEDGE_MAINTENANCE:-}" = "launch-safety-rollback" ] || exit 64
  RUN=
else
  RUN="python scripts/ops/local_command_stub.py"
fi

$RUN systemctl stop vl-watchdog.timer vl-watchdog.service
$RUN scripts/ops/maintenance_mode.sh enable
$RUN nginx -t
$RUN systemctl reload nginx
$RUN systemctl stop vl-nuxt
# Purge only paths enumerated by the installed readiness manifest.
$RUN systemctl start vl-nuxt
$RUN curl --fail http://127.0.0.1:3000/_internal/launch-readiness
$RUN python scripts/ops/probe_launch_boundary.py --expect closed --maintenance-probe
$RUN scripts/ops/maintenance_mode.sh disable
$RUN nginx -t
$RUN systemctl reload nginx
$RUN python scripts/ops/probe_launch_boundary.py --expect closed
$RUN systemctl start vl-watchdog.timer
```

Create `scripts/ops/local_command_stub.py` to execute the same state machine against sandboxed temporary paths and stub services. This workstream runs only the default `--local-rehearsal` mode; it never invokes `--execute-on-host`. The runbook documents recovery: remain in maintenance, roll forward to a corrected closed artifact, otherwise restore the recorded known-good closed package; never restore an open artifact.

- [ ] **Step 4: Run GREEN and Bash syntax checks**

Run: `python -m pytest tests/launch_safety/test_watchdog_contract.py tests/launch_safety/test_rollback_runbook.py -q`

Run: `& 'C:\Program Files\Git\bin\bash.exe' -n scripts/ops/maintenance_mode.sh`

Run: `& 'C:\Program Files\Git\bin\bash.exe' -n scripts/ops/rehearse_launch_rollback.sh`

Expected: ordering, safety, maintenance, watchdog, and local elapsed-time evidence tests pass; no live SLA claim is emitted.

- [ ] **Step 5: Commit**

```bash
git add ops/nginx/maintenance scripts/ops/maintenance_mode.sh scripts/ops/rehearse_launch_rollback.sh scripts/ops/local_command_stub.py docs/runbooks/launch-safety-rollback.md scripts/ops/watchdog.sh ops/systemd/vl-watchdog.service ops/systemd/vl-watchdog.timer tests/launch_safety/test_watchdog_contract.py tests/launch_safety/test_rollback_runbook.py
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
$env:SITEMAP_BUNDLE_TEST_DATABASE_URL='postgresql://vl360:vl360_dev_password@127.0.0.1:5432/vl360_launch_test'
python -m pytest agent/tests/test_sitemap_bundle_postgres.py -m integration -q
python -m pytest tests/launch_safety/integration -m integration -q
cd web-nuxt
npm run smoke:launch-safety
```

Expected: provisioned opt-in checks pass; unavailable local dependencies are recorded as explicit skips. The known parallel resource timeout is recorded separately and never changes functional expectations.

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
