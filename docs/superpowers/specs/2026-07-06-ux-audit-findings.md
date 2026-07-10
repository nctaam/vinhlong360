# Kết quả test-Chrome + audit 36 trang → danh sách nâng cấp ưu tiên (2026-07-06)
> STATUS (2026-07-10): done — design/audit đã hiện thực & ship.


Nguồn: live Chrome probes (home/detail desktop+mobile — sạch) + swarm audit 6 sub-agent đọc mã + grep. Xếp theo impact.

## ❌ MUST-FIX (rõ ràng, tác động cao)

1. **`thong-bao.vue` — trang TỤT HẬU rõ nhất** (8 sóng không đụng tới). Bare `<h1>Thông báo>` không eyebrow/serif; thẻ notification phẳng không rule/serif; **nút X dismiss 24×24px** (dưới 44px — BUG touch-target a11y thật); shell 640px hẹp, không breakpoint tablet. → Masthead pass (dateline-eyebrow + serif h1 như tai-khoan), thẻ notif serif-title + tri-province rule, dismiss 44px, item → NuxtLink, thêm dark coverage.
2. **`dia-diem/index.vue` — trùng lặp bộ lọc 4 lớp** cho 2 facet: province-stamps (area) + type-scroll-row (type) + 2 FilterChips (type+area lần nữa) trong `.dd-refine` — tất cả điều khiển cùng `areaFilter`/`typeFilter`. → Bỏ cặp FilterChips dư, giữ province-stamps + type-scroll-row (signature) + CHỈ ô search trong refine-bar.
3. **`khu-vuc/[area].vue:128` — h2 "Khám phá thêm {area}" nằm NGOÀI `.section-head`** → render KHÔNG có sediment tick (lệch thấy rõ trên trang vốn full-tick). → Bọc `<div class="section-head">` hoặc thêm selector.
4. **`nguoi-dung/[id].vue` — nhảy heading h1→h4** (`.bs-cat-title` là h4, không có h2/h3 giữa) → SR nhảy cấp. → Bump `.bs-cat-title` lên h3.

## ⚠️ SHOULD-IMPROVE (theo chủ đề, gom sửa)

