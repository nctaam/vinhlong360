# Audit toàn dự án VinhLong360 — 2026-08-31

Authority: config/release-authority.json

> STATUS: active — truth-sync `2026-09-05T09:48Z`, HEAD `edd9c07a954f7dc6ae88e983f51b8cbd0b106af2`. Báo cáo audit evidence-first này supersedes the working conclusions in `docs/2026-08-21-danh-gia-toan-du-an.md` where the evidence below is newer. Acceptance thực tế vẫn `NO_GO`, release verifier vẫn `BLOCKED`; không coi local deterministic probes là staging/production proof.
>
> Phạm vi: toàn repo ở branch `codex/correction-case-pilot`, gồm backend FastAPI, frontend Nuxt, dữ liệu catalogue, correction kernel, UGC/identity, AI/guardrails, storage, CI/CD, backup/restore, monitoring, legal copy và governance.
>
> Đây là audit kỹ thuật và vận hành, không phải ý kiến luật sư, pentest độc lập, kiểm định accessibility bằng người dùng thật, hay chứng nhận factual accuracy của catalogue.

## 0. Cách đọc và giới hạn bằng chứng

### Nhãn kết luận

- **Verified**: quan sát được trực tiếp từ mã, cấu hình, artifact hoặc lệnh tái lập trong phiên.
- **Unproven**: có thiết kế hoặc test liên quan nhưng chưa có bằng chứng runtime/production đủ mạnh.
- **Decision required**: không thể tự quyết bằng code; cần chủ dự án, DPO, luật sư hoặc owner vận hành chốt.
- **Stale artifact**: tài liệu cũ vẫn hữu ích để truy nguyên nhưng không được dùng làm bằng chứng hiện trạng nếu chưa tái xác minh.

### Phương pháp

- Đọc `CLAUDE.md`, architecture decisions, ROADMAP, handoff và các standard sống trước khi kết luận.
- Dùng graphify trên graph hiện có: **1.746 entities, 12.060 relationships, 33 itineraries**; traversal xuyên miền qua correction, identity, lifecycle, storage, deployment, monitoring, verification, public API, reports và moderation.
- Tái chạy `python scripts/deep_audit.py` và `python scripts/validate_data.py --json` ngày 2026-08-31.
- Đọc source và test tại các điểm tin cậy cao; đối chiếu lại 23 surface/flow theo Checklist Design, gồm correction/form, OTP/2FA, search, detail, feed/chat, settings/account, admin/audit, notifications, dashboard, report, privacy và maintenance (chi tiết ở mục 5.5).
- Không chạy full-suite trần vì chính repo ghi nhận lệnh đó tạo lỗi môi trường giả trên Windows; lần thử `python scripts/scorecard.py --no-append` không trả output sau hơn hai phút và đã dừng, do đó không dùng nó làm số đo mới.

### Giới hạn quan trọng

- Không có quyền truy cập production database, object store, CDN, DNS, GitHub Actions runner hoặc provider moderation/LLM trong phiên.
- Không có screenshot hoặc browser smoke capture mới; các kết luận giao diện dưới đây là **source-level**, không phải phán quyết pixel/render.
- `web/data.json` là export/seed, không chứng minh dữ liệu production hiện đang giống nó. `scripts/validate_data.py` đọc `web/data.json`, không đọc database runtime.
- Graphify cảnh báo skill metadata 0.9.29 trong khi package cài là 0.9.43; graph hữu ích cho topology nhưng không thay thế source/test evidence.

## 1. Bản đồ hệ thống và các ranh giới tin cậy

```text
                    ┌──────────────────────────────┐
                    │  Nuxt SSR / browser           │
                    │  public pages + correction UI│
                    └──────────────┬───────────────┘
                                   │ HTTPS / cookie / CSRF
                    ┌──────────────▼───────────────┐
                    │ FastAPI public/admin routers  │
                    │ cases · identity · UGC · chat │
                    └───────┬──────────┬────────────┘
                            │          │
                 ┌──────────▼───┐  ┌───▼────────────────┐
                 │ PostgreSQL    │  │ SQLite knowledge   │
                 │ SoT: cases,    │  │ dev/cache + seed   │
                 │ UGC, identity  │  │ (not UGC authority)│
                 └───────┬────────┘  └─────────┬─────────┘
                         │                     │
                 ┌───────▼────────┐   ┌────────▼─────────┐
                 │ reports, audit  │   │ data.json export │
                 │ lifecycle jobs  │   │ + prerender seed  │
                 └─────────────────┘   └──────────────────┘

       ┌────────────────────┐     ┌──────────────────────┐
       │ Object storage/CDN │     │ Telegram/Zalo bot    │
       │ public immutable    │     │ memory + egress      │
       │ media objects       │     │ + optional phone OTP │
       └────────────────────┘     └──────────────────────┘

       ┌────────────────────┐     ┌──────────────────────┐
       │ Scheduler/LLM loop  │     │ CI/CD + Nginx         │
       │ autonomous opt-in   │     │ deploy/backup/metrics │
       └────────────────────┘     └──────────────────────┘
```

### Những ranh giới cần giữ đúng

1. **DB-as-SoT**: PostgreSQL là authority cho production; SQLite chỉ là knowledge cache/dev; `data.json` không được ghi ngược đè edit production.
2. **Correction authority**: reporter input → public API → Postgres case store → evidence/decision → atomic publication → public projection.
3. **Trust metadata**: `attributes.verifiedAt` mới là bằng chứng kiểm chứng thực địa; `entity.verified` chỉ là cờ publish.
4. **Identity/lifecycle**: cookie capability, OTP, trusted devices, browser storage, bot memory, reports và media phải cùng một chính sách retention/erasure, nhưng hiện chưa cùng một registry.
5. **Operational authority**: health, metrics, backup, restore, release và rollback phải chứng minh cùng một artifact; hiện còn nhiều đường “có script” nhưng chưa chứng minh chạy cùng nhau.

## 2. Phán quyết điều hành

VinhLong360 có một lõi correction-case đáng giữ: mô hình authority rõ, payload riêng tư được mã hóa, capability cookie/CSRF, idempotency, rate-limit, lease/CAS, publication atomic và nhiều adversarial tests. Đây là nền tốt cho một closed pilot có kiểm soát.

Nhưng trạng thái hiện tại **chưa đủ để gọi là production-ready**. Nguy cơ lớn nhất không phải một lỗ hổng đơn lẻ; đó là hệ thống có thể nói “đã kiểm chứng”, “đã xoá”, “đã backup”, “đang monitor” hoặc “đã gửi OTP” trong khi một tầng khác không thực sự hoàn tất. Đó là failure mode của niềm tin, không chỉ của UX.

### Scorecard định tính

| Lát cắt | Đánh giá | Lý do chính |
|---|---|---|
| Product/value | Amber | Định vị Vĩnh Long mới rõ, nhưng catalogue chưa có ảnh, noindex chủ động và chưa có bằng chứng usage/retention/activation. |
| Data/trust | Red | 1.406 timestamp đảo, 874 entity approximate, 32 orphan, image metric không nhận local paths; schema `verifiedAt` lệch tầng. |
| Backend/API | Red | Correction kernel tốt, nhưng search/pagination làm mất discoverability, cache coherence chưa khép, contract FE/BE, `/api/stats`, queue key và production environment còn rủi ro. |
| Security/privacy | Red | raw input vào logger riêng, bot giữ hội thoại, fallback credential, prompt-injection miss, export thiếu, và unified search có public-cache risk. |
| AI/egress | Amber-Red | Fail-closed moderation là điểm cộng; detector chưa chặn câu phổ biến và policy media mâu thuẫn. |
| Frontend/UX/accessibility | Amber | Form có review/error summary/loading; phone verification thiếu đường nhập mã và có lỗi contract `reportedValue`. |
| Operations/reliability | Red | Backup/restore khác định dạng, monitoring thiếu target/alerting, homepage single-flight hỏng dưới burst, scheduler chưa có leader và deploy workflow chưa rollout/rollback thật. |
| Compliance/governance | Red | Legal copy hứa SLA/residency chưa có durable control; cần rà theo luật hiện hành và quyết định media/commerce. |
| Delivery/release | Red | Dependency ranges rộng, image/base tags trôi nổi, audit dependency non-blocking, migration history thiếu checksum/lock chứng minh. |

**Kết luận:** closed pilot chỉ **Go có điều kiện** sau khi đóng các P1 và chứng minh acceptance evidence. Public launch hiện **No-Go**.

## 2.1 Ma trận các module đã tách

Đếm runtime trên `server.app.routes` ngày 2026-08-31 cho thấy việc tách file đã tạo ra topology rõ hơn, nhưng ownership của state, cache, side effect và auth chưa đồng đều. “Có router riêng” không đồng nghĩa “có boundary độc lập”.

| Module | Route runtime | SoT/owner chính | Auth boundary | Cache/state/side effect | Test hiện có | Verdict |
|---|---:|---|---|---|---|---|
| `cases/` | 24 | PostgreSQL case store; publication projection | public capability + admin scope; composition root wiring | encrypted payload, receipt, outbox, publication; cần rollback wiring | domain/store/erasure nhiều, nhưng thiếu late-failure wiring và evidence temporal | Lõi tốt, P1 ở transactional wiring/evidence |
| `community/` | 114 | PostgreSQL UGC/social | user/CSRF trong public; inherited admin dependency trong admin | moderation, feed/trending/leaderboard cache, JSONL comment reports | PG integration phong phú; thiếu CAS race, scheduled consumer, collection visibility | Bề mặt lớn nhất; Red do state machine phân mảnh |
| `entities/` | 70 | PostgreSQL entities + in-memory `knowledge` projection | inherited admin dependency; public projection policy | detail cache, KB sync, image/object side effects | CRUD/FTS/source guards; thiếu audit mọi mutation, saga image, snapshot parity | P1/P2 ở accountability và coherence |
| `identity/` | 30 | PostgreSQL users/sessions/2FA | handler + CSRF lazy dependency; session binding | OTP, sessions, trusted device, export/erasure | auth/erasure/2FA nhiều; export completeness và cleanup scheduler chưa đủ | Bảo mật nền khá, lifecycle chưa đóng |
| `chat/` + `chat_identity.py`/`chat_usage.py` | 4 | memory + exact/semantic cache + provider | owner cookie hoặc authenticated user; feedback receipt | stream/SSE, semantic leases, prompt/memory, tool egress | privacy/stream/resilience có; thiếu cross-process cache/import parity | Tốt về privacy cục bộ, rủi ro topology và singleton |
| `llmops/` | 50 | analytics, optimizer, vector/semantic stores | nhiều route gọi `require_admin` bên trong handler | learning/evolution/cache/checkpoints/traces | chủ yếu AST/source + smoke; OpenAPI/security graph chưa đủ | P2 hidden-auth và side-effect audit |
| `itineraries/` | 8 | PostgreSQL itinerary rows; public read projection | public read; inherited admin dependency | public HTTP cache 5 phút; CRUD không purge/audit | optimizer/schedule tests tốt; thiếu mutation→cache test | Chức năng ổn, ops boundary yếu |
| `siteops/` | 24 | DB + files/backup/metrics | inherited admin dependency; public settings/announcement read | backup subprocess, quality queues, settings history | launch-safety và source guards; thiếu PG health/export snapshot | P2 do observability/export consistency |

Hai điểm đặc biệt: (1) `community.api` và `public_api` vẫn có coupling ngược qua JSONL/report helpers; (2) `features.py` nạp `vector_search` dạng flat còn `semantic_cache.py` nạp `agent.vector_search`, nên topology import có thể tạo hai singleton khác nhau. Những điểm này làm các test “router đã tách” xanh nhưng chưa chứng minh state ownership.

### 2.2 Hồ sơ sâu từng module

Ma trận trên trả lời “module nào có gì”; phần này trả lời câu hỏi khó hơn: module đó có thực sự là một boundary vận hành độc lập không, failure mode nằm ở đâu, và test hiện nay đang chứng minh được đến mức nào.

#### `cases/` — lõi trust, nhưng composition root còn mutable

- Đây là module trưởng thành nhất về domain: receipt, encrypted payload, idempotency, lease/CAS, transitions, publication và outbox đã được tách thành các lớp có tên rõ (`domain`, `store`, `service`, `publication`, `work_control`, `lifecycle`).
- Điểm yếu nằm ở đường ghép: các `configure_*` ghi dependency vào nhiều global khác nhau. F-40 chứng minh late failure có thể để lại capability nửa sống; F-41 chứng minh evidence helper không phải invariant bắt buộc của decision path; F-53 chứng minh side effect SMS vẫn chỉ at-least-once.
- Bộ test cases rất rộng, nhưng phần lớn test wiring dùng fake/monkeypatch và test PG được skip nếu thiếu DSN. Vì vậy “kernel có nhiều test” không đồng nghĩa “browser → PG → provider → projection” đã có một proof duy nhất.
- Quyết định kiến trúc cần chốt: composition root phải commit một bundle bất biến; evidence phải là typed/provenance record; outbox phải khai báo rõ exactly-once không thể có nếu provider không hỗ trợ idempotency.

#### `community/` — bề mặt lớn nhất, state machine bị chia nhỏ

- 114 route dồn vào hai file lớn (`api.py` khoảng 220 KB, `admin_api.py` khoảng 80 KB). Việc tách router đã giúp route ownership, nhưng chưa tách đủ policy, repository và transition engine; một thay đổi feed/moderation/collection dễ đi xuyên nhiều state store.
- F-42, F-49 và F-55 cùng chỉ vào một họ lỗi: trạng thái được ghi nhưng consumer/transition/visibility không khép kín. Scheduled post có timestamp nhưng không có worker; moderation thiếu CAS; collection nhận bản ghi mà public JOIN cố ý giấu.
- PG integration test có các case schedule/list/cancel, nhưng không có test worker “đến hạn” và race hai moderator. Đây là khoảng cách giữa CRUD correctness và lifecycle correctness.
- Cần xem community như một state machine có bảng chuyển trạng thái, actor, version, notification và public projection; không coi từng endpoint POST/PATCH/DELETE là một feature độc lập.

#### `entities/` — authority dữ liệu chưa đồng nhất với projection chất lượng

- `entities/api.py` và `admin_api.py` đều lớn, cùng chạm PostgreSQL, `knowledge._entities`, detail cache, image suggestion và relationship graph. F-44/F-46 cho thấy actor/audit và snapshot version không đi cùng mọi đường ghi/đọc.
- F-47 và F-48 mở rộng rủi ro sang media: approval là saga nhiều bước; ingest là SELECT-then-INSERT. Đây là nơi “entity đã có trong DB” nhưng chưa chắc object, credit, KB và audit cùng trạng thái.
- F-54 là lỗi chức năng trực tiếp: stale queue gọi method không tồn tại. F-45 là lỗi đo lường: quality dashboard có thể báo 10.000% ở trường hợp đầy đủ.
- Test CRUD/schema/source guard khá nhiều, nhưng thiếu invariant cross-worker: mutation ở worker A phải làm dashboard, public detail, search và KB ở worker B thấy cùng generation.

#### `identity/` — auth boundary tốt hơn lifecycle boundary

- Module có nền bảo mật đáng kể: session binding, OTP/2FA, trusted device và account deletion transport đều có test riêng. Đây là lý do chưa gắn P0 cho identity.
- Tuy nhiên identity là điểm phát sinh dữ liệu nhạy cảm nhất, trong khi export/erasure/report/bot/browser storage chưa cùng một registry (F-06, F-10, F-11, F-34). “Đăng nhập an toàn” không kéo theo “chủ thể dữ liệu kiểm soát được toàn bộ dấu vết”.
- Nhiều test PG chỉ chạy khi có DSN disposable; môi trường mặc định của conftest ép SQLite và tắt scheduler. Do đó cleanup thật, bảng `user_sessions`, notification và retention cần acceptance trên PG chứ không chỉ unit transport.
- Rủi ro sản phẩm: nếu policy không phân biệt secret/auth material với content phải export, đội vận hành sẽ hoặc trả quá nhiều bí mật hoặc trả thiếu nhưng vẫn gọi là “all user data”.

#### `chat/` — privacy transport mạnh, topology cache yếu

- Chỉ 4 route runtime nhưng `chat/api.py` khoảng 144 KB và điều phối nhiều optional subsystem (guardrail, semantic cache, memory, tool, optimizer, tracing, cost). Đây là “module nhỏ trên wire, lớn trong graph”.
- Privacy boundary đã có test streaming, chunk split, cancellation, fallback và không ghi sink khi redaction fail; đây là một điểm mạnh thật sự.
- F-38, F-56, F-59 và F-60 cho thấy lớp sau boundary vẫn có rủi ro: shared cache có thể cá nhân hóa, import namespace tạo singleton kép, TF-IDF stats drift, L2 file cache không an toàn đa process.
- Acceptance đúng phải đo cả privacy và topology: hai owner khác nhau, hai process khác nhau, cache hit/miss, provider lỗi giữa stream, restart giữa lúc ghi semantic cache.

#### `llmops/` — route đã dời, security metadata chưa dời đủ

- 50 route trong `llmops/api.py` đã được kéo khỏi `server.py`; test route-count/module ownership bắt được duplicate handler và import ngược trực tiếp.
- F-50 cho thấy dời source không đồng nghĩa dời security contract: auth nằm trong thân handler nên OpenAPI/dependency graph không biểu diễn đúng. Đây là rủi ro review và tooling, ngay cả khi request hiện tại bị chặn.
- LLM-ops còn chạm checkpoints, vectors, learning/evolution và image recognition — các side effect có tính phá huỷ hoặc tốn chi phí. AST/source tests chưa thay thế được authorization matrix, idempotency và audit của từng thao tác.

#### `itineraries/` — logic domain ổn, public projection chưa có invalidation

- Generator/selection/schedule/multiday/optimizer đã tách khá sạch; test algorithm nhiều hơn số route runtime có thể gợi ý.
- F-43 là seam vận hành: admin mutation ghi DB nhưng public cache 5–15 phút và audit actor không được nối vào. Với itinerary du lịch, stale không chỉ là UX; nó có thể đổi giờ mở cửa, tuyến hoặc điểm dừng sau correction.
- Cần acceptance theo phiên bản itinerary: mutate → GET qua proxy/CDN → generate lại → MCP/public cùng version; không chỉ assert hàm optimizer trả đúng list.

#### `siteops/` — nhiều control có tên, ít control có chứng cứ end-to-end

- `siteops` gom health, backup, export, settings, announcements và data quality. Đây là module mà operator tin để biết hệ thống đang an toàn.
- F-57 làm endpoint health có thể 500 vì tên bảng; F-58 làm announcement incident bị cache; F-61 làm backup failure khóa lần thử; các lỗi này nguy hiểm vì làm control plane nói sai về chính nó.
- Test boundary/source guard chứng minh route đã mount và kế thừa auth; chưa chứng minh PG schema thật, subprocess failure, proxy cache và notifier thật. Với siteops, “không throw trong unit test” không phải acceptance đủ.

### 2.3 Điểm mù do tách module

Các bộ test hiện tại rất tốt trong việc giữ route count, import direction, symbol re-export, schema shape và isolated unit behavior. Nhưng chúng chưa tự chứng minh các thuộc tính liên module sau:

| Điểm mù | Vì sao test module riêng vẫn xanh | Failure đã chạm | Bằng chứng cần bổ sung |
|---|---|---|---|
| Transaction/composition | Mỗi `configure_*` được assert riêng; không có late-failure rollback trong baseline | F-40 | Inject failure ở từng bước, assert toàn bộ global/route dormant |
| State machine consumer | Endpoint ghi timestamp/status hợp lệ là đủ để CRUD test xanh | F-42, F-49, F-55 | Worker due, CAS race, public visibility và notification audit |
| Cross-store truth | DB fixture và in-memory fixture được test riêng | F-09, F-46, F-56 | Mutation → DB/KB/cache/search trên process khác cùng generation |
| External side effects | Provider/object/subprocess thường được mock | F-47, F-53, F-61 | Crash window, retry, orphan cleanup, provider idempotency |
| Auth metadata | Handler tự gọi guard nên request test có thể bị chặn | F-50 | OpenAPI/dependency graph/runtime route matrix + scope/CSRF |
| Concurrency/topology | `threading.Lock` đủ trong một process test | F-31, F-36, F-60, F-62 | Multi-worker/replica, kill/restart, shared lease/cache |
| Cache invalidation | Assert DB mutation hoặc hàm invalidate đơn lẻ | F-32, F-38, F-43, F-58 | Read-through proxy ngay sau mutate cho từng consumer |
| Production schema/ops | SQLite, env test và scheduler disabled làm test deterministic | F-13, F-14, F-15, F-57 | PG + Nginx/proxy + subprocess + alert/restore artifact thật |

