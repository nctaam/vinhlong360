# Launch Safety Remediation Implementation Plan

> STATUS: implementation complete / launch remains closed - approved remediation direction from the 2026-07-20 repository audit; no deploy, production mutation, secret change, or live indexing authorization.

> **Progress truth (refreshed after `c1875b3`):** Tasks 1-8 implementation machinery and the bounded backend runner are integrated on `codex/ls-remed-rollback`. The official revision-bound matrix passed at candidate `c1875b37f643ac6ca06a4db25ccce4902b04d717` with exit `0`; `EvidenceDocument.validate_final()` validated all 12 required sections. Exact pass/skip values are authoritative in `docs/superpowers/results/2026-07-20-launch-safety-gate-evidence.md`, committed as Evidence B `580b9b8`. Backend full regression used serial Phase A excluding `tests/launch_safety/test_closed_installer.py`, then only that installer module with exactly two xdist workers. Equivalence remains authoritative only at `a79b094` (303/303 node IDs and JUnit cases, identical outcomes, 284 passed/19 skipped in both runs); from `a79b094` to `c1875b3` only the two route-guard files changed. Global `noindex` and external gates remain active (`H1=blocked; H2=blocked; owner=not-authorized`); no push, merge, deploy, production mutation, secret change, or live indexing authorization is granted.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the AI-only media policy, close launch-runtime safety gaps, make regression/hard gates green, and then record trustworthy Task 45 evidence.

**Architecture:** Existing image data remains untouched, but only canonical AI entity media and placeholders may cross public/render/SEO boundaries. Nuxt remains the public SEO authority. Launch operations consume the reviewed combined release package and explicit opt-in evidence harnesses. No production data, deploy, secret, or live indexing state is changed.

**Tech Stack:** FastAPI/Python, pytest, Nuxt 4/Vue 3/TypeScript, PowerShell, Bash, Nginx, Docker Compose.

---

## Execution lanes

- **Session baseline:** run `python scripts/ops/run_backend_regression.py --deadline-seconds 7000` once before workers begin and record every known failure. The runner keeps phases sequential: Phase A is serial, and only `tests/launch_safety/test_closed_installer.py` runs in Phase B with exactly two xdist workers. The seven Nginx route-parity failures and the noindex AST guard failure were historical RED findings and are remediated; fresh full-suite status/evidence remains pending, and any newly observed failure stops execution.
- **First wave:** Tasks 1, 3, 4 and 7 are file-disjoint and may run concurrently.
- **Second wave:** Task 2 depends on Task 1; Task 5 follows Task 4 because they share rollback tests; Task 6 depends on Task 5; Task 8 runs after Tasks 1-7.
- **Task 9 - Task 45 evidence:** starts only after Tasks 1-8 pass review and functional/hard gates are green on a clean commit.

Every task follows RED -> GREEN -> focused verification -> self-review -> commit -> spec review -> quality review.

## Task 1: Enforce the canonical AI-image boundary

**Files:**
- Create: `agent/media_policy.py`
- Modify: `agent/image_descriptor.py`, `agent/admin.py`, `agent/social.py`, `agent/public_api.py`
- Modify: `web-nuxt/utils/imageDescriptors.ts`
- Test: `agent/tests/test_media_policy.py`, existing image/admin tests, `web-nuxt/tests/image-descriptors.test.ts`

- [x] **Step 1: Write failing backend tests**

```python
def test_legacy_entity_images_require_canonical_ai_path():
    assert describe_entity_images({"id": "x", "images": ["/img/entities/ok.webp"]})[0].source_kind == "entity-editorial"
    assert describe_entity_images({"id": "x", "images": ["https://cdn.example/photo.jpg"]}) == []

def test_admin_non_ai_ingest_is_rejected_without_mutation(client_mocked):
    response = client_mocked.post("/admin/entities/x/images", json={"url": "https://cdn.example/photo.jpg"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ai_only_media"
```

Cover URL add, file upload, suggestion approval, entity create/update with non-empty raw images, social upload/post/draft images, and unchanged DB/storage/network state. Pydantic shape errors remain 422.

- [x] **Step 2: Write failing frontend tests**

Assert unknown legacy URLs return no descriptor; user-uploaded/unknown descriptors never become AI; public helpers suppress review/post sources.

