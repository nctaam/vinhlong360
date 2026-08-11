# Nocturne Civic Fieldbook — Whole-Service Constitution

> **STATUS:** `approved-design / written-spec-review`
> **Ngày chốt kiến trúc:** 2026-08-11
> **Phạm vi:** toàn hệ thống vinhlong360: public, tài khoản, cộng đồng, AdminCP, backend, dữ liệu, AI, vận hành và phát hành
> **Tên chương trình:** **Nocturne Civic Fieldbook — Whole-Service Integrity**
> **Visual operating system:** **Adaptive Nocturne Fieldbook**

## 1. Mục đích

Tài liệu này là hiến pháp kiến trúc và vận hành cho giai đoạn nâng cấp tiếp theo
của vinhlong360. Nó chuyển định hướng từ “website/super-app có nhiều màn hình”
sang một dịch vụ thông tin địa phương end-to-end:

- giúp người dân và người ghé thăm hiểu địa bàn;
- cho phép kiểm tra nguồn, độ mới và mức độ tin cậy;
- giúp người dùng thực hiện bước tiếp theo nhanh và an toàn;
- khép kín các công việc từ giao diện đến xử lý backstage, thông báo kết quả,
  khiếu nại và recovery;
- tiếp tục hoạt động có kiểm soát khi dữ liệu, mạng, map, AI hoặc hạ tầng suy
  giảm;
- chỉ tuyên bố mức trưởng thành dựa trên bằng chứng gắn với artifact và hành vi
  production thực tế.

Đây không phải một mega-feature spec và không cho phép triển khai toàn bộ trong
một branch hoặc một implementation plan duy nhất. Nó xác định authority,
invariants, ranh giới kiến trúc, maturity ladder và portfolio spec bắt buộc.

## 2. Luận đề sản phẩm

### 2.1 Civic value proposition

> **vinhlong360 giúp người dân và người ghé thăm hiểu địa bàn, kiểm tra nguồn và
> thực hiện bước tiếp theo.**

Category của sản phẩm là **hạ tầng thông tin địa phương**, không chỉ là cổng du
lịch, tạp chí địa phương hoặc mạng xã hội.

### 2.2 Các quyết định sản phẩm bất biến

- Năm destination cốt lõi luôn là: **Trang chủ, Khám phá, Gần bạn, Cộng đồng,
  Cá nhân**.
- Đặc sản và Lịch trình nằm trong contextual navigation hoặc task flow, không
  trở thành destination thứ sáu.
- Shell sở hữu navigation, context, notice và mobile bottom bar.
- Bottom navigation ổn định; contextual CTA thuộc page hoặc ActionDock riêng.
- Search dùng một contract chung; catalog/list và map là hai presentation của
  cùng DiscoveryState.
- Adaptation chỉ được thay đổi ordering, density, explanation và CTA trong một
  module ổn định. Nó không được đổi topology, route, authority hoặc ý nghĩa
  destination.
- Không tạo tourist mode và resident mode. Context dùng location/time/explicit
  intent, không suy đoán danh tính xã hội của người dùng.
- Public và AdminCP dùng chung truth/status terminology nhưng không dùng chung
  cinematic treatment hoặc density.

## 3. Authority và quy tắc kế thừa

### 3.1 Authority chain

Khi có xung đột, thứ tự áp dụng là:

1. tài liệu Whole-Service Constitution này;
2. `design-system/vinhlong360/MASTER.md` cho visual foundation và family grammar;
3. `2026-07-31-nocturne-heritage-adaptive-public-design.md` cho Nocturne art
   direction còn tương thích;
4. kernel/capability specs được liệt kê tại Mục 21;
5. route/page specs;
6. implementation plan, code và tests.

Một tài liệu cấp dưới chỉ được ghi đè cấp trên khi ghi rõ:

- invariant bị ảnh hưởng;
- lý do;
- owner phê duyệt;
- evidence cần có;
- thời hạn hoặc điều kiện gỡ ngoại lệ.

### 3.2 Truth synchronization

- Mỗi tài liệu active phải có `status`, `owner`, `supersedes` và
  `superseded_by` khi phù hợp.
