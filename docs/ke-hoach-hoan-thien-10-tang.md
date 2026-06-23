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

---

# PHẦN II — ĐÀO SÂU (Wave 2: verify + định lượng + line-level)

> 6 agent đào sâu: adversarial-verify P0, map data-contract FE↔BE, định lượng KB, exhaustive 10-tầng top-5 trang, CWV/bundle, pipeline chat. Mọi verdict đọc code thật.

## II.0 Verdict các P0 Phần I (adversarial verify)

| P0 cũ | Verdict | Ghi chú |
|---|---|---|
| P0-1 claim flow | ✅ CONFIRMED | footer dùng `?ref=claim` đúng → chỉ CTA chi tiết vỡ |
| P0-2 `/dang-nhap`+`/cai-dat` 404 | ✅ CONFIRMED | High — link sống trên trang đã ship |
| P0-3 tel regex | ✅ CONFIRMED | `/\\./g` khớp backslash |
| P0-4 role param 422 | ✅ CONFIRMED | đổi role luôn fail |
| P0-5 theme CSS-injection | 🟡 NUANCED → P1 | admin-gated, defacement (không script-exec); radius/font_scale ĐÃ validate, chỉ 3 màu chưa |
| P0-6 session token plaintext | ✅ CONFIRMED | High |
| P0-7 comment bỏ kiểm duyệt | ✅ CONFIRMED | + moderation cũng "approve" khi thiếu API key → lỗ kép |
| P0-8 phone PII | ✅ CONFIRMED (post) | `_format_comment` KHÔNG lộ — claim hơi quá ở comment |
| P0-9 ai.vue confirm/path | 🟡 PARTIAL → P2 | **path ĐÚNG** (nuxt proxy map chuẩn); chỉ thiếu confirm (low-risk) |
| P0-10 guard nội-dung | 🟡 MIXED → P1 | ảnh shape/count + assign_place ĐÃ validate; gap thật = itinerary stop FK + source free-form |

## II.1 P0 MỚI (Wave 2 phát hiện — đều verified)

| ID | Tầng | Vị trí | Vấn đề |
|---|---|---|---|
| **P0-11** | T1/T2 | `nguoi-dung/[id].vue:162-176` ↔ `social.py:520` | **Profile user VỠ HOÀN TOÀN**: FE đọc flat `profile.display_name/phone/post_count/avatar`, BE nest `{user:{display_name,avatar_url,bio,stats:{posts,reviews}}}` → mọi field undefined, profile trống |
| **P0-12** | T7 | `server.py:3058` | **Tạo dynamic-agent KHÔNG auth** → ai cũng inject system_prompt + tool_whitelist vào pool agent chat (prompt-injection / đốt LLM budget) |
| **P0-13** | T7 | `admin.py:664` | **SSRF**: `approve_image_suggestion` `httpx.get(url, follow_redirects=True)` không allowlist host → fetch `169.254.169.254`/nội bộ (admin-gated nhưng là SSRF primitive thật) |
| **P0-14** | T1/T7 | `notifications.py:41` ↔ `init.sql:233`; `admin.py:978` ↔ `init.sql:236` | **2 lỗi DB CHECK→500**: report `target_type='entity'` không có trong CHECK; `resolve_report` set `status='resolved'` không có trong CHECK |
| **P0-15** | T7 | `auth.py:319` | **`/auth/login` KHÔNG rate-limit** → brute-force mật khẩu (OTP thì có limit) |
| **P0-16** | T7 | `dia-diem/[id].vue:257` | `entity.attributes.website` → `href` **không allowlist scheme** → `javascript:` URI XSS |
| **P0-17** | T7 | `xa-phuong:259`, `tao-lich-trinh:429`, map detail | **HTML injection map popup**: tên entity/place/stop nhét raw vào `setHTML` (lặp 3 chỗ → 1 helper `escapeHtml` sửa hết) |
| **P0-18** | T1 | `cong-dong.vue:434` | Tab bookmark đọc `res.posts` nhưng BE trả `{bookmarks}` → **bookmark luôn rỗng** |
| **P0-19** | T1/T2 | `tao-lich-trinh.vue:247` | `FavoriteItem` không có `coordinates` → stop từ mục đã-lưu **không route/map được** |
| **P0-20** | T1 | `server.py` (public_api ↔ notifications) | **`/api/report` route đụng nhau** (public_api thắng, notifications.py thành dead) — reorder router = đổi hành vi âm thầm |

**Refuted (KHÔNG sửa):** UGC IDOR (ownership-check đủ ở delete/saved/notif), produced_in→craft_village (resolve transitively), 29-ward-rỗng (thực chất **5** + 38 business mis-type `place` là defect KHÁC).

