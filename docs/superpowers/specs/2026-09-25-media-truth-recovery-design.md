# Media Truth Recovery Design

> STATUS: design approved in chat on 2026-09-25; written-spec review pending. No protected-data mutation is authorized by this document.

**Date:** 2026-09-25
**Scope:** Delete the `prov-1` ghost record, correct Batch 21 image provenance, add truthful rights-cleared media support, and establish the catalog-wide media recovery program.

## Decision

Use a two-phase recovery:

1. Phase 1 deletes `prov-1`, corrects all remaining Batch 21 image classifications, and makes the runtime media contract capable of representing AI, placeholders, and rights-cleared sourced photographs without guessing from a file path.
2. Phase 2 inventories every remaining entity image and moves each record through the same evidence-backed classification contract in reviewable batches.

This is preferable to deleting only `prov-1` because the same Batch 21 process attached unsupported documentary claims to 40 records. It is also preferable to a single catalog-wide mutation because the protected SQLite and JSON stores are already divergent and require bounded, owner-approved changes.

## Evidence and Current State

The read-only history report at `.superpowers/research/prov-1/history-report.md` and its independent review support these conclusions:

- `prov-1` is a ghost/test-like entity with `12 duong Thu Nghiem`, `0900 000 000`, confidence `0.4`, and `https://example.test/source`.
- It was deleted as junk or test data in `a89f8e55`, `86904d3`, and `3cd27e1c`, then restored through later whole-file data snapshots.
- Its local WebP predates the restored entity and is a generic `BAN SAC NAM BO` graphic, not a documentary photograph.
- Commit `68d59f0f` attached unsupported author, publisher, license, `documentary`, and `is_verified_photo=true` claims without acquiring or modifying the image bytes.
- Batch 21 contains 40 affected records: 38 visually confirmed generated placeholders and two AI-generated assets, `tep-rang-dua` and `cua-com-duyen-hai`, introduced by commit `30a3fae9`.
- All 40 current JSON records are marked documentary and verified, and none has complete image-specific source and permission evidence.
- JSON contains one `prov-1` entity and six outgoing relationships. No itinerary stop references it. SQLite contains the entity but no related relationship row.
- The protected stores remain unchanged at the design checkpoint:
  - SQLite SHA-256: `ea83864990cf8455061b2436f072c097bc7011f56428c5ba3ba43bcd66fb78a4`
  - JSON SHA-256: `8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f`

The runtime also has a policy mismatch. Project policy allows rights-cleared press, documentary, journalistic, and official images, but the current Python and TypeScript descriptor boundaries accept only AI and placeholders for entity media. Legacy local entity paths are inferred as AI without consulting the record's provenance attributes.

## Goals

1. Remove `prov-1` and its production-coupled references without changing unrelated entity data.
2. Correct the other 39 Batch 21 records: 38 generated placeholders and two AI-generated assets.
3. Remove unsupported press credits, licenses, captions, and verified-photo claims from those records.
4. Represent rights-cleared sourced photographs explicitly in API and frontend descriptors.
5. Fail closed when provenance is missing, malformed, private, generic, or contradictory.
6. Produce a deterministic, hash-bound mutation proposal before any protected-store apply.
7. Close the current JSON publication race before the apply path can be authorized.
8. Inventory all 1,771 entities remaining after `prov-1` deletion and route later corrections through reviewable batches.

## Non-Goals

- Do not find or invent a Bao Vinh Long article or photograph for `prov-1`.
- Do not treat author/source attribution alone as re-hosting permission.
- Do not delete the 39 other Batch 21 entities merely because their image metadata is wrong.
- Do not copy the current JSON over SQLite or export the whole current SQLite store over JSON.
- Do not claim global SQLite/JSON parity as part of this targeted media correction.
- Do not increase a legacy provenance exemption, self-backdate a record into an exemption, or add a new unreviewed waiver.
- Do not apply, publish, push, or remove a protected-data backup without a separate explicit owner decision.

## Canonical Media Classification

`attributes.image_type` is the canonical stored classification. The supported entity-media states are:

| Stored class | Meaning | `is_verified_photo` | Required provenance |
| --- | --- | --- | --- |
| `generated-placeholder` | A generic local graphic that does not depict the specific entity | `false` | No press author/source/license claims |
| `ai-generated` | An AI-created editorial illustration | `false` | Generation model/reference when repository evidence exists; no press claims |
| `documentary` | A rights-cleared documentary photograph | `true` only after the full evidence gate | Author, source, image-specific public URL, license/re-host scope, permission evidence |
| `journalistic` | A rights-cleared journalistic photograph | Same as documentary | Same as documentary |
| `official` | A rights-cleared official photograph | Same as documentary | Same as documentary |
| `press` | A rights-cleared press photograph | Same as documentary | Same as documentary |
| absent/unknown | No trustworthy classification | Never inferred as verified | Quarantine or render a generated placeholder |

The following invariants are mandatory:

- `generated-placeholder` and `ai-generated` never carry `is_verified_photo=true`.
- A sourced-photo class never passes solely because an author and publisher string exist.
- `image_source_url` must be image-specific, syntactically valid, public, and non-placeholder.
- A credit line and a copyright statement are not permission evidence.
- Mutable record timestamps never establish legacy eligibility.
- A denial or restriction in the matching evidence set overrides an affirmative-looking statement.
- Unknown provenance is not converted to AI, documentary, or verified based on the local filename.

## Public Descriptor Contract

The Python and TypeScript descriptor boundaries will become media-aware rather than AI-only. The public union will support:

- `source_class: "ai-generated"`, `source_kind: "entity-editorial"`;
- `source_class: "placeholder"`, `source_kind: "generated-placeholder"`;
- `source_class: "rights-cleared"`, with `source_kind` equal to `documentary`, `journalistic`, `official`, or `press`; and
- the existing user-uploaded forms, which remain suppressed or handled according to the existing UGC policy.

The descriptor adds a nullable traceable `source_url`. Rights-cleared descriptors require both a non-empty visible `credit` and a valid `source_url`. AI and placeholder descriptors require both values to be null. The disclosure policy gains a sourced-photo entry with neutral copy that directs the user to the visible author/source credit; it must not imply on-site verification by vinhlong360.

Descriptor production uses the entity's normalized image attributes and the shared provenance validator. A raw local path is only a location; it does not determine the media class. Incomplete sourced-photo evidence produces no sourced-photo descriptor and falls back to the explicit placeholder path.

The existing disclosure artifact may be extended in this phase, but it will not be renamed. Renaming the artifact and removing compatibility surfaces are separate cleanup work and must not obscure the truth correction.

## Phase 1: `prov-1` and Batch 21

### Ghost deletion

The targeted proposal will:

- delete the `prov-1` entity from SQLite and JSON;
- delete exactly six JSON relationships with `from == "prov-1"` and no unrelated relationships;
- assert that SQLite currently has zero matching relationship rows;
- remove the Batch 21 ledger/generator row;
- remove production-specific publication exclusion, reconciliation, manifest, and image-review assumptions that require the ghost to exist;
- remove `web-nuxt/public/img/entities/prov-1.webp` as a tracked, Git-recoverable deletion;
- regenerate current public indexes and LLM artifacts; and
- preserve generic unit-test fixture identifiers named `prov-1` when they are independent synthetic examples rather than production references.

Historical reports remain in Git as evidence. Current generated artifacts that refer to the live ghost are regenerated or marked superseded; history is not silently rewritten.

### Remaining 39 records

For the 38 placeholder records:

- retain the existing local graphic when it is a safe, valid asset;
- set `image_type=generated-placeholder` and `is_verified_photo=false`;
- remove unsupported author, publisher, image-source, image-license, permission, and photo-verification claims;
- remove or replace the hard-coded photographic caption with the canonical placeholder disclosure; and
- expose a placeholder descriptor with no press credit.

For `tep-rang-dua` and `cua-com-duyen-hai`:

- retain the AI-generated assets;
- set `image_type=ai-generated` and `is_verified_photo=false`;
- remove unsupported press author/source/license claims;
- set `image_generation_model="cx/gpt-5.5-image"` and
  `image_generation_reference="git:30a3fae9"`; and
- expose the canonical AI disclosure in every public renderer.

No entity-level `verifiedAt` field is treated as image-rights evidence. It is changed only if the target record's broader verification semantics independently require it.

## Phase 2: Catalog-Wide Media Truth Recovery

After Phase 1, generate a deterministic inventory with exactly one row for each of the remaining 1,771 entity IDs. Each row records:

- entity ID and image path/hash;
- current classification and claims;
- evidence-backed proposed class;
- source/generation evidence references;
- missing requirements;
- review status; and
- `mutationAllowed: false`.

The inventory groups records into:

1. generated placeholders;
2. repository-proven AI images;
3. documentary candidates with complete rights evidence;
4. documentary candidates missing evidence; and
5. unknown/quarantined media.

Later data corrections are emitted in bounded batches. Each batch has its own exact ID set, before hashes, candidate output, tests, review, and owner apply decision. Phase 2 shrinks unsupported documentary claims and legacy exemptions; it never expands them merely to make a gate pass.

## Deterministic Mutation Proposal

Implementation and validation occur first on fixture copies. A deterministic `media-truth-plan.json` is then generated with:

- exact input SHA-256, size, and identity for SQLite and JSON;
- exact asset hashes for every affected media file;
- one before/after mutation record per affected field or row;
- expected deletion counts for entities and relationships;
- expected candidate hashes;
- canonical plan digest;
- explicit scope showing that unrelated IDs are unchanged; and
- `mutationAllowed: false` until a separate owner-approved apply step.

The plan performs targeted field-level changes in both stores. It does not use either divergent store as a whole-file replacement for the other. Verification reports target-scoped parity for the affected IDs and accurately preserves any unrelated known global drift.

## Apply and Recovery Safety

No live apply is authorized by this spec review. Before a later apply request can be presented, the apply harness must meet these requirements:

1. Create and verify backups of both protected stores.
2. Verify expected hashes, sizes, mtimes, row identities, asset hashes, and SQLite sidecar absence.
3. Acquire the reconciliation lock and require the maintenance-window/live-input flags.
4. Stage and fully validate candidate SQLite/JSON outputs before protected mutation.
5. Apply SQLite changes in an explicit transaction with exact before-value predicates.
6. Publish JSON using atomic capture plus no-overwrite publication, not check-then-`os.replace`.
7. Record durable journal phases before and after each irreversible boundary.
8. Revalidate candidate identity, hashes, sidecar absence, target-scoped parity, and public-artifact bytes before declaring completion.

### JSON publication protocol

The current check immediately followed by `os.replace` has a race window. The replacement protocol is:

1. Atomically move the current target to a unique captured-original path.
2. Verify the bytes and identity of the file that was actually captured.
3. If it differs from the approved input, restore it without overwriting another writer and abort.
4. Publish the candidate with a no-overwrite operation so a concurrently recreated target causes failure rather than data loss.
5. Retain the captured original until final verification succeeds.

Rollback may replace the published candidate only when the current target still matches the exact candidate identity and hash. If another writer changed it, recovery fails closed and leaves the verified backups and journal for manual resolution.

### Failure behavior

- Before SQLite commit: roll back the transaction and remove only owned temporary files.
- After SQLite commit but before verified JSON publication: keep the journal, block further apply attempts, and restore both stores from verified backups when ownership checks permit.
- After JSON publication but before completion: verify both published targets before automatic restoration; never overwrite an unexpected concurrent edit.
- On crash: a subsequent apply is refused until the journal recovery path completes.
- On any hash, count, identity, sidecar, permission, or parity mismatch: stop without inventing a repair.

## Generated and Public Artifacts

Generated outputs are rebuilt from the reviewed candidate data before live apply and rebuilt again after apply. The two generations must be byte-identical. At minimum, this includes current entity indexes, LLM text outputs, image-provenance review outputs, Batch 21 ledgers, data-review manifests, and any renderer registry or release artifact affected by the descriptor contract.