- Không có hai tài liệu cùng tự nhận là visual hoặc program authority cho cùng
  một phạm vi.
- Tài liệu legacy vẫn được giữ để truy vết nhưng không tham gia acceptance nếu
  đã bị supersede.
- Mọi authority exception phải nằm trong một registry có owner và expiry.

## 4. Maturity hiện tại và target

Tại thời điểm phê duyệt kiến trúc:

| Lớp | Mức hiện tại |
|---|---|
| Một số màn hình public riêng lẻ | mạnh về thị giác |
| Visual operating system toàn route | phân mảnh |
| Journey public | có primitive tốt nhưng còn dead end/race |
| Service end-to-end | chưa khép kín frontstage-backstage-outcome |
| Trust/data/AI | research-ready, chưa publish-ready |
| Security/privacy | chưa đạt target ASVS L2 |
| Reliability | metrics ad hoc, chưa SLO-managed |
| Release | chưa có exact-artifact admission graph |

Không dùng `world-class`, `production-ready`, `verified` hoặc `official` như
nhãn marketing. Mọi claim mức trưởng thành phải theo Definition Ladder tại Mục
18.

## 5. Whole-service operating model

### 5.1 Actors

Hệ thống thiết kế cho bốn nhóm actor chính:

- **Resident:** cần thông tin địa phương, cảnh báo, dịch vụ, sự kiện và cách sửa
  dữ liệu sai.
- **Visitor:** cần khám phá, định hướng, thông tin đáng tin và lập kế hoạch.
- **Listing owner:** cần claim, cập nhật, chứng minh và duy trì listing trong
  phạm vi được cấp.
- **Contributor/community member:** cần đóng góp, theo dõi xử lý, nhận lý do và
  appeal khi bị moderation.

### 5.2 Ba task lane chung

| Lane | Outcome |
|---|---|
| Cần biết hoặc làm ngay | cảnh báo, danh bạ, thông tin gần, giờ/giá/dịch vụ |
| Khám phá và lập kế hoạch | địa điểm, món ăn, văn hóa, sự kiện, hành trình |
| Góp ý và tham gia | correction, claim, review, report, community |

Homepage phải cho utility và discovery xuất hiện trong hai module đầu. Không
lane nào chiếm quá 60% số primary modules.

### 5.3 Service Owner Charter

Toàn dịch vụ có một **Service Owner** chịu trách nhiệm end-to-end, gồm:

- mission, roadmap và backlog;
- service performance và user outcomes;
- budget, capacity và supplier/provider;
- online, assisted và backstage channels;
- content, trust, safety và data policy;
- reliability, incident và recovery;
- publication, release admission và production evidence.

Slice lead sở hữu delivery của một job; họ không thay thế Service Owner.

### 5.4 Multidisciplinary ownership

Mỗi service slice có đại diện cần thiết từ:

- product/service ownership;
- design/research/content;
- engineering/data;
- frontline/back-office operator;
- trust and safety;
- privacy/security/legal khi risk yêu cầu.

Operations không đứng ngoài team. Failure demand, scripts, queue policy và
offline handoff cùng nằm trong backlog dịch vụ.

## 6. Định nghĩa vertical slice hoàn chỉnh

Một vertical slice chỉ hoàn tất khi có đủ:

```text
User trigger
  -> eligibility/prerequisite
  -> online hoặc assisted path
  -> canonical case/job state
  -> backstage decision/operation
  -> notification/status
  -> appeal/recovery
  -> terminal outcome
  -> outcome evidence
```

Definition of Done bắt buộc:

1. named owner có authority thực tế;
2. boundary từ trigger đến terminal outcome;
3. online, assisted và backstage handoff cần thiết;
4. receipt, status, audit, appeal và recovery;
5. capacity model, SLA và incident owner;
6. outcome metrics theo channel và nhóm người dùng;
7. end-to-end test với edge users và operator;
8. kế hoạch operate, improve và publish performance sau launch.

`API exists`, `page renders` hoặc `queue can update status` không đủ để gọi
service slice hoàn tất.

## 7. Assisted-service contract

Các job correction, claim, account recovery và safety report phải xác định:

- self-service path;
- phone/chat-assisted path;
- on-behalf-of permission nếu operator thao tác thay người dùng;
- consent, identity và audit contract;
- support capacity và SLA;
- handoff từ hỗ trợ sang domain queue;
- receipt và terminal outcome dùng chung với online path.

Generic contact inbox không phải assisted service hoặc governance system of
record.

## 8. Kiến trúc ba lớp

```text
Service Operating Model
        -> actors, channels, outcomes, ownership, operations

Integrity Kernels
        -> truth, owner, journey, interaction, delivery, evidence

Evidence-Governed Delivery
        -> modular monolith, runtime, SLO, security, admission, canary
```

Kernel chỉ sở hữu irreducible core và interfaces. Domain workflow, operator
decision và outcome vẫn thuộc vertical slice; không tạo một central workflow
monolith.

## 9. Integrity Kernel 1 — Truth

### 9.1 Minimal evidence model

Không xây RDF, full claim graph hoặc sentence-level annotation ở giai đoạn này.
Mô hình tối thiểu gồm:

- `publication_state`: `draft | review | published | withdrawn`;
- `admin_unit_code`;
- một bảng `entity_assertions`;
- một administrative-unit manifest có version và digest;
- một pure policy engine dùng chung.

Entity/detail tables tiếp tục giữ canonical displayed values. Assertion chứng
minh một subject value tại một thời điểm.

### 9.2 Assertion contract

```text
entity_id
subject_key
asserted_value_json
value_hash
provenance_kind
evidence_json
review_state
issuer_name / credential_ref
source_published_at / source_modified_at / source_captured_at
observed_at / valid_until / review_due_at
reviewer_id / reviewed_at
revoked_at / supersedes_assertion_id
```

Assertion hợp lệ khi:

1. accepted;
2. value hash khớp canonical value hiện tại;
3. evidence/provenance policy đạt;
4. chưa hết hạn, revoked hoặc conflicted;
5. đúng policy và geography revision.

Không tạo một authority score tổng hợp. Provenance, review và lifecycle là ba
trục độc lập.

### 9.3 Authority lanes

1. **Official:** organization identity, publisher, source URL, scope, time và
   expiry.
2. **Verified partner:** verification record, scope, renewal và conflict-of-
   interest disclosure.
3. **Editorial:** editor/byline, source set, update và correction history.
4. **Community:** author attribution, moderation state và report path; không hàm
   ý factual verification.
5. **Unknown:** fallback an toàn, không badge tích cực.

AI là metadata trực giao: illustration, retrieval, ranking, summary hoặc
drafting. AI không được gán authority tier.

### 9.4 Policy surfaces

Policy engine trả quyết định riêng cho:

- public card;
- public detail;
- structured data;
- indexing;
- AI grounding.

Fail closed theo field/surface khi có thể. Một field hết hạn không làm trắng
toàn bộ entity nếu identity cơ bản vẫn hợp lệ.

## 10. Integrity Kernel 2 — Owner

Mọi private state phải bind với:

```text
ownerKey + ownerEpoch + schemaVersion
```

Áp dụng cho favorites, recent history, planner draft, saved plans,
notifications, personal detail actions, offline operation queue và private
Nuxt payload/cache.

Invariants:

- owner A không render, merge hoặc apply dưới guest hoặc owner B;
- logout/account switch tăng epoch và reset visible private state;
- pending response của epoch cũ bị discard;
- guest-to-account transfer là explicit one-time operation;
- private cache luôn owner-scoped và `private, no-store` ở HTTP boundary;
- raw location, prompt, plan content hoặc identity selector không đi vào shared
  cache/telemetry.

## 11. Integrity Kernel 3 — Journey

### 11.1 Canonical contracts

Chỉ giữ ba contract chính:

- `DiscoveryState`;
- `NavigationIntent`;
- `PlanSnapshot` cùng `PublishIntent`.

### 11.2 DiscoveryState

```text
committed: query, intent, filters, area, bbox/near, sort, cursor
pending: input, pending bounds, highlighted item
privateByEntry: selection, panel, scroll anchor
```

Chỉ committed state vào URL. Pending state không được thay đổi result hoặc share
URL. Back/Forward phục hồi route identity và committed state của đúng history
entry.