## II.2 Data-contract FE↔BE (mismatch)

- **P0-11** profile (trên). **P0-20** report collision (trên).
- **P1:** comment đọc `c.display_name`/`c.phone` nhưng BE chỉ trả `author.display_name` (`social.py:646`) → tên comment trống. `/api/me/bookmarks` key (P0-18).
- **Error envelope 4 kiểu** (`{detail}` / `{error}` JSONResponse / `{error}` HTTP-200 ở `seo.py:461,527` / in-band `error` field FE khai mà BE không trả) — FE chỉ parse `detail` → 404 `{error:"not_found"}` mất message. **→ chuẩn hoá 1 envelope `{detail}` + HTTPException.**
- **Pagination 4 kiểu** (`{posts,page,total,has_more}` / `{total,entities}` / `{total,limit,offset}` / `{posts}` trống) → `users/{id}/posts` + `bookmarks` không có tín hiệu hết-trang. **→ chuẩn `{items,total,page,limit,has_more}`.**
- **P2:** `/api/search` `results` orphan (FE dùng `/api/entities?q=`), facility `source` shape (list/str/dict) FE giả định dict, SEO event-date key drift (`startDate` vs `date_start`).

## II.3 KB data-graph (định lượng — số thật từ data.json)

**Sạch (0 defect):** self-loop 0, dangling 0, near>50km 0, bbox-violation 0, itinerary-stop refs 0 (11 free-text §1.4), produced_in transitively-located.
**Số liệu:** 1779 entity / 9303 rel / 33 itinerary. Coords 1625/1779 (91%); **643 coords_approximate**, 154 coordless. Summary: 5 rỗng, 336 <120c, 1275 chuẩn, 163 >400c. Source: **868 có URL thật, 911 chỉ placeholder**.

**Fixable in-repo (KHÔNG cần dịch vụ trả phí):**
| Việc | Số | Tầng |
|---|---|---|
| Gộp dup coord-matched (9 nhóm chắc + ~26 review) | 9–52 | T2 |
| Re-type business gắn nhầm `type=place` (Agribank/bến xe/chợ/nhà hàng…) | 38 | T2 |
| Tách bớt catch-all `p-long-chau` (re-assign ward suy từ address/coords có sẵn) | 247 | T2 |
| Viết content 5 ward rỗng (an-ngai-trung, hieu-phung, my-thuan, quoi-an, song-phu) + 5 summary rỗng | 10 | T2 |
| Bỏ field `description` chết (rỗng ×1779) hoặc tái dụng | 1779 | T1 |

**Track-H (cần nguồn ngoài — KHÔNG đoán §1.4):** coords thật cho 154 coordless + hạ-cấp 643 approximate (cần geocode), ward thật cho phần dư p-long-chau địa-chỉ-mơ-hồ, citation cho 911 placeholder-source (research).

## II.4 CWV / Performance (backlog có số)

**P0:** (1) **Cache `/homepage`** — mỗi request scan toàn bảng entity + score + 6×COUNT (`public_api.py:367,485`), TTFB nặng trên VPS 1CPU → cache TTL 60-300s theo tháng. (2) **Prerender ~1700 trang chi tiết** — hiện SWR-only + `crawlLinks:false` (`nuxt.config.ts:98,167`) → cold-SSR mỗi cửa-sổ revalidate; feed route-list từ data.json hoặc warm-crawl sau deploy. (3) **Hero + cover → WebP/NuxtImg** — hero.jpg **217KB raw** (CSS bg, bypass weserv), cover detail raw `<img>` (`[id].vue:18`) → ↓55-65% payload LCP.
**P1:** tách `catalog.css` (40KB) khỏi global; reserve height ClientOnly islands + beta-banner (CLS); **gỡ `@nuxt/fonts`** (0 `@font-face` emit, Inter nằm sau system-font → module chết); set `--max-old-space-size` vào `package.json` (hiện chỉ ở `deploy.sh:69`).
**P2:** prune `base.css` 72.7KB (test-first §B3); WebP cho `/img/cat/*.jpg`.
**Tốt rồi (giữ):** maplibre lazy-split (1.05MB chỉ load trang map), detail.css/events.css per-route, EntityCard NuxtImg, hero min-height (CLS guard), maplibre `optimizeDeps.exclude`.

## II.5 Chat/AI pipeline (T8 + T10)

