# Kế hoạch hoàn thiện 10 tầng — vinhlong360

> Lập 2026-06-23 sau đợt quét sâu toàn hệ thống (6 agent đọc song song: trang công khai,
> cộng đồng/UGC, admin CMS, backend core, backend AI/ops, docs/test/cross-cutting).
> Mọi mục có file:line đã được agent **verify trên code thật**, không phỏng đoán.
> Nguồn sự thật của *thứ tự thực thi vĩ mô* vẫn là `docs/ROADMAP.md`; file này là *bản đồ
> hoàn thiện chi tiết* cho từng trang + chức năng, áp khung **10 tầng**.

---

## 0. Khung 10 tầng (áp cho MỌI trang + chức năng)

| Tầng | Tên | Câu hỏi nghiệm thu |
|---|---|---|
| **T1** | Chức năng / đúng-sai | Có chạy đúng không? Bug? Tính năng thiếu? UI chết? Link 404? |
| **T2** | Dữ liệu (§1.4) | Null-safety? Empty/missing xử lý? Không bịa? Không publish dữ liệu chưa kiểm? |
| **T3** | UX/UI (Apple-HIG) | Phân cấp, bố cục, tương tác, nhất quán, phản hồi thao tác? |
| **T4** | A11y (WCAG AA) | Tương phản, bàn phím, ARIA, focus, alt, target ≥44px, thứ tự heading? |
| **T5** | SEO/GEO | title, meta description, canonical, JSON-LD, OG, h1 duy nhất, sitemap? |
| **T6** | Performance/CWV | LCP, CLS, INP, bundle, lazy-load, cache, N+1? |
| **T7** | Bảo mật | authn/authz, validate input, rate-limit, XSS/injection, secret, PII? |
| **T8** | Chịu lỗi | loading/empty/error states, timeout, retry, rollback, degrade? |
| **T9** | Mobile/responsive | breakpoint, overflow, touch, stack? |
| **T10** | Test + observability | test phủ? log/metric/trace? audit trail? |

**Quy tắc nghiệm thu một trang/chức năng = "hoàn thiện 10 tầng"**: pass DoD §5 cho cả 10 tầng.

---

## 1. Bảng điểm hiện trạng (scorecard 0–5, ước lượng từ audit)

| Subsystem | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | T9 | T10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Trang công khai | 4 | 3 | 4 | 3 | 4 | 4 | 4 | 3 | 4 | 2 |
| Cộng đồng/UGC/auth | **2** | 3 | 4 | 3 | 3 | 3 | **2** | 3 | 3 | 3 |
| Admin CMS | 3 | **2** | 4 | 4 | 5 | 4 | 3 | **2** | 3 | **2** |
| Backend core | 4 | 4 | 3 | – | 3 | 3 | **3** | 3 | – | 4 |
| Backend AI/ops | 4 | 4 | – | – | – | 4 | 4 | 3 | – | 4 |
| Data graph (KB) | 3 | 3 | – | – | 3 | 4 | – | – | – | 3 |

Điểm thấp (≤2) = ưu tiên cao nhất: **UGC T1+T7** (link auth vỡ, comment không kiểm duyệt, token plaintext),
**Admin T2+T8+T10** (guard nội-dung chỉ "khuyến cáo", 503 lẫn error, không audit log).

---

## 2. Backlog ưu tiên tổng (đã verify file:line)

### 🔴 P0 — Bug chức năng / lỗ bảo mật / vi phạm bất biến (làm trước)