Vì vậy coverage nên được báo theo **boundary evidence**, không chỉ theo line/route/module coverage. Một module tách thành công khi ownership, transaction, state transition, auth metadata, cache generation và operational evidence cùng đi qua boundary đó.

## 3. Bằng chứng dữ liệu và graph

### 3.1 Điều đã làm tốt

- Không có broken relationship, duplicate relationship, self-loop, near sai khoảng cách, `produced_in` cross-area hoặc itinerary integrity error.
- 1.746 entity có 100% place-coordinate coverage ở nhóm place; mọi area hiện hợp lệ.
- 33 connected components, component lớn nhất 1.714 entity; graph không phải một đống cạnh hỏng.
- Public projection có ý thức loại provisional entity thay vì đưa mọi bản ghi nháp ra ngoài.

### 3.2 Những gì số đo không nói

- **Quality score trung bình 88.1** là heuristic về completeness/shape; không chứng minh tên, số điện thoại, giờ mở cửa, mùa vụ hoặc địa chỉ là đúng ngoài đời.
- **1.406 timestamp inversion** làm yếu audit chronology; không thể dùng `created_at/updatedAt` hiện tại để suy ra ai sửa gì trước/sau.
- **874 entity trong 40 cụm coordinate approximate** có thể làm map, nearby và SEO địa phương nhìn như nhiều địa điểm ở một tâm giả; cờ `coords_approximate` phải xuất hiện ở mọi consumer, không chỉ một badge.
- **32 orphan entity** và **7 entity thiếu location** là khoảng trống discoverability, không chỉ lỗi cosmetic.
- **5 exact-normalized duplicate names + 37 near-duplicate pairs** là nguy cơ merge nhầm, canonical URL collision và correction gắn sai entity.
- **150 duplicate source URLs** làm giảm diversity/provenance; một nguồn lặp lại không phải là 150 bằng chứng độc lập.
- **0% image coverage** theo validator không đồng nghĩa không có media: raw export có 57 `images` path nội bộ (`/img/...`), nhưng checker chỉ nhận URL bắt đầu bằng `http`. Đây là contract drift của công cụ đo; media completeness/credit vẫn chưa được chứng minh.
- 1 text join lỗi (`word.next`) và 1 phone sai format cho thấy pipeline content chưa có invariant cuối cùng.

## 4. Findings ưu tiên

**Tổng hợp hiện trạng:** 73 findings có ID liên tục F-01–F-73; **0 P0, 28 P1, 45 P2**. Trong đó 8 P1 mới (F-40, F-41, F-42, F-44, F-47, F-49, F-53, F-69) tập trung vào wiring, state transition, audit, external side effect và integrity của release evidence; 12 P2 mới (F-61, F-62, F-63–F-68, F-70–F-73) chạm vào control-plane, cache topology, design-system governance, tài liệu vận hành, chat chronology và legal disclosure. Các nhãn `Verified`, `Unproven risk` và `Decision required` vẫn được giữ riêng; không cộng rủi ro chưa chứng minh vào P0.

### P0 — chưa quan sát thấy

Không có P0 được chứng minh trong phiên. Điều này không có nghĩa đã qua pentest; nó chỉ có nghĩa chưa thấy failure đủ trực tiếp để gắn mức catastrophic.

### P1 — phải đóng trước closed pilot/public claim

| ID | Finding và tác động | Bằng chứng | Trạng thái | Owner | Acceptance evidence |
|---|---|---|---|---|---|
| F-01 | **Correction intake/phone verification đứt hành trình.** UI phát OTP trước khi case/access cookie tồn tại; lỗi bị nuốt; có hàm verify nhưng không có UI nhập mã hoặc gọi thành công `/contact/verify`. Người dùng có thể tin rằng đã verify trong khi hệ thống chưa có proof. | `web-nuxt/pages/yeu-cau/sua-thong-tin.vue:68`; `web-nuxt/composables/useCorrectionCases.ts:210`; `agent/cases/public_api.py:472` | Verified | Frontend + cases | Browser smoke: nhập số → gửi OTP → nhập mã → verify success/error/resend; request phải gắn đúng access context và không nuốt lỗi. |
| F-02 | **`reportedValue` optional ở FE nhưng bắt buộc ở BE.** Form có thể hợp lệ rồi POST nhận 422, tạo cảm giác lỗi ngẫu nhiên và mất draft. | `web-nuxt/components/cases/CorrectionIntakeForm.vue:93`, `:203`; `agent/cases/public_api.py:194` | Verified | Frontend + API | Contract test chia rõ “không biết giá trị hiện tại” và “phải gửi giá trị hiện tại”; FE/BE cùng schema và error copy. |
| F-03 | **Production compose không ép `ENVIRONMENT=production`.** Default ở config là development; stack có thể chạy “prod-like” nhưng dùng guard/CORS/secret behavior của dev. | `agent/config.py:80`; `docker-compose.prod.yml` | Verified | Ops | Render compose + startup assertion fail-closed nếu environment không phải production; test CORS/secret guards trên image release. |
| F-04 | **Auto-promotion đánh đồng engagement với verification.** Query hit ≥3 có thể gán `status=verified, verified=True` mà không có human evidence/`attributes.verifiedAt`, trái trust policy. | `agent/kb_curation.py:256-282`; `CLAUDE.md §1.7` | Verified; autonomous mặc định đang off | Content/governance | Không có đường nào set verified nếu thiếu evidence level + actor + `verifiedAt`; test bật scheduler vẫn không auto-claim. |
| F-05 | **Raw user input lọt vào logger ngoài structured redaction.** Query/message có thể chứa PII, secrets hoặc prompt injection; logger riêng không đi qua middleware redaction. | `agent/scheduler.py:41`; `agent/learn_loop.py:56,345,487`; `agent/auto_learn.py:638`; `agent/bot_gateway.py:40,624,686,790`; `agent/middleware.py:53` | Verified | Security/platform | Log fixture có phone/token/prompt injection → output chỉ còn digest/redacted fields; retention và access policy được kiểm. |
| F-06 | **Bot giữ raw hội thoại trong memory 24h.** Tối đa 20 message/session và 5.000 session; chưa chứng minh account-erasure, identity unlink hoặc policy riêng cho Telegram/Zalo. | `agent/bot_gateway.py:252-299` | Verified | Bot/privacy | Test TTL, bounded memory, explicit purge theo identity, process restart; DPA/notice mô tả retention. |
| F-07 | **Prompt-injection detector bỏ lọt câu phổ biến.** Threshold 0.15 nhưng `repeat your system prompt` chỉ ~0.037, `ignore previous instructions` ~0.0741, `Show me your system prompt` không match. Bộ test dài/gộp tạo false confidence. | `agent/guardrails.py:47`; runtime probes ngày 2026-08-31 | Verified | AI/security | Corpus test tối thiểu 50 biến thể ngắn/dài/đa ngôn ngữ; block/neutralize đúng; đo false positive/negative và log an toàn. |
| F-08 | **Admin provisional queue đọc sai key.** Curation trả `provisional_count`, admin đọc `pending`, nên badge/alert có thể luôn 0 dù queue có dữ liệu. | `agent/kb_curation.py:292-298`; `agent/admin.py:1140-1143,1211-1215` | Verified | Admin/content | API contract test và UI fixture có provisional entity → badge count >0, link tới queue và empty state phân biệt. |
| F-09 | **Schema trust drift: `verifiedAt` sai tầng dữ liệu.** `web/data.json` có top-level `verifiedAt` nhưng `attributes.verifiedAt` bằng 0; database đọc nested và loại top-level khi projection. Bằng chứng kiểm chứng có thể tồn tại trong artifact nhưng biến mất ở runtime. | `web/data.json`; `agent/database.py:2486-2492,2530`; `CLAUDE.md §1.7` | Verified | Data/platform | Migration/normalizer canonicalize một tầng; round-trip DB→export→public projection giữ `verifiedAt`; test cấm claim khi thiếu nested evidence. |
| F-10 | **Report architecture phân mảnh.** Comment reports ghi `reports.jsonl`; entity/info reports đi qua admin; post/user reports ở PostgreSQL. Erasure registry không phủ JSONL, object storage hay bot session. Dashboard, retention và delete có thể nhìn các vũ trụ khác nhau. | `agent/community/api.py:2665-2683`; `agent/admin.py:1419`; `agent/data_lifecycle.py:26-53` | Verified | Trust/privacy | Một report ID duy nhất, registry source-of-truth, export/delete audit toàn bộ sink; chaos test xoá một user và truy vết không còn bản định danh. |
| F-11 | **Account cleanup chưa được scheduler gọi đầy đủ.** `cleanup_expired_data()` tồn tại nhưng `task_session_cleanup()` hiện chỉ dọn `user_sessions`, `otp_sessions`, login history và posts; không gọi helper này để dọn pending 2FA/trusted devices. Các browser storage key (favorites/recent/drafts/search recents) cũng nằm ngoài server-side cleanup. | `agent/identity/api.py:214-227`; `agent/scheduler.py:1000-1098`; các key local/session storage trong `web-nuxt` | Verified | Identity/privacy | Job định kỳ bounded/idempotent; deletion export liệt kê mọi store; test expiry và account erasure end-to-end. |
| F-12 | **Xoá DB không đồng nghĩa xoá media/CDN.** Low-level object delete có nhưng chưa chứng minh mọi delete path gọi nó; upload dùng `public, max-age=31536000, immutable`, làm bản cũ tiếp tục sống ở edge. | `agent/storage.py:151-155,196-209` | Unproven risk | Storage/ops | Delete propagation test: DB row, object, CDN URL và cache purge đều biến mất/được invalidated trong SLA; audit mọi caller. |
| F-13 | **Backup/restore/offsite không cùng định dạng.** Daily backup tạo `*.sql.gz`, restore drill tìm `.dump/.backup`, offsite script không tìm `*.sql.gz`; job có thể xanh nhưng artifact không restore được. | `scripts/ops/backup_db_daily.sh:10-28`; `scripts/restore_drill.py:30-45`; `scripts/backup_offsite.py:36-52` | Verified | Ops | Một artifact duy nhất đi qua backup → integrity check → offsite → restore vào DB rỗng → row/checksum verification; failure làm job đỏ. |
| F-14 | **Monitoring chưa chứng minh alerting.** Prometheus scrape `node-exporter:9100` nhưng Compose không có service; `/metrics` admin-gated có thể trả 401; không thấy Alertmanager/rules/notifier tổng quát. Watchdog chủ yếu log/restart. | `scripts/monitoring/prometheus.yml:5-20`; `agent/public_api.py` metrics gate; `scripts/ops/watchdog.sh:37-65` | Verified | Ops/SRE | `promtool check`, target UP, 401/200 auth test, alert rule firing vào notifier thật và runbook người nhận. |
| F-15 | **Deploy workflow chưa deploy VPS.** Workflow precheck informational, tạo GitHub Release; không SSH/remote compose/rollout/rollback; backup và health check `continue-on-error`. | `.github/workflows/deploy.yml:90-199` | Verified | Release/ops | Staging rollout thật với immutable image/archive, migration gate, smoke, rollback và evidence URL; bỏ `continue-on-error` ở gate bắt buộc. |
| F-16 | **Legal/transparency copy chưa có durable control.** Copy hứa xử lý 48h/24h; chưa có assignee, SLA clock, escalation, audit hay storage residency tương ứng. R2 region `auto` không tự chứng minh lưu trữ Việt Nam. | `web-nuxt/utils/legalContent.ts:80-82`; `agent/public_api.py:3016-3048`; `agent/storage.py:49-53` | Decision required | Owner + legal/DPO | Chốt wording với luật sư; ticket có owner/deadline/escalation; probe residency/processor/subprocessor; dashboard SLA thực. |
| F-17 | **Accountability của correction chưa bao phủ hai phía.** Kernel có receipt/review và statement of reasons, nhưng người bị ảnh hưởng không có đường thông báo hai chiều/takedown audit như một policy hoàn chỉnh. | `agent/cases/*`; old external review in `docs/2026-08-21-danh-gia-toan-du-an.md` | Unproven/decision | Trust/product | Decision table: ai được báo, khi nào, nội dung tối thiểu, appeal, redaction, retention; test từng disposition. |
| F-32 | **Reload/admin write không invalidates toàn bộ cache phụ thuộc entity.** `/reload` và `_sync_kb()` xoá LLM response cache, place cache và KB context nhưng không gọi semantic cache invalidation, không xoá `_REVIEW_STATS_CACHE` và `_similar_cache`. Các cache này có TTL 300 giây (semantic L2 có thể lâu hơn), nên sau correction/takedown vẫn có thể trả review/similar hoặc câu trả lời cũ; điều này đụng trực tiếp correction authority và erasure. | `agent/server.py:1047-1061`; `agent/admin_common.py:58-81`; `agent/entities/api.py:943-1129`; `agent/semantic_cache.py:375-486`; `agent/features.py:167-172` | Verified | Trust/platform | Một `invalidate_entity(entity_id)`/generation bump chung cho mọi cache; test sửa, takedown, xoá entity rồi đọc chat/review/similar ngay lập tức và xác nhận không còn snapshot cũ; test L1/L2/Redis. |
| F-34 | **Data export tự nhận là “all user data” nhưng thiếu nhiều bảng và im lặng cắt 5.000 dòng.** Export không có `user_plans`, notifications, reports, login history, consent/privacy, trusted devices/2FA metadata, moderation appeals, post edit history, collection items; posts còn bỏ images/draft/scheduled/updated fields. Mọi query dùng `LIMIT 5000` nhưng không trả cờ `truncated`/cursor. Đây là failure của quyền truy cập dữ liệu và khả năng tự kiểm tra/xoá dữ liệu, dù một số secret/auth material có thể cần loại trừ có chủ đích. | `agent/identity/api.py:1618-1787`; `init.sql:142-329,468-478`; `agent/migrations/007_user_plans.sql,017_cover_and_login_history.sql,018_privacy_settings.sql,021_notification_preferences.sql,023_consent_log.sql,035_moderation_appeals.sql,046_post_edit_history.sql,066_two_factor_auth.sql,067_trusted_devices.sql,049_user_collections.sql` | Verified; scope legal cần chốt | Identity/privacy/legal | Data inventory phân loại “export bắt buộc / secret loại trừ / retention-only”; export có manifest/schema/version, per-table counts, cursor hoặc explicit truncation; test fixture >5.000 rows và đối chiếu với erasure registry. |
| F-38 | **Unified search đánh dấu response là public dù payload phụ thuộc người xem.** Route nhận `get_current_user`, gọi `_enrich_all(posts, user)` để thêm `is_liked`/`is_bookmarked`, áp block/mute predicates cho post/user search, nhưng trả `Cache-Control: public` và không có `Vary: Authorization`/owner namespace. Một shared cache/CDN có thể phục vụ trạng thái tương tác hoặc tập kết quả của user A cho user B. | `agent/public_api.py:1348-1415,1555-1614`; `agent/community/api.py:149-197`; `agent/public_api.py:1614-1616` | Verified risk | Security/web/platform | Response cá nhân hóa phải `private, no-store` hoặc cache key gồm identity + filter; thêm header contract test với Authorization và proxy integration test chứng minh không cross-user. |
| F-40 | **`cases.wiring` không thực sự all-or-nothing.** Nếu một `configure_*` thất bại ở bước cuối, các module gọi trước đã ghi global dependency state nhưng `except` chỉ trả `False`, không rollback/reset. Probe monkeypatch `configure_case_contact` ném lỗi cho thấy public/admin/publication vẫn còn `_SERVICE`/`_DATABASE`/`_CRYPTO` khác `None` dù hàm báo kernel dormant. Capability có thể ở trạng thái half-wired trái claim fail-closed. | `agent/cases/wiring.py:77-141`; late-failure monkeypatch probe 2026-08-31 | Verified | Cases/platform | Wiring transactional: build dependency bundle tạm rồi commit một lần, hoặc reset toàn bộ khi lỗi; test lỗi ở từng bước xác nhận mọi global về `None` và route không nhận intake. |
| F-41 | **Evidence temporal/scope invariant không nối vào decision path.** Helper `usable_evidence()` có lọc scope, observed/expiry nhưng `decide_item()`/`validate_decision()` dùng toàn bộ evidence đã load. `add_evidence()` chỉ chặn `observed_at` ở tương lai, không chặn effective date tương lai, expiry trước effective, datetime naive hay scope sai. Evidence chưa có hiệu lực/hết hạn/sai scope có thể hỗ trợ ruling nếu lọt vào DB. | `agent/cases/correction.py:86-96,195-213,401-423,449-481`; `agent/cases/admin_api.py:646-676` | Verified source-level trust risk | Cases/trust | Decision bắt buộc gọi `usable_evidence` với scope yêu cầu; reject naive/future-effective/expiry-order sai; test stale, wrong-scope, future evidence không thể publish/correct và API trả 422 rõ ràng. |
| F-42 | **Scheduled community post có trạng thái nhưng không có consumer publish.** `schedule_draft()` chuyển `is_draft=FALSE`, giữ `moderation_status='pending'` và trả success; không tìm thấy worker/task nào đọc `scheduled_at`. Feed chỉ lấy `approved`, còn list/cancel chỉ nhìn thời điểm tương lai, nên bài đến hạn có thể biến mất khỏi cả lịch và feed mà không có outcome. | `agent/community/api.py:696-734,737-791`; `agent/scheduler.py:1329-1357`; `rg scheduled_at` không thấy consumer | Verified | Community/SRE | Worker có lease/CAS, moderation ngay trước publish, retry/failed state và timezone rõ; test scheduled→due→approved/rejected, restart/concurrent worker không publish trùng. |
| F-44 | **Entity mutation audit không đồng nhất.** `update_entity()` dùng `upsert_entity_with_audit`, nhưng create/delete, image/media, place assignment, relationships và bulk actions phần lớn gọi `upsert_entity`/`delete_entity`/`add_relationship` không truyền actor/provenance. Delete destructive có thể không có entity history, khiến không trả lời được ai đã thay đổi projection. | `agent/entities/admin_api.py:513-605,614-702,748-870,1076-1090`; `agent/database.py:1424-1460` | Verified | Content governance | Mọi mutation có actor, reason, before/after, correlation ID; audit và mutation cùng transaction; bulk có per-item outcome; test delete/relationship/media và replay audit. |
| F-47 | **Approve image suggestion là saga không có claim/idempotency/compensation.** Flow upload object → upsert entity → mark suggestion approved → sync KB. Upload thành công rồi DB fail tạo orphan; DB thành công rồi queue update fail tạo entity public nhưng suggestion pending; retry có thể attach/credit lặp. `mark_status()` không yêu cầu current status pending. | `agent/entities/admin_api.py:1190-1290`; `agent/image_suggestions.py:256-280` | Verified | Entities/storage | Claim suggestion bằng atomic CAS, idempotency key, object metadata/cleanup saga và retry test với injected failure ở từng bước; credit không nhân đôi. |
| F-49 | **Moderation approve/reject và appeal không có CAS trạng thái.** `UPDATE` chỉ theo ID hoặc SELECT kiểm tra trước rồi UPDATE, không ràng buộc current status. Hai operator có thể ghi approve/reject cuối cùng theo last-write-wins và phát hai notification/audit; image suggestion cũng unconditional. | `agent/community/admin_api.py:446-500,928-990`; `agent/entities/admin_api.py:1241-1297` | Verified | Community/entities moderation | Atomic state transition `... WHERE status IN (...) RETURNING`; xung đột trả 409, chỉ một outcome/notification/audit thắng; concurrency test hai moderator. |
| F-53 | **Case outbox chỉ at-least-once ở provider không có idempotency.** Code commit lease trước khi gửi giúp tránh duplicate giữa worker đang sống, nhưng crash sau `provider.send()` và trước `_settle(...); conn.commit()` làm lease hết hạn và gửi SMS lại. `delivery_key` chỉ log nội bộ, eSMS payload không mang token dedup. | `agent/cases/outbox.py:90-99,180-228`; `agent/sms_provider.py:102-173` | Verified residual risk | Cases/notifications | Provider-side idempotency hoặc durable send receipt trước side effect; nếu không thể thì copy/UX phải chấp nhận at-least-once, có duplicate-cost metric và test crash window. |
| F-69 | **Full-suite verifier có thể tuyên bố `HẾT-DIFF` dù còn `ERROR`.** Harness trong scratchpad chỉ regex các dòng `^FAILED (\S+)`, không thu `ERROR`, không fail theo `pytest` return code và không lưu danh sách error/collection failure. Artifact cuối ghi `15 failed ... 12 errors` nhưng vẫn in `HẾT-DIFF`; synthetic reproduction với 1 `FAILED` + 1 `ERROR` cũng cho kết quả HET-DIFF. Vì vậy “0 regression” hiện chỉ là claim trên tập failed, không phải trên toàn bộ test outcome; 12 errors chưa được phân loại là môi trường hay lỗi sản phẩm. | `external scratchpad/fullsuite.py` (unversioned temp artifact, inspected 2026-08-31); `docs/2026-08-31-ban-giao-tiep-tuc.md:25-47`; artifact `tasks/b3p3a0fbl.output`; synthetic parser probe 2026-08-31 | Verified release-evidence integrity risk | QA/release | Đưa harness vào repo; parse `FAILED`, `ERROR`, collection/interrupt và return code; lưu JSON gồm counts + nodeids + environment/disk; `HẾT-DIFF` chỉ hợp lệ khi mọi nhóm outcome ngoài allowlist đều rỗng; chạy lại 12 errors và phân loại từng node. |