**Resilience gaps:** (1) **stream path** không circuit-breaker/retry/KB-fallback (kém hơn `/chat`). (2) `weather`/`web_search` không breaker (breaker **định nghĩa nhưng chết** `circuit_breaker.py:399,407`); `weather` còn không timeout. (3) **guardrail fail-OPEN** (`except: pass` → input không kiểm, `server.py:1522,1896`). (4) tool args `args["x"]` → KeyError nếu LLM thiếu field (8 chỗ). (5) **`blocked_reason` lộ ra user** (chuỗi chẩn-đoán injection). (6) cost = ước-lượng, không đọc `usage` thật.
**Correctness P0:** **`_is_error_reply` false-positive** (`server.py:1627`) — reply hợp lệ chứa "lỗi"/"sự cố" trong 60 ký tự đầu → **bị KB-fallback ghi đè** = trả "Hệ thống AI đang bảo trì" cho câu trả lời đúng.
**Test matrix cần (lõi sản phẩm, chỉ smoke-test):** TC-02 (14 nhánh `call_tool`: search/entity_detail/seasonal/itinerary/compare/nearby/web_search-timeout/weather/followups/ocop/accommodation/community/unknown/malformed-args) + TC-10 (13 path orchestrator: specialist-fail→general, round-exhaustion synthesis, safe_llm_call fail, cap, empty-search hint, **_is_error_reply false-positive**, KB-fallback hit/abstain, guardrail-block-safe, fail-open, stream-error, circuit-open). Chi tiết trong báo cáo agent.

## II.6 Checklist exhaustive per-page (top-5) — tóm tắt P0

- **index.vue:** JSON-LD `addressRegion` dùng slug thay tên (`:374`); stats-bar render khi rỗng (`:47`); recentSaved `<img>` thiếu `@error`. Type `homeData` (`Record<unknown>`).
- **dia-diem/[id].vue:** website href no-allowlist (P0-16); **SEO/meta + 404 KHÔNG cập nhật khi đổi param client** (`:672,:383` non-reactive); lightbox thiếu focus-trap; dead `qualityMissingLabels`.
- **xa-phuong/[id].vue:** tel regex (P0-3); `hasStats` ẩn cả "số địa điểm" khi thiếu area/population (`:168`); map popup injection (P0-17).
- **cong-dong.vue:** bookmark key (P0-18); chip↔textarea dual-bind `reportReason`; ảnh base64 ~tới 67MB POST (no downscale); `onScroll` no throttle.
- **tao-lich-trinh.vue:** favorites coords undefined (P0-19); map `'load'` race (`:406`); popup injection (P0-17); nested `<button>` trong `role=button`; `:key` chứa idx → remount input khi reorder.
**Xuyên suốt:** thiếu **analytics trên mọi conversion** (tap phone/Zalo/map/directory, save/share plan, post/report) — gap T10 lớn nhất của site showcase. Typing drift (tsconfig loose). Meta non-reactive ở detail (chuẩn hoá form `() =>`).

## II.7 Master priority cập nhật (sau verify)

**P0 (20 mục):** P0-1..4, 6, 7, 8, 11..20 (đã loại/giảm 5→P1, 9→P2, 10→P1 split). Thêm perf-P0 (homepage cache, prerender detail, hero/cover WebP) + chat-P0 (`_is_error_reply`).
**Lộ trình cập nhật (chèn vào §4):**
- **Đợt A (P0 FE bug):** +P0-11 profile, P0-18 bookmark, P0-19 builder-coords, P0-16 website-href, P0-17 map-escape (helper dùng chung).
- **Đợt B (P0 bảo mật BE):** +P0-12 dynamic-agent auth, P0-13 SSRF allowlist, P0-14 DB CHECK (2), P0-15 login rate-limit (cùng session token + comment mod + phone PII).
- **Đợt B2 (data-contract):** P0-20 report collision, comment author field, chuẩn error-envelope + pagination.
- **Đợt D (resilience):** + chat: stream breaker/retry, wire weather/web_search breaker + timeout, guardrail fail-CLOSED + ẩn blocked_reason, `_is_error_reply` siết, tool-arg `.get` guard; +TC-02/TC-10 test.
- **Đợt E2 (perf):** homepage cache, prerender detail pages, hero/cover WebP, tách catalog.css, gỡ @nuxt/fonts.
- **Đợt C2 (data-graph in-repo):** gộp 9 dup, re-type 38 business, tách p-long-chau, 5 ward + 5 summary rỗng.

---

## 7. Liên kết
`docs/ROADMAP.md` (thứ tự vĩ mô + Track-H) · `docs/audit-findings-20260622.md` (110 finding gốc) ·
`docs/architecture-decisions.md` · `docs/stabilization-plan.md` · `docs/design-system-plan.md`.