| ID | Tầng | Vị trí | Vấn đề | Cách sửa |
|---|---|---|---|---|
| **P0-1** | T1 | `lien-he.vue:92` ↔ `dia-diem/[id].vue:504` | Claim flow VỠ: trang liên hệ đọc `?ref=claim`, trang chi tiết phát `?claim={id}` → CTA "đăng ký quản lý cơ sở" không bao giờ mở thẻ claim | Thống nhất 1 param (đề xuất `?ref=claim&entity={id}`); contact page nhận cả 2 |
| **P0-2** | T1/T7 | `cong-dong.vue:103,169`, `bai-viet/[id].vue:36`, `nguoi-dung/[id].vue:30` | `/dang-nhap` và `/cai-dat` **không tồn tại** → toàn bộ phễu logged-out + sửa hồ sơ 404. AuthModal chỉ mở từ topbar | Tạo `useAuthModal()` global (`useState('show-auth')`); thay link bằng mở modal; tạo trang `/cai-dat` (sửa hồ sơ); route-rule redirect `/dang-nhap`→mở modal |
| **P0-3** | T1/T2 | `xa-phuong/[id].vue:110` | `tel:` regex bug: `replace(/\\./g,'')` khớp **backslash** không phải dấu chấm → link gọi khẩn cấp giữ dấu chấm, có máy không quay được | `replace(/[.\s]/g,'')`; gom thành helper `telHref()` |
| **P0-4** | T1 | `users.vue:295` ↔ `admin.py:1166` | Đổi role gửi `body:{role}` nhưng backend nhận `?role=` query → 422, đổi role **âm thầm thất bại** | Sửa client gửi query param; thêm test |
| **P0-5** | T7 | `cai-dat/giao-dien.vue` → `default.vue:200-202,211` | Màu theme (primary/accent/secondary) chèn RAW vào `<style>` toàn site, **không validate hex** → CSS-injection bôi nhọ toàn site | Validate `/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/` trước khi lưu + trước khi inject |
| **P0-6** | T7 | `auth.py:299-301,433` | Session token lưu **plaintext** trong DB + tra cứu bằng giá trị thô → lộ DB = chiếm toàn bộ tài khoản | Hash SHA-256 lúc lưu, tra cứu bằng hash (test-first, §B3) |
| **P0-7** | T2/T7 | `social.py:368`, `init.sql:163` | `create_comment` **không gọi** `moderate_content`, comment default `approved` → mọi bình luận public tức thì (vector spam/abuse, §1.4) | Gọi `moderate_content` cho comment hoặc default `pending`; +test khoá |
| **P0-8** | T7 | `social.py:153,250,311,629` | `phone` (PII) trả raw trong payload post/comment/feed (auth.py đã mask, social.py thì không) | Strip/mask phone trong `_format_post`/`_format_comment` |
| **P0-9** | T2/T7 | `ai.vue:276-319` | `trigger-learn`+`triage` (tốn LLM, §B8) + `reload` (§B7) bắn 1-click **không confirm**; `/health`,`/reload` fetch sai path (origin Nuxt thay vì FastAPI) | Thêm confirm + cảnh báo chi phí; sửa path qua `/admin-api/` |
| **P0-10** | T2/T7/B6 | `entities.vue:147`, `danh-ba.vue:143`, `lich-trinh.vue:282` | Guard nội-dung chỉ là **khuyến cáo**: admin thêm ảnh URL bất kỳ (vi phạm B6), facility nguồn-không-chính-thống vẫn lưu, itinerary stop entityId/tên không kiểm | Enforce cứng: ảnh chỉ nguồn cấp phép, facility bắt buộc nguồn `.gov.vn`, stop phải tham chiếu entity thật |

### 🟠 P1 — Chất lượng / bảo mật phụ / phủ test

