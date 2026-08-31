# Proof-First Optimization Plan — Design Spec

> **STATUS:** `written-spec-pending-review`
> **Ngày:** 2026-08-31
> **Parent authority:** `docs/audit-toan-du-an-2026-08.md`
> **Owner:** Service Owner của vinhlong360
> **Supersedes:** none
> **Superseded by:** none

## 1. Mục đích

Spec này chuyển kết quả audit 73 findings thành một thiết kế tối ưu để đóng
P1, tăng độ tin cậy của release evidence và đưa correction-case pilot tới một
trạng thái có thể kiểm chứng. Đây là thiết kế remediation, không phải tuyên bố
production-ready và không tự cấp quyền deploy hay thay đổi dữ liệu production.

### 1.1 In scope

- một evidence/control plane duy nhất cho test, baseline, audit, release và
  Go/No-Go;
- các primitive dùng chung cho contract, generation/cache, clock, lifecycle,
  audit, idempotency và optimistic concurrency;
- đóng 28 P1 theo dependency graph thay vì sửa tuần tự từng file/module;
- acceptance evidence xuyên browser → API → PostgreSQL → worker/provider →
  projection/cache/search → audit/erasure;
- các module đã tách: `cases/`, `identity/`, `community/`, `entities/`,
  `chat/`, `llmops/`, `itineraries/`, `siteops/`;
- kế hoạch rollout additive-first, rollback rõ và không làm mất thay đổi người
  dùng trong worktree.

### 1.2 Out of scope

- thêm feature tăng trưởng, booking, payment, commerce hoặc social surface mới;
- microservices/database-per-domain hoặc rewrite lớn không phục vụ P1;
- tự chốt legal wording, residency, SLA, provider contract hoặc risk acceptance
  thay cho chủ dự án/DPO/luật sư;
- sửa dữ liệu production, xoá sink thật, rotate secret thật hoặc deploy VPS;
- coi focused test SQLite/mocked provider là bằng chứng production;
- mở public indexing trước khi các gate trong spec đạt.

## 2. Bằng chứng hiện tại và phản biện

Audit ngày 2026-08-31 ghi nhận **73 findings** gồm **28 P1** và **45 P2**,
không có P0 được chứng minh. Những rủi ro có tính trung tâm cao nhất là:

- verifier ngoài repo có thể in `HẾT-DIFF` dù artifact có 12 `ERROR` và return
  code chưa được kiểm (F-69);
- baseline/HEAD/rule inventory nằm ở nhiều tài liệu có trạng thái `active` nhưng
  không đồng nhất (F-70);
- audit active còn untracked, nên clone/CI có thể mất artifact quyết định
  (F-71);
- correction, cache, search, publication, erasure và media chưa có một
  generation/lifecycle proof chung (F-01, F-10, F-11, F-32, F-40, F-41,
  F-47, F-49, F-53);
- community/entities có state transition và side effect nhưng thiếu worker,
  CAS, saga compensation hoặc audit đầy đủ (F-42, F-44, F-47, F-49, F-55);
- data/search/timezone có thể làm dữ liệu đúng trở nên không tìm thấy hoặc hiển
  thị sai thời điểm (F-24–F-29, F-33);
- monitoring, backup, restore, deploy và public/legal disclosure chưa khép
  thành một control path (F-13–F-16, F-57–F-62, F-63–F-73).

Phản biện trung tâm: làm xanh từng module riêng lẻ không đủ. Một module chỉ
được coi là đã tối ưu khi ownership, transaction, state transition, auth
metadata, cache generation, external side effect và release evidence đi cùng
một boundary có thể tái lập.

## 3. Mục tiêu và tiêu chí thành công

### 3.1 Mục tiêu bắt buộc

1. Không còn verdict release sai vì parser bỏ qua `ERROR`, collection failure,
   interruption hoặc return code.
2. Một authority duy nhất cho baseline, HEAD, rule inventory, test roster và
   audit artifact; tài liệu quá hạn không được dùng làm evidence.
3. Một mutation correction có thể truy vết cùng `case_id`, `revision`,
   `generation` và `correlation_id` qua mọi consumer liên quan.
4. Mọi P1 có owner, failing test, cross-boundary test, acceptance artifact và
   rollback/failure-path evidence.
5. Closed pilot chỉ mở khi toàn bộ P1 đạt gate; public launch vẫn bị chặn bởi
   các decision/legal/production gates chưa được chủ dự án phê duyệt.

### 3.2 Chỉ số sau tối ưu

