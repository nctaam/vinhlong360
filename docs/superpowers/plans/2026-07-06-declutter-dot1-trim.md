# Declutter Đợt 1 — Trim rủi-ro-thấp: Implementation Plan
> STATUS (2026-07-10): done — plan đã thực thi & ship.


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xoá ~19 khối UI thừa/trùng-chức-năng rủi-ro-thấp trên 12 trang public (spec: `docs/superpowers/specs/2026-07-06-ui-declutter-design.md`, mục Đợt 1) — không đổi logic dữ liệu, không thêm mới.

**Architecture:** Toàn bộ là xoá template + dọn CSS/state mồ côi trong cùng commit. Không có backend. Mỗi task một commit, hệ thống chạy được sau mỗi commit (§B5).

**Tech Stack:** Nuxt 4 SSR (`web-nuxt/`), Vue SFC, CSS thuần + tokens.

## Global Constraints

- **Bất khả xâm phạm (không được đụng):** byline `.entity-byline`; trust-card + link "Báo sai hoặc bổ sung nguồn"; nhãn "AI gợi ý" + disclaimer; nhãn honesty "chưa có ảnh thật"; motif phù-sa (tick/stratum/sediment-head/sediment-divider); text pháp lý ("không bán tour", disclaimer); breadcrumb; skip-link; SaveButton/Share; EmptyState illustration.
- **Chỉ XOÁ/GỘP** — không thêm feature, không refactor lan man. Line-number trong plan là con trỏ *ước lượng từ audit* — LUÔN xác nhận anchor-string trước khi xoá; nếu lệch, tìm anchor bằng Grep.
- Xoá template ⇒ **grep mọi class/ref/computed chỉ khối đó dùng** → xoá CSS/state mồ côi trong CÙNG commit. Không xoá thứ nơi khác còn dùng.
- **Giao thức verify V** (dùng cho mọi task): dev server chạy sẵn (`preview_start` nuxt, port 3000). Fetch SSR:
  `PYTHONIOENCODING=utf-8 python -c "import urllib.request as u;print(u.urlopen('http://localhost:3000/<path>').read().decode('utf-8'))" | grep -c "<anchor>"`
  — Trước khi xoá: kỳ vọng `>=1` (khối đang render). Sau khi xoá: kỳ vọng `0` + anchor của **khối giữ lại** vẫn `>=1`. KHÔNG tin screenshot (bài học frame-trắng); style-check bằng computed-style nếu cần.
- Commit message: `refactor(declutter-1): <trang> — bỏ <khối> (lý do 1 dòng)`. Kết đợt: `cd web-nuxt && npm run build` phải xanh + chạy full `python -m pytest -q` backend không đỏ thêm.
- FE không có component-test harness chạy được (vitest env hỏng — đã biết) ⇒ chu trình test của task = verify-V (present→absent→kept) thay cho RED/GREEN.

---

### Task 1: Layout — bỏ beta-banner 🚧 (A3a)

**Files:** Modify: `web-nuxt/layouts/default.vue:55-63` (+ state/CSS liên quan)

- [ ] **Step 1: Xác nhận anchor.** Grep `Trang đang trong giai đoạn xây dựng` trong `layouts/default.vue`. Đọc block chứa nó (div banner + nút `aria-label="Đóng thông báo"`), tìm state đóng/mở (grep tên biến trong block, vd `betaBanner`/`showBeta`/localStorage key) và class CSS của block.
- [ ] **Step 2: Xoá** block template + biến state/handler chỉ nó dùng + CSS class mồ côi (grep từng class trước khi xoá — class dùng chung thì GIỮ).
- [ ] **Step 3: Verify V** trên `/`: anchor `Trang đang trong giai đoạn xây dựng` = 0; anchor giữ-lại `class="logo"` ≥1. Console dev không lỗi compile.
- [ ] **Step 4: Commit** `refactor(declutter-1): layout — bỏ beta-banner 🚧 (OnboardingSheet đã truyền thông beta; hết 2 interrupt chồng nhau)`

### Task 2: Homepage — bỏ section "Trợ lý AI" CTA (B1-1)

**Files:** Modify: `web-nuxt/pages/index.vue:351-359` (+ CSS `.chatbot-cta*`)