### P2 — phải đóng trước public launch hoặc trước khi scale

| ID | Finding và tác động | Bằng chứng | Trạng thái | Owner | Acceptance evidence |
|---|---|---|---|---|---|
| F-18 | **Credential fallback yếu.** PostgreSQL và Grafana có fallback dev/admin; nếu env thiếu, stack có thể khởi động với secret đoán được. | `docker-compose.yml:7,43,163` | Verified | Ops/security | Production startup fail nếu secret unset/weak; secret scanner + negative test trên compose render. |
| F-19 | **`/api/stats` lộ topology/filesystem và contract drift.** SQLite có thể trả backend, db size và absolute db path; mô tả nói user counts nhưng implementation không trả. | `agent/public_api.py:1649`; `agent/database.py:2267` | Verified | API/security | Public response allowlist; không có path/backend detail; OpenAPI/schema test khớp payload thật. |
| F-20 | **CSP rộng và lệch giữa proxy/app.** `unsafe-inline`, `connect-src http: https: ws: wss:` mở rộng bề mặt XSS/egress và tạo hành vi khác nhau theo entrypoint. | `nginx.conf:33`; `nginx-ssl.conf:70` | Verified | Web/security | CSP report-only → enforce, nonce/hash cho inline cần thiết, HTTPS-only production, browser security header test. |
| F-21 | **Dependency reproducibility yếu.** Python dùng `>=`, frontend dùng caret; dependency audit CI non-blocking, nên build hôm nay và tháng sau có thể khác. | `requirements.txt`; `web-nuxt/package.json:18-33`; `.github/workflows/ci.yml:675-705` | Verified | Build/release | Lock/hash/pin strategy; SBOM; vulnerability threshold làm gate; rebuild từ clean runner cho cùng digest. |
| F-22 | **Migration runner thiếu lock/checksum lịch sử trong DB.** Gate kiểm source checksum hiện tại nhưng schema history chỉ ghi version/name; chưa chứng minh advisory lock hoặc checksum applied. | `scripts/apply_migrations.py:120-155`; `scripts/check_migration_gate.py` | Unproven risk | Database/release | Concurrent runner test, per-migration checksum ledger, advisory lock, tamper/replay test. |
| F-23 | **AI-only media policy mâu thuẫn.** Social images bị reject nhưng avatar/cover vẫn upload; người dùng và moderator không biết policy áp cho entity, UGC hay toàn hệ thống. | `agent/community/api.py:3637-3641`; `agent/identity/api.py:1419-1488`; `CLAUDE.md §1.5` | Decision required | Product/trust | Policy matrix theo media class; validation, labels, appeal và deletion semantics đồng nhất. |
| F-24 | **Data freshness/provenance chưa là product invariant.** `updatedAt` đảo, duplicate source URL, verified coverage 0 và noindex chủ động; người dùng không thấy freshness/confidence đủ rõ để định lượng rủi ro. | `scripts/validate_data.py --json`; `CLAUDE.md §1.7,§1.8` | Verified | Content/product | Hiển thị last-reviewed/source count/approx badge; freshness budget; stale entity queue; KPI theo correction acceptance và source diversity. |
| F-25 | **Coordinate approximate có nguy cơ gây hiểu nhầm.** 874 entity nằm trong cụm approximate; nếu consumer bỏ qua flag, map/nearby chỉ dẫn sai. | `scripts/deep_audit.py`; `agent/database.py` coordinate handling | Verified | Data/frontend | Contract bắt buộc `coords_approximate` trong mọi map/nearby response; visual copy và test snapshot. |
| F-26 | **Orphan/duplicate entity làm yếu canonical identity.** 32 orphan, 5 duplicate normalized names và 37 near duplicates có thể tạo trang trùng, correction nhầm hoặc analytics phân mảnh. | `scripts/deep_audit.py`; `scripts/validate_data.py --json` | Verified | Data/content | Entity resolution queue có human decision, canonical ID/redirect, duplicate regression test trước publish. |
| F-27 | **Image validator cho kết quả 0% giả.** Export có 57 local image paths, nhưng `image_url()` chỉ nhận URL `http`, khiến metric/quality gate không đo được media nội bộ và credit metadata. | `scripts/validate_data.py:73-80,564-576`; `web/data.json` | Verified | Data/tooling | Checker nhận local immutable paths theo policy, kiểm credit/license/source đúng; báo cáo tách “không có ảnh” khỏi “checker không nhận dạng ảnh”. |

