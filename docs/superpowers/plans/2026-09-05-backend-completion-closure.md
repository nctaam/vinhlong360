# Backend Completion Closure Implementation Plan

> STATUS (2026-09-05): active — kế hoạch đang được thực thi theo từng task, giữ nguyên NO_GO/BLOCKED cho tới khi có evidence hợp lệ.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Đưa backend từ trạng thái correctness cục bộ tốt nhưng release bị BLOCKED đến trạng thái có boundary dữ liệu nhất quán, concurrency an toàn, side-effect có thể truy vết và evidence staging đủ để ra quyết định pilot trung thực.

**Architecture:** Giữ modular monolith với PostgreSQL là authority cho state dùng chung và API contract versioned cho frontend độc lập. Không tách microservice trong đợt này. Mutation quan trọng đi qua transaction, audit envelope, idempotency/CAS, projection generation và outbox/saga; claim release phải có receipt tái lập và phân biệt local disposable proof với production-equivalent proof.

**Tech Stack:** Python 3.14, FastAPI, Pydantic, PostgreSQL/psycopg2, pytest, Docker Compose, JSONL chỉ cho legacy/append-only sink có registry, Nuxt 4 contract consumer, PowerShell/Git Bash release harness, Nginx/proxy staging.

## Global Constraints

- Giữ pilot acceptance = NO_GO và release verifier = BLOCKED cho tới khi từng gate có evidence hợp lệ.
- Không deploy, push, sửa production secret/data, thêm dịch vụ trả phí hoặc chạy destructive data command trong kế hoạch này.
- PostgreSQL là authority cho UGC, reports, cases, identity, scheduler lease và lifecycle receipts; SQLite chỉ phục vụ local deterministic tests.
- Additive-first: thêm schema/adapter/reader trước; chỉ chuyển authority sau khi dual-read/verification chứng minh parity.
- Không coi focused SQLite, mock provider, một process hoặc HTTP 200 là bằng chứng production.
- Trước migration/data cleanup: chạy python scripts/backup_data.py cho local fixture và pg_dump cho disposable/staging; lưu checksum backup.
- Mỗi task kết thúc bằng test riêng, python scripts/checks/run_hard.py --all, git diff --check và một commit nhỏ.
- Không chỉnh frontend layout/visual implementation; chỉ cập nhật contract types/tests khi cần giữ API compatibility.

## Hiện trạng và phạm vi còn lại

15 task proof-first đã hoàn tất: evidence verifier, authority registry nền, contract foundation, case transaction/CAS, lifecycle receipts, generation/cache, media compensation, cross-worker proof, scanner/legal/design gates và shared JSONL writer. PostgreSQL disposable đã có proof cục bộ cho một số P1.

Khoảng trống còn thật sự mở:

1. POST /api/report nhận target giả, không canonicalize/dedup/idempotency; report authority chia giữa JSONL và PostgreSQL.
2. Scheduler khởi động trong mỗi process; _scheduler_lock chỉ bảo vệ một process, nhiều task chưa có DB lease/receipt.
3. SMS outbox là at-least-once; eSMS không nhận idempotency token, crash sau provider accept trước commit có thể gửi trùng.
4. Image suggestion dùng check-then-insert; migration chưa có unique constraint cho pending candidate.
5. public_api.py import private internals của community.api; vector_search có nguy cơ tạo hai singleton.
6. Chưa có evidence production-equivalent cho browser/proxy, multi-process, HA/failover, backup-restore-checksum, rollback, provider/object sandbox và alert receiver.
7. docs/HANDOFF.md và authority snapshot còn stale; untracked test artifact phải được phân loại trước release bundle.

## File Map

