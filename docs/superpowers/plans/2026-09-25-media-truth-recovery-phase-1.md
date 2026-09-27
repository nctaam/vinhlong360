# Media Truth Recovery Phase 1 Implementation Plan

> STATUS: ready for owner implementation-plan review; no protected-data mutation is authorized.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the `prov-1` ghost safely, correct all Batch 21 media classifications, add fail-closed rights-cleared media descriptors, and produce a reviewed candidate plus catalog inventory without touching protected stores before a separate apply approval.

**Architecture:** Extend the existing canonical disclosure/descriptor boundary so media class comes from validated entity attributes rather than file paths. Freeze the 40-record Batch 21 truth set in an immutable manifest, generate exact cross-store mutations and candidates on copies, then harden the existing reconciliation apply engine with target-scoped verification and atomic capture/no-overwrite JSON publication. The implementation stops at a destructive apply gate; live data, tracked asset deletion, and baseline changes happen only after explicit owner approval.

**Tech Stack:** Python 3.14, FastAPI/Pydantic, SQLite, TypeScript, Nuxt 4/Vue 3, Vitest, pytest, Ruff, Git.

**Spec:** `docs/superpowers/specs/2026-09-25-media-truth-recovery-design.md`

## Global Constraints

- Protected SQLite SHA-256 before the apply gate: `ea83864990cf8455061b2436f072c097bc7011f56428c5ba3ba43bcd66fb78a4`.
- Protected JSON SHA-256 before the apply gate: `8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f`.
- Never mutate `agent/data/vinhlong360.db`, `web/data.json`, or SQLite sidecars before the explicit Task 12 apply gate.
- Never use current JSON as a whole-file replacement for SQLite or current SQLite as a whole-file replacement for JSON.
- Batch 21 truth is exactly 40 records: delete `prov-1`; retain 37 generated placeholders and two AI assets (`tep-rang-dua`, `cua-com-duyen-hai`).
- The six JSON relationships outgoing from `prov-1` are the only relationship deletions in this phase; SQLite currently has zero matching rows.
- `generated-placeholder` and `ai-generated` always use `is_verified_photo=false`.
- `documentary`, `journalistic`, `official`, and `press` descriptors require author, source, image-specific public URL, affirmative license/re-host scope, and explicit permission evidence.
- A credit line or copyright statement alone is never permission evidence.
- Mutable timestamps never grant legacy eligibility; legacy exemptions may shrink but must not expand.
- Unknown provenance fails closed to an explicit placeholder and is never inferred from `/img/entities/{id}.webp`.
- Implementation and proposal generation must leave protected hashes, mtimes, and sidecar absence unchanged.
- No push, publication, or live apply is implied by code/spec/plan approval.
- Each implementation task uses TDD, commits only its intended files, receives an independent task review, and leaves no open Critical or Important finding before the next task.

## Per-Task Review Gate

After each task commit, create a review package in the plan workspace using these Windows-native commands with `$base` set to the commit recorded before dispatch and `$head` set to the task HEAD:

```powershell
$review = ".superpowers/sdd/2026-09-25-media-truth-recovery-phase-1/task-review-$taskNumber-$head.txt"
git log --oneline "$base..$head" | Set-Content $review
git diff --stat "$base..$head" | Add-Content $review
git diff -U10 "$base..$head" | Add-Content $review
```

Dispatch the independent task reviewer with the task brief, implementer report, this review package, and Global Constraints, then record both spec-compliance and code-quality verdicts in the SDD ledger. The next task cannot start while a Critical/Important finding is open; every fix round requires a scoped re-review and a ledger entry. A clean reviewer verdict is a required acceptance step, not an optional postscript.

## File and Responsibility Map

- `agent/media_provenance.py`: canonical public-URL, license, permission, and sourced-photo evidence validation used by runtime and checks.
- `agent/media_policy.py`: allowed descriptor triples and stored media-class invariants.
- `agent/media_truth_manifest.py`: strict loader for the reviewed Batch 21 delete/AI/placeholder partition.
- `config/ai-disclosure.json`: canonical disclosure copy; filename remains stable while schema gains sourced-photo copy.
- `agent/ai_disclosure.py`, `web-nuxt/utils/aiDisclosure.ts`: strict Python/TypeScript artifact loaders.
- `agent/image_descriptor.py`, `agent/api_schemas.py`, `agent/entity_read.py`: backend media-aware descriptor production and API validation.
- `web-nuxt/types/image.ts`, `web-nuxt/utils/imageDescriptors.ts`, `web-nuxt/components/ImageDisclosure.vue`: frontend descriptor union, normalization, rendering, and linked credit.
- `docs/standards/batch-21-media-truth.json`: immutable Phase 1 truth set and actions.
- `docs/standards/r10.6-legacy-image-revocations.txt`: exact IDs that can no longer use legacy documentary compatibility.
- `scripts/ops/generate_batch_21.py`, `outputs/batch_culinary_restaurants_photos.json`: corrected, deterministic Batch 21 ledger.
- `scripts/checks/apply_data_reconciliation.py`, `scripts/checks/reconciliation_journal.py`: mutation semantics, target verification, atomic publication, and recovery.
- `scripts/checks/build_media_truth_plan.py`: deterministic, non-authorizing Phase 1 mutation proposal.
- `scripts/checks/stage_data_reconciliation.py`: apply a review plan only to explicit fixture/candidate copies.
- `scripts/checks/build_media_truth_inventory.py`: one-row-per-entity Phase 2 inventory from the staged candidate.
- `scripts/generate_llms_txt.py`, `scripts/export_fe_data.py`: parameterized, truth-aware public artifact generation.
- `docs/runbooks/media-truth-apply.md`: exact review, approval, apply, recovery, and verification procedure.

---

### Task 1: Canonical Media Provenance and Disclosure Contract

**Files:**
- Create: `agent/media_provenance.py`
- Modify: `scripts/checks/provenance_url_policy.py`
- Modify: `scripts/checks/provenance_evidence_policy.py`
- Modify: `config/ai-disclosure.json`
- Modify: `agent/ai_disclosure.py`
- Modify: `agent/media_policy.py`
- Modify: `agent/api_schemas.py`
- Modify: `web-nuxt/utils/aiDisclosure.ts`
- Modify: `web-nuxt/types/image.ts`
- Modify: `tests/fixtures/ai-disclosure-validator-corpus.json`
- Create: `tests/fixtures/media-provenance-validator-corpus.json`
- Test: `agent/tests/test_media_provenance.py`
- Test: `agent/tests/test_ai_disclosure.py`
- Test: `agent/tests/test_media_policy.py`
- Test: `web-nuxt/tests/ai-disclosure.test.ts`
- Test: `tests/launch_safety/test_ai_disclosure_artifact.py`
- Test: `tests/launch_safety/test_release_package.py`

**Interfaces:**
- Produces: `SourcedPhotoEvidence`, `sourced_photo_evidence(attributes: object) -> SourcedPhotoEvidence | None`, `is_public_provenance_url(value: object, *, require_path: bool = True) -> bool`, and `select_affirmative_license_scope(values: Iterable[object]) -> str | None`.
- Produces descriptor triple: `("rights-cleared", image_type, "entity-sourced-photo")` where `image_type` is one of `documentary`, `journalistic`, `official`, or `press`.
- Produces disclosure revision `media-disclosure-v2` in the existing `config/ai-disclosure.json` filename.
- Produces `ImageDescriptor.source_url: string | null` in both Python API validation and TypeScript types.
- Produces a shared cross-language provenance corpus covering valid press, missing field, denial override, placeholder/private URL, self-backdated legacy bypass, AI, and generated-placeholder cases.

- [ ] **Step 1: Write failing Python evidence-policy tests**

```python
def test_sourced_photo_evidence_requires_the_complete_rights_bundle():
    attrs = {
        "image_type": "press",
        "is_verified_photo": True,
        "image_author": "Tran Phuoc",
        "image_source": "Bao Vinh Long",
        "image_source_url": "https://baovinhlong.com.vn/images/photo.webp",
        "image_license": "Permission granted for re-hosting",
        "permission_evidence": "owner-record:IMG-2026-001",
    }

    evidence = sourced_photo_evidence(attrs)

    assert evidence == SourcedPhotoEvidence(
        image_type="press",
        author="Tran Phuoc",
        source="Bao Vinh Long",
        source_url="https://baovinhlong.com.vn/images/photo.webp",
        license_scope="Permission granted for re-hosting",
        permission_evidence="owner-record:IMG-2026-001",
        credit="Tran Phuoc · Bao Vinh Long",
    )


@pytest.mark.parametrize("missing", [
    "image_author", "image_source", "image_source_url",
    "image_license", "permission_evidence",
])
def test_sourced_photo_evidence_fails_closed_when_a_requirement_is_missing(missing):
    attrs = valid_press_attributes()
    attrs.pop(missing)
    assert sourced_photo_evidence(attrs) is None
```

- [ ] **Step 2: Run the focused Python tests and verify RED**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q agent/tests/test_media_provenance.py agent/tests/test_ai_disclosure.py agent/tests/test_media_policy.py`

Expected: FAIL because `agent.media_provenance`, `SourcedPhotoEvidence`, and `entity-sourced-photo` do not exist.

- [ ] **Step 3: Move the shared validators and implement the evidence bundle**

Move the current URL and license logic from `scripts/checks/provenance_url_policy.py` and `scripts/checks/provenance_evidence_policy.py` into `agent/media_provenance.py`; keep both script files as import-compatible shims so existing CLI imports continue to work.

```python
DOCUMENTARY_IMAGE_TYPES = frozenset({
    "documentary", "journalistic", "official", "press",
})


@dataclass(frozen=True)
class SourcedPhotoEvidence:
    image_type: str
    author: str
    source: str
    source_url: str
    license_scope: str
    permission_evidence: str
    credit: str


