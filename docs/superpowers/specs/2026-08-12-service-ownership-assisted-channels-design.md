# Child Spec 1 — Service Ownership & Assisted Channels

> **STATUS:** `approved-design / written-spec-pending-review`
> **Ngày:** 2026-08-12
> **Parent authority:** `docs/superpowers/specs/2026-08-11-nocturne-civic-whole-service-constitution-design.md`
> **Owner:** Service Owner của vinhlong360
> **Supersedes:** none
> **Superseded by:** none

## 1. Mục đích và phạm vi

Child Spec này biến Whole-Service Constitution thành một contract có thể vận
hành cho nhóm governance jobs, bắt đầu bằng pilot **Sửa thông tin sai/cũ**.
Nó định nghĩa ownership, online/assisted channels, Case Kernel, state fabric,
evidence-to-publication, receipt/status/notification, operator work control,
migration và acceptance evidence.

Spec này không phải implementation plan và không cấp phép gọi hệ thống là
`production-proven`. Mức trưởng thành phải tuân theo Definition Ladder của
Constitution.

### 1.1 In scope

- correction là vertical slice đầu tiên;
- contract chung có thể mở rộng cho claim, account recovery và safety report;
- anonymous, optional-contact, authenticated và operator-assisted paths;
- canonical case, interaction, party authority, work item, decision, promise và
  receipt;
- evidence ladder, risk registry và tách quyết định khỏi publication;
- queue, assignment, review, escalation, capacity evidence và service promise;
- additive-first migration từ JSONL/legacy admin path;
- end-to-end acceptance gates cho pilot.

### 1.2 Out of scope

- triển khai claim, account recovery hoặc safety workflow hoàn chỉnh;
- tự động suy luận truth từ AI, engagement, likes hoặc authority score;
- full RDF/claim graph, microservices hoặc database-per-domain;
- public resolution SLA trước khi có tối thiểu 28 ngày capacity evidence;
- biến generic email inbox thành system of record;
- operator hỏi hoặc nhập password, OTP, recovery code;
- thay đổi Constitution, visual operating system hoặc release-plane contract.

## 2. Bằng chứng hiện tại và phản biện

Các điểm dưới đây là lý do cần Child Spec, không phải acceptance cho trạng thái
hiện tại:

- `/lien-he` đang công bố lời hứa `24–48 giờ` dù chưa có capacity evidence tại
  `web-nuxt/pages/lien-he.vue`;
- public correction đang ghi JSONL và trả thông báo chung, không có durable
  receipt/status tại `agent/public_api.py`;
- AdminCP chỉ đổi `open/resolved/dismissed`, không biểu đạt domain outcome,
  decision reason hoặc publication state tại `agent/admin.py`;
- detail trust CTA còn chuyển sang community query thay vì canonical correction
  intake tại `web-nuxt/pages/dia-diem/[id].vue`;
- entity mutation và entity audit hiện đi qua các đường connection riêng, chưa
  chứng minh mutation + audit + outbox atomic;
- legacy records có thể thiếu consent, evidence, risk và receipt, nên migration
  không được bịa dữ liệu còn thiếu.

Phản biện chính: một queue có thể đổi trạng thái không đồng nghĩa service đã
hoàn tất. Acceptance phải nối trigger, intake, decision, publication, receipt,
appeal/recovery và outcome evidence trong cùng một contract.

## 3. Nguyên tắc bất biến

1. Một Service Owner chịu trách nhiệm end-to-end; slice lead không thay thế
   authority đó.
2. Mỗi case có đúng một write authority tại một thời điểm.
3. `Case` giữ canonical service state; domain extension giữ payload và policy
   riêng.
4. Case đã đóng không reopen. Reconsideration/appeal tạo `ReviewCase` liên kết.
5. Public status là projection an toàn, không phải raw backstage state.
6. `accepted` là quyết định factual; `published` là trạng thái public projection.
7. Backlog không được dùng để pause clock hoặc che breach.
8. Operator hỗ trợ có thể transcribe correction/safety; claim/recovery chỉ tạo
   provisional intake và secure continuation.
9. Operator không bao giờ hỏi hoặc nhập secret xác thực.
10. Receipt phải bền vững ngay sau intake; notification là side effect có thể
    retry, không phải điều kiện tạo case.
