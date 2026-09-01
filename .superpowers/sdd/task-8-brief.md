### Task 8: Entity mutation audit và image approval saga (WS-2)

**Findings:** F-44, F-47; supports F-12, F-32 and F-53-style external side effects.

**Files:**
- Create: `agent/control_plane/saga.py`, `agent/tests/test_media_saga.py`
- Modify: `agent/entities/admin_api.py`, `agent/database.py`, `agent/image_suggestions.py`, `agent/storage.py`, `agent/entities/api.py`
- Create: `agent/tests/test_media_gallery.py`, `agent/tests/test_media_saga.py`
- Test: `agent/tests/test_admin_mutations.py`, `agent/tests/test_media_policy.py`

**Interfaces:**
- `SagaStep(name: str, run: Callable[[], StepReceipt], compensate: Callable[[StepReceipt], None])`.
- `run_saga(steps: Sequence[SagaStep], *, idempotency_key: str) -> SagaReceipt`.
- `approve_image_suggestion(suggestion_id: str, actor_id: str, *, idempotency_key: str) -> SagaReceipt`.

- [ ] **Step 1: Write failing audit/saga tests**

```python
def test_delete_relationship_and_bulk_mutation_have_before_after_audit(pg_database):
    mutate_all_entity_paths(pg_database, actor_id="admin-1", reason="correction")
    events = load_entity_audit(pg_database)
    assert all(event.actor_id == "admin-1" and event.reason == "correction" for event in events)
    assert all(event.before is not None and event.after is not None for event in events)

def test_image_upload_failure_compensates_object_and_retry_is_idempotent(fake_storage, pg_database):
    fake_storage.fail_after_upload_once = True
    first = approve_image_suggestion("s-1", "admin-1", idempotency_key="k-1")
    assert first.status == "failed_compensated"
    assert fake_storage.objects == set()
    second = approve_image_suggestion("s-1", "admin-1", idempotency_key="k-1")
    assert second == first
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_media_saga.py agent/tests/test_admin_mutations.py -q`

Expected: FAIL because several mutation paths have no actor/before/after and image approval has no claim or compensation.

- [ ] **Step 3: Implement audit envelope on every mutation**

Route create/update/delete, image add/remove/upload, place assignment, relationship add/delete, bulk actions, featured toggle and provisional/claim decisions through transaction helpers. Capture the row snapshot before and after, attach actor/reason/correlation/revision, and write audit before commit. Bulk operations return one outcome per item.

- [ ] **Step 4: Implement image saga and status claim**

Claim a pending suggestion with CAS and idempotency key; upload an object containing the suggestion ID/generation; commit entity/media/credit/audit in one database transaction; mark approved only after commit; on later failure delete the object or record `orphan_cleanup_pending`. `mark_status()` must require the current pending status.

- [ ] **Step 5: Run GREEN and failure injection**

Run: `python -m pytest agent/tests/test_media_saga.py agent/tests/test_admin_mutations.py agent/tests/test_media_gallery.py agent/tests/test_media_policy.py -q`

Expected: PASS; each injected failure leaves a visible receipt and no duplicate credit/object/audit after retry.

- [ ] **Step 6: Commit**

```powershell
git add agent/control_plane/saga.py agent/entities/admin_api.py agent/database.py agent/image_suggestions.py agent/storage.py agent/entities/api.py agent/tests/test_media_saga.py agent/tests/test_admin_mutations.py agent/tests/test_media_gallery.py agent/tests/test_media_policy.py
git commit -m "fix: make entity media mutations auditable and compensating"
```