- [x] **Step 3: Run RED**

```powershell
python -m pytest agent/tests/test_media_policy.py agent/tests/test_image_descriptor.py agent/tests/test_admin_mutations.py -q
cd web-nuxt; npm test -- --run tests/image-descriptors.test.ts tests/image-adapters.test.ts
```

- [x] **Step 4: Implement minimal policy**

`agent/media_policy.py` owns exact source triples and `AI_ONLY_MEDIA_DETAIL = {"code": "ai_only_media", ...}`. Legacy entity strings are trusted only when they match `/img/entities/<lowercase-slug>.webp` with no query/fragment. Explicit renderable entity descriptors require `ai-generated/entity-editorial/entity-ai`; placeholders remain allowed. Unknown/UGC media is suppressed, never relabeled. Admin/social non-AI ingest returns 400 before storage, network or DB mutation. Existing stored values are not rewritten or deleted.

- [x] **Step 5: Run GREEN and commit**

```powershell
python -m pytest agent/tests/test_media_policy.py agent/tests/test_image_descriptor.py agent/tests/test_admin_mutations.py -q
cd web-nuxt; npm test -- --run tests/image-descriptors.test.ts tests/image-adapters.test.ts
git add agent/media_policy.py agent/image_descriptor.py agent/admin.py agent/social.py agent/public_api.py agent/tests/test_media_policy.py agent/tests/test_image_descriptor.py agent/tests/test_admin_mutations.py web-nuxt/utils/imageDescriptors.ts web-nuxt/tests/image-descriptors.test.ts web-nuxt/tests/image-adapters.test.ts
git commit -m "fix: enforce ai-only media provenance"
```

## Task 2: Suppress public UGC/unknown media and retire legacy SEO roots

**Files:**
- Modify: `agent/public_api.py`, `agent/seo.py`, `agent/server.py`
- Modify: `web-nuxt/components/ReviewCard.vue`, `PostCard.vue`, `EntityCard.vue`, `SavedEntityCard.vue`, `web-nuxt/pages/bai-viet/[id].vue`
- Modify: `web-nuxt/config/entity-image-renderers.json`, `scripts/checks/check_entity_image_renderers.py`
- Test: image metadata, SEO, renderer inventory and guard suites

- [x] **Step 1: Write RED tests**

Assert public gallery/list/detail/JSON-LD/OG/media sitemap contain only AI editorial or placeholder descriptors. Review/post photos are absent from public image arrays. Root `/robots.txt`, `/sitemap-media.xml`, and `/sitemap-index.xml` are not registered on `seo.router`. Registry rows use `render_policy: render` for AI/placeholder and `render_policy: suppress` plus `no-image-invariant` for UGC.

- [x] **Step 2: Run RED**

```powershell
python -m pytest agent/tests/test_seo.py agent/tests/test_seo_structured.py agent/tests/test_image_metadata_disclosure.py tests/launch_safety/test_entity_image_renderer_guard.py -q
cd web-nuxt; npm test -- --run tests/image-metadata-disclosure.test.ts tests/ugc-image-classification.test.ts tests/image-renderer-inventory.test.ts
```

- [x] **Step 3: Implement**

Remove review-row appending from the public entity gallery while retaining moderation data. Gate every SEO image object through the shared AI predicate and remove raw URL/legacy-credit fallbacks. Remove public FastAPI root SEO decorators; immutable internal launch sitemap routes remain. Update renderer inventory/checker so suppressed rows fail if a public `<img>`, background, OG or JSON-LD sink reappears.

- [x] **Step 4: Verify and commit**

```powershell
python -m pytest agent/tests/test_seo.py agent/tests/test_seo_structured.py agent/tests/test_image_metadata_disclosure.py tests/launch_safety/test_entity_image_renderer_guard.py -q
cd web-nuxt; npm test -- --run tests/image-metadata-disclosure.test.ts tests/ugc-image-classification.test.ts tests/image-renderer-inventory.test.ts; npm run typecheck
git add agent/public_api.py agent/seo.py agent/server.py agent/tests/test_seo.py agent/tests/test_seo_structured.py agent/tests/test_image_metadata_disclosure.py web-nuxt/components/ReviewCard.vue web-nuxt/components/PostCard.vue web-nuxt/components/EntityCard.vue web-nuxt/components/SavedEntityCard.vue web-nuxt/pages/bai-viet/[id].vue web-nuxt/config/entity-image-renderers.json web-nuxt/tests/image-metadata-disclosure.test.ts web-nuxt/tests/ugc-image-classification.test.ts web-nuxt/tests/image-renderer-inventory.test.ts scripts/checks/check_entity_image_renderers.py tests/launch_safety/test_entity_image_renderer_guard.py
git commit -m "fix: suppress non-ai public media"
```