11. Evidence, provenance, review và lifecycle là các trục độc lập.
12. Không có terminal outcome chung kiểu `resolved` hoặc `dismissed` cho
    correction domain.

## 4. Service ownership và role model

### 4.1 Accountable Service Owner

Service Owner có authority thực tế đối với:

- mission, roadmap, backlog và scope của service slice;
- budget, provider, frontline capacity và coverage;
- policy về content, trust, privacy, safety và publication;
- queue policy, escalation, incident, recovery và rollback;
- user outcomes, failure demand và performance reporting;
- release admission và production evidence.

Mỗi slice phải có owner được định danh trong runtime/config manifest. Không dùng
team alias hoặc mailbox chung làm accountable owner.

### 4.2 Logical roles

Các role là logical authority, có thể do cùng một người giữ trong R0/R1 nếu
policy cho phép, nhưng không được vượt maker-checker của R2/R3:

| Role | Trách nhiệm | Ràng buộc |
|---|---|---|
| Policy owner | duy trì policy, risk và outcome semantics | không tự thay evidence của case |
| Duty operator | tiếp nhận, triage, read-back, status | không nhận secret xác thực |
| Assignee | thực hiện WorkItem | lease, scope và clearance bắt buộc |
| Decision maker | xác lập domain outcome | không vượt risk/role guard |
| Reviewer | kiểm tra độc lập | bắt buộc cho R2/R3 theo policy |
| Privacy/security authority | identity, consent, access, incident | step-up và revocation |
| Support provider | cung cấp channel/handoff | không trở thành truth authority |
| Service Owner | accountable end-to-end | chịu trách nhiệm outcome và evidence |

Mọi role transition, delegation, recusal và supervisor takeover đều là audit
event. Permission được cấp theo action và risk, không theo một role string duy
nhất.

## 5. Canonical Case Kernel

### 5.1 Envelope

Mọi correction, claim, recovery và safety intake dùng envelope chung:

```text
Case
  case_id
  service_kind
  category
  phase
  activity
  disposition_family
  domain_outcome
  severity
  reporter_privacy
  owner_ref
  current_revision
  promise_policy_ref
  created_at / updated_at / closed_at

Interaction
  interaction_id
  case_id
  channel
  actor_ref
  direction
  consent_ref
  identity_assurance
  payload_ref
  created_at

PartyAuthority
  party_ref
  authority_kind
  scope
  assurance_level
  granted_at / expires_at / revoked_at

WorkItem
  work_item_id
  case_id
  kind
  required_role
  risk_class
  status
  assignee_ref
  lease_expires_at
  ready_at / next_review_at
  revision

DecisionOutcome
  decision_id
  case_id / item_id
  outcome_code
  reason_code
  evidence_refs
  decision_maker_ref
  reviewer_ref
  decided_at

PromiseClock
  clock_id
  kind
  started_at
  due_at
  health
  policy_revision
  observed_at

InteractionReceipt
  receipt_id
  case_id
  public_reference
  capability_digest
  capability_key_version
  notification_consent_ref
  expires_at / revoked_at
```

Domain payload không được làm loãng envelope. Ví dụ correction giữ
`CorrectionItem[]`; claim giữ listing authority payload; recovery giữ secure
continuation state; safety giữ severity/evidence riêng.

### 5.2 Idempotency và revision

- Mỗi create/command có `Idempotency-Key` bounded theo actor/channel.
- Duplicate request trả cùng logical result hoặc `409` có problem detail rõ;
  không tạo interaction/case thứ hai.
- Mọi command gửi `expected_revision`; mismatch phải re-read/rebase, không blind
  overwrite.
- Current state là transactional snapshot; transition ledger immutable. Đây
  không phải full event sourcing.
- Business row, audit row và outbox intent commit trong cùng transaction.

## 6. Orthogonal Case State Fabric

State được biểu diễn trên các chiều độc lập, không nhồi mọi ý nghĩa vào một
status string:

| Dimension | Giá trị chuẩn |
|---|---|
| Phase | `intake`, `triage`, `investigation`, `decision`, `fulfillment`, `closed` |
| Activity | `active`, `waiting_on_requester`, `waiting_on_external` |
| Disposition family | `undetermined`, `action_taken`, `no_action`, `transferred`, `withdrawn`, `duplicate` |
| Domain outcome | thuộc domain; correction không dùng generic resolved/dismissed |
| Review relation | derived từ linked `ReviewCase` |
| Promise health | `on_track`, `at_risk`, `breached`, `recovery` |