| Chỉ số | Điều kiện đạt |
|---|---|
| Evidence completeness | Bundle có outcome counts, nodeids, return code, environment, SHA và checksum |
| Baseline consistency | `CLAUDE`, `ROADMAP`, `HANDOFF`, README/index và audit registry khớp authority + freshness |
| Correction coherence | Browser/API/DB/worker/public projection/cache/search đọc cùng generation sau mutate |
| Erasure coverage | Có inventory export/erase cho PG, JSONL, log, bot, browser, object/CDN và retention-only sinks |
| Concurrency safety | CAS/lease/idempotency test chứng minh chỉ một outcome/side effect thắng |
| Operational readiness | Backup→restore, target→alert, deploy→smoke→rollback đều có artifact độc lập |
| Design/runtime consistency | Token, font, state, density, z-index và accessibility có contract/snapshot theo module |

## 4. Nguyên tắc bất biến

1. **Evidence trước claim:** không dùng câu “xanh”, “đã xoá”, “đã backup” hoặc
   “đã kiểm chứng” nếu artifact chưa chứng minh đúng boundary.
2. **Một authority cho một sự thật:** schema, clock, generation, lifecycle,
   baseline và policy đều có owner/version/expiry.
3. **Additive-first:** thêm registry, manifest, adapter và test trước; không xoá
   đường cũ cho tới khi consumer mới có parity evidence.
4. **Transactional boundary:** business mutation, audit intent và outbox intent
   phải commit cùng transaction hoặc trả failure rõ.
5. **Idempotent by default:** retry không nhân đôi case, decision, credit,
   notification, SMS hoặc object side effect.
6. **Explicit topology:** state process-local, shared hoặc leader-owned phải
   được khai báo; test một process không được đại diện cho multi-worker.
7. **No silent truncation:** export, search, pagination, verifier và dashboard
   phải báo rõ `truncated`, `errors`, `stale` hoặc `degraded`.
8. **Không vượt quyết định con người:** legal, provider at-least-once,
   residency, SLA và public launch cần owner chốt bằng risk acceptance.

## 5. Kiến trúc tối ưu

### 5.1 Control tower và evidence registry

Tạo một release/evidence registry machine-readable (đặt trong vùng release
control hiện hữu, tên cụ thể sẽ được chốt ở implementation plan) với các trường
bắt buộc:

```json
{
  "schema_version": "1",
  "artifact_id": "stable-id",
  "head_sha": "40-hex",
  "branch": "codex/correction-case-pilot",
  "started_at": "UTC timestamp",
  "finished_at": "UTC timestamp",
  "command": "exact command",
  "environment": {
    "os": "",
    "python": "",
    "pytest": "",
    "node": "",
    "database_target": "redacted descriptor",
    "disk_before_bytes": 0,
    "disk_after_bytes": 0
  },
  "outcomes": {
    "passed": 0,
    "failed": 0,
    "errors": 0,
    "skipped": 0,
    "xfailed": 0,
    "collection_errors": 0,
    "interrupted": false,
    "return_code": 0
  },
  "allowlist": [],
  "verdict": "PASS|BLOCKED|UNCLASSIFIED",
  "artifacts": [],
  "output_sha256": "64-hex"
}
```

Verdict `PASS` chỉ hợp lệ khi `failed`, `errors`, `collection_errors` và
`interrupted` đều bằng 0 ngoài allowlist khớp nodeid/prefix; `return_code` phải
bằng 0. `UNCLASSIFIED` luôn chặn release.

### 5.2 Shared primitives

| Primitive | Trách nhiệm | Consumer chính |
|---|---|---|
| Contract registry | schema/version/error mapping FE↔BE và route↔OpenAPI | cases, identity, public API, admin, Nuxt composables |
| Snapshot generation | `entity_id`/generation và invalidation adapter cho L1/L2/Redis/CDN | cases, entities, chat, search, reviews, homepage, itineraries |
| Canonical clock | UTC storage, VN presentation, injectable boundary clock | homepage, feed, chat, MCP, scheduler, seasonal copy |
| Lifecycle registry | export/erase/retention method, owner, secret/content class, sink | identity, reports, logs, bot, browser, object/CDN |
| Audit/event envelope | actor, reason, before/after, correlation, revision, resource | cases, entities, community, admin, siteops |
| Idempotency/CAS helper | atomic command, expected revision, claim/lease, conflict 409 | moderation, image saga, outbox, scheduled post, backup |
| Evidence adapter | test result, browser snapshot, proxy trace, provider receipt | release gate, audit report, Go/No-Go |