| ID | Tầng | Vị trí | Vấn đề | Cách sửa |
|---|---|---|---|---|
| P1-1 | T8 | `ChatWidget.vue:128` | SSE fetch không timeout/abort/cancel → backend treo = input khoá vĩnh viễn | AbortController + timeout + nút Dừng + retry-last |
| P1-2 | T8 | `server.py` (judge `llm_judge.py:401`, vision `image_recognition.py:375`, scheduler `scheduler.py:370`, rerank `contextual_retrieval.py:433`) | Nhiều LLM call **không timeout** | Thêm `timeout=`; đặt `OpenAI(timeout=30)` làm sàn |
| P1-3 | T7/T8 | `llm_judge.py:53` | Hardcode endpoint fallback `https://rnfg39r.abc-tunnel.us/v1` → env thiếu = gọi host lạ/chết | Bỏ fallback, bắt buộc env như `server.py:270` |
| P1-4 | T1/T6 | `du-lich.vue:208`, `san-pham.vue:187`, `ocop.vue:259`, `theo-mua.vue` | `.sort()` mutate mảng reactive thượng nguồn → xáo trộn stats/category | `[...list].sort()` |
| P1-5 | T8 | `danh-ba.vue` (facilities fetch), settings pages | Fetch-fail hiển thị như "không có dữ liệu" (civic page sai lệch); 503 (thiếu Postgres) lẫn với lỗi chung | Track error ref → EmptyState tone=error + retry; shared 503 state |
| P1-6 | T5 | `seo.py:439-443` ↔ `public_api.py:411` | Event JSON-LD đọc `startDate/endDate`, data dùng `date_start/date_end` → event **không có ngày** trong structured data | Đồng bộ tên field |
| P1-7 | T5 | `seo.py:572` | `sitemap.xml` gồm cả entity provisional/chưa-verify (listing đã loại) → crawler index trang site tự ẩn | Lọc `_is_public` trong sitemap |
| P1-8 | T5 | `Breadcrumb.vue` + `su-kien.vue`, `luu-tru.vue` | JSON-LD BreadcrumbList tự-chế mỗi trang → su-kien/luu-tru thiếu; `index.vue:417` `Organization.sameAs:[]` rỗng | Tập trung BreadcrumbList vào component Breadcrumb |
| P1-9 | T7 | `auth.py:352` | Đổi mật khẩu không revoke session cũ; không cap số session/user | Revoke-on-set-password + cap session |
| P1-10 | T6 | `public_api.py:107,372,552` | `/homepage` (endpoint nóng nhất) load TOÀN bộ entity + `db.stats()` (6 COUNT) mỗi request, không cache | Cache homepage 60s |
| P1-11 | T2 | `NotificationBell.vue:62,69` | Dùng nhầm DOM `Notification` global thay vì type app | Import type từ `~/types` |
| P1-12 | T2/T8 | nhiều file (AuthModal, cong-dong, EntityReviews…) | `e.data?.detail` trên `e:unknown` (không `?.` ở `e`) → throw trong catch, nuốt message backend | Helper `getErrorDetail(e)` dùng chung |
| P1-13 | T2 | `tao-lich-trinh.vue:319,337` | Builder 100% localStorage, không sync tài khoản (favorites thì có) → mất plan đa thiết bị | Sync tùy chọn lên tài khoản |
| P1-14 | T4 | `dia-diem/[id].vue` lightbox; `le-hoi`/`su-kien` calendar | Lightbox không focus-trap; calendar `role=grid` thiếu roving-tabindex/arrow nav | Thêm focus-trap; roving tabindex |
| P1-15 | T7 | `site_settings.py:141-171` | `upsert/bulk_upsert` không allow-list/schema → giá trị/shape bất kỳ ghi được (kết hợp P0-5) | Allow-list key + validate shape |
| P1-16 | T10 | `validate_data.py` | Thiếu check: self-loop rel, dangling itinerary-stop, produced_in target-type, place level=None | Thêm các check (DI-005) |
| P1-17 | T10 | `agent/tests/test_chat_smoke.py` | 15+ nhánh `call_tool` + orchestrator error-path chưa test (chat = lõi sản phẩm) | Thêm test TC-02/TC-10 |
| P1-18 | T5/T6 | `nuxt.config.ts:164-166` | Prerender thiếu `/gioi-thieu`, `/chinh-sach-bao-mat`, `/dieu-khoan-su-dung` (SEO-05) | Thêm vào prerender |
| P1-19 | T7 | `auth.py:294,335` | verify-otp/login log `request.client.host` (IP proxy) thay vì `get_client_ip` | Dùng `get_client_ip` |
| P1-20 | T2/T8 | `entities.vue:233`, `lich-trinh.vue:286`, `tinh-nang.vue:86` | `res || []` có thể gán object vào ref mảng; JSON mode không assert array; feature-flag default client ghi đè backend | Assert shape; nguồn flag từ backend |

### 🟡 P2 — Nợ kỹ thuật / vệ sinh