- Create: agent/reports/__init__.py, agent/reports/models.py, agent/reports/service.py, agent/reports/repository.py.
- Create: agent/scheduler_control.py, agent/provider_receipts.py.
- Create: config/report-authority.json.
- Create: agent/tests/test_report_authority.py, agent/tests/test_report_concurrency_postgres.py.
- Create: agent/tests/test_scheduler_control.py, agent/tests/test_scheduler_multiprocess_postgres.py.
- Create: agent/tests/test_provider_ambiguity.py, agent/tests/test_outbox_provider_contract.py.
- Create: agent/tests/test_image_suggestions_concurrency_postgres.py.
- Create: tests/checks/test_module_boundaries.py, tests/checks/test_lifecycle_registry.py.
- Create: tests/integration/test_staging_evidence_contract.py.
- Create: scripts/ops/probe_multiprocess_scheduler.py, scripts/ops/probe_provider_sandbox.py, scripts/ops/probe_proxy_contract.py.
- Modify: agent/public_api.py, agent/admin.py, agent/community/api.py, agent/community/admin_api.py, agent/data_lifecycle.py, agent/erasure.py.
- Modify: agent/scheduler.py, agent/server.py, agent/config.py, agent/database.py.
- Modify: agent/cases/outbox.py, agent/sms_provider.py, agent/cases/store.py.
- Modify: agent/image_suggestions.py, agent/migrations/005_image_suggestions.sql.
- Modify: agent/features.py, agent/semantic_cache.py, agent/vector_search.py.
- Modify: config/lifecycle-registry.json, config/release-authority.json, docs/HANDOFF.md, docs/ROADMAP.md, docs/audit-toan-du-an-2026-08.md, .superpowers/sdd/progress.md.

---

### Task 0: Baseline freeze và phân loại artifact

**Files:** docs/HANDOFF.md, config/release-authority.json, docs/ROADMAP.md, docs/superpowers/plans/2026-09-05-backend-completion-closure.md; tests/control_plane/test_authority.py, tests/test_release_quality_gates.py.

**Interfaces:**
- python scripts/check_release_authority.py --root . là kiểm tra authority trước mỗi task.
- git status --short phải được ghi vào baseline; artifact chưa phân loại không được đưa vào evidence bundle.

- [ ] Step 1: Ghi baseline hiện tại.

~~~powershell
git rev-parse HEAD
git branch --show-current
git status --short
python scripts/check_release_authority.py --root .
~~~

Expected: branch codex/correction-case-pilot; authority báo STALE hoặc BLOCKED rõ ràng, không che giấu.

- [ ] Step 2: Viết RED cho stale snapshot và untracked artifact.

~~~python
def test_untracked_artifact_cannot_enter_release_bundle(tmp_path):
    report = build_authority_report(tmp_path, tracked_paths={"docs/HANDOFF.md"})
    assert report.status == "BLOCKED"
    assert "untracked" in " ".join(report.mismatches)
~~~

Run: python -m pytest tests/control_plane/test_authority.py -q. Expected: FAIL cho test mới.

- [ ] Step 3: Cập nhật snapshot có provenance.

docs/HANDOFF.md phải ghi HEAD, branch, ngày đo và lệnh đo thật; config/release-authority.json phải trỏ audit/progress hiện tại. Không xóa agent/.pytest-task15-review-green/; chỉ ghi nhận đây là generated artifact và xử lý ở bước cleanup được owner duyệt.

- [ ] Step 4: GREEN và commit.

~~~powershell
python -m pytest tests/control_plane/test_authority.py tests/test_release_quality_gates.py -q
python scripts/checks/run_hard.py --all
git diff --check
git add docs/HANDOFF.md config/release-authority.json docs/ROADMAP.md docs/superpowers/plans/2026-09-05-backend-completion-closure.md tests/control_plane/test_authority.py tests/test_release_quality_gates.py
git commit -m "docs: freeze backend completion baseline"
~~~

---

### Task 1: Canonical report authority, target registry và idempotent intake

**Files:** agent/reports/{__init__.py,models.py,service.py,repository.py}; config/report-authority.json; agent/migrations/087_report_authority.sql; agent/public_api.py; agent/admin.py; agent/community/api.py; agent/community/admin_api.py; agent/data_lifecycle.py; agent/erasure.py; config/lifecycle-registry.json; agent/tests/test_report_authority.py; agent/tests/test_report_concurrency_postgres.py.

**Interfaces:**

~~~python
class ReportService:
    def create(self, request: ReportCreate, *, actor: ReportActor,
               idempotency_key: str, correlation_id: str) -> ReportRecord: ...
    def transition(self, report_id: str, *, expected_revision: int,
                   status: ReportStatus, actor: ReportActor,
                   reason: str) -> ReportRecord: ...
