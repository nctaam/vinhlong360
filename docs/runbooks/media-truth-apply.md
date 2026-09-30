> STATUS: draft; awaiting exact protected-data apply approval.

# Media-truth owner review

This package is read-only evidence. No command below is authorization to mutate
protected data. Every apply or recovery command is marked
`mutationAllowed=false`, `doNotExecute=true`, and `owner_approval_required`.

## Reviewed inputs

- Review-source plan: `outputs/media-truth-plan-2026-09-25.json`.
- Approved plan: `.tmp/media-truth-approved/media-truth-plan-approved.json`.
- Review-source file SHA-256: `aa5cbaec34c758e8b67f27ca943461c31d2d27bf661d4e8e013334892edcb37b`.
- Approved-plan file SHA-256: `524f0d18d48bebfc8cc768b60ecc5bfdeb7854cf8dc9ed04c3113c3ec0a106f6`.
- Approved-plan canonical SHA-256: `39d55df5e10897165dcdb2410def7ed1666b054d8e97e4818ea726bbb4b7a032`.
- Controller owner marker: `owner-approved-2026-09-30-media-truth-phase-1-review-498ac0b8d5349f79`.
- Candidate: `.tmp/media-truth-stage-test-4/candidate/stage-result.json`.
- Inventory: `outputs/media-truth-inventory-2026-09-25.json`.
- Task 9 artifact manifest: `.tmp/media-truth-artifacts/first/manifest.json` (the
  recorded artifact is `manifest.json`, not the illustrative `artifact-manifest.json`).
- Reviewed exact backup: `.tmp/media-truth-backups-phase-1/20260930-143449-before-media-truth-apply-review-exact`.
- Exact backup manifest SHA-256: `af7937bee236ec4338716080887c931dbef9a09a855438d6547b060439c6be86`.
- Exact backup `data.json` SHA-256: `8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f`.
- Exact backup `vinhlong360.db` SHA-256: `ea83864990cf8455061b2436f072c097bc7011f56428c5ba3ba43bcd66fb78a4`.

## Evidence commands

```powershell
python scripts/backup_data.py --target local --out-dir .tmp/media-truth-backups-phase-1 --label before-media-truth-apply-review-exact --keep 50 --max-age-days 3650 --require-byte-exact-sqlite
python scripts/checks/build_media_truth_plan.py --output outputs/media-truth-plan-2026-09-25.json
python scripts/checks/stage_data_reconciliation.py --plan outputs/media-truth-plan-2026-09-25.json --asset-root web-nuxt/public/img/entities --output-dir .tmp/media-truth-candidate
```

The backup command is a regeneration command only; it must not overwrite the
reviewed snapshot. Known external fixture truth-debt remains documented for
`https://example.test/image-1.webp` and `lang-nghe-san-xuat-chi-xo-dua`.

## Owner gate

The review builder rejects open Critical/Important findings, count drift from
`40/1/37/2/6/0`, protected hash drift, backup mismatch, incomplete artifact
member hashes, non-deterministic candidates, malformed evidence, and any true
authorization marker. It never executes the rendered commands.

Use only the exact command and recovery command recorded in
`outputs/media-truth-review-2026-09-25.json`; do not guess a journal or lock path.
The command now binds the canonical approved-plan digest, not the review-source
file digest. This changed exact digest and command require a new owner approval;
the earlier approval package does not authorize execution.

## Exact inert commands from the generated package

Reviewed exact backup: `.tmp/media-truth-backups-phase-1/20260930-143449-before-media-truth-apply-review-exact`; manifest is bound by `backupProcedure.manifestSha256` in the generated JSON.

```text
# mutationAllowed=false doNotExecute=true owner_approval_required
python scripts/checks/apply_data_reconciliation.py --plan C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.tmp\media-truth-approved\media-truth-plan-approved.json --sqlite C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\agent\data\vinhlong360.db --json C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\web\data.json --sqlite-backup .tmp\media-truth-backups-phase-1\20260930-143449-before-media-truth-apply-review-exact\vinhlong360.db --json-backup .tmp\media-truth-backups-phase-1\20260930-143449-before-media-truth-apply-review-exact\data.json --plan-sha256 39d55df5e10897165dcdb2410def7ed1666b054d8e97e4818ea726bbb4b7a032 --lock-path C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.tmp\media-truth-approved\.reconciliation.lock --journal-path C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.tmp\media-truth-approved\media-truth-apply-journal.json --maintenance-window --confirm-phase-b --allow-live-protected-inputs

# mutationAllowed=false doNotExecute=true owner_approval_required
python scripts/checks/apply_data_reconciliation.py --recover-phase-b-journal --journal-path C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.tmp\media-truth-approved\media-truth-apply-journal.json --lock-path C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.tmp\media-truth-approved\.reconciliation.lock --sqlite-backup .tmp\media-truth-backups-phase-1\20260930-143449-before-media-truth-apply-review-exact\vinhlong360.db --json-backup .tmp\media-truth-backups-phase-1\20260930-143449-before-media-truth-apply-review-exact\data.json
```

Stop if any digest, count, backup manifest, protected hash, sidecar, finding, or
authorization marker differs. These strings are evidence only and must not be
executed without explicit owner approval.