`activity` không được dùng để che backlog. Waiting luôn có actor đang chờ,
reason, evidence và `next_review_at`. Clock vẫn giữ wall-clock lineage; các
đoạn chờ được báo cáo riêng thay vì âm thầm reset due date.

Review relation không nằm trong disposition. Nó được derive từ case graph:
`none`, `review_requested`, `under_review` hoặc `review_completed` dựa trên
`ReviewCase` liên kết.

### 6.1 Bốn service clocks

Đây là policy nội bộ, không phải tên gọi của một chuẩn bên ngoài:

1. **Receipt clock:** từ submit hợp lệ đến durable receipt.
2. **Triage clock:** từ receipt đến triage, owner và next action.
3. **Update clock:** từ một promise đến user-visible update kế tiếp.
4. **Resolution clock:** từ intake đến terminal outcome.

Receipt và update phải có target vận hành ngay. Triage target được dùng nội bộ
để quản trị queue. Resolution target chỉ được công bố sau tối thiểu 28 ngày
capacity evidence theo loại/risk/channel.

### 6.2 Transition guards

- `closed` không chuyển về phase khác.
- review relation `review_requested` hoặc `under_review` luôn trỏ tới
  `ReviewCase` mới; không mutate terminal case để giả lập appeal.
- `fulfillment` chỉ thành `closed/corrected` sau publication verification nếu
  domain outcome yêu cầu public change.
- Không chuyển `waiting_on_requester` nếu chưa có request cụ thể và safe message.
- Mọi transition có actor, reason, policy revision và correlation id.

## 7. Assisted-service contract

### 7.1 Channel boundaries

```text
Self-service web
  -> Case Kernel

Phone/Zalo human assistance
  -> AssistedSession + PartyAuthority
  -> Guided transcriber
  -> Case Kernel

Zalo AI conversation
  -> separate trust boundary
  -> explicit handoff
  -> structured intake only after confirmation
```

Generic email không phải source of truth. Nếu email được nhận trong giai đoạn
chuyển tiếp, operator phải transcribe vào case và ghi source interaction.
Pilot không ghi âm cuộc gọi. Phone-only user nhận human reference và chỉ được
đọc public-safe status qua operator, trừ khi có PartyAuthority và step-up hợp lệ.

### 7.2 Guided transcriber

Operator được phép hoàn tất correction và safety intake, với các bước:

1. đọc mục đích và privacy notice;
2. thu consent đúng scope;
3. đọc lại target, field, assertion và contact;
4. người dùng xác nhận nội dung;
5. tạo case và receipt;
6. đọc human reference và cách tra cứu status;
7. ghi channel, operator và authority audit.

Claim và account recovery chỉ tạo provisional intake. Người dùng phải tự hoàn
tất identity step-up trong secure continuation. Operator không chạm vào password,
OTP, recovery code hoặc secret tương đương.

Safety signal khẩn cấp không chờ correction queue. Nó tạo emergency escalation
theo safety policy và hiển thị hướng dẫn liên hệ cơ quan khẩn cấp phù hợp; pilot
không được mô tả vinhlong360 như emergency-response authority.

### 7.3 AI/Zalo handoff

AI conversation không tự động trở thành case payload. Handoff phải:

- hiển thị rõ đang rời AI để vào service case;
- cho người dùng xem và sửa structured fields;
- yêu cầu xác nhận trước khi submit;
- giữ conversation digest hoặc reference tối thiểu cần thiết, không đẩy toàn bộ
  transcript vào case nếu không cần;
- không truyền evidence content như tool instruction hoặc authority.

### 7.4 `/lien-he` service router

`/lien-he` định tuyến theo job thay vì trình bày một generic inbox:

- sửa thông tin sai/cũ -> correction intake;
- báo nguy cơ/vi phạm -> safety/report intake phù hợp;
- nhận quản lý trang -> claim provisional intake và secure continuation;
- khôi phục tài khoản -> recovery secure path;
- privacy/data request -> policy-specific service path;
- hợp tác thương mại -> contact lane riêng, không giả làm governance case.

Shell/page chỉ mô tả capability đang thật sự hoạt động. Không công bố resolution
SLA hoặc assisted coverage vượt capacity evidence.