### 11.3 NavigationIntent

Intent phải immutable, TTL ngắn và consume-once. Nó bind source entry, return
path, target object và action. Close/cancel/route invalidation hủy intent và
mọi async attempt cũ.

Không giữ singleton callback function cho auth continuation.

### 11.4 PlanSnapshot và publication

PlanSnapshot bind owner, revision, title, stops, mode, travel budget và
schedule. Planner startup luôn theo thứ tự:

```text
BOOT
  -> HYDRATE_OWNER_DRAFT
  -> APPLY_NAVIGATION_INTENT_ONCE
  -> ENABLE_PERSISTENCE_AND_ROUTING
  -> READY
```

Publish plan bắt buộc preview và xác nhận public projection cho title, author,
stop names, times, notes và coordinates. API không trả raw arbitrary `stops`.

## 12. Integrity Kernel 4 — Interaction và geometry

### 12.1 Task Spine + Evidence Bands

Public/task grammar:

```text
Task masthead
  -> context/state band
  -> primary task stream
  -> evidence bands
  -> continuation
```

- một `main` duy nhất;
- một `h1` và tối đa một primary filled action trong mỗi task region;
- named region biểu đạt task, không biểu đạt decoration;
- map/gallery/sticky aside là progressive enhancement, không là source of
  truth duy nhất.

### 12.2 OverlayCoordinator

Một owner duy nhất quản lý:

- overlay stack;
- topmost-only Escape;
- inert background;
- reference-counted scroll lock;
- focus origin và LIFO restoration;
- Back-button dismissal;
- z-index và fixed-stack reservation.

### 12.3 Geometry

```text
G = clamp(16px, 3vw, 32px)
D = clamp(16px, 2.5vw, 32px)
C = container inline-size sau padding
A = 100dvh - shellBlockSize - fixedStackReservedSize
```

Container states:

- compact `<40rem`;
- standard `40–64rem`;
- wide `>64rem`.

Height states:

- short `<48rem`;
- critical `<32rem`.

Map split chỉ khi `C >=64rem && A >=40rem`. Planner ba vùng chỉ khi
`C >=72rem && A >=40rem`. Critical height chuyển về một cột, không sticky và
chỉ giữ chrome thiết yếu.

### 12.4 Visual operating system

Adaptive Nocturne Fieldbook dùng các invariant:

- Nocturne là outer canvas; Parchment là reading/evidence/decision plate;
- Be Vietnam Pro cho interface/body; Fraunces chỉ cho place, feature, human
  quote hoặc cultural voice;
- mỗi view tối đa một Dòng địa bàn và mọi node phải là dữ liệu/state thật;
- River = action, Clay = brand/editorial, Orchard = proof, Amber = warning/time,
  Coral = danger;
- một accent biểu cảm chính trên mỗi viewport;
- không quá hai cấp enclosure;
- row/table không hover-lift;
- tối đa một structural reveal và một exceptional ambient moment mỗi view;
- map/planner/directory không có cinematic hero, serif hoặc decorative texture;
- AdminCP dùng `queue -> status -> owner -> next action`.

## 13. Accessibility contract

### 13.1 WCAG 2.2 AA baseline

- 200% text resize không mất nội dung/chức năng;
- reflow tại 320 x 256 CSS px;
- focus visible và không bị che hoàn toàn;
- target size đạt 24 CSS px hoặc spacing theo tiêu chí;
- drag có single-pointer non-drag alternative;
- password manager, paste và OTP autofill không bị chặn;
- status messages có semantics mà không đánh cắp focus;
- modal thực sự inert, focus-contained và có deterministic return focus.

### 13.2 B+ enhanced requirements

- focused component hoàn toàn không bị che;
- focus indicator 2 CSS px và 3:1;
- public task controls ưu tiên 44 x 44;
- short-height test 320 x 180;
- overlay ba tầng stack-safe;
- announcement ngắn, deduplicated và không bọc retained DOM;
- list/map và click/drag parity;
- Vietnamese strings 2x, tên 64 ký tự và đầy đủ dấu không mất identity.