def sourced_photo_evidence(attributes: object) -> SourcedPhotoEvidence | None:
    if not isinstance(attributes, Mapping):
        return None
    image_type = (_clean_text(attributes.get("image_type")) or "").lower()
    author = _clean_text(attributes.get("image_author"))
    source = _clean_text(attributes.get("image_source"))
    source_url = _clean_text(attributes.get("image_source_url"))
    permission = _clean_text(attributes.get("permission_evidence"))
    license_scope = select_affirmative_license_scope(
        [attributes.get("image_license"), attributes.get("license_scope")]
    )
    if (
        image_type not in DOCUMENTARY_IMAGE_TYPES
        or attributes.get("is_verified_photo") is not True
        or not author
        or not source
        or not source_url
        or not is_public_provenance_url(source_url)
        or not license_scope
        or not permission
    ):
        return None
    return SourcedPhotoEvidence(
        image_type=image_type,
        author=author,
        source=source,
        source_url=source_url,
        license_scope=license_scope,
        permission_evidence=permission,
        credit=f"{author} · {source}",
    )
```

- [ ] **Step 4: Extend the canonical disclosure artifact and strict loaders**

Set `schema_version` to `2`, revision to `media-disclosure-v2`, and add this exact root member:

```json
"sourced_photo": {
  "short_label": "Ảnh có nguồn",
  "full_disclosure": "Ảnh tư liệu có nguồn và căn cứ sử dụng — xem tác giả, cơ quan nguồn và liên kết gốc.",
  "accessible_description_key": "entity-sourced-photo-full"
}
```

Add `CANONICAL_SOURCED_PHOTO` and strict root-key/copy validation in Python and TypeScript. Keep `load_ai_disclosure` and `aiDisclosure` as compatibility aliases for this phase, but expose new canonical names `load_media_disclosure` and `mediaDisclosure` for new code.

Create `tests/fixtures/media-provenance-validator-corpus.json` with exact-key rows shaped as `{name, attributes, accepted, expected_reason}`. The required rows are `valid-press`, `missing-author`, `missing-source-url`, `reserved-source-url`, `license-denial`, `missing-permission`, `self-backdated-uninventoried`, `valid-ai`, and `valid-placeholder`. Python tests consume every row in Task 1; TypeScript consumes the same rows in Task 3.

- [ ] **Step 5: Extend descriptor source types and exact API combinations**

```python
ENTITY_RIGHTS_CLEARED_SOURCES = frozenset(
    ("rights-cleared", image_type, "entity-sourced-photo")
    for image_type in DOCUMENTARY_IMAGE_TYPES
)
```

Add `source_url` to `GalleryImageDescriptor`. Require non-null `credit` and `source_url` only for `rights-cleared`; require `source_url=None` for AI, placeholder, and UGC descriptors. Update exact-key and release-artifact tests instead of weakening strict validation.
The stored-class validator requires literal `is_verified_photo is False` for `generated-placeholder` and `ai-generated`; absent, null, or true values are invalid and must fail closed. Rights-cleared classes require literal `is_verified_photo is True` plus the complete evidence bundle.

- [ ] **Step 6: Run Python, TypeScript, and release-artifact tests**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q agent/tests/test_media_provenance.py agent/tests/test_ai_disclosure.py agent/tests/test_media_policy.py agent/tests/test_image_descriptor.py tests/launch_safety/test_ai_disclosure_artifact.py tests/launch_safety/test_release_package.py`

Run: `npm --prefix web-nuxt exec vitest run tests/ai-disclosure.test.ts`

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add config/ai-disclosure.json agent/media_provenance.py agent/ai_disclosure.py agent/media_policy.py agent/api_schemas.py scripts/checks/provenance_url_policy.py scripts/checks/provenance_evidence_policy.py web-nuxt/utils/aiDisclosure.ts web-nuxt/types/image.ts tests/fixtures/ai-disclosure-validator-corpus.json tests/fixtures/media-provenance-validator-corpus.json agent/tests/test_media_provenance.py agent/tests/test_ai_disclosure.py agent/tests/test_media_policy.py web-nuxt/tests/ai-disclosure.test.ts tests/launch_safety/test_ai_disclosure_artifact.py tests/launch_safety/test_release_package.py
git commit -m "feat(media): add rights-cleared provenance contract"
```

### Task 2: Python Media-Aware Entity Descriptors

**Files:**
- Modify: `agent/image_descriptor.py`
- Modify: `agent/entity_read.py`
- Modify: `agent/public_api.py`
- Modify: `agent/api_schemas.py`
- Test: `agent/tests/test_image_descriptor.py`
- Test: `agent/tests/test_image_metadata_disclosure.py`

**Interfaces:**
- Consumes: `sourced_photo_evidence`, `DOCUMENTARY_IMAGE_TYPES`, and disclosure copy from Task 1.
- Produces: unchanged public function `describe_entity_images(entity: object, *, disclosure: object) -> tuple[ImageDescriptor, ...]` with media-aware behavior.
- Produces: `ImageDescriptor.source_url: str | None`.
- Rule: raw local paths without a supported `attributes.image_type` produce no descriptor; callers use the existing explicit placeholder fallback.

- [ ] **Step 1: Add failing descriptor tests**

```python
def test_describe_entity_images_builds_a_rights_cleared_descriptor():
    entity = {
        "name": "Dinh Long Ho",
        "images": ["/img/entities/dinh-long-ho.webp"],
        "attributes": valid_press_attributes(),
    }

    descriptor = describe_entity_images(entity, disclosure=DISCLOSURE)[0]

    assert descriptor.source_class == "rights-cleared"
    assert descriptor.source_kind == "press"
    assert descriptor.disclosure_key == "entity-sourced-photo"
    assert descriptor.credit == "Tran Phuoc · Bao Vinh Long"
    assert descriptor.source_url == "https://baovinhlong.com.vn/images/photo.webp"


def test_unclassified_legacy_path_is_not_inferred_as_ai():
    entity = {"name": "Unknown", "images": ["/img/entities/unknown.webp"]}
    assert describe_entity_images(entity, disclosure=DISCLOSURE) == ()


def test_local_placeholder_asset_remains_renderable_but_unverified():
    entity = {
        "name": "Placeholder",
        "images": ["/img/entities/placeholder.webp"],
        "attributes": {
            "image_type": "generated-placeholder",
            "is_verified_photo": False,
        },
    }
    descriptor = describe_entity_images(entity, disclosure=DISCLOSURE)[0]
    assert (descriptor.source_class, descriptor.url, descriptor.credit) == (
        "placeholder", "/img/entities/placeholder.webp", None,
    )


def test_incomplete_sourced_photo_falls_back_to_explicit_placeholder():
    entity = {
        "name": "Incomplete press record",
        "images": ["/img/entities/incomplete.webp"],
        "attributes": {"image_type": "press", "is_verified_photo": False},
    }
    descriptor = describe_entity_images(entity, disclosure=DISCLOSURE)[0]
    assert descriptor.source_class == "placeholder"
    assert descriptor.source_url is None
    assert descriptor.credit is None
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q agent/tests/test_image_descriptor.py agent/tests/test_image_metadata_disclosure.py`

Expected: FAIL because legacy paths are still always labeled AI and `source_url` is not populated.

- [ ] **Step 3: Implement classification-driven descriptor production**

Keep `describe_entity_images` as the only public entity conversion boundary. Normalize `entity.attributes.image_type` once, then dispatch each valid local image to one of three private builders:

```python
def _entity_media_class(entity: Mapping[str, object]) -> str | None:
    attributes = entity.get("attributes")
    if not isinstance(attributes, Mapping):
        return None
    value = attributes.get("image_type")
    return value.strip().lower() if type(value) is str and value.strip() else None


def describe_entity_images(entity: object, *, disclosure: object) -> tuple[ImageDescriptor, ...]:
    loaded = _require_disclosure(disclosure)
    if not isinstance(entity, Mapping):
        return ()
    supplied = _supplied_entity_descriptors(entity, disclosure=loaded)
    if "image_descriptor" in entity or "image_descriptors" in entity:
        return supplied
    media_class = _entity_media_class(entity)
    if media_class not in {"generated-placeholder", "ai-generated", *DOCUMENTARY_IMAGE_TYPES}:
        return ()
    return _descriptors_for_classified_entity(entity, media_class, loaded)
```

For sourced-photo types, call `sourced_photo_evidence`; when it returns `None`, return the explicit placeholder descriptor for the local asset instead of an empty or inferred AI descriptor. For AI and placeholder types, require the literal `is_verified_photo is False`; missing, null, or true values fail closed to the explicit placeholder path. Set `credit=None` and `source_url=None` for AI and placeholder descriptors.

- [ ] **Step 4: Update API projection and validation**

Ensure `_gallery_editorial_images` serializes `source_url`, keeps only `is_renderable_entity_descriptor` results, and never copies raw provenance fields into the public descriptor. Update `GalleryImageDescriptor` exact invariants and tests.

- [ ] **Step 5: Run focused backend tests**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q agent/tests/test_image_descriptor.py agent/tests/test_image_metadata_disclosure.py agent/tests/test_media_policy.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add agent/image_descriptor.py agent/entity_read.py agent/public_api.py agent/api_schemas.py agent/tests/test_image_descriptor.py agent/tests/test_image_metadata_disclosure.py
git commit -m "feat(media): classify backend entity descriptors honestly"
```

### Task 3: TypeScript Descriptors, Linked Credits, and Renderer Registry

