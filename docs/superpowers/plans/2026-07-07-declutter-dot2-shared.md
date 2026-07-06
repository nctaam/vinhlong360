# Declutter Đợt 2 — Hệ thống dùng chung: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Chuẩn hoá/cắt các hệ thống dùng chung (Tầng A spec + B4) trên nhánh `feat/declutter-dot2`: ledger filter-aware, 1-đường-filter-khu-vực, cross-links 4→3 script-driven, rail policy, tim-kiem Row E, ChatWidget conditional, footer 7→4, interstitial inline policy.

**Architecture:** 8 task thứ tự rủi-ro tăng dần; mỗi task 1-2 commit; anchor-string (không line-number); additive-first cho thay đổi cấu trúc; grounded bởi workflow 9-agent (2026-07-07) với 9 hiệu chỉnh spec (bảng ⚠️ AUDIT dưới).

**Tech Stack:** Nuxt 4 SSR (`web-nuxt/`), Vue SFC, CSS tokens; 1 file backend (`agent/seed_site_settings.py` — Task 7).

**Trạng thái:** ĐANG THỰC THI inline (executing-plans), dev server port 3000.

---

## Chi tiết task (grounded — anchor đã xác nhận trên code hiện tại)

> Spec gốc: `docs/superpowers/specs/2026-07-06-ui-declutter-design.md` (§2 Tầng A, §5 Đợt 2). Nhánh: `feat/declutter-dot2` (= main sau Đợt 1, 12 commit `3939aef..9f49c13`). Mọi anchor dưới đây **đã grep/đọc trên code hiện tại** — line-number trong spec đã lệch, dùng anchor-string làm chuẩn.

## Ràng buộc toàn cục (kế thừa Đợt 1)

- **Bất khả xâm phạm:** byline `.entity-byline`; trust-card + "Báo sai hoặc bổ sung nguồn"; nhãn "AI gợi ý" + disclaimer (gồm `chat-disclaimer` trong ChatWidget); nhãn honesty; motif phù-sa (tick/stratum/`sediment-head`/sediment-divider — chú ý các section sắp cắt có chứa `sediment-head`: chỉ cắt *instance trong khối bị bỏ*, không đụng pattern); pháp lý; breadcrumb; skip-link; SaveButton/Share; EmptyState illustration; **lunar-ribbon su-kien + lunar-label le-hoi** (signature âm lịch).
- **Giao thức verify V** (như Đợt 1): dev server port 3000, fetch SSR bằng `PYTHONIOENCODING=utf-8 python -c "import urllib.request as u;print(u.urlopen('http://localhost:3000/<path>').read().decode('utf-8'))"` + grep anchor cắt-mất/giữ-còn. Lưu ý bài học Đợt 1: `/` có SWR — phải cache-bust; **phần tử trong `<ClientOnly>` KHÔNG có trong SSR HTML** (ChatWidget, SmartRecommendations) → verify bằng `preview_eval`/đọc source.
- Xoá template ⇒ grep class/computed/import mồ côi, dọn trong **cùng commit**. Commit: `refactor(declutter-2): <phạm vi> — <việc> (<lý do>)`.
- FE vitest harness hỏng (đã biết) — smoke.test.ts là source-string test; vẫn phải sửa cho nhất quán khi cắt UI mà test đang assert (xem T4).

## ⚠️ AUDIT: chỗ SPEC SAI / ĐÃ LỖI THỜI so với code hiện tại