Không primitive nào tự trở thành microservice. Mục tiêu là một contract/adapter
có thể test độc lập trong repository hiện tại.

### 5.3 Chuỗi dữ liệu chuẩn

```text
command
  -> contract validation + actor/CSRF/idempotency
  -> transaction (business row + audit + outbox intent)
  -> commit revision/generation
  -> worker/provider side effect with claim/lease
  -> public projection + cache invalidation
  -> cross-consumer read proof
  -> evidence bundle + receipt/incident trail
```

Failure ở mỗi bước phải có problem detail, retry policy, compensation hoặc
`UNCLASSIFIED/BLOCKED`; không trả success nếu chỉ mới ghi một tầng.

## 6. Workstream và dependency graph

Thứ tự dưới đây tối ưu theo `impact × blast-radius × dependency-centrality ×
evidence-gap / effort`, không theo kích thước file.

### WS-0 — Evidence và authority (blocker chung)

**Findings:** F-69, F-70, F-71.

**Deliverable:** verifier versioned trong repo; authority registry cho baseline,
HEAD, rules và audit; artifact checksum/tracking gate; phân loại 12 `ERROR`.

**Exit gate:** một synthetic run có `FAILED + ERROR + return_code=1` trả
`BLOCKED`; một run sạch đầy đủ trả `PASS`; clone/CI tìm thấy đúng audit artifact.

### WS-1 — Trust/lifecycle correction

**Findings:** F-01, F-02, F-06, F-10, F-11, F-12, F-32, F-34, F-38,
F-40, F-41, F-53.

**Modules:** `cases/`, `identity/`, `chat/`, `entities/`, report/bot/storage
adapters và Nuxt correction/settings.

**Deliverable:** contract registry, transactional wiring, evidence temporal/scope
guard, lifecycle inventory, export/erase manifest, generation invalidation,
personalized-cache policy và provider side-effect receipt.

**Exit gate:** browser correction drill và erasure drill truy cùng identifiers
đã băm qua DB/audit/outbox/projection/cache; stale/wrong-scope evidence bị chặn;
retry không tạo duplicate case/SMS/notification.

### WS-2 — State machine, concurrency và media saga

**Findings:** F-42, F-44, F-47, F-49, F-55.

**Modules:** `community/`, `entities/`, moderation, collection, scheduler,
image suggestions.

**Deliverable:** transition table có actor/revision/notification/public state;
worker due có lease/CAS; media approval có claim/idempotency/compensation;
mọi mutation có audit before/after.

**Exit gate:** hai worker/operator chạy đồng thời chỉ tạo một outcome, một audit
và một side effect; scheduled post/appeal/image failure injection có recovery
state nhìn thấy được.

### WS-3 — Data, search, pagination và chronology

**Findings:** F-08, F-09, F-24–F-29, F-33, F-45, F-54, F-56, F-59, F-60,
F-62.

**Modules:** `entities/`, `public_api.py`, `database.py`, `chat/`,
`itineraries/`, data validators và frontend search/detail/feed.

**Deliverable:** canonical `verifiedAt`, accent-insensitive ranking, full-catalog
pagination, one clock, singleton import convention, semantic cache replacement,
quality dashboard truthful status và data warning taxonomy.

**Exit gate:** fixture ở offset >500 vẫn truy cập được; `dua sap` và `dừa sáp`
cho cùng kết quả; boundary 16:59/17:00 UTC thống nhất; mutation rồi đọc detail,
search, chat, review, similar và homepage thấy cùng generation.

### WS-4 — Security, operations và release path

**Findings:** F-03, F-04, F-05, F-07, F-13, F-14, F-15, F-18, F-19, F-31,
F-36, F-50–F-52, F-57–F-61.

**Modules:** `siteops/`, `llmops/`, scheduler, storage, monitoring, CI/CD,
compose, egress và admin routes.

**Deliverable:** fail-closed production config, structured redaction, provider/
egress policy, backup/restore manifest, monitoring target/alert receiver,
staging rollout/rollback, route auth metadata và shared topology preflight.

**Exit gate:** backup artifact restore vào DB rỗng; alert receiver nhận alert;
staging rollout có smoke và rollback; route inventory/OpenAPI biểu diễn đúng
auth/scope/CSRF; no raw PII trong log fixture.

### WS-5 — UX, design-system và legal disclosure

**Findings:** F-16, F-17, F-63–F-68, F-72, F-73.