| F-28 | **Search/typeahead xếp hạng sai và cắt pool trước khi xếp hạng.** `/api/search` chỉ lexical-rerank trên pool tối đa 400 hàng đã bị DB sắp theo `confidence`; `/api/autocomplete` còn trả trực tiếp thứ tự DB nên không có lexical rerank. Probe trên catalog hiện tại cho thấy các truy vấn “dừa sáp”, “cù lao”, “vĩnh long”, “chợ” có thể đặt kết quả không liên quan lên đầu; truy vấn không dấu “dua sap” trả rỗng ở SQLite. Đây là lỗi discoverability và làm người dùng nghi ngờ dữ liệu không tồn tại. | `agent/public_api.py:1540-1640`; `agent/database.py:806-824,1611-1659`; probe 2026-08-31 trên 1.621 public entity | Verified | Search/data | Search test corpus có exact/prefix/accent-insensitive/summary cases; query phải tìm đúng entity trong toàn catalog trước khi cắt limit; autocomplete và unified search dùng cùng ranking contract; đo MRR/recall@k. |
| F-29 | **Advanced entity search không phân trang được toàn catalog.** Handler lấy `db.search_entities(... limit=500)` rồi mới lọc/sort/paginate và đặt `total = len(all_entities)`. Với 1.621 entity public hiện tại, các trang sau vùng 500 bị mất và `total` bị báo sai; giới hạn `page <= 200` tạo ảo giác rằng toàn bộ dữ liệu có thể truy cập. | `agent/entities/api.py:1552-1600`; probe `limit=500`: 500 + 500 + 121 trên catalog public | Verified | API/data | Query count và page query cùng predicate; không hard-cap trước pagination hoặc phải trả `truncated`; contract test truy cập entity ở offset >500. |
| F-30 | **Homepage cache lock không bao phủ thời gian rebuild.** Code set `_homepage_rebuilding` rồi nhả `_homepage_lock` trước `await _build_homepage_payload(month)`, trong khi cache-hit chỉ kiểm tra trạng thái lock và không đọc cờ rebuilding. Probe với barrier cho thấy hai request đồng thời đều chạy builder (`builds_before_release = 2`). Khi cache stale/empty, traffic burst sẽ nhân đôi quét DB, curation và analytics. | `agent/public_api.py:1945-1953,2364-2379`; concurrency probe 2026-08-31 | Verified | Platform/SRE | Single-flight test với 10 request chỉ có một build; request còn lại chờ cùng future/result; có metric build duration, waiters và error path không để cờ kẹt. |
| F-31 | **Rate-limit chỉ còn process-local khi PostgreSQL shared store lỗi.** Sau lỗi DB, module tắt shared path 60 giây rồi ghi `_buckets` trong từng process. Với nhiều worker/replica hoặc DB chập chờn, cùng một actor có thể phân tán request qua các bucket và vượt ngưỡng anti-abuse; restart còn xoá trạng thái bộ nhớ. Chưa có deployment topology/runtime evidence để gọi đây là exploit hiện tại. | `agent/ratelimit.py:56-127`; `docker-compose.yml` không chứng minh leader/shared fallback | Unproven risk | Security/SRE | Fault-injection test khi PG timeout; policy fail-closed hoặc Redis bắt buộc cho production; metric/alert khi fallback bật; multi-worker load test giữ nguyên limit toàn cụm. |
| F-33 | **Các consumer dùng nhiều “chiếc đồng hồ” cho mùa vụ/ngày hiện tại.** Homepage dùng giờ Việt Nam, nhưng recommend, chat seasonal fallback/current month, community feed boost và prompt cache dùng UTC; MCP lại dùng UTC+7. Trong khoảng 00:00–07:00 giờ Việt Nam, cùng một request có thể nhận tháng/ngày khác nhau giữa homepage, feed, chat, prompt và MCP. Boundary probe 2026-08-31 xác nhận 17:00 UTC đã là 00:00 ngày hôm sau ở VN (tháng có thể đổi trước UTC). | `agent/public_api.py:2215-2220`; `agent/entities/api.py:1622-1625`; `agent/chat/api.py:562-567,1114-1175`; `agent/community/api.py:1058-1061`; `agent/prompt_cache.py:249-255`; `agent/mcp_server.py:44,588-621`; probe 16:59/17:00 UTC | Verified | Platform/product | Một helper `now_vietnam()`/clock injection dùng cho mọi seasonal/date copy; boundary tests 16:59–17:00 UTC (23:59–00:00 VN) và snapshot thống nhất giữa API/chat/MCP. |
| F-35 | **Hợp đồng public collection mâu thuẫn với auth boundary.** Docstring của `GET /api/me/collections/{id}/items` nói public collection “viewable by anyone”, nhưng route luôn `Depends(require_user)`; frontend hiện chỉ mở tab collections cho chính chủ nên chưa chứng minh đây là lỗi production, nhưng public link/SEO hoặc share flow sẽ nhận 401 trái copy. | `agent/community/api.py:3393-3413`; `web-nuxt/pages/nguoi-dung/[id].vue:175-210,531-539` | Verified contract mismatch / Decision required | Product/API | Chốt public/private semantics; nếu public thật thì route không bắt login nhưng vẫn lọc private; nếu private-only thì sửa doc/schema/UI và thêm contract test 401/200. |
| F-36 | **Scheduler nền khởi động một bản trên mỗi process.** `start_scheduler()` chỉ có `threading.Lock` trong process; lifespan gọi nó khi app start. Không có distributed lease/leader election cho các task cleanup, digest, outbox, cache-warm, moderation hoặc learning. Compose hiện không khai replica, nên đây là rủi ro scale chưa được chứng minh trong topology hiện tại. | `agent/server.py:391-414`; `agent/scheduler.py:1360-1400`; `docker-compose.yml` service `agent` | Unproven risk | SRE | Chạy scheduler tách service hoặc dùng DB advisory lease; multi-worker/replica test chứng minh mỗi task một execution window; dashboard có owner/last-run/lease loss. |
| F-37 | **SQLite và PostgreSQL không có search parity.** PostgreSQL dùng `f_unaccent(lower(...))`, còn SQLite dùng `LIKE` trực tiếp; cùng code path vì vậy có kết quả khác về dấu/hoa-thường. Probe local: “dua sap” không trả entity nào, trong khi route production PG được thiết kế unaccent. Điều này làm test/dev không đại diện cho behavior production và dễ che regression ở frontend typeahead. | `agent/database.py:806-824`; probe 2026-08-31 (`db._use_pg=False`, query `dua sap` → 0) | Verified (environment parity) | Data/platform/test | Shared conformance corpus chạy cả SQLite và PG; hoặc cấm dùng SQLite để kết luận search correctness; thêm unaccent FTS/normalizer tương đương và report parity diff. |
| F-39 | **Container/runtime artifact vẫn dùng image tag trôi nổi.** Compose dùng `prom/prometheus:latest`, `grafana/grafana:latest`, `grafana/loki:latest`, `grafana/promtail:latest`; Dockerfile/Nuxt cũng dùng tag nền mutable như `python:3.12-slim` và `node:22-alpine`. Cùng một commit có thể kéo dependency OS khác nhau, làm mất khả năng tái dựng digest, rollback và điều tra CVE theo release. | `docker-compose.yml:141-179`; `Dockerfile:2,19`; `web-nuxt/Dockerfile:1,7,21` | Verified | Release/ops | Pin digest cho mọi base/service image; lưu SBOM + image manifest trong release; rebuild cùng source phải ra digest đã khai báo hoặc fail preflight. |
| F-43 | **Itinerary admin mutation không purge public cache hoặc ghi audit.** Public list/detail tự công bố `max-age=300, stale-while-revalidate=600`; create/update/delete chỉ ghi DB, không generation bump/purge và không nhận actor/reason. Sau sửa/xoá, người dùng có thể đọc itinerary cũ tối đa 5–15 phút; khi cần correction/takedown sẽ không có bằng chứng ai làm thay đổi. | `agent/itineraries/api.py:339-407`; `agent/itineraries/admin_api.py:31-115` | Verified | Itineraries/platform | Invalidate/generation key sau mutation; proxy test GET ngay thấy version mới; immutable audit actor/reason/correlation cho create/update/delete. |
| F-45 | **`completeness_overview.overall_pct` sai đơn vị.** Hàm tính `pct(sum_counts) / 4 * total`; khi mọi trường đầy đủ, `total=100` trả `10000` thay vì `100`. Dashboard quality gate có thể báo số vô nghĩa và làm operator ưu tiên sai. | `agent/entities/admin_api.py:978-1008`; formula probe/source inspection | Verified | Entities/admin | Công thức là `round(sum_counts / (4*total) * 100, 1)`; fixture 0%, 25%, 100% và schema range `0..100`. |
| F-46 | **Data-quality dashboard đọc các snapshot khác nhau.** `list_entities`/`entity_kinds` đọc DB, còn `completeness_overview`, `completeness_details`, `stale_queue` đọc `knowledge._entities` trong process. `_sync_kb()` chỉ cập nhật process hiện tại; operator có thể thấy DB mới nhưng quality queue cũ trên worker khác. | `agent/entities/admin_api.py:513-605,850-1090`; `agent/admin_common.py:58-81` | Verified architecture risk | Entities/platform | Chọn DB hoặc versioned snapshot làm SoT; trả `snapshot_id/updated_at`; multi-worker mutation A → dashboard B phải thấy cùng version. |
| F-48 | **Concurrent image-suggestion ingest có thể tạo duplicate pending rows.** `_pending_exists()` SELECT rồi mới INSERT; không có unique constraint/canonical hash/advisory lock trên `(entity_id,candidate_url,status)`. Hai ingest worker có thể cùng thấy “chưa có” rồi tạo hai credit candidate. | `agent/image_suggestions.py:116-168`; migration `005_image_suggestions.sql` | Verified race risk | Entities/data | Unique index theo canonical URL/hash và trạng thái, hoặc atomic insert-on-conflict; concurrency test hai worker chỉ còn một pending row. |
| F-50 | **LLM-ops auth nằm trong handler, không nằm trong route dependency graph.** Nhiều `/system/*`, `/vectors/*`, `/checkpoints/*`, `/image/recognize` có `deps=[]` khi runtime scan vì import lười rồi gọi `require_admin` trong thân hàm. OpenAPI, route inventory, middleware và security review tập trung không nhìn thấy admin/scope/CSRF contract. | `agent/llmops/api.py:90-220` và các handler `/system/learning/run`, `/vectors/build`, `/confirm/{id}`, `/image/recognize`; runtime route dependency scan 2026-08-31 | Verified architecture risk | Security/platform | Dùng `Depends`/router dependency factory có metadata rõ; route matrix runtime và OpenAPI security schema phải thể hiện auth + scope + CSRF cho mọi admin route. |
| F-51 | **Runtime import cycle bị che bằng lazy import.** `public_api` import `community.api` cho search/feed, trong khi `community.api` import ngược `public_api` để lấy `_jsonl_lock`/rotation. Đây là coupling ngược ở runtime dù AST boundary test cho phép ngoại lệ; import order/monkeypatch có thể đổi namespace và phân mảnh ownership report store. | `agent/public_api.py:1352-1393,2899`; `agent/community/api.py:2677-2683` | Verified | Platform/architecture | Tách `report_store/jsonl_store` leaf module; cấm domain import composition/root; import-order tests trên nhiều thứ tự và một lock/store identity duy nhất. |
| F-52 | **Public report nhận target giả và không coalesce duplicate.** `/api/report` ghi JSONL với `target_id`/`target_type` gần như nguyên văn; chưa xác nhận entity/post/comment tồn tại, chưa có canonical target registry hoặc dedup open report. Có thể bơm queue rác và làm sai dashboard/SLA. | `agent/public_api.py:2683-2775` | Verified | Trust/moderation | Validate target/type trước enqueue (404/422), canonicalize ID, deduplicate report đang mở theo reporter-target-field; test bogus và duplicate. |
| F-54 | **Stale-queue “mark reviewed” gọi method DB không tồn tại.** Handler lấy entity rồi gọi `db.update_entity(entity_id, {"attributes": attrs})`, nhưng `Database` không có `update_entity` (runtime `hasattr(db, "update_entity") == False`). Mọi thao tác đánh dấu stale đã xem sẽ 500, khiến queue không thể đóng bằng UI. | `agent/entities/admin_api.py:968-974`; runtime probe 2026-08-31 | Verified | Entities/admin | Dùng API writer hợp lệ và audit actor; route test thật với entity fixture phải trả 200, reload projection và ghi `stale_reviewed_at`. |
| F-55 | **Collection có thể nhận post pending/deleted rồi trả success nhưng item vô hình.** `add_to_collection` chỉ kiểm collection owner và giới hạn số lượng, sau đó INSERT post_id; public list JOIN lọc `moderation_status='approved' AND deleted_at IS NULL`. Người dùng tưởng đã lưu bài nhưng item không bao giờ hiện, count trước/sau cũng lệch kỳ vọng. | `agent/community/api.py:3341-3369,3411-3426` | Verified | Community/product | Kiểm post tồn tại, approved, chưa xoá trước insert; nếu policy cho phép lưu pending thì UI/schema phải hiển thị trạng thái và count; test pending/deleted/approved. |
| F-56 | **Import hai namespace tạo singleton kép.** `features.py` dùng `from vector_search import ...`, còn `semantic_cache.py` ưu tiên `from agent.vector_search import ...`. Runtime probe nạp đồng thời cho thấy module và `embedding_store` khác identity (`same_module=False`, `same_embedding_store=False`), nên index/vector state có thể lệch giữa retrieval và semantic cache. | `agent/features.py:27`; `agent/semantic_cache.py:31-34`; runtime probe 2026-08-31 | Verified | Platform/search | Chọn một import convention; cấm mixed namespace; startup assertion không có duplicate singleton; test build index rồi semantic lookup dùng cùng object/generation. |
| F-57 | **Siteops system-health hỏng trên PostgreSQL do truy vấn bảng `sessions`.** Schema và identity dùng `user_sessions`, nhưng `_system_health_pg` truy vấn `FROM sessions` ngoài `try`; khi PG bật, toàn endpoint `/admin/system-health` có thể 500 thay vì trả health degraded. | `agent/siteops/admin_api.py:191-244`; `agent/identity/api.py:1146-1185`; migrations `075_hot_path_indexes_and_session_timeouts.sql` | Verified | Siteops/ops | Đổi sang bảng authority, per-check isolation để một metric lỗi không làm hỏng toàn response; PG integration test với schema thật và readiness alert. |
| F-58 | **Announcements public cache không có invalidation sau admin mutation.** Public `/api/announcements` đặt `max-age=60, stale-while-revalidate=120`; create/update/delete admin không purge/generation. Thông báo bảo trì hoặc incident có thể chậm hiển thị/tắt tối đa vài phút, trái mục tiêu điều hành. | `agent/siteops/api.py:46-73`; `agent/siteops/admin_api.py:851-944` | Verified | Siteops/platform | Cache key generation/purge sau mutation; test publish/disable rồi GET qua proxy ngay; emergency announcement path `no-store`. |
| F-59 | **Semantic matcher phình sai khi ghi đè cùng key.** `SemanticMatcher.add()` luôn tăng `_doc_count` và `_df` dù key đã tồn tại; `MultiTierCache.put()` gọi add lại cho cùng query. Probe thêm cùng key hai lần làm `doc_count` 1→2 và df token 1→2 dù chỉ có một entry, khiến TF-IDF/similarity drift theo thời gian. | `agent/semantic_cache.py:101-124,375-430`; runtime probe 2026-08-31 | Verified | Chat/search | Remove/replace atomically trước add hoặc cập nhật DF theo diff; property test repeated put giữ doc_count/df đúng và similarity ổn định. |
| F-60 | **Semantic L2 JSON cache không an toàn đa process.** `_save_l2()` dùng một file `.tmp` cố định rồi `replace`, chỉ bảo vệ bằng `threading.Lock` trong process. Hai worker có thể ghi đè/lost update hoặc cạnh tranh replace; một process có thể đọc snapshot khác process và semantic index không cùng generation. | `agent/semantic_cache.py:279-319`; `docker-compose.yml`/scheduler topology | Unproven scale risk | Chat/platform | Redis hoặc file lock liên process + atomic versioned manifest; concurrent writer/kill test; cache backend phải được nêu trong production preflight. |
| F-61 | **Backup thủ công kích hoạt cooldown trước khi biết backup có chạy thành công.** `trigger_backup()` ghi `_last_backup_time` trước khi kiểm tra script tồn tại và trước `subprocess.run`; lỗi thiếu script, timeout hoặc return code khác 0 vẫn khóa lần thử tiếp theo trong toàn bộ cooldown. Ở nhiều worker, biến này lại chỉ nằm trong process nên vừa có cửa sổ từ chối nhầm vừa không chống được chạy song song giữa replica. | `agent/siteops/admin_api.py:567-618` | Verified source-level ops risk | Siteops/SRE | Chỉ commit cooldown sau backup thành công; lock/lease dùng chung; test missing-script/timeout/non-zero/success và concurrent admin requests. |
| F-62 | **Geocode cache ghi file dùng lock không đầy đủ cho discovery chạy đồng thời.** `_cache_lock` chỉ bảo vệ lần load đầu; `geocode()` đọc/ghi dictionary và `_save_cache()` ngoài lock, dùng một `.tmp` cố định. Hai thread/process có thể cùng gọi Nominatim, làm mất entry, thay snapshot hoặc tranh chấp `replace`; state cache của worker này không phản ánh worker kia. | `agent/geocode.py:63-88,135-154`; callers `agent/auto_learn.py:413`, `agent/discover_province.py:254`, `agent/learn_loop.py:225` | Unproven scale risk (autonomous mặc định off) | Discovery/platform | Shared cache hoặc file lock liên process, merge-before-write/versioned manifest; concurrent writer/kill test; metrics cho duplicate geocode và lost update. |
| F-63 | **Authority token bị phân mảnh dù đã tuyên bố kiến trúc 3 tầng.** `variables.css` có primitive, semantic `--color-*`, alias legacy (`--primary`, `--bg`, `--card`...) và component/role tokens; `tri-region-color.css` còn remap `--primary` theo `data-color-system`. Vì component có thể nhận cùng tên token nhưng khác giá trị tùy selector/context, việc di chuyển component giữa shell, catalog và admin có thể đổi màu/contrast mà không đổi code. Quét thô 181 source files ghi nhận khoảng 3.820 lượt legacy semantic so với 631 lượt `--color-*`; đây là tín hiệu migration chưa có boundary/lint bắt buộc, không phải bằng chứng mọi lượt dùng đều sai. | `web-nuxt/assets/css/variables.css:1-3,35-90,148-200,614-618`; `web-nuxt/assets/css/tri-region-color.css:1-25`; `web-nuxt/assets/css/components.css:127-149`; scan source 2026-08-31 | Verified architecture risk | Design/platform | Chọn canonical semantic authority; khai báo compatibility layer có allowlist/expiry; lint cấm thêm alias legacy ngoài vùng cho phép; contract test kiểm computed token trong default, `.light`, `.dark` và `data-color-system`. |
| F-64 | **Typography contract lệch giữa tài liệu và runtime.** Design skill vẫn ghi Inter self-hosted và yêu cầu `font-optical-sizing: auto`, trong khi token/runtime dùng `Be Vietnam Pro` cho interface và `Fraunces` cho editorial; `nuxt.config.ts` khai báo hai family đó và toàn repo không có rule `font-optical-sizing`. Người tiếp quản có thể thêm Inter hoặc tin rằng optical sizing đã hoạt động, gây lệch metric, fallback và CLS trên tiếng Việt. | `web-nuxt/docs/design-skill/SKILL.md:10-16,60-63`; `web-nuxt/assets/css/variables.css:329-334`; `web-nuxt/assets/css/base.css:15`; `web-nuxt/nuxt.config.ts:29-42`; `rg font-optical-sizing web-nuxt` không có kết quả | Verified documentation/runtime drift | Design/content/platform | Hoặc cập nhật docs theo Be Vietnam Pro/Fraunces, hoặc đổi runtime về Inter; thêm font inventory/build assertion, `font-optical-sizing` policy, glyph/diacritic browser fixture và đo FOIT/CLS ở 1x/2x text scale. |
| F-65 | **State/variant tokens chủ yếu là token chết.** `--state-hover/focus/pressed/dragged`, opacity state và các biến thể `--card-elevated/filled/outlined-*` được khai báo nhưng search toàn `web-nuxt` chỉ thấy ở `variables.css`; CSS thực tế vẫn dùng opacity, `rgba` và shadow cục bộ. Vì vậy một thay đổi state/elevation phải sửa nhiều module và dễ lệch giữa light/dark/forced-colors. | `web-nuxt/assets/css/variables.css:238-260,483-485`; `web-nuxt/assets/css/components.css:127-149,375`; token-consumption scan 2026-08-31 | Verified | Design-system/frontend | Mỗi token variant phải có consumer thật hoặc bị xoá; lập state matrix cho button/input/card/dialog/table (hover, focus-visible, pressed, disabled, loading, error) và snapshot computed style ở light/dark/high-contrast. |
| F-66 | **AdminCP có ngữ pháp component riêng, lệch khỏi public system.** Layout và page-local CSS dùng nhiều radius 6/8/10/14px, màu `rgba` và semantic legacy; control có `min-height: 32/36/40px` trong data-quality, pagination, refresh, moderation và image review, trong khi design baseline nêu 44px. Accessibility snapshot hiện đo 7/7 control đại diện đạt ngưỡng và không có overflow, nhưng chưa bao phủ mọi admin route nên không thể coi source/runtime contract đã thống nhất. | `web-nuxt/layouts/admin.vue:390-410,473-517`; `web-nuxt/pages/admin/data-quality.vue:717`; `web-nuxt/pages/admin/kiem-duyet.vue:528,587`; `web-nuxt/pages/admin/duyet-anh.vue:352`; `web-nuxt/pages/admin/ai.vue:413-596`; `web-nuxt/docs/design-skill/SKILL.md:34-35` | Verified source drift; rendered coverage incomplete | Admin/frontend | Định nghĩa admin component tokens và biến thể `dense-workbench` có chủ đích; quyết định control nào được phép <44px; kiểm tra keyboard/focus/contrast ở entities, dashboard, AI, moderation, settings, siteops trên desktop/mobile và 200% zoom. |
| F-67 | **Stacking authority có lỗ hổng.** Scale chính chỉ định `--z-modal-high: 900`, `--z-lightbox: 9999`, `--z-skip-link: 10000`, nhưng `SourceTrustDrawer` và `WhyThisDrawer` cùng dùng raw `z-index: 1200`. Hai drawer này không có token/ownership mô tả quan hệ với modal, command palette, toast và mobile nav; thêm overlay mới có thể che sai hoặc bị che mà lint không phát hiện. | `web-nuxt/assets/css/variables.css:594-606`; `web-nuxt/components/SourceTrustDrawer.vue:196`; `web-nuxt/components/WhyThisDrawer.vue:112`; các overlay khác dùng `--z-modal-high`, `--z-lightbox` | Verified | Design/platform | Thêm token có tên (`--z-drawer` hoặc layer registry), cấm raw z-index ngoài allowlist; fixture mở đồng thời drawer/dialog/toast/lightbox và kiểm thứ tự keyboard/pointer/visual. |
| F-68 | **Ratchet màu chỉ bảo vệ vài public surface, không chứng minh token purity toàn hệ thống.** `check-tri-region-color-debt.mjs` pass nhưng catalog/detail vẫn có tổng rawHex `5/25` và legacy-primary `103/103`; các cụm `dark-overrides.css`, `detail.css`, `components.css` và admin còn nhiều `rgba`/màu semantic cục bộ. Nếu không phân loại exemption, debt trang trí/media, fallback, forced-colors và debt tương tác bị trộn, khiến gate xanh nhưng state mới vẫn có thể lệch theme/contrast. | Output `node web-nuxt/scripts/check-tri-region-color-debt.mjs` ngày 2026-08-31; `web-nuxt/assets/css/dark-overrides.css`, `detail.css`, `components.css`, `layouts/admin.vue`; `web-nuxt/assets/css/variables.css:35-90,968-1012` | Verified governance gap | Design/platform | Tạo registry machine-readable cho `semantic-ui`, `decorative-scene`, `media-scrim`, `SVG/data-uri`, `forced-colors` và fallback; đặt budget debt theo region; lint màu semantic mới phải trỏ token và contrast test phải chạy trên tất cả component states. |
| F-70 | **Tài liệu baseline/triage có nhiều authority sống cùng lúc.** `CLAUDE.md` yêu cầu baseline 15 fail và trỏ `ROADMAP.md` §Fail-đã-biết; `docs/ROADMAP.md:526` ghi 15; nhưng `docs/HANDOFF.md` vẫn mang `STATUS: active`, ngày 2026-08-04 và nói “Hiện không có fail-đã-biết”. Handoff mới hơn còn claims HEAD `d05024eb` trong khi HEAD thực tế là `24aae184` (hai commit mới hơn). Inventory chuẩn cũng lệch: `docs/README.md` nói bảng standards có 34 rule, còn `docs/standards/00-INDEX.md` hiện liệt kê 38 rule. Handoff có câu “CLAUDE thắng”, nhưng không có freshness gate hoặc kiểm tự động chặn tài liệu active quá cũ. Người tiếp quản có thể chọn runner/roster sai hoặc xem 15 test là regression mới, làm sai cả chẩn đoán lẫn quyết định release. | `CLAUDE.md:40,62`; `docs/ROADMAP.md:526-533`; `docs/HANDOFF.md:1-4,24,146`; `docs/2026-08-31-ban-giao-tiep-tuc.md:1-9`; `docs/README.md:27`; `docs/standards/00-INDEX.md:6-52`; `git rev-parse HEAD` ngày 2026-08-31 | Verified governance/documentation risk | Release/docs | Một registry authority duy nhất có `last_verified_at`, `head_sha`, owner và expiry; CI kiểm link/branch/baseline/rule-inventory consistency; tài liệu quá hạn phải tự chuyển `stale` và không được dùng làm release evidence. |
| F-71 | **Báo cáo audit active nhưng chưa được version hóa.** `docs/audit-toan-du-an-2026-08.md` tự nhận là báo cáo active và evidence được tái lập trên branch, nhưng `git status` cho thấy file vẫn `??` (untracked). Clone/CI/release package có thể không chứa chính artifact dùng để quyết định Go/No-Go; người khác không thể kiểm checksum hoặc biết báo cáo nào là bản có hiệu lực. Đây là lỗi durability của evidence, khác với parser full-suite (F-69) và tài liệu baseline stale (F-70). | `docs/audit-toan-du-an-2026-08.md:1-3,945-950`; `git status --short` ngày 2026-08-31 | Verified release-artifact risk | Release/docs | Version hóa audit hoặc lưu vào release evidence bundle có `head_sha`, timestamp, checksum và owner; CI fail nếu Go/No-Go tham chiếu artifact chưa tracked/signed. |
| F-72 | **Chat không có chronology cho từng message.** State/render chỉ giữ `role`, `content` và `failed`; không có `createdAt`/`<time>` hoặc hiển thị thời điểm gửi/nhận. Khi stream, retry hoặc session kéo dài, người dùng không thể phân biệt câu trả lời cũ/mới, đối chiếu incident hay chứng minh nội dung thuộc generation nào. Đây là gap auditability của chat, không trùng F-24 freshness catalogue. | `web-nuxt/components/ChatWidget.vue:23-27,66,178-183`; Checklist Design Chat tại `docs/audit-toan-du-an-2026-08.md:473` | Verified UX/trust gap | Chat/frontend | Server trả timestamp monotonic + timezone/display policy; UI render `<time datetime>` cho user/assistant/error/retry; fixture stream/reconnect giữ chronology và không leak session metadata. |
| F-73 | **Legal disclosure thiếu cookie policy và policy change history.** Checklist đã đánh dấu đỏ nhưng sản phẩm chỉ có privacy/terms và `updated_date`; không thấy inventory cookie theo purpose/expiry/SameSite/Secure, user control, hoặc changelog giải thích thay đổi policy. Cookie capability/CSRF tồn tại trong code nhưng không có lớp công khai tương ứng, nên consent/notice và audit legal không khép. | `docs/audit-toan-du-an-2026-08.md:508-510`; `agent/auth_middleware.py`; `web-nuxt/utils/legalContent.ts`; `web-nuxt/pages/chinh-sach-bao-mat.vue`, `dieu-khoan-su-dung.vue` | Verified legal/documentation gap; wording cần owner/legal chốt | Legal/DPO + frontend | Lập cookie inventory và purpose/retention/control; thêm policy version + plain-language changelog; contract test link/updated/version/cookie disclosure và rà với luật sư/DPO trước public launch. |

### P3 — nợ chất lượng nhưng không được che bằng “pilot”

- Chuẩn hóa text join, phone format và 28 singleton relationship types.
- Rà source URL trùng theo canonical URL/hash, không chỉ theo string.
- Tách rõ heuristic score khỏi factual confidence trong UI/admin.
- Ghi browser smoke artifact (desktop/mobile, 200% zoom, keyboard, reduced motion, error/success states) vào release evidence.

## 5. Checklist lens: correction flow và admin

Đây là audit từ source, không phải visual critique. Những item về contrast, spacing, focus rendering, mobile hit area và animation chỉ được xem là “chưa chứng minh” cho đến khi có screenshot/browser capture.

### 5.1 Submitting a form

| | Item | Đánh giá |
|---|---|---|
| 🟢 | Show button to submit | Có review button và nút `Xác nhận gửi yêu cầu` trong `CorrectionIntakeForm.vue`. |
| 🟢 | Show loading state after submission | `busy` disable nút và đổi copy thành `Đang gửi…`; cần browser smoke để xác nhận không có double-submit ngoài source. |
| 🟢 | Show success message | Receipt card được render sau `createCorrection` thành công; cần kiểm tra focus/announcement khi chuyển state. |
| 🟢 | If it doesn't, show an error message | Page có `failure` role alert và retry cho entity load. |
| 🟡 | Error may occur because of wrong information | Error summary/field error tốt, nhưng `reportedValue` không được validate trong FE trong khi BE bắt buộc; đây là F-02. |

### 5.2 Verifying account/contact

| | Item | Đánh giá |
|---|---|---|
| 🟡 | Establish a trigger point | Nút gửi mã chỉ xuất hiện sau số điện thoại + consent; copy chưa nói rõ mã có hiệu lực bao lâu và xác minh dùng để làm gì ngoài “báo kết quả”. |
| ⚪ | Method selection | Không cần nhiều phương thức cho closed pilot; phone là kênh tùy chọn. |
| 🟢 | Confirm delivery/contact information | Review panel hiển thị số nhận kết quả; cần xác minh masking trên màn hình công khai. |
| 🔴 | Ability to input verification code | Composable có `verifyContact`, nhưng không có UI gọi nó trong page/form; F-01. |
| 🔴 | Incorrect value and resend | Chưa thấy state/code input/resend/expired/too-many-attempts trong public journey. |
| 🔴 | Verification success state | Chưa có trạng thái thành công mà người dùng nhìn thấy và biết OTP đã gắn vào capability hiện tại. |

### 5.3 Admin panel và auditability

| | Item | Đánh giá |
|---|---|---|
| 🟢 | Role-based access | Architecture quyết định route-level scopes; cần staging matrix test cho từng scope, không chỉ unit test. |
| 🟡 | User management | Có identity/admin surfaces, nhưng audit này chưa chứng minh toàn bộ invite/edit/remove flow qua UI. |
| ⚪ | Organisation settings | Không phải core value của sản phẩm consumer hiện tại; chỉ cần nếu vận hành B2G/workspace. |
| ⚪ | Billing and plan management | Non-goal hiện tại; premium listing là decision/legal risk riêng, không nên giả định đã có billing control. |
| 🟡 | Usage overview | `/api/stats` tồn tại nhưng contract lộ topology và thiếu user counts như mô tả; F-19. |
| 🟡 | Audit log | Có endpoint và trang `/admin/nhat-ky`, nhưng report/event vẫn phân mảnh và chưa chứng minh một source-of-truth cho mọi loại report; F-10. |
| 🟡 | Danger zone | Có các endpoint nhạy cảm và guard, nhưng acceptance phải chứng minh typed confirmation, backup và rollback trước mọi destructive op. |

### 5.4 Privacy/legal page

| | Item | Đánh giá |
|---|---|---|
| 🟡 | Privacy policy | Có legal content và retention copy, nhưng chưa chứng minh mọi sink (bot, logs, JSONL, media, browser storage) được liệt kê/erasure. |
| 🟡 | Terms of service | Có định hướng showcase-only, nhưng premium/featured listing và UGC authority cần wording nhất quán với quyết định thương mại. |
| 🔴 | Cookie policy | Không có policy riêng công bố cookie inventory, purpose, expiry, SameSite/Secure và opt-out; capability/CSRF trong code không thay thế tài liệu người dùng đọc được. |
| 🟢 | Last updated date | `LEGAL_PRIVACY`, `LEGAL_TERMS` và `ABOUT_PAGE` đều có `updated_date` và các trang render ngày đó. |
| 🔴 | Version history/changelog | Chưa thấy changelog chính sách có diff/plain-language summary. |
| 🟡 | Contact for legal queries | Có CTA qua trang Liên hệ, nhưng chưa chứng minh dedicated legal/data address và routing/ownership rõ. |