**Files:**
- Modify: `web-nuxt/types/image.ts`
- Modify: `web-nuxt/utils/imageDescriptors.ts`
- Modify: `web-nuxt/utils/savedImageDescriptors.ts`
- Modify: `web-nuxt/components/ImageDisclosure.vue`
- Modify: `web-nuxt/config/entity-image-renderers.json`
- Test: `web-nuxt/tests/ai-disclosure.test.ts`
- Test: `web-nuxt/tests/entity-card-disclosure.test.ts`
- Test: `web-nuxt/tests/entity-image-detail.test.ts`
- Test: `web-nuxt/tests/gallery-disclosure.test.ts`
- Test: `web-nuxt/tests/admin-image-disclosure.test.ts`
- Test: `tests/launch_safety/test_entity_image_renderer_guard.py`

**Interfaces:**
- Consumes: `mediaDisclosure`, `ImageDescriptor.source_url`, and source triples from Tasks 1-2.
- Produces: `describeEntityImages(entity)` with the same classification behavior as Python.
- Produces: visible linked author/source credit for rights-cleared media only.

- [ ] **Step 1: Add failing TypeScript normalization and rendering tests**

```typescript
const press: ImageDescriptor = {
  url: '/img/entities/dinh-long-ho.webp',
  alt: 'Đình Long Hồ — ảnh tư liệu',
  source_class: 'rights-cleared',
  source_kind: 'press',
  disclosure_key: 'entity-sourced-photo',
  short_label: mediaDisclosure.sourced_photo.short_label,
  full_disclosure: mediaDisclosure.sourced_photo.full_disclosure,
  credit: 'Trần Phước · Báo Vĩnh Long',
  source_url: 'https://baovinhlong.com.vn/images/photo.webp',
  width: null,
  height: null,
}

it('renders sourced-photo credit as a safe source link', async () => {
  const wrapper = await mountSuspended(ImageDisclosure, {
    props: { descriptor: press, presentation: 'full' },
  })
  const credit = wrapper.get('a[data-credit]')
  expect(credit.attributes('href')).toBe(press.source_url)
  expect(credit.attributes('rel')).toContain('noopener')
  expect(credit.text()).toBe(press.credit)
})
```

Add a parity test proving raw `/img/entities/*.webp` without `attributes.image_type` returns no image descriptor.
Add tests proving an incomplete sourced-photo record and an AI/placeholder record with missing or null `is_verified_photo` render the explicit placeholder descriptor and never a rights-cleared or verified descriptor.

- [ ] **Step 2: Run focused Vitest and verify RED**

Run: `npm --prefix web-nuxt exec vitest run tests/entity-card-disclosure.test.ts tests/entity-image-detail.test.ts tests/gallery-disclosure.test.ts`

Expected: FAIL because rights-cleared triples and `source_url` are unsupported.

- [ ] **Step 3: Implement media-aware frontend normalization**

Update the exact descriptor key signature to include `source_url`. Permit these combinations:

```typescript
const ALLOWED_SOURCE_COMBINATIONS = new Set([
  'ai-generated|entity-editorial|entity-ai',
  'placeholder|generated-placeholder|entity-placeholder',
  'rights-cleared|documentary|entity-sourced-photo',
  'rights-cleared|journalistic|entity-sourced-photo',
  'rights-cleared|official|entity-sourced-photo',
  'rights-cleared|press|entity-sourced-photo',
  'user-uploaded|review-ugc|ugc-photo',
  'user-uploaded|post-ugc|ugc-photo',
])
```

Derive legacy entity descriptors from `entity.attributes.image_type`; do not infer AI from the URL. Use the same full-evidence requirements as the backend before constructing a rights-cleared descriptor. AI and placeholder descriptors require `is_verified_photo === false` and have `source_url: null`; missing, null, or true values return the explicit placeholder descriptor.

- [ ] **Step 4: Render credit and source safely**

```vue
<a
  v-if="descriptor.credit && descriptor.source_url"
  class="image-disclosure-credit"
  data-credit
  :href="descriptor.source_url"
  target="_blank"
  rel="noopener noreferrer"
>{{ descriptor.credit }}</a>
<span v-else-if="descriptor.credit" class="image-disclosure-credit" data-credit>
  {{ descriptor.credit }}
</span>
```

Keep the full disclosure associated through `aria-describedby`. Update saved/recent snapshot normalization so `source_url` survives serialization.

- [ ] **Step 5: Register rights-cleared rendering wherever entity AI rendering is registered**

For every `entity-image-renderers.json` entry with `source_class: "ai-generated"` and an entity-media producer, add the equivalent `rights-cleared` entry with the same surface, presentation, accessibility, and test file. Do not add rights-cleared rendering to UGC surfaces.

- [ ] **Step 6: Run frontend and renderer-guard tests**

Run: `npm --prefix web-nuxt exec vitest run tests/ai-disclosure.test.ts tests/entity-card-disclosure.test.ts tests/entity-image-detail.test.ts tests/gallery-disclosure.test.ts tests/admin-image-disclosure.test.ts`

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/launch_safety/test_entity_image_renderer_guard.py`

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add web-nuxt/types/image.ts web-nuxt/utils/imageDescriptors.ts web-nuxt/utils/savedImageDescriptors.ts web-nuxt/components/ImageDisclosure.vue web-nuxt/config/entity-image-renderers.json web-nuxt/tests/ai-disclosure.test.ts web-nuxt/tests/entity-card-disclosure.test.ts web-nuxt/tests/entity-image-detail.test.ts web-nuxt/tests/gallery-disclosure.test.ts web-nuxt/tests/admin-image-disclosure.test.ts tests/launch_safety/test_entity_image_renderer_guard.py
git commit -m "feat(media): render rights-cleared entity credits"
```

### Task 4: Freeze Batch 21 Truth and Revoke False Legacy Compatibility

**Files:**
- Create: `docs/standards/batch-21-media-truth.json`
- Create: `docs/standards/r10.6-legacy-image-revocations.txt`
- Create: `agent/media_truth_manifest.py`
- Modify: `scripts/ops/generate_batch_21.py`
- Modify: `outputs/batch_culinary_restaurants_photos.json`
- Modify: `scripts/checks/check_banned_claims.py`
- Modify: `tests/checks/test_r10_6_legacy_inventory.py`
- Test: `tests/ops/test_generate_batch_21.py`
- Test: `agent/tests/test_media_truth_manifest.py`
- Test: `tests/checks/test_hard_checks.py`

**Interfaces:**
- Produces: immutable manifest schema `batch-21-media-truth-v1`.
- Produces: `load_batch_21_truth(root: Path | None = None) -> Batch21Truth` and `reviewed_removal_ids(root: Path) -> frozenset[str]`.
- Produces: `revoked_legacy_image_ids()` used by R10.6 as a subtractive deny-set.
- Produces corrected 39-row ledger with no unsupported press metadata.

- [ ] **Step 1: Write failing manifest and generator tests**

```python
def test_batch_21_truth_partition_is_exact_and_complete():
    manifest = load_batch_21_truth()
    all_ids = set(manifest.delete)
    all_ids.update(manifest.ai_generated)
    all_ids.update(manifest.generated_placeholder)
    assert len(all_ids) == 40
    assert manifest.delete == ("prov-1",)
    assert manifest.ai_generated == ("cua-com-duyen-hai", "tep-rang-dua")
    assert len(manifest.generated_placeholder) == 37


def test_generated_ledger_contains_only_truthful_media_fields():
    rows = build_batch_21_ledger()
    assert len(rows) == 39
    assert {row["entity_id"] for row in rows}.isdisjoint({"prov-1"})
    assert sum(row["image_type"] == "generated-placeholder" for row in rows) == 37
    assert sum(row["image_type"] == "ai-generated" for row in rows) == 2
    assert all(row["is_verified_photo"] is False for row in rows)
    assert all("author" not in row and "license" not in row for row in rows)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q agent/tests/test_media_truth_manifest.py tests/ops/test_generate_batch_21.py tests/checks/test_r10_6_legacy_inventory.py tests/checks/test_hard_checks.py`

Expected: FAIL because the truth/revocation manifests do not exist and the ledger still contains 40 false documentary rows.

- [ ] **Step 3: Create the exact Batch 21 truth manifest**

Use these exact partitions:

```json
{
  "schemaVersion": 1,
  "revision": "batch-21-media-truth-v1",
  "sourceLedgerCommit": "68d59f0f",
  "aiEvidenceCommit": "30a3fae9",
  "delete": ["prov-1"],
  "ai_generated": ["cua-com-duyen-hai", "tep-rang-dua"],
  "generated_placeholder": [
    "ba-nhi-bun-bo-hue-vinh-long-vinh-long",
    "banh-canh-ben-tre",
    "banh-trang-my-long",
    "banh-xeo-mien-tay",
    "bo-nuong-la-lot",
    "bun-bo-co-tam-cho-ben-tre-ben-tre",
    "bun-mam-mien-tay",
    "ca-tai-tuong-chien-xu",
    "caffe-takeaway---tan-ke",
    "cha-gio-chay",
    "chao-ca-loc-rau-dang",
    "chuoi-nuong-gia-truyen",
    "co-dai---sinh-to-giai-khat",
    "com-chay-au-lac-vinh-long",
    "com-ga-xoi-mo-5-vi-ben-tre",
    "duong-dua",
    "goi-cuon-tom-thit",
    "hot-pot-72---quan-lau",
    "khoi---lau-nuong",
    "kimchi-kimchi---mi-cay-han-quoc",
    "lau-bo",
    "lau-mam-ben-tre",
    "lau-tai-co",
    "lu-lu---cake-drink",
    "ma-van-tai-quan---pham-thai-buong",
    "mam-tom-cha-vinh-long",
    "mi-cay-vinh-long",
    "nem-nuong-thanh-binh-ben-tre",
    "nha-hang-thien-tan",
    "tinh-binh-chay-vinh-long",
    "tiem-ba-khoang",
    "tom-cang-xanh-nuong",
    "tom-cang-xanh-song-tien",
    "tom-rang-muoi-ot",
    "vys-house-drinks-tea---2-thang-9",
    "xoi-vi-mien-tay",
    "xom-nuong-que-nha"
  ]
}
```