| # | Spec nói | Code thật (đã grep) | Hệ quả |
|---|---|---|---|
| S1 | A1: "4 card **giống hệt nhau** ở cuối mỗi trang" | 4 trang catalog có 4 **bộ card khác nhau** (`du-lich.vue:188-203` = san-pham/lich-trinh/ban-do/luu-tru; `san-pham.vue:166-181` = ocop/theo-mua/du-lich/am-thuc; `ocop.vue:225-240`; `luu-tru.vue:147-162`). `.cross-links` còn ở **13 trang**, A1 chỉ scope 4 | Việc thật = trim 4→3 + bỏ card trùng-đích-trên-trang, không phải khử "giống hệt" |
| S2 | A4b: bỏ section "Trợ lý AI" homepage | **ĐÃ LÀM Đợt 1** (commit `691e694`) | A4 chỉ còn FAB-conditional |
| S3 | A5 liệt kê `danh-ba.vue:31-49` | Quick-picks danh-bạ bind `selectedArea` lọc optgroup của select — là **đường filter khu vực DUY NHẤT** trên trang (không có FilterChips nào trùng) | **NO-OP** — không cắt, fail duplication-test |
| S4 | B3/A6: ledger su-kien "bỏ place_name line 95 + **lunar detail**" | `place_name` đúng còn ở `su-kien.vue:95` (**user hỏi — xác nhận CHƯA trim**). Nhưng row ledger su-kien **không có lunar detail nào** (lunar-ribbon ở hero là signature; `lunar-label` chỉ ở `le-hoi.vue:86` — ý nghĩa lễ âm lịch, GIỮ) | Chỉ bỏ `ledger-place`; phần "lunar detail" là spec ảo |
| S5 | B4: zero-result "bỏ lớp lồng trùng với lớp khi-có-kết-quả (81-91)" | **Đã không còn trùng**: `searchNextActions` trả `[]` khi 0 kết quả (`tim-kiem.vue:305`), 2 SmartRecommendations nằm 2 nhánh loại trừ (81 vs 101) | Dedupe = NO-OP; chỉ còn việc tuỳ chọn gộp 2 instance rail thành 1 (chuẩn-hoá) |
| S6 | A3b: sửa footer cột "Khám phá" tại `layouts/default.vue` | `footer.columns` là **key CMS seeded** (`agent/seed_site_settings.py:93-120`) — DB override `DEFAULT_FOOTER_COLUMNS` (`layouts/default.vue:161-189`); giá trị seed đã **khác** default FE ("3 vùng" + emoji vs "Khu vực") | Sửa default FE không đủ nếu DB đã seed → phải sửa cả seed + cập nhật DB; prod = việc vận hành lúc deploy (ngoài phạm vi commit) |
| S7 | A7: "Verify `useJourneyActions()` trước khi bỏ instance tai-khoan" | `smoke.test.ts:81-82` assert tai-khoan.vue chứa `userCpJourneyActions` + `JourneyActionRail`; `:455` assert composable chứa `userCpJourneyActions`; builder này **chỉ** tai-khoan dùng | Bỏ rail ⇒ phải xoá builder mồ côi + sửa 3 assertion cùng commit (test mã hoá UI cũ bị spec duyệt bỏ — không phải "sửa cho xanh" vô cớ) |
| S8 | A2 điểm gọi `san-pham.vue:81-86`, `du-lich.vue:81`… | Line lệch: san-pham `:63-68`, du-lich `:81-86` (đúng), tổng **11 call site** (thêm tuyen-duong:66, theo-mua:145, dia-diem/index:77, khu-vuc/[area]:38, le-hoi:133, su-kien:104, lich-trinh:110, ocop:119, luu-tru:85) | Dùng anchor `<CatalogInterstitial` |
| S9 | Line spec A5/A6/A7 nói chung | Đa số lệch nhẹ: le-hoi FilterChips khu vực `:181-187` (khớp!), su-kien `:159-165` (khớp), lich-trinh quick-picks `:83-100`, ocop region-picks `:96-116`, ledger le-hoi `:66-92` + computed `upcoming` `:373-382`, su-kien `upcoming` `:342-351`, tai-khoan rail `:45-52` (khớp), da-luu rail `:37-43` (khớp), tim-kiem Row E `:168-181` (spec nói 155-181) | Anchor trong task dưới là số ĐÃ xác nhận hôm nay |

---

## Task 1 — A6: Ledger sự kiện filter-aware + trim `place_name` su-kien