- [ ] **Step 1: Xác nhận anchor.** Grep `chatbot-cta` trong `index.vue` — block section chứa nút `Hỏi ngay` (`openChat`). Kiểm `openChat` có nơi khác dùng không (nếu chỉ section này → xoá luôn hàm).
- [ ] **Step 2: Xoá** section + CSS `.chatbot-cta*` + hàm/import mồ côi.
- [ ] **Step 3: Verify V** trên `/`: `chatbot-cta` = 0; ChatWidget FAB (`chat-fab`) vẫn ≥1 (đây là lý do cắt — FAB làm cùng việc).
- [ ] **Step 4: Commit** `refactor(declutter-1): home — bỏ section Trợ lý AI (trùng ChatWidget FAB)`

### Task 3: Homepage — xoá dead-code `trending` + khử trùng seasonal (B1-3)

**Files:** Modify: `web-nuxt/pages/index.vue` (~487, ~572-575)

- [ ] **Step 1: Xác nhận.** Grep `trending` trong `index.vue`: computed `trending` (~487) có được template dùng không? (Audit: không — dead). Grep `seasonalList` + `firstSeasonal` (~572-575).
- [ ] **Step 2: Sửa.** Xoá computed `trending` nếu đúng là dead. Sửa `seasonalList` để luôn loại `firstSeasonal` khỏi scroll-row: `const seasonalList = computed(() => (…nguồn cũ…).filter(e => e?.id !== firstSeasonal.value?.id))` (giữ nguyên nguồn cũ, chỉ thêm filter — decision card đã đại diện cho item này).
- [ ] **Step 3: Verify V** trên `/`: trang 200; nếu có `firstSeasonal`, id của nó không xuất hiện 2 lần trong section mùa (grep id entity trong HTML — đếm giảm 1).
- [ ] **Step 4: Commit** `refactor(declutter-1): home — xoá dead trending + seasonal không lặp firstSeasonal`

### Task 4: Homepage — storyland fallback card → EmptyState (B1-6a)

**Files:** Modify: `web-nuxt/pages/index.vue:309-321` (+ CSS `.storyland-*` nếu mồ côi)

- [ ] **Step 1: Xác nhận anchor.** Grep `storyland` trong `index.vue` — block card dùng ảnh `/img/spread/song-nuoc.webp` (fallback khi feed trống).
- [ ] **Step 2: Thay** block bằng EmptyState nhất quán (pattern dòng ~75-81):
  ```html
  <EmptyState tone="empty" title="Cộng đồng đang khởi động"
    message="Chưa có bài viết nổi bật tuần này — bạn là người kể chuyện đầu tiên nhé!" />
  ```
  Giữ CTA "Tham gia cộng đồng" sẵn có (~305-307). Xoá CSS `.storyland-*` mồ côi.
- [ ] **Step 3: Verify V** trên `/`: `storyland-card` = 0; `Tham gia cộng đồng` ≥1.
- [ ] **Step 4: Commit** `refactor(declutter-1): home — storyland fallback → EmptyState (nhất quán pattern trống)`

### Task 5: Detail — xoá `.contact-row` chết (B5a)

**Files:** Modify: `web-nuxt/pages/dia-diem/[id].vue:400-407` (+ CSS `.contact-row`, `.contact-cta` ~1255)

- [ ] **Step 1: PRECHECK (điều kiện cắt).** Đọc `ContactWidget.vue` — xác nhận nó render phone + zalo + (map khi thiếu contact). Kiểm `buyContactUrl`: grep trong `[id].vue` — nếu CHỈ contact-row dùng mà ContactWidget không có, thì DỜI nút "Hỏi mua trực tiếp" vào khối next-steps thay vì mất chức năng (additive-first) — ghi rõ vào commit.
- [ ] **Step 2: Xác nhận chết.** Grep CSS `~1255` — rule ẩn `.contact-row` ở desktop; mobile bị ContactWidget che (audit đã verify). Xoá block template `.contact-row` + CSS mồ côi.
- [ ] **Step 3: Verify V** trên `/dia-diem/cu-lao-my-hoa`: `contact-row` = 0; ContactWidget (`cw-row` hoặc `cw-btn`) ≥1; nếu entity có buyContactUrl → nút hỏi-mua vẫn tồn tại ở vị trí mới.
- [ ] **Step 4: Commit** `refactor(declutter-1): dia-diem/[id] — bỏ contact-row chết (desktop bị CSS ẩn, mobile ContactWidget che)`

### Task 6: Detail — fix best_time render 2 lần (B5b)

**Files:** Modify: `web-nuxt/pages/dia-diem/[id].vue` (~149-155 vs ~780)