## 8. Identity, consent và party authority

Identity assurance là action-specific:

| Job | Mức tối thiểu |
|---|---|
| Correction | anonymous hoặc optional contact |
| Safety report | anonymous/optional contact; escalation riêng nếu khẩn cấp |
| Claim | identity phù hợp với listing và scope |
| Account recovery | identity step-up bắt buộc |

Contact verification chứng minh quyền nhận notification, không tự chứng minh
quyền sở hữu listing hoặc account.

`PartyAuthority` phải có scope, expiry, revocation và audit. Operator acting on
behalf-of chỉ được làm đúng scope đã consent. Access session ngắn hạn, có step-up
khi xem evidence/private notes; revoke phải có precedence trên queued side effect.

## 9. Correction pilot: evidence-to-publication

### 9.1 CorrectionItem

Một case có thể có nhiều field-level item:

```text
CorrectionItem
  item_id
  entity_id
  field_path
  reported_value
  proposed_value
  base_entity_revision
  risk_class
  evidence_refs
  decision_ref
  changeset_ref
  publication_state
```

### 9.2 Evidence ladder

| Level | Ý nghĩa |
|---|---|
| E0 | assertion của người báo |
| E1 | artifact có ngữ cảnh |
| E2 | nguồn công khai độc lập |
| E3 | nguồn authoritative |
| E4 | field/independent verification |

Evidence level không tự động quyết định outcome. Policy còn xét field risk,
conflict, source scope, time, expiry, geography revision và reviewer authority.

### 9.3 Risk registry

| Risk | Ví dụ | Quy tắc |
|---|---|---|
| R0 | presentation/typo/layout | có thể fulfillment nhanh sau validation |
| R1 | routine facts, price, hours, image | decision maker được xử lý theo policy |
| R2 | identity, contact, location | cần authoritative evidence hoặc independent review |
| R3 | civic, safety, legal | bắt buộc Truth/Publication review và maker-checker |

### 9.4 CorrectionChangeSet

Decision không được ghi trực tiếp vào live entity. Accepted item tạo immutable
`CorrectionChangeSet` gồm:

- case/item linkage;
- base entity revision;
- before/after patch;
- evidence/provenance refs;
- policy revision và risk decision;
- decision maker/reviewer;
- apply status và public projection verification.

Atomic apply phải commit entity change, provenance, case fulfillment, audit và
outbox cùng transaction. `updatedAt` chỉ đổi khi content thực sự đổi.
`verifiedAt` chỉ đổi sau authorized verification activity.

Revision conflict phải rebase. Rollback dùng inverse patch và fail closed nếu
entity đã drift sau change set.

Terminal correction outcome dùng reason code cụ thể:

- `corrected`, chỉ hợp lệ sau khi public projection xác nhận title, field,
  source/time và giá trị hiển thị đúng;
- `confirmed_current`;
- `insufficient_evidence`;
- `out_of_scope`;
- `duplicate_linked`;
- `unable_to_verify`;
- `withdrawn_by_requester`.

Publication failure không phải terminal outcome. Nó giữ case trong fulfillment
hoặc recovery, tạo escalation và chỉ đóng khi public state đã được xác lập hoặc
decision được thay thế bằng một outcome hợp lệ khác.

## 10. Receipt, status và notification

### 10.1 Dual-track receipt

Mỗi case cấp:

- `public_reference`: human-readable, không bí mật, dùng qua phone/operator;
- capability secret entropy cao, chỉ hiển thị/cung cấp có kiểm soát;
- capability digest lưu tại server, không lưu plaintext lâu dài;
- access session ngắn hạn sau `POST` exchange.

Receipt secret không nằm trong query string, notification body, analytics,
referrer hoặc log. Client retry dùng idempotency response envelope được mã hóa
trong thời hạn giới hạn; sau thời hạn, anonymous user mất secret không được hứa
khả năng khôi phục.

Account link hoặc verified contact recovery phải là explicit và có step-up.
Rotation tạo capability mới và revoke grant cũ; revoked/expired grant không được
phục hồi bằng cache, queued notification hoặc session cũ.

### 10.2 Public status projection

Status view chỉ trả:

```text
public_reference
received_at
current_step
waiting_for
next_action
next_update_at
promise_health
item_decisions
item_publication_states
review_path
```