*Rủi ro: THẤP (computed thuần + 1 dòng template). Không phụ thuộc task nào.*

**Files:** `web-nuxt/pages/le-hoi.vue`, `web-nuxt/pages/su-kien.vue`

**Steps (anchor-based):**
1. `le-hoi.vue:373-382` — computed `const upcoming` hiện chỉ lọc `ds >= now`. Thêm lọc theo `areaFilter` (dùng `getArea(e)`) và `statusFilter` (dùng `eventStatus(e)`) **trước** `.slice(0, 6)`. Hành vi khi cả hai = `'all'` phải **y hệt cũ** (guard hành vi phần giữ lại).
2. `su-kien.vue:342-351` — computed `upcoming` tương tự (lọc thêm `areaFilter`/`statusFilter`, giữ sort + slice).
3. `su-kien.vue:95` — xoá dòng `<span v-if="e.place_name" class="ledger-place">📍 {{ e.place_name }}</span>`. **KHÔNG** đụng `le-hoi.vue:85-86` (`ledger-place` + `lunar-label` của lễ hội — xem S4; nếu muốn đồng bộ cả le-hoi thì phải hỏi lại chủ dự án, spec chỉ duyệt su-kien). Grep `.ledger-place` trong CSS: nếu chỉ còn le-hoi dùng → GIỮ CSS.
4. Kiểm `v-else-if` off-season của le-hoi (`:95-103`): khi filter làm `upcoming.length === 0` nhưng `allEvents.length > 0`, nhánh off-season sẽ hiện — chấp nhận được (thông điệp vẫn đúng) hay cần thêm điều kiện? Quyết tại thực thi, ghi vào commit.

**Verify:** SSR `/su-kien`: `ledger-place` = 0, `ical-bulk-btn` ≥ 1; SSR `/le-hoi`: `ledger-place` ≥ 1 (giữ). Client (preview_click): bấm quick-pick "Bến Tre" trên /le-hoi → hàng ledger thay đổi theo (snapshot đếm `ledger-row` trước/sau); bỏ chọn → về như cũ.

**Commit:** `refactor(declutter-2): le-hoi+su-kien — ledger filter-aware (hết list động/ledger tĩnh) + su-kien bỏ place_name ledger`

---

## Task 2 — A5: Quy tắc "1 đường filter khu vực / trang" (le-hoi, su-kien, lich-trinh, ocop)

*Rủi ro: THẤP-VỪA (cắt UI bind chung ref — logic filter giữ nguyên). Làm sau Task 1 vì đụng cùng file.*

**Files:** `web-nuxt/pages/le-hoi.vue`, `web-nuxt/pages/su-kien.vue`, `web-nuxt/pages/lich-trinh/index.vue`, `web-nuxt/pages/ocop.vue` (+ CSS mồ côi nếu có)

**Steps:**
1. **le-hoi** — xoá block `<FilterChips ... aria-label="Lọc theo khu vực">` (`le-hoi.vue:181-187`); GIỮ quick-picks blob (`:113-130`, bind cùng `areaFilter`) + GIỮ FilterChips trạng thái (`:174-180`). Grep `areaFilterOptions` trong file — nếu chỉ FilterChips này dùng → xoá computed (le-hoi `~:355-367`).
2. **su-kien** — tương tự: xoá `su-kien.vue:159-165` (FilterChips khu vực); giữ quick-picks (`:115-132`) + `areaFilterOptions` orphan-check (`~:330-336`).
3. **lich-trinh (NGƯỢC)** — xoá section quick-picks "Chọn theo khu vực" (`lich-trinh/index.vue:83-100`); GIỮ `chip-row` khu vực trong controls (`:128-136`). Orphan-check: `countByArea` (`:~97` chỉ quick-picks dùng?) — grep rồi xoá nếu mồ côi. `AREA_META` vẫn dùng ở chip-row — GIỮ.
4. **ocop** — xoá section `region-picks-subordinate` (`ocop.vue:96-116`); GIỮ FilterChips "Khu vực" trong controls (`:166-173` — trang này controls là nhà của 3 tầng filter sao/khu vực/tháng). Orphan-check: `REGION_TAGLINE`, `countByArea`, CSS `region-quick-picks`/`region-pick`/`region-tagline`/`region-picks-subordinate` (grep cả `assets/css/` — `region-quick-picks` còn ở `danh-ba.vue:36` → class dùng chung, chỉ xoá rule riêng nếu có).
5. **danh-ba: NO-OP** (S3) — ghi vào plan-result, không sửa.
6. Kiểm `useFilterUrl` (`le-hoi.vue:322` — param `vung`) vẫn hoạt động: vào `/le-hoi?vung=ben-tre` → quick-pick Bến Tre active + grid đã lọc.