~~~

ReportCreate.target_type chỉ nhận entity, facility, post, comment, user, stale_field; target phải tồn tại hoặc trả 404 target_not_found. Không coerce giá trị lạ thành other. Bảng reports hiện hữu giữ cột khóa chính id; ReportRecord.report_id là tên API ánh xạ từ id. Unique key là actor_scope + idempotency_key; transition dùng revision CAS.

- [ ] Step 1: RED cho target giả, replay và race.

~~~python
def test_unknown_target_type_is_rejected(client):
    response = client.post("/api/report", json={"target_id": "x", "target_type": "bogus", "reason": "x"})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_target_type"

def test_same_report_idempotency_key_replays_one_record(report_service):
    first = report_service.create(request(), actor=actor(), idempotency_key="r-1", correlation_id="c-1")
    second = report_service.create(request(), actor=actor(), idempotency_key="r-1", correlation_id="c-2")
    assert second.report_id == first.report_id
~~~

Run: python -m pytest agent/tests/test_report_authority.py -q. Expected: FAIL vì service chưa tồn tại.

- [ ] Step 2: Mở rộng schema/repository hiện hữu theo hướng additive.

Migration 087 không tạo lại bảng reports. Nó giữ id UUID PRIMARY KEY hiện hữu; đổi reporter_id thành nullable để nhận báo cáo ẩn danh; bổ sung actor_scope, reporter_hash, detail, contact_ciphertext, field, revision, idempotency_key, updated_at, resolved_by, resolved_at, correlation_id, source_channel và legacy_locator. CHECK target_type được mở rộng có stale_field; JSONL open được chuẩn hóa thành pending khi import. Tạo unique index trên actor_scope + idempotency_key, unique partial index trên legacy_locator và index target_type + target_id + status.

- [ ] Step 3: Chuyển writers sang service.

public_api.submit_report, report_stale_field và community report handlers gọi cùng ReportService.create. admin.info_report_action gọi transition với report_id + expected_revision. JSONL chỉ còn adapter đọc/import lịch sử sau cutover marker.

- [ ] Step 4: Nối lifecycle/erasure.

Nâng cấp hai entry reports và reports-jsonl đã có trong config/lifecycle-registry.json; export trả metadata tối thiểu, contact redact theo policy, audit giữ actor/reason/revision; không export secret, IP raw hoặc bearer token.

- [ ] Step 5: GREEN trên SQLite và disposable PostgreSQL.

~~~powershell
python -m pytest agent/tests/test_report_authority.py -q
$env:VL360_TEST_DATABASE_URL = "postgresql://...loopback-disposable..."
python -m pytest agent/tests/test_report_concurrency_postgres.py agent/tests/test_case_legacy_reconciliation_postgres.py -q
python scripts/checks/run_hard.py --all
~~~

Expected: invalid target, duplicate và revision race deterministic; PostgreSQL chứng minh chỉ một row tạo và một transition thắng.

- [ ] Step 6: Commit.

~~~powershell
git add agent/reports agent/migrations/087_report_authority.sql agent/public_api.py agent/admin.py agent/community/api.py agent/community/admin_api.py agent/data_lifecycle.py agent/erasure.py config/report-authority.json config/lifecycle-registry.json agent/tests/test_report_authority.py agent/tests/test_report_concurrency_postgres.py
git commit -m "feat: establish canonical report authority"
~~~

---

### Task 2: Distributed scheduler lease và execution receipt

**Files:** agent/scheduler_control.py; agent/migrations/088_scheduler_leases.sql; agent/scheduler.py; agent/server.py; agent/config.py; agent/database.py; agent/tests/test_scheduler_control.py; agent/tests/test_scheduler_multiprocess_postgres.py; scripts/ops/probe_multiprocess_scheduler.py.

**Interfaces:**

~~~python
def claim_task_slot(db, *, task_name: str, slot_key: str, owner_id: str,
                    now: datetime, lease_seconds: int) -> LeaseClaim: ...
def finish_task_slot(db, *, lease_id: str, outcome: str,
                     finished_at: datetime, receipt: dict) -> None: ...
~~~