## 5.5 Checklist Design re-audit — toàn bộ bề mặt đã tách

⚠️ Đây là audit **source-level** trên Vue/Nuxt và backend liên quan, không phải visual critique. Tôi chưa có browser capture mới nên không thể kết luận trung thực về contrast, spacing, hover, focus ring, animation, hit-area hay responsive rendering; các điểm đó được đánh dấu `❔ Can't tell` thay vì suy đoán. Các checklist dưới đây giữ nguyên thứ tự item của Checklist Design; mỗi bảng chỉ đánh giá surface tương ứng trong sản phẩm này.

### [Submitting a form](https://www.checklist.design/flows/submitting-a-form)

| | Item | Why |
|---|---|---|
| 🟢 | **Show button to submit** — Below the form fields, a button to submit the information needs to be present. | `CorrectionIntakeForm.vue` có nút `Xác nhận gửi yêu cầu` sau bước xem lại; settings và admin forms cũng có submit action. |
| 🟢 | **Show loading state after submission** — The user must see the form is in the process of being submitted. | `busy`/`saving` disable nút và đổi copy (`Đang gửi…`, `Đang lưu…`) trong `web-nuxt/components/cases/CorrectionIntakeForm.vue` và `web-nuxt/pages/cai-dat.vue`. |
| 🟢 | **Show success message when it submits** — The form was submitted and should communicate that clearly. | Correction page chuyển sang receipt; settings dùng toast thành công (`Đã lưu hồ sơ`) — `web-nuxt/pages/yeu-cau/sua-thong-tin.vue:111-125`, `web-nuxt/pages/cai-dat.vue:1497-1505`. |
| 🟢 | **If it doesn't, show an error message** — If the form cannot submit, an error needs to be shown. | Có `role="alert"`, retry và toast lỗi ở correction/settings/admin forms — `CorrectionIntakeForm.vue`, `cai-dat.vue`, `admin/entities.vue`. |
| 🟡 | **An error may occur because of the wrong information** — If criteria are not met, the failed submission must detail what is wrong. | Field error và error summary có, nhưng `reportedValue` vẫn lệch contract backend (F-02), nên thông báo chưa bao phủ mọi lỗi dữ liệu — `CorrectionIntakeForm.vue:80-114`, `agent/cases/validation.py`. |

### [Verifying account](https://www.checklist.design/flows/verifying-account)

Trong sản phẩm có hai lane: account OTP trong `AuthModal` khá đầy đủ; phone nhận kết quả của correction là lane riêng và hiện chưa khép kín.

| | Item | Why |
|---|---|---|
| 🟢 | **Establish a trigger point** — Clearly indicate when verification is required and why. | `AuthModal` dẫn từ nhập phone → đăng ký/đăng nhập → OTP; correction chỉ hiện nút gửi mã sau khi nhập phone và consent — `web-nuxt/components/AuthModal.vue:12-45`, `CorrectionIntakeForm.vue:257-266`. |
| ⚪ | **Method selection (optional)** — Email, SMS, or authenticator methods may be offered. | Closed pilot chủ động dùng phone/SMS làm kênh chính; không mở thêm method để tránh policy và provider surface mới. |
| 🟢 | **Confirm delivery and contact information used** — Show the email or phone where the code is sent. | Auth step hiển thị `phone`; correction review hiển thị số nhận kết quả, nhưng nên masking khi render công khai — `AuthModal.vue:48-112`, `CorrectionIntakeForm.vue:281-291`. |
| 🟡 | **Ability to input verification code** — Provide an accessible code input. | Account lane có sáu ô OTP, paste và keyboard handling; correction contact lane chỉ emit `request-phone-verification`, chưa có UI nhập mã (F-01) — `AuthModal.vue:142-169`, `CorrectionIntakeForm.vue:263-269`. |
| 🟡 | **Incorrect value (and resend option)** — Explain expired/incorrect/too-many-attempts cases and next steps. | `AuthModal` có lỗi mã sai và resend countdown; correction lane chưa có expired/resend/lockout state — `AuthModal.vue:465-518`, `yeu-cau/sua-thong-tin.vue:56-74`. |
| 🟢 | **Verification success state** — Confirm success and continue to the next interface step. | Account lane chuyển sang `done`/welcome; correction receipt chưa chứng minh OTP capability đã bind nhưng không làm mất account success — `AuthModal.vue:258-273`, `agent/identity/api.py`. |

### [Saving changes](https://www.checklist.design/flows/saving-changes)

| | Item | Why |
|---|---|---|
| 🟢 | **Show action that enables change** — Provide an edit action or an editable state. | Settings mở trực tiếp các form hồ sơ, mật khẩu, privacy và danger zone; profile có link `Sửa hồ sơ` — `web-nuxt/pages/cai-dat.vue:40-149`, `web-nuxt/pages/nguoi-dung/[id].vue:52-60`. |
| 🟡 | **Disable save action until changes are made** — The save action can start disabled when nothing changed. | Có `isDirty` để theo dõi, nhưng nút save chủ yếu chỉ disable khi request đang chạy; trạng thái clean chưa được buộc đồng nhất cho mọi tab — `web-nuxt/pages/cai-dat.vue:147-1513`. |
| 🟡 | **State changes to active once a change is made** — A pending change should make the action visibly active. | Nút luôn là primary và dirty state chỉ tồn tại ở profile; các preference auto-save dùng notice riêng, chưa có một contract active thống nhất — `cai-dat.vue:751-934`. |
| 🟢 | **Action changes to loading state when pressed** — Show progress while the save is in flight. | `saving`, `savingPw`, `securityBusy`, `preferenceBusy` và `aria-busy` được dùng ở các lane — `cai-dat.vue:149-184`, `cai-dat.vue:203-219`. |
| 🟢 | **Notify changes have been saved** — Tell the user that changes are safely persisted. | Toast/inline notice cho hồ sơ, password, notification, privacy và personalization; lỗi cũng rollback notice — `cai-dat.vue:861-934`, `cai-dat.vue:1497-1507`. |

### [Showing input error](https://www.checklist.design/flows/showing-input-error)

| | Item | Why |
|---|---|---|
| 🟢 | **Keep the input in default state** — Check for errors after information has been entered. | Correction form khởi đầu không gắn lỗi; AuthModal chỉ đánh dấu khi có `error` — `CorrectionIntakeForm.vue:61-70`, `AuthModal.vue:20-33`. |
| 🟢 | **Allow user to enter information** — Let users type without interrupting them. | Textarea/input dùng `v-model`; validation chính chạy khi review/submit, không chặn từng ký tự — `CorrectionIntakeForm.vue:199-232`. |
| 🟡 | **Signal error after loss of focus** — On blur, explain the error with visual and text cues. | Username có blur validation, nhưng correction fields chủ yếu validate lúc submit; chưa chứng minh icon/error timing nhất quán trên mọi field — `AuthModal.vue:78-86`, `CorrectionIntakeForm.vue:80-114`. |
| 🟡 | **Return to default state upon reattempt** — Refocusing should clear the error until rechecked. | AuthModal reset `error` khi retry; correction giữ error summary đến lần validate kế tiếp và chưa clear per-field khi focus — `AuthModal.vue:459-518`, `CorrectionIntakeForm.vue:104-114`. |

### [Uploading media](https://www.checklist.design/flows/uploading-media)

| | Item | Why |
|---|---|---|
| 🟡 | **Empty state** — Show a placeholder indicating drop or click to upload. | Community composer có icon + file input; settings có nút đổi avatar/cover nhưng không có drop-zone minh thị — `web-nuxt/pages/cong-dong.vue:109-151`, `web-nuxt/pages/cai-dat.vue:40-72`. |
| 🔴 | **Drag and drop interaction** — Show a state change when a file is dragged over the canvas. | Không thấy `dragover`/`drop` handler trong composer/settings; hiện chỉ có `<input type="file">`. |
| 🟡 | **Progress indicator** — Show real-time progress, names, and overall progress for multiple files. | Có busy copy/spinner và preview status, nhưng không có percentage hoặc per-file upload progress — `cong-dong.vue:118-151`, `cai-dat.vue:50-70`. |
| 🟢 | **File restrictions & constraints** — State file size/format limits and explain invalid uploads. | Avatar/cover giới hạn MIME bằng `accept="image/jpeg,image/png,image/webp"`; backend media policy còn cần đối chiếu copy với composer `image/*` — `cai-dat.vue:54-72`, `agent/media_policy.py`. |
| 🟡 | **Outcome status** — Show success/failure indicators and recovery guidance. | Preview có `data-preview-status`, invalid text và image error opacity; chưa có một success receipt/retry contract cho mọi media path — `cong-dong.vue:118-132`, `ImageDisclosure.vue`. |
| 🟡 | **Upload actions** — Offer retry, cancel, delete, or rename as appropriate. | Remove image và disable while upload exist; retry/cancel/rename không đồng nhất giữa avatar, cover và UGC — `cong-dong.vue:123-132`, `cai-dat.vue:50-70`. |
| 🟢 | **Showing multiple uploaded files** — Display multiple files in a scalable list/grid. | Composer nhận `multiple`, render preview grid và nút xoá từng ảnh — `cong-dong.vue:118-132`. |

### [Filtering items](https://www.checklist.design/flows/filtering-items)

| | Item | Why |
|---|---|---|
| 🟢 | **Show action near item collection** — Place filtering above or beside the collection. | Search, map, community, notifications, reports và admin entities đều đặt filter ngay trên collection — `web-nuxt/pages/tim-kiem.vue:18-31`, `cong-dong.vue:225-285`, `admin/entities.vue:11-65`. |
| 🟢 | **Show available filter options** — Reveal options on the same page or a dedicated filter surface. | `FilterChips`, tabs, selects và status/type groups expose option lists in-place — `web-nuxt/components/FilterChips.vue`, `web-nuxt/pages/admin/bao-cao.vue:20-65`. |
| 🟢 | **Consider different filter types** — Use multi-select, checkbox, slider, dropdown, or the easiest control per property. | Type/status chips, select, date input, search input và checkbox được dùng theo loại dữ liệu — `ban-do.vue`, `admin/entities.vue`, `admin/nhat-ky.vue`. |
| 🟢 | **Show active filters clearly when applied** — Indicate which filters are in use. | Active class/`aria-pressed`, tag banner và chip count hiển thị state đang lọc — `tim-kiem.vue:425-437`, `cong-dong.vue:255-285`, `admin/entities.vue:43-66`. |
| 🟢 | **Provide easy filter removal** — Clear one or all filters. | Có nút clear search, bỏ tìm, chip toggle và action remove-filter — `tim-kiem.vue:430-437`, `ban-do.vue:131-138`, `admin/entities.vue:18-30`. |
| 🟢 | **Show result count** — Show the reduced total where meaningful. | Search count, community result count, entities total và report pager đều render số kết quả — `tim-kiem.vue`, `cong-dong.vue:243-254`, `admin/entities.vue:6-8`, `admin/bao-cao.vue:188-194`. |
| 🟢 | **Empty state** — Explain zero results and suggest adjusting or clearing filters. | Search/reports/entities/notifications đều có empty copy và đường reset/thử lại — `tim-kiem.vue:128-151`, `admin/entities.vue:214-232`, `admin/bao-cao.vue:147-164`. |

### [Search Results](https://www.checklist.design/web-app/search-results)

| | Item | Why |
|---|---|---|
| 🟢 | **Search input** — A pre-filled field at the top lets users refine the current query. | `tim-kiem.vue` bind query từ route, autocomplete và submit bằng Enter/button — `web-nuxt/pages/tim-kiem.vue:18-31`, `SearchAutocomplete.vue`. |
| 🟢 | **Result count** — Show how many results were found, including zero. | `totals` và section counts render cho entity/post/user; zero-result recovery vẫn giữ query — `tim-kiem.vue:376-430`. |
| 🟢 | **Result items** — Each result has enough title/type/image/snippet to identify it. | Result cards dùng name, type metadata, image descriptor, snippet/freshness — `tim-kiem.vue:64-104`, `EntityCard.vue`. |
| 🟢 | **Result type indicators** — Label/icon marks the result kind. | `TYPE_META`, category icon và type chip phân biệt entity/post/user — `tim-kiem.vue:24-31`, `EntityCard.vue`. |
| 🟡 | **Filters** — Narrow results by category, date, status, or relevant values. | Có type/filter chips và selected state; date/status cross-search chưa đầy đủ, backend ranking/pagination còn F-28/F-29 — `tim-kiem.vue:64-104`, `agent/public_api.py`. |
| 🟢 | **No results state** — Offer suggestions or spelling alternatives rather than a blank page. | `zeroResultRecoverySteps`, alias query, clear-filter và browse alternatives được render — `tim-kiem.vue:128-151`, `tim-kiem.vue:367-437`. |
| 🟡 | **Recent searches** — Show previous queries when the field is focused and empty. | `SearchAutocomplete` có recents và remove; trang kết quả nổi bật recently viewed hơn là danh sách query history — `web-nuxt/components/SearchAutocomplete.vue:55-66`, `tim-kiem.vue:170-214`. |

### [Single Item Detail](https://www.checklist.design/web-app/single-item-detail)

| | Item | Why |
|---|---|---|
| 🟢 | **Clear title or identifier** — Prominent name, ID, or primary label. | Entity detail render `h1` với `entity.name`, type chip và place — `web-nuxt/pages/dia-diem/[id].vue:54-90`. |
| 🟡 | **Status indicator (if applicable)** — Show state with text, not colour alone. | Freshness/trust/provisional components tồn tại nhưng public status projection và browser readability chưa được chứng minh — `EntityTrustPanel.vue`, `FreshnessLine.vue`, `agent/publication_status.py`. |
| 🟢 | **Key details section** — Surface important attributes with secondary details below/sidebar. | Detail có hero, practical info, trust panel, reviews, map, related entities và source disclosure — `dia-diem/[id].vue`. |
| 🟡 | **Edit action** — Provide a clear way to modify the item. | Public user được `Báo sai dữ liệu`/correction thay vì edit trực tiếp; admin có edit modal — `danh-ba.vue`, `yeu-cau/sua-thong-tin.vue`, `admin/entities.vue`. |
| 🟢 | **Related items or activity** — Show associated records or change/activity history. | Nearby, reviews, entity feed, itinerary links và source/trust drawers được nối từ detail — `dia-diem/[id].vue`, `NearbyEntities.vue`, `EntityFeed.vue`. |
| 🟢 | **Breadcrumb or back navigation** — Return to list or parent context. | Breadcrumb có parent type/admin unit và nút quay lại — `dia-diem/[id].vue:15-34`. |
| ⚪ | **Destructive actions** — Delete/archive options separated from primary actions. | Public detail không cho xoá; destructive entity actions chỉ thuộc admin table/modal và được audit riêng. |

### [Feed](https://www.checklist.design/web-app/feed)

| | Item | Why |
|---|---|---|
| 🟢 | **Feed item preview** — A preview of each feed item sufficient to judge whether it is worth opening. | `PostCard` và feed hiển thị nội dung, tác giả, ảnh/loại bài và metadata trước khi mở — `web-nuxt/pages/cong-dong.vue:302-371`, `PostCard.vue`. |
| 🟢 | **Author** — The name and avatar of the person who created or posted each item. | Post card lấy author/display name/avatar và profile link; fallback avatar cũng có — `PostCard.vue`, `AvatarPlaceholder.vue`. |
| 🟡 | **Timestamps** — When each item was published or last updated. | Có `timeAgo` và `datetime` trong post/comment detail; source-level chưa chứng minh chuyển sang full timestamp khi item cũ — `web-nuxt/pages/bai-viet/[id].vue:83-99`, `cong-dong.vue`. |
| 🟢 | **Engagement actions** — Ways to like, comment, share, save, or react. | Feed nối like/comment/bookmark/repost/quote/report/delete vào `PostCard` — `cong-dong.vue:307-315`, `PostCard.vue`. |
| 🟢 | **New content indicator** — A banner or button for new items after the feed loaded. | `showNewPostHint` render nút “Vừa có chuyện mới — cuộn lên xem” để không đẩy người đang đọc — `cong-dong.vue:23-32`, `cong-dong.vue:1440-1450`. |
| 🟢 | **Filtering** — Controls for category, content type, or followed accounts. | Tabs latest/trending/following/bookmarks, type filters, tag/search và URL sync có đủ — `cong-dong.vue:230-302`, `cong-dong.vue:540-600`. |
| 🟢 | **Pagination or infinite scroll** — Load more as the user reaches the bottom. | Có `Load more` và IntersectionObserver gọi `loadMore`, kèm bookmark pagination — `cong-dong.vue:375-378`, `cong-dong.vue:1071-1085`, `cong-dong.vue:1440-1450`. |
| 🟢 | **Empty state** — Explain empty feed and point to a first action. | EmptyState phân biệt bookmark/following/feed lỗi/no-post và gợi ý đăng bài, theo dõi hoặc khám phá — `cong-dong.vue:323-371`. |

### [Chat](https://www.checklist.design/web-app/chat)

Sản phẩm dùng chat với AI, không phải chat người-người; các item về read receipt, file share và emoji reaction vì vậy là lựa chọn phạm vi, không phải thiếu sót tự động.

| | Item | Why |
|---|---|---|
| 🟢 | **Message thread** — A chronological display of messages with the most recent at the bottom. | `renderedMessages`, SSE stream, auto-scroll và retry message được triển khai — `web-nuxt/components/ChatWidget.vue:18-37`, `:188-260`. |
| 🟡 | **Message input** — A text field for composing and sending messages, with support for multi-line input. | Có input Enter-to-send, maxlength và stop stream; chỉ là single-line `<input>`, chưa có multi-line/Shift+Enter — `ChatWidget.vue:42-49`. |
| 🟡 | **Sender identification** — Sender name/avatar alongside each message. | Phân biệt role user/assistant bằng class và nội dung nhưng không render tên/avatar; với AI có thể chấp nhận, song không đạt pattern đầy đủ — `ChatWidget.vue:18-28`. |
| 🔴 | **Timestamps** — Relative time for recent messages and full timestamp for older ones. | Message state chỉ lưu role/content/failed, không có timestamp hiển thị — `ChatWidget.vue:175-181`. |
| ⚪ | **Read receipts** — Whether the other participant has seen a message. | Không áp dụng cho chat AI một người dùng; không có participant cần xác nhận đã đọc. |
| ⚪ | **File and media sharing** — Attach images, files, or links within the conversation. | Chat hiện là text/SSE assistant; media upload có lane riêng trong community/entity, nên không mở ở widget này. |
| ⚪ | **Reactions** — Emoji reactions on individual messages. | Không cần cho assistant turn hiện tại; feedback được xử lý bằng receipt/API riêng (`agent/chat/api.py:3502-3634`). |

### [Admin Panel](https://www.checklist.design/web-app/admin-panel)

| | Item | Why |
|---|---|---|
| 🟢 | **Role-based access** — Admin panel only for users with appropriate permissions. | Tất cả page admin dùng middleware `admin`; backend map scope và default-deny qua `require_admin` — `web-nuxt/pages/admin/index.vue:282`, `agent/admin.py:368-400`. |
| 🟡 | **User management** — View users, invite, edit roles, and remove members. | Có users table, search/role filter, ban/unban, đổi role, pagination và confirmation; chưa thấy invite-member flow riêng — `web-nuxt/pages/admin/users.vue:20-142`. |
| ⚪ | **Organisation settings** — Account-level name, logo, SSO, and domains. | Sản phẩm hiện là consumer/public civic guide, không có workspace/SSO/domain organization để quản trị. |
| 🟡 | **Usage overview** — High-level usage metrics with export. | Dashboard và `/admin/thong-ke` có metrics, gaps, top entities, CSV; `/api/stats` contract/topology vẫn là F-19 và export scope cần proof — `admin/index.vue`, `admin/thong-ke.vue`. |
| ⚪ | **Billing and plan management** — Subscription, seats, invoices. | Non-goal hiện tại; legal copy tuyên bố không booking/thanh toán, nên không giả lập billing surface. |
| 🟡 | **Audit log** — Account actions such as logins, permission changes, and deletions. | Có DB/JSONL audit, trang lọc/export; coverage giữa reports, UGC, identity và anonymous info reports chưa thành một source-of-truth — F-10, `agent/admin.py:1479-1505`. |
| 🟡 | **Danger zone** — Destructive account-level actions with separated friction and confirmation. | User/account delete, ban và backup/admin destructive actions có confirm/guards; chưa có workspace transfer/delete vì org model không tồn tại — `web-nuxt/pages/cai-dat.vue:612-639`, `admin/users.vue:115-123`. |