- [ ] **Step 1: Xác nhận.** Grep `best_time` trong `[id].vue` — 2 chỗ render: highlights row (~149-155) và `practicalTips` (~780). Chọn giữ **highlights row** (gần hero, dễ thấy), bỏ entry trong `practicalTips`.
- [ ] **Step 2: Xoá** entry `best_time` khỏi mảng `practicalTips` (chỉ entry đó).
- [ ] **Step 3: Verify V**: chọn 1 entity có `best_time` (grep data hoặc dùng `/dia-diem/cu-lao-my-hoa`); đếm occurrence giá trị best_time trong HTML = 1 (trước: 2).
- [ ] **Step 4: Commit** `refactor(declutter-1): dia-diem/[id] — best_time chỉ render 1 chỗ (highlights)`

### Task 7: Cộng đồng — bỏ friend-activity section (B6a)

**Files:** Modify: `web-nuxt/pages/cong-dong.vue:293-315` (+ CSS/state mồ côi)

- [ ] **Step 1: Xác nhận anchor.** Grep `friend-activity` (hoặc đọc 293-315) — section trùng tab "Đang theo dõi" (~292). Grep composable/fetch chỉ section này dùng.
- [ ] **Step 2: Xoá** section + fetch/state/CSS mồ côi.
- [ ] **Step 3: Verify V** trên `/cong-dong`: anchor section = 0; tab `Đang theo dõi` ≥1.
- [ ] **Step 4: Commit** `refactor(declutter-1): cong-dong — bỏ friend-activity (trùng tab Đang theo dõi)`

### Task 8: Cộng đồng — bỏ sidebar "Cách tham gia" (B6b)

**Files:** Modify: `web-nuxt/pages/cong-dong.vue:481-502`

- [ ] **Step 1: Xác nhận anchor** `Cách tham gia` (sidebar card hướng dẫn 3-4 bước — composer + chips là affordance sống rồi).
- [ ] **Step 2: Xoá** card + CSS mồ côi.
- [ ] **Step 3: Verify V**: anchor = 0; composer (`Kể về trải nghiệm`) ≥1.
- [ ] **Step 4: Commit** `refactor(declutter-1): cong-dong — bỏ sidebar Cách-tham-gia (composer tự nói)`

### Task 9: Cộng đồng — sidebar "Quy tắc" → 1 link (B6c)

**Files:** Modify: `web-nuxt/pages/cong-dong.vue:504-513`

- [ ] **Step 1: Xác nhận anchor** `Quy tắc cộng đồng` — card đang duplicate nguyên văn nội dung của `/huong-dan-thanh-vien` (rủi ro maintenance).
- [ ] **Step 2: Thay** cả card bằng 1 dòng link đặt cuối sidebar-card "Đôi lời" (~408-411):
  ```html
  <NuxtLink to="/huong-dan-thanh-vien" class="sidebar-rules-link">Xem quy tắc cộng đồng →</NuxtLink>
  ```
  CSS: dùng class link sẵn có của sidebar nếu có (grep `sidebar-` link pattern); chỉ thêm rule mới nếu bắt buộc.
- [ ] **Step 3: Verify V**: text quy tắc dài = 0; `Xem quy tắc cộng đồng` = 1.
- [ ] **Step 4: Commit** `refactor(declutter-1): cong-dong — quy tắc thành link (hết duplicate huong-dan-thanh-vien)`

### Task 10: Cộng đồng — bỏ empty-state onboard-follows (B6e)

**Files:** Modify: `web-nuxt/pages/cong-dong.vue:367-380`

- [ ] **Step 1: Xác nhận anchor** (block gợi ý follow trong empty-state của tab feed) — GIỮ sidebar "Gợi ý kết bạn" (~452-466) làm nguồn duy nhất.
- [ ] **Step 2: Xoá** block trong empty-state (giữ message trống cơ bản của tab).
- [ ] **Step 3: Verify V**: sidebar `Gợi ý kết bạn` ≥1; block onboard trong empty-state = 0 (test bằng tab Đang-theo-dõi khi chưa follow ai — hoặc grep anchor class trong HTML).
- [ ] **Step 4: Commit** `refactor(declutter-1): cong-dong — bỏ onboard-follows trong empty-state (sidebar gợi ý kết bạn là nguồn duy nhất)`

### Task 11: Tài khoản — bỏ `.cp-stats` (B7-đợt1)