slot_key theo interval UTC, owner_id chứa hostname/process UUID. LeaseClaim.acquired=False là trạng thái bình thường khi replica khác giữ lease.

- [ ] Step 1: RED single-process/two-owner race.

~~~python
def test_only_one_owner_claims_a_task_slot(store):
    first = claim_task_slot(store, task_name="admin-digest", slot_key="2026-09-05T08:00Z", owner_id="a", now=NOW, lease_seconds=60)
    second = claim_task_slot(store, task_name="admin-digest", slot_key="2026-09-05T08:00Z", owner_id="b", now=NOW, lease_seconds=60)
    assert first.acquired is True
    assert second.acquired is False
~~~

Run: python -m pytest agent/tests/test_scheduler_control.py -q. Expected: FAIL.

- [ ] Step 2: Tạo schema.

088 tạo scheduler_task_slots với khóa task_name + slot_key, owner_id, lease_id, lease_until, status, started_at, finished_at, outcome, receipt_json; index lease_until.

- [ ] Step 3: Bọc ScheduledTask.run() bằng shared claim.

Tính slot, claim trước callback, ghi receipt khi kết thúc, release/expire trong finally. publish-due-posts giữ CAS hiện có; CAS là guard domain thứ hai. Task local/dev phải có topology local và tắt trên production khi thiếu shared DB.

- [ ] Step 4: GREEN/multiprocess.

~~~powershell
python -m pytest agent/tests/test_scheduler_control.py -q
$env:VL360_TEST_DATABASE_URL = "postgresql://...loopback-disposable..."
python -m pytest agent/tests/test_scheduler_multiprocess_postgres.py -q
python scripts/ops/probe_multiprocess_scheduler.py --workers 2 --slots 20
~~~

Expected: 20 slot chỉ có 20 success receipt, lease expiry cho phép takeover một lần và không duplicate side effect.

- [ ] Step 5: Commit.

~~~powershell
git add agent/scheduler_control.py agent/migrations/088_scheduler_leases.sql agent/scheduler.py agent/server.py agent/config.py agent/database.py agent/tests/test_scheduler_control.py agent/tests/test_scheduler_multiprocess_postgres.py scripts/ops/probe_multiprocess_scheduler.py
git commit -m "fix: make scheduled work replica-safe"
~~~

---

### Task 3: Outbox/provider ambiguity và SMS delivery contract

**Files:** agent/provider_receipts.py; agent/migrations/089_provider_delivery_receipts.sql; agent/cases/outbox.py; agent/sms_provider.py; agent/cases/store.py; agent/config.py; config/lifecycle-registry.json; agent/tests/test_provider_ambiguity.py; agent/tests/test_outbox_provider_contract.py.

**Interfaces:**

~~~python
class ProviderCapabilities(TypedDict):
    idempotency: bool
    reconciliation: bool

class ProviderReceipt(TypedDict):
    operation_id: str
    provider: str
    state: Literal["accepted", "rejected", "ambiguous", "unknown"]
    provider_reference: str | None
    observed_at: str
~~~

EsmsProvider.capabilities.idempotency = False cho tới khi provider contract thực tế chứng minh ngược lại. Timeout sau request có thể đã được chấp nhận phải chuyển ambiguous, không retry mù.

- [ ] Step 1: RED crash-window.

~~~python
def test_timeout_after_provider_accept_is_ambiguous_not_retryable(outbox, provider):
    provider.send_then_raise_timeout = True
    result = dispatch_case_outbox(now=NOW)
    row = outbox.load_one()
    assert row.status == "ambiguous"
    assert result.retried == 0
~~~

Run: python -m pytest agent/tests/test_provider_ambiguity.py -q. Expected: FAIL.

- [ ] Step 2: Tạo durable receipt/reconciliation schema.

089 tạo unique operation_id, provider, state, provider reference, request hash, timestamps và reconciliation status; không lưu plaintext phone/message.

- [ ] Step 3: Tách transport result khỏi business outcome.

sms_provider.py trả accepted/rejected/ambiguous/unknown kèm capability; cases/outbox.py settle sent chỉ khi accepted rõ ràng, pending chỉ khi chắc chắn chưa gửi, ambiguous cho lỗi không xác định. delivery_key trở thành operation_id nội bộ và log sanitized.