| ID | Tầng | Vị trí | Vấn đề | Cách sửa |
|---|---|---|---|---|
| P2-1 | T3 | builder/list/EntityReviews/UserMenu | `confirm()`/`alert()` native cho thao tác phá hủy | Dialog in-app thống nhất |
| P2-2 | T2/T9 | `cong-dong.vue:305`, profile/comments onMounted | Sidebar stats page-local (sai tổng); follow/comment client-only → flash hydration | Stats từ server; SSR state |
| P2-3 | T2/T3 | `index.vue:326`/`le-hoi`/`theo-mua` | Viết tắt tháng 3 kiểu ("Th{m}"/"Tg {m}"/"Tháng N") | Helper format tháng dùng chung |
| P2-4 | T9 | JourneyBar + scroll-FAB + bookmark-cue | 3 phần tử fixed-bottom chồng nhau mobile | Điều phối stack |
| P2-5 | T7 | `server.py:3074-3089` | Route legacy `/admincp`,`/admin-dashboard` không auth (hiện vô hại do thiếu file) | Xoá |
| P2-6 | T6 | `burn_gpt55.py`,`train.py`,`learn_now.py`,`run_eval.py`, dead imports `eval_framework`,`hybrid_search` | CLI-only/import-thừa = bề mặt thừa | Đánh dấu/dọn |
| P2-7 | T10 | entity/itinerary/settings/user mutation | Không audit log "ai sửa gì khi nào" | Thêm audit trail |
| P2-8 | T7 | `users.vue:92,318`, `bao-cao.vue:83` | Phone đầy đủ trong bảng + CSV export | Giữ mask |
| P2-9 | T6 | `web-nuxt/assets/css` (admin pages nhiều hex) | ~447 hex literal page + 111 component; `base.css` 71KB | Đẩy về token (public trước), prune base.css |
| P2-10 | T10 | `requirements.txt` `>=`, không lockfile | Build không tái lập | `requirements.lock` + commit `package-lock.json` |
| P2-11 | T8/T10 | `middleware.py:98,110`, `autonomous_budget.py:62`, `admin.py:46` | `except: pass` nuốt lỗi vận hành | Log mức warning |
| P2-12 | T6 | `ban-do.vue:170` | Filter bấm trước khi map load → no-op | Re-apply trong `map.on('load')` |

---

## 3. Chi tiết theo subsystem (10 tầng)

### 3.1 Trang công khai (28 trang)
- **Mạnh:** `index.vue` (JSON-LD đầy đủ, LCP preload, fallback degrade), `theo-mua.vue`, `ban-do.vue` (clustering, esc XSS-safe), `danh-ba.vue` (kỷ luật §1.4/Track-H), `dia-diem/[id].vue` (JSON-LD per-type, OG tuyệt đối).
- **T1:** P0-1 (claim), P0-3 (tel regex), P1-4 (sort mutate). **T2:** null-safety nhìn chung tốt; `tim-kiem.vue:153` dùng `any` (nên type). **T4:** P1-14 (lightbox/calendar), ocop hero-creds `aria-hidden` che số liệu thật, region mini-switcher thiếu `aria-pressed`. **T5:** P1-6/7/8 (event dates, sitemap, breadcrumb), clamp meta description dia-diem. **T6:** P1-10 (homepage cache), P2-12 (map filter). **T8:** P1-5 (fetch-fail vs empty). **T2/T3:** P2-3 (month abbr), hero-count vs visible mismatch (theo-mua, tuyến-đường "3 khu vực" hardcode).
- **Hoàn thiện:** link stop tuyến-đường → `/dia-diem/{id}` (internal-link); scroll affordance desktop cho `.scroll-row`.

### 3.2 Cộng đồng / UGC / auth (6 trang + 14 component) — ƯU TIÊN CAO NHẤT
- **T1/T7 (điểm 2):** P0-2 (auth funnel vỡ), P0-7 (comment không kiểm duyệt), P0-8 (PII phone). **T8:** P1-1 (chat SSE abort), P1-12 (error helper). **T2:** P1-11 (Notification type), P1-13 (builder sync). **T7:** P0-6 (session token), P1-9 (session rotation). **T3:** P2-1 (confirm native), P2-2 (hydration flash).
- **Hoàn thiện:** sau P0-2, route mọi toast "Đăng nhập…" (like/bookmark/follow/review hint) → mở AuthModal; cap payload ảnh feed; maxlength/min-length comment khớp server.

### 3.3 Admin CMS (30 trang) — guard + an toàn
- **Tin tốt:** backend auth enforce đúng MỌI route admin (`admin.py:77` `Depends(require_admin)`), fail-closed prod key, constant-time, rate-limit, noindex+robots. **Không có XSS sink** (mdLite escape+whitelist+chặn `javascript:`).
- **T7:** P0-5 (theme CSS-injection), P1-15 (settings allow-list), P2-5 (dead routes), P2-8 (PII). **T1:** P0-4 (role param), P0-9 (confirm cost/path). **T2 (điểm 2):** P0-10 (guard enforce), validate trước save (SEO length, email/phone, area enum). **T8 (điểm 2):** P1-5 (503 state), partial-failure handling, concurrent-edit guard. **T10 (điểm 2):** P2-7 (audit trail), freshness "data as of". **T6:** pagination chua-phan-loai cap 200 (data ẩn), entities/users count per-page.