Không mô tả B+ enhanced gate như yêu cầu normative của WCAG AA.

## 14. Integrity Kernel 5 — Delivery

### 14.1 Modular monolith

Giữ một PostgreSQL và các bounded contexts:

- Catalog & Editorial;
- Identity & Trust;
- Community & Safety;
- Personal Planner;
- Discovery read models;
- Assistant Knowledge;
- Delivery Platform;
- Governance.

AdminCP gọi domain services, không tạo một AdminRepository ghi trực tiếp mọi
bảng domain.

### 14.2 Command path

```text
route
  -> command service chạy ngoài event loop nếu dùng sync DB
     -> open Unit of Work
        -> lock/CAS/unique-constrained mutation
        -> audit + outbox intent
        -> construct và strict-validate response DTO
        -> commit
     -> return validated DTO
```

Không commit trong dependency teardown sau khi response đã gửi. UoW không thay
thế CAS, row lock hoặc unique constraint.

### 14.3 Outbox semantics

- business row + audit + outbox intent cùng transaction;
- delivery là at-least-once;
- consumer idempotent theo aggregate revision/event type;
- không giữ transaction khi gọi external provider;
- consumer revalidate consent, block/mute và privilege tại thời điểm side
  effect;
- revoke/cancel/tombstone có precedence trên queued event cũ;
- BackgroundTasks hoặc `asyncio.create_task` không là correctness path.

### 14.4 Projection và cache

- knowledge/homepage/search projection build từ một immutable snapshot revision;
- public eligibility overlay là strong-consistency boundary;
- ranking/vector/trending có thể eventual;
- auth, privacy, unpublish và erasure không được chờ cache TTL;
- public cache key gồm DTO/source/policy revision;
- private cache không dùng shared Nitro/Nginx/SW cache.

## 15. Frontend runtime contract

### 15.1 Hai runtime planes

**SSR request plane:** request context, launch safety, session bootstrap,
serialized `useState` và `useAsyncData` payload.

**Client lifetime plane:** theme/accessibility listeners, network/context clock,
overlay/focus stack và browser-only effects.

Không có mutable module-level request/session ref, timer, promise hoặc installed
boolean.

### 15.2 Query/mutation split

- initial SSR/read dùng `useAsyncData` hoặc `useFetch` với explicit key và
  abortable side-effect-free handler;
- domain API dùng common transport;
- click/form mutation gọi domain API trực tiếp rồi refresh/invalidate;
- `SurfaceState` là computed projection của canonical AsyncData;
- handler không toast, navigate, storage hoặc DOM side effect;
- middleware pure/idempotent vì initial navigation chạy server và client;
- logout clear toàn bộ user-keyed Nuxt state/data;
- no full-page Nitro SWR cho cookie/session/personalized routes.

## 16. Security và privacy control plane

Target kiểm soát:

- OWASP ASVS L2 cho public application;
- L3-equivalent controls cho AdminCP, Authority Registry và release plane;
- host-only `__Host-` cookies, Secure, HttpOnly, SameSite;
- cookie-only session; không trả raw bearer token trong JSON;
- rotation, timeout, revocation và step-up authentication;
- actor-target rank policy cho role/ban/unban/bulk actions;
- submitter, reviewer và credential issuer tách biệt;
- builder, release approver, signer và deployer tách biệt;
- server-authoritative consent trước location/provider disclosure;
- erasure production state machine, không audit-only mặc định;
- telemetry/log/outbox cấm raw prompt, GPS/IP, session selector, plan content và
  secrets;
- production startup từ chối debug, placeholder credential, auto-generated
  secret và unknown config;
- route recipes chỉ chọn compile-time allowlisted IDs, không dynamic URL/path;
- feature flags không bao giờ là auth, consent hoặc ownership control.

## 17. Reliability, capacity và SLO

### 17.1 Small-topology first

Thiết kế cho single-process/small VPS trước, scale-out sau. Không thêm
microservices, Redis-required, multi-worker hoặc full observability stack nếu
chưa có evidence.

Initial admission budgets:

| Lane | Active | Bounded queue |
|---|---:|---:|
| Public DB/API | 8 | 16, wait <=250ms |
| LLM/provider | 4 | 4, wait <=2s |
| Heavy admin/index | 1 | no queue |
| Private mutations | 4 | deadline 5s |
| SSR documents | 10 | wait <=500ms |

Các giá trị này là launch hypothesis, không phải proven capacity.

### 17.2 SLO targets

Rolling window 28 ngày:

| Journey | Availability target |
|---|---:|
| Public SSR/core API | 99.5% |
| Typeahead/auth/community/private | 99.0% |
| Chat/provider journey | 98.0% |

Good event phải đúng contract và nằm trong deadline. Blank core, invalid
projection, stale vượt max, duplicate provider/mutation và blocked primary task
là bad event dù HTTP 200.

Web Vitals p75, tách mobile/desktop:

- LCP <=2.5s;
- INP <=200ms;
- CLS <=0.1.

SLI phải bền vững ít nhất 35 ngày và không reset khi restart/deploy. Không dùng
`/health/slo` hiện tại làm production evidence cho đến khi denominator/window
được sửa.

### 17.3 Degradation ladder

1. normal;
2. bỏ community/map/prefetch;
3. serve stale public, tắt LLM và private mutations;
4. branded maintenance/static legal shell.

Public read core được ưu tiên hơn background, chat và optional panels khi memory
hoặc dependency bị áp lực.

## 18. Integrity Kernel 6 — Evidence và release

### 18.1 Definition Ladder

- **D0 Claim:** named capability/owner/risk; không readiness claim.
- **D1 Defined:** executable policy, expected evidence và failure/skip semantics.
- **D2 Fast verified:** static/unit/contract/security-baseline evidence.
- **D3 Artifact integrated:** authoritative artifact built once; integration/DB
  evidence bind digest.
- **D4 Journey/runtime verified:** browser, a11y, security, migration và NFR trên
  deployed ephemeral artifact.
- **D5 Release admitted:** provenance, signed admission, SBOM, direct source
  controls, zero unexpected skip và valid exceptions.
- **D6 Outcome proven:** cùng digest qua canary; production failure/recovery,
  rollback/rework và RCA được nối lại.

Không dùng `complete`, `ready`, `production-proven` hoặc `world-class` ngoài
ladder này.

### 18.2 Build and admission

Artifact set:

```text
release.tar.gz
release.spdx.json
release.intoto.jsonl
release.sigstore.json
admission.json
```

- build production archive đúng một lần từ admitted SHA;
- SLSA/in-toto provenance mô tả build lineage;
- custom in-toto B+ Quality predicate mô tả test/security/migration/NFR;
- signed admission predicate tổng hợp verdict;
- promotion chỉ tải exact digest; không checkout/rebuild/repackage;
- target trước mắt là SLSA Build L2-oriented, không tuyên bố L3;
- OpenSSF Scorecard là heuristic signal, không là release verdict;
- trusted final admission check phải fail mọi unexpected skip vì GitHub required
  checks có thể chấp nhận skipped/neutral job.

### 18.3 Promotion state machine

```text
SOURCE
  -> CI_ADMITTED
  -> BUILD_ONCE
  -> SIGNED
  -> MIGRATION_READY
  -> DARK_DEPLOYED
  -> OPERATORS
  -> CANARY_5
  -> CANARY_25
  -> PRODUCTION_100
```

Raw flag combinations không hợp lệ fail closed. Một request dùng một config
snapshot thống nhất cho SSR và hydration.

Dark deploy mặc định zero business write/outbox/provider effect. Rollback chỉ
hoàn tất khi readiness, representative journeys và user-impact signals trở lại
baseline. DB restore là recovery class riêng và cần explicit data-loss
authorization.

## 19. Community, moderation và public communication

### 19.1 SafetyCase

Mọi correction/report/moderation/appeal dùng canonical case model:

```text
case_id, category, severity, evidence, reporter privacy,
owner, assignee, SLA, status, decision reason,
notifications, appeal, terminal outcome
```

Queue ưu tiên oldest/SLA/risk, không tối ưu “queue sạch”, session approve count
hoặc batch throughput.

### 19.2 Participation integrity

Một civic participation process phải công bố:

- sponsor và câu hỏi quyết định;
- phạm vi ảnh hưởng;
- thời hạn;
- privacy và anti-harassment protections;
- cách input được sử dụng;
- kết quả và điều gì đã thay đổi.

Community posting không tự được gọi là civic consultation.

### 19.3 Feature cuts

Loại khỏi authority/trust experience:

- leaderboard, podium, public XP và streak;
- engagement-derived labels như Đại sứ, Người địa phương, Nội dung chất lượng;
- likes/followers trong trust tier hoặc expert ranking;
- copy `Đánh giá thật`, `Trải nghiệm thật` hoặc `Cộng đồng đã xác minh` khi
  không có evidence tương ứng.

Moderation approval chỉ chứng minh nội dung vượt safety policy, không chứng minh
factual correctness.

## 20. AI grounding và structured data

- AI factual retrieval chỉ nhận accepted/current assertion projections;
- factual output phải có cited assertion IDs hoặc abstain;
- invalid marker được retry một lần, sau đó trả insufficient evidence;
- factual prose phải buffer và validate trước khi stream;
- cache key bind assertion set, policy, model, prompt và grounding revision;
- evidence content được coi là data, không là instruction/tool authority;
- structured data dựng từ visible policy projection, không raw DB;
- không suy diễn InStock, price 0, EventScheduled, official hoặc credential;
- nếu rich-result object thiếu required evidence, bỏ object đó;
- không ưu tiên FAQPage chỉ để săn rich result;
- `sameAs` chỉ biểu diễn identity equivalence, không là evidence.

## 21. Spec portfolio bắt buộc

Constitution này được triển khai qua bảy spec độc lập:

1. **Service Ownership & Assisted Channels**
2. **Visual, Interaction & Layout Operating System**
3. **Owner & Journey State Contracts**
4. **Truth, Publication & AI Grounding**
5. **Modular Monolith & Runtime Reliability**
6. **Security & Privacy Control Plane**
7. **Quality, Release & Production Evidence**

Mỗi spec cần user review riêng trước implementation plan. Không gộp bảy spec
thành một plan.

## 22. Roadmap cấp chương trình

### Wave 0 — Stop-the-line

- cross-account state contamination;
- publish-plan privacy;
- auth wrong-target callbacks/generation;
- role hierarchy, cookie scope, 2FA step-up và erasure;
- fake near/directions/walking/cycling/offline claims;
- release publication trước admission;
- trust/official/OCOP fail-open.

### Wave 1 — Service constitution và integrity pilot

- Service Owner Charter và actor/channel/outcome map;
- authority registry và architecture ratchets;
- SSR/client runtime split, Owner Kernel và Interaction Kernel;
- pilot `/tim-kiem` trước homepage đang dirty;
- exact-artifact evidence skeleton.

### Wave 2 — Public read journey

- shell, homepage, catalog/search, map và detail;
- DiscoveryState, exact DTO, bbox/near/pagination;
- Adaptive Nocturne Fieldbook family grammar;
- public degradation và SLO instrumentation.

### Wave 3 — Private journey

- auth continuation, saved state, planner, publish/share;
- owner epoch, idempotency, revision, tombstone và disclosure;
- guest-to-account explicit transfer.

### Wave 4 — Governance jobs

- correct stale information;
- claim and maintain listing;
- official announcement draft-review-publish-expire/revoke;
- assertion policy, receipt, SLA, assisted path và operator queue.

### Wave 5 — Community và AdminCP

- SafetyCase, moderation, appeal và outcome;
- Admin overview/review/data/settings family recipes;
- remove authority gamification;
- operational metrics và review quality.

### Wave 6 — Production proof

- ASVS controls và security evidence;
- persistent SLI/error budget;
- migration ledger và N/N-1 compatibility;
- signed build-once archive, dark deploy, canary;
- rollback/restore/incident rehearsal;
- D6 production outcome evidence.

## 23. Những phần cắt và hoãn

### Cut

- microservice-like abstractions không có operational boundary;
- multiple theme/context/adaptive stores;
- generic universal page model hoặc mega route manifest;
- raw `$fetch` ngoài approved transport/stream adapters;
- decorative Dòng địa bàn, catalog hero trên task utility và generic SaaS card
  grammar;