**Verify:** SSR từng trang: le-hoi/su-kien — `aria-label="Lọc theo khu vực"` = 0, `quick-picks` ≥ 1, `aria-label="Lọc theo trạng thái"` ≥ 1; lich-trinh — `Chọn theo khu vực` = 0, `chip-row` ≥ 1; ocop — `region-picks-subordinate` = 0, `aria-label="Lọc theo khu vực"` ≥ 1. URL-param test như step 6.

**Commit:** 2 commit — `refactor(declutter-2): le-hoi+su-kien — 1 đường filter khu vực (giữ quick-picks, bỏ chips trùng)` và `refactor(declutter-2): lich-trinh+ocop — 1 đường filter khu vực (giữ chips controls, bỏ quick-picks/region-picks trùng)`

---

## Task 3 — A1: Cross-links 4 trang catalog → 3 card từ mảng script (bỏ hardcode template)

*Rủi ro: VỪA (đổi cấu trúc template 4 trang; additive-first).*

**Files:** `web-nuxt/pages/du-lich.vue:184-205`, `web-nuxt/pages/san-pham.vue:162-183`, `web-nuxt/pages/ocop.vue:221-242`, `web-nuxt/pages/luu-tru.vue:143-164`

**Steps:**
1. Mỗi trang: chuyển 4 `<NuxtLink class="cross-card">` hardcode thành `const relatedCatalogs = [...]` trong script + `v-for` render (giữ nguyên markup card, giữ emoji hiện trạng — KHÔNG nhân tiện đổi sang IconLine, đó là việc khác). **Chỉ 4 trang catalog** — 9 trang `.cross-links` còn lại ngoài scope A1.
2. Trim 4→3 theo nguyên tắc: *bỏ card có đích đến đã xuất hiện ở khối khác trên cùng trang*. Đề xuất (chốt khi thực thi): du-lich bỏ **Bản đồ** (có ở interstitial links `:85` + nav); san-pham bỏ **OCOP** (trùng ocop-teaser-strip `:52-60`); ocop bỏ **Theo mùa** (trùng interstitial links `:123`); luu-tru bỏ card trùng interstitial của trang đó (grep `luu-tru.vue:85` interstitial links trước khi chọn).
3. CSS: `.cross-links` (`assets/css/catalog.css:217, 233, 371`) là auto-fill + 2-up tablet/mobile — **3 card không cần sửa CSS** (spec đúng ở điểm này). Không đụng.
4. Additive-first: sửa từng trang → verify SSR trang đó → mới sang trang kế.

**Verify:** SSR từng trang: đếm `cross-card` = 3 (trước: 4); card bị bỏ (grep label, vd `>Bản đồ<` trong section cross) = 0; khối thay thế nó trên trang (teaser/interstitial link cùng đích) ≥ 1.

**Commit:** 1 commit/trang hoặc gộp 2+2: `refactor(declutter-2): <trang> — cross-links 4→3 từ mảng script (bỏ card trùng <khối>)`

---

## Task 4 — A7: Chính sách JourneyActionRail (da-luu empty-state-only, tai-khoan bỏ hẳn)

