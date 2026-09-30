> STATUS: draft; awaiting exact protected-data apply approval.

# Media-truth owner review

This package is read-only evidence. No command below is authorization to mutate
protected data. Every apply or recovery command is marked
`mutationAllowed=false`, `doNotExecute=true`, and `owner_approval_required`.

## Reviewed inputs

- Canonical plan: `outputs/media-truth-plan-2026-09-25.json`.
- Approved-plan bytes: `.tmp/media-truth-approved/media-truth-plan-approved.json`.
- Candidate: `.tmp/media-truth-stage-test-4/candidate/stage-result.json`.
- Inventory: `outputs/media-truth-inventory-2026-09-25.json`.
- Task 9 artifact manifest: `.tmp/media-truth-artifacts/first/manifest.json` (the
  recorded artifact is `manifest.json`, not the illustrative `artifact-manifest.json`).
- Reviewed backup: `.tmp/media-truth-backups-phase-1/20260929-054438-before-media-truth-review`.

## Evidence commands

```powershell
python scripts/backup_data.py --target local --out-dir .tmp/media-truth-backups-phase-1 --label before-media-truth-review --keep 50 --max-age-days 3650
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

## Exact inert commands from the generated package

Reviewed backup: `.tmp/media-truth-backups-phase-1/20260929-054438-before-media-truth-review`; manifest is bound by `backupProcedure.manifestSha256` in the generated JSON.

```text
# mutationAllowed=false doNotExecute=true owner_approval_required
python scripts/checks/apply_data_reconciliation.py --plan C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.tmp\media-truth-approved\media-truth-plan-approved.json --sqlite C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\agent\data\vinhlong360.db --json C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\web\data.json --sqlite-backup .tmp\media-truth-backups-phase-1\20260929-054438-before-media-truth-review\vinhlong360.db --json-backup .tmp\media-truth-backups-phase-1\20260929-054438-before-media-truth-review\data.json --plan-sha256 aa5cbaec34c758e8b67f27ca943461c31d2d27bf661d4e8e013334892edcb37b --lock-path C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.tmp\media-truth-approved\.reconciliation.lock --journal-path C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.tmp\media-truth-approved\media-truth-apply-journal.json --maintenance-window --confirm-phase-b --allow-live-protected-inputs

# mutationAllowed=false doNotExecute=true owner_approval_required
python scripts/checks/apply_data_reconciliation.py --recover-phase-b-journal --journal-path C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.tmp\media-truth-approved\media-truth-apply-journal.json --lock-path C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot\.tmp\media-truth-approved\.reconciliation.lock --sqlite-backup .tmp\media-truth-backups-phase-1\20260929-054438-before-media-truth-review\vinhlong360.db --json-backup .tmp\media-truth-backups-phase-1\20260929-054438-before-media-truth-review\data.json
```

Stop if any digest, count, backup manifest, protected hash, sidecar, finding, or
authorization marker differs. These strings are evidence only and must not be
executed without explicit owner approval.