Không trả raw evidence, private note, operator identity ngoài mức policy cho
phép, IP hash hoặc contact data.

Decision và publication luôn hiển thị riêng. “Đã chấp nhận” không được render
thành “đã cập nhật công khai”.

### 10.3 Notification

- receipt commit trước notification;
- outbox delivery at-least-once, consumer idempotent;
- re-check consent, mute/block và privilege tại thời điểm side effect;
- message generic, không chứa evidence nhạy cảm hoặc bearer secret;
- notification failure tạo retry/incident signal, không rollback case;
- update bị trễ chuyển promise health sang `breached` hoặc `recovery` và phát
  hành next update mới.

## 11. Backstage Work Control

### 11.1 Policy-derived queue

`WorkItem` được tạo từ phase, risk, required role, evidence need và promise
health. Queue không phải danh sách status chung.

Thứ tự ưu tiên minh bạch:

```text
Emergency/regulatory override
→ breached/at-risk promise
→ risk class
→ ready_at lâu nhất
→ received_at lâu nhất
```

Không tối ưu queue sạch, approve count, batch throughput hoặc session count.

### 11.2 Assignment và lease

- một work item chỉ có một active assignee;
- claim dùng lease có expiry và heartbeat;
- takeover/reassign cần reason và audit;
- supervisor không được bypass risk guard bằng thao tác UI;
- conflict of interest tạo recusal và work item mới;
- completed work item phải có evidence/result reference.

### 11.3 Maker-checker

- R0 có thể cùng operator xử lý và fulfill;
- R1 theo policy có thể một decision maker;
- R2 yêu cầu authoritative evidence hoặc reviewer độc lập;
- R3 bắt buộc maker-checker và Truth/Publication review;
- người tạo evidence không được tự review item cần independence.

### 11.4 Operator workbench

AdminCP dùng grammar:

```text
Queue → Promise health → Owner → Next action
```

Workbench phải có target, field risk, evidence ladder, before/after diff,
decision reason, change set, publication verification, interaction history và
user-safe message preview. Không có nút terminal chung `Đã xử lý`.

## 12. Capacity, promise và escalation

### 12.1 Capacity evidence

Đo riêng theo risk và channel:

- arrival/completion rate;
- backlog age, ready time, waiting time, touch time;
- rework, review overturn, publication failure;
- WIP trên mỗi operator và queue coverage;
- promise breach, failure demand và repeated contact;
- anonymous/optional-contact/authenticated/assisted completion.

Dữ liệu phải giữ window liên tục tối thiểu 28 ngày trước public resolution SLA.
Không reset denominator khi deploy hoặc restart.

### 12.2 Escalation

Tạo escalation work item khi:

- case không có accountable owner;
- promise at-risk/breached;
- R2/R3 có evidence conflict;
- publication hoặc rollback thất bại;
- privacy/security/safety signal;
- lease hết hạn lặp lại hoặc case bị bỏ quên.

Escalation không âm thầm sửa history hoặc đổi terminal outcome.

## 13. Additive-first migration và pilot rollout

### 13.1 Migration records

Legacy JSONL nhập thành `LegacyIntakeRecord` với:

- source file/line locator;
- raw record digest;
- imported case id;
- legacy status mapping;
- missing-data flags;
- imported_at và reconciliation result.

`resolved` cũ không tự chuyển thành `corrected`; contact cũ không tự trở thành
verified consent; thiếu evidence không được bịa.

Adapter phải phân loại theo target và intent, không nhập toàn bộ JSONL thành
correction:

- `stale_field`, facility/entity factual issue -> CorrectionCase;
- post/comment policy violation -> legacy safety/moderation linkage;
- record mơ hồ -> manual triage, không auto-classify;
- duplicate source rows -> một canonical case và migration linkage cho từng row.

### 13.2 Cutover sequence

1. Deploy schema additive và policy/config không tạo business side effect.
2. Shadow import, checksum, duplicate check và reject ledger.
3. Rehearse với synthetic và operator cases.
4. Chuyển `/danh-ba`/entity correction sang Kernel.
5. Chuyển detail/trust drawer.
6. Chuyển `/lien-he` router và assisted intake.
7. Chuyển các entry point còn lại.
8. Freeze JSONL write path thành read-only archive.
9. Reconcile sau cutover và công bố pilot metrics nội bộ.