*Rủi ro: VỪA (đụng composable + smoke test — xem S7).*

**Files:** `web-nuxt/pages/da-luu.vue:37-43`, `web-nuxt/pages/tai-khoan.vue:45-52`, `web-nuxt/composables/useJourneyActions.ts:191-278`, `web-nuxt/tests/smoke.test.ts:81-82, 455`

**Steps:**
1. **da-luu** — rail `:37-43` luôn-on (builder `savedWorkspaceActions` luôn trả action). Gate về empty-state: `v-if="totalSaved === 0"` (giữ `savedJourneyActions` — khi trống builder trả "Tìm điểm để lưu"/"Mở bộ lập lịch trình", đúng vai empty-state; `totalSaved` đã có tại `:199`). smoke.test `:105-107` vẫn pass (string còn).
2. **tai-khoan** — xoá rail `:45-52` (trùng panel "Việc nên làm tiếp" `:86-102` — xác nhận `<strong>Việc nên làm tiếp</strong>` ở `:89`). Xoá import/call `useJourneyActions` (`:182, :191`) + computed `userCpJourneyActions` trong page.
3. **Composable** — builder `userCpJourneyActions` (`useJourneyActions.ts:191-278`) thành mồ côi → xoá + bỏ khỏi return (`:447`). Grep lại toàn repo trước khi xoá.
4. **smoke.test.ts** — xoá 3 assertion mã hoá UI cũ: `:81` (`userCpJourneyActions`), `:82` (`JourneyActionRail` trong tai-khoan), `:455` (composable). Ghi rõ trong commit message đây là cập-nhật-test-theo-spec-đã-duyệt. `journeyActions.test.ts` chỉ dùng `homepageDecisionActions` — không đụng.
5. **KHÔNG đụng** instance homepage (`index.vue:64`) và admin (`admin/index.vue:158`, `admin/data-quality.vue:62` — ngoài phạm vi 44 trang public). Instance tim-kiem xử ở Task 5.

**Verify:** tai-khoan cần login → verify bằng đọc source sau sửa + build xanh (như Đợt 1 T11); grep `userCpJourneyActions` toàn repo = 0. da-luu: client-check (login) — có item: rail biến mất; xoá hết item (hoặc account trống): rail hiện.

**Commit:** `refactor(declutter-2): rail policy — tai-khoan bỏ rail trùng panel; da-luu rail chỉ empty-state (+dọn builder & smoke-test mồ côi)`

---

## Task 5 — B4: tim-kiem — bỏ Row E "Tìm theo khu vực" + gộp 2 rail thành 1

*Rủi ro: THẤP.*

**Files:** `web-nuxt/pages/tim-kiem.vue`

**Steps:**
1. Xoá section `:168-181` (anchor `<h2>Tìm theo khu vực</h2>`) — 2 grid `quick-picks` xếp chồng với Row D (`:156-166`, giữ). Footer cột "Khu vực" + `/khu-vuc/*` vẫn phục vụ intent này. CSS dùng class chung — không có orphan.
2. **Zero-result dedupe: NO-OP** (S5) — ghi nhận, không sửa.
3. (Chuẩn-hoá, tuỳ chọn — spec A7 "gộp 2 instance thành 1"): thay 2 rail (`:86-91` và `:106-110`) bằng 1 instance với `:actions="totalSearchResults ? searchNextActions : zeroResultActions"` + title computed tương ứng ("Bước tiếp theo" / "Có thể đi tiếp theo hướng này"), đặt sau vùng kết quả/empty. Giữ nguyên chuỗi `searchRecoveryActions`/`searchSuccessActions`/`JourneyActionRail`/`zero_result` để smoke.test `:433-438` pass.

**Verify:** SSR `/tim-kiem`: `Tìm theo khu vực` = 0; `Bạn đang tò mò điều gì?` (Row D) ≥ 1. SSR `/tim-kiem?q=xyz-khong-co`: EmptyState "Chưa thấy đúng ý bạn" ≥ 1, đúng 1 `journey-rail`-anchor trong HTML (grep class root của JourneyActionRail — đọc component lấy class). `/tim-kiem?q=chua` (có kết quả): rail 1 lần.