- [ ] Step 4: Thêm admin reconciliation.

Admin-only path chỉ liệt kê ambiguous rows, không tự gửi lại; mọi quyết định resolve/retry thủ công phải audit actor/reason.

- [ ] Step 5: GREEN và commit.

~~~powershell
python -m pytest agent/tests/test_provider_ambiguity.py agent/tests/test_outbox_provider_contract.py agent/tests/test_case_outbox.py -q
python scripts/checks/run_hard.py --all
git add agent/provider_receipts.py agent/tests/test_provider_ambiguity.py agent/tests/test_outbox_provider_contract.py agent/migrations/089_provider_delivery_receipts.sql agent/cases/outbox.py agent/sms_provider.py agent/cases/store.py agent/config.py config/lifecycle-registry.json
git commit -m "fix: make provider ambiguity explicit"
~~~

---

### Task 4: Image suggestion unique/CAS integrity

**Files:** agent/migrations/090_image_suggestion_pending_unique.sql; agent/migrations/005_image_suggestions.sql; agent/image_suggestions.py; agent/tests/test_image_suggestions_concurrency_postgres.py; agent/tests/test_admin_mutations.py.

**Interfaces:**
- create_batch() dùng INSERT ... ON CONFLICT DO NOTHING cho entity_id + candidate_url khi status=pending.
- mark_status() giữ WHERE status=pending và trả False khi state đã đổi.

- [ ] Step 1: RED race.

~~~python
def test_two_workers_create_one_pending_candidate(pg_db):
    results = run_two_workers(lambda: create_batch([{"entity_id": "e1", "candidate_url": "https://x/a.jpg"}]))
    assert sum(result["created"] for result in results) == 1
    assert count_pending(pg_db, "e1", "https://x/a.jpg") == 1
~~~

- [ ] Step 2: Kiểm tra duplicate trước migration.

~~~sql
SELECT entity_id, candidate_url, COUNT(*)
FROM image_suggestions
WHERE status = 'pending'
GROUP BY entity_id, candidate_url
HAVING COUNT(*) > 1;
~~~

Nếu có duplicate disposable/staging, giữ row cũ nhất, ghi cleanup receipt, rồi mới tạo partial unique index; production cleanup chỉ sau backup và owner approval.

- [ ] Step 3: Thêm constraint và đổi insert.

Tạo unique partial index trên entity_id + candidate_url với điều kiện status='pending'; SQLite dùng unique index tương đương. Thay check-then-insert bằng conflict-safe insert và đọc rowcount.

- [ ] Step 4: GREEN và commit.

~~~powershell
python -m pytest agent/tests/test_image_suggestions_concurrency_postgres.py agent/tests/test_admin_mutations.py -q
python scripts/checks/run_hard.py --all
git diff --check
git add agent/migrations/090_image_suggestion_pending_unique.sql agent/migrations/005_image_suggestions.sql agent/image_suggestions.py agent/tests/test_image_suggestions_concurrency_postgres.py agent/tests/test_admin_mutations.py
git commit -m "fix: enforce image suggestion pending uniqueness"
~~~

---

### Task 5: Làm sạch module boundary và singleton topology

**Files:** agent/community/contracts.py; tests/checks/test_module_boundaries.py; agent/tests/test_singleton_identity.py; agent/public_api.py; agent/community/api.py; agent/features.py; agent/semantic_cache.py; agent/vector_search.py.

**Interfaces:**

~~~python
def collect_new_entities(*, since: datetime, limit: int = 100) -> list[dict]: ...
def feed_new_since(*, since: datetime, limit: int = 100) -> list[dict]: ...
def is_blocked(user_id: str, target_id: str) -> bool: ...
~~~

public_api.py chỉ import symbols từ community.contracts, không import _block_sql, _mute_sql hoặc private collector. agent.vector_search là canonical namespace; flat import chỉ ở explicit script compatibility path.

- [ ] Step 1: RED boundary scan.

~~~python
def test_public_api_does_not_import_private_community_symbols():
    source = Path("agent/public_api.py").read_text(encoding="utf-8")
    assert "from community.api import _" not in source

def test_semantic_cache_and_features_share_vector_singleton():
    import agent.features as features
    import agent.semantic_cache as cache
    assert features.embedding_store is cache.embedding_store