## Task 3: Use relationship snapshot for ward sitemap counts

**Files:**
- Modify: `agent/sitemap_render.py`, `agent/index_policy.py`, `docs/api-contract.md`
- Test: `agent/tests/test_sitemap_render.py`, `agent/tests/test_sitemap_snapshot.py`

- [x] **Step 1: Add RED divergence test**

Create a snapshot where `located_in` points to ward A while child `placeId` points to ward B; assert the sitemap count follows the snapshot relationship.

- [x] **Step 2: Run RED**

```powershell
python -m pytest agent/tests/test_sitemap_render.py::test_ward_child_counts_use_relationship_snapshot -q
```

- [x] **Step 3: Implement and document**

Pass `snapshot.relationships` into the ward count authority and count only valid `located_in` edges. Update `docs/api-contract.md` for all three immutable sitemap documents and exact query validation.

- [x] **Step 4: Verify and commit**

```powershell
python -m pytest agent/tests/test_sitemap_render.py agent/tests/test_sitemap_snapshot.py -q
git add agent/sitemap_render.py agent/index_policy.py agent/tests/test_sitemap_render.py agent/tests/test_sitemap_snapshot.py docs/api-contract.md
git commit -m "fix: count ward children from snapshot relations"
```

## Task 4: Make rollback admission and recovery truthful

**Files:**
- Modify: `scripts/ops/rehearse_launch_rollback.sh`, `scripts/ops/local_command_stub.py`
- Modify: `docs/runbooks/launch-safety-rollback.md`
- Test: `tests/launch_safety/test_rollback_runbook.py`, `tests/launch_safety/test_watchdog_contract.py`

- [x] **Step 1: Write runtime RED tests**

Cover failure while stopping watchdog, enabling maintenance, reloading Nginx, and probing the closed boundary. Assert recovery is armed before the first mutation; original exit status is preserved; all later recovery phases are recorded passed/failed/skipped; `drained` requires both public and operator-source proof. The local stub must model service/listener/readiness transitions and must not curl an unrelated host process.

- [x] **Step 2: Run RED**

```powershell
python -m pytest tests/launch_safety/test_rollback_runbook.py tests/launch_safety/test_watchdog_contract.py -q
```

- [x] **Step 3: Implement**

Arm the recovery trap before watchdog/selector/Nginx mutation. Replace unconditional `TRAFFIC_STATE=drained` with the existing full boundary classifier. Make local readiness/listener/dependency authorities injectable and deterministic; keep the reviewed Task 31 listener contract at loopback port 3000 unless the package contract explicitly requires an agent listener.

- [x] **Step 4: Verify and commit**

```powershell
python -m pytest tests/launch_safety/test_rollback_runbook.py tests/launch_safety/test_watchdog_contract.py -q
& 'C:\Program Files\Git\bin\bash.exe' -n scripts/ops/rehearse_launch_rollback.sh
git add scripts/ops/rehearse_launch_rollback.sh scripts/ops/local_command_stub.py docs/runbooks/launch-safety-rollback.md tests/launch_safety/test_rollback_runbook.py tests/launch_safety/test_watchdog_contract.py
git commit -m "fix: make rollback recovery fail closed"
```

## Task 5: Make the closed installer atomic and authority-verified

**Files:**
- Modify: `scripts/ops/install_closed_release.sh`, `scripts/ops/verify_closed_release.py`
- Create: `tests/launch_safety/test_closed_installer.py`
- Test: `tests/launch_safety/test_rollback_runbook.py`, `tests/launch_safety/test_closed_installer.py`

- [x] **Step 1: Write RED tests**