Artifacts must use truthful labels:

- placeholder: `Minh hoa do hoa` / the canonical Vietnamese placeholder disclosure;
- AI: `Minh hoa AI` / the canonical AI disclosure; and
- rights-cleared sourced photo: visible author/source credit with a traceable source link and no vinhlong360 field-verification claim.

## Test Strategy

Implementation follows TDD and uses independent task review plus a final whole-branch review.

### Classification and provenance tests

- Accept each valid canonical class and reject mixed or contradictory combinations.
- Reject verified placeholders and verified AI assets.
- Reject sourced-photo claims missing any required evidence field.
- Reject placeholder, private, malformed, generic, or mismatched URLs.
- Confirm denial evidence overrides affirmative evidence.
- Confirm mutable timestamps and new IDs cannot acquire legacy compatibility.

### Batch 21 migration tests

- Assert exactly one entity deletion and exactly six JSON relationship deletions.
- Assert zero matching SQLite relationship deletions are expected.
- Assert exactly 38 placeholders and two AI records remain.
- Assert all 39 records have `is_verified_photo=false` and no unsupported press claims.
- Assert only the two evidence-backed AI records receive generation provenance.
- Assert unrelated entity and relationship canonical digests are unchanged.

### API and frontend tests

- Python and TypeScript normalize equivalent inputs to equivalent descriptors.
- AI and placeholder disclosures remain visible and accessible on every registered renderer.
- Rights-cleared media renders visible author/source credit and a safe traceable source link.
- Saved/recent item snapshots preserve the descriptor class and provenance link.
- Incomplete sourced-photo records render the explicit placeholder rather than being inferred as AI or documentary.

### Apply and recovery tests

- Cover concurrent JSON changes before capture, after capture, before publication, after publication, and during rollback.
- Cover SQLite commit failures, journal recovery, candidate corruption, asset mismatch, and late SQLite sidecar creation.
- Prove rollback never overwrites a target that no longer matches the tool-owned candidate.
- Prove plan generation and candidate/public output generation are byte-identical across repeated runs.

### Validation gates

Run focused and full Python suites, the root data Vitest suite, affected Nuxt suites, type checking, linting, hard checks, entity-write governance, and release-artifact verification. The protected SQLite and JSON hashes and mtimes must remain unchanged throughout implementation and proposal generation.

## Acceptance Criteria

Before a separate apply approval:

1. The implementation and all candidate-data tests pass using fixture copies.
2. The plan identifies exactly the approved 40-record scope and six JSON relationships.
3. The candidate contains 38 placeholders and two AI records among the 39 retained Batch 21 entities.
4. No retained Batch 21 record has an unsupported documentary/verified claim.
5. Rights-cleared descriptors cannot be constructed without complete validated evidence.
6. Repeated plan, candidate, and artifact generation is byte-identical.
7. Protected hashes, mtimes, and sidecar state remain unchanged.
8. Independent task reviews and a final whole-branch review report no open Critical or Important finding.

After a separately approved apply:

1. `prov-1`, its six JSON relationships, its Batch 21 row, production-only dependencies, and its tracked asset are absent.
2. The remaining 39 Batch 21 records match the approved classifications and evidence fields in both stores.
3. No unrelated record changed according to canonical scope digests.
4. Public artifacts match the pre-reviewed candidate artifacts.
5. Backups and the journal prove the operation is recoverable, and no unexpected SQLite sidecar remains.
6. The Phase 2 inventory contains exactly one row for every remaining entity and grants no mutation authority.

## Approval Boundaries

The owner approvals are distinct:

1. design approval -- already given in chat;
2. written-spec approval -- required before implementation planning;
3. implementation-plan approval -- required before subagent-driven execution;
4. protected-data apply approval -- required after code, tests, reviews, exact mutation plan, candidate hashes, and backup procedure are available; and
5. publication/push approval -- not implied by any earlier approval.
