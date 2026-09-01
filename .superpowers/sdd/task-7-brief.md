### Task 7: Community state machine, scheduled worker và moderation CAS (WS-2)

**Findings:** F-42, F-49; supports F-55 and F-31/F-36 topology proof.

**Files:**
- Create: `agent/control_plane/concurrency.py`, `agent/tests/test_state_cas.py`
- Modify: `agent/community/api.py`, `agent/community/admin_api.py`, `agent/scheduler.py`, `agent/ratelimit.py`
- Test: `agent/tests/test_case_contention_postgres.py`, community/admin/moderation/scheduler tests

**Interfaces:**
- `IdempotencyKey(command: str, actor_id: str, key: str)` and `claim_idempotency(transaction, key, request_hash) -> ClaimResult`.
- `cas_transition(transaction, table: str, row_id: str, *, expected_status: str, new_status: str, actor_id: str, reason: str, correlation_id: str) -> TransitionResult`.
- `claim_due(transaction, table: str, *, due_before: datetime, worker_id: str, lease_seconds: int) -> Lease | None`.

- [ ] **Step 1: Write failing concurrency tests**

```python
def test_two_moderators_yield_one_outcome_one_notification(pg_database, moderators, post_id):
    results = run_concurrently(lambda moderator: decide_post(post_id, "approved", moderator), moderators)
    assert sorted(result.status_code for result in results) == [200, 409]
    assert count_audits(pg_database, post_id) == 1
    assert count_notifications(pg_database, post_id) == 1

def test_due_scheduled_post_is_claimed_once_after_restart(pg_database, post_id):
    leases = claim_from_two_workers(pg_database, post_id)
    assert sum(lease is not None for lease in leases) == 1
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_state_cas.py agent/tests/test_case_contention_postgres.py -q`

Expected: FAIL because transitions are last-write-wins and no worker claims `scheduled_at`.

- [ ] **Step 3: Implement shared CAS/lease helper**

Use `UPDATE ... WHERE id = %s AND status = %s AND revision = %s RETURNING id, status, revision`; map zero rows to a deterministic 409 conflict. Store `claimed_by`, `claim_expires_at`, and incremented revision in the same transaction. Idempotency claims use a unique key and request hash; a hash mismatch is a 409, while an exact retry returns the original receipt.

- [ ] **Step 4: Add scheduled-post consumer and moderation transition table**

Implement `task_publish_due_posts(now: datetime, worker_id: str, limit: int = 100) -> BatchResult`. It claims due drafts, rechecks moderation immediately before publication, transitions to `approved`, `rejected` or `publish_failed`, and records retry count/error code. Update appeal/moderation endpoints to use `cas_transition()` and return 409 on conflicts; do not emit notification/audit until the CAS wins.

- [ ] **Step 5: Run GREEN with multi-process evidence**

Run: `python -m pytest agent/tests/test_state_cas.py agent/tests/test_case_contention_postgres.py agent/tests/test_scheduler.py agent/tests/test_moderation*.py -q`

Expected: PASS; concurrent workers create one outcome/audit/notification and a failed publish remains visible with retry metadata.

- [ ] **Step 6: Commit**

```powershell
git add agent/control_plane/concurrency.py agent/community/api.py agent/community/admin_api.py agent/scheduler.py agent/ratelimit.py agent/tests/test_state_cas.py agent/tests/test_case_contention_postgres.py agent/tests/test_scheduler.py agent/tests/test_moderation*.py
git commit -m "fix: close community state transitions with CAS"
```