**Files:** Modify: `web-nuxt/pages/tai-khoan.vue:105-110`

- [ ] **Step 1: PRECHECK.** Mở `/nguoi-dung/<id>` của user thật (hoặc đọc `nguoi-dung/[id].vue`) xác nhận các stat này có trên public profile (audit nói có — verify trước, đúng ghi chú spec).
- [ ] **Step 2: Xoá** `.cp-stats` block + CSS mồ côi.
- [ ] **Step 3: Verify V** trên `/tai-khoan` (cần đăng nhập — SSR trả login-gate thì verify bằng đọc source sau sửa + build xanh; ghi chú vào commit).
- [ ] **Step 4: Commit** `refactor(declutter-1): tai-khoan — bỏ cp-stats (đã có trên trang cá nhân công khai)`

### Task 12: Cài đặt — bỏ `.settings-overview` 5 card (B7)

**Files:** Modify: `web-nuxt/pages/cai-dat.vue:17-43`

- [ ] **Step 1: Xác nhận anchor** `settings-overview` — 5 card tóm tắt đúng các tab panel ngay bên dưới.
- [ ] **Step 2: Xoá** block + CSS mồ côi.
- [ ] **Step 3: Verify** build/compile (trang cần login — như Task 11).
- [ ] **Step 4: Commit** `refactor(declutter-1): cai-dat — bỏ settings-overview (tóm tắt cái ngay bên dưới)`

### Task 13: Tài khoản — robots `noindex,nofollow` → `noindex, follow` (B7)

**Files:** Modify: `web-nuxt/pages/tai-khoan.vue:200-202`

- [ ] **Step 1: Xác nhận.** Grep `nofollow` trong `tai-khoan.vue` (useSeoMeta robots).
- [ ] **Step 2: Đổi** thành `'noindex, follow'` (nofollow chặn truyền link-equity vô cớ).
- [ ] **Step 3: Verify:** grep source sau sửa; build xanh.
- [ ] **Step 4: Commit** `refactor(declutter-1): tai-khoan — robots noindex,follow (đồng bộ chuẩn site)`

### Task 14: Liên hệ — bỏ section "Xem thêm" cross-links (C)

**Files:** Modify: `web-nuxt/pages/lien-he.vue:68-88`

- [ ] **Step 1: Xác nhận anchor** (section cross-links cuối trang — trùng footer). GIỮ link "Chính sách bảo mật" contextual trong copy (~63).
- [ ] **Step 2: Xoá** section + CSS mồ côi.
- [ ] **Step 3: Verify V** trên `/lien-he`: anchor section = 0; `Chính sách bảo mật` ≥1 (link trong copy); footer vẫn ≥1.
- [ ] **Step 4: Commit** `refactor(declutter-1): lien-he — bỏ cross-links cuối (trùng footer)`

### Task 15: Bản đồ — bỏ khối empty-state (C)

**Files:** Modify: `web-nuxt/pages/ban-do.vue:29-39`

- [ ] **Step 1: Xác nhận anchor** (khối empty-state dưới filter — bản đồ trống + result-meta count đã là feedback đủ).
- [ ] **Step 2: Xoá** khối; nếu message hữu ích → dời thành 1 dòng text nhỏ trong result-meta (không tạo component mới).
- [ ] **Step 3: Verify V** trên `/ban-do`: anchor = 0; filter chips + map container ≥1.
- [ ] **Step 4: Commit** `refactor(declutter-1): ban-do — bỏ empty-state thừa (map + count là feedback)`

### Task 16: Hướng dẫn thành viên — bỏ CTA section cuối (C)

**Files:** Modify: `web-nuxt/pages/huong-dan-thanh-vien.vue:96-103`

- [ ] **Step 1: Xác nhận anchor** (CTA band cuối trang).
- [ ] **Step 2: Xoá** + CSS mồ côi.
- [ ] **Step 3: Verify V** trên `/huong-dan-thanh-vien`: anchor = 0; nội dung 8 section chính ≥1.
- [ ] **Step 4: Commit** `refactor(declutter-1): huong-dan-thanh-vien — bỏ CTA band cuối`

### Task 17: Danh bạ — bỏ page-article editorial (C)

**Files:** Modify: `web-nuxt/pages/danh-ba.vue:52-56`