Force a failure after persistent-data detach and after release-root swap; assert old root, mount and bytes are restored. Assert verifier flags for config/ingress/unit digests and persistent mount are executed, not only parsed. Assert dependency checks cover staged Python and Nuxt production dependencies and installed unit bytes match the package manifest.

- [x] **Step 2: Run RED**

```powershell
python -m pytest tests/launch_safety/test_rollback_runbook.py tests/launch_safety/test_closed_installer.py -q
```

- [x] **Step 3: Implement**

Replace explicit `die; exit` paths after mutation with error propagation through one rollback authority. Verify `findmnt` source/options, package digests and unit bytes before activation. Run injected/local-safe dependency and unit installation hooks; record exact results without live claims.

- [x] **Step 4: Verify and commit**

```powershell
python -m pytest tests/launch_safety/test_rollback_runbook.py tests/launch_safety/test_closed_installer.py -q
& 'C:\Program Files\Git\bin\bash.exe' -n scripts/ops/install_closed_release.sh
git add scripts/ops/install_closed_release.sh scripts/ops/verify_closed_release.py tests/launch_safety/test_rollback_runbook.py tests/launch_safety/test_closed_installer.py
git commit -m "fix: make closed release installation atomic"
```

## Task 6: Wire canonical deploy and Compose runtime contracts

**Files:**
- Modify: `scripts/deploy.sh`, `docker-compose.yml`, `docker-compose.prod.yml`, `web-nuxt/Dockerfile`
- Modify: `scripts/ops/compose_network_audit.py`
- Test: `tests/launch_safety/test_deploy_readiness.py`, `tests/launch_safety/test_release_package.py`, `tests/launch_safety/test_compose_contract.py`

- [x] **Step 1: Write RED deploy/Compose tests**

Assert deploy uses the combined launch archive, sidecar, verifier and installer; reject `vl-deploy.tar.gz`, `vl-nuxt-output.tar.gz`, direct release `tar -xzf`, and `rm -rf .output`. Assert Compose provides a writable/populated maintenance runtime before Nginx startup. Assert Nuxt receives build-time `API_BASE=http://agent:8360` and runtime `NUXT_API_BASE=http://agent:8360`.

- [x] **Step 2: Run RED**

```powershell
python -m pytest tests/launch_safety/test_deploy_readiness.py tests/launch_safety/test_release_package.py tests/launch_safety/test_compose_contract.py -q
```

- [x] **Step 3: Implement**

Make deploy produce/upload the existing combined release package and `.sha256`, run remote verification, then invoke the closed installer. Keep destructive data/migration flags outside this closed-release path. Add Compose runtime initialization/mount shared with `maintenance_mode.sh`; preserve exclusive ingress/network checks. Pass API origin at both build and runtime layers.

- [x] **Step 4: Verify and commit**

```powershell
python -m pytest tests/launch_safety/test_deploy_readiness.py tests/launch_safety/test_release_package.py tests/launch_safety/test_compose_contract.py -q
& 'C:\Program Files\Git\bin\bash.exe' -n scripts/deploy.sh
git add scripts/deploy.sh docker-compose.yml docker-compose.prod.yml web-nuxt/Dockerfile scripts/ops/compose_network_audit.py tests/launch_safety
git commit -m "fix: deploy the canonical closed release"
```

## Task 7: Fix Nginx/noindex guard drift

**Files:**
- Modify: `agent/tests/test_route_manifest_parity.py`, `web-nuxt/nuxt.config.ts`
- Test: existing route-parity and noindex guard tests

- [x] **Step 1: Add RED guard assertions**

Add fixtures allowing only the exact reviewed `$agent_upstream$request_uri`, bot and Nuxt variable targets; arbitrary variables remain rejected. Preserve HTTP/HTTPS parity, admin rewrite and segment-boundary assertions. Keep the noindex AST guard fail-closed.

- [x] **Step 2: Reproduce RED**

```powershell
python -m pytest agent/tests/test_route_manifest_parity.py tests/test_entity_status_migration_guardrails.py::test_global_noindex_default_and_authoritative_header_are_executable_code -q
```

Expected: seven variable-proxy failures and one security-header object-literal failure.

- [x] **Step 3: Implement**

Resolve only approved variable targets to audited upstream identities in the test parser. Inline the `nitro.routeRules['/**'].headers` object literal, or teach the AST guard to resolve one immutable local constant without accepting dynamic expressions. Do not broaden variable handling or remove noindex behavior.