### 3.4 Backend core
- **Mạnh:** SQL parameterized toàn bộ, ownership-check trên delete, quarantine `_is_public` (§1.4), §B8 gating đúng, body-cap, CORS allowlist.
- **T7:** P0-6 (token), P0-7 (comment mod), P0-8 (phone), P1-9 (session), P1-19 (IP). **T5:** P1-6/7 (event date, sitemap), sitemap-index dead refs. **T6:** P1-10 (homepage cache), connection-per-request (chấp nhận <10k). **T8:** P1-2 (timeouts), P2-11 (except pass). **T2:** `server.py:270` `os.environ["LLM_API_KEY"]` crash import (route qua `settings`).

### 3.5 Backend AI/ops
- **Tin tốt lớn:** **không có ungated autonomous LLM** — scheduler ON nhưng 7 task tốn-tiền OFF mặc định (`AUTONOMOUS_TASKS_ENABLED=false`); `autonomous-agent` self-gate qua `autonomous_budget` (opt-in+cap+kill-switch) ĐÚNG §B8. Per-request chỉ main loop tốn LLM (timeout 30s + circuit breaker). judge/vision off/admin-gated.
- **T8:** P1-2 (timeouts judge/vision/scheduler/rerank), P1-3 (hardcode endpoint). **T6:** P2-6 (dead-code candidates: burn_gpt55/train/learn_now/run_eval CLI-only; dead imports). **T10:** observability tốt (cost_tracker, metrics, tracing).

### 3.6 Cross-cutting (data / test / design-system / CWV / ops)
- **Data graph (còn nợ, giới hạn nguồn ngoài):** GS-07 (`p-long-chau` catch-all 209 entity), GS-11 (29 ward rỗng — gap nội dung), ~644 coords approximate, ~199 placeId=None (CỐ Ý §1.4), edge near/associated_with sai ngữ nghĩa, 128 produced_in→craft_village. **Cần geocode trả phí / dữ liệu B2G** → phần lớn Track-H.
- **Test:** breadth tốt (~72 file, ~1214 pass); blind-spot còn: P1-17 (call_tool/orchestrator), comment-moderation test (P0-7 đi kèm), optimize_data/crawler 0%.
- **Design-system:** token 3-tầng mạch lạc (variables.css), nợ = hex literal (admin nặng), prune base.css.
- **i18n:** vắng — Việt-only theo thiết kế (đúng scope, không cần i18n).
- **CWV/build:** SSR+SWR+prerender cấu hình; maplibre lazy; **HELD**: prerender ~1700 trang chi tiết (10.1, cần backend-at-build), verify `NODE_OPTIONS` heap trong deploy.sh, Lighthouse "Good" chưa verify (DoD-10).
- **CI:** 8 job; typecheck (~642 lỗi vue-tsc)/CVE/coverage đang `continue-on-error` → chưa thành cổng chặn.

---

## 4. Lộ trình thực thi (đợt nhỏ, mỗi đợt để hệ thống xanh — §B5)

> Mỗi đợt: làm → `pytest -q` xanh + `validate_data` exit 0 + build FE → commit nhỏ → deploy (deploy.sh đã hardened: timeout + health-gate `:8360`). Module blind-spot (auth/social/database/chat): **test trước khi sửa** (§B3).