- fake capability copy;
- public trust derived từ engagement;
- parallel release provenance lanes;
- scalar quality/Scorecard score làm admission verdict.

### Defer

- microservices/database-per-domain;
- multi-worker Uvicorn;
- Redis/PgBouncer bắt buộc;
- full RDF/claim graph;
- cold-offline navigation/API cache;
- semantic LLM cache;
- autonomous adaptive orchestration;
- owner self-edit trước scoped permission/revocation;
- public ranking/trending trước anti-Sybil evidence;
- SLSA L3 claim trước builder isolation proof.

## 24. Non-negotiable evidence gates

- Không một byte state của owner A render hoặc merge dưới guest/B.
- Async response chỉ apply khi owner, route, generation và fingerprint còn khớp.
- Không public plan field ngoài preview đã xác nhận.
- Không badge/JSON-LD/AI factual claim thiếu assertion hợp lệ.
- Không official item thiếu organization identity/source/time/scope.
- Không authority label suy từ likes, followers, XP, rank hoặc streak.
- Không page-level horizontal overflow tại 320 CSS px ngoài accessible 2D region.
- Focus không bị fixed chrome che; overlay stack đóng/restore theo LIFO.
- SSR initial query tạo đúng một upstream request và không refetch khi hydrate.
- 20 cold homepage calls tạo đúng một payload build.
- Mutation + audit + outbox commit hoặc rollback cùng nhau.
- Unexpected PG/CI skip bằng 0 trong admission verdict.
- Artifact digest, provenance, admission, runtime manifest và schema compatibility
  phải khớp trước promotion.
- Dark deploy tạo zero business side effect.
- Rollback flag phục hồi user journey trong năm phút hoặc chuyển sang artifact
  rollback/maintenance.
- Không gọi production-proven trước D6 evidence.

## 25. Thay đổi Constitution

Thay đổi một invariant trong tài liệu này cần:

1. problem statement và affected service outcomes;
2. security/privacy/trust impact;
3. architecture alternatives và lý do chọn;
4. migration/rollback plan;
5. updated evidence gates;
6. Service Owner approval;
7. spec revision và authority registry update.

Implementation không được âm thầm thay Constitution bằng code behavior hoặc
test snapshot.

## 26. Benchmark anchors

Kiến trúc này được đối chiếu ngày 2026-08-11 với các nguồn chính thức sau:

- GOV.UK Service Standard: whole problem, joined-up channels, accessibility,
  multidisciplinary ownership, performance và reliable operation;
- US Digital Services Playbook: whole experience, accountable leader và
  data-driven decisions;
- W3C WCAG 2.2, WAI-ARIA Authoring Practices và WAI Forms guidance;
- Nuxt 4, Vue SSR và Nitro 2 documentation;
- PostgreSQL 18, FastAPI và Pydantic documentation;
- Google SRE Book/Workbook, Web Vitals và OpenTelemetry semantic conventions;
- OWASP ASVS 5.0, NIST SSDF/Zero Trust, SLSA 1.2 và OpenSSF Security Baseline;
- NIST AI RMF/Generative AI Profile, Schema.org và Google structured-data
  policies;
- OECD citizen participation/open-government/public-communication guidance và
  UNESCO digital-platform governance guidance.

Các nguồn này định hình target và evidence model; chúng không phải chứng nhận
compliance hiện tại. Level, SLO, threshold hoặc control nào là lựa chọn sản phẩm
nội bộ đều phải được ghi rõ, không được gán nhầm là yêu cầu nguyên văn của một
chuẩn.

## 27. Tiêu chí hoàn tất Constitution

Tài liệu đạt trạng thái `reviewed-constitution` khi:

- người dùng xác nhận written spec phản ánh đúng kiến trúc đã chốt;
- không còn placeholder, TBD hoặc authority conflict chưa được quyết định;
- bảy spec trong portfolio có scope và dependency order rõ;
- Wave 0 blockers và non-negotiable gates được chấp nhận;
- bước tiếp theo được giới hạn ở spec số 1, không chuyển thẳng sang code.