The file must be LF-only, sorted within each classification, unique, and exact-key validated.

Implement `agent/media_truth_manifest.py` as the only runtime loader. `Batch21Truth` is a frozen dataclass with tuple fields `delete`, `ai_generated`, and `generated_placeholder`; `load_batch_21_truth` validates exact keys, revision, disjoint partitions, 40 total IDs, 1/2/37 counts, and sorted uniqueness before returning it. Scripts import this loader instead of parsing the JSON independently.

- [ ] **Step 4: Generate the revocation inventory and corrected ledger**

Write all 40 manifest IDs, sorted and unique, to `r10.6-legacy-image-revocations.txt` with headers tying it to `batch-21-media-truth-v1`. Update R10.6 eligibility to compute `legacy_ids - revoked_ids`; never delete or rewrite the immutable snapshot inventories.

Change `generate_batch_21.py` so it reads the truth manifest and emits:

```python
{
    "entity_id": entity_id,
    "image": f"web-nuxt/public/img/entities/{entity_id}.webp",
    "image_type": media_class,
    "is_verified_photo": False,
    **({
        "image_generation_model": "cx/gpt-5.5-image",
        "image_generation_reference": "git:30a3fae9",
    } if media_class == "ai-generated" else {}),
}
```

- [ ] **Step 5: Run focused checks and deterministic regeneration**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q agent/tests/test_media_truth_manifest.py tests/ops/test_generate_batch_21.py tests/checks/test_r10_6_legacy_inventory.py tests/checks/test_hard_checks.py`

Run twice: `python scripts/ops/generate_batch_21.py`

Expected: PASS; the second run leaves `outputs/batch_culinary_restaurants_photos.json` byte-identical.

- [ ] **Step 6: Commit**

```powershell
git add docs/standards/batch-21-media-truth.json docs/standards/r10.6-legacy-image-revocations.txt agent/media_truth_manifest.py agent/tests/test_media_truth_manifest.py scripts/ops/generate_batch_21.py outputs/batch_culinary_restaurants_photos.json scripts/checks/check_banned_claims.py tests/ops/test_generate_batch_21.py tests/checks/test_r10_6_legacy_inventory.py tests/checks/test_hard_checks.py
git commit -m "fix(media): correct batch 21 provenance ledger"
```

### Task 5: Entity Mutation Semantics and Target-Scoped Verification

**Files:**
- Modify: `scripts/checks/apply_data_reconciliation.py`
- Modify: `scripts/checks/reconciliation_journal.py`
- Test: `tests/checks/test_apply_data_reconciliation.py`
- Test: `tests/checks/test_reconciliation_journal.py`

**Interfaces:**
- Produces SQLite/JSON entity operations: `update`, `remove`, and `delete` with exact before-value checks.
- Produces `verify_plan_result(plan, sqlite_path, json_path, connection=None) -> dict[str, Any]`.
- Supports existing `global-parity-v1` plans unchanged.
- Adds `targeted-media-v1`, which verifies affected projections and per-store unrelated digests without pretending unrelated store drift is fixed.

- [ ] **Step 1: Add failing fixture tests for entity deletion and nested field removal**

```python
def test_entity_delete_and_attribute_remove_apply_to_both_fixture_stores(tmp_path):
    db, data, db_backup, data_backup = media_fixture(tmp_path)
    plan = approved_targeted_media_plan(db, data, mutations=[
        entity_delete("sqlite", "prov-1"),
        entity_delete("json", "prov-1", index=1),
        entity_remove("sqlite", "kept-1", "attributes.image_author", "Fake"),
        entity_remove("json", "kept-1", "attributes.image_author", "Fake", index=0),
    ])

    result = apply_plan(
        plan, db, data, db_backup, data_backup,
        confirm=True,
        plan_sha256=canonical_plan_sha256(plan),
    )

    assert result["verification"]["status"] == "clean"
    assert sqlite_entity_ids(db) == {"kept-1"}
    assert json_entity_ids(data) == {"kept-1"}
    assert "image_author" not in json_entity(data, "kept-1")["attributes"]
```

- [ ] **Step 2: Add a failing test that preserves unrelated global drift**

```python
def test_targeted_media_verification_does_not_claim_global_parity(tmp_path):
    db, data, db_backup, data_backup = divergent_media_fixture(tmp_path)
    plan = approved_targeted_media_plan(db, data)

    result = apply_plan(
        plan, db, data, db_backup, data_backup,
        confirm=True,
        plan_sha256=canonical_plan_sha256(plan),
    )

    assert result["verification"] == {
        "mode": "targeted-media-v1",
        "status": "clean",
        "globalParity": "known-drift-preserved",
    }
```

- [ ] **Step 3: Run focused tests and verify RED**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py`

Expected: FAIL because entity delete/remove and targeted verification are unsupported.

- [ ] **Step 4: Implement exact entity mutation helpers**

Add these explicit dispatch rules:

```python
def _sqlite_mutation(conn: sqlite3.Connection, mutation: dict[str, Any]) -> None:
    if mutation.get("recordType") == "relationship":
        _relationship_mutation(conn, mutation)
        return
    if mutation.get("recordType") != "entity":
        raise ApplyError(f"unsupported mutation record type: {mutation.get('recordType')}")
    if mutation.get("operation") == "delete":
        _delete_sqlite_entity(conn, mutation)
        return
    if mutation.get("operation") in {"update", "remove"}:
        _update_sqlite_entity(conn, mutation)
        return
    raise ApplyError(f"unsupported entity mutation: {mutation.get('mutationId')}")
```

`remove` must assert the current nested attribute value equals `before`, then remove the key. `delete` must compare a canonical before projection before deleting exactly one row. Implement equivalent JSON entity operations using the exact manifest index and ID; sort deletes descending within each record type.

- [ ] **Step 5: Add plan-declared verification dispatch**

```python
def verify_plan_result(plan, sqlite_path, json_path, connection=None):
    mode = ((plan.get("verification") or {}).get("mode"))
    if mode in {None, "global-parity-v1"}:
        return {"mode": "global-parity-v1", **_parity(sqlite_path, json_path, connection)}
    if mode == "targeted-media-v1":
        return _targeted_media_verification(plan, sqlite_path, json_path, connection)
    raise ApplyError(f"unsupported verification mode: {mode}")
```

`_targeted_media_verification` must verify:

- exact expected canonical projections for every target ID in both stores;
- `prov-1` absence;
- no relationship endpoint references to `prov-1`;
- before/after per-store digests for all non-target entity rows and non-target relationships; and
- an explicit `globalParity: "known-drift-preserved"` result rather than `clean` global parity.

- [ ] **Step 6: Run focused apply and journal tests**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py`

Expected: PASS, including all existing global-parity fixtures.

- [ ] **Step 7: Commit**

```powershell
git add scripts/checks/apply_data_reconciliation.py scripts/checks/reconciliation_journal.py tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py
git commit -m "feat(data): support targeted media reconciliation"
```

### Task 6: Atomic Capture, No-Overwrite JSON Publication, and Safe Recovery

**Files:**
- Modify: `scripts/checks/apply_data_reconciliation.py`
- Modify: `scripts/checks/reconciliation_journal.py`
- Test: `tests/checks/test_apply_data_reconciliation.py`
- Test: `tests/checks/test_reconciliation_journal.py`

**Interfaces:**
- Produces: `_capture_json_target`, `_publish_json_no_overwrite`, and `_restore_captured_json`.
- Journal schema records `capturedPath`, `capturedSha256`, `publishedIdentity`, and `publishedSha256`.
- Removes the check-then-`os.replace` publication path.

- [ ] **Step 1: Add failing race-window tests**

Add one test for each named boundary:

```python
@pytest.mark.parametrize("hook", [
    "before_capture",
    "after_capture",
    "before_publish",
    "after_publish",
    "before_rollback_capture",
])
def test_json_publication_never_overwrites_a_concurrent_writer(tmp_path, monkeypatch, hook):
    harness = race_harness(tmp_path, hook=hook, foreign_bytes=b'{"foreign":true}\n')
    with pytest.raises(ApplyError):
        harness.apply()
    assert harness.foreign_bytes_are_preserved_or_captured()
    assert harness.journal_is_recoverable()
```

Add a Windows-compatible test proving publication refuses an already recreated target and a late sidecar test after the final journal write.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py`

Expected: FAIL because `_publish_json` still uses check-then-`os.replace`.

- [ ] **Step 3: Stage candidate JSON in the target directory**

Create the staged JSON under `json_path.parent`, not the journal directory, so the no-overwrite hard-link publication is guaranteed to remain on one filesystem volume.

- [ ] **Step 4: Implement atomic capture and no-overwrite publish**

```python
def _capture_json_target(json_path: Path, captured_path: Path) -> None:
    if captured_path.exists():
        raise ApplyError(f"captured JSON path already exists: {captured_path}")
    os.replace(json_path, captured_path)


def _publish_json_no_overwrite(staged_path: Path, json_path: Path) -> None:
    try:
        os.link(staged_path, json_path)
    except FileExistsError as exc:
        raise ApplyError("JSON target appeared concurrently") from exc
```

After capture, verify the bytes actually moved to `captured_path` against the approved input hash and identity. If they differ, restore by no-overwrite link/rename only when the target is absent; never overwrite a target recreated by another writer.

- [ ] **Step 5: Implement rollback by capturing the current target first**