**Commit:** `refactor(declutter-2): tim-kiem — bỏ Row E khu vực (trùng Row D) + gộp 2 rail thành 1`

---

## Task 6 — A4: ChatWidget FAB ẩn trên detail page dia-diem

*Rủi ro: VỪA (đụng mọi trang qua layout; nhưng sửa 1 chỗ trong component).*

**Files:** `web-nuxt/components/ChatWidget.vue` (root `v-if` tại `:3`)

**Steps:**
1. Grep bằng chứng scope: chỉ `dia-diem/[id].vue` có `LazyAITravelTips` (`:243`) + `LazySmartRecommendations` (`:251`) inline → chỉ ẩn trên **route `dia-diem-id`**. KHÔNG ẩn trên `/dia-diem` (catalog), `/lich-trinh/[id]`, v.v.
2. `ChatWidget.vue:3` — `v-if="ff('chat_widget')"` → thêm điều kiện `&& !isEntityDetail` với `const isEntityDetail = computed(() => route.name === 'dia-diem-id')` (`route` đã có sẵn `:44`; dùng route-name, KHÔNG regex path — id chứa `%2F`).
3. Layout `default.vue:65` giữ nguyên `<LazyChatWidget />` (component tự quyết — 1 chỗ, ăn mọi trang).

**Verify:** ChatWidget trong `<ClientOnly>` → **không dùng SSR grep**. `preview_eval`: trên `/` và `/du-lich` → `!!document.querySelector('.chat-fab')` = true; trên `/dia-diem/<id thật>` = false, đồng thời `document.querySelector('.smart-recs, [class*=ai-tips]')` (đọc class thật của 2 component trước) tồn tại. Chuyển trang client-side detail→catalog: FAB xuất hiện lại (route reactivity).

**Commit:** `refactor(declutter-2): ChatWidget — ẩn FAB trên dia-diem/[id] (đã có AITravelTips + SmartRecommendations inline)`

---

## Task 7 — A3b: Footer cột "Khám phá" 7 link → "Gợi ý nhanh" 4 link ⚠️ có PRECHECK CMS

*Rủi ro: VỪA (S6 — CMS override). Có thể phải HOÃN NỬA nếu backend không chạy được local.*

**Files:** `web-nuxt/layouts/default.vue:161-170` (DEFAULT_FOOTER_COLUMNS cột "Khám phá"), `agent/seed_site_settings.py:93-120`

**Steps:**
1. **PRECHECK (bắt buộc):** curl `http://localhost:8000/api/site-settings` (hoặc qua Nuxt proxy `:3000/api/site-settings`) — kiểm key `footer.columns`. Local SQLite hiện **không có bảng site_settings** (đã kiểm `agent/data/vinhlong360.db` — 22 bảng, không có) → local fallback default FE, sửa default là thấy ngay. **Prod (PG) nhiều khả năng đã seed** (giá trị seed khác default FE — bằng chứng S6) → thay đổi chỉ lên prod khi cập nhật row DB qua AdminCP lúc deploy. Ghi việc này vào ghi-chú-vận-hành trong plan-result, KHÔNG tự deploy (§4 CLAUDE.md).
2. Sửa `DEFAULT_FOOTER_COLUMNS` cột 1: title `Khám phá` → `Gợi ý nhanh`, 7 link → 4 curated (đề xuất: `/du-lich`, `/san-pham`, `/theo-mua`, `/le-hoi` — ocop tới được từ trang san-pham + nav; luu-tru/su-kien có trong nav "Khám phá" topbar `:132-143`).
3. Sửa `agent/seed_site_settings.py:93-120` giá trị `footer.columns` tương ứng (giữ 3 cột còn lại nguyên trạng). Không đổi schema → không kích hoạt bất biến B4; nhưng grep `footer.columns` trong `agent/tests/` trước — nếu có assert nội dung seed thì cập nhật test cùng commit.
4. Cân nhắc SEO (memory hub-spoke footer): 3 link bị bỏ vẫn có ở topbar nav (crawlable SSR) — ghi nhận vào plan-result, không chặn.