~~~

Run: python -m pytest tests/checks/test_module_boundaries.py agent/tests/test_singleton_identity.py -q. Expected: FAIL trên topology hiện tại.

- [ ] Step 2: Tạo facade, rewire imports, thêm assertion sys.modules không đồng thời có vector_search và agent.vector_search sau app boot.

- [ ] Step 3: GREEN route regression.

~~~powershell
python -m pytest tests/checks/test_module_boundaries.py agent/tests/test_singleton_identity.py agent/tests/test_public_api.py agent/tests/test_chat_smoke.py -q
python scripts/checks/run_hard.py --all
git add agent/community/contracts.py tests/checks/test_module_boundaries.py agent/tests/test_singleton_identity.py agent/public_api.py agent/community/api.py agent/features.py agent/semantic_cache.py agent/vector_search.py
git commit -m "refactor: close backend module boundaries"
~~~

---

### Task 6: Lifecycle/retention parity cho report, audit và external sinks

**Files:** config/lifecycle-registry.json; agent/data_lifecycle.py; agent/erasure.py; agent/admin.py; agent/public_api.py; agent/community/admin_api.py; agent/jsonl_store.py; tests/checks/test_lifecycle_registry.py; agent/tests/test_report_lifecycle.py.

**Interfaces:**
- list_lifecycle_sinks() trả reports, admin_audit, case_outbox, provider_receipts, jsonl_legacy_archive, bot_conversations, browser_storage, object_media.
- Mỗi sink khai báo authority, contains_personal_data, export_mode, erasure_mode, retention_days, proof_level.

- [ ] Step 1: RED inventory parity.

~~~python
def test_every_report_sink_has_export_and_erasure_policy():
    sinks = {sink.name: sink for sink in list_lifecycle_sinks()}
    assert sinks["reports"].export_mode == "redacted"
    assert sinks["reports"].erasure_mode in {"redact", "delete"}
    assert sinks["jsonl_legacy_archive"].authority == "legacy-read-only"
~~~

- [ ] Step 2: Registry fail-closed.

Invalid sink, missing retention hoặc authority không hợp lệ phải làm validate_drill_index.py --root . exit 2; không silently skip.

- [ ] Step 3: Nối report service vào export/erasure.

Export chỉ trả report_id, target, reason, status, timestamps, actor pseudonym và redacted detail. Erasure tạo receipt với số row trước/sau; không xóa immutable admin audit nếu policy chỉ cho redact.

- [ ] Step 4: GREEN và commit.

~~~powershell
python -m pytest tests/checks/test_lifecycle_registry.py agent/tests/test_report_lifecycle.py tests/integration/test_ops_control_path.py -q
python scripts/ops/validate_drill_index.py --root .
python scripts/checks/run_hard.py --all
git add config/lifecycle-registry.json agent/data_lifecycle.py agent/erasure.py agent/admin.py agent/public_api.py agent/community/admin_api.py agent/jsonl_store.py tests/checks/test_lifecycle_registry.py agent/tests/test_report_lifecycle.py
git commit -m "fix: make report lifecycle policy explicit"
~~~

---

### Task 7: Staging evidence harness cho boundary chưa chứng minh

**Files:** scripts/ops/probe_multiprocess_scheduler.py; scripts/ops/probe_provider_sandbox.py; scripts/ops/probe_proxy_contract.py; scripts/ops/probe_rollback.py; tests/integration/test_staging_evidence_contract.py; scripts/ops/run_pilot_acceptance.py; scripts/ops/probe_runtime_evidence.py; scripts/ops/restore_drill.py; docker-compose.prod.yml; nginx.conf; docs/runbooks/proof-first-pilot-acceptance.md; config/release-authority.json.

**Interfaces:**
- Mỗi probe tạo receipt JSON có probe_id, head_sha, environment_id, timestamps, exact command, exit code, output SHA-256, test nodeids và verdict.
- Probe không chứa production secret/data; DSN phải disposable/staging và loopback/allowlisted.

- [x] Step 1: RED receipt completeness.