**A. Sediment-head thiếu trên h2 phụ** (consistency — nhiều trang chỉ tick h2 chính, bỏ h2 phụ):
- `cong-dong.vue` 7 sidebar h2 (bold sans, không tick)
- `danh-ba.vue` 3 h2 (:34/:53/:127) + không dùng font-editorial ở đâu cả
- `kham-pha/[interest].vue` "Đi tiếp" h2 (:107)
- (đã liệt ở #3: khu-vuc "Khám phá thêm")

**B. Emoji-trong-vòng-tròn / emoji trần (anti-slop tell)**:
- `lien-he.vue` 5 thẻ contact `.card-icon` (emoji giữa vòng 56px — nổi bật nhất trang)
- `tim-kiem.vue` cross-link `.cross-icon` emoji trần
- `tai-khoan.vue`/`cai-dat.vue` tab + action emoji
→ Bọc emoji-in-designed-chip hoặc glyph SVG lệch-tâm (như EntityCard).

**C. Hex hardcode (nợ token — không phải bug dark vì có fallback/override, nhưng doc cấm)**:
- `var(--danger, #c0392b)` × nhiều (nguoi-dung, tai-khoan, cai-dat) — bỏ fallback literal
- `#f5f5f5` (cai-dat `--bg-warm` fallback)
- `xa-phuong/[id].vue:377-383` hero gradient hex per-area (light+dark) → token hoá
- `huong-dan-thanh-vien.vue` level-tier hex (#8bc34a/#2196f3/#ff9800/#d4a017 + dark set) → token

**D. Copy chung chung (voice-guide cấm)**:
- `index.vue` "Khám phá ngay →" / "Xem tất cả" (:187/207/240/261) → story-voice ("Đọc câu chuyện {name} →")
- `tim-kiem.vue` heading "Khám phá theo chủ đề" (:156) → lời mời có ngữ cảnh

**E. Khác**:
- `danh-ba.vue` skeleton `.sk-bar` gradient phẳng KHÔNG grain (AI-slop tell) → thêm `var(--grain)`
- `danh-ba.vue` `.fac` office-card không editorial DNA → ít nhất serif tên `.fac strong`
- `kham-pha` chip bespoke thay vì `FilterChips` (consistency)
- `index.vue` sediment tick = fork inline (không dùng shared class) — nợ maintenance
- `index.vue` `.dx-*` tone hex không có dark override (:1076-1080) — contrast tối
- `xa-phuong` map không có list-view keyboard/SR alternative; dead `.sec-icon` markup
- Legal pages: không có anchor TOC cho 6 mục
- `bang-xep-hang` fetchFailed hydration → ĐÃ có task_8aa977f1
- Nhiều trang thiếu breakpoint ~768px tablet (minor)

## ❌ THÊM (từ audit flagship + seasonal/products — CAO GIÁ TRỊ, sóng bỏ sót)
5. **`dia-diem/[id].vue` — h2 CỦA TRANG (Mùa vụ/Liên kết/Thông tin/Độ tin cậy/Lưu ý/Nên thử/Bước tiếp) KHÔNG có sediment-head** — trong khi component con (Nearby/KnowBeforeYouGo/Reviews/Feed/AI) CÓ → trang flagship "nhấp nháy" ticked/unticked khi cuộn. (Live-probe của tôi đếm 7 sediment nhưng đó là của component con, không phải h2 trang!) → thêm `.sediment-head` cho h2 trang.
6. **`EntityHeroPlaceholder.vue` (build ở Sóng 1) KHÔNG trang nào dùng** — detail tự chế hero no-photo inline (gradient+grain nhưng THIẾU motif glyph lệch-tâm). → thay hero inline bằng `<EntityHeroPlaceholder :id :cat :label>`.
7. **`da-luu.vue` — thẻ saved BESPOKE, không phải EntityCard** (thiếu serif/dateline/card-rule/grain). → reuse EntityCard hoặc backport class.
8. **`.event-info h3` (events.css:467) không serif** → vỡ Story-Card title parity le-hoi+su-kien (shared, 1 fix 2 trang).
9. **`lich-trinh/index.vue`** h2 (:96,:113) không sediment-head; `.quick-pick` thiếu `aria-pressed` (a11y).
10. **`.catalog-cross h2` (14 trang "Khám phá thêm") — ĐÃ FIX inline** (catalog.css: +serif +tick +dark). Verify page-local theo-mua/tuyen-duong không override.

## ⚠️ THÊM
- `le-hoi` status-now pulse infinite suốt nhiều ngày lễ hội (motion budget) → gate first-day.
- `su-kien`/`luu-tru`/`kham-pha` chip bespoke thay FilterChips (mất tri-province active).
- `dia-diem/[id]` significance/atmosphere/famous_for render 3× (extraContent+tips+facts) — trùng.
- `dia-diem/[id]` Ken Burns + peak-pulse cùng viewport (motion); month-strip cells không keyboard.
- `da-luu` `.saved-inline-warning` #fff7e6 không dark.
- Map route-line `#2563eb` hardcode (dựa `.dark canvas invert` filter — check hue).

## Điểm MẠNH (xác nhận trong test)
- home + detail (desktop+mobile): 0 overflow, serif h1, 0 broken img, console sạch, mobile nav/CTA đúng, 0 touch-target <40px.
- `bang-xep-hang`, `gioi-thieu`, legal pages, `tim-kiem` zero-result: kỷ luật cao, dark+RM đầy đủ, v-html an toàn (mdLite escape-whitelist).
- SSR 200 toàn bộ 33 route. 8 sóng giữ vững dưới test thật.