**Verify:** SSR `/`: cột `Gợi ý nhanh` ≥ 1, đếm link trong cột = 4, `Khám phá` (footer h2 — phân biệt với nav-group topbar cùng tên) = 0; footer-legal + disclaimer còn nguyên. `python -m pytest -q agent/tests -k site_settings` không đỏ thêm.

**Commit:** `refactor(declutter-2): footer — cột Khám phá 7 link → Gợi ý nhanh 4 link (default FE + seed; DB prod cập nhật lúc deploy)`

---

## Task 8 — A2: Chính sách CatalogInterstitial — inline vào editorial (pilot san-pham → lan dần)

*Rủi ro: VỪA (11 call site — làm cuối, component giữ nguyên).*

**Files:** pilot `web-nuxt/pages/san-pham.vue:63-68` + `:71-82`; đợt lan: `du-lich.vue:81-86`→`:89-110`, `ocop.vue:119-124`→`:127-137`, `le-hoi.vue:133-138`, `su-kien.vue:104-113`→`:135-139`, `lich-trinh/index.vue:110-118`→`:103-107`, `luu-tru.vue:85`, `theo-mua.vue:145`, `tuyen-duong.vue:66`, `dia-diem/index.vue:77`, `khu-vuc/[area].vue:38`

**Steps:**
1. **Pilot san-pham:** dời `<CatalogInterstitial ...>` (`:63-68`) vào **trong** section `.page-article` (`:71-82`), đặt giữa khối "Đặc sản vùng sông nước" và h2 "Mua gì, tháng nào?" (`:77`). Component + props giữ nguyên (nó đã là `<aside role="complementary">`). Nếu cần 1 rule spacing: thêm `.page-article .interstitial { ... }` dùng token — không sửa component.
2. Verify pilot xong mới lan (additive-first). Đợt lan xử từng trang theo cùng pattern; **ngoại lệ ghi nhận khi audit:** trên **le-hoi**, fact interstitial (`:134` "giao thoa văn hoá Kinh – Khmer – Hoa…") **trùng gần nguyên văn** đoạn mở editorial (`:144`) → inline sẽ lộ trùng — áp nhánh "suppress trên trang ít giá trị": bỏ hẳn call site le-hoi (duplication test), ghi rõ trong commit.
3. Trang **không có** `.page-article` (grep từng trang; khả năng: `khu-vuc/[area]`, `dia-diem/index`, `tuyen-duong`, `theo-mua`) → **giữ nguyên vị trí hiện tại** trong Đợt 2 (đừng suppress tuỳ tiện — khu-vuc thuộc B9/Đợt 3). Ghi danh sách giữ-nguyên vào plan-result.
4. `v-once` trên các section editorial: interstitial có `NuxtLink` — kiểm không bị `v-once` nuốt reactivity (đặt interstitial ngoài phần tử `v-once` hoặc bỏ `v-once` của riêng section đó nếu buộc phải — test SSR + client nav).

**Verify (mỗi trang):** SSR — fact text còn ≥ 1 và **nằm sau** chuỗi `page-article` trong HTML (python: `html.find('page-article') < html.find('<fact-substring>')`); không còn interstitial đứng giữa 2 section rời. le-hoi: fact = 0, editorial `:144` còn nguyên.

**Commit:** `refactor(declutter-2): san-pham — interstitial inline vào editorial (pilot A2)` → sau đó `refactor(declutter-2): interstitial inline policy — áp <danh sách trang> (le-hoi: suppress vì trùng editorial)`

---

## HOÃN (không làm trong Đợt 2 — lý do)