Mỗi surface chỉ có một write authority. Compatibility projection chỉ phục vụ
đọc hoặc rollback presentation; không tạo dual-write lâu dài.

### 13.3 Rollback

Trước live cutover có thể tắt Kernel feature flag. Sau live case, không quay lại
JSONL writable; rollback chuyển UI/status/publication sang degraded path trong khi
Canonical Case Kernel vẫn là authority. Publication có kill switch riêng; intake,
receipt và audit tiếp tục hoạt động.

## 14. Acceptance và test contract

### 14.1 Contract tests

- state transition/property tests;
- command guard và expected-revision tests;
- idempotency/lost-response tests;
- concurrent assignment/lease/CAS tests;
- transactional case + audit + outbox tests;
- receipt digest, exchange, expiry, rotation và revocation tests;
- party authority scope/step-up/recusal tests;
- evidence/risk/policy tests;
- change set conflict và inverse-patch fail-closed tests.

### 14.2 Journey tests

- anonymous correction từ detail tới public corrected projection;
- optional-contact consent và generic notification;
- authenticated case link;
- phone-only assisted read-back và human reference;
- Zalo AI explicit handoff;
- R2/R3 maker-checker;
- insufficient evidence và confirmed current;
- appeal tạo ReviewCase;
- notification provider outage;
- publication failure/recovery;
- migration legacy record và reconciliation.

### 14.3 Accessibility và privacy

- keyboard-only, screen reader, 200% text, 320×256 reflow và 320×180 short
  height;
- receipt/status không expose secret qua URL, DOM retained state hoặc telemetry;
- user A không đọc status/evidence của user B;
- operator không thấy secret authentication;
- generic error cho invalid/expired receipt để chống enumeration;
- mọi notification re-check consent và revocation.

## 15. Pilot exit criteria

Pilot correction chỉ được mở rộng khi:

1. named owner, duty coverage, queue policy và incident runbook hoạt động;
2. online và assisted path dùng cùng Case Kernel;
3. mọi terminal case có domain outcome, reason và evidence lineage;
4. mọi accepted public change có verified projection;
5. không có lost receipt, cross-case disclosure hoặc blind overwrite;
6. migration reconciliation không có loss/duplicate/unexplained status;
7. D4 journey/runtime evidence đã được bind với artifact;
8. 28-day capacity window đã bắt đầu và được giữ nguyên;
9. không còn unsupported resolution SLA hoặc generic `Đã xử lý` trong pilot;
10. claim, recovery và safety chỉ được mở sau domain-specific risk review.

Pilot exit không phải D5 release admission hoặc D6 production outcome proof.
Các gate đó thuộc Spec 7 và release control plane của Constitution.

## 16. Dependency và authority

Child Spec này phụ thuộc vào Whole-Service Constitution, đặc biệt các phần về
Service Owner, Integrity Kernel, security/privacy, outbox, publication eligibility
và evidence ladder. Nó cung cấp contract cho:

- Spec 3: Owner & Journey State Contracts;
- Spec 4: Truth, Publication & AI Grounding;
- Spec 5: Modular Monolith & Runtime Reliability;
- Spec 6: Security & Privacy Control Plane;
- Spec 7: Quality, Release & Production Evidence.

Nếu implementation gặp xung đột, không âm thầm sửa contract. Phải ghi
problem statement, affected outcome, security/privacy impact, migration/rollback,
evidence gate và Service Owner approval theo Constitution.

## 17. Research anchors

Thiết kế đối chiếu với các nguồn đã dùng trong Constitution:

- GOV.UK Service Standard và assisted digital guidance;
- CMMN 1.1 và SCXML cho case/stage/orthogonal state;
- RFC 9110 cho `If-Match` và lost-update prevention;
- RFC 9457 cho problem details;
- RFC 9700 cho việc không đưa bearer token vào URI query;
- OWASP Forgot Password/Session Management;
- NIST SP 800-63B cho recovery, notification và identity assurance;
- Google SRE SLO/low-traffic alerting;
- AWS Transactional Outbox;
- UK Government Data Quality Framework và W3C PROV-O;
- PHSO complaint-handling principles.

Các nguồn trên định hướng control và evidence; không phải chứng nhận compliance
hiện tại. Threshold nội bộ chỉ có hiệu lực khi được ghi trong policy revision và
được đo bằng artifact tương ứng.