Rollback must atomically move the current target to a unique observed path, verify that observed bytes equal the journaled published candidate, then restore the original capture. If the observed bytes differ, preserve them and fail closed with all paths recorded in the journal.

- [ ] **Step 6: Recheck candidate, original capture, and SQLite sidecars at the final boundary**

The final success path must revalidate:

- JSON target hash and identity;
- captured original hash;
- SQLite logical target verification;
- absence of `-wal`, `-shm`, and `-journal`; and
- journal/candidate path ownership.

- [ ] **Step 7: Run race, recovery, and full apply tests**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py`

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add scripts/checks/apply_data_reconciliation.py scripts/checks/reconciliation_journal.py tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py
git commit -m "fix(data): close reconciliation publication races"
```

### Task 7: Deterministic Media Truth Plan and Candidate Staging

**Files:**
- Create: `scripts/checks/build_media_truth_plan.py`
- Create: `scripts/checks/stage_data_reconciliation.py`
- Create: `tests/checks/test_build_media_truth_plan.py`
- Create: `tests/checks/test_stage_data_reconciliation.py`
- Create: `outputs/media-truth-plan-2026-09-25.json`
- Modify: `scripts/check_entity_write_paths.py`
- Modify: `tests/test_entity_write_guard.py`

**Interfaces:**
- Produces: `build_plan(root: Path, sqlite_path: Path, json_path: Path, truth_path: Path) -> dict[str, Any]`.
- Produces: `sqlite_logical_digest(sqlite_path: Path) -> str` for deterministic source/candidate/backup identity.
- Produces: `stage_plan(plan, sqlite_input, json_input, asset_root, output_dir) -> StageResult` that refuses protected output paths and stages the reviewed asset set under `output_dir/candidate/public/img/entities`.
- Output plan status is `review_required`, `mutationAllowed=false`, and verification mode `targeted-media-v1`.

- [ ] **Step 1: Add failing plan-shape and scope tests**

```python
def test_plan_has_exact_phase_1_scope(repo_fixture):
    plan = build_plan(
        repo_fixture.root,
        repo_fixture.sqlite,
        repo_fixture.json,
        repo_fixture.truth_manifest,
    )

    assert plan["status"] == "review_required"
    assert plan["mutationAllowed"] is False
    assert plan["verification"]["mode"] == "targeted-media-v1"
    assert plan["summary"] == {
        "batch21Records": 40,
        "deletedEntities": 1,
        "retainedPlaceholders": 37,
        "retainedAi": 2,
        "jsonRelationshipsDeleted": 6,
        "sqliteRelationshipsDeleted": 0,
    }
    assert set(plan["verification"]["entityIds"]) == set(repo_fixture.batch21_ids)
```

Add tests proving the plan leaves `verifiedAt` untouched, removes false press fields with `operation="remove"`, and adds generation fields only to the two AI IDs.

- [ ] **Step 2: Add failing protected-path and determinism tests**

```python
def test_stage_refuses_protected_outputs(repo_fixture, tmp_path):
    plan = build_plan_from_fixture(repo_fixture)
    with pytest.raises(StageError, match="protected"):
        stage_plan(plan, repo_fixture.sqlite, repo_fixture.json, repo_fixture.asset_root, repo_fixture.root)


def test_plan_and_candidate_are_byte_deterministic(repo_fixture, tmp_path):
    first = stage_twice(repo_fixture, repo_fixture.asset_root, tmp_path / "first")
    second = stage_twice(repo_fixture, repo_fixture.asset_root, tmp_path / "second")
    assert first.plan_bytes == second.plan_bytes
    assert first.json_bytes == second.json_bytes
    assert first.logical_sqlite_digest == second.logical_sqlite_digest
```

- [ ] **Step 3: Run tests and verify RED**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/test_entity_write_guard.py`

Expected: FAIL because the builder/stager do not exist.

- [ ] **Step 4: Implement exact mutation generation**

For each store, emit exact before-value mutations:

- delete `prov-1` entity;
- delete six JSON relationships whose `from` is `prov-1`;
- set `image_type=generated-placeholder` and `is_verified_photo=false` for 37 IDs;
- set `image_type=ai-generated`, `is_verified_photo=false`, `image_generation_model="cx/gpt-5.5-image"`, and `image_generation_reference="git:30a3fae9"` for two IDs;
- remove `image_author`, `image_source`, `image_source_url`, `image_license`, `permission_evidence`, `rights_evidence`, `permission`, and the false photographic `image_caption` when present; and
- leave `verifiedAt` and unrelated attributes unchanged.

The builder must fail if counts differ from 40/37/2/6/0, an expected ID is absent, an unexpected relationship references `prov-1`, or an asset hash is missing.

The builder opens SQLite through the repository's immutable read-only helper, refuses any live sidecar, applies the exact mutations to owned temporary copies, and records `expectedOutputs.jsonSha256`, `expectedOutputs.sqliteLogicalDigest`, candidate row counts, and every affected asset SHA-256 in the plan. Physical SQLite file bytes are not used as the deterministic identity; the canonical logical digest is.

- [ ] **Step 5: Implement staging only on owned copies**

Copy both stores into `output_dir`, apply the review plan using shared mutation functions without live flags, and write:

```text
candidate/vinhlong360.db
candidate/data.json
candidate/public/img/entities/{entity_id}.webp
candidate/stage-result.json
```

Copy the complete source `web-nuxt/public/img/entities` tree into the owned candidate asset root, omit only the reviewed `prov-1` asset from the candidate, and record every retained/removed asset SHA-256. `stage-result.json` records exact input hashes, candidate JSON hash, candidate SQLite logical digest, candidate asset-root digest, target verification result, counts, and protected-store after-hashes. No command in this task deletes or overwrites the protected tracked asset.

- [ ] **Step 6: Register only the exact new offline write boundary**

Update `scripts/check_entity_write_paths.py` for the exact staging function and occurrence count. Do not allowlist a directory, wildcard, new mutation kind, or live path.

- [ ] **Step 7: Create and verify the pre-apply review snapshot**

Run:

```powershell
python scripts/backup_data.py --target local --out-dir .tmp/media-truth-backups-phase-1 --label before-media-truth-review --keep 50 --max-age-days 3650
```

Verify the newest backup manifest names both `web/data.json` and `agent/data/vinhlong360.db`. Require the backup JSON byte hash to equal the protected JSON hash; require `PRAGMA integrity_check`, canonical SQLite logical digest, and row counts to equal the protected SQLite source. Record the backup directory, manifest SHA-256, both backup file SHA-256 values, and the SQLite logical digest for Task 11. Do not assume a SQLite backup API copy has the same physical file hash as its source, and do not prune or overwrite this reviewed backup.

- [ ] **Step 8: Generate the checked-in review plan twice**

Run: `python scripts/checks/build_media_truth_plan.py --output outputs/media-truth-plan-2026-09-25.json`

Run the same command again and compare Git status/hash.

Expected: byte-identical output, `status=review_required`, `mutationAllowed=false`, expected candidate digests present, protected hashes and mtimes unchanged, and no SQLite sidecar.

- [ ] **Step 9: Run tests and commit**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/test_entity_write_guard.py`

```powershell
git add scripts/checks/build_media_truth_plan.py scripts/checks/stage_data_reconciliation.py tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py outputs/media-truth-plan-2026-09-25.json scripts/check_entity_write_paths.py tests/test_entity_write_guard.py
git commit -m "feat(data): build media truth reconciliation candidate"
```

### Task 8: Remove Production Coupling to the `prov-1` Ghost

**Files:**
- Modify: `agent/publication_status.py`
- Modify: `agent/tests/test_publication_status.py`
- Modify: `scripts/checks/reconcile_data_dry_run.py`
- Modify: `tests/checks/test_reconcile_data_dry_run.py`
- Modify: `scripts/checks/build_data_review_manifest.py`
- Modify: `tests/checks/test_build_data_review_manifest.py`
- Modify: `scripts/checks/build_image_provenance_review.py`
- Modify: `tests/checks/test_build_image_provenance_review.py`
- Modify: `docs/runbooks/image-provenance-review.md`

**Interfaces:**
- Consumes: `docs/standards/batch-21-media-truth.json` and the Phase 1 review plan.
- Produces: tombstone-aware publication filtering that is safe before and after deletion.
- Produces: general image provenance review CLI `--entity-id` and `--image-path`; no fixed production target.
- Produces: legacy reconciliation and review artifacts that mark prior `prov-1` repair proposals as superseded rather than re-adding the entity.

- [ ] **Step 1: Add failing pre/post deletion compatibility tests**

```python
def test_publication_suppresses_manifest_tombstones_before_physical_delete():
    assert decide_publication_candidate(_candidate(id="prov-1")) == (
        "excluded", "reviewed-removal"
    )


def test_review_manifest_does_not_require_a_deleted_ghost(media_candidate_root):
    manifest = build_manifest(media_candidate_root)
    assert not any(item["recordId"] == "prov-1" and item["status"] == "repair" for item in manifest["findings"])
    assert any(item["recordId"] == "prov-1" and item["status"] == "superseded" for item in manifest["history"])
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q agent/tests/test_publication_status.py tests/checks/test_reconcile_data_dry_run.py tests/checks/test_build_data_review_manifest.py tests/checks/test_build_image_provenance_review.py`

Expected: FAIL because production code and generators still require or repair the ghost.

- [ ] **Step 3: Replace hard-coded ghost logic with manifest-driven tombstones**

Load the exact `delete` IDs from `batch-21-media-truth.json`. Publication filtering remains active before apply and becomes a no-op when the entity is absent. `reconcile_data_dry_run.py` must not emit spatial, image, orphan, or verified-at repairs for tombstoned IDs.

- [ ] **Step 4: Generalize image provenance review targeting**