**Modules:** Nuxt forms/chat/admin, CSS token system, legal pages/content,
contact/support surface.

**Deliverable:** phone verification journey, message chronology, canonical token
and state recipes, admin density/layer registry, cookie inventory và policy
version/changelog; mọi legal claim có owner/risk decision.

**Exit gate:** browser matrix desktop/mobile/keyboard/200%/reduced-motion/
forced-colors không có lỗi blocker; legal pages có version, updated date,
cookie purpose/control và contact owner sau khi DPO/lawyer duyệt.

## 7. Test và evidence strategy

Mỗi finding P1 phải có tối thiểu một bằng chứng ở đúng lớp rủi ro:

| Lớp | Chứng minh | Không được suy ra từ |
|---|---|---|
| Unit/source | invariant, parser, schema, guard | production behavior |
| PostgreSQL integration | migration, transaction, row lock, erasure | SQLite-only fixture |
| Multi-process/chaos | worker race, restart, file/cache contention | `threading.Lock` trong một process |
| Browser/proxy | cookie/CSRF, visibility, cache headers, focus, chronology | source template |
| External-side-effect sandbox | SMS/object/subprocess receipt, retry, compensation | mock không có failure window |
| Release evidence | command, environment, output, checksum, verdict | agent report hoặc summary line |

Mỗi task implementation sau này phải theo TDD:

1. viết test tái hiện lỗi;
2. chạy và ghi failure artifact;
3. sửa tối thiểu;
4. chạy focused + cross-boundary test;
5. cập nhật evidence registry và audit mapping;
6. commit một đơn vị thay đổi có rollback rõ.

## 8. Rollout và rollback

- WS-0 và shared primitives đi trước; không sửa đồng thời nhiều state machine
  nếu chưa có contract/generation/lifecycle adapter.
- Migrations additive-first; mọi backfill có dry-run, row count, checksum và
  rollback note.
- Feature flag phải có default an toàn, owner, expiry và metric; không dùng flag
  để che failure hoặc biến test đỏ thành xanh.
- Chỉ chạy provider/object/delete/restore/deploy thật sau khi owner cấp quyền;
  local/staging sandbox phải được chứng minh trước.
- Mỗi release candidate có evidence bundle bất biến gắn `head_sha`; rollback
  chọn artifact trước đó và kiểm lại migration/projection/cache generation.

## 9. Trade-off và quyết định cần chốt

### 9.1 Trade-off

- **Proof-first chậm hơn sửa UI đơn lẻ**, nhưng giảm nguy cơ sửa xong một lớp rồi
  phát hiện projection/cache/provider vẫn sai.
- **Shared primitives tăng coupling ban đầu**, nhưng coupling được đặt tên,
  version hóa và testable thay vì global/helper ngầm.
- **Additive migration giữ legacy lâu hơn**, đổi lại rollback và parity an toàn
  cho closed pilot.
- **Evidence bundle tốn storage**, nhưng rẻ hơn một lần release quyết định trên
  verdict giả.

### 9.2 Decision required từ chủ dự án/DPO/luật sư

- chấp nhận hay bắt buộc provider-side idempotency cho SMS (F-53);
- bật erasure thật hay giữ audit-only trong closed pilot;
- legal wording về 24/48 giờ, residency, cookie consent và policy history;
- owner/on-call, support route và correction SLA clock;
- điều kiện dữ liệu tối thiểu để chuyển từ noindex pilot sang public launch.

## 10. Definition of Done

Spec này được coi là đã chuyển sang implementation khi:

1. WS-0 có verifier và authority registry được version hóa;
2. mọi P1 nằm trong đúng một hoặc nhiều workstream có owner và acceptance test;
3. shared primitive signatures và file ownership được ghi trong implementation
   plan, không còn tên hàm mơ hồ;
4. test matrix chỉ rõ lớp evidence cần cho từng P1;
5. không có bước nào yêu cầu deploy, chi phí, legal approval hoặc destructive
   production action mà chưa ghi rõ decision gate;
6. implementation plan được viết thành các task 2–5 phút, có command và expected
   output theo chuẩn writing-plans.

Kết luận thiết kế: tối ưu không phải giảm số dòng code; tối ưu là giảm số lần
hệ thống có thể nói đúng ở một module nhưng sai ở boundary kế tiếp. Proof-first
đặt release evidence, authority và shared invariants lên trước, sau đó mới đóng
state machine và UX/legal. Đây là đường ngắn nhất có thể bảo vệ niềm tin mà không
đánh đổi khả năng rollback của closed pilot.