| Đợt | Nội dung | Items | Verify |
|---|---|---|---|
| **A — P0 chức năng FE** | claim flow, auth funnel + `/cai-dat` + global open-auth, tel regex, role param, ai.vue confirm/path | P0-1,2,3,4,9 | click-test từng luồng + role-change 200 |
| **B — P0 bảo mật BE** (test-first) | hash session token, comment moderation, mask phone PII | P0-6,7,8 | +test khoá; `pytest test_writepaths_*` |
| **C — P0 toàn-vẹn nội-dung** (§B6/§1.4) | enforce ảnh nguồn-cấp-phép, facility nguồn `.gov.vn`, itinerary stop FK; theme hex validate | P0-5,10 | thử submit dữ liệu xấu → bị chặn |
| **D — P1 chịu lỗi** | LLM/DDGS timeout + os.environ guard, ChatWidget abort, 503 state, sort-clone, fetch-error vs empty, error helper | P1-1,2,3,4,5,12 | chat hang→dừng được; settings thiếu PG→state rõ |
| **E — P1 SEO/data** | event JSON-LD date, sitemap `_is_public`, BreadcrumbList tập trung, prerender legal, validate_data checks, NotificationBell type | P1-6,7,8,11,16,18 | Rich Results test; validate exit 0 |
| **F — P1 perf + auth** | homepage cache 60s, session rotation/cap, IP fix, shape-assert | P1-9,10,19,20 | thời gian /homepage; đổi mật khẩu→session cũ chết |
| **G — P1 phủ test** | call_tool/orchestrator test, builder account-sync, lightbox/calendar a11y | P1-13,14,17 | coverage tăng; keyboard nav |
| **H — P2 vệ sinh** | confirm in-app, hydration SSR, month helper, dead routes/code, audit log, hex→token, deps lock, except-pass log | P2-* | build xanh; review |
| **Track-H (cần người)** | NĐ147 (H1), luật sư (H2), **GĐ8 ảnh** (R2/Wikimedia/WebP/upload/SEO ảnh — khối code lớn nhất chưa xây), monitoring accounts (GĐ9), domain/deploy public | ROADMAP H1-H5 + GĐ8/9 | — |

**Thứ tự khuyến nghị:** A → B → C (xong P0 = hết bug/lỗ nghiêm trọng) → D → E → F → G → H.
GĐ8 (ảnh) chạy song song bởi người duyệt từng bước (không tự deploy public).

---

## 5. DoD cho từng tầng (cổng nghiệm thu mỗi trang/chức năng)

- **T1:** mọi nút/link hoạt động, 0 link 404 nội bộ, tính năng nêu ở UI đều chạy.
- **T2:** mọi truy cập API có null-safety; empty/missing có nhánh riêng; **không field bịa**; nghi ngờ → ẩn/None.
- **T3:** phân cấp rõ, phản hồi mọi thao tác (loading→success/error), nhất quán với design-system.
- **T4:** keyboard đủ, focus thấy + bẫy trong modal, ARIA đúng, tương phản ≥4.5:1, target ≥44px.
- **T5:** title + meta ≤155c + canonical + JSON-LD hợp lệ (Rich Results pass) + h1 duy nhất; trang index-able trong sitemap, trang nội bộ noindex.
- **T6:** LCP <2.5s, CLS <0.1, không N+1 nóng, ảnh lazy + NuxtImg, route-CSS tách.
- **T7:** mọi endpoint mutate có authz; input validate; rate-limit; 0 XSS/injection; PII mask; secret không lộ.
- **T8:** có loading/empty/error states phân biệt; external-call có timeout + retry/abort; rollback optimistic.
- **T9:** không overflow ngang, target chạm đủ, layout 1-cột mobile, fixed-element không chồng.
- **T10:** test phủ nhánh chính; log lỗi không nuốt; thao tác admin có audit; có metric/trace.

---

## 6. KHÔNG làm (đã verify — đừng tốn công)

- §B8 autonomous LLM: gating đúng, **không** nới (CLAUDE.md §B8).
- XSS qua `v-html`: mdLite an toàn; UGC render `{{ }}`. Không có sink.
- Backend admin auth: enforce đúng mọi route, fail-closed prod. Không "thêm guard FE thay BE".
- Viết content cho ~200 POI thương mại (siêu thị/chợ/nhà hàng): §1.4 cấm bịa → để trống đúng-bài.
- i18n: không cần (Việt-only theo scope).
- Data graph "còn nợ" (coords approximate, placeId=None, ward rỗng): giới hạn nguồn ngoài → Track-H, **không đoán bừa**.
- N+1 in-memory KB: O(1) microsec, không phải vấn đề.
- Pool PG (D02): giữ OFF mặc định (đã gây incident treo prod 2026-06-22).

---

## 7. Liên kết
`docs/ROADMAP.md` (thứ tự vĩ mô + Track-H) · `docs/audit-findings-20260622.md` (110 finding gốc) ·
`docs/architecture-decisions.md` · `docs/stabilization-plan.md` · `docs/design-system-plan.md`.
