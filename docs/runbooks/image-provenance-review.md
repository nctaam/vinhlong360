# Image Provenance Review Runbook

> STATUS: active read-only review procedure (2026-09-29); the historical `prov-1` packet is superseded by the reviewed Batch 21 deletion evidence. No protected-store mutation is authorized.

## Purpose

Use this procedure to prepare documentary, journalistic, press, or official
image evidence for owner review. It implements the constitutional rule that
press/documentary imagery is allowed only when author, publication/source,
license or re-host scope, a traceable source URL, and explicit rights evidence
are all available.

The review packet is evidence only. It never approves a mutation, never edits
`agent/data/vinhlong360.db` or `web/data.json`, and never turns attribution into
permission. A credit line alone is not evidence that re-hosting is allowed.

## Historical `prov-1` status

`prov-1` is listed in `docs/standards/batch-21-media-truth.json` under
`delete`. Any packet or reconciliation proposal that referred to its old
documentary image is historical evidence only and is superseded by
`batch-21-media-truth-v1`; it must not be re-added after physical deletion.

## Current target status

The current repository evidence supplies an author, publication/source, and a
copyright attribution statement. It does not supply:

- an image-specific, non-placeholder HTTP(S) source URL; or
- a license or re-host scope that actually permits reuse; or
- explicit permission evidence showing that the image may be re-hosted.

Consequently, `R10.6` must remain blocked. Do not replace the placeholder with
an inferred article, publisher homepage, search result, or invented permission.

## Accepted evidence

The owner-review packet requires all of the following:

1. `image_source_url`: a traceable, image-specific URL belonging to the
   publisher or rights holder. It must be attached to the target image, not a
   generic entity citation. Malformed URLs, single-label/intranet hosts,
   reserved suffixes such as `.corp`, legacy numeric IPv4 forms, and every
   non-global IPv4/IPv6 literal are rejected.
2. `author`: the photographer, creator, or official credit exactly as published.
3. `source`: the publisher, press organization, or issuing authority.
4. `license`: affirmative, specific published license or permitted re-host
   scope. A copyright attribution, credit line, or denial such as `not licensed
   for re-hosting`, `reuse prohibited`, or `no permission to re-host` is
   retained as observed evidence, but does not itself satisfy this requirement.
   Accepted affirmative forms include a concrete identifier (`CC0 1.0`, `CC BY
   4.0`, `CC BY-SA 4.0`, `CC BY-NC-ND 4.0`, or `Public Domain Mark 1.0`) or
   an explicit grant such as `Permitted to re-host for this project` or
   `Được phép tái sử dụng`. Bare labels (`creative commons`, `public domain`)
   and denial variants (`Not public domain`, `Creative Commons licenses are not
   available`, or `all rights reserved`) never qualify. A standalone denial or
   prohibition term anywhere in the statement (`not`, `no`, `prohibited`,
   `forbidden`, `denied`, `unavailable`, `cannot`, or `may not`) overrides any
   identifier or apparent grant in the same statement. Matching uses word
   boundaries, so valid identifiers such as `CC BY-NC-ND 4.0` remain accepted.
   Statements containing `license`, `reuse`, or `re-host` without an
   affirmative grant do not qualify. If the matching target-image evidence set
   contains both an affirmative grant and a denial, the entire set fails
   closed while every raw statement remains visible for owner review.
5. One of `permission_evidence`, `rights_evidence`, or `permission`: a
   traceable reference to the written/public rights basis, not a generic claim.
   Accepted forms are a public HTTP(S) URL on a public host, or one of the
   structured references `owner-record:<id>`, `document:<id>`, or
   `case-file:<id>`, where `<id>` contains only letters, digits, `.`, `_`,
   `/`, or `-`. Values such as `yes` and `written release` are not evidence.

Store sensitive correspondence outside Git. The repository evidence field
should contain a non-secret reference suitable for review, such as a public
license URL, document identifier, or owner-controlled evidence record ID.

## Generate the packet

Run the generator against current read-only fixtures:

```powershell
python scripts/checks/build_image_provenance_review.py `
  --entity-id <entity-id> `
  --image-path /img/entities/<entity-id>.webp `
  --output outputs/image-provenance-review.json