- [ ] **Step 1: Xác nhận anchor** (khối editorial lặp nội dung hero). Caveat "đang cập nhật" nếu nằm trong đó → dời thành footnote 1 dòng cạnh select khu vực.
- [ ] **Step 2: Xoá/dời** + CSS mồ côi.
- [ ] **Step 3: Verify V** trên `/danh-ba`: khối editorial = 0; hero + select ≥1; footnote caveat = 1 (nếu dời).
- [ ] **Step 4: Commit** `refactor(declutter-1): danh-ba — bỏ editorial trùng hero (caveat thành footnote)`

### Task 18: Theo mùa — bỏ season-moment-pill + full-grid cuối (B8-đợt1)

**Files:** Modify: `web-nuxt/pages/theo-mua.vue:38-41, 205-231`

- [ ] **Step 1: Xác nhận 2 anchor:** (a) `season-moment-pill` (~38-41) — catalog-stats ngay dưới show cùng count; (b) full grid "Tất cả đang mùa" cuối (~205-231) — scroll đúp nội dung shelves phía trên.
- [ ] **Step 2: Xoá** cả hai + CSS mồ côi. (month-grid fallback ~65-82 là việc Đợt 3 — KHÔNG đụng.)
- [ ] **Step 3: Verify V** trên `/theo-mua`: 2 anchor = 0; season-ring + shelves ≥1; catalog-stats ≥1.
- [ ] **Step 4: Commit** `refactor(declutter-1): theo-mua — bỏ moment-pill (trùng stats) + full-grid cuối (scroll đúp)`

### Task 19: FilterChips — fix `--surface-inverse` undefined (bug đi kèm)

**Files:** Modify: `web-nuxt/assets/css/variables.css` + xác nhận `web-nuxt/components/FilterChips.vue:91-102`

- [ ] **Step 1: Xác nhận.** Grep `--surface-inverse` toàn `web-nuxt/` — chỉ FilterChips dùng, chưa define ở variables.css → active-chip mất nền.
- [ ] **Step 2: Define** trong `variables.css` khối `:root`: `--surface-inverse: var(--ink-900);` và trong dark-override: `--surface-inverse: #f5f5f7;` (đảo tương phản 2 theme).
- [ ] **Step 3: Verify** computed-style: mở trang có FilterChips (vd `/dia-diem`), active chip — `getComputedStyle(el).backgroundColor` ra màu thật (không rỗng/transparent) ở cả 2 theme.
- [ ] **Step 4: Commit** `fix(declutter-1): define --surface-inverse (FilterChips active mất nền cả 2 theme)`

---

### Kết đợt (bắt buộc trước khi báo hoàn thành)

- [ ] `cd web-nuxt && npm run build` — xanh.
- [ ] `cd agent && python -m pytest -q` — không đỏ thêm ngoài 6 PG-index pre-existing.
- [ ] SSR-sweep 6 URL: `/`, `/dia-diem/cu-lao-my-hoa`, `/cong-dong`, `/theo-mua`, `/lien-he`, `/ban-do` — 200 + không anchor-đã-xoá nào còn.
- [ ] Grep toàn `web-nuxt/assets/css` + SFC styles các class đã xoá — 0 orphan còn lại.

---

## KẾT QUẢ THỰC THI (2026-07-06)

**18/19 task hoàn thành, 12 commit** (`3939aef`..`9f49c13`). Hai deviation có chủ đích, đều theo nguyên tắc của chính plan:
- **T18b (theo-mua full-grid): KHÔNG cắt** — shelves cap 8 mục/loại; full-grid là listing đầy đủ duy nhất (paging) → cắt = mất truy cập mục 9+, fail deletion-test. Audit sai ở tail này.
- **T19 (--surface-inverse): SKIP** — premise sai ở code hiện tại: `--chip-active-bg: var(--surface-inverse, var(--ink))` có fallback hoạt động cả 2 theme; không có bug để fix.
- T3 seasonal-dedup: đã có sẵn trong code (no-op); chỉ xoá computed `trending`.

**Kết đợt:** `npm run build` ✅ xanh · pytest ✅ 4213 passed (6 fail = TestPhase14PgIndexes pre-existing, thiếu Postgres) · SSR-sweep ✅ mọi trang đụng tới 200 + anchor cắt-mất/giữ-còn đạt (lưu ý: `/` có SWR 300s — verify phải cache-bust; phần tử ClientOnly không hiện trong SSR, verify bằng source) · orphan-grep ✅ (còn lại chỉ comment giải thích + `.guide-cta` của huong-dan.vue thuộc Đợt 3).