```python
def build_packet(
    root: Path,
    *,
    entity_id: str,
    image_path: str,
    photo_ledger: Path | None = None,
) -> dict[str, Any]:
    entity = _find_entity(root / "web/data.json", entity_id)
    if entity is None:
        if entity_id not in reviewed_removal_ids(root):
            raise ProvenanceReviewError(f"entity not found: {entity_id}")
        return {
            "schemaVersion": 1,
            "mode": "read-only-image-provenance-review",
            "status": "target_absent",
            "mutationAllowed": False,
            "target": {"entityId": entity_id, "imagePath": image_path},
            "supersededBy": "batch-21-media-truth-v1",
            "evidenceChecklist": [],
        }
    return _build_present_target_packet(
        root,
        entity=entity,
        entity_id=entity_id,
        image_path=image_path,
        photo_ledger=photo_ledger,
    )
```

Extract the current present-target packet body into `_build_present_target_packet` without changing its evidence-selection semantics. The implementation must return the exact controlled `target_absent` result above when a reviewed tombstone is missing, and must keep `mutationAllowed=false`. Update the runbook to mark the old `prov-1` packet as superseded by deletion evidence.

- [ ] **Step 5: Run focused tests**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q agent/tests/test_publication_status.py tests/checks/test_reconcile_data_dry_run.py tests/checks/test_build_data_review_manifest.py tests/checks/test_build_image_provenance_review.py`

Expected: PASS against both current data and staged candidate fixtures.

- [ ] **Step 6: Commit**

```powershell
git add agent/publication_status.py agent/tests/test_publication_status.py scripts/checks/reconcile_data_dry_run.py tests/checks/test_reconcile_data_dry_run.py scripts/checks/build_data_review_manifest.py tests/checks/test_build_data_review_manifest.py scripts/checks/build_image_provenance_review.py tests/checks/test_build_image_provenance_review.py docs/runbooks/image-provenance-review.md
git commit -m "fix(data): retire prov-1 production repair paths"
```

### Task 9: Truth-Aware Candidate Public Artifacts

**Files:**
- Modify: `scripts/generate_llms_txt.py`
- Modify: `scripts/export_fe_data.py`
- Create: `scripts/checks/build_media_truth_artifacts.py`
- Create: `tests/test_generate_llms_media_truth.py`
- Modify: `tests/test_export_fe_data.py`
- Create: `tests/checks/test_build_media_truth_artifacts.py`
- Modify: `scripts/checks/build_data_review_manifest.py`
- Modify: `scripts/checks/build_image_provenance_review.py`
- Modify: `tests/llms-specification.test.ts`
- Modify: `tests/image-governance.test.ts`

**Interfaces:**
- Produces: `generate_llms(data_path: Path, output_dir: Path) -> dict[str, Path]`.
- Produces: `export_frontend_data(*, sqlite_path: Path | None, json_path: Path | None, output_dir: Path) -> dict[str, Path]` with exactly one explicit source.
- Produces: `build_candidate_artifacts(candidate_root: Path, output_dir: Path, *, truth_manifest: Path, batch_ledger: Path, renderer_registry: Path) -> dict[str, Path]`.
- Both functions accept candidate paths and never silently fall back when explicit input is supplied.
- The artifact bundle contains byte-addressed `entity-index.json`, `llms.txt`, `llms-full.txt`, `image-provenance-review.json`, `data-review-manifest.json`, the corrected Batch 21 ledger, and the affected renderer/release artifact. Every output is generated from the candidate root or an explicitly named immutable reviewed input, never from a default live path.

- [ ] **Step 1: Add failing artifact truth tests**

```python
def test_llms_output_does_not_invent_press_credits(candidate_json, tmp_path):
    outputs = generate_llms(candidate_json, tmp_path)
    full = outputs["llms_full"].read_text(encoding="utf-8")
    assert "prov-1" not in full
    assert "100% ảnh WebP nội bộ" not in full
    assert "bản quyền Google Images" not in full
    assert "Minh họa AI" in full
    assert "Minh họa đồ họa" in full


def test_frontend_export_uses_only_the_explicit_candidate_source(candidate_json, tmp_path):
    outputs = export_frontend_data(
        sqlite_path=None,
        json_path=candidate_json,
        output_dir=tmp_path,
    )
    index = json.loads(outputs["entity_index"].read_text(encoding="utf-8"))
    assert "prov-1" not in {row["id"] for row in index}
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/test_generate_llms_media_truth.py tests/test_export_fe_data.py`

Run: `npm --prefix web-nuxt run test:data -- tests/llms-specification.test.ts tests/image-governance.test.ts`

Expected: FAIL because both generators use fixed live paths and LLM output invents documentary claims.

- [ ] **Step 3: Parameterize generators and remove fallback claims**

Refactor `generate_llms_txt.py` so `format_entity_block` branches on `image_type`:

```python
def media_lines(entity: dict) -> list[str]:
    attrs = entity.get("attributes") or {}
    image_type = attrs.get("image_type")
    if image_type == "ai-generated":
        return ["- **Hình ảnh**: Minh họa AI — không phải ảnh chụp tại chỗ."]
    if image_type == "generated-placeholder":
        return ["- **Hình ảnh**: Minh họa đồ họa — chưa có ảnh riêng cho thực thể."]
    evidence = sourced_photo_evidence(attrs)
    if evidence is not None:
        return [
            f"- **Ảnh có nguồn**: {evidence.credit}",
            f"- **Nguồn truy vết**: {evidence.source_url}",
        ]
    return ["- **Hình ảnh**: Chưa có ảnh đã xác minh nguồn gốc."]
```

Remove every default such as `Phóng viên`, `Báo chí địa phương`, `100%`, and `Google Images`. Add argparse options `--data`, `--llms-output`, and `--llms-full-output`.

Refactor `export_fe_data.py` into import-safe functions and add `--sqlite`, `--json`, and `--output-dir`; exactly one source must be selected. `--help` must print help without generating files.

Implement `build_media_truth_artifacts.py` as the deterministic bundle orchestrator. It passes the candidate JSON/SQLite and candidate asset root to the parameterized generators, passes the candidate root to `build_data_review_manifest`, calls generalized `build_image_provenance_review` for the exact 40-record truth scope (including a controlled tombstone packet for `prov-1`), copies the corrected Batch 21 ledger and renderer/release registry into the bundle, and writes a sorted-key manifest containing each output's relative path, byte length, and SHA-256.

- [ ] **Step 4: Replace the 1,772-documentary test with a type-aware truth contract**

The revised Vitest loop reads every entity and asserts:

```typescript
if (attrs.image_type === 'ai-generated' || attrs.image_type === 'generated-placeholder') {
  expect(attrs.is_verified_photo).toBe(false)
}
if (['documentary', 'journalistic', 'official', 'press'].includes(attrs.image_type)) {
  expect(hasCompleteRightsEvidence(attrs)).toBe(true)
}
```

Do not add an exemption for Batch 21 or a hard-coded expected documentary count.

- [ ] **Step 5: Generate the complete candidate artifact bundle twice outside public live paths**

Run:

```powershell
python scripts/checks/build_media_truth_artifacts.py --candidate-root .tmp/media-truth-candidate/candidate --truth docs/standards/batch-21-media-truth.json --batch-ledger outputs/batch_culinary_restaurants_photos.json --renderer-registry web-nuxt/config/entity-image-renderers.json --output-dir .tmp/media-truth-artifacts/first
python scripts/checks/build_media_truth_artifacts.py --candidate-root .tmp/media-truth-candidate/candidate --truth docs/standards/batch-21-media-truth.json --batch-ledger outputs/batch_culinary_restaurants_photos.json --renderer-registry web-nuxt/config/entity-image-renderers.json --output-dir .tmp/media-truth-artifacts/second
```

Compare every bundle byte using the generated manifests, including the image-provenance review, data-review manifest, Batch 21 ledger, renderer/release registry, entity index, and both LLM outputs. Do not run default-path generators during this task.

- [ ] **Step 6: Run tests and commit**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/test_generate_llms_media_truth.py tests/test_export_fe_data.py`

Run: `npm --prefix web-nuxt run test:data -- tests/llms-specification.test.ts tests/image-governance.test.ts`

```powershell
git add scripts/generate_llms_txt.py scripts/export_fe_data.py scripts/checks/build_media_truth_artifacts.py scripts/checks/build_data_review_manifest.py scripts/checks/build_image_provenance_review.py tests/test_generate_llms_media_truth.py tests/test_export_fe_data.py tests/checks/test_build_media_truth_artifacts.py tests/llms-specification.test.ts tests/image-governance.test.ts
git commit -m "fix(media): generate truthful public image metadata"
```

### Task 10: Catalog-Wide Media Truth Inventory

**Files:**
- Create: `scripts/checks/build_media_truth_inventory.py`
- Create: `tests/checks/test_build_media_truth_inventory.py`
- Create: `outputs/media-truth-inventory-2026-09-25.json`
- Modify: `docs/runbooks/image-provenance-review.md`

**Interfaces:**
- Consumes the Task 7 candidate root whose fixed layout is `candidate/data.json`, `candidate/vinhlong360.db`, `candidate/public/img/entities`, and `candidate/stage-result.json`.
- Produces: `build_inventory(root: Path, data_path: Path, asset_root: Path, truth_path: Path) -> dict[str, Any]`.
- Inventory contains exactly one row per candidate entity and always `mutationAllowed=false`.
- Classification enum: `generated-placeholder`, `ai-generated`, `rights-cleared`, `documentary-candidate-missing-evidence`, `unknown-quarantined`.

- [ ] **Step 1: Add failing completeness and fail-closed tests**

