# Personal Data Erasure Runbook

> STATUS: active safety runbook; every production mutation requires separately scoped approval and immutable backup evidence.

This runbook covers the approved 30-day deletion lifecycle and the historical
file-backed scrub. Production mutation stays disabled until the operator has a
separate approval for the exact step.

## Guardrails

- Account erasure remains audit-only until the activation gate is approved.
- PostgreSQL is authoritative; do not substitute SQLite for production evidence.
- Never run the scrub against a live data directory without a completed backup
  and an immutable backup evidence file.
- The legacy scrub tool targets only its declared store inventory and exact
  structured owner fields. It does not perform recursive deletion or global
  UUID/string replacement.

## Sequence

1. **Backup.** Run the approved backup procedure and save the resulting manifest
   or checksum evidence outside the data root.
2. **Deadline backfill.** Run `python scripts/backfill_erasure_deadlines.py`
   without `--apply` first. Apply only after the PostgreSQL backup gate and a
   separate approval are recorded.
3. **Audit one account.** Keep `ERASURE_AUDIT_ONLY=True`; run
   `python scripts/run_account_erasure.py --limit 1` and inspect the subject-free
   report.
4. **Activate one account.** With explicit approval, provide the backup evidence
   and run the erasure command with `--activate --limit 1`. Verify PostgreSQL and
   every registered external store before increasing the batch size.
5. **Scrub historical files.** First plan without mutation:

   ```powershell
   python scripts/scrub_legacy_personal_data.py `
     --owner-id user:REDACTED `
     --root agent/data
   ```

   Review the store/file counts and digests. Then, only after separate approval,
   apply with the exact backup evidence and write the sealed manifest:

   ```powershell
   python scripts/scrub_legacy_personal_data.py `
     --owner-id user:REDACTED `
     --root agent/data `
     --apply `
     --backup-evidence C:\secure\backup-manifest.json `
     --manifest C:\secure\legacy-scrub-manifest.json
   ```

6. **Verify.** Confirm the manifest reports zero remaining owner references and
   zero PII findings, inspect before/after digests, and retain only the manifest
   and operational evidence. Do not commit raw backup files or scrubbed data.
7. **Normal batches.** Only after the single-account verification is accepted,
   enable normal erasure batches and continue monitoring overdue/failure metrics.

## Recovery

If a digest mismatch, parser error, backup-gate failure, or non-zero post-scrub
sentinel occurs, stop. Preserve the immutable plan and evidence, restore from the
backup if mutation has started, and open a review before retrying.