### [Audit Log](https://www.checklist.design/web-app/audit-log)

| | Item | Why |
|---|---|---|
| 🟢 | **Event list** — Chronological table of action, actor, and timestamp. | Trang `/admin/nhat-ky` render table timestamp/method/path/actor/IP và API phân trang — `web-nuxt/pages/admin/nhat-ky.vue:35-67`, `agent/admin.py:1479-1503`. |
| 🟡 | **Actor identification** — User name and identifier, including system actions. | Có `actor`, `actor_role`, `actor_scopes` trong DB; UI chủ yếu render actor, chưa luôn hiển thị immutable user ID/system label — `agent/admin.py:245-261`, `nhat-ky.vue:49-55`. |
| 🟡 | **Event type** — Categorised action label such as login, permission change, deletion, export. | HTTP method và path cho biết loại thô; domain event taxonomy chưa được chuẩn hoá nên admin phải suy luận từ path — `nhat-ky.vue:51-53`, `agent/admin.py:276-277`. |
| 🟡 | **Affected resource** — Specific record and what changed. | Path/IP/reason/meta và DB before/after có khả năng lưu, nhưng UI không mở resource link hoặc before/after diff trong bảng — `agent/admin.py:214-218`, `nhat-ky.vue:52-54`. |
| 🟢 | **Date range filter** — Narrow log to a time period. | Hai `input type="date"` gửi `date_from/date_to` tới API — `nhat-ky.vue:13-24`, `agent/admin.py:1484-1492`. |
| 🟢 | **Search and filter** — Filter by user, event type, or affected resource. | Search input, method filter và API q/date filters tồn tại; UI có filter method/date, search field — `nhat-ky.vue:13-24`, `agent/admin.py:1484-1492`. |
| 🟡 | **Export** — Download audit log as CSV. | Có export CSV, nhưng source hiện serialize `entries` đang tải trên trang thay vì chứng minh export toàn bộ tập kết quả — `nhat-ky.vue:120-129`. |

### [Privacy](https://www.checklist.design/website/legal-privacy)

| | Item | Why |
|---|---|---|
| 🟡 | **Privacy policy** — Explain data collected, use, retention, and deletion requests. | Có sáu section, retention theo correction/account và link xoá; inventory chưa bao phủ mọi sink như bot, logs, JSONL, media, browser storage — F-06/F-10/F-11, `web-nuxt/utils/legalContent.ts:23-64`. |
| 🟡 | **Terms of service** — Agreement governing responsibilities, acceptable use, and liability. | Có account, UGC, report/takedown, third-party sources và disclaimer; premium/featured listing cần chốt wording thương mại/legal — `legalContent.ts:66-98`. |
| 🔴 | **Cookie policy** — Explain cookies, purposes, and user controls. | Không có tài liệu/chế độ xem cookie riêng; capability/CSRF cookies tồn tại nhưng inventory, purpose, expiry, SameSite/Secure và opt-out copy chưa được công bố — `agent/auth_middleware.py`, `web-nuxt/utils/legalContent.ts`. |
| 🟢 | **Last updated date** — Clear timestamp on each legal document. | `updated_date` được render ở hero của privacy và terms — `chinh-sach-bao-mat.vue:7-14`, `dieu-khoan-su-dung.vue:7-14`. |
| 🔴 | **Version history or changelog** — Explain changes between policy versions. | Không thấy lịch sử phiên bản/diff hoặc plain-language change summary; chỉ có một ngày cập nhật. |
| 🟡 | **Contact for legal queries** — Dedicated email/address for legal or privacy questions. | Có link trang Liên hệ và cấu hình `contact.email/claim_email`; chưa chứng minh dedicated legal/data owner/address và routing SLA — `lien-he.vue:87-88`, `legalContent.ts:59`. |

### [Account](https://www.checklist.design/web-app/account)

| | Item | Why |
|---|---|---|
| 🟢 | **Profile photo** — Upload or change profile image with fallback. | Settings upload avatar/cover, MIME accept và `AvatarPlaceholder` fallback — `web-nuxt/pages/cai-dat.vue:40-72`. |
| 🟢 | **Display name** — Name shown across the product. | Editable display name/full name render ở settings/profile/community — `cai-dat.vue:90-150`, `nguoi-dung/[id].vue:24-60`. |
| 🟢 | **Account details** — Email, phone, and other identifying fields relevant to the product. | Settings hiển thị phone/email/contact, login history, sessions và consent records — `cai-dat.vue:90-150`, `:229-270`, `:592-605`. |
| ⚪ | **Linked accounts (if applicable)** — Third-party account connections with disconnect. | Không có social sign-in/third-party account linking trong scope hiện tại; account là phone/OTP. |
| 🟢 | **Save confirmation** — Clear inline or toast feedback. | `showToast('Đã lưu hồ sơ')`, password/security/preference notices và rollback lỗi — `cai-dat.vue:861-934`, `:1497-1507`. |
| 🟢 | **Delete or deactivate account** — Clearly separated deactivate/delete actions. | Danger zone tách riêng, có confirm và trạng thái scheduled deletion/deactivation — `cai-dat.vue:612-639`, `:1435-1471`. |

### [2FA](https://www.checklist.design/web-app/2-factor-authentication)

| | Item | Why |
|---|---|---|
| 🟡 | **Method selection** — Authenticator app, SMS, or email code. | Setup UI hiện cung cấp authenticator; SMS là login OTP chứ chưa phải lựa chọn 2FA độc lập, nên chưa đạt gợi ý hai method — `cai-dat.vue:203-223`, `AuthModal.vue:207-257`. |
| 🟢 | **Setup instructions** — Step-by-step guidance, especially for authenticator setup. | Copy hướng dẫn quét QR, nhập mã six-digit và confirm trước khi bật — `cai-dat.vue:211-219`. |
| 🟢 | **QR code or setup key** — Scannable QR or copyable secret. | Render cả `setupData.qr` và `setupData.secret` — `cai-dat.vue:211-215`, `:1166-1186`. |
| 🟢 | **Verification step** — Enter a code to confirm setup before enabling. | Nút `Xác nhận & bật` gọi `confirm2FASetup`; account login cũng có TOTP challenge — `cai-dat.vue:219`, `AuthModal.vue:546-566`. |
| 🟢 | **Recovery codes** — One-time backup codes with copy/download. | Recovery list có copy, download và close-after-save — `cai-dat.vue:194-200`, `:1214-1225`. |
| 🟢 | **Setup confirmation** — Clear success state that 2FA is active. | Setup response đưa recovery codes; trạng thái enabled render “Đã bật” và remaining count — `cai-dat.vue:203-209`, `:1183-1188`. |
| 🟡 | **Disable or reset option** — Reconfigure/disable with re-authentication. | Có input mã và nút tắt; source chưa chứng minh re-authentication bắt buộc trong mọi disable path — `cai-dat.vue:203-210`, `:1193-1202`. |

### [Settings](https://www.checklist.design/web-app/settings)

| | Item | Why |
|---|---|---|
| 🟢 | **Structure** — Organise controls into logical categories. | Tabs hồ sơ, bảo mật, thông báo, quyền riêng tư, cá nhân hoá và nguy hiểm tách rõ — `web-nuxt/pages/cai-dat.vue:18-40`, `:612-639`. |
| 🟢 | **Account details** — Update name, email, and profile photo. | Profile form có display name/full name/email/avatar/cover với save action — `cai-dat.vue:40-150`. |
| 🟢 | **Security details** — Password, 2FA, and other security information. | Password form, 2FA, sessions, trusted devices và login history được gom trong tab bảo mật — `cai-dat.vue:163-270`. |
| 🟢 | **Notification preferences** — Choose notification types/channels. | Notification preference groups và toggles được render, lưu qua API, có offline/conflict notice — `cai-dat.vue:280-406`. |
| ⚪ | **Billing** — Payment/upgrade/cancel controls. | Không áp dụng với product non-commerce hiện tại và legal copy không nhận thanh toán. |
| 🟢 | **Additional preferences (if applicable)** — Language, timezone, date format, appearance. | Có theme Parchment/Nocturne, location/personalisation controls; language/timezone không phải setting hiện tại — `cai-dat.vue:300-350`, `:407-538`. |
| 🟢 | **Danger zone** — Destructive actions separated with confirmation. | Vô hiệu hoá/xoá tài khoản nằm trong tab và panel danger riêng, có confirm/rollback message — `cai-dat.vue:612-639`, `:1435-1471`. |

### [Data Table](https://www.checklist.design/web-app/data-table)

| | Item | Why |
|---|---|---|
| 🟢 | **Sortable columns** — Click headers to toggle ascending/descending. | Entity table có `aria-sort`, sort buttons và `toggleSort` cho ID/name/type/place — `web-nuxt/pages/admin/entities.vue:148-153`. |
| 🟡 | **Column visibility and order** — Show/hide/reorder columns with persistence. | Columns thay đổi theo kind nhưng không thấy control để user ẩn/kéo đổi hoặc persist preference — `admin/entities.vue:151-171`. |
| 🟢 | **Row selection and bulk actions** — Select rows and show action bar with count. | Checkbox từng dòng, select all, bulk assign/delete và count selected — `admin/entities.vue:77-113`, `:155-170`. |
| 🟡 | **Row actions on hover** — Contextual edit/delete/view actions on row hover. | Edit/clone/delete luôn hiện trong action cell, không phụ thuộc hover; vẫn đủ actions nhưng khác pattern checklist — `admin/entities.vue:192-197`. |
| 🟢 | **Search and filter** — Quick search alongside attribute filters. | Search, type/orphan filters, kind chips và active count đặt cạnh bảng — `admin/entities.vue:11-66`. |
| 🟢 | **Pagination** — Navigate pages and indicate total scale. | Previous/next, current page, total entity and last-page hint — `admin/entities.vue:214-224`. |
| 🟡 | **Frozen columns** — Pin first column for wide tables. | Bảng có horizontal wrapper nhưng source chưa thấy `position: sticky`/frozen first column; cần browser capture để xác nhận usability — `admin/entities.vue:145-224`. |
| 🟢 | **Export action** — Download visible or selected rows. | JSON/CSV export buttons trên toolbar, label rõ số entity của page hiện tại — `admin/entities.vue:11-30`. |
| 🟢 | **Empty and loading states** — Distinct fetch/loading and no-row states. | Skeleton table, load error retry và empty search/create state có riêng — `admin/entities.vue:115-140`, `:201-212`. |

### [Empty State](https://www.checklist.design/web-app/empty-state)

| | Item | Why |
|---|---|---|
| 🟢 | **Illustration or icon** — Contextual visual rather than a broken-looking blank. | Reusable `EmptyState` có icon/iconName hoặc illustration contextual, tone error riêng — `web-nuxt/components/EmptyState.vue:1-40`. |
| 🟢 | **Clear heading** — Plain-language title naming what's missing. | Callers dùng “Chưa lưu bài viết nào”, “Không có báo cáo nào”, “Đăng nhập để xem thông báo” — `da-luu.vue`, `thong-bao.vue`, `admin/bao-cao.vue`. |
| 🟢 | **Supporting description** — Explain what belongs here. | `message`/`hint` props và empty copy theo context được render — `EmptyState.vue:35-40`, `cong-dong.vue:323-371`. |
| 🟢 | **Primary action** — Point to creating/importing/next step. | Empty slots có đăng nhập, khám phá, tạo entity, thử lại, clear filter tùy context — `EmptyState.vue:40-45`, `admin/entities.vue:206-212`. |
| 🟢 | **Zero state vs. no-results state** — Distinguish new/empty from query/filter no-results. | Search/report/saved/entities copy tách `!reports.length` khỏi `reports.length but filter empty`, và có reset route — `admin/bao-cao.vue:147-164`, `da-luu.vue:85-114`. |
| 🟢 | **Error state variant** — Separate failed load from genuine emptiness. | `tone="error"`, `role="alert"`, skeleton and retry are separate from empty state — `EmptyState.vue:3-6`, `thong-bao.vue:58-65`. |

### [Dashboard](https://www.checklist.design/web-app/dashboard)

| | Item | Why |
|---|---|---|
| 🟡 | **Welcome state** — Re-orient returning users with what's happened since last visit. | Admin dashboard có title/subtitle và recent activity, nhưng chưa có user-specific welcome/since-last-visit summary — `web-nuxt/pages/admin/index.vue:3-8`, `:184-200`. |
| 🟢 | **Key metrics** — Relevant numbers readable without leaving home. | Entities, places, relationships, itineraries, users/posts, quality và health metrics render trên dashboard — `admin/index.vue:26-75`, `:99-115`. |
| 🟢 | **Recent activity** — Recent created/updated items. | Recent admin audit actions render method/path/time — `admin/index.vue:184-200`, `agent/admin.py:1233-1241`. |
| 🟢 | **Needs attention** — Time-sensitive queues surfaced prominently. | Dynamic priority alerts link moderation, reports, images, provisional and quality queues — `admin/index.vue:79-96`, `agent/admin.py:1150-1187`. |
| 🟢 | **Quick actions** — Common tasks accessible from landing page. | Entity, data quality, moderation and Knowledge Agent shortcuts — `admin/index.vue:211-220`. |
| 🟢 | **Empty state** — Blank dashboard points to first action. | All-clear alert, degraded/error state, zero queue and chart empty panels exist — `admin/index.vue:14-23`, `:89-96`, `:184-200`; deeper panel empty states in `admin/thong-ke.vue`. |
| ⚪ | **Layout control (if applicable)** — Show/hide/reorder widgets. | Dashboard không tuyên bố customizable workspace; fixed operator cockpit là chủ ý hiện tại. |

### [Notifications](https://www.checklist.design/web-app/notifications)

| | Item | Why |
|---|---|---|
| 🟢 | **Notification list** — Chronological feed of alerts and activity. | `/thong-bao` fetches paged notifications and renders title/body/time list — `web-nuxt/pages/thong-bao.vue:35-54`, `:111-136`. |
| 🟢 | **Read and unread states** — Clear distinction and unread count. | `is_read`, unread class/dot, “Đọc tất cả” and menu unread badge — `thong-bao.vue:36-47`, `UserMenu.vue:16-20`. |
| 🟢 | **Notification type** — Visual/label for type. | Type filters and icon mapping like/comment/follow/mention/repost — `thong-bao.vue:51-55`, `:138-146`. |
| 🟢 | **Timestamp** — Relative recent and full older time. | `<time datetime>` plus `timeAgo`; exact old-date formatting is delegated to shared composable — `thong-bao.vue:45-47`, `:84-88`. |
| 🟢 | **Actions (if applicable)** — Action related to notification. | Links open target and mark read; no-target notifications are keyboard-activatable; dismiss is available — `thong-bao.vue:35-56`, `:155-184`. |
| 🟢 | **Mark all as read** — Single action to clear unread indicators. | Header button calls `/api/notifications/read-all` with optimistic rollback — `thong-bao.vue:6-8`, `:172-181`. |
| 🟢 | **Empty state** — Clear no-notification message. | EmptyState differs all vs filtered type and guest state — `thong-bao.vue:58-67`. |

### [Public Profile](https://www.checklist.design/web-app/public-profile)

| | Item | Why |
|---|---|---|
| 🟢 | **Avatar and display name** — Primary profile identifier with fallback. | Cover/avatar/image or initials, display name and share controls are prominent — `web-nuxt/pages/nguoi-dung/[id].vue:5-60`. |
| 🟢 | **Role or title** — Relevant role/title in context. | Reputation level/badges and member eyebrow provide community role context; role is not employment title — `nguoi-dung/[id].vue:61-92`. |
| 🟢 | **Bio or description** — User-written short description. | `profile.bio` renders when present — `nguoi-dung/[id].vue:93-95`. |
| 🟢 | **Activity or contributions** — Public posts, reviews, and activity summary. | Tabs posts/reviews/timeline, counts and heatmap are shown only when profile is public — `nguoi-dung/[id].vue:116-180`. |
| 🟢 | **Contact or follow action** — Follow/connect depending on product. | Follow button and share/report/block menu exist; no direct private messaging is intentionally exposed — `nguoi-dung/[id].vue:40-60`. |
| 🟢 | **Joined date (optional)** — Date user joined. | `profile.created_at` renders a joined date — `nguoi-dung/[id].vue:146-160`. |
| 🟢 | **Profile visibility controls** — Fields follow privacy preferences. | Public/private state is shown, private profile hides activity and settings expose profile visibility/show_activity/show_saved controls — `nguoi-dung/[id].vue:62-74`, `cai-dat.vue:315-351`. |

### [Report View](https://www.checklist.design/web-app/report-view)

Sản phẩm hiện có report/analytics surfaces dành cho admin, không phải một report-builder tùy biến cho khách hàng.

| | Item | Why |
|---|---|---|
| 🟡 | **Report metadata** — Title, author, date range, and generation time. | `admin/thong-ke` có title và selected 7/30/90/all range; author và generation timestamp chưa được render thành field riêng — `web-nuxt/pages/admin/thong-ke.vue:3-25`. |
| 🟢 | **Summary or key findings section** — Narrative/highlights before detail. | Summary cards total queries, unique queries, gaps and cost đứng trước panels — `admin/thong-ke.vue:39-69`. |
| 🟢 | **Data visualisations** — Charts/tables/graphs for interpretation. | Sparkline, ranked bars and dashboard donut/bar charts có accessible labels — `admin/thong-ke.vue:48-58`, `admin/index.vue:224-280`. |
| 🟡 | **Filter capabilities** — Explore underlying data by chart/row. | Có date-range chips và knowledge-gap links sang entity search; chart/row drill-down tương tác chưa đầy đủ — `admin/thong-ke.vue:15-25`, `:88-116`. |
| 🟢 | **Export to PDF, CSV, or spreadsheet** — Download for sharing/analysis. | Analytics report có CSV export; PDF/spreadsheet riêng chưa có, CSV là format phù hợp hiện tại — `admin/thong-ke.vue:7-11`, `:184-196`. |
| 🟡 | **Table of contents** — Navigate report sections. | Report có headings “Phân tích chi tiết” và panels nhưng không có TOC/anchor navigation như legal pages — `admin/thong-ke.vue:73-116`. |

### [Maintenance](https://www.checklist.design/web-app/maintenance)

| | Item | Why |
|---|---|---|
| 🟡 | **Clear status message** — Explain scheduled maintenance versus unexpected outage. | `error.vue` có thông báo server error đang sửa chữa, nhưng không có maintenance surface riêng phân biệt scheduled/outage — `web-nuxt/error.vue:38-47`. |
| 🔴 | **Estimated return time** — Give a specific expected return time. | Không thấy ETA/maintenance window trong error or dedicated page. |
| 🔴 | **Status page link** — Link to an independently reachable live status page. | Không thấy status-page URL/link trong `web-nuxt` hoặc siteops maintenance response. |
| 🟡 | **Contact or support link** — Reach support for urgent issues. | Error 403 copy nói “Liên hệ hỗ trợ” nhưng CTA không nối tới contact; `/lien-he` tồn tại ở site-level — `error.vue:45`, `web-nuxt/pages/lien-he.vue`. |
| ❔ | **Brand consistency** — Maintenance page styled consistently with the product. | Có error illustration/CSS theo brand, nhưng chưa có maintenance page/render capture; screenshot hoặc URL chạy thật sẽ quyết định trạng thái visual. |

### Beyond the checklist