~~~python
def test_staging_receipt_rejects_missing_environment_or_output_hash(tmp_path):
    receipt = {"probe_id": "scheduler", "head_sha": "a" * 40, "verdict": "PASS"}
    assert verify_probe_receipt(receipt).verdict == "BLOCKED"
~~~

- [x] Step 2: Thêm probes.

1. probe_multiprocess_scheduler.py: hai process cùng PostgreSQL, đo duplicate slot.
2. probe_proxy_contract.py: Nginx/staging đến FastAPI đến PostgreSQL, kiểm status, cache headers, authenticated no-store và SSR route.
3. probe_provider_sandbox.py: fake provider accept/timeout/reject, xác minh ambiguous không retry mù.
4. restore_drill.py: backup đến restore DB mới đến checksum bảng/row counts đến receipt.
5. Rollback probe: staged release A đến B đến health fail giả lập đến revert artifact B, không chạm production.

- [x] Step 3: Nối acceptance nhưng giữ fail-closed.

run_pilot_acceptance.py chỉ nâng verdict khi đủ probe receipt hợp lệ. Thiếu browser/proxy, backup-restore, multiprocess hoặc provider evidence phải giữ NO_GO, không biến SKIPPED thành PASS.

- [x] Step 4: GREEN trên disposable/staging.

~~~powershell
python -m pytest tests/integration/test_staging_evidence_contract.py tests/integration/test_probe_runtime_evidence.py -q
python scripts/ops/probe_multiprocess_scheduler.py --workers 2 --slots 20
python scripts/ops/probe_provider_sandbox.py --mode deterministic
python scripts/ops/probe_proxy_contract.py --base-url http://127.0.0.1:8360
python scripts/ops/run_pilot_acceptance.py --root . --evidence-dir artifacts/staging-evidence
~~~

Expected: local disposable probes có thể pass, nhưng acceptance vẫn NO_GO nếu thiếu staging, custody key hoặc human sign-off.

- [x] Step 5: Commit.

~~~powershell
git add scripts/ops/run_pilot_acceptance.py scripts/ops/probe_runtime_evidence.py scripts/ops/restore_drill.py scripts/ops/probe_multiprocess_scheduler.py scripts/ops/probe_provider_sandbox.py scripts/ops/probe_proxy_contract.py tests/integration/test_staging_evidence_contract.py docker-compose.prod.yml nginx.conf docs/runbooks/proof-first-pilot-acceptance.md config/release-authority.json
git commit -m "test: add production-boundary backend evidence probes"
~~~

---

### Task 8: Full verification, documentation truth-sync và release decision

**Files:** docs/HANDOFF.md; docs/ROADMAP.md; docs/audit-toan-du-an-2026-08.md; config/release-authority.json; .superpowers/sdd/progress.md.

**Interfaces:**
- Official backend gate: python scripts/ops/run_backend_regression.py --deadline-seconds 7000.
- Contract gate: python scripts/check_contract_drift.py.
- Hard gate: python scripts/checks/run_hard.py --all.
- Release verifier: python scripts/ops/verify_release_bundle.py --bundle artifacts/pilot-acceptance.json.

- [x] Step 1: Chạy full suite trên cây đứng yên.

Đo disk free và lưu git rev-parse HEAD trước khi chạy; nếu working tree đổi giữa các phase, hủy verdict và chạy lại. Lưu stdout/stderr riêng, checksum từng output.

~~~powershell
python scripts/ops/run_backend_regression.py --deadline-seconds 7000
python scripts/check_contract_drift.py
python scripts/checks/run_hard.py --all
~~~

Expected: failure ngoài allowlist là regression; không dùng số lịch sử 8761 passed làm baseline mới nếu chưa có receipt của HEAD hiện tại.

Kết quả HEAD `edd9c07a`: Phase A hoàn tất với `12448 passed, 65 failed, 822 skipped, 249 deselected, 1 xfailed`. Đây là failure set cần triage, chưa được chấp nhận làm baseline/allowlist mới; full decision vẫn BLOCKED.

- [!] Step 2: Kiểm tra evidence matrix.

Phải có PostgreSQL schema/migration, report race, scheduler multiprocess, provider ambiguity, image suggestion race, browser/proxy, backup-restore-checksum, rollback, alert receiver và lifecycle/erasure; mỗi dòng có command, environment, SHA, verdict, owner.