```

Expected current summary:

```text
{"missingRequirementCount": 3, "mutationAllowed": false, "status": "ready_for_owner_review"}
```

To evaluate a proposed photo-ledger file without changing repository data:

```powershell
python scripts/checks/build_image_provenance_review.py `
  --entity-id <entity-id> `
  --image-path /img/entities/<entity-id>.webp `
  --photo-ledger C:\path\to\review-photos.json `
  --output .tmp\image-provenance-review.json
```

The packet records `inputs.photoLedger.sha256` as the exact input file's byte
digest. `canonicalEvidenceSha256` is a separately named digest of canonicalized
emitted rows that match both `prov-1` and its target image. Reordering matching
rows or changing unrelated/unused ledger content does not change this canonical
identity or the selected evidence. Those edits still change the truthful raw
input byte hash and may therefore change packet bytes. Generating twice from
the same exact input remains byte-identical. Packet JSON is UTF-8, uses LF
newlines on every platform, and ends in exactly one LF.

The generator refuses output paths that collide with any input or with the
protected SQLite database's `-wal`, `-shm`, `-journal`, and
`.reconciliation.lock` paths. It must never be used to create or replace those
files.

## Catalog-wide media truth inventory

Build the inventory from the staged candidate only; never point this command at
the live JSON or SQLite paths:

```powershell
python scripts/checks/build_media_truth_inventory.py `
  --data .tmp/media-truth-candidate/candidate/data.json `
  --asset-root .tmp/media-truth-candidate/candidate/public/img/entities `
  --truth docs/standards/batch-21-media-truth.json `
  --output outputs/media-truth-inventory-2026-09-25.json
```

The output is a deterministic, LF-only, sorted-key inventory with one row per
candidate entity. It classifies only explicit truth-manifest and rights
evidence; file size, filenames, visual resemblance, and mutable dates never
upgrade a row. Unknown records are quarantined, missing documentary evidence is
reported for owner review, and every row has `proposedMutation: null`. The
inventory always declares `mutationAllowed: false` and is evidence for review,
not an apply or publication authorization. Run it twice and compare the output
bytes before attaching it to an owner-review package.

## Owner review checklist

- Confirm the URL resolves to the exact image or its authoritative publication.
- Confirm the credited author and publication match the evidence.
- Confirm the rights statement explicitly permits this project's re-host use.
- Confirm the local WebP is the same work covered by that permission.
- Confirm the UI visibly renders author and source credit.
- Record an explicit owner decision before preparing any separate data proposal.

Even when every requirement is satisfied, the packet remains
`mutationAllowed: false`. Applying data requires a separately reviewed and
explicitly approved procedure; this runbook does not provide one.

`R10.6` is a necessary constitutional check, not publication approval. Its
three immutable compatibility manifests are tied to the 2026-09-21 snapshot:
`r10.6-legacy-image-license-ids.txt` covers exact IDs for legacy copyright
labels, `r10.6-legacy-generic-url-ids.txt` covers exact IDs whose historical
generic public citation remains compatible, and `r10.6-image-url-debt.txt`
covers exact IDs allowed to omit an image-specific URL. Adding an ID requires a
reviewed policy change to the whole manifest; mutable record dates are
untrusted input and never establish legacy eligibility. Generic entity
citations and legacy copyright labels are still not accepted as image-specific
evidence for unlisted IDs. Clearing `R10.6` never supplies the packet's
additional traceable permission evidence and never authorizes owner approval,
mutation, or publication.

When a requested entity is absent but is listed in the reviewed deletion
manifest, the generator emits a controlled `target_absent` packet with
`mutationAllowed: false` and `supersededBy: "batch-21-media-truth-v1"`.

## Verification

```powershell
python -m pytest -q --basetemp .tmp/pytest tests/checks/test_build_image_provenance_review.py
python -m ruff check scripts/checks/build_image_provenance_review.py scripts/checks/provenance_evidence_policy.py scripts/checks/provenance_url_policy.py tests/checks/test_build_image_provenance_review.py
python -m py_compile scripts/checks/build_image_provenance_review.py scripts/checks/provenance_evidence_policy.py scripts/checks/provenance_url_policy.py
python scripts/checks/run_hard.py --all
```

The final hard check is expected to continue reporting `R10.6` until genuine,
owner-reviewed URL and rights evidence is incorporated through an authorized
data change.