- **Trust/freshness is product-critical, not a decoration.** A generic checklist can say “status” is present, but VinhLong360 must show source, `verifiedAt`, approximate-location disclosure, provisional state and correction path together wherever a visitor makes a real-world decision.
- **The correction journey is higher-stakes than a normal form.** The important proof is not only submit/loading/success; it is that reported value, evidence, OTP capability, decision, publication, cache/search consumers, receipt and erasure all refer to one case and one generation. Existing F-01/F-02/F-10/F-32/F-40/F-41 remain the relevant blockers; this re-audit does not invent duplicate findings.

## 5.6 Design-system audit — token authority và từng module

### Phạm vi và phán quyết riêng

Audit này áp dụng design-system skill vào token, cascade, typography, spacing/radius, component state/variant, layering, motion preference và accessibility preference. Bằng chứng là source/config/test; không có browser capture mới nên không kết luận pixel-level về mọi hover, focus ring, contrast, animation hay responsive breakpoint. Hai script màu/contrast và accessibility chỉ là các lát cắt có chọn lọc.

**Phán quyết:** hệ thống đã có ý đồ thiết kế rõ (Mekong palette, Nocturne/Parchment, 3 tầng token, touch target và preference rules), nhưng “authority” chưa khép. Public shell mới có ratchet tốt hơn; module cũ, AdminCP và page-local CSS vẫn tiêu thụ alias/giá trị thô. Đây là nợ governance có thể biến thành regression chéo module, không chỉ là vấn đề thẩm mỹ.

### 5.6.1 Bản đồ authority token

| Tầng | Ý định | Bằng chứng hiện tại | Đánh giá |
|---|---|---|---|
| Primitive | Tên theo cảnh quan và màu vật liệu (`clay`, `amber`, `leaf`, `river`, `sand`, `night`) | `variables.css:8-33,225-236` | Có nguồn nền rõ; cần registry để phân biệt primitive semantic với primitive trang trí. |
| Semantic | Vai trò (`--color-canvas`, `--color-action`, `--color-error`, ...) tự remap theo theme | `variables.css:35-90,720-790` | Tốt ở token mới, nhưng alias legacy vẫn là API thực tế của nhiều module. |
| Component/role | Radius, framed dossier, theme control, chip/gallery/detail, card variants | `variables.css:100-116,483-485,703-716,968-990` | Khai báo khá phong phú nhưng mức tiêu thụ không đồng đều; nhiều token mới chỉ là catalog. |
| Compatibility/context | Giữ `--primary`, `--bg`, `--card` và remap theo `data-color-system` | `variables.css:148-200,614-618`; `tri-region-color.css:1-25` | Hữu ích cho di trú, nhưng cùng một tên có thể mang brand hoặc action tùy DOM context; cần boundary/lint. |

### 5.6.2 Cascade và theme mode

- Có `:root { color-scheme: light }` ở `variables.css:6-7`, rồi một `:root { color-scheme: dark; ... }` làm Nocturne mặc định ở `:root:673-718`; `.light`, `.dark` và `@supports (color: oklch(...))` tiếp tục ghi đè. Đây có thể là chủ ý, nhưng computed authority không thể suy ra an toàn chỉ bằng cách đọc một block.
- `--surface-2/3` phẳng ở light nhưng color-mix ở dark; `--border`, `--border-input`, `--save-red`, `--on-warning` có các lớp override khác nhau. Mỗi token đơn lẻ có lý do, song thiếu cascade fixture khiến thêm selector mới dễ tạo theme split.
- `tri-region-color.css` remap `--primary` thành `--color-action` trong một số page recipe; shared `.btn` và link vẫn đọc `--primary`. Component tái sử dụng ngoài recipe có thể đổi ngữ nghĩa mà không đổi markup.

**Bằng chứng cần bổ sung:** fixture DOM tối thiểu cho default Nocturne, `.light`, `.dark`, `data-color-system=tri-region-v1`, `prefers-contrast`, `forced-colors` và `prefers-reduced-transparency`; lưu computed token map và ảnh/DOM snapshot trong CI.

### 5.6.3 Typography và content density

- Docs quy định Inter + `font-optical-sizing: auto`, nhưng runtime thực dùng `Be Vietnam Pro`/`Fraunces` (`variables.css:329-334`, `nuxt.config.ts:39-42`); không thấy declaration optical sizing trong toàn `web-nuxt`.
- Body có line-height token và input baseline, nhưng page-local heading/label ở AdminCP và community vẫn có font-size/tracking trực tiếp. Điều này làm cùng một hierarchy (label, caption, title) thay đổi khi component đi qua module.
- Fraunces là lựa chọn editorial có chủ ý và phù hợp tên địa danh/tiêu đề; vấn đề là docs/implementation không cùng authority, không phải bản thân cặp font sai.

### 5.6.4 Spacing, radius và density

- Purpose tokens hiện có `--radius-control: 8px`, `--radius-surface: 12px`, `--radius-sheet: 20px`; đó là hướng di trú hợp lệ, không nên quay lại một thang generic khác.
- Tuy nhiên page/admin/local CSS vẫn dùng raw 6/8/10/12/14px và các padding/margin literal. Chênh lệch thấy rõ ở dashboard, entities, moderation, AI, settings và itinerary builder; public cards dùng token nhiều hơn.
- Touch baseline 44px được đặt trong docs/base, nhưng admin có compact controls 32/36/40px. Snapshot accessibility 720px hiện không bắt được vi phạm, nên cần xác minh theo route và trạng thái thật trước khi coi đây là exception được chấp thuận.

### 5.6.5 Component states, variants và motion

- Shared components có nền tốt: `.btn` có hover/active/focus-visible/disabled; input có focus/error/success/disabled/readonly; base có reduced-motion, prefers-contrast, forced-colors và reduced-transparency blocks (`base.css:927-1055`).
- State token M3 và card variant token chưa được consume (F-65). CSS thực tế còn hardcode opacity/background/shadow, khiến dark/high-contrast tuning không có một điểm điều khiển.
- Local modules không đồng đều: `CorrectionIntakeForm` có reduced-motion nhưng không có focus-visible riêng; `ChatWidget` có retry focus nhưng không có local reduced-motion/forced-colors; admin AI/community có block riêng. Dựa vào global rule là hợp lệ, nhưng cần ghi trong component contract để tránh khi tách CSS khỏi base.

### 5.6.6 Ma trận từng module đã tách

| Module | Token/typography hiện dùng | State/density evidence | Rủi ro thiết kế-system | Verdict |
|---|---|---|---|---|
| `cases/` | Trộn `--color-error` với `--bg-alt`, `--border`, `--muted`; raw radius 8/10px | Review/error summary rõ; reduced-motion có; focus dựa global | Một form correction có thể đổi surface/contrast khi đặt trong recipe khác | Freeze compatibility trước pilot; canonicalize trước public launch |
| `identity/` | Auth/settings còn `--primary`, `--bg`, `--card`, `--muted`; heading dùng Fraunces | Consent/OTP state có; focus chủ yếu global; nhiều spacing local ở `cai-dat.vue` | Typography và appearance control tách khỏi shared control grammar | P2 drift, dễ tạo hai “settings language” |
| `community/` | 147 legacy refs trong page scan, chỉ 1 `--color-*`; nhiều rgba/local radius | 15 focus-visible, 6 reduced-motion block; feed/moderation state phân tán | Bề mặt lớn nhất, selector-local override khó audit theo theme | P2 regression surface cao |
| `entities/` | 72 legacy refs; shared input/table nhưng local colors/radius | Có focus/reduced-motion; action row source khai 32px | Quality queue, table và image action không cùng density/audit grammar | Cần admin component tokens + snapshot |
| Admin dashboard/siteops | Dashboard/layout dùng metric colors, rgba và radius 10/14px; legacy semantic chiếm ưu thế | Layout admin có focus/reduced-motion nhưng compact pagination/refresh 36px | Control plane có thể “đúng dữ liệu” nhưng trình bày khác mode/priority giữa screen | Cần một admin recipe và exception registry |
| `llmops/` | 48 legacy refs, gần như không `--color-*`; status trả màu inline/legacy | Reduced-motion có; ad-hoc status/error/triage surfaces | Rõ nhất về divergence khỏi public Nocturne token authority | P2 trước scale AI operations |
| `itineraries/` | Public card qua shared CSS; builder/detail dùng alias và literal radius/rgba | Reduced-motion ở page; nhiều focus dựa global | Public projection và builder có cảm giác thuộc hai hệ khi chuyển route | Chuẩn hóa recipe card/step/action |
| `chat/` | Local style dùng alias; panel/base đã tokenized hơn | Retry/send 44px, stream/typing reduced-motion chủ yếu global/base | Floating/modal semantics và state token chưa có component contract độc lập | Cần fixture desktop/mobile + preference |

### 5.6.7 Màu, z-index và accessibility preference

- Raw color debt tập trung ở `dark-overrides.css`, `detail.css`, `components.css`, `base.css`, `cards.css` và AdminCP. Không nên token hóa mù các scrim/media/SVG; phải tách semantic interactive color khỏi scene palette và forced-colors fallback.
- Z-index scale có tên và thứ tự tốt ở `variables.css:594-606`, nhưng raw `1200` ở hai drawer phá vỡ registry (F-67). Đây là rủi ro thứ tự layer, không phải chỉ là con số lớn.
- Base đã có `prefers-reduced-motion`, `prefers-contrast`, `forced-colors`, `prefers-reduced-transparency`; lần chạy cuối của script accessibility ghi nhận forced colors active, controls đại diện 7/7 bounded, overflow 0, contrast violation 0, LCP 384ms, CLS ~0,0546, INP 0ms. Lệnh vẫn exit 1 vì bundle gzip 811KB vượt budget 278KB; không được diễn giải thành “accessibility fail”.
- Chưa có capture cho từng module, nên trạng thái focus ring, hover, disabled differentiation, 200% text scale và modal/drawer stacking vẫn là `❔ Can't tell` ở runtime.

### 5.6.8 Remediation và acceptance gate

1. Chốt canonical public semantic tokens và compatibility aliases có expiry/owner; thêm lint không cho legacy drift.
2. Cập nhật design docs về Be Vietnam Pro/Fraunces hoặc đổi runtime về Inter; kiểm font loading, optical sizing và Vietnamese diacritics.
3. Làm cho card/button/input/table/dialog state tokens có consumer thật; thêm state matrix và computed-style snapshots.
4. Tạo admin recipe: control, table, badge, panel, density; ghi rõ ngoại lệ 32/36/40px nếu thực sự cần cho workbench.
5. Thêm `--z-drawer` và layer registry; kiểm simultaneous overlay interactions.
6. Xây exemption registry cho raw color và ratchet theo region; catalog/detail phải có debt budget giảm dần.
7. Bổ sung browser evidence cho mọi module: desktop/mobile, keyboard, reduced motion, forced colors, 200% zoom/text scale, light/dark và dynamic content states.

**Acceptance tối thiểu trước public launch:** token lint không tăng debt; docs/runtime font contract khớp; mọi component state có owner/token; admin density exception được ký; cascade/layer fixtures xanh; browser matrix không có lỗi contrast/focus/overflow; bundle budget được xử lý hoặc risk acceptance có owner.

## 5.7 Systematic-debugging re-audit — truy từ triệu chứng về nguồn

### 5.7.1 Triệu chứng, reproduction và root cause

| Triệu chứng quan sát | Tái hiện/đối chiếu | Truy ngược boundary | Root cause hiện tại | Kết luận |
|---|---|---|---|---|
| Full-suite in `HẾT-DIFF` nhưng summary có `12 errors` | Đọc artifact `b3p3a0fbl.output`; chạy synthetic parser probe với một dòng `FAILED` và một dòng `ERROR` → parser vẫn trả `HET-DIFF` | `pytest` output → `out.splitlines()` → regex `^FAILED` → `got` → `new/missing` → verdict | Harness chỉ mô hình hóa failed, không mô hình hóa error/return code; không phải lỗi pytest | F-69 là lỗi evidence pipeline, 12 errors vẫn chưa được phân loại |
| Cùng repository có baseline 15 fail nhưng handoff nói không có fail | So sánh `CLAUDE.md`, `ROADMAP.md`, `HANDOFF.md` và handoff 2026-08-31 | Tài liệu onboarding → lệnh baseline → roster expected → triage outcome | Không có registry freshness/authority; header `active` không bảo đảm tài liệu khớp HEAD | F-70 là lỗi governance; không tự suy ra lỗi sản phẩm |
| Erasure API phải đổi câu chữ khi kéo cầu dao | Focused HTTP/config suite: `20 passed` | Settings → `config.erasure_is_audit_only()` → scheduler delegate + identity response → transport test | Hai consumer đã được nối vào một nguồn sự thật; đây là path đã được sửa, không phải finding mới | Bằng chứng fix P0 hiện có, nhưng vẫn cần runtime PG/worker proof |
| Accessibility gate exit 1 dù snapshot không có lỗi a11y | Chạy script: controls 7/7, overflow 0, contrast 0; reason duy nhất `bundle-budget-exceeded` | Browser probe → snapshot metrics → bundle audit → exit status | Gate gộp accessibility và bundle vào một exit code; cần tách verdict để không đọc sai | Không gọi đây là accessibility failure; bundle vẫn là release blocker riêng |

### 5.7.2 Pattern analysis và giả thuyết đã kiểm

- **Giả thuyết H1:** 12 errors là regression sản phẩm. Chưa đủ bằng chứng; artifact chỉ có số đếm, không có nodeid/trace. Không được đưa vào “known failure” hay bỏ qua.
- **Giả thuyết H2:** 12 errors là nhiễu môi trường như đợt disk-full trước. Có tín hiệu hỗ trợ (số lượng thay đổi giữa lượt), nhưng chưa chứng minh; cần chạy lại với disk budget, temp-root và PG test databases đã ghi manifest.
- **Giả thuyết H3:** `HẾT-DIFF` chứng minh suite sạch. Bị bác bỏ trực tiếp bởi parser source và synthetic reproduction; không dùng verdict này cho release.
- **Giả thuyết H4:** focused erasure test xanh chứng minh worker/PG erasure production đúng. Bị bác bỏ về phạm vi: test HTTP/config không đi qua PostgreSQL scheduler, shared lease, restart hay actual sink deletion.

### 5.7.3 Defense-in-depth cần có ở release evidence

1. **Entry:** runner kiểm disk free, temp-root writable, required PG URLs và branch/HEAD SHA trước khi chạy.
2. **Execution:** giữ nguyên stdout/stderr, return code, duration, environment summary và collection errors; không chỉ giữ dòng summary.
3. **Classification:** parse `FAILED`, `ERROR`, `SKIPPED`, `XFAIL`, interruption và collection failure thành schema máy đọc được; allowlist phải match nodeid/prefix rõ ràng.
4. **Verdict:** chỉ in `HẾT-DIFF` khi failed **và** error **và** collection/interruption đều không có ngoài allowlist; không coi `returncode != 0` là xanh.
5. **Artifact:** lưu JSON/NDJSON có `head_sha`, test command, Python/pytest version, disk trước/sau, PG target đã che secret và checksum của output.

### 5.7.4 Phần chưa thể kết luận

- Chưa chạy lại full-suite 28 phút chỉ để lấy 12 error nodeid; việc này cần máy đủ dung lượng, PG test databases và thời gian vận hành phù hợp. Vì vậy audit nâng mức cảnh báo về evidence integrity, không khẳng định 12 errors là regression sản phẩm.
- Chưa có production/browser evidence cho các module; focused tests chỉ xác nhận boundary cụ thể, không thay thế multi-process, proxy, worker restart hoặc external provider tests.

## 6. Các mẫu nguyên nhân gốc

### 6.1 Contract drift

`reportedValue`, `provisional_count/pending`, `/api/stats` và phone verification đều là biến thể của cùng một lỗi: producer và consumer có schema khác nhau nhưng không có contract test chạy xuyên tầng. Fix riêng từng dòng sẽ tạo lỗi mới ở điểm kế tiếp.

**Biện pháp:** schema generate từ một authority, contract tests FE↔API, fixture success/error, và browser smoke bắt buộc cho flow có cookie/OTP/receipt.

### 6.2 Truth drift

`verifiedAt` top-level/nested, `data.json`/DB, approximate coordinate flag và timestamp là những nơi hệ thống có nhiều “sự thật” cạnh tranh. Khi public projection loại một field hoặc đọc sai tầng, UI có thể nói ngược với artifact.

**Biện pháp:** canonical schema + migration, provenance tuple (source, actor, observed_at, verified_at, confidence), invariant kiểm tại import/runtime/export.

### 6.3 Lifecycle drift

Report JSONL, PostgreSQL, logs, bot memory, browser storage và object storage có retention riêng. Một nút “delete account” chỉ đáng tin khi có inventory và evidence không còn identifier ở tất cả sink.

**Biện pháp:** data map có owner/retention/delete method cho từng store; erasure job idempotent; tombstone/audit không chứa PII; quarterly restore/erasure drill.

### 6.4 Operational non-closure

Có `backup`, `restore`, `prometheus`, `watchdog`, `deploy` nhưng các artifact/target/format không khớp. Đây là “control theater” nếu chỉ nhìn file tồn tại thay vì chứng minh đường đi end-to-end.

**Biện pháp:** mỗi control có một executable acceptance path: create → verify → consume → alert/rollback; bỏ `continue-on-error` ở gate có tác động dữ liệu.

### 6.5 Governance defaults

Development environment mặc định, credential fallback, autonomous promotion, noindex và AI-only media đều là quyết định có chủ ý hoặc tạm thời. Nếu không được biểu diễn thành startup guard/policy matrix, người triển khai sau sẽ đọc nhầm chúng là behavior an toàn mặc định.

**Biện pháp:** fail-closed production config, policy-as-code, decision log có expiry/reviewer và preflight kiểm đúng owner decision.

### 6.6 Search as a trust boundary

Search không chỉ là tính năng tăng trưởng. Nó là cửa người dùng dùng để kiểm chứng “địa điểm này có tồn tại không” và là đường vào correction. Khi ranking bị cắt theo confidence/ID, autocomplete không dùng cùng lexical contract, hoặc SQLite/PG xử lý dấu khác nhau, hệ thống có thể trả lời sai theo kiểu không báo lỗi: dữ liệu đúng vẫn nằm trong kho nhưng người dùng không tìm thấy.

**Biện pháp:** coi recall@k, exact-match rate, accent parity và pagination completeness là SLO; ghi query fixture vào release evidence; không dùng “có bản ghi trong DB” làm bằng chứng discoverability.

### 6.7 Cache coherence as correction authority

Một correction chỉ có giá trị nếu mọi projection đọc cùng generation dữ liệu. Hiện invalidation được chia theo module (LLM, place, KB context, semantic, review, similar, homepage), không có registry/generation chung. Vì vậy test “DB đã đổi” có thể xanh trong khi người dùng vẫn đọc snapshot cũ từ một consumer khác.

**Biện pháp:** version/generation cho entity snapshot; một invalidation bus/adapter cho mọi cache; acceptance test đọc chéo chat → detail → review → similar → homepage ngay sau mutate.

### 6.8 Time and chronology invariants

Timestamp đảo trong catalog và timezone rời rạc trong consumer làm yếu cả factual freshness lẫn trải nghiệm theo mùa. Đây là lỗi khó thấy vì chỉ xuất hiện ở boundary, khi mỗi module riêng lẻ vẫn có test hợp lệ.

**Biện pháp:** chuẩn hóa UTC storage + VN presentation bằng clock injectable; kiểm thứ tự `created_at ≤ updated_at` hoặc gắn cờ “unknown chronology”; boundary tests là release gate, không phải test phụ.

### 6.9 Data-subject completeness

Export và erasure là hai mặt của cùng một inventory. Nếu export không liệt kê một sink thì owner cũng không thể tự phát hiện sink đó khi yêu cầu xoá; nếu query cắt 5.000 dòng không báo, “đã export toàn bộ” là claim không thể kiểm toán.