```python
def test_candidate_inventory_has_one_row_per_remaining_entity(candidate_root):
    inventory = build_inventory(
        candidate_root,
        candidate_root / "data.json",
        candidate_root / "public/img/entities",
        ROOT / "docs/standards/batch-21-media-truth.json",
    )
    ids = [row["entityId"] for row in inventory["items"]]
    assert len(ids) == 1771
    assert len(set(ids)) == 1771
    assert "prov-1" not in ids
    assert inventory["mutationAllowed"] is False


def test_unknown_asset_is_quarantined_not_inferred_from_file_size(candidate_root):
    row = inventory_row(candidate_root, "unknown-asset")
    assert row["classification"] == "unknown-quarantined"
    assert row["proposedMutation"] is None
```

- [ ] **Step 2: Run the test and verify RED**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/checks/test_build_media_truth_inventory.py`

Expected: FAIL because the inventory builder does not exist.

- [ ] **Step 3: Implement deterministic evidence-backed classification**

Classification priority is exact and non-heuristic:

1. Batch 21 truth manifest classification.
2. Complete `sourced_photo_evidence` -> `rights-cleared`.
3. Documentary family without complete evidence -> `documentary-candidate-missing-evidence`.
4. Explicit `ai-generated` with generation reference -> `ai-generated`.
5. Explicit `generated-placeholder` -> `generated-placeholder`.
6. Everything else -> `unknown-quarantined`.

File size, visual resemblance, filename, and mutable dates must never upgrade a class. Each row includes entity ID, image paths and SHA-256 values, current claims, evidence references, missing requirements, classification reason, and review status.

- [ ] **Step 4: Generate twice from the staged candidate**

Run: `python scripts/checks/build_media_truth_inventory.py --data .tmp/media-truth-candidate/candidate/data.json --asset-root .tmp/media-truth-candidate/candidate/public/img/entities --truth docs/standards/batch-21-media-truth.json --output outputs/media-truth-inventory-2026-09-25.json`

Run it again and compare bytes.

Expected: 1,771 unique rows, deterministic output, no mutation authority, protected hashes unchanged.

- [ ] **Step 5: Run tests and commit**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/checks/test_build_media_truth_inventory.py`

```powershell
git add scripts/checks/build_media_truth_inventory.py tests/checks/test_build_media_truth_inventory.py outputs/media-truth-inventory-2026-09-25.json docs/runbooks/image-provenance-review.md
git commit -m "feat(media): inventory catalog provenance truth"
```

### Task 11: Pre-Apply Verification and Owner Review Package

**Files:**
- Create: `docs/runbooks/media-truth-apply.md`
- Create: `scripts/checks/build_media_truth_review.py`
- Create: `tests/checks/test_build_media_truth_review.py`
- Create: `outputs/media-truth-test-evidence-2026-09-25.json`
- Create: `outputs/media-truth-review-2026-09-25.json`

**Interfaces:**
- Produces: `build_review_package(root: Path, *, plan_path: Path, approved_plan_path: Path, stage_result_path: Path, inventory_path: Path, artifact_manifest_path: Path, backup_dir: Path, test_evidence_path: Path) -> dict[str, Any]`.
- Produces: `render_non_authorizing_apply_command(approved_plan_path: Path, *, sqlite_path: Path, json_path: Path, sqlite_backup: Path, json_backup: Path, plan_sha256: str, lock_path: Path, journal_path: Path) -> str` and `render_recovery_command(journal_path: Path, *, sqlite_backup: Path, json_backup: Path) -> str`.
- Produces a non-authorizing review package with plan digest, candidate hashes, exact mutation counts, test evidence, backup commands, recovery commands, and `mutationAllowed=false`.
- This task is the last task permitted before explicit protected-data apply approval.

- [ ] **Step 1: Add failing review-package tests**

```python
def test_review_package_is_hash_bound_and_non_authorizing(review_fixture):
    package = build_review_package(**review_fixture.kwargs)
    assert set(package) == {
        "schemaVersion", "status", "mutationAllowed", "plan", "candidate",
        "scope", "tests", "protectedInputs", "backupProcedure",
        "applyProcedure", "recoveryProcedure", "openFindings",
    }
    assert package["status"] == "ready_for_owner_review"
    assert package["mutationAllowed"] is False
    assert package["scope"]["counts"] == {
        "batch21Records": 40,
        "deletedEntities": 1,
        "retainedPlaceholders": 37,
        "retainedAi": 2,
        "jsonRelationshipsDeleted": 6,
        "sqliteRelationshipsDeleted": 0,
    }
    assert package["backupProcedure"]["manifestSha256"] == review_fixture.manifest_sha256
    assert package["applyProcedure"]["authorization"] == "owner_approval_required"
    assert package["applyProcedure"]["doNotExecute"] is True
    assert package["applyProcedure"]["approvedPlanPath"] == ".tmp/media-truth-approved/media-truth-plan-approved.json"
    assert "--plan-sha256" in package["applyProcedure"]["command"]
    assert package["recoveryProcedure"]["doNotExecute"] is True


def test_review_package_rejects_open_load_bearing_findings(review_fixture):
    review_fixture.write_test_evidence(open_findings=[{"severity": "Important"}])
    with pytest.raises(ReviewPackageError, match="open Critical/Important"):
        build_review_package(**review_fixture.kwargs)
```

Add negative tests for a mismatched backup copy, protected-input hash drift, a non-deterministic candidate marker, a missing artifact-bundle member/hash, and any count other than 40/37/2/6/0.