- [x] **Step 4: Verify and commit**

```powershell
python -m pytest agent/tests/test_route_manifest_parity.py tests/test_entity_status_migration_guardrails.py::test_global_noindex_default_and_authoritative_header_are_executable_code -q
git add agent/tests/test_route_manifest_parity.py web-nuxt/nuxt.config.ts tests/helpers/noindex_ast_guard.cjs tests/test_entity_status_migration_guardrails.py
git commit -m "fix: align launch guards with reviewed ingress"
```

## Task 8: Restore standards ratchets

**Files:**
- Refactor every non-baseline R20.8 function: `agent/admin.py::bulk_ban_users`, `agent/database.py::_conn`, three validators in `agent/image_descriptor.py`, `agent/launch_policy_api.py::launch_sitemap_document`, `agent/publication_status.py::decide_publication_candidate`, two functions in `agent/route_manifest.py`, `agent/sitemap_bundle.py::build_bundle`, `agent/sitemap_store.py::_validate_metadata_envelope`, three validators in `scripts/package_launch_release.py`, `scripts/postgres_target.py::canonical_target_identity`, two functions in `scripts/stage_b_attestation.py`, and two functions in `scripts/ops/compose_network_audit.py`. The three existing chat handlers are the only allowed baseline count.
- Replace net-new R30.3 literals in `web-nuxt/components/ImageLightbox.vue`, `web-nuxt/components/PhotoGallery.vue`, `web-nuxt/components/PostCard.vue`, `web-nuxt/pages/admin/entities.vue`, `web-nuxt/pages/admin/media.vue`, `web-nuxt/pages/bai-viet/[id].vue`, `web-nuxt/pages/dia-diem/[id].vue`, and `web-nuxt/pages/index.vue`.
- Test: `tests/checks/test_hard_checks.py`

- [x] **Step 1: Capture RED**

```powershell
python scripts/checks/run_hard.py --all
```

Historical RED captured before the ratchet refactor: R20.8 and R30.3 exceeded their baselines.

- [x] **Step 2: Refactor by independent file group**

Extract validation/normalization helpers until `run_hard.py --all` reports R20.8 at or below the committed baseline of 3. Replace new literal colors with existing semantic tokens until R30.3 is at or below 306. Do not update the baseline to hide debt.

- [x] **Step 3: Verify and commit**

```powershell
python -m pytest tests/checks/test_hard_checks.py -q
python scripts/checks/run_hard.py --all
git diff --check
git add agent/admin.py agent/database.py agent/image_descriptor.py agent/launch_policy_api.py agent/publication_status.py agent/route_manifest.py agent/sitemap_bundle.py agent/sitemap_store.py scripts/package_launch_release.py scripts/postgres_target.py scripts/stage_b_attestation.py scripts/ops/compose_network_audit.py web-nuxt/components/ImageLightbox.vue web-nuxt/components/PhotoGallery.vue web-nuxt/components/PostCard.vue web-nuxt/pages/admin/entities.vue web-nuxt/pages/admin/media.vue web-nuxt/pages/bai-viet/[id].vue web-nuxt/pages/dia-diem/[id].vue web-nuxt/pages/index.vue tests/checks/test_hard_checks.py
git commit -m "refactor: restore launch standards ratchets"
```

Task 9 is blocked until `python scripts/checks/run_hard.py --all` exits 0. Do not defer or baseline-bump residual violations.

## Task 9: Update plan truth and implement Task 45 evidence

**Files:**
- Modify: `docs/superpowers/plans/2026-07-13-launch-safety-gate.md`
- Create: `scripts/ops/record_launch_evidence.py`, `scripts/ops/release_gate_harness.ps1`
- Create: `tests/launch_safety/test_evidence_record.py`, `tests/launch_safety/powershell/test_release_gate_harness.ps1`
- Modify: `tests/launch_safety/test_launch_matrix_contract.py`
- Create: `docs/superpowers/results/2026-07-20-launch-safety-gate-evidence.md`
- Modify: `scripts/release_gate.ps1`, `scripts/launch_safety_browser_e2e.mjs`, `.github/workflows/ci.yml`
- Create: `scripts/ops/run_backend_regression.py`, `tests/launch_safety/test_backend_regression_runner.py`
- Modify: `requirements-dev.txt`
- Reference: `docs/superpowers/specs/2026-07-20-launch-safety-task45-correction-design.md`, `docs/superpowers/specs/2026-07-24-bounded-backend-regression-design.md`