| Mục | Lý do hoãn |
|---|---|
| **A3c** JourneyBar + ReportModal global→page-level (`layouts/default.vue:67-68`) | Spec §5 xếp Đợt 3 (cần build analysis); đụng lazy-chunk mọi trang |
| **A8** KBYG tinh gọn | Spec §5 Đợt 3. **Data-audit ĐÃ chạy (1730 entity):** tips/golden_hours/checklist = **0%** (khối spec muốn tinh gọn KHÔNG BAO GIỜ render trên trang thật); amenities 3.5% (accommodation 36.6%); hours 19.2%; opening_hours 0.2%. → Scope A8 thật cho Đợt 3 = hours-dedup + amenities single-source + xét hành vi KBYG khi data rỗng — KHÔNG phải grid golden-hours. |
| **A5-danh-ba** | NO-OP — S3, không có duplication |
| **B4 zero-result dedupe** | NO-OP — S5, code hiện tại đã loại trừ nhau |
| **A3b nửa-DB (prod)** | Cập nhật row `footer.columns` PG prod = thao tác deploy/AdminCP — điều kiện dừng §4; chỉ ship default+seed trong repo |

## Kết-đợt (bắt buộc trước khi báo hoàn thành)

1. `cd web-nuxt && npm run build` — xanh.
2. `cd agent && python -m pytest -q` — không đỏ thêm ngoài 6 fail `TestPhase14PgIndexes` pre-existing (thiếu Postgres).
3. **SSR-sweep 10 URL** (cache-bust, tuần tự): `/`, `/du-lich`, `/san-pham`, `/ocop`, `/luu-tru`, `/le-hoi`, `/su-kien`, `/lich-trinh`, `/tim-kiem`, `/dia-diem/<id thật>` — 200 + mọi anchor-cắt = 0 + anchor-giữ ≥ 1 (theo bảng verify từng task).
4. `preview_eval` chat-fab (Task 6) — ClientOnly không nằm trong SSR.
5. Grep orphan cuối: `areaFilterOptions` (le-hoi/su-kien), `countByArea` (lich-trinh/ocop), `userCpJourneyActions`, `region-tagline`, class cross-card thừa — 0 mồ côi ngoài comment giải thích.
6. Cập nhật mục "KẾT QUẢ THỰC THI" vào plan file + ghi chú vận hành A3b (DB prod) — KHÔNG tự ghi vào ROADMAP ngoài mục Backlog phát sinh nếu có việc mới.
---

## KẾT QUẢ THỰC THI ĐỢT 2 (2026-07-07)

**8/8 task, 10 commit** (`d9a5ca3..c1533e3`). Điều chỉnh trong thực thi (đều theo nguyên tắc plan):
- T5: gộp-2-rail SKIP (2 nhánh đã loại trừ nhau qua data — cosmetic, YAGNI).
- T8: luu-tru chuyển từ inline → SUPPRESS (fact trùng gần nguyên văn đoạn editorial ngay trên — phát hiện khi verify); lich-trinh + su-kien GIỮ NGUYÊN (interstitial có v-if động, inline vào v-once sẽ freeze).
- T7: prod DB override footer.columns (verified qua /api/site-settings) — cập nhật row qua AdminCP lúc deploy (vận hành, §4).

**Kết đợt:** build ✅ (lần 1 fail transient, lần 2 sạch) · pytest 4213 passed (6 pre-existing PG) · SSR-sweep 10 URL trên server restart: 10/10 (2 false-positive đã giải trình: footer đọc CMS prod; "ngủ giữa vườn trái cây" là summary entity Homestay Út Trinh, không phải interstitial) · orphan-grep sạch (areaFilterOptions còn ở luu-tru/ocop là hợp lệ — đường filter duy nhất của trang).

**GOTCHA MỚI:** Nitro SWR route-rules cache theo PATH, query-string KHÔNG bust — verify sau sửa phải restart dev server hoặc chờ revalidate; đừng tin ?vv= bust như Đợt 1 tưởng.