**Biện pháp:** data map có cặp cột `exported_by`/`erased_by` cho từng bảng, manifest đếm row và cờ truncation, phân biệt content cần trả với secret chỉ cần chứng minh đã huỷ.

### 6.10 Scale topology and singletons

Rate-limit fallback và scheduler hiện dựa vào state trong process. Một instance đơn lẻ có thể đúng, nhưng scale ngang hoặc restart biến semantics thành “mỗi process một thế giới”. Đây là rủi ro topology chưa được thể hiện trong compose/readiness evidence.

**Biện pháp:** mọi control có phân loại `process-local`/`shared`/`leader-owned`; production preflight từ chối cấu hình nhiều worker nếu chưa có lease/shared store; chaos/load test chạy đúng topology phát hành.

### 6.11 Boundary extraction không làm giảm độ phức tạp nội tại

Tách `server.py` thành router con đã giảm duplicate route và làm ownership nhìn thấy, nhưng phần lớn miền vẫn là file rất lớn với nhiều trách nhiệm cùng lúc: community trộn feed, moderation, collection, media và report; entities trộn CRUD, quality, image saga và KB sync; chat trộn transport, privacy, cache, provider và optional subsystems. Vì vậy coupling chuyển từ “import rõ” sang “global/helper/DB convention ngầm”.

**Biện pháp:** sau mỗi lần tách, đo thêm fan-in/fan-out, số side effect, transaction boundary và state owner; chỉ coi module hoàn tất khi domain service/repository/transition/adapter có thể test độc lập mà không monkeypatch composition root.

### 6.12 Control-plane optimism

Backup, health, quality queue, announcement, stale review và scheduler status đều là cơ chế để operator biết hệ thống đang làm gì. F-45, F-54, F-57, F-58 và F-61 cho thấy control-plane có thể báo số sai, 500, snapshot cũ hoặc cooldown sai trong khi core data vẫn chạy. Đây là rủi ro điều hành cao hơn một lỗi UI vì nó làm chậm phát hiện và khắc phục sự cố.

**Biện pháp:** mọi control-plane endpoint phải có degraded-but- truthful contract: per-check isolation, `snapshot_id`, `last_success`, `last_error_code`, correlation ID và metric về stale age; test failure injection phải kiểm cả nội dung response lẫn exit/alert semantics.

### 6.13 Test determinism đang che production topology

Conftest chủ động ép `SCHEDULER_ENABLED=false`, `USE_PG=false`/SQLite tạm, reset circuit/rate-limit và redirect audit file để suite ổn định. Những guard này hợp lý cho unit test, nhưng nếu không có stage đối chứng thì test xanh chỉ chứng minh behavior trong một process, không chứng minh PG schema, worker cạnh tranh, proxy cache, subprocess hay external provider.

**Biện pháp:** chia báo cáo test thành `unit-isolated`, `PG integration`, `multi-process/chaos`, `browser/proxy` và `external-side-effect sandbox`; mỗi release phải có tối thiểu một bằng chứng từ nhóm sau cùng cho từng P1 liên quan.

## 7. Go/No-Go và tiêu chí mở khóa

### Closed pilot — Go có điều kiện

Chỉ mở cho nhóm mời, noindex vẫn bật, không dùng claim “đã kiểm chứng” nếu thiếu `attributes.verifiedAt`, và phải có người trực xử lý correction. Điều kiện tối thiểu:

1. **Toàn bộ 28 P1** (F-01–F-17, F-32, F-34, F-38, F-40–F-42, F-44, F-47, F-49, F-53, F-69) đã có fix + test/browser evidence; riêng F-10/F-11 phải có erasure drill, F-40/F-41 phải có decision-path proof, F-42/F-49 phải có concurrency/lifecycle proof, F-53 phải có provider-side idempotency hoặc risk acceptance được ký, và F-69 phải có full-suite verifier versioned xử lý cả `ERROR`/return code.
2. F-13 backup/restore chạy được trên artifact mới; F-14 có alert receiver thật; F-15 có staging rollout/rollback.
3. F-10/F-11 có data inventory và erasure drill cho một user/report mẫu.
4. Có owner/on-call, support route, correction SLA clock và incident escalation.
5. Chạy đúng bộ test theo `CLAUDE.md`: temp-root Windows, `npx vitest run`, `npm run typecheck`, backend tests chạy chung; ghi rõ 15 known failures và không có fail mới.

### Task 14 — proof-first acceptance snapshot (2026-09-02)

- Runner: `scripts/ops/run_pilot_acceptance.py`; authority: `config/release-authority.json`; owner: `service-owner`.
- Local artifact: `artifacts/pilot-acceptance.json`, ID `pilot-acceptance-20260902T020417Z`, canonical envelope digest (`output_sha256`) `f955d16598ebe1c2a74a62f20879b57ba36400e7e0a4ce58ee01ca98cdae1d63`, HEAD `7bd85e772843ac5ab3c7db656a1b0766aed8ede3`.
- Coverage envelope contains all 28 P1 sections and the five required layers (`unit`, `postgres`, `multi_process`, `browser`, `external_side_effect`); no raw personal data, secrets, production calls, or provider calls are recorded.
- Gate result: **NO_GO**. PostgreSQL evidence is unavailable (`postgres-integration-command-not-run`; Docker availability is never treated as PostgreSQL proof), multi-process contention evidence is unavailable (`multi-process-contention-command-not-run`), browser evidence is unavailable (`browser-base-url-not-supplied`), external provider/object retry evidence is unavailable, and owner sign-off/decision-required approvals are not recorded. The external layer is a local no-provider sandbox receipt only.
- This snapshot is local and time-bounded (24 hours); it is not a public-launch claim. Re-run the complete matrix on a disposable PostgreSQL/browser host after the owner and legal/provider decisions are signed.

#### Đính chính 2026-09-02 — artifact id/digest trên là giá trị **point-in-time**

Giữ nguyên khối Task 14 phía trên làm bản ghi lịch sử. Khối này **supersedes** hai con
số định danh trong đó.

- **Artifact được sinh lại mỗi lần chạy**, nên mọi ID/digest được trích dẫn trong tài liệu
  chỉ đúng tại thời điểm ghi. ID `pilot-acceptance-20260902T020417Z` và `output_sha256`
  `f955d165…` ở trên **đã bị thay**; bundle hiện tại trên máy là
  `pilot-acceptance-20260902T104323Z`, `output_sha256`
  `b00710c1ea4aaf595a516898f023354c9525d4c18c7ace8ebf3ce54efbafa51a`, cùng HEAD
  `7bd85e772843ac5ab3c7db656a1b0766aed8ede3`. **Không trích digest này vào tài liệu
  khác như một hằng số** — đối chiếu trực tiếp với `artifacts/pilot-acceptance.json`.
- **Thực tế từng lớp ở lần chạy hiện hành:**
  - `postgres`: **PASS cho đúng 3/28 P1** — `F-42`, `F-49`, `F-53`, chạy thật trên
    PostgreSQL disposable qua `agent/tests/test_case_contention_postgres.py`
    (ánh xạ nodeids: `scripts/ops/run_pilot_acceptance.py:381-396`). **25 P1 còn lại
    UNCLASSIFIED** với gap có tên `no-postgres-proof-mapped-for-finding`
    (`scripts/ops/run_pilot_acceptance.py:1137`).
  - `multi_process`, `browser`, `external_side_effect`: **UNCLASSIFIED cho cả 28 P1** —
    không có host/trình duyệt/sandbox provider trên máy đơn này.
  - `unit`: **cũng UNCLASSIFIED cho cả 28 P1**. Đính chính trong cùng ngày: một lượt
    chạy trước đó **không kết thúc** (`return_code: 124`, `captured_output` kết ở
    `TIMEOUT`) vì drill dùng timeout mặc định 120 giây trong khi bộ cross-boundary đã
    dài quá hai phút. Lỗi đó **đã sửa** (timeout 1800 giây); lượt chạy hiện tại kết thúc
    thật với `return_code: 0` và `95 passed`. Lớp này vẫn `UNCLASSIFIED` vì lý do
    ĐÚNG: một capture gộp không phải bằng chứng riêng cho từng finding, nên
    `_bind_evidence` hạ cấp nó. Hệ quả **không đổi**: **25/28 P1 không có lớp nào PASS**,
    3 P1 còn lại chỉ có đúng một lớp (`postgres`). Không được đọc việc khối này chỉ liệt
    kê ba lớp kia là ngụ ý `unit` đã xanh.
  - Ngoài ma trận acceptance, vẫn **không có bằng chứng** cho: HA/failover,
    backup → offsite → restore → checksum, staging rollout → smoke → rollback,
    alert receiver thật.
- **Lỗ hổng bundle-bía-đặt đã đóng** (lúc ghi khối Task 14 thì chưa): gate parse lại
  `captured_output` khi chấm điểm (`scripts/ops/run_pilot_acceptance.py:138-186`,
  dùng ở `:734-743`); bắt buộc đủ bốn vai ký `runner`/`owner`/`countersign`/`ci`
  (`agent/control_plane/attestation.py:46`, `:257-278`); và có countersigner
  tái-thực-thi độc lập (`scripts/ops/countersign_pilot_acceptance.py`).
- **Countersigner đã chạy: 3/3 confirmed nhưng UNSIGNED.**
  `artifacts/pilot-countersignature.json` ghi `complete=true`, `confirmed=3`,
  `expected=3`, `covers=["F-42/postgres","F-49/postgres","F-53/postgres"]`,
  `attestation.scheme="unsigned"`, `signature=""`. Khóa `PILOT_ATTEST_COUNTERSIGN_KEY`
  **cố ý vắng mặt** theo quyết định của chủ dự án trong phiên 2026-09-02.
- **Kết quả cổng không đổi:** acceptance = **NO_GO**, release verifier = **BLOCKED**.
  Đây là trạng thái đúng. Không khối nào trong tài liệu này được đọc là "đủ điều kiện
  mở closed pilot".
- **Lưu ý custody:** `scripts/ops/run_pilot_acceptance.py`, `artifacts/pilot-acceptance.json`
  và `docs/runbooks/proof-first-pilot-acceptance.md` hiện **UNTRACKED tại HEAD**; khối
  `pilot_acceptance` trong `config/release-authority.json` là diff **chưa commit**.

### Public launch — No-Go hiện tại

Chưa mở index/public acquisition khi còn đồng thời:

- trust coverage thực địa gần như bằng 0; media coverage/credit chưa đo được đáng tin (validator hiện báo 0% vì không nhận local paths);
- legal basis, storage residency, takedown SLA và commerce/premium boundary chưa được chủ/lawyer chốt;
- deploy chưa rollout/rollback thật, monitoring chưa chứng minh alerting, backup chưa qua restore;
- account/report/media erasure chưa phủ mọi sink;
- search/typeahead và catalog pagination còn có thể giấu dữ liệu đúng;
- cache invalidation và export completeness chưa chứng minh correction/erasure tức thời;
- unified search chưa chứng minh không rò trạng thái cá nhân qua shared cache;
- frontend phone/contract journey còn failure trực tiếp;
- design-system authority, typography contract, AdminCP density, state-token consumption và stacking registry chưa có acceptance evidence (F-63–F-68).
- release evidence chưa đáng tin cậy cho tới khi parser full-suite xử lý cả `ERROR` và tài liệu baseline có một authority duy nhất (F-69/F-70).

## 8. Roadmap theo rủi ro

### 0–7 ngày: đóng đường hỏng trực tiếp

- Làm xong phone verification UI + resend/expired/error/success và browser smoke.
- Đồng bộ `reportedValue` contract; thêm test 422/200 và preserve draft.
- Ép `ENVIRONMENT=production`; xoá credential fallback hoặc fail startup.
- Redact raw logger; thêm short prompt-injection corpus và threshold regression.
- Sửa `provisional_count` contract; canonicalize `verifiedAt` nested.
- Sanitize `/api/stats`; thêm public schema test.
- Sửa search ranking/autocomplete, bỏ hard-cap pagination và thêm accent-parity fixture.
- Thiết kế cache-generation/invalidation registry; thêm correction-to-all-consumers test.
- Chốt export inventory, manifest/count/truncation và phân loại secret-vs-content.
- Tách cache public khỏi response search cá nhân hóa; thêm `Vary`/proxy test theo identity.
- Chốt một clock VN/UTC duy nhất; chạy boundary tests cho homepage/feed/chat/MCP.
- Chốt người nhận alert và làm một restore drill từ artifact mới.
- Đóng F-40/F-41: wiring commit một lần, evidence lọc theo scope/thời gian ngay trước ruling; thêm failure injection cho từng bước.
- Đóng F-42/F-49/F-55: lập state-transition table cho scheduled post, moderation/appeal và collection visibility; thêm CAS + worker due test + conflict 409.
- Đóng F-44/F-47: mọi entity/media mutation có actor/reason/before-after; approval image dùng claim/idempotency/compensation và cleanup orphan.
- Chốt F-53: bật idempotency provider nếu có; nếu không, ghi risk acceptance cho at-least-once SMS và metric duplicate.
- Đóng F-69/F-70 trước lần baseline kế tiếp: version hoá harness, phân loại 12 `ERROR`, kiểm return code và đồng bộ `CLAUDE`/`ROADMAP`/`HANDOFF` bằng freshness gate.

### 2–4 tuần: khép lifecycle và release controls

- Một report registry thống nhất; erasure map cho PG/JSONL/log/bot/browser/object/CDN.
- Scheduler cleanup bounded/idempotent; account deletion evidence.
- Tách scheduler thành leader-owned service hoặc áp advisory lease; buộc shared rate-limit ở topology scale.
- Object deletion + CDN invalidation test; đặt TTL/versioning phù hợp.
- Chuẩn hóa backup extension/manifest/checksum/offsite/restore.
- Prometheus target/rules/Alertmanager hoặc notifier free-tier tương đương.
- Migration advisory lock + checksum ledger; pin/hash dependency và SBOM.
- CSP tighten, HTTPS-only egress và browser header tests.
- Sửa F-61/F-62: cooldown backup chỉ ghi sau success; geocode cache dùng shared/file lock liên process và kiểm merge/version trước replace.
- Chuẩn hóa import namespace cho vector store; startup/runtime test chứng minh một singleton và một generation giữa search/semantic cache.
- Đóng F-63/F-65/F-68: canonical token/compatibility allowlist, state/card token consumers và exemption registry + debt budget theo region.
- Đóng F-64/F-66/F-67: thống nhất docs/runtime font, admin density recipe, named drawer layer và fixture cascade/stacking.

### Trước closed pilot

- Staging giống production: PostgreSQL, Redis, object store, Nginx, real TLS, no dev fallback.
- Chạy full acceptance matrix correction/OTP/receipt/review/appeal/public projection.
- Chạy data remediation cho timestamp, duplicate names, orphan, approximate labels và source diversity.
- Có runbook on-call, rollback, restore, account erasure và legal escalation.
- Chạy module boundary matrix: mỗi module phải có ít nhất một test xuyên DB + cache + auth + external side effect, không chỉ route/source guard.

### Trước public launch

- Owner + luật sư/DPO chốt Luật dữ liệu hiện hành, NĐ147/commerce/premium, storage residency, takedown và SLA copy.
- Quyết định media policy cho entity/UGC/avatar/cover; label AI không giả ảnh thật.
- Có coverage `verifiedAt` thực địa theo ngưỡng sản phẩm tự đặt, freshness budget và correction metrics.
- Deploy thật có immutable artifact, migration gate, smoke, rollback; metrics/alerts đã fire thử.
- Owner quyết định tắt noindex sau khi mọi claim public được evidence-backed.

## 9. Phụ lục: lệnh và freshness

### Lệnh đã chạy hoặc đối chiếu

```text
python scripts/deep_audit.py
python scripts/validate_data.py --json
python -m graphify reflect --if-stale
python -m graphify query "correction case identity lifecycle storage deployment monitoring verification public api report moderation" --budget 3500
python -m graphify save-result ... --outcome useful
python scripts/scorecard.py --no-append   # không trả output sau >2 phút, đã dừng
PYTHONPATH=agent python -c "probe search, pagination, homepage single-flight, and UTC/VN boundary"
node web-nuxt/scripts/check-tri-region-color-debt.mjs        # repo root; PASS; targeted ratchet only
# cwd=web-nuxt for the following commands
node scripts/check-tri-region-contrast.mjs                  # PASS; targeted semantic paths
node scripts/check-public-accessibility.mjs                  # exit 1: bundle 811KB > 278KB; tested a11y snapshot had 0 contrast/overflow violations
npx vitest run tests/css-token-treo.test.ts tests/design-authority-contract.test.ts --reporter=verbose
$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; $env:BUILD_SEARCH_INDEXES='false'; $env:BACKGROUND_INDEX_BUILD='false'; $env:SCHEDULER_ENABLED='false'; python -m pytest -q agent/tests/test_account_deletion_transport.py agent/tests/test_erasure_config.py tests/test_release_quality_gates.py --tb=line
@'
import re
sample = '''FAILED tests/test_known.py::test_known
ERROR tests/test_hidden.py::test_hidden
15 failed, 100 passed, 1 error in 2.0s'''
got = set()
for line in sample.splitlines():
    m = re.match(r'FAILED (\S+)', line.strip())
    if m:
        got.add(m.group(1))
print('parser_got=', sorted(got))
print('error_line_present=', any(line.startswith('ERROR ') for line in sample.splitlines()))
print('false_verdict=', 'HET-DIFF' if got == {'tests/test_known.py::test_known'} else 'CO-DIFF')
'@ | python -
git status --short
```

### Design-system check snapshot

- `check-tri-region-color-debt.mjs`: **PASS**; newer public surfaces pass, nhưng catalog/detail còn rawHex `5/25` và legacy-primary `103/103` trong phạm vi script.
- `check-tri-region-contrast.mjs`: **PASS** cho các semantic paths được cấu hình; không thay thế audit toàn bộ state/render.
- `check-public-accessibility.mjs`: **a11y snapshot đạt** trong lần chạy cuối (forced colors active, control đại diện 7/7 bounded, overflow 0, contrast violations 0, LCP 384ms, CLS ~0,0546, INP 0ms) nhưng **exit 1** do bundle gzip 811KB vượt budget 278KB.
- Vitest token/authority: **3 tests passed** (`design-authority-contract` 2, `css-token-treo` 1).
- Systematic-debugging focused suite: **20 tests passed** (erasure transport/config + release quality gates).
- Fresh data checks: `deep_audit.py` **exit 0** (1.746 entities / 12.060 relationships / 33 itineraries; 5 fuzzy duplicate-name groups); `validate_data.py --json` **exit 0** nhưng vẫn ghi 1.406 timestamp inversions, 874 approximate clustered entities, 32 orphans, 150 duplicate source URLs và các warning đã nêu ở mục 3.
- Full-suite verifier: **không được coi `HẾT-DIFF` là xanh**; artifact có 12 `ERROR` chưa có nodeid và harness chưa parse chúng.

### Artifact freshness

- Báo cáo này: **2026-08-31**, evidence tái lập trong branch hiện tại.
- `docs/2026-08-21-danh-gia-toan-du-an.md`: **stale artifact** cách 10 ngày; giữ để truy nguyên, không dùng thay cho kiểm chứng mới.
- `graphify-out/`: artifact người dùng đã có từ trước; không được xem là production snapshot.
- Worktree có thay đổi người dùng cần giữ nguyên: `docs/standards/90-exceptions-log.md` và `graphify-out/`.

### Kết luận cuối

Dự án không thiếu ý tưởng hay thiếu lớp phòng thủ; dự án thiếu **bằng chứng khép kín giữa các lớp**. Ưu tiên không phải thêm feature. Ưu tiên là làm cho một lời hứa duy nhất—“tôi gửi correction, hệ thống xác minh, xử lý, công bố hoặc từ chối có lý do, và xoá được dữ liệu khi cần”—đúng từ browser đến database, log, media, backup, alert và policy. Khi chuỗi đó có test và artifact end-to-end, closed pilot có thể mở; trước thời điểm đó, public launch vẫn là No-Go.