- [x] **Step 1: Correct plan authority before execution**

Update status, current worktree/branch and completed/partial task tracking. Link this remediation plan and the Task 45 correction amendment. Do not mark Docker/PG/build evidence complete when it was skipped.

- [x] **Step 2: Write and run RED contracts**

Test twelve required sections, external gates `{H1: blocked, H2: blocked, owner: not-authorized}`, idempotent temp-state upsert, final-pass requirements, primary/cleanup/recorder precedence, explicit Docker/browser opt-in, environment restoration, one `System.Int32`, and `--probe-browser` parity.

```powershell
python -m pytest tests/launch_safety/test_evidence_record.py tests/launch_safety/test_launch_matrix_contract.py -q
$powershell = (Get-Command pwsh,powershell -ErrorAction Stop | Select-Object -First 1).Source
& $powershell -NoProfile -File tests/launch_safety/powershell/test_release_gate_harness.ps1
if ($LASTEXITCODE -eq 0) { throw 'PowerShell RED contract unexpectedly passed' }
```

- [x] **Step 3: Implement recorder, harness and browser probe**

Use temp JSON state, canonical final rendering, test-owned Nginx Compose, disposable PostgreSQL port 55432, and a real local Nuxt preview for browser smoke. Default invocation starts no Docker/browser resources.


- [x] **Step 4: Run focused GREEN**

```powershell
python -m pytest tests/launch_safety/test_evidence_record.py tests/launch_safety/test_launch_matrix_contract.py -q
$powershell = (Get-Command pwsh,powershell -ErrorAction Stop | Select-Object -First 1).Source
& $powershell -NoProfile -File tests/launch_safety/powershell/test_release_gate_harness.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

- [x] **Step 5: Commit clean Commit A**

```powershell
git add docs/superpowers/plans/2026-07-13-launch-safety-gate.md scripts/ops/record_launch_evidence.py scripts/ops/release_gate_harness.ps1 scripts/release_gate.ps1 scripts/launch_safety_browser_e2e.mjs .github/workflows/ci.yml tests/launch_safety/test_evidence_record.py tests/launch_safety/powershell/test_release_gate_harness.ps1 tests/launch_safety/test_launch_matrix_contract.py
git commit -m "test: add launch safety evidence gate"
```

- [x] **Step 6: Run the final matrix phase-sequentially from clean current HEAD**

The 2026-07-24 matrix reached the external two-hour bound during the old monolithic backend command and produced only partial diagnostic state; this is not final evidence. From a clean current HEAD, bind the matrix state to the current full revision. Run backend focused tests, then the bounded backend runner `python scripts/ops/run_backend_regression.py --deadline-seconds 7000` (Phase A serial with only `tests/launch_safety/test_closed_installer.py` in Phase B using exactly two xdist workers), followed by frontend focused/full serial tests, typecheck, build, `run_hard.py --all`, PowerShell contract, rollback local rehearsal and explicit opt-ins. Use an outer execution timeout greater than 7,000 seconds. Record exact prerequisite skips. Do not render final evidence if any required functional section fails.

- [x] **Step 7: Render and commit evidence B**

```powershell
python scripts/ops/record_launch_evidence.py render --final
git add docs/superpowers/results/2026-07-20-launch-safety-gate-evidence.md
git commit -m "test: record launch safety gate evidence"
```

Recorded completion: the matrix state was bound to the full candidate revision above, validated with the exact required-section and gate rules, and rendered to Evidence B commit `580b9b8`.

## Final completion gate

- [x] Spec-compliance review for each lane; fix and re-review all Important/Critical findings.
- [x] Code-quality review after spec compliance.
- [x] Fresh focused tests, `git diff --check`, `run_hard.py --all`, bounded backend regression via `python scripts/ops/run_backend_regression.py --deadline-seconds 7000`, Nuxt typecheck/build, and available Docker/PG/browser opt-ins.
- [x] No push, deploy, secret change, production-data mutation, or live indexing enablement.