- [ ] **Step 2: Run the review-package tests and verify RED**

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/checks/test_build_media_truth_review.py`

Expected: FAIL because the review-package builder does not exist.

- [ ] **Step 3: Implement the builder and write the runbook with exact commands and stop conditions**

The runbook must include:

```powershell
python scripts/backup_data.py --target local --out-dir .tmp/media-truth-backups-phase-1 --label before-media-truth-review --keep 50 --max-age-days 3650
python scripts/checks/build_media_truth_plan.py --output outputs/media-truth-plan-2026-09-25.json
python scripts/checks/stage_data_reconciliation.py --plan outputs/media-truth-plan-2026-09-25.json --asset-root web-nuxt/public/img/entities --output-dir .tmp/media-truth-candidate
```

The runbook begins with `> STATUS: draft; awaiting exact protected-data apply approval.` The backup command is a regeneration command, not an instruction to overwrite the reviewed snapshot. The runbook records the exact timestamped directory created in Task 7. It includes the exact digest-, backup-, lock-, and journal-bound apply and recovery command strings rendered into the review package, each marked `doNotExecute=true` and `owner_approval_required`; the commands are evidence for a later approval, not authorization to run them. Recovery commands must use the journal recorded in that package, not a guessed path.

`build_media_truth_review.py` validates the canonical plan digest, staged candidate digests, inventory row count, complete candidate artifact-bundle manifest, exact scope IDs/triples/counts, protected input hashes, backup manifest and copied-file hashes, backup JSON byte equality, backup SQLite integrity/logical equality, deterministic-generation markers, and the test-evidence schema before writing LF-only sorted-key JSON. It renders exact apply/recovery commands from those bound paths and digests, marks them non-authorizing, rejects any open Critical/Important finding, and never accepts or emits an apply authorization field set to true.

- [ ] **Step 4: Run focused validation suites**

Run:

```powershell
$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q agent/tests/test_media_provenance.py agent/tests/test_ai_disclosure.py agent/tests/test_media_policy.py agent/tests/test_image_descriptor.py agent/tests/test_image_metadata_disclosure.py
$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/checks/test_hard_checks.py tests/checks/test_r10_6_legacy_inventory.py tests/checks/test_apply_data_reconciliation.py tests/checks/test_reconciliation_journal.py tests/checks/test_build_media_truth_plan.py tests/checks/test_stage_data_reconciliation.py tests/checks/test_build_media_truth_inventory.py tests/checks/test_build_media_truth_artifacts.py tests/checks/test_build_media_truth_review.py
$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest -q tests/test_generate_llms_media_truth.py tests/test_export_fe_data.py tests/test_entity_write_guard.py
$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest tests/launch_safety/ -m "" -n0 -q
npm --prefix web-nuxt exec vitest run tests/ai-disclosure.test.ts tests/entity-card-disclosure.test.ts tests/entity-image-detail.test.ts tests/gallery-disclosure.test.ts tests/admin-image-disclosure.test.ts
npm --prefix web-nuxt run test:data -- tests/image-governance.test.ts tests/llms-specification.test.ts
python -m ruff check agent scripts/checks scripts/ops tests
python -m py_compile agent/media_provenance.py agent/ai_disclosure.py agent/media_policy.py agent/image_descriptor.py scripts/checks/build_media_truth_plan.py scripts/checks/stage_data_reconciliation.py scripts/checks/build_media_truth_inventory.py scripts/checks/build_media_truth_artifacts.py scripts/checks/build_media_truth_review.py scripts/checks/apply_data_reconciliation.py
python scripts/checks/run_hard.py --all
```

- [ ] **Step 5: Run broad existing suites**

Run: `Get-PSDrive C` and stop before the full suites if free space is below 5 GB.

Run: `$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest tests/ agent/tests/ -m "not slow" -q --tb=line`

Run: `npm --prefix web-nuxt test`

Run: `npm --prefix web-nuxt run typecheck`

Run: `npm --prefix web-nuxt run test:data`

Compare the Python result with the exact current `docs/ROADMAP.md` `Fail-đã-biết` list rather than requiring a misleading zero-failure count. Record environmental failures separately from product failures; do not mark a product failure as an environment issue without reproducible evidence, and do not accept any new failure outside the documented baseline.

- [ ] **Step 6: Verify protected stores, backup, and sidecars**

```powershell
Get-FileHash -Algorithm SHA256 agent/data/vinhlong360.db,web/data.json
Get-ChildItem agent/data -Force | Where-Object { $_.Name -match 'vinhlong360\.db-(wal|shm|journal)$' }
$backupRoot = Resolve-Path '.tmp/media-truth-backups-phase-1'
$backupDir = Get-ChildItem $backupRoot -Directory | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
if ($null -eq $backupDir) { throw 'Reviewed media-truth backup is missing' }
Get-FileHash -Algorithm SHA256 (Join-Path $backupDir.FullName 'manifest.json'),(Join-Path $backupDir.FullName 'vinhlong360.db'),(Join-Path $backupDir.FullName 'data.json')
```

Expected protected hashes are the two Global Constraints values, the sidecar query returns no rows, the backup JSON byte hash matches its protected input, the backup SQLite integrity/logical digest/counts match its protected source, and the manifest hash matches the Task 7 recorded value.

- [ ] **Step 7: Record test evidence and generate the review package**

Write `outputs/media-truth-test-evidence-2026-09-25.json` from the actual completed command results using the exact top-level keys `schemaVersion`, `commands`, `knownBaseline`, `openFindings`, and `generatedArtifacts`. Every command row contains the literal command, exit code, result classification, and SHA-256 of its captured output; no row may claim pass when the exit code and documented baseline disagree.

Resolve `$backupDir` exactly as in Step 6, then run:

```powershell
python scripts/checks/build_media_truth_review.py --plan outputs/media-truth-plan-2026-09-25.json --approved-plan-path .tmp/media-truth-approved/media-truth-plan-approved.json --stage-result .tmp/media-truth-candidate/candidate/stage-result.json --inventory outputs/media-truth-inventory-2026-09-25.json --artifact-manifest .tmp/media-truth-artifacts/first/artifact-manifest.json --backup-dir $backupDir.FullName --test-evidence outputs/media-truth-test-evidence-2026-09-25.json --output outputs/media-truth-review-2026-09-25.json
```

The JSON must contain these exact top-level fields:

```json
{
  "schemaVersion": 1,
  "status": "ready_for_owner_review",
  "mutationAllowed": false,
  "plan": {},
  "candidate": {},
  "scope": {},
  "tests": [],
  "protectedInputs": {},
  "backupProcedure": {},
  "applyProcedure": {},
  "recoveryProcedure": {},
  "openFindings": []
}
```

Run the builder twice and compare bytes. Reject generation if any Critical/Important finding is open, counts differ from 40/37/2/6/0, candidate generation is not deterministic, the reviewed backup is missing or mismatched, or protected inputs changed.

- [ ] **Step 8: Dispatch final whole-branch review**

Use the final review package from the SDD skill. Any findings receive one fix wave and one scoped re-review. Do not proceed to Task 12 with an open Critical or Important finding.

- [ ] **Step 9: Commit the review package and runbook**

```powershell
git add docs/runbooks/media-truth-apply.md scripts/checks/build_media_truth_review.py tests/checks/test_build_media_truth_review.py outputs/media-truth-test-evidence-2026-09-25.json outputs/media-truth-review-2026-09-25.json
git commit -m "docs(media): prepare protected apply review package"
```

## Mandatory Protected-Data Apply Gate

Stop after Task 11 and present the owner with:

- exact plan SHA-256;
- current and candidate SQLite logical digests;
- current and candidate JSON SHA-256;
- mutation counts by store, record type, operation, and field;
- the 40 target IDs and six relationship triples;
- backup directory and manifest hash;
- full test/review verdicts; and
- exact apply and recovery commands from the reviewed runbook.

Do not execute Task 12 unless the owner explicitly approves this exact apply package. A general instruction to continue, prior design approval, or implementation-plan approval is not sufficient.

### Task 12: Owner-Approved Protected Apply and Tracked Data Cleanup

**Files:**
- Modify after approval: `agent/data/vinhlong360.db` (protected local runtime artifact; do not stage if ignored)
- Modify after approval: `web/data.json`
- Delete after approval: `web-nuxt/public/img/entities/prov-1.webp`
- Modify after approval: `web-nuxt/public/data/entity-index.json`
- Modify after approval: `web-nuxt/public/llms.txt`
- Modify after approval: `web-nuxt/public/llms-full.txt`
- Modify after approval: current generated review/parity artifacts named in the review package
- Modify after approval: exact old-hash baselines that guard the two protected stores

**Interfaces:**
- Consumes the exact approved plan digest, backup paths, candidate artifacts, and runbook from Task 11.
- Produces protected stores and public artifacts matching the reviewed candidate.

- [ ] **Step 1: Reverify the exact backup named in the approval package**

Verify the existing approved backup's manifest, copied file hashes, sizes, counts, JSON byte equality, and SQLite integrity/logical digest before continuing. If it is missing or mismatched, cancel the approval and return to Task 11 to generate a new review package; do not silently create a replacement under the old approval.

- [ ] **Step 2: Reverify live input hashes and absence of sidecars**

Expected hashes must still equal the Global Constraints values. Any mismatch cancels the approval and returns to Task 11 with a newly generated package.

- [ ] **Step 3: Materialize an approved plan copy**

Write the approved copy only to `.tmp/media-truth-approved/media-truth-plan-approved.json`, the exact path pre-bound in the review package. It must preserve the reviewed mutations and canonical digest, add the exact owner decision marker recorded by the controller, set `status="approved"`, and set `reviewedPlanMarker` without modifying the review-required source plan. Recompute and present the approved plan digest before running apply; if it differs for any reason beyond the approval fields, stop.

- [ ] **Step 4: Execute the exact reviewed apply command**

Only after the owner separately approves the exact `applyProcedure.command` recorded in the review package may the operator execute that exact string. The command must include all of:

```text
--plan
--sqlite
--json
--sqlite-backup
--json-backup
--plan-sha256
--lock-path
--journal-path
--maintenance-window
--confirm-phase-b
--allow-live-protected-inputs
```

Do not add `--accept-deferred` unless the approved package explicitly lists and accepts each deferred item.

- [ ] **Step 5: Verify post-apply state before deleting the asset**

Confirm `prov-1` is absent from both stores, zero relationships reference it, all 39 retained records have the approved classes, target verification is clean, unrelated digests are unchanged, and no sidecar exists.

- [ ] **Step 6: Delete the tracked ghost asset and regenerate public artifacts**

Delete only `web-nuxt/public/img/entities/prov-1.webp`. Run the complete parameterized candidate-artifact bundle against the newly applied protected data and retained asset root, then compare every output byte with the pre-reviewed artifact manifest before staging them: entity index, both LLM files, image-provenance review, data-review manifest, corrected Batch 21 ledger, and renderer/release artifact.

- [ ] **Step 7: Replace old protected-hash baselines atomically**

Search all tracked files for the two old hashes. Update each live-state guard to the exact new hash, remove the old hash from accepted live values, and preserve historical hashes only in explicitly historical reports/specs. Run the focused hash guard tests immediately.

- [ ] **Step 8: Commit the approved data change**

Stage only the tracked data, asset deletion, generated outputs, and exact baseline updates listed by `git diff --name-status`. Do not stage unrelated dirty-tree changes.

```powershell
git commit -m "fix(data): apply media truth recovery phase 1"
```

### Task 13: Post-Apply Verification and Phase 2 Handoff

**Files:**
- Modify: `outputs/media-truth-inventory-2026-09-25.json`
- Modify: `outputs/media-truth-review-2026-09-25.json`
- Modify: `docs/runbooks/media-truth-apply.md`
- Create: `docs/reports/2026-09-25-media-truth-recovery-phase-1.md`

**Interfaces:**
- Produces final applied hashes, counts, test evidence, recovery evidence, and the authoritative 1,771-row Phase 2 inventory.
- Produces the input required to write the separate Phase 2 remediation plan; it does not authorize Phase 2 mutations.

- [ ] **Step 1: Regenerate the Phase 2 inventory from applied data**

Run the inventory generator twice and require byte-identical output with exactly 1,771 unique entity rows and no `prov-1`.

- [ ] **Step 2: Run all validation gates again**

Repeat every command in Task 11 Steps 4-6 against the applied stores. Add `git diff --check` and verify every generated artifact matches the reviewed candidate manifest, not only the entity index and LLM files.

- [ ] **Step 3: Perform an explicit recovery rehearsal on copies**

Copy the applied stores and verified backups into a temporary fixture directory, inject a journaled post-commit failure, execute recovery, and prove the fixture returns to the exact before hashes. Never rehearse recovery on the live paths.

- [ ] **Step 4: Write the Phase 1 report**

Begin the report with `> STATUS: completed evidence; does not authorize Phase 2 mutations.` Record:

- commits and reviewers;
- old/new protected hashes;
- exact mutation counts;
- backup and journal identities;
- test commands and outcomes;
- confirmation that `prov-1` and its six relationships are gone;
- 37 placeholder and two AI retained Batch 21 records;
- inventory category counts for all 1,771 remaining entities; and
- unresolved Phase 2 groups with no mutation authority.

- [ ] **Step 5: Commit final evidence**

```powershell
git add outputs/media-truth-inventory-2026-09-25.json outputs/media-truth-review-2026-09-25.json docs/runbooks/media-truth-apply.md docs/reports/2026-09-25-media-truth-recovery-phase-1.md
git commit -m "docs(media): record phase 1 recovery evidence"
```

- [ ] **Step 6: Dispatch final whole-branch re-review if Task 12 changed code or baselines after the prior review**

The re-review is scoped to the approved apply and post-apply baseline/artifact changes. Any residual load-bearing finding is surfaced to the owner; there is no silent waiver.

## Execution Handoff

The owner already selected **Subagent-Driven Development**: one fresh implementer per task, an independent task review after every task, and a broad final review before the apply gate. Execution begins with Task 1 and runs continuously through Task 11. Task 12 is a mandatory stop for separate protected-data approval.