Matrix hiện còn thiếu production-equivalent browser/proxy, live PostgreSQL multiprocess, backup/restore row-checksum, provider/object reconciliation, staging rollback và alert receiver; local deterministic evidence không được thay thế các dòng này.

- [x] Step 3: Truth-sync tài liệu.

Mỗi finding là closed with local proof, staging proof, unproven hoặc decision required; last_verified_at chỉ cập nhật sau command thật trên HEAD. Giữ NO_GO/BLOCKED nếu P1 hoặc evidence custody còn thiếu.

- [x] Step 4: Final verifier.

~~~powershell
python scripts/ops/run_pilot_acceptance.py --root . --evidence-dir artifacts/pilot-acceptance
python scripts/ops/countersign_pilot_acceptance.py --root . --bundle artifacts/pilot-acceptance.json
python scripts/ops/verify_release_bundle.py --bundle artifacts/pilot-acceptance.json
~~~

Expected: trên laptop hiện tại verdict trung thực vẫn NO_GO/exit 2 nếu thiếu staging, custody key hoặc human sign-off; đó là kết quả đúng.

- [x] Step 5: Commit docs-only truth-sync.

~~~powershell
git add docs/HANDOFF.md docs/ROADMAP.md docs/audit-toan-du-an-2026-08.md config/release-authority.json .superpowers/sdd/progress.md
git commit -m "docs: publish backend completion evidence status"
~~~

## Thứ tự thực hiện và cổng dừng

1. Task 0 bắt buộc trước mọi thay đổi.
2. Task 1 phải hoàn tất trước Task 6 vì lifecycle/report cần một authority thật.
3. Task 2 độc lập với Task 1 nhưng phải xong trước Task 7.
4. Task 3 và Task 4 có thể chạy sau Task 0; không gộp chung migration/commit.
5. Task 5 chỉ refactor boundary sau khi route baseline đã được chụp.
6. Task 6 sau Task 1 và trước Task 8.
7. Task 7 chỉ chạy khi Task 1 đến 6 focused green; thiếu môi trường thì ghi UNAVAILABLE, không thay bằng mock.
8. Task 8 là cổng quyết định, không phải bước đổi màu tài liệu.

## Definition of Done

- API contract/version/schema export không drift; endpoint inventory có auth/cache/idempotency metadata.
- Report, case, identity, moderation và scheduler có authority rõ; không còn writer mới vào JSONL legacy.
- Mọi state transition cạnh tranh có CAS/lease hoặc unique constraint được chứng minh trên PostgreSQL.
- External side effect có operation id, receipt và ambiguous state; không tuyên bố exactly-once nếu provider không hỗ trợ.
- Lifecycle registry phủ report/audit/outbox/provider/object/log/browser sink và export/erasure có receipt.
- Full backend regression trên HEAD hiện tại chạy trên cây đứng yên; lỗi ngoài allowlist = BLOCKED.
- Có staging evidence cho browser/proxy, multi-process, backup/restore/checksum, rollback, provider sandbox và alert receiver.
- HANDOFF, release-authority và ROADMAP cùng trỏ một HEAD/ngày đo; không stale claim.
- Verifier chỉ chuyển khỏi BLOCKED sau countersignature/custody/human decision thực sự tồn tại.

## Self-review

- Spec coverage: report authority, scheduler scale, provider ambiguity, image race, module coupling, lifecycle parity, runtime evidence và release truth-sync đều có task riêng.
- Placeholder scan: các task đều có file, interface, test command và expected outcome cụ thể; không có bước mô tả mơ hồ.
- Type consistency: ReportService.create/transition, claim_task_slot/finish_task_slot, ProviderReceipt và lifecycle sink names nhất quán.
- Scope guard: không bao gồm tách microservice, đổi frontend layout, deploy production, push remote hoặc xử lý secret thật.

Plan complete and saved to docs/superpowers/plans/2026-09-05-backend-completion-closure.md. Two execution options:

1. Subagent-Driven (recommended) — dispatch một worker cho từng task, review hai lớp giữa các task.
2. Inline Execution — thực hiện tuần tự trong session này với checkpoint sau mỗi task.
